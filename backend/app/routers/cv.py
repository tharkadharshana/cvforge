from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import models, schemas, audit
from ..database import get_db
from ..auth import get_current_user
from ..schemas import CVData
from ..cv import pipeline
from ..cv.extract import extract_text, UnsupportedFile
from ..logging_config import get_logger

router = APIRouter(prefix="/cv", tags=["base-cv"])
log = get_logger("cv")


class RawCVIn(BaseModel):
    raw_text: str


def _get_or_create(db: Session, user: models.User) -> models.BaseCV:
    if not user.base_cv:
        bc = models.BaseCV(user_id=user.id, data=CVData().model_dump())
        db.add(bc)
        db.commit()
        db.refresh(bc)
        return bc
    return user.base_cv


def _has_cv(cv: CVData) -> bool:
    return bool(cv.contact.full_name) and (
        bool(cv.experience) or bool(cv.education) or bool(cv.projects) or bool(cv.summary)
    )


@router.get("/status", response_model=schemas.CVStatus)
def status(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    bc = _get_or_create(db, user)
    cv = CVData.model_validate(bc.data)
    return schemas.CVStatus(
        has_base_cv=_has_cv(cv),
        experience_count=len(cv.experience),
        education_count=len(cv.education),
        project_count=len(cv.projects),
        skill_categories=len(cv.skills),
    )


@router.get("", response_model=schemas.CVData)
def get_base_cv(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    bc = _get_or_create(db, user)
    return CVData.model_validate(bc.data)


@router.post("/import", response_model=schemas.CVData)
def import_raw_cv(payload: RawCVIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Paste current CV text -> parsed into structured base CV."""
    log.info("import_raw_cv user=%s chars=%d", user.id, len(payload.raw_text))
    try:
        parsed = pipeline.parse_raw_cv(payload.raw_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CV parse failed: {e}")
    bc = _get_or_create(db, user)
    bc.data = parsed.model_dump()
    db.commit()
    audit.record("cv_import", user_id=user.id, meta={"exp": len(parsed.experience), "edu": len(parsed.education)})
    return parsed


@router.post("/import-file", response_model=schemas.CVData)
async def import_file(file: UploadFile = File(...), db: Session = Depends(get_db),
                      user: models.User = Depends(get_current_user)):
    """Upload PDF / DOCX / TXT -> text extracted -> parsed into structured base CV."""
    content = await file.read()
    log.info("import_file user=%s name=%r type=%r bytes=%d",
             user.id, file.filename, file.content_type, len(content))
    try:
        text = extract_text(file.filename, content, file.content_type or "")
    except UnsupportedFile as e:
        log.warning("import_file rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("import_file extract error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"could not read file: {e}")
    try:
        parsed = pipeline.parse_raw_cv(text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CV parse failed: {e}")
    bc = _get_or_create(db, user)
    bc.data = parsed.model_dump()
    db.commit()
    audit.record("cv_import_file", user_id=user.id, meta={"exp": len(parsed.experience), "edu": len(parsed.education)})
    return parsed


@router.post("/build", response_model=schemas.CVData)
def build_cv(payload: schemas.BuildIn, db: Session = Depends(get_db),
             user: models.User = Depends(get_current_user)):
    """Build a polished base CV from questionnaire answers."""
    log.info("build_cv user=%s fields=%d", user.id, len(payload.answers))
    try:
        built = pipeline.build_from_answers(payload.answers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CV build failed: {e}")
    bc = _get_or_create(db, user)
    bc.data = built.model_dump()
    db.commit()
    audit.record("cv_build", user_id=user.id, meta={"exp": len(built.experience)})
    return built


@router.put("", response_model=schemas.CVData)
def replace_base_cv(payload: CVData, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Direct structured edit (manual corrections / full editor save)."""
    log.info("replace_base_cv user=%s", user.id)
    bc = _get_or_create(db, user)
    bc.data = payload.model_dump()
    db.commit()
    audit.record("cv_edit", user_id=user.id)
    return payload


@router.post("/qualification", response_model=schemas.CVData)
def add_qualification(payload: schemas.AddQualificationIn, db: Session = Depends(get_db),
                      user: models.User = Depends(get_current_user)):
    """Dump new qualification/experience as text -> merged into base CV."""
    log.info("add_qualification user=%s chars=%d", user.id, len(payload.text))
    bc = _get_or_create(db, user)
    current = CVData.model_validate(bc.data)
    try:
        updated = pipeline.merge_qualification(current, payload.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Merge failed: {e}")
    bc.data = updated.model_dump()
    db.commit()
    audit.record("cv_qualification", user_id=user.id)
    return updated
