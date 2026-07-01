from fastapi import APIRouter, Depends, HTTPException, Query
from .. import schemas, models
from ..auth import get_current_user
from ..jobs.fetch import fetch_job_text, FetchError
from ..jobs import aggregator
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


@router.get("/search", response_model=schemas.JobSearchOut)
def search_jobs(q: str = Query(..., min_length=2), location: str = "", page: int = 1,
                user: models.User = Depends(get_current_user)):
    """Search a legal job aggregator (Adzuna) so the user can generate a CV against a
    listing without pasting the description. Returns enabled=False if not configured."""
    if not aggregator.enabled():
        return schemas.JobSearchOut(results=[], page=page, enabled=False)
    try:
        results = aggregator.search(q.strip(), location.strip(), page)
    except aggregator.AggregatorError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return schemas.JobSearchOut(results=results, page=page, enabled=True)
