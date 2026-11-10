"""Real PayPal Sandbox integration (Orders API v2).

Credentials come only from the environment:
    PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
They are never hardcoded, logged, or included in any response.

Flow (standard PayPal checkout):
    1. OAuth2 client-credentials token from /v1/oauth2/token
    2. Create order  -> POST /v2/checkout/orders        (intent=CAPTURE)
    3. Buyer approves via the 'approve' link from the create response
    4. Capture order -> POST /v2/checkout/orders/{id}/capture
"""

import os

import httpx

from .http_util import http_client

BASE_URL = "https://api-m.sandbox.paypal.com"


class PayPalError(Exception):
    pass


def _credentials():
    client_id = os.environ.get("PAYPAL_CLIENT_ID")
    client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise PayPalError("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET not set")
    return client_id, client_secret


def get_access_token() -> str:
    client_id, client_secret = _credentials()
    with http_client(timeout=20.0) as client:
        client.base_url = httpx.URL(BASE_URL)
        resp = client.post(
            "/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        raise PayPalError(f"OAuth token request failed: HTTP {resp.status_code}")
    return resp.json()["access_token"]


def create_order(items: list, total_usd: float) -> dict:
    """Create a CAPTURE-intent order. Returns {order_id, status, approve_url}."""
    token = get_access_token()
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": "agentic-pay-demo",
                "description": "Agentic Pay delegated purchase",
                "amount": {
                    "currency_code": "USD",
                    "value": f"{total_usd:.2f}",
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": f"{total_usd:.2f}",
                        }
                    },
                },
                "items": [
                    {
                        "name": item["name"][:127],
                        "quantity": str(item.get("quantity", 1)),
                        "unit_amount": {
                            "currency_code": "USD",
                            "value": f"{item['price_usd']:.2f}",
                        },
                    }
                    for item in items
                ],
            }
        ],
        "application_context": {
            "brand_name": "Agentic Pay",
            "user_action": "PAY_NOW",
        },
    }
    with http_client(timeout=20.0) as client:
        client.base_url = httpx.URL(BASE_URL)
        resp = client.post(
            "/v2/checkout/orders",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
    if resp.status_code not in (200, 201):
        raise PayPalError(f"Create order failed: HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    approve_url = next(
        (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"),
        None,
    )
    return {"order_id": data["id"], "status": data["status"], "approve_url": approve_url}


def capture_order(order_id: str) -> dict:
    """Capture a buyer-approved order. Returns a receipt-shaped dict."""
    token = get_access_token()
    with http_client(timeout=20.0) as client:
        client.base_url = httpx.URL(BASE_URL)
        resp = client.post(
            f"/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
    if resp.status_code not in (200, 201):
        raise PayPalError(f"Capture failed: HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    capture = data["purchase_units"][0]["payments"]["captures"][0]
    return {
        "order_id": data["id"],
        "capture_id": capture["id"],
        "status": data["status"],
        "amount_usd": float(capture["amount"]["value"]),
        "currency": capture["amount"]["currency_code"],
        "payer_email": data.get("payer", {}).get("email_address"),
    }
