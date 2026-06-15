import pytest
from conftest import auth_headers
from app.routers import generate as generate_router

BASE_CV = {
    "contact": {"full_name": "Jane Doe", "email": "j@test.com"}, "summary": "x", "skills": {},
    "experience": [], "projects": [], "education": [], "certifications": [], "awards": [], "languages": [],
}

TAILORED_CV = {
    "contact": {"full_name": "Jane Doe", "email": "j@test.com"},
    "summary": "Tailored summary",
    "skills": {"Languages": ["Python"]},
    "experience": [], "projects": [], "education": [], "certifications": [], "awards": [], "languages": [],
}

JD = "Backend engineer FastAPI Postgres SaaS role needed here now."


class FakeDrafter:
    def complete_json(self, system, user, pro=False):
        return dict(TAILORED_CV)

    def complete(self, system, user, json_mode=False, pro=False):
        return "Dear hiring team, I'm excited about this role."


class FakeCritic:
    def complete_json(self, system, user, pro=False):
        return {"ats_score": 88, "keyword_matches": ["Python"], "missing_keywords": [],
                "human_tone_notes": [], "suggestions": []}


class FailingDrafter:
    def complete_json(self, system, user, pro=False):
        raise RuntimeError("provider overloaded")

    def complete(self, system, user, json_mode=False, pro=False):
        raise RuntimeError("provider overloaded")


def _mock_llm(monkeypatch, drafter=FakeDrafter, critic=FakeCritic):
    monkeypatch.setattr(generate_router, "drafter", lambda: drafter())
    monkeypatch.setattr(generate_router, "critic", lambda: critic())


def _with_base_cv(client, headers):
    assert client.put("/cv", headers=headers, json=BASE_CV).status_code == 200


def test_start_is_instant_and_no_llm_call(client):
    H = auth_headers(client, email="start@test.com")
    _with_base_cv(client, H)
    r = client.post("/generate/start", headers=H,
                    json={"job_description": JD, "company": "Acme", "job_title": "Backend Engineer"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert isinstance(body["job_id"], int)


def test_start_blocked_without_base_cv(client):
    H = auth_headers(client, email="nocv@test.com")
    r = client.post("/generate/start", headers=H, json={"job_description": JD})
    assert r.status_code == 400


def test_start_blocked_when_out_of_credits(client):
    H = auth_headers(client, email="broke2@test.com")
    _with_base_cv(client, H)
    admin = auth_headers(client, email="admin@test.com")
    uid = client.get("/admin/users?query=broke2", headers=admin).json()[0]["id"]
    client.post(f"/admin/users/{uid}/credits", headers=admin, json={"delta": -2, "reason": "drain"})
    r = client.post("/generate/start", headers=H, json={"job_description": JD})
    assert r.status_code == 402


def test_full_flow_charges_credit_exactly_once(client, monkeypatch):
    _mock_llm(monkeypatch)
    H = auth_headers(client, email="flow@test.com")
    _with_base_cv(client, H)
    credits_before = client.get("/billing/summary", headers=H).json()["credits"]

    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]

    r = client.post(f"/generate/{job_id}/tailor", headers=H)
    assert r.status_code == 200
    assert r.json()["status"] == "tailored"
    assert r.json()["tailored_cv"]["summary"] == "Tailored summary"

    r = client.post(f"/generate/{job_id}/cover", headers=H)
    assert r.status_code == 200
    assert r.json()["status"] == "covered"
    assert "excited" in r.json()["cover_letter"]

    # credit not yet charged before critique
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits_before

    r = client.post(f"/generate/{job_id}/critique", headers=H)
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["ats_score"] == 88

    credits_after = client.get("/billing/summary", headers=H).json()["credits"]
    assert credits_after == credits_before - 1

    # idempotent retry: re-running critique does not charge again
    r = client.post(f"/generate/{job_id}/critique", headers=H)
    assert r.status_code == 200
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits_after

    # completed job shows up in history
    apps = client.get("/applications", headers=H).json()
    assert any(a["id"] == job_id for a in apps)


def test_get_job_resume_after_tailor(client, monkeypatch):
    _mock_llm(monkeypatch)
    H = auth_headers(client, email="resume@test.com")
    _with_base_cv(client, H)
    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]
    client.post(f"/generate/{job_id}/tailor", headers=H)

    r = client.get(f"/generate/{job_id}", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "tailored"
    assert body["tailored_cv"]["summary"] == "Tailored summary"
    assert body["cover_letter"] is None
    assert body["critique"] is None

    # not yet complete -> not in history
    assert all(a["id"] != job_id for a in client.get("/applications", headers=H).json())


def test_failed_step_does_not_charge_and_can_be_retried(client, monkeypatch):
    H = auth_headers(client, email="fail@test.com")
    _with_base_cv(client, H)
    credits_before = client.get("/billing/summary", headers=H).json()["credits"]
    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]

    _mock_llm(monkeypatch, drafter=FailingDrafter)
    r = client.post(f"/generate/{job_id}/tailor", headers=H)
    assert r.status_code == 502

    body = client.get(f"/generate/{job_id}", headers=H).json()
    assert body["status"] == "failed"
    assert "provider overloaded" in body["error"]
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits_before

    # retry succeeds once the provider works again
    _mock_llm(monkeypatch)
    r = client.post(f"/generate/{job_id}/tailor", headers=H)
    assert r.status_code == 200
    assert r.json()["status"] == "tailored"


def test_cover_requires_tailored_first(client, monkeypatch):
    _mock_llm(monkeypatch)
    H = auth_headers(client, email="order@test.com")
    _with_base_cv(client, H)
    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]
    r = client.post(f"/generate/{job_id}/cover", headers=H)
    assert r.status_code == 409
    r = client.post(f"/generate/{job_id}/critique", headers=H)
    assert r.status_code == 409
