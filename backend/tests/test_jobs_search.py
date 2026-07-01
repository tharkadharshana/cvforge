"""Job aggregator search endpoint (Feature 3a)."""
from conftest import auth_headers
from app.jobs import aggregator


def test_search_returns_disabled_when_unconfigured(client, monkeypatch):
    # CI has no Adzuna keys configured
    monkeypatch.setattr(aggregator, "enabled", lambda: False)
    H = auth_headers(client, email="jobs1@test.com")
    r = client.get("/jobs/search?q=python", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["results"] == []


def test_search_returns_normalized_results(client, monkeypatch):
    monkeypatch.setattr(aggregator, "enabled", lambda: True)
    monkeypatch.setattr(aggregator, "search", lambda q, loc, page: [
        {"id": "1", "title": "Backend Engineer", "company": "Acme", "location": "Remote",
         "description": "Build APIs", "url": "https://x/1", "source": "adzuna"},
    ])
    H = auth_headers(client, email="jobs2@test.com")
    r = client.get("/jobs/search?q=backend&location=remote", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["results"][0]["title"] == "Backend Engineer"
    assert body["results"][0]["url"] == "https://x/1"


def test_search_surfaces_aggregator_errors(client, monkeypatch):
    def boom(q, loc, page):
        raise aggregator.AggregatorError("Daily job-search limit reached. Try again tomorrow.")
    monkeypatch.setattr(aggregator, "enabled", lambda: True)
    monkeypatch.setattr(aggregator, "search", boom)
    H = auth_headers(client, email="jobs3@test.com")
    r = client.get("/jobs/search?q=python", headers=H)
    assert r.status_code == 502
    assert "limit reached" in r.json()["detail"]


def test_search_requires_auth(client):
    assert client.get("/jobs/search?q=python").status_code == 401


def test_normalize_cleans_html(monkeypatch):
    item = {"id": 5, "title": "Dev", "company": {"display_name": "Acme"},
            "location": {"display_name": "NYC"}, "description": "<p>Hello&nbsp;world</p>",
            "redirect_url": "https://x/5"}
    out = aggregator._normalize(item)
    assert out["id"] == "5"
    assert out["company"] == "Acme"
    assert out["location"] == "NYC"
    assert out["description"] == "Hello world"
