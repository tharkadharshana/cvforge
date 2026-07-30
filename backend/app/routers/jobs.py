from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import schemas, models, billing
from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..jobs.fetch import fetch_job_text, FetchError
from ..jobs import aggregator, linkedin, gemini_search
from ..logging_config import get_logger
from ..errors import opaque_502

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
        raise opaque_502(log, "Job board search failed", e)
    return schemas.JobSearchOut(results=results, page=page, enabled=True)


# ---------------------------------------------------------------------------
# LinkedIn job discovery (public jobs-guest pages, no API key). Off by default
# — see docs/LEGAL_NOTES.md before enabling. Everything below 404s cleanly
# when disabled rather than silently no-op'ing.
# ---------------------------------------------------------------------------

def _require_linkedin_enabled():
    if not settings.linkedin_search_enabled:
        raise HTTPException(status_code=404, detail="This job search source is not enabled on this server")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _cache_and_record(db: Session, user: models.User, cache_model, result_model, out_cls,
                      jobs: list[dict], cache_fields: list[str], search_keywords: str) -> list:
    """Upsert each job into its cache table and this user's per-job save/dismiss
    row, returning the *Out schema list for the response. Shared by every job
    search source's search endpoint -- only the models/output class differ."""
    out = []
    for j in jobs:
        cached = db.get(cache_model, j["job_id"])
        if not cached:
            cached = cache_model(job_id=j["job_id"])
            db.add(cached)
        for f in cache_fields:
            setattr(cached, f, j[f])
        # job_id columns here are bare ForeignKeys with no ORM relationship(),
        # so the unit-of-work has no dependency info to order the insert --
        # flush explicitly so the cache row exists before the result row.
        db.flush()

        row = db.query(result_model).filter(
            result_model.user_id == user.id, result_model.job_id == j["job_id"]
        ).first()
        if not row:
            row = result_model(user_id=user.id, job_id=j["job_id"], search_keywords=search_keywords,
                               saved=False, dismissed=False)
            db.add(row)
        out.append(out_cls(
            job_id=j["job_id"], title=j["title"], company=j["company"], location=j["location"],
            posted_at=j["posted_at"], url=j["url"], saved=row.saved, dismissed=row.dismissed,
        ))
    return out


def _check_and_bump_quota(db: Session, user: models.User, usage_model, limit: int) -> int | None:
    """Returns searches remaining today, or None if unlimited (paid plan).
    Raises 429 if the free daily limit is already used up."""
    if billing.is_paid(user):
        return None
    today = _today()
    row = db.query(usage_model).filter(
        usage_model.user_id == user.id, usage_model.date == today
    ).first()
    if not row:
        row = usage_model(user_id=user.id, date=today, search_count=0)
        db.add(row)
    if row.search_count >= limit:
        raise HTTPException(status_code=429, detail=f"Daily search limit reached ({limit}/day on the free plan).")
    row.search_count += 1
    db.commit()
    return limit - row.search_count


