"""Legal job-search feed via the Adzuna aggregator API.

Adzuna aggregates listings from LinkedIn, Indeed and many boards and exposes them
through an official, terms-compliant REST API (free tier ~250 req/day). We use it so
users can search for roles inside the app and generate a tailored CV against a listing
without copy-pasting the description — instead of scraping LinkedIn, which its ToS
forbids. Applications are still made by the user on the original posting.
"""
from __future__ import annotations
import re
import httpx
from ..config import settings
from ..logging_config import get_logger

log = get_logger("jobagg")

_BASE = "https://api.adzuna.com/v1/api/jobs"


class AggregatorError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.adzuna_app_id and settings.adzuna_app_key)


def _clean(html_or_text: str) -> str:
    # Adzuna descriptions are short snippets, sometimes with stray tags/entities.
    t = re.sub(r"<[^>]+>", " ", html_or_text or "")
    t = re.sub(r"&nbsp;", " ", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def _normalize(item: dict) -> dict:
    return {
        "id": str(item.get("id", "")),
        "title": item.get("title", "") or "",
        "company": (item.get("company") or {}).get("display_name", "") or "",
        "location": (item.get("location") or {}).get("display_name", "") or "",
        "description": _clean(item.get("description", "")),
        "url": item.get("redirect_url", "") or "",
        "source": "adzuna",
    }


def search(query: str, location: str = "", page: int = 1, per_page: int = 20) -> list[dict]:
    """Return a list of normalized job listings. Raises AggregatorError on problems."""
    if not enabled():
        raise AggregatorError("Job search isn't configured. Add ADZUNA_APP_ID / ADZUNA_APP_KEY.")

    page = max(1, min(page, 50))
    country = settings.adzuna_country or "us"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": max(1, min(per_page, 50)),
        "what": query,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    url = f"{_BASE}/{country}/search/{page}"
    log.info("job search q=%r loc=%r page=%d", query[:60], location[:40], page)
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(url, params=params)
    except httpx.HTTPError as e:
        log.warning("adzuna request failed: %s", e)
        raise AggregatorError(f"Job search request failed: {e}")

    if r.status_code == 429:
        raise AggregatorError("Daily job-search limit reached. Try again tomorrow.")
    if r.status_code >= 400:
        log.warning("adzuna %s: %s", r.status_code, r.text[:200])
        raise AggregatorError(f"Job search failed ({r.status_code}).")

    try:
        results = r.json().get("results", [])
    except Exception as e:
        raise AggregatorError(f"Bad job-search response: {e}")
    return [_normalize(it) for it in results]
