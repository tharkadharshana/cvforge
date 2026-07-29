"""Shared helpers for the LLM-backed job search sources (gemini_search.py,
openai_search.py) — normalizing a grounded-search text response into job dicts."""
from __future__ import annotations
import hashlib
import json


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def extract_json_array(raw: str) -> list:
    """Grounding/web-search tools aren't reliably combinable with strict JSON
    response modes, so the model is instructed via prompt text to emit raw JSON
    and we defensively extract it -- analog of llm/base.py::_safe_json but for
    a top-level array instead of an object. Raises ValueError on failure."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    s = s.strip().strip("`").strip()
    start, end = s.find("["), s.rfind("]")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"model did not return valid JSON: {e}")
    if not isinstance(data, list):
        raise ValueError("model response was not a JSON array")
    return data


def normalize_items(items: list) -> list[dict]:
    """Normalize raw {title, company, location, posted_at, url, description}
    dicts into the job shape used across both search sources, keyed by
    sha256(url). Skips items without a url."""
    jobs = []
    for it in items:
        if not isinstance(it, dict):
            continue
        url = (it.get("url") or "").strip()
        if not url:
            continue
        jobs.append({
            "job_id": url_hash(url),
            "title": (it.get("title") or "").strip()[:255],
            "company": (it.get("company") or "").strip()[:255],
            "location": (it.get("location") or "").strip()[:255],
            "posted_at": (it.get("posted_at") or "").strip()[:40],
            "url": url[:500],
            "description": (it.get("description") or "").strip(),
        })
    return jobs
