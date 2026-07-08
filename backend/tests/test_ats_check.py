"""Public ATS checker: free 2/day/IP, paid users get fixes + no limit."""
from conftest import auth_headers
from app.database import SessionLocal
from app import models
from app.routers import ats as ats_router

CV_TEXT = (
    "Jane Doe\njane@test.com | +1 555 0100 | Berlin\n\n"
    "Experience\nBackend Engineer, Acme Corp, 2020-2024\n- Built FastAPI services on Postgres\n\n"
    "Education\nBSc Computer Science, TU Berlin, 2016-2020\n"
)

FAKE_REPORT = {
    "ats_score": 78, "parse_rate": 90,
    "categories": {"sections": 80, "ats_essentials": 75, "hr_red_flags": 60,
                   "discrimination": 90, "seniority": 70, "tailoring": None},
    "issues": [
        {"category": "hr_red_flags", "severity": "high", "title": "Bullets lack metrics",
         "fix": "Quantify each bullet with impact numbers."},
        {"category": "sections", "severity": "low", "title": "No summary section",
         "fix": "Add a 2-3 line professional summary at the top."},
    ],
}


class FakeCritic:
    def complete_json(self, system, user, pro=False):
        return dict(FAKE_REPORT)


def _mock_llm(monkeypatch):
    monkeypatch.setattr(ats_router, "critic", lambda: FakeCritic())


def _make_paid(email):
    db = SessionLocal()
    try:
        db.query(models.User).filter(models.User.email == email).update({"plan": "pro"})
        db.commit()
    finally:
        db.close()


def test_anonymous_check_gated_and_rate_limited(client, monkeypatch):
    _mock_llm(monkeypatch)
    r = client.post("/ats/check", data={"raw_text": CV_TEXT})
    assert r.status_code == 200
    body = r.json()
    assert body["ats_score"] == 78
    assert body["parse_rate"] == 90
    assert body["categories"]["sections"] == 80
    assert body["detailed"] is False
    assert body["checks_left"] == 1
    # free tier never sees the fix instructions
    assert all("fix" not in i for i in body["issues"])
    assert body["issues"][0]["title"] == "Bullets lack metrics"

    assert client.post("/ats/check", data={"raw_text": CV_TEXT}).json()["checks_left"] == 0
    r3 = client.post("/ats/check", data={"raw_text": CV_TEXT})
    assert r3.status_code == 429


def test_too_short_input_rejected_and_not_counted(client, monkeypatch):
    _mock_llm(monkeypatch)
    assert client.post("/ats/check", data={"raw_text": "hi"}).status_code == 400
    # rejected attempts don't burn the quota
    assert client.post("/ats/check", data={"raw_text": CV_TEXT}).json()["checks_left"] == 1


def test_paid_user_gets_fixes_and_no_limit(client, monkeypatch):
    _mock_llm(monkeypatch)
    H = auth_headers(client, email="paid@test.com")
    _make_paid("paid@test.com")
    for _ in range(3):  # beyond the free cap
        r = client.post("/ats/check", data={"raw_text": CV_TEXT}, headers=H)
        assert r.status_code == 200
    body = r.json()
    assert body["detailed"] is True
    assert body["checks_left"] is None
    assert body["issues"][0]["fix"].startswith("Quantify")


def test_spoofed_forwarded_for_cannot_reset_quota(client, monkeypatch):
    """Only the last XFF entry (appended by the trusted proxy) counts; the
    client-controlled first entries must not mint fresh rate-limit buckets."""
    _mock_llm(monkeypatch)
    for i in range(2):
        r = client.post("/ats/check", data={"raw_text": CV_TEXT},
                        headers={"x-forwarded-for": f"fake-{i}.example, 9.9.9.9"})
        assert r.status_code == 200
    r = client.post("/ats/check", data={"raw_text": CV_TEXT},
                    headers={"x-forwarded-for": "fake-99.example, 9.9.9.9"})
    assert r.status_code == 429


def test_free_logged_in_user_still_limited(client, monkeypatch):
    _mock_llm(monkeypatch)
    H = auth_headers(client, email="free@test.com")  # trial plan, not paid
    r = client.post("/ats/check", data={"raw_text": CV_TEXT}, headers=H)
    assert r.status_code == 200
    assert r.json()["detailed"] is False
