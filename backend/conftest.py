import os
import base64

# Deterministic settings for CI — set BEFORE app/config is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ci.db")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("FREE_TIER_MODE", "trial")
os.environ.setdefault("FREE_TRIAL_CREDITS", "2")
os.environ.setdefault("CREDITS_PER_GENERATION", "1")
os.environ.setdefault("ADMIN_EMAILS", "admin@test.com")
os.environ.setdefault("POLAR_WEBHOOK_SECRET", base64.b64encode(b"ci-webhook-secret").decode())
os.environ.setdefault(
    "BILLING_PLANS_JSON",
    '[{"id":"pro","name":"Pro","price_usd":29,"credits":500,"polar_product_id":"prod_ci","recurring":true}]',
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client, email="user@test.com", password="supersecret1", full_name="User"):
    client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})
    tok = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}
