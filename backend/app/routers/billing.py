from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .. import models, schemas, billing, audit
from ..database import get_db
from ..auth import get_current_user
from ..config import settings
from ..payments import polar
from ..logging_config import get_logger

router = APIRouter(prefix="/billing", tags=["billing"])
log = get_logger("billing.api")


def _plan_out(p: billing.Plan) -> schemas.PlanOut:
    return schemas.PlanOut(id=p.id, name=p.name, price_usd=p.price_usd, credits=p.credits,
                           recurring=p.recurring, available=bool(p.polar_product_id),
                           price_per_credit=p.price_per_credit, margin_pct=p.margin_pct,
                           min_ats_score=p.min_ats_score)


def _summary_out(db: Session, user: models.User) -> schemas.BillingSummary:
    billing.maybe_refill_monthly(db, user)
    return schemas.BillingSummary(
        billing_enabled=settings.billing_enabled,
        plan=user.plan,
        credits=user.credits or 0,
        free_tier_mode=settings.free_tier_mode,
        credits_per_generation=settings.credits_per_generation,
        has_customer=bool(user.polar_customer_id),
        plans=[_plan_out(p) for p in billing.get_plans()],
    )


def _ledger_out(db: Session, user: models.User) -> list[schemas.LedgerRow]:
    rows = db.query(models.CreditLedger).filter(models.CreditLedger.user_id == user.id) \
        .order_by(models.CreditLedger.created_at.desc()).limit(50).all()
    return [schemas.LedgerRow(delta=r.delta, reason=r.reason, balance_after=r.balance_after,
                              created_at=r.created_at.isoformat()) for r in rows]


@router.get("/summary", response_model=schemas.BillingSummary)
def summary(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _summary_out(db, user)


@router.get("/ledger", response_model=list[schemas.LedgerRow])
def ledger(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _ledger_out(db, user)


@router.get("/overview", response_model=schemas.BillingOverview)
def overview(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Combined summary + ledger in one round trip (avoids two concurrent
    cold-start invocations for the billing page)."""
    return schemas.BillingOverview(summary=_summary_out(db, user), ledger=_ledger_out(db, user))


@router.post("/checkout", response_model=schemas.CheckoutOut)
def checkout(plan_id: str, user: models.User = Depends(get_current_user)):
    plan = billing.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Unknown plan")
    try:
        url = polar.create_checkout(plan, user)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("checkout error: %s", e)
        raise HTTPException(status_code=502, detail="Could not start checkout. Try again.")
    audit.record("checkout_started", user_id=user.id, meta={"plan_id": plan.id, "recurring": plan.recurring})
    return schemas.CheckoutOut(checkout_url=url)


@router.post("/portal", response_model=schemas.CheckoutOut)
def portal(user: models.User = Depends(get_current_user)):
    """Hosted portal to manage saved cards, subscriptions, invoices."""
    if not user.polar_customer_id:
        raise HTTPException(status_code=400, detail="No billing account yet — make a purchase first.")
    try:
        url = polar.create_portal_session(user.polar_customer_id)
    except Exception as e:
        log.error("portal error: %s", e)
        raise HTTPException(status_code=502, detail="Could not open billing portal. Try again.")
    audit.record("portal_opened", user_id=user.id)
    return schemas.CheckoutOut(checkout_url=url)


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Polar webhook. Source of truth for crediting. Verified via Standard Webhooks (fail closed)."""
    body = await request.body()
    headers = {
        "webhook-id": request.headers.get("webhook-id", ""),
        "webhook-timestamp": request.headers.get("webhook-timestamp", ""),
        "webhook-signature": request.headers.get("webhook-signature", ""),
    }
    if not settings.polar_webhook_secret:
        log.error("POLAR_WEBHOOK_SECRET not set — rejecting webhook")
        raise HTTPException(status_code=503, detail="billing not configured")
    try:
        event = polar.verify_webhook(body, headers)   # raises on bad signature / stale timestamp
    except Exception as e:
        log.warning("webhook signature rejected: %s", e)
        audit.record("webhook_received", status="rejected", meta={"why": "bad_signature"})
        raise HTTPException(status_code=401, detail="invalid signature")

    etype = event.get("type")
    data = event.get("data", {}) or {}
    log.info("webhook verified type=%s", etype)
    audit.record("webhook_received", meta={"type": etype})

    # order.paid fires for one-time purchases AND subscription renewals -> credit each time
    if etype == "order.paid":
        _handle_order_paid(db, data)
    elif etype in ("subscription.canceled", "subscription.revoked"):
        _handle_subscription_end(db, data)
    return {"ok": True}


def _handle_subscription_end(db: Session, data: dict):
    meta = data.get("metadata") or {}
    customer = data.get("customer") or {}
    user = None
    uid = meta.get("user_id")
    if uid:
        try:
            user = db.get(models.User, int(uid))
        except (ValueError, TypeError):
            user = None
    if not user and customer.get("id"):
        user = db.query(models.User).filter(models.User.polar_customer_id == customer["id"]).first()
    if not user and customer.get("email"):
        user = db.query(models.User).filter(models.User.email == customer["email"]).first()
    if not user:
        log.warning("subscription end unmatched meta=%s", meta)
        return
    user.plan = "free"          # keep remaining credits; just drop the paid plan label
    db.commit()
    audit.record("subscription_canceled", user_id=user.id)
    log.info("subscription ended user=%s -> free", user.id)


def _handle_order_paid(db: Session, data: dict):
    order_id = str(data.get("id", ""))
    if not order_id:
        log.warning("order.paid missing id")
        return

    meta = data.get("metadata") or {}
    customer = data.get("customer") or {}
    product_id = data.get("product_id") or (data.get("product") or {}).get("id", "")

    # resolve plan: metadata.plan_id (set by us at checkout) -> product mapping
    plan = billing.get_plan(meta.get("plan_id", "")) or billing.get_plan_by_product(product_id)
    if not plan:
        log.warning("order.paid unmatched product=%s meta=%s", product_id, meta)
        return

    # resolve user: trusted server-set metadata.user_id -> fallback to customer email
    user = None
    uid = meta.get("user_id")
    if uid:
        try:
            user = db.get(models.User, int(uid))
        except (ValueError, TypeError):
            user = None
    if not user and customer.get("email"):
        user = db.query(models.User).filter(models.User.email == customer["email"]).first()
    if not user:
        log.warning("order.paid unmatched user meta=%s email=%s", meta, customer.get("email"))
        return

    # store polar customer id for the portal
    cust_id = customer.get("id")
    if cust_id and not user.polar_customer_id:
        user.polar_customer_id = cust_id

    # idempotent credit (dedupe on order id)
    granted = billing.add_purchase(db, user, plan, order_id)
    if granted:
        audit.record("purchase", user_id=user.id,
                     meta={"plan_id": plan.id, "credits": plan.credits, "order_id": order_id,
                           "amount_usd": plan.price_usd})
    log.info("order.paid user=%s plan=%s granted=%s", user.id, plan.id, granted)