@router.get("/listings/search", response_model=schemas.LinkedInSearchOut)
def linkedin_search(q: str = Query(..., min_length=2), location: str = "", start: int = 0,
                    time_filter: str = "week", experience: str = "",
                    db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    remaining = _check_and_bump_quota(db, user, models.JobSearchUsage, settings.linkedin_free_daily_searches)

    tpr = linkedin.TIME_FILTERS.get(time_filter, "")
    exp = linkedin.EXPERIENCE_LEVELS.get(experience, "")
    try:
        results = linkedin.search_jobs(q.strip(), location.strip(), start=start, time_filter=tpr, experience=exp)
    except linkedin.LinkedInError as e:
        raise opaque_502(log, "Web listings search failed", e)

    limit = settings.linkedin_paid_results_per_search if billing.is_paid(user) else settings.linkedin_free_results_per_search
    out = _cache_and_record(db, user, models.LinkedInJobCache, models.JobSearchResult, schemas.LinkedInJobOut,
                            results[:limit], ["title", "company", "location", "posted_at", "url"], q.strip())
    db.commit()
    return schemas.LinkedInSearchOut(jobs=out, searches_remaining_today=remaining)


@router.get("/listings/preferences", response_model=schemas.LinkedInPreferencesOut)
def get_linkedin_preferences(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    pref = db.query(models.JobSearchPreference).filter(models.JobSearchPreference.user_id == user.id).first()
    if not pref:
        return schemas.LinkedInPreferencesOut()
    return schemas.LinkedInPreferencesOut(
        keywords=pref.keywords, location=pref.location,
        experience_level=pref.experience_level, time_filter=pref.time_filter,
    )


@router.put("/listings/preferences", response_model=schemas.LinkedInPreferencesOut)
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


@router.get("/listings/{job_id}", response_model=schemas.LinkedInJobDetailOut)
def get_linkedin_job(job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_linkedin_enabled()
    cached = db.get(models.LinkedInJobCache, job_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Job not found (search for it first)")

    if not cached.description:
        try:
            detail = linkedin.get_job_detail(job_id)
        except linkedin.LinkedInError as e:
            raise opaque_502(log, "Could not load job details", e)
        cached.description = detail["description"]
        cached.description_hash = detail["description_hash"]
        cached.criteria = detail["criteria"]
        db.commit()

    return schemas.LinkedInJobDetailOut(
        job_id=cached.job_id, title=cached.title, company=cached.company, location=cached.location,
        url=cached.url, description=cached.description, criteria=cached.criteria or {},
    )


@router.patch("/listings/{job_id}/action")
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


# ---------------------------------------------------------------------------
# Gemini job discovery (google_search grounding tool). Auto-enabled whenever a
# Gemini key is configured -- legitimate use of Google's own search API, no
# ToS risk like the LinkedIn scraper, so no opt-in flag / 404 gate here.
# Kept on its own quota counter and cache table, independent from LinkedIn's.
# ---------------------------------------------------------------------------

@router.get("/gemini/search", response_model=schemas.GeminiSearchOut)
def gemini_job_search(q: str = Query(..., min_length=2), location: str = "",
                      db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if not gemini_search.enabled():
        return schemas.GeminiSearchOut(jobs=[], searches_remaining_today=None, enabled=False)
    remaining = _check_and_bump_quota(db, user, models.GeminiSearchUsage, settings.gemini_free_daily_searches)

    limit = settings.gemini_paid_results_per_search if billing.is_paid(user) else settings.gemini_free_results_per_search
    try:
        results = gemini_search.search_jobs(q.strip(), location.strip(), limit=limit)
    except gemini_search.GeminiSearchError as e:
        raise opaque_502(log, "AI search failed", e)

    out = _cache_and_record(db, user, models.GeminiJobCache, models.GeminiSearchResult, schemas.GeminiJobOut,
                            results, ["title", "company", "location", "posted_at", "url", "description"], q.strip())
    db.commit()
    return schemas.GeminiSearchOut(jobs=out, searches_remaining_today=remaining, enabled=True)


@router.get("/gemini/{job_id}", response_model=schemas.GeminiJobDetailOut)
def get_gemini_job(job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    cached = db.get(models.GeminiJobCache, job_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Job not found (search for it first)")
    return schemas.GeminiJobDetailOut(
        job_id=cached.job_id, title=cached.title, company=cached.company,
        location=cached.location, url=cached.url, description=cached.description,
    )


@router.patch("/gemini/{job_id}/action")
def patch_gemini_job_action(job_id: str, payload: schemas.GeminiActionIn, db: Session = Depends(get_db),
                            user: models.User = Depends(get_current_user)):
    row = db.query(models.GeminiSearchResult).filter(
        models.GeminiSearchResult.user_id == user.id, models.GeminiSearchResult.job_id == job_id
    ).first()
    if not row:
        if not db.get(models.GeminiJobCache, job_id):
            raise HTTPException(status_code=404, detail="Job not found (search for it first)")
        row = models.GeminiSearchResult(user_id=user.id, job_id=job_id, saved=False, dismissed=False)
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
