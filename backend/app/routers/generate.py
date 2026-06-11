from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from .. import models, schemas, billing, audit
from ..database import get_db
from ..auth import get_current_user
from ..schemas import CVData
from ..cv import pipeline, render
from ..logging_config import get_logger

router = APIRouter(tags=["generate"])
log = get_logger("generate")


@router.post("/generate", response_model=schemas.GenerateOut)
def generate(payload: schemas.GenerateIn, db: Session = Depends(get_db),
             user: models.User = Depends(get_current_user)):
    has_cv = user.base_cv and user.base_cv.data.get("contact", {}).get("full_name")
    if not has_cv:
        log.warning("generate blocked user=%s: no base CV", user.id)
        audit.record("generate", status="blocked", user_id=user.id, meta={"why": "no_base_cv"})
        raise HTTPException(status_code=400, detail="Set up your base CV first")

    billing.maybe_refill_monthly(db, user)
    if not billing.has_credits(user):
        log.warning("generate blocked user=%s: out of credits (%s)", user.id, user.credits)
        audit.record("generate", status="blocked", user_id=user.id,
                     meta={"why": "no_credits", "credits": user.credits or 0})
        raise HTTPException(status_code=402, detail="Out of credits. Upgrade to keep generating.")

    log.info("generate user=%s company=%r title=%r credits=%s",
             user.id, payload.company, payload.job_title, user.credits)
    base = CVData.model_validate(user.base_cv.data)
    try:
        tailored, cover, crit = pipeline.generate_application(
            base, payload.job_description, payload.company, payload.job_title
        )
    except Exception as e:
        audit.record("generate", status="failed", user_id=user.id,
                     meta={"why": "llm_error", "error": str(e)[:200],
                           "company": payload.company, "title": payload.job_title})
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")
    app = models.Application(
        user_id=user.id,
        job_title=payload.job_title,
        company=payload.company,
        job_description=payload.job_description,
        tailored_cv=tailored.model_dump(),
        cover_letter=cover,
        ats_score=int(crit.get("ats_score", 0)),
        critique=crit,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    billing.charge_generation(db, user, ref=str(app.id))
    audit.record("generate", status="ok", user_id=user.id,
                 meta={"application_id": app.id, "ats_score": app.ats_score,
                       "company": payload.company, "title": payload.job_title,
                       "credits_after": user.credits})
    return schemas.GenerateOut(
        application_id=app.id,
        tailored_cv=tailored,
        cover_letter=cover,
        critique=schemas.CritiqueOut(**crit),
    )


@router.get("/applications")
def list_applications(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    apps = db.query(models.Application).filter(models.Application.user_id == user.id) \
        .order_by(models.Application.created_at.desc()).all()
    return [
        {"id": a.id, "job_title": a.job_title, "company": a.company,
         "ats_score": a.ats_score, "created_at": a.created_at.isoformat()}
        for a in apps
    ]


def _get_app(db: Session, user: models.User, app_id: int) -> models.Application:
    a = db.query(models.Application).filter(
        models.Application.id == app_id, models.Application.user_id == user.id
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Application not found")
    return a


@router.get("/applications/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    a = _get_app(db, user, app_id)
    return {
        "id": a.id, "job_title": a.job_title, "company": a.company,
        "tailored_cv": a.tailored_cv, "cover_letter": a.cover_letter,
        "ats_score": a.ats_score, "critique": a.critique,
    }


@router.get("/applications/{app_id}/download")
def download(app_id: int, doc: str = "cv", fmt: str = "pdf",
             db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """doc=cv|cover  fmt=pdf|docx"""
    a = _get_app(db, user, app_id)
    cv = CVData.model_validate(a.tailored_cv)
    slug = (a.company or "application").replace(" ", "_")

    if doc == "cv" and fmt == "pdf":
        return Response(render.render_pdf(cv), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="CV_{slug}.pdf"'})
    if doc == "cv" and fmt == "docx":
        return Response(render.render_docx(cv),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="CV_{slug}.docx"'})
    if doc == "cover" and fmt == "docx":
        return Response(render.render_cover_letter_docx(a.cover_letter, cv.contact.full_name),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="CoverLetter_{slug}.docx"'})
    if doc == "cover" and fmt == "pdf":
        from .. import schemas as _s  # noqa
        contact = cv.contact
        line = "  |  ".join([x for x in [contact.email, contact.phone, contact.location] if x])
        return Response(render.render_cover_letter_pdf(a.cover_letter, line, contact.full_name),
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="CoverLetter_{slug}.pdf"'})
    raise HTTPException(status_code=400, detail="bad doc/fmt")
