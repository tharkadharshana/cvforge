"""Job discovery via Gemini's native `google_search` grounding tool — a
legitimate use of Google's own search API (unlike app/jobs/linkedin.py's guest-HTML
scrape), so no opt-in flag / ToS gate is needed. Auto-enabled whenever a Gemini
key is configured (see enabled()).
"""
from __future__ import annotations
import hashlib
import json
from ..config import settings
from ..llm.base import call_with_key_rotation
from ..logging_config import get_logger

log = get_logger("gemini_search")

_clients: dict[str, object] = {}


class GeminiSearchError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.gemini_api_keys_list)


def _client_for(key: str):
    client = _clients.get(key)
    if client is None:
        from google import genai
        from google.genai import types
        client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_s * 1000)),
        )
        _clients[key] = client
    return client


_PROMPT = """You have Google Search grounding available. Search for current job \
listings matching the query below and return ONLY a JSON array (no prose, no \
markdown fences) of up to {limit} objects, each shaped exactly as:
{{"title": "", "company": "", "location": "", "posted_at": "", "url": "", "description": ""}}

- "url" must be the direct link to the original job posting (not a Google search result page).
- "description" should be a real summary of the role (2-6 sentences), not just the search snippet.
- Omit listings you are not reasonably confident are real, current job postings.
- If you find nothing relevant, return [].

Query: {query}
Location: {location}
"""


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _extract_json_array(raw: str) -> list:
    """Grounding + strict JSON response_mime_type aren't reliably combinable in the
    SDK, so the model is instructed via prompt text to emit raw JSON and we
    defensively extract it -- analog of llm/base.py::_safe_json but for a
    top-level array instead of an object."""
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
        raise GeminiSearchError(f"Gemini did not return valid JSON: {e}")
    if not isinstance(data, list):
        raise GeminiSearchError("Gemini response was not a JSON array")
    return data


def search_jobs(query: str, location: str = "", limit: int = 10) -> list[dict]:
    """Return normalized job listings via Gemini's google_search grounding tool.
    Raises GeminiSearchError on problems."""
    from google.genai import types

    prompt = _PROMPT.format(limit=max(1, min(limit, 20)), query=query, location=location or "any")
    cfg = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
        max_output_tokens=settings.llm_max_tokens,
    )

    def attempt(key: str) -> str:
        resp = _client_for(key).models.generate_content(
            model=settings.gemini_search_model, contents=prompt, config=cfg,
        )
        return resp.text

    log.info("gemini job search q=%r loc=%r", query[:60], (location or "")[:40])
    try:
        raw = call_with_key_rotation("gemini_search", settings.gemini_api_keys_list, attempt)
    except Exception as e:
        log.warning("gemini job search failed: %s", e)
        raise GeminiSearchError(f"Job search request failed: {e}")

    items = _extract_json_array(raw)
    jobs = []
    for it in items:
        if not isinstance(it, dict):
            continue
        url = (it.get("url") or "").strip()
        if not url:
            continue
        jobs.append({
            "job_id": _url_hash(url),
            "title": (it.get("title") or "").strip()[:255],
            "company": (it.get("company") or "").strip()[:255],
            "location": (it.get("location") or "").strip()[:255],
            "posted_at": (it.get("posted_at") or "").strip()[:40],
            "url": url[:500],
            "description": (it.get("description") or "").strip(),
        })
    log.info("gemini job search: %d jobs parsed", len(jobs))
    return jobs
