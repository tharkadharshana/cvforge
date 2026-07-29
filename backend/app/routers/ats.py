from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from .. import models, audit, billing
from ..database import get_db
from ..auth import get_optional_user
from ..cv import prompts
from ..cv.extract import extract_text, UnsupportedFile
from ..llm.orchestrator import critic
from ..logging_config import get_logger, client_ip_var
from ..errors import opaque_502

router = APIRouter(prefix="/ats", tags=["ats"])
log = get_logger("ats")

FREE_CHECKS_PER_DAY = 2
MIN_CV_CHARS = 50
MAX_CV_CHARS = 20_000  # keep the LLM prompt bounded

CATEGORY_KEYS = ("sections", "ats_essentials", "hr_red_flags", "discrimination", "seniority", "tailoring")


def _checks_used_today(db: Session, ip: str) -> int:
    # Rate limiting rides on the audit trail: every successful check writes an
    # "ats_check" audit row with the client IP, so counting today's rows *is*
    # the quota. No extra table, survives serverless restarts.
    # ponytail: naive UTC bind (SQLite stores naive; PG session is UTC); racing
    # requests from one IP can slip past the cap — acceptable for a free tool.
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0,
                                                   microsecond=0, tzinfo=None)
    return db.query(models.AuditEvent).filter(
        models.AuditEvent.event == "ats_check",
        models.AuditEvent.status == "ok",
        models.AuditEvent.ip == (ip or ""),
        models.AuditEvent.created_at >= day_start,
    ).count()


@router.post("/check")
async def check(file: Optional[UploadFile] = File(None),
                raw_text: str = Form(""),
                job_description: str = Form(""),
                db: Session = Depends(get_db),
                user: Optional[models.User] = Depends(get_optional_user)):
    """Public ATS score check: upload a CV (PDF/DOCX/TXT) or paste text, optional JD.

    Anonymous and free users get FREE_CHECKS_PER_DAY per IP with issue titles only.
    Paid users get unlimited checks plus the full fix instructions per issue.
    """
    if file is not None:
        content = await file.read()
        try:
            text = extract_text(file.filename, content, file.content_type or "")
        except UnsupportedFile as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.error("ats/check extract error: %s", e, exc_info=True)
            raise HTTPException(status_code=400, detail="Could not read file. Try a different file or paste the text instead.")
    else:
        text = raw_text.strip()
    if len(text) < MIN_CV_CHARS:
        raise HTTPException(status_code=400, detail="That doesn't look like a CV — upload a file or paste the full text.")

    detailed = user is not None and billing.is_paid(user)
    ip = client_ip_var.get()
    used = 0
    if not detailed:
        used = _checks_used_today(db, ip)
        if used >= FREE_CHECKS_PER_DAY:
            audit.record("ats_check", status="blocked", user_id=user.id if user else None,
                         meta={"why": "daily_limit"})
            raise HTTPException(status_code=429,
                                detail="Free limit reached (2 checks per day). Come back tomorrow or upgrade for unlimited checks.")

    sys, usr = prompts.ats_check(text[:MAX_CV_CHARS], job_description)
    try:
        crit = critic().complete_json(sys, usr)
    except Exception as e:
        raise opaque_502(log, "ATS analysis failed", e)

    categories = crit.get("categories") or {}
    categories = {k: categories.get(k) for k in CATEGORY_KEYS}
    issues = [i for i in (crit.get("issues") or []) if isinstance(i, dict)]
    if not detailed:
        # free/anonymous: the diagnosis is free, the cure ("fix") is the paid part
        issues = [{k: i.get(k, "") for k in ("category", "severity", "title")} for i in issues]

    audit.record("ats_check", user_id=user.id if user else None,
                 meta={"ats_score": crit.get("ats_score"), "detailed": detailed,
                       "issues": len(issues), "had_jd": bool(job_description.strip())})
    return {
        "ats_score": int(crit.get("ats_score") or 0),
        "parse_rate": int(crit.get("parse_rate") or 0),
        "categories": categories,
        "issues": issues,
        "issue_count": len(issues),
        "detailed": detailed,
        "checks_left": None if detailed else max(0, FREE_CHECKS_PER_DAY - used - 1),
    }
