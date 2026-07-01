from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from .. import models, schemas, billing, audit
from ..config import settings
from ..database import get_db
from ..auth import get_current_user
from ..schemas import CVData
from ..cv import pipeline, prompts, render, templates
from ..llm.orchestrator import drafter, critic
from ..logging_config import get_logger

router = APIRouter(tags=["generate"])
log = get_logger("generate")

# "quality" tier may use the pro model for tailoring (slower, current behavior).
# "fast" (default, required on Vercel) always uses the flash/non-pro model so a
# single call comfortably finishes well under the 60s function limit.
_TAILOR_PRO = settings.generation_tier == "quality"


def _get_job(db: Session, user: models.User, job_id: int) -> models.Application:
    job = db.query(models.Application).filter(
        models.Application.id == job_id, models.Application.user_id == user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


def _fail(db: Session, user: models.User, job: models.Application, step: str, e: Exception):
    job.status = "failed"
    job.error = str(e)[:500]
    db.commit()
    audit.record("generate_failed", status="failed", user_id=user.id,
                 meta={"job_id": job.id, "step": step, "error": str(e)[:200]})
    raise HTTPException(status_code=502, detail=f"LLM generation failed at step '{step}': {e}")


@router.get("/templates")
def list_templates():
    """The CV render template catalog (shared by the picker and the browser extension)."""
    return {"templates": templates.catalog(), "default": templates.DEFAULT_TEMPLATE_ID}


@router.post("/generate/start", response_model=schemas.GenerateStartOut)
def start(payload: schemas.GenerateIn, db: Session = Depends(get_db),
          user: models.User = Depends(get_current_user)):
    has_cv = user.base_cv and user.base_cv.data.get("contact", {}).get("full_name")
    if not has_cv:
        log.warning("generate/start blocked user=%s: no base CV", user.id)
        audit.record("generate_start", status="blocked", user_id=user.id, meta={"why": "no_base_cv"})
        raise HTTPException(status_code=400, detail="Set up your base CV first")

    billing.maybe_refill_monthly(db, user)
    if not billing.has_credits(user):
        log.warning("generate/start blocked user=%s: out of credits (%s)", user.id, user.credits)
        audit.record("generate_start", status="blocked", user_id=user.id,
                     meta={"why": "no_credits", "credits": user.credits or 0})
        raise HTTPException(status_code=402, detail="Out of credits. Upgrade to keep generating.")

    template_id = payload.template_id if payload.template_id in templates.TEMPLATES else templates.DEFAULT_TEMPLATE_ID
    job = models.Application(
        user_id=user.id,
        job_title=payload.job_title,
        company=payload.company,
        job_description=payload.job_description,
        template_id=template_id,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    log.info("generate/start user=%s job=%s company=%r title=%r credits=%s",
             user.id, job.id, payload.company, payload.job_title, user.credits)
    audit.record("generate_start", status="ok", user_id=user.id,
                 meta={"job_id": job.id, "company": payload.company, "title": payload.job_title})
    return schemas.GenerateStartOut(job_id=job.id, status=job.status)


@router.post("/generate/{job_id}/tailor", response_model=schemas.GenerateTailorOut)
def tailor(job_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = _get_job(db, user, job_id)
    if job.status not in ("pending", "tailored", "failed"):
        raise HTTPException(status_code=409, detail=f"Job is '{job.status}', cannot run tailor step")

    base = CVData.model_validate(user.base_cv.data)
    try:
        sys, usr = prompts.tailor_cv(base.model_dump(), job.job_description)
        tailored = CVData.model_validate(drafter().complete_json(sys, usr, pro=_TAILOR_PRO))
    except Exception as e:
        _fail(db, user, job, "tailor", e)

    job.tailored_cv = tailored.model_dump()
    job.status = "tailored"
    job.error = None
    db.commit()
    audit.record("generate_tailor", status="ok", user_id=user.id, meta={"job_id": job.id})
    return schemas.GenerateTailorOut(job_id=job.id, status=job.status, tailored_cv=tailored)


@router.post("/generate/{job_id}/cover", response_model=schemas.GenerateCoverOut)
def cover(job_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = _get_job(db, user, job_id)
    if job.status not in ("tailored", "covered", "failed") or not job.tailored_cv:
        raise HTTPException(status_code=409, detail=f"Job is '{job.status}', cannot run cover step")

    try:
        sys, usr = prompts.cover_letter(job.tailored_cv, job.job_description, job.company, job.job_title)
        letter = drafter().complete(sys, usr).strip()
    except Exception as e:
        _fail(db, user, job, "cover", e)

    job.cover_letter = letter
    job.status = "covered"
    job.error = None
    db.commit()
    audit.record("generate_cover", status="ok", user_id=user.id, meta={"job_id": job.id})
    return schemas.GenerateCoverOut(job_id=job.id, status=job.status, cover_letter=letter)


def _score_cv(user: models.User, tailored_cv: dict, cover_letter: str, job_description: str) -> dict:
    """Run the ATS critic on a CV/cover/JD and return a fully-populated critique dict.

    Shared by the critique step and the manual-edit re-evaluate endpoint so both
    produce the same critique shape and honour the plan's ATS guarantee.
    """
    sys, usr = prompts.critique(tailored_cv, cover_letter, job_description)
    crit = critic().complete_json(sys, usr)
    for k, d in (("ats_score", 0), ("keyword_matches", []), ("missing_keywords", []),
                 ("human_tone_notes", []), ("suggestions", [])):
        crit.setdefault(k, d)
    pipeline.annotate_ats_guarantee(crit, billing.min_ats_score_for(user))
    return crit


@router.post("/generate/{job_id}/critique", response_model=schemas.GenerateCritiqueOut)
def critique(job_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = _get_job(db, user, job_id)
    if job.status not in ("covered", "done", "failed") or not job.cover_letter:
        raise HTTPException(status_code=409, detail=f"Job is '{job.status}', cannot run critique step")

    try:
        crit = _score_cv(user, job.tailored_cv, job.cover_letter, job.job_description)
    except Exception as e:
        _fail(db, user, job, "critique", e)

    job.critique = crit
    job.ats_score = int(crit.get("ats_score", 0))
    job.ats_stale = False
    job.status = "done"
    job.error = None

    credits_after = user.credits
    if not job.charged:
        billing.charge_generation(db, user, ref=str(job.id))
        job.charged = True
        credits_after = user.credits
    db.commit()

    audit.record("generate_done", status="ok", user_id=user.id,
                 meta={"job_id": job.id, "ats_score": job.ats_score, "credits_after": credits_after})
    return schemas.GenerateCritiqueOut(
        job_id=job.id, status=job.status, application_id=job.id,
        critique=schemas.CritiqueOut(**crit), ats_score=job.ats_score,
    )


@router.get("/generate/{job_id}", response_model=schemas.GenerateJobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = _get_job(db, user, job_id)
    return schemas.GenerateJobOut(
        job_id=job.id,
        status=job.status,
        job_title=job.job_title,
        company=job.company,
        tailored_cv=CVData.model_validate(job.tailored_cv) if job.tailored_cv else None,
        cover_letter=job.cover_letter,
        critique=schemas.CritiqueOut(**job.critique) if job.critique else None,
        ats_score=job.ats_score,
        error=job.error,
    )


@router.post("/applications/{app_id}/improve", response_model=schemas.GenerateOut)
def improve_application(app_id: int, auto: bool = False, db: Session = Depends(get_db),
                         user: models.User = Depends(get_current_user)):
    a = _get_app(db, user, app_id)
    if a.status != "done":
        raise HTTPException(status_code=409, detail="Application is not complete yet")

    billing.maybe_refill_monthly(db, user)

    # An "auto" improve is a free retry the backend offers to honor the plan's ATS
    # guarantee: only allowed for paid plans with a guarantee (min > 0) whose current
    # score is still below it. Anything else falls back to a normal charged improve.
    target = billing.min_ats_score_for(user)
    free = auto and target > 0 and int(a.ats_score or 0) < target
    if not free and not billing.has_credits(user):
        log.warning("improve blocked user=%s: out of credits (%s)", user.id, user.credits)
        audit.record("generate_improve", status="blocked", user_id=user.id,
                     meta={"why": "no_credits", "credits": user.credits or 0, "application_id": app_id})
        raise HTTPException(status_code=402, detail="Out of credits. Upgrade to keep improving.")

    base = CVData.model_validate(user.base_cv.data)
    prev_cv = CVData.model_validate(a.tailored_cv)
    log.info("improve user=%s application=%s prev_score=%s credits=%s",
             user.id, a.id, a.ats_score, user.credits)
    try:
        tailored, cover_text, crit = pipeline.improve_application(
            base, prev_cv, a.cover_letter, a.critique or {}, a.job_description, a.company, a.job_title
        )
    except Exception as e:
        audit.record("generate_improve", status="failed", user_id=user.id,
                     meta={"why": "llm_error", "error": str(e)[:200], "application_id": a.id})
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

    pipeline.annotate_ats_guarantee(crit, target)
    new_score = int(crit.get("ats_score", 0))

    # Never let a retry regress the result: keep the new pass only if it scores
    # at least as high as what the user already had.
    if new_score >= int(a.ats_score or 0):
        a.tailored_cv = tailored.model_dump()
        a.cover_letter = cover_text
        a.ats_score = new_score
        a.critique = crit
        out_cv, out_cover, out_crit = tailored, cover_text, crit
    else:
        out_cv = CVData.model_validate(a.tailored_cv)
        out_cover = a.cover_letter
        out_crit = pipeline.annotate_ats_guarantee(a.critique or {}, target)
    db.commit()
    db.refresh(a)

    if not free:
        billing.charge_generation(db, user, ref=f"improve:{a.id}")
    audit.record("generate_improve", status="ok", user_id=user.id,
                 meta={"application_id": a.id, "ats_score": a.ats_score,
                       "auto": free, "charged": not free, "credits_after": user.credits})
    return schemas.GenerateOut(
        application_id=a.id,
        tailored_cv=out_cv,
        cover_letter=out_cover,
        critique=schemas.CritiqueOut(**out_crit),
    )


@router.get("/applications")
def list_applications(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    apps = db.query(models.Application).filter(
        models.Application.user_id == user.id, models.Application.status == "done"
    ).order_by(models.Application.created_at.desc()).all()
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
        "ats_score": a.ats_score, "critique": a.critique, "status": a.status,
        "ats_stale": bool(a.ats_stale),
        "template_id": a.template_id or "ats_classic",
        "template_overrides": a.template_overrides,
    }


@router.patch("/applications/{app_id}")
def patch_application(app_id: int, payload: schemas.ApplicationPatchIn,
                      db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Update a completed application in place.

    - Editing ``tailored_cv``/``cover_letter`` is a free manual edit: it saves the
      new content and marks the ATS score stale (hidden in the UI until the user
      re-evaluates). No LLM call, no credit.
    - Setting ``template_id``/``template_overrides`` only changes how the CV is
      rendered; it never touches the score.
    """
    a = _get_app(db, user, app_id)
    if a.status != "done":
        raise HTTPException(status_code=409, detail="Application is not complete yet")

    edited_content = False
    if payload.template_id is not None:
        if payload.template_id not in templates.TEMPLATES:
            raise HTTPException(status_code=400, detail=f"Unknown template '{payload.template_id}'")
        a.template_id = payload.template_id
    if payload.template_overrides is not None:
        a.template_overrides = payload.template_overrides
    if payload.tailored_cv is not None:
        a.tailored_cv = payload.tailored_cv.model_dump()
        edited_content = True
    if payload.cover_letter is not None:
        a.cover_letter = payload.cover_letter
        edited_content = True

    if edited_content:
        # The stored score/critique no longer reflect the edited CV. Keep them for
        # reference but flag them stale so the UI hides the score until re-eval.
        a.ats_stale = True

    db.commit()
    db.refresh(a)
    if edited_content:
        audit.record("application_edit", status="ok", user_id=user.id,
                     meta={"application_id": a.id, "template_id": a.template_id})
    return get_application(app_id, db, user)


@router.post("/applications/{app_id}/reevaluate")
def reevaluate_application(app_id: int, db: Session = Depends(get_db),
                           user: models.User = Depends(get_current_user)):
    """Re-run the ATS critic after a manual edit and restore the score.

    Billing mirrors the auto-tune free-retry policy: the first re-evaluation after
    an edit (``ats_stale`` is set) is free, since the user is only re-scoring content
    they already paid to generate. A re-evaluation of an already-scored CV costs a
    credit like any other LLM pass.
    """
    a = _get_app(db, user, app_id)
    if a.status != "done" or not a.tailored_cv:
        raise HTTPException(status_code=409, detail="Application is not complete yet")

    billing.maybe_refill_monthly(db, user)
    free = bool(a.ats_stale)
    if not free and not billing.has_credits(user):
        audit.record("application_reevaluate", status="blocked", user_id=user.id,
                     meta={"why": "no_credits", "credits": user.credits or 0, "application_id": app_id})
        raise HTTPException(status_code=402, detail="Out of credits. Upgrade to keep re-evaluating.")

    try:
        crit = _score_cv(user, a.tailored_cv, a.cover_letter or "", a.job_description)
    except Exception as e:
        audit.record("application_reevaluate", status="failed", user_id=user.id,
                     meta={"why": "llm_error", "error": str(e)[:200], "application_id": a.id})
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

    a.critique = crit
    a.ats_score = int(crit.get("ats_score", 0))
    a.ats_stale = False
    db.commit()

    if not free:
        billing.charge_generation(db, user, ref=f"reevaluate:{a.id}")
    audit.record("application_reevaluate", status="ok", user_id=user.id,
                 meta={"application_id": a.id, "ats_score": a.ats_score,
                       "free": free, "credits_after": user.credits})
    return get_application(app_id, db, user)


@router.get("/applications/{app_id}/download")
def download(app_id: int, doc: str = "cv", fmt: str = "pdf",
             db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """doc=cv|cover  fmt=pdf|docx"""
    a = _get_app(db, user, app_id)
    if a.status != "done" or not a.tailored_cv:
        raise HTTPException(status_code=409, detail="Application is not complete yet")
    cv = CVData.model_validate(a.tailored_cv)
    slug = (a.company or "application").replace(" ", "_")
    # ATS-safe style for the chosen template (designer templates fall back to the
    # default safe style; this is always the parseable file the user uploads).
    style = templates.resolve_style(a.template_id, a.template_overrides)

    if doc == "cv" and fmt == "pdf":
        return Response(render.render_pdf(cv, style), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="CV_{slug}.pdf"'})
    if doc == "cv" and fmt == "docx":
        return Response(render.render_docx(cv, style),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="CV_{slug}.docx"'})
    if doc == "cover" and fmt == "docx":
        return Response(render.render_cover_letter_docx(a.cover_letter, cv.contact.full_name),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="CoverLetter_{slug}.docx"'})
    if doc == "cover" and fmt == "pdf":
        contact = cv.contact
        line = "  |  ".join([x for x in [contact.email, contact.phone, contact.location] if x])
        return Response(render.render_cover_letter_pdf(a.cover_letter, line, contact.full_name),
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="CoverLetter_{slug}.pdf"'})
    raise HTTPException(status_code=400, detail="bad doc/fmt")
