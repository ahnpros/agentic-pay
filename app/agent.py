"""Deterministic agent decision step for Agentic Pay.

The agent builds its *best* bundle first, without looking at the budget:
one best-value item per category (so the assortment is complete), then the
remaining highest-value items until the bundle reaches TARGET_ITEMS.
Value = rating per dollar, so cheap and well-reviewed products rank first.

The budget is deliberately NOT an input to selection. The budget guard in
app.main compares the finished plan against the budget afterwards, which is
what makes the over-budget stop-and-ask-for-approval flow possible and
identical in simulated and real PayPal modes.

An optional Gemini hook (explain_with_gemini) exists for richer wording but
is never required: if GEMINI_API_KEY is unset or the call fails, the
deterministic explanation is used.
"""

import os

from .catalog import PRODUCTS

TARGET_ITEMS = 7


def value_score(product):
    return product["rating"] / product["price_usd"]


def build_plan(goal: str) -> dict:
    ranked = sorted(PRODUCTS, key=value_score, reverse=True)

    selected = []
    seen_categories = set()
    # Pass 1: best-value item of each category, in overall value order.
    for product in ranked:
        if product["category"] not in seen_categories:
            selected.append(product)
            seen_categories.add(product["category"])
    # Pass 2: fill up to TARGET_ITEMS with the best remaining values.
    for product in ranked:
        if len(selected) >= TARGET_ITEMS:
            break
        if product not in selected:
            selected.append(product)
    selected = selected[:TARGET_ITEMS]

    total = round(sum(p["price_usd"] for p in selected), 2)
    categories = sorted({p["category"] for p in selected})
    top = max(selected, key=value_score)

    explanation = (
        f"For '{goal}', I picked {len(selected)} items covering "
        f"{len(categories)} categories ({', '.join(categories)}), ranked by "
        f"rating per dollar. Best value: {top['name']} "
        f"({top['rating']} stars at ${top['price_usd']:.2f}). "
        f"Bundle total: ${total:.2f}."
    )
    explanation = explain_with_gemini(goal, selected, total) or explanation

    return {
        "goal": goal,
        "items": [
            {
                "id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "price_usd": p["price_usd"],
                "rating": p["rating"],
                "quantity": 1,
            }
            for p in selected
        ],
        "total_usd": total,
        "explanation": explanation,
    }


def explain_with_gemini(goal: str, selected: list, total: float):
    """Optional LLM wording. Returns None unless GEMINI_API_KEY is set and
    the call succeeds; the demo must run fully without it."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from .http_util import http_client

        names = ", ".join(p["name"] for p in selected)
        prompt = (
            "In one or two short sentences, explain this purchasing agent's "
            f"choice. Goal: {goal}. Chosen items: {names}. "
            f"Total: ${total:.2f}. Selection rule: best rating per dollar, "
            "one item per snack category first."
        )
        with http_client(timeout=10.0) as client:
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.0-flash:generateContent",
                params={"key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip() or None
    except Exception:
        return None
