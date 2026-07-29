from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import schemas, models, billing
from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..jobs.fetch import fetch_job_text, FetchError
from ..jobs import aggregator, linkedin
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


# ---------------------------------------------------------------------------
# LinkedIn job discovery (public jobs-guest pages, no API key). Off by default
# — see docs/LEGAL_NOTES.md before enabling. Everything below 404s cleanly
# when disabled rather than silently no-op'ing.
# ---------------------------------------------------------------------------

def _require_linkedin_enabled():
    if not settings.linkedin_search_enabled:
        raise HTTPException(status_code=404, detail="LinkedIn job search is not enabled on this server")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _check_and_bump_search_quota(db: Session, user: models.User) -> int | None:
    """Returns searches remaining today, or None if unlimited (paid plan).
    Raises 429 if the free daily limit is already used up."""
    if billing.is_paid(user):
        return None
    today = _today()
    row = db.query(models.JobSearchUsage).filter(
        models.JobSearchUsage.user_id == user.id, models.JobSearchUsage.date == today
    ).first()
    if not row:
        row = models.JobSearchUsage(user_id=user.id, date=today, search_count=0)
        db.add(row)
    limit = settings.linkedin_free_daily_searches
    if row.search_count >= limit:
        raise HTTPException(status_code=429, detail=f"Daily search limit reached ({limit}/day on the free plan).")
    row.search_count += 1
    db.commit()
    return limit - row.search_count


@router.get("/linkedin/search", response_model=schemas.LinkedInSearchOut)
def linkedin_search(q: str = Query(..., min_length=2), location: str = "", start: int = 0,
                    time_filter: str = "week", experience: str = "",
                    db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    remaining = _check_and_bump_search_quota(db, user)

    tpr = linkedin.TIME_FILTERS.get(time_filter, "")
    exp = linkedin.EXPERIENCE_LEVELS.get(experience, "")
    try:
        results = linkedin.search_jobs(q.strip(), location.strip(), start=start, time_filter=tpr, experience=exp)
    except linkedin.LinkedInError as e:
        raise HTTPException(status_code=502, detail=str(e))

    limit = settings.linkedin_paid_results_per_search if billing.is_paid(user) else settings.linkedin_free_results_per_search
    results = results[:limit]

    out = []
    for j in results:
        cached = db.get(models.LinkedInJobCache, j["job_id"])
        if not cached:
            cached = models.LinkedInJobCache(job_id=j["job_id"])
            db.add(cached)
        cached.title, cached.company, cached.location, cached.posted_at, cached.url = (
            j["title"], j["company"], j["location"], j["posted_at"], j["url"]
        )

        row = db.query(models.JobSearchResult).filter(
            models.JobSearchResult.user_id == user.id, models.JobSearchResult.job_id == j["job_id"]
        ).first()
        if not row:
            row = models.JobSearchResult(user_id=user.id, job_id=j["job_id"], search_keywords=q.strip(),
                                         saved=False, dismissed=False)
            db.add(row)
        out.append(schemas.LinkedInJobOut(
            job_id=j["job_id"], title=j["title"], company=j["company"], location=j["location"],
            posted_at=j["posted_at"], url=j["url"], saved=row.saved, dismissed=row.dismissed,
        ))
    db.commit()
    return schemas.LinkedInSearchOut(jobs=out, searches_remaining_today=remaining)


@router.get("/linkedin/preferences", response_model=schemas.LinkedInPreferencesOut)
def get_linkedin_preferences(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    pref = db.query(models.JobSearchPreference).filter(models.JobSearchPreference.user_id == user.id).first()
    if not pref:
        return schemas.LinkedInPreferencesOut()
    return schemas.LinkedInPreferencesOut(
        keywords=pref.keywords, location=pref.location,
        experience_level=pref.experience_level, time_filter=pref.time_filter,
    )


@router.put("/linkedin/preferences", response_model=schemas.LinkedInPreferencesOut)
def put_linkedin_preferences(payload: schemas.LinkedInPreferencesIn, db: Session = Depends(get_db),
                             user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    pref = db.query(models.JobSearchPreference).filter(models.JobSearchPreference.user_id == user.id).first()
    if not pref:
        pref = models.JobSearchPreference(user_id=user.id)
        db.add(pref)
    pref.keywords = payload.keywords
    pref.location = payload.location
    pref.experience_level = payload.experience_level
    pref.time_filter = payload.time_filter
    db.commit()
    return payload


@router.get("/linkedin/{job_id}", response_model=schemas.LinkedInJobDetailOut)
def get_linkedin_job(job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    cached = db.get(models.LinkedInJobCache, job_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Job not found (search for it first)")

    if not cached.description:
        try:
            detail = linkedin.get_job_detail(job_id)
        except linkedin.LinkedInError as e:
            raise HTTPException(status_code=502, detail=str(e))
        cached.description = detail["description"]
        cached.description_hash = detail["description_hash"]
        cached.criteria = detail["criteria"]
        db.commit()

    return schemas.LinkedInJobDetailOut(
        job_id=cached.job_id, title=cached.title, company=cached.company, location=cached.location,
        url=cached.url, description=cached.description, criteria=cached.criteria or {},
    )


@router.patch("/linkedin/{job_id}/action")
def patch_linkedin_job_action(job_id: str, payload: schemas.LinkedInActionIn, db: Session = Depends(get_db),
                              user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    row = db.query(models.JobSearchResult).filter(
        models.JobSearchResult.user_id == user.id, models.JobSearchResult.job_id == job_id
    ).first()
    if not row:
        if not db.get(models.LinkedInJobCache, job_id):
            raise HTTPException(status_code=404, detail="Job not found (search for it first)")
        row = models.JobSearchResult(user_id=user.id, job_id=job_id, saved=False, dismissed=False)
        db.add(row)
    if payload.action == "save":
        row.saved = True
    elif payload.action == "unsave":
        row.saved = False
    elif payload.action == "dismiss":
        row.dismissed = True
    elif payload.action == "undismiss":
        row.dismissed = False
    db.commit()
    return {"job_id": job_id, "saved": row.saved, "dismissed": row.dismissed}
