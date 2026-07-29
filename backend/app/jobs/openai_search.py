"""Fallback job search engine using OpenAI's `web_search` tool (Responses API).
Only used by gemini_search.py when the Gemini grounding call fails -- see
that module for the primary path and the reasoning for the fallback.
"""
from __future__ import annotations
from datetime import datetime, timezone
from ..config import settings
from ..llm.base import call_with_key_rotation
from ..logging_config import get_logger
from .search_util import extract_json_array, normalize_items

log = get_logger("openai_search")

_clients: dict[str, object] = {}


class OpenAISearchError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.openai_api_keys_list)


def _client_for(key: str):
    client = _clients.get(key)
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=key, timeout=settings.llm_timeout_s)
        _clients[key] = client
    return client


_PROMPT = """Search the web for current job listings matching the query below and \
return ONLY a JSON array (no prose, no markdown fences) of up to {limit} objects, \
each shaped exactly as:
{{"title": "", "company": "", "location": "", "posted_at": "", "url": "", "description": ""}}

- "url" must be the direct link to the original job posting (not a search result page).
- "posted_at" must be an ISO 8601 date (YYYY-MM-DD) if you can determine or reasonably
  estimate it, else "". Today's date is {today}.
- "description" should be a real summary of the role (2-6 sentences).
- Omit listings you are not reasonably confident are real, current job postings.
- If you find nothing relevant, return [].

Query: {query}
Location: {location}
"""


def search_jobs(query: str, location: str = "", limit: int = 10) -> list[dict]:
    """Return normalized job listings via OpenAI's web_search tool.
    Raises OpenAISearchError on problems."""
    today = datetime.now(timezone.utc).date().isoformat()
    prompt = _PROMPT.format(limit=max(1, min(limit, 20)), query=query, location=location or "any", today=today)

    def attempt(key: str) -> str:
        resp = _client_for(key).responses.create(
            model=settings.openai_search_model,
            tools=[{"type": "web_search"}],
            input=prompt,
        )
        return resp.output_text

    log.info("openai job search q=%r loc=%r", query[:60], (location or "")[:40])
    try:
        raw = call_with_key_rotation("openai_search", settings.openai_api_keys_list, attempt)
    except Exception as e:
        log.warning("openai job search failed: %s", e)
        raise OpenAISearchError(f"Job search request failed: {e}")

    try:
        items = extract_json_array(raw)
    except ValueError as e:
        raise OpenAISearchError(str(e))

    jobs = normalize_items(items)
    log.info("openai job search: %d jobs parsed", len(jobs))
    return jobs
