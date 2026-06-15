from conftest import auth_headers


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_auth_flow(client):
    r = client.post("/auth/register", json={"email": "a@test.com", "password": "supersecret1"})
    assert r.status_code == 201
    # duplicate
    assert client.post("/auth/register", json={"email": "a@test.com", "password": "supersecret1"}).status_code == 400
    # good login
    assert client.post("/auth/login", data={"username": "a@test.com", "password": "supersecret1"}).status_code == 200
    # bad login
    assert client.post("/auth/login", data={"username": "a@test.com", "password": "nope"}).status_code == 401


def test_cv_status_and_generate_gating(client):
    H = auth_headers(client)
    assert client.get("/cv/status", headers=H).json()["has_base_cv"] is False
    # generate blocked without a base CV
    assert client.post("/generate/start", headers=H,
                       json={"job_description": "Backend engineer FastAPI MySQL SaaS role needed here."}).status_code == 400
    # set base CV
    cv = {"contact": {"full_name": "Jane", "email": "j@test.com"}, "summary": "x", "skills": {},
          "experience": [], "projects": [], "education": [], "certifications": [], "awards": [], "languages": []}
    assert client.put("/cv", headers=H, json=cv).status_code == 200
    assert client.get("/cv/status", headers=H).json()["has_base_cv"] is True


def test_request_id_in_error_responses(client):
    H = auth_headers(client)
    r = client.post("/generate/start", headers=H, json={"job_description": "short"})  # validation error
    assert r.status_code == 422
    assert "request_id" in r.json()
    assert "x-request-id" in {k.lower() for k in r.headers}
