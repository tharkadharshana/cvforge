"""Job discovery via Gemini's native `google_search` grounding tool — a
legitimate use of Google's own search API (unlike app/jobs/linkedin.py's guest-HTML
scrape), so no opt-in flag / ToS gate is needed. Auto-enabled whenever a Gemini
or OpenAI key is configured (see enabled()).

Falls back to app/jobs/openai_search.py (OpenAI's web_search tool) whenever the
Gemini call fails -- in practice this has meant Gemini's google_search grounding
quota not being provisioned on the Google Cloud project, which is a billing
setting outside this app's control, not a transient error worth just retrying.
"""
from __future__ import annotations
from datetime import datetime, timezone
from ..config import settings
from ..llm.base import call_with_key_rotation
from ..logging_config import get_logger
from . import openai_search
from .search_util import extract_json_array, normalize_items

log = get_logger("gemini_search")

_clients: dict[str, object] = {}


class GeminiSearchError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.gemini_api_keys_list) or openai_search.enabled()


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
- "posted_at" must be an ISO 8601 date (YYYY-MM-DD) if you can determine or reasonably estimate
  it from the listing (e.g. "posted 3 days ago" relative to today), else "". This is used to sort
  results by recency alongside other job sources, so prefer a best-effort date over leaving it blank.
- "description" should be a real summary of the role (2-6 sentences), not just the search snippet.
- Omit listings you are not reasonably confident are real, current job postings.
- If you find nothing relevant, return [].
- Today's date is {today}.

Query: {query}
Location: {location}
"""


def _search_via_gemini(query: str, location: str, limit: int) -> list[dict]:
    from google.genai import types

    today = datetime.now(timezone.utc).date().isoformat()
    prompt = _PROMPT.format(limit=max(1, min(limit, 20)), query=query, location=location or "any", today=today)
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

    raw = call_with_key_rotation("gemini_search", settings.gemini_api_keys_list, attempt)
    items = extract_json_array(raw)
    return normalize_items(items)


def search_jobs(query: str, location: str = "", limit: int = 10) -> list[dict]:
    """Return normalized job listings, preferring Gemini's google_search grounding
    and falling back to OpenAI's web_search tool if Gemini fails or isn't
    configured. Raises GeminiSearchError only if neither is available/succeeds."""
    log.info("ai job search q=%r loc=%r", query[:60], (location or "")[:40])

    gemini_error: Exception | None = None
    if settings.gemini_api_keys_list:
        try:
            jobs = _search_via_gemini(query, location, limit)
            log.info("gemini job search: %d jobs parsed", len(jobs))
            return jobs
        except Exception as e:
            gemini_error = e
            log.warning("gemini job search failed, falling back to openai: %s", e)

    if openai_search.enabled():
        try:
            return openai_search.search_jobs(query, location, limit)
        except openai_search.OpenAISearchError as e:
            raise GeminiSearchError(str(e)) from e

    raise GeminiSearchError(f"Job search request failed: {gemini_error}" if gemini_error else "Job search is not configured.")
