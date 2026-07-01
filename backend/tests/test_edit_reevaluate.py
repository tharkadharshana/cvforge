"""Manual editing + ATS re-evaluate (Feature 2) and template selection (Feature 1)."""
from conftest import auth_headers
from app.routers import generate as generate_router

JD = "Backend engineer FastAPI Postgres SaaS role needed here now."

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


class FakeDrafter:
    def complete_json(self, system, user, pro=False):
        return dict(TAILORED_CV)

    def complete(self, system, user, json_mode=False, pro=False):
        return "Dear hiring team, I'm excited about this role."


class FakeCritic:
    def complete_json(self, system, user, pro=False):
        return {"ats_score": 88, "keyword_matches": ["Python"], "missing_keywords": [],
                "human_tone_notes": [], "suggestions": []}


def _mock_llm(monkeypatch):
    monkeypatch.setattr(generate_router, "drafter", lambda: FakeDrafter())
    monkeypatch.setattr(generate_router, "critic", lambda: FakeCritic())


def _with_base_cv(client, headers):
    assert client.put("/cv", headers=headers, json=BASE_CV).status_code == 200


def _completed_app(client, monkeypatch, email):
    """Run the full pipeline and return (headers, application_id)."""
    _mock_llm(monkeypatch)
    H = auth_headers(client, email=email)
    _with_base_cv(client, H)
    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]
    client.post(f"/generate/{job_id}/tailor", headers=H)
    client.post(f"/generate/{job_id}/cover", headers=H)
    client.post(f"/generate/{job_id}/critique", headers=H)
    return H, job_id


def test_edit_marks_score_stale_without_charging(client, monkeypatch):
    H, app_id = _completed_app(client, monkeypatch, "edit1@test.com")
    before = client.get(f"/applications/{app_id}", headers=H).json()
    assert before["ats_stale"] is False
    assert before["ats_score"] == 88
    credits = client.get("/billing/summary", headers=H).json()["credits"]

    edited = dict(TAILORED_CV)
    edited["summary"] = "Hand edited summary"
    r = client.patch(f"/applications/{app_id}", headers=H, json={"tailored_cv": edited})
    assert r.status_code == 200
    body = r.json()
    assert body["ats_stale"] is True
    assert body["tailored_cv"]["summary"] == "Hand edited summary"
    # editing is free
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits


def test_reevaluate_after_edit_is_free_and_clears_stale(client, monkeypatch):
    H, app_id = _completed_app(client, monkeypatch, "edit2@test.com")
    edited = dict(TAILORED_CV); edited["summary"] = "edited"
    client.patch(f"/applications/{app_id}", headers=H, json={"tailored_cv": edited})
    credits = client.get("/billing/summary", headers=H).json()["credits"]

    r = client.post(f"/applications/{app_id}/reevaluate", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["ats_stale"] is False
    assert body["ats_score"] == 88
    # first re-eval after an edit is free
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits


def test_reevaluate_without_edit_charges_a_credit(client, monkeypatch):
    H, app_id = _completed_app(client, monkeypatch, "edit3@test.com")
    credits = client.get("/billing/summary", headers=H).json()["credits"]
    # not stale -> a re-eval is a normal charged LLM pass
    r = client.post(f"/applications/{app_id}/reevaluate", headers=H)
    assert r.status_code == 200
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits - 1


def test_set_template_does_not_touch_score(client, monkeypatch):
    H, app_id = _completed_app(client, monkeypatch, "tpl1@test.com")
    credits = client.get("/billing/summary", headers=H).json()["credits"]
    r = client.patch(f"/applications/{app_id}", headers=H, json={"template_id": "ats_modern"})
    assert r.status_code == 200
    body = r.json()
    assert body["template_id"] == "ats_modern"
    assert body["ats_stale"] is False          # template change never stales the score
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits


def test_unknown_template_rejected(client, monkeypatch):
    H, app_id = _completed_app(client, monkeypatch, "tpl2@test.com")
    r = client.patch(f"/applications/{app_id}", headers=H, json={"template_id": "nope"})
    assert r.status_code == 400


def test_templates_catalog_is_public_and_has_default(client):
    r = client.get("/templates")
    assert r.status_code == 200
    body = r.json()
    ids = [t["id"] for t in body["templates"]]
    assert body["default"] in ids
    assert "ats_classic" in ids
    assert any(not t["ats_safe"] for t in body["templates"])   # at least one designer template
