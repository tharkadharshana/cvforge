import os
import json
import datetime
from standardwebhooks import Webhook
from conftest import auth_headers


def test_signup_grant_and_deduction(client):
    H = auth_headers(client, email="credit@test.com")
    s = client.get("/billing/summary", headers=H).json()
    assert s["credits"] == 2          # FREE_TRIAL_CREDITS
    assert s["plan"] == "trial"
    # margin is computed server-side and present
    assert all("margin_pct" in p for p in s["plans"])


def test_generate_blocked_when_out_of_credits(client):
    H = auth_headers(client, email="broke@test.com")
    cv = {"contact": {"full_name": "Jane", "email": "j@test.com"}, "summary": "x", "skills": {},
          "experience": [], "projects": [], "education": [], "certifications": [], "awards": [], "languages": []}
    client.put("/cv", headers=H, json=cv)
    # drain credits to 0 via admin
    admin = auth_headers(client, email="admin@test.com")
    users = client.get("/admin/users?query=broke", headers=admin).json()
    uid = users[0]["id"]
    client.post(f"/admin/users/{uid}/credits", headers=admin, json={"delta": -2, "reason": "test_drain"})
    # now generation must be blocked with 402 (before any LLM call)
    r = client.post("/generate/start", headers=H,
                    json={"job_description": "Backend engineer FastAPI MySQL SaaS role needed here now."})
    assert r.status_code == 402


def _signed(payload: dict):
    secret = os.environ["POLAR_WEBHOOK_SECRET"]
    wh = Webhook(secret)
    body = json.dumps(payload)
    msg_id = "msg_ci_test"
    ts = datetime.datetime.now()
    sig = wh.sign(msg_id, ts, body)
    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": str(int(ts.timestamp())),
        "webhook-signature": sig,
        "content-type": "application/json",
    }
    return body, headers


def test_webhook_credits_idempotent_and_secure(client):
    H = auth_headers(client, email="buyer@test.com")
    uid = client.get("/admin/users?query=buyer",
                     headers=auth_headers(client, email="admin@test.com")).json()
    uid = uid[0]["id"]
    order = {"type": "order.paid", "data": {"id": "order_ci_1", "product_id": "prod_ci",
             "customer": {"id": "cust_ci_1", "email": "buyer@test.com"},
             "metadata": {"user_id": str(uid), "plan_id": "pro"}}}

    body, headers = _signed(order)
    assert client.post("/billing/webhook", content=body, headers=headers).status_code == 200
    assert client.get("/billing/summary", headers=H).json()["credits"] == 2 + 500

    # replay same order -> no double credit
    body, headers = _signed(order)
    client.post("/billing/webhook", content=body, headers=headers)
    assert client.get("/billing/summary", headers=H).json()["credits"] == 502

    # forged signature -> 401
    forged = client.post("/billing/webhook", content=body,
                         headers={"webhook-id": "x", "webhook-timestamp": "1",
                                  "webhook-signature": "v1,ZmFrZQ==", "content-type": "application/json"})
    assert forged.status_code == 401

    # unsigned -> 401
    assert client.post("/billing/webhook", content=body,
                       headers={"content-type": "application/json"}).status_code == 401
