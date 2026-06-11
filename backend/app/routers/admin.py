from __future__ import annotations
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from .. import models, billing, audit
from ..database import get_db
from ..auth import get_current_admin
from ..logging_config import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
log = get_logger("admin")


def _user_row(u: models.User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "plan": u.plan,
            "credits": u.credits or 0, "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None}


@router.get("/users")
def list_users(query: str = Query("", description="email/name substring"),
               limit: int = 50, db: Session = Depends(get_db),
               admin: models.User = Depends(get_current_admin)):
    q = db.query(models.User)
    if query:
        like = f"%{query}%"
        q = q.filter(or_(models.User.email.ilike(like), models.User.full_name.ilike(like)))
    users = q.order_by(models.User.created_at.desc()).limit(min(limit, 200)).all()
    return [_user_row(u) for u in users]


@router.get("/users/{user_id}")
def user_detail(user_id: int, db: Session = Depends(get_db),
                admin: models.User = Depends(get_current_admin)):
    """Full investigation view: profile, credits, payments, ledger, audit trail, generations."""
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    payments = db.query(models.Payment).filter(models.Payment.user_id == user_id) \
        .order_by(models.Payment.created_at.desc()).limit(50).all()
    ledger = db.query(models.CreditLedger).filter(models.CreditLedger.user_id == user_id) \
        .order_by(models.CreditLedger.created_at.desc()).limit(100).all()
    events = db.query(models.AuditEvent).filter(models.AuditEvent.user_id == user_id) \
        .order_by(models.AuditEvent.created_at.desc()).limit(100).all()
    apps = db.query(models.Application).filter(models.Application.user_id == user_id) \
        .order_by(models.Application.created_at.desc()).limit(50).all()

    return {
        "user": _user_row(u),
        "payments": [{"id": p.id, "provider": p.provider, "provider_ref": p.provider_ref,
                      "plan_id": p.plan_id, "amount_usd": p.amount_usd, "credits": p.credits,
                      "status": p.status, "created_at": p.created_at.isoformat()} for p in payments],
        "ledger": [{"delta": r.delta, "reason": r.reason, "balance_after": r.balance_after,
                    "ref": r.ref, "created_at": r.created_at.isoformat()} for r in ledger],
        "audit": [{"event": e.event, "status": e.status, "request_id": e.request_id, "ip": e.ip,
                   "meta": e.meta, "created_at": e.created_at.isoformat()} for e in events],
        "generations": [{"id": a.id, "job_title": a.job_title, "company": a.company,
                         "ats_score": a.ats_score, "created_at": a.created_at.isoformat()} for a in apps],
    }


@router.get("/audit")
def audit_search(user_id: int | None = None, event: str | None = None,
                 request_id: str | None = None, status: str | None = None,
                 limit: int = 100, db: Session = Depends(get_db),
                 admin: models.User = Depends(get_current_admin)):
    q = db.query(models.AuditEvent)
    if user_id is not None:
        q = q.filter(models.AuditEvent.user_id == user_id)
    if event:
        q = q.filter(models.AuditEvent.event == event)
    if request_id:
        q = q.filter(models.AuditEvent.request_id == request_id)
    if status:
        q = q.filter(models.AuditEvent.status == status)
    rows = q.order_by(models.AuditEvent.created_at.desc()).limit(min(limit, 500)).all()
    return [{"id": e.id, "user_id": e.user_id, "event": e.event, "status": e.status,
             "request_id": e.request_id, "ip": e.ip, "meta": e.meta,
             "created_at": e.created_at.isoformat()} for e in rows]


class CreditAdjustIn(BaseModel):
    delta: int = Field(description="positive grants, negative refunds/removes")
    reason: str = Field(min_length=2, max_length=80)


@router.post("/users/{user_id}/credits")
def adjust_credits(user_id: int, payload: CreditAdjustIn, db: Session = Depends(get_db),
                   admin: models.User = Depends(get_current_admin)):
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.credits = (u.credits or 0) + payload.delta
    db.add(models.CreditLedger(user_id=u.id, delta=payload.delta,
                               reason=f"admin:{payload.reason}", balance_after=u.credits,
                               ref=f"admin:{admin.email}"))
    db.commit()
    audit.record("admin_credit_adjust", user_id=u.id,
                 meta={"delta": payload.delta, "reason": payload.reason, "by": admin.email,
                       "balance_after": u.credits})
    log.info("admin %s adjusted user=%s by %d -> %d", admin.email, u.id, payload.delta, u.credits)
    return {"user_id": u.id, "credits": u.credits}
