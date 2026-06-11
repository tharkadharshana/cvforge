from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
from .config import settings
from .logging_config import get_logger
from . import models

log = get_logger("billing")


@dataclass
class Plan:
    id: str
    name: str
    price_usd: float
    credits: int
    polar_product_id: str = ""
    recurring: bool = False

    @property
    def price_per_credit(self) -> float:
        return round(self.price_usd / self.credits, 4) if self.credits else 0.0

    @property
    def margin_pct(self) -> float:
        """Profit margin given your per-generation cost. Tune via env."""
        cost_per_credit = settings.cost_per_generation_usd / max(settings.credits_per_generation, 1)
        ppc = self.price_per_credit
        if ppc <= 0:
            return 0.0
        return round((ppc - cost_per_credit) / ppc * 100, 1)


def get_plans() -> list[Plan]:
    try:
        raw = json.loads(settings.billing_plans_json)
        return [Plan(**p) for p in raw]
    except Exception as e:
        log.error("bad BILLING_PLANS_JSON: %s", e)
        return []


def get_plan(plan_id: str) -> Plan | None:
    return next((p for p in get_plans() if p.id == plan_id), None)


def get_plan_by_product(product_id: str) -> Plan | None:
    return next((p for p in get_plans() if p.polar_product_id and p.polar_product_id == product_id), None)


# ---------- credit operations ----------
def _ledger(db: Session, user: models.User, delta: int, reason: str, ref: str = ""):
    user.credits = (user.credits or 0) + delta
    db.add(models.CreditLedger(user_id=user.id, delta=delta, reason=reason,
                               balance_after=user.credits, ref=ref))
    log.info("credit %s%d user=%s reason=%s balance=%d", "+" if delta >= 0 else "", delta, user.id, reason, user.credits)


def grant_signup_credits(db: Session, user: models.User):
    if not settings.billing_enabled:
        return
    if settings.free_tier_mode == "forever_free":
        user.plan = "free"
        user.monthly_refill_at = _next_month()
        _ledger(db, user, settings.free_monthly_credits, "signup_free_monthly")
    else:  # trial
        user.plan = "trial"
        _ledger(db, user, settings.free_trial_credits, "signup_trial")


def maybe_refill_monthly(db: Session, user: models.User):
    """forever_free: top back up to the monthly allowance when the period rolls over."""
    if not settings.billing_enabled or settings.free_tier_mode != "forever_free":
        return
    if user.plan != "free":
        return
    now = datetime.now(timezone.utc)
    refill_at = user.monthly_refill_at
    if refill_at is not None and refill_at.tzinfo is None:
        refill_at = refill_at.replace(tzinfo=timezone.utc)
    if refill_at is None or now >= refill_at:
        target = settings.free_monthly_credits
        if (user.credits or 0) < target:
            _ledger(db, user, target - (user.credits or 0), "monthly_refill")
        user.monthly_refill_at = _next_month()
        db.commit()


def has_credits(user: models.User, amount: int | None = None) -> bool:
    if not settings.billing_enabled:
        return True
    need = settings.credits_per_generation if amount is None else amount
    return (user.credits or 0) >= need


def charge_generation(db: Session, user: models.User, ref: str = ""):
    if not settings.billing_enabled:
        return
    _ledger(db, user, -settings.credits_per_generation, "generation", ref)
    db.commit()


def add_purchase(db: Session, user: models.User, plan: Plan, provider_ref: str):
    """Idempotent credit top-up from a confirmed payment."""
    exists = db.query(models.Payment).filter(models.Payment.provider_ref == provider_ref).first()
    if exists:
        log.info("duplicate webhook ignored ref=%s", provider_ref)
        return False
    db.add(models.Payment(user_id=user.id, provider=settings.billing_provider, provider_ref=provider_ref,
                          amount_usd=plan.price_usd, credits=plan.credits, plan_id=plan.id, status="paid"))
    user.plan = plan.id
    _ledger(db, user, plan.credits, f"purchase:{plan.id}", provider_ref)
    db.commit()
    return True


def _next_month() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)
