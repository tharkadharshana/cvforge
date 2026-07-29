"""LinkedIn job discovery via the public, unauthenticated `jobs-guest` pages —
the same HTML a logged-out browser gets. No API key, no OAuth.

Off by default (settings.linkedin_search_enabled) and must stay that way unless
explicitly turned on: this reads pages in a way that is against LinkedIn's
Terms of Service. See docs/LEGAL_NOTES.md before enabling in production.
"""
from __future__ import annotations
import hashlib
import re
import httpx
from bs4 import BeautifulSoup
from ..logging_config import get_logger

log = get_logger("linkedin")

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

TIME_FILTERS = {"any": "", "day": "r86400", "week": "r604800", "month": "r2592000"}
EXPERIENCE_LEVELS = {"any": "", "entry": "2", "mid_senior": "3", "senior": "4", "director": "5"}


class LinkedInError(Exception):
    pass


def _text(el, tag: str, cls: str) -> str:
    found = el.find(tag, class_=cls)
    return found.get_text(strip=True) if found else ""


def search_jobs(keywords: str, location: str = "", start: int = 0,
                time_filter: str = "", experience: str = "") -> list[dict]:
    """Return normalized job listings. Raises LinkedInError on problems."""
    params = {"keywords": keywords, "start": max(0, start)}
    if location:
        params["location"] = location
    if time_filter:
        params["f_TPR"] = time_filter
    if experience:
        params["f_E"] = experience

    log.info("linkedin search q=%r loc=%r start=%d", keywords[:60], location[:40], start)
    try:
        with httpx.Client(timeout=15.0, headers=HEADERS) as c:
            r = c.get(SEARCH_URL, params=params)
    except httpx.HTTPError as e:
        log.warning("linkedin search failed: %s", e)
        raise LinkedInError(f"Job search request failed: {e}")

    if r.status_code == 429:
        raise LinkedInError("Rate limited by LinkedIn. Try again later.")
    if r.status_code >= 400:
        log.warning("linkedin search %s: %s", r.status_code, r.text[:200])
        raise LinkedInError(f"Job search failed ({r.status_code}).")

    soup = BeautifulSoup(r.text, "lxml")
    jobs = []
    for card in soup.find_all("div", class_="base-card"):
        urn = card.get("data-entity-urn", "")
        job_id = urn.split(":")[-1] if urn else ""
        if not job_id:
            continue
        time_el = card.find("time")
        jobs.append({
            "job_id": job_id,
            "title": _text(card, "h3", "base-search-card__title"),
            "company": _text(card, "h4", "base-search-card__subtitle"),
            "location": _text(card, "span", "job-search-card__location"),
            "posted_at": time_el.get("datetime", "") if time_el else "",
            "url": f"https://www.linkedin.com/jobs/view/{job_id}",
        })
    log.info("linkedin search: %d jobs parsed", len(jobs))
    return jobs


def get_job_detail(job_id: str) -> dict:
    """Full description + criteria for one job. Raises LinkedInError on problems."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", job_id or ""):
        raise LinkedInError("Invalid job id")
    url = DETAIL_URL.format(job_id=job_id)
    try:
        with httpx.Client(timeout=15.0, headers=HEADERS) as c:
            r = c.get(url)
    except httpx.HTTPError as e:
        log.warning("linkedin detail failed job=%s: %s", job_id, e)
        raise LinkedInError(f"Could not load job details: {e}")

    if r.status_code == 429:
        raise LinkedInError("Rate limited by LinkedIn. Try again later.")
    if r.status_code >= 400:
        raise LinkedInError(f"Could not load job details ({r.status_code}).")

    soup = BeautifulSoup(r.text, "lxml")
    desc_el = soup.find("div", class_="show-more-less-html__markup")
    description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""

    criteria = {}
    for li in soup.find_all("li", class_="description__job-criteria-item"):
        label = _text(li, "h3", "description__job-criteria-subheader")
        value = _text(li, "span", "description__job-criteria-text")
        if label and value:
            criteria[label] = value

    if not description:
        raise LinkedInError("Could not read the job description (LinkedIn markup may have changed).")

    return {
        "job_id": job_id,
        "description": description,
        "criteria": criteria,
        "description_hash": hashlib.sha256(description.encode()).hexdigest(),
    }
