from __future__ import annotations
import httpx
from ..config import settings
from ..logging_config import get_logger

log = get_logger("polar")


def _base() -> str:
    return "https://api.polar.sh" if settings.polar_server == "production" else "https://sandbox-api.polar.sh"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.polar_access_token}", "Content-Type": "application/json"}


def create_checkout(plan, user) -> str:
    """Create a Polar hosted checkout and return its URL. Handles one-time + subscription products."""
    if not settings.polar_access_token:
        raise RuntimeError("POLAR_ACCESS_TOKEN not set")
    if not plan.polar_product_id:
        raise RuntimeError(f"No Polar product configured for plan '{plan.id}' (set polar_product_id)")
    body = {
        "products": [plan.polar_product_id],
        "success_url": settings.polar_success_url,
        "customer_email": user.email,
        # metadata is echoed back on the order webhook -> we trust this (set server-side) to match the buyer
        "metadata": {"user_id": str(user.id), "plan_id": plan.id},
    }
    with httpx.Client(timeout=30.0) as c:
        r = c.post(f"{_base()}/v1/checkouts/", headers=_headers(), json=body)
        if r.status_code >= 400:
            log.error("polar checkout failed %s: %s", r.status_code, r.text[:300])
            r.raise_for_status()
        data = r.json()
    return data["url"]


def create_portal_session(customer_id: str) -> str:
    """Customer portal: manage cards, subscriptions, invoices, cancel. Polar/Stripe handle PCI."""
    if not settings.polar_access_token:
        raise RuntimeError("POLAR_ACCESS_TOKEN not set")
    with httpx.Client(timeout=30.0) as c:
        r = c.post(f"{_base()}/v1/customer-sessions/", headers=_headers(), json={"customer_id": customer_id})
        if r.status_code >= 400:
            log.error("polar portal failed %s: %s", r.status_code, r.text[:300])
            r.raise_for_status()
        data = r.json()
    return data.get("customer_portal_url") or data.get("url", "")


def verify_webhook(body: bytes, headers: dict) -> dict:
    """Verify Standard Webhooks signature using the official library. Raises on any failure (fail closed)."""
    from standardwebhooks import Webhook
    wh = Webhook(settings.polar_webhook_secret)
    return wh.verify(body, headers)  # returns parsed dict; raises if signature/timestamp invalid
