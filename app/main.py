"""Agentic Pay — delegated purchasing agent (PayPal AI Hackathon demo).

Run:  uvicorn app.main:app --port 8077
"""

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import agent, payments

# --- tiny .env loader (no extra dependency) --------------------------------
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip())

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Agentic Pay", version="0.1.0")

# In-memory plan store for the demo (single-process, no database).
PLANS: dict = {}


class PlanRequest(BaseModel):
    goal: str = Field(default="Team snacks for the office")
    budget_usd: float = Field(gt=0)


class PayRequest(BaseModel):
    plan_id: str
    human_approved: bool = False


class CaptureRequest(BaseModel):
    plan_id: str


def _public_plan(plan: dict) -> dict:
    return {
        "plan_id": plan["plan_id"],
        "goal": plan["goal"],
        "budget_usd": plan["budget_usd"],
        "items": plan["items"],
        "total_usd": plan["total_usd"],
        "explanation": plan["explanation"],
        "within_budget": plan["within_budget"],
        "over_by_usd": plan["over_by_usd"],
        "status": plan["status"],
        "payment_mode": payments.payment_mode(),
        "payment": plan.get("payment"),
        "receipt": plan.get("receipt"),
    }


@app.get("/api/health")
def health():
    mode = payments.payment_mode()
    return {
        "status": "ok",
        "payment_mode": mode,
        "notice": payments.SIM_NOTICE if mode == "SIMULATED" else "PayPal Sandbox configured.",
    }


@app.post("/api/plan")
def make_plan(req: PlanRequest):
    """Agent builds its best bundle; the budget guard evaluates it."""
    built = agent.build_plan(req.goal)
    total = built["total_usd"]
    within = total <= req.budget_usd
    plan = {
        "plan_id": uuid.uuid4().hex[:12],
        "goal": req.goal,
        "budget_usd": req.budget_usd,
        "items": built["items"],
        "total_usd": total,
        "explanation": built["explanation"],
        "within_budget": within,
        "over_by_usd": round(total - req.budget_usd, 2) if not within else 0.0,
        # The guard: over-budget plans cannot be paid until a human approves.
        "status": "READY_TO_PAY" if within else "AWAITING_HUMAN_APPROVAL",
        "payment": None,
        "receipt": None,
    }
    PLANS[plan["plan_id"]] = plan
    return _public_plan(plan)


@app.get("/api/plan/{plan_id}")
def get_plan(plan_id: str):
    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    return _public_plan(plan)


@app.post("/api/pay")
def pay(req: PayRequest):
    """Pay for a plan. BUDGET GUARD: if the plan is over budget and the
    request does not carry explicit human approval, refuse BEFORE any
    payment call is made — in both simulated and real PayPal modes."""
    plan = PLANS.get(req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    if plan["receipt"]:
        raise HTTPException(status_code=409, detail="plan already paid")
    if not plan["within_budget"] and not req.human_approved:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Budget guard: total ${plan['total_usd']:.2f} exceeds budget "
                f"${plan['budget_usd']:.2f} by ${plan['over_by_usd']:.2f}. "
                "Explicit human approval is required before payment."
            ),
        )
    try:
        result = payments.create_payment(plan["items"], plan["total_usd"])
    except Exception as exc:  # PayPal errors surface as 502, never silently pass
        raise HTTPException(status_code=502, detail=f"Payment failed: {exc}")
    plan["payment"] = result
    if result.get("receipt"):
        plan["receipt"] = result["receipt"]
        plan["status"] = "PAID"
    else:
        plan["status"] = result["status"]  # AWAITING_PAYER_APPROVAL (real mode)
    return _public_plan(plan)


@app.post("/api/capture")
def capture(req: CaptureRequest):
    """Capture after the buyer approved in PayPal (real mode only)."""
    plan = PLANS.get(req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    if plan["receipt"]:
        return _public_plan(plan)
    if not plan.get("payment") or not plan["payment"].get("order_id"):
        raise HTTPException(status_code=409, detail="no PayPal order to capture yet")
    try:
        result = payments.capture_payment(plan["payment"]["order_id"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Capture failed: {exc}")
    plan["receipt"] = result["receipt"]
    plan["status"] = "PAID"
    return _public_plan(plan)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
