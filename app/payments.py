"""Payment dispatch: real PayPal Sandbox vs. clearly labeled simulation.

DEMO_MODE fallback: when PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not
both set, payments run against a local simulation. Every simulated response
carries mode="SIMULATED" and a human-readable notice, and the UI shows a
persistent banner. Nothing about the simulation pretends to be PayPal.

The budget guard lives in app.main and runs before this module is touched,
so the guard and approval logic are identical in both modes.
"""

import os
import uuid

from . import paypal_client

SIM_NOTICE = "SIMULATED (no PayPal credentials) — no real PayPal order was created."


def payment_mode() -> str:
    if os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_CLIENT_SECRET"):
        return "PAYPAL_SANDBOX"
    return "SIMULATED"


def create_payment(items: list, total_usd: float) -> dict:
    """Start a payment. Simulated mode completes in one step; real mode
    returns an approve URL and waits for capture."""
    if payment_mode() == "PAYPAL_SANDBOX":
        order = paypal_client.create_order(items, total_usd)
        return {
            "mode": "PAYPAL_SANDBOX",
            "status": "AWAITING_PAYER_APPROVAL",
            "order_id": order["order_id"],
            "approve_url": order["approve_url"],
            "notice": "Approve this order with a PayPal Sandbox buyer account, then capture.",
        }
    order_id = "SIM-" + uuid.uuid4().hex[:12].upper()
    capture_id = "SIMCAP-" + uuid.uuid4().hex[:12].upper()
    return {
        "mode": "SIMULATED",
        "status": "COMPLETED",
        "order_id": order_id,
        "approve_url": None,
        "receipt": {
            "order_id": order_id,
            "capture_id": capture_id,
            "status": "COMPLETED",
            "amount_usd": total_usd,
            "currency": "USD",
            "payer_email": None,
        },
        "notice": SIM_NOTICE,
    }


def capture_payment(order_id: str) -> dict:
    """Capture a previously created real PayPal order."""
    receipt = paypal_client.capture_order(order_id)
    return {"mode": "PAYPAL_SANDBOX", "status": receipt["status"], "receipt": receipt}
