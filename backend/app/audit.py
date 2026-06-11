from __future__ import annotations
from typing import Optional
from .database import SessionLocal
from .logging_config import get_logger, request_id_var, client_ip_var
from . import models

log = get_logger("audit")

# events that are part of normal money/security flows we always want a trail for
# (free-form strings are allowed; this is just documentation)
EVENTS = {
    "register", "login", "login_failed",
    "cv_import", "cv_import_file", "cv_build", "cv_qualification", "cv_edit",
    "generate", "checkout_started", "portal_opened",
    "webhook_received", "purchase", "subscription_canceled",
    "admin_credit_adjust",
}


def record(event: str, *, status: str = "ok", user_id: Optional[int] = None,
           meta: Optional[dict] = None, request_id: Optional[str] = None,
           ip: Optional[str] = None) -> None:
    """Write a durable audit row. Uses its own session so it persists independently of the
    request transaction (a failed/rolled-back request still leaves its audit trail).
    Never raises — auditing must not break the request."""
    rid = request_id if request_id is not None else request_id_var.get()
    cip = ip if ip is not None else client_ip_var.get()
    meta = _safe_meta(meta or {})
    db = SessionLocal()
    try:
        db.add(models.AuditEvent(user_id=user_id, request_id=rid or "", event=event,
                                 status=status, ip=cip or "", meta=meta))
        db.commit()
    except Exception as e:  # pragma: no cover
        log.error("audit write failed event=%s: %s", event, e)
        db.rollback()
    finally:
        db.close()
    log.info("audit event=%s status=%s user=%s", event, status, user_id)


# never let raw user content (CV text, JD, cover letters) into audit meta — keep it non-PII
_BLOCKED_KEYS = {"raw_text", "text", "job_description", "cover_letter", "cv", "tailored_cv", "password"}


def _safe_meta(meta: dict) -> dict:
    out = {}
    for k, v in meta.items():
        if k in _BLOCKED_KEYS:
            continue
        if isinstance(v, str) and len(v) > 300:
            out[k] = v[:300] + "…"
        else:
            out[k] = v
    return out
