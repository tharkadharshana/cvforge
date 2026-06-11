from fastapi import APIRouter, Depends, HTTPException
from .. import schemas, models
from ..auth import get_current_user
from ..jobs.fetch import fetch_job_text, FetchError
from ..logging_config import get_logger

router = APIRouter(prefix="/jobs", tags=["jobs"])
log = get_logger("jobs")


@router.post("/fetch-url", response_model=schemas.FetchUrlOut)
def fetch_url(payload: schemas.FetchUrlIn, user: models.User = Depends(get_current_user)):
    log.info("fetch-url user=%s", user.id)
    try:
        title, text = fetch_job_text(payload.url.strip())
    except FetchError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # cap to keep prompts sane
    return schemas.FetchUrlOut(title=title, text=text[:20000])
