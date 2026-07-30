"""Interview prep coaching for a completed application."""
from conftest import auth_headers
from app.routers import generate as generate_router

BASE_CV = {
    "contact": {"full_name": "Jane Doe", "email": "j@test.com"}, "summary": "x", "skills": {},
    "experience": [], "projects": [], "education": [], "certifications": [], "awards": [], "languages": [],
}
TAILORED_CV = {
    "contact": {"full_name": "Jane Doe", "email": "j@test.com"}, "summary": "Tailored summary",
    "skills": {"Languages": ["Python"]},
    "experience": [], "projects": [], "education": [], "certifications": [], "awards": [], "languages": [],
}
JD = "Backend engineer FastAPI Postgres SaaS role needed here now."

PREP = {
    "likely_questions": [{"question": "Tell me about a time you used Python.",
                          "why_asked": "Matches your listed skill.", "suggested_approach": "Use STAR."}],
    "topics_to_research": ["Company funding stage"],
    "questions_to_ask_them": ["What does success look like in 6 months?"],
}


class FakeDrafter:
    def complete_json(self, system, user, pro=False):
        return dict(TAILORED_CV)

    def complete(self, system, user, json_mode=False, pro=False):
        return "Dear hiring team, excited about this role."


class FakeCritic:
    def complete_json(self, system, user, pro=False):
        return {"ats_score": 88, "keyword_matches": ["Python"], "missing_keywords": [],
                "human_tone_notes": [], "suggestions": []}


class FakeInterviewCritic(FakeCritic):
    """Same critic, but returns the interview prep shape when asked -- distinguished
    by call order isn't needed since complete_json's caller controls the prompt;
    here we just always return PREP for simplicity since this critic instance is
    only ever used for the interview-prep call in these tests."""
    def complete_json(self, system, user, pro=False):
        return dict(PREP)


def _mock_llm(monkeypatch, critic=FakeCritic):
    monkeypatch.setattr(generate_router, "drafter", lambda: FakeDrafter())
    monkeypatch.setattr(generate_router, "critic", lambda: critic())


def _done_application(client, monkeypatch, email):
    H = auth_headers(client, email=email)
    assert client.put("/cv", headers=H, json=BASE_CV).status_code == 200
    _mock_llm(monkeypatch)
    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]
    client.post(f"/generate/{job_id}/tailor", headers=H)
    client.post(f"/generate/{job_id}/cover", headers=H)
    client.post(f"/generate/{job_id}/critique", headers=H)
    return H, job_id


def test_interview_prep_charges_one_credit(client, monkeypatch):
    H, job_id = _done_application(client, monkeypatch, "prep1@test.com")
    credits_before = client.get("/billing/summary", headers=H).json()["credits"]

    monkeypatch.setattr(generate_router, "critic", lambda: FakeInterviewCritic())
    r = client.post(f"/applications/{job_id}/interview-prep", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["likely_questions"][0]["question"] == "Tell me about a time you used Python."
    assert body["topics_to_research"] == ["Company funding stage"]

    credits_after = client.get("/billing/summary", headers=H).json()["credits"]
    assert credits_after == credits_before - 1


def test_interview_prep_is_cached_and_free_on_repeat(client, monkeypatch):
    H, job_id = _done_application(client, monkeypatch, "prep2@test.com")
    monkeypatch.setattr(generate_router, "critic", lambda: FakeInterviewCritic())
    client.post(f"/applications/{job_id}/interview-prep", headers=H)
    credits_after_first = client.get("/billing/summary", headers=H).json()["credits"]

    # second call must not hit the LLM again or charge again
    def boom():
        raise AssertionError("should not call critic again -- result is cached")
    monkeypatch.setattr(generate_router, "critic", boom)
    r = client.post(f"/applications/{job_id}/interview-prep", headers=H)
    assert r.status_code == 200
    assert client.get("/billing/summary", headers=H).json()["credits"] == credits_after_first


def test_interview_prep_requires_completed_application(client, monkeypatch):
    H = auth_headers(client, email="prep3@test.com")
    assert client.put("/cv", headers=H, json=BASE_CV).status_code == 200
    _mock_llm(monkeypatch)
    job_id = client.post("/generate/start", headers=H, json={"job_description": JD}).json()["job_id"]
    r = client.post(f"/applications/{job_id}/interview-prep", headers=H)
    assert r.status_code == 409


def test_interview_prep_blocked_when_out_of_credits(client, monkeypatch):
    H, job_id = _done_application(client, monkeypatch, "prep4@test.com")
    admin = auth_headers(client, email="admin@test.com")
    uid = client.get("/admin/users?query=prep4", headers=admin).json()[0]["id"]
    credits = client.get("/billing/summary", headers=H).json()["credits"]
    client.post(f"/admin/users/{uid}/credits", headers=admin, json={"delta": -credits, "reason": "drain"})

    monkeypatch.setattr(generate_router, "critic", lambda: FakeInterviewCritic())
    r = client.post(f"/applications/{job_id}/interview-prep", headers=H)
    assert r.status_code == 402


def test_interview_prep_included_in_application_detail(client, monkeypatch):
    H, job_id = _done_application(client, monkeypatch, "prep5@test.com")
    monkeypatch.setattr(generate_router, "critic", lambda: FakeInterviewCritic())
    client.post(f"/applications/{job_id}/interview-prep", headers=H)

    r = client.get(f"/applications/{job_id}", headers=H)
    assert r.json()["interview_prep"]["topics_to_research"] == ["Company funding stage"]
