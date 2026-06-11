from __future__ import annotations
import re
import httpx
from urllib.parse import urlparse
from ..logging_config import get_logger

log = get_logger("jobfetch")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class FetchError(Exception):
    pass


def fetch_job_text(url: str) -> tuple[str, str]:
    """Return (title, text). Raises FetchError on problems."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise FetchError("Enter a valid http(s) URL")
    log.info("fetch url host=%s", p.netloc)
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": UA}) as c:
            r = c.get(url)
            r.raise_for_status()
            html = r.text
    except httpx.HTTPError as e:
        log.warning("fetch failed: %s", e)
        raise FetchError(f"Could not load the page ({e}). Paste the text instead.")

    title, text = _extract(html)
    log.info("fetch extracted title=%r chars=%d", title[:60], len(text))
    if len(text) < 120:
        raise FetchError(
            "Couldn't read the job text from that page (it may need login or load via JavaScript, "
            "common with LinkedIn). Open the posting, copy the description, and paste it."
        )
    return title, text


def _extract(html: str) -> tuple[str, str]:
    # prefer trafilatura (best main-content extraction); fall back to crude strip
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
        if extracted.strip():
            return title, extracted.strip()
    except Exception as e:
        log.debug("trafilatura unavailable/failed: %s", e)
    return _crude_strip(html)


def _crude_strip(html: str) -> tuple[str, str]:
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
    html = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return title, text.strip()
