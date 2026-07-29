"""Gemini google_search-grounded job discovery (3rd job source), with an
OpenAI web_search fallback when Gemini's grounding call fails."""
import pytest
from conftest import auth_headers
from app.jobs import gemini_search, linkedin, openai_search, search_util


def test_search_returns_disabled_when_unconfigured(client, monkeypatch):
    monkeypatch.setattr(gemini_search, "enabled", lambda: False)
    H = auth_headers(client, email="gemini1@test.com")
    r = client.get("/jobs/gemini/search?q=python", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["jobs"] == []


def test_search_returns_normalized_results(client, monkeypatch):
    monkeypatch.setattr(gemini_search, "enabled", lambda: True)
    monkeypatch.setattr(gemini_search, "search_jobs", lambda q, loc, limit: [
        {"job_id": "abc123", "title": "Backend Engineer", "company": "Acme", "location": "Remote",
         "posted_at": "2 days ago", "url": "https://x/1", "description": "Build APIs"},
    ])
    H = auth_headers(client, email="gemini2@test.com")
    r = client.get("/jobs/gemini/search?q=backend&location=remote", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["jobs"][0]["title"] == "Backend Engineer"
    assert body["jobs"][0]["job_id"] == "abc123"

    # detail reads from the cache populated during search, no second Gemini call
    r2 = client.get("/jobs/gemini/abc123", headers=H)
    assert r2.status_code == 200
    assert r2.json()["description"] == "Build APIs"


def test_search_surfaces_gemini_errors(client, monkeypatch):
    def boom(q, loc, limit):
        raise gemini_search.GeminiSearchError("Job search request failed: boom")
    monkeypatch.setattr(gemini_search, "enabled", lambda: True)
    monkeypatch.setattr(gemini_search, "search_jobs", boom)
    H = auth_headers(client, email="gemini3@test.com")
    r = client.get("/jobs/gemini/search?q=python", headers=H)
    assert r.status_code == 502
    assert r.json()["detail"] == "AI search failed. Please try again."


def test_search_requires_auth(client):
    assert client.get("/jobs/gemini/search?q=python").status_code == 401


def test_detail_404_when_not_cached(client, monkeypatch):
    monkeypatch.setattr(gemini_search, "enabled", lambda: True)
    H = auth_headers(client, email="gemini4@test.com")
    assert client.get("/jobs/gemini/never-searched", headers=H).status_code == 404


def test_action_save_and_dismiss(client, monkeypatch):
    monkeypatch.setattr(gemini_search, "enabled", lambda: True)
    monkeypatch.setattr(gemini_search, "search_jobs", lambda q, loc, limit: [
        {"job_id": "job1", "title": "Dev", "company": "Acme", "location": "NYC",
         "posted_at": "", "url": "https://x/1", "description": "desc"},
    ])
    H = auth_headers(client, email="gemini5@test.com")
    client.get("/jobs/gemini/search?q=dev", headers=H)

    r = client.patch("/jobs/gemini/job1/action", json={"action": "save"}, headers=H)
    assert r.status_code == 200
    assert r.json()["saved"] is True

    r = client.patch("/jobs/gemini/job1/action", json={"action": "dismiss"}, headers=H)
    assert r.json()["dismissed"] is True


def test_quota_is_independent_from_linkedin(client, monkeypatch):
    """Gemini and LinkedIn searches must not share a daily counter."""
    monkeypatch.setattr(gemini_search, "enabled", lambda: True)
    monkeypatch.setattr(gemini_search, "search_jobs", lambda q, loc, limit: [])
    monkeypatch.setattr("app.config.settings.linkedin_search_enabled", True)
    monkeypatch.setattr(linkedin, "search_jobs", lambda *a, **kw: [])
    H = auth_headers(client, email="gemini6@test.com")

    from app.config import settings
    limit = settings.gemini_free_daily_searches

    for _ in range(limit):
        r = client.get("/jobs/gemini/search?q=dev", headers=H)
        assert r.status_code == 200
        # interleave a LinkedIn search -- must not consume the Gemini counter
        client.get("/jobs/listings/search?q=dev", headers=H)

    r = client.get("/jobs/gemini/search?q=dev", headers=H)
    assert r.status_code == 429


def test_extract_json_array_variants():
    assert search_util.extract_json_array('[{"a": 1}]') == [{"a": 1}]
    assert search_util.extract_json_array('```json\n[{"a": 1}]\n```') == [{"a": 1}]
    assert search_util.extract_json_array('Here are the results:\n[{"a": 1}]\nHope that helps!') == [{"a": 1}]
    assert search_util.extract_json_array('[]') == []


def test_extract_json_array_rejects_non_array():
    with pytest.raises(ValueError):
        search_util.extract_json_array('{"not": "an array"}')
    with pytest.raises(ValueError):
        search_util.extract_json_array('not json at all')


def test_falls_back_to_openai_when_gemini_fails(monkeypatch):
    """gemini_search.search_jobs() itself (not the router mock) should retry
    via OpenAI's web_search tool if the Gemini grounding call errors out."""
    monkeypatch.setattr("app.config.settings.gemini_api_key", "fake-gemini-key")
    monkeypatch.setattr(gemini_search, "_search_via_gemini",
                        lambda q, loc, limit: (_ for _ in ()).throw(RuntimeError("429 RESOURCE_EXHAUSTED")))
    monkeypatch.setattr(openai_search, "enabled", lambda: True)
    monkeypatch.setattr(openai_search, "search_jobs", lambda q, loc, limit: [
        {"job_id": "oa1", "title": "Fallback Job", "company": "Acme", "location": "Remote",
         "posted_at": "", "url": "https://x/1", "description": "via openai"},
    ])
    jobs = gemini_search.search_jobs("backend engineer")
    assert jobs[0]["title"] == "Fallback Job"


def test_raises_when_gemini_and_openai_both_fail(monkeypatch):
    monkeypatch.setattr("app.config.settings.gemini_api_key", "fake-gemini-key")
    monkeypatch.setattr(gemini_search, "_search_via_gemini",
                        lambda q, loc, limit: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(openai_search, "enabled", lambda: True)
    monkeypatch.setattr(openai_search, "search_jobs",
                        lambda q, loc, limit: (_ for _ in ()).throw(openai_search.OpenAISearchError("also boom")))
    with pytest.raises(gemini_search.GeminiSearchError, match="also boom"):
        gemini_search.search_jobs("backend engineer")


def test_enabled_true_when_only_openai_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.gemini_api_key", "")
    monkeypatch.setattr("app.config.settings.gemini_api_keys", "")
    monkeypatch.setattr(openai_search, "enabled", lambda: True)
    assert gemini_search.enabled() is True
