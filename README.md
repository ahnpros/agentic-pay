# Agentic Pay — a delegated purchasing agent

**PayPal AI Hackathon demo.** You give the agent a *goal* and a *budget*
("team snacks, ₩100,000"). The agent searches a catalog, compares options,
pays with **PayPal Sandbox**, and hands you a receipt. If its best plan goes
**over budget, it stops before any payment** and asks a human to approve —
that budget guard is the core of the product: delegation with a hard limit.

## What it does

1. **Plan** — a deterministic agent ranks a mock catalog of 9 snack products
   by value (rating per dollar), picks one best-value item per category so
   the assortment is complete, then fills the bundle to 7 items. It explains
   its choice in the UI. Selection ignores the budget on purpose.
2. **Budget guard** — the finished plan is compared against the budget.
   - Within budget → ready to pay.
   - Over budget → plan status `AWAITING_HUMAN_APPROVAL`. The pay endpoint
     refuses over-budget payments without explicit human approval (HTTP
     403), and **no PayPal order is created** until approval is given.
3. **Pay** — PayPal Sandbox Orders API: OAuth client-credentials →
   create order → buyer approves in PayPal → capture. The receipt shows
   order ID, capture ID, status, and amount.

## Architecture

```
static/index.html     Single-page UI (vanilla JS), served by FastAPI
app/main.py           API: /api/health, /api/plan, /api/pay, /api/capture
                      The budget guard lives here, before any payment call.
app/agent.py          Deterministic value-ranking planner + optional Gemini
                      explanation hook (never required)
app/catalog.py        Mock catalog, 9 products, USD prices
app/paypal_client.py  Real PayPal Sandbox integration (OAuth + Orders API)
app/payments.py       Mode dispatch: PAYPAL_SANDBOX vs SIMULATED
```

### Demo mode (no credentials)

If `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` are not both set, the payment
step runs a **local simulation**, visibly labeled
`SIMULATED (no PayPal credentials)` in the UI banner, in API responses, and
on the receipt. The full flow — including the budget guard and the approval
stop — works identically in both modes; only the payment rail differs.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8077
# open http://localhost:8077
```

Without credentials you get the simulated mode — enough to demo everything.
Quick API check:

```bash
curl localhost:8077/api/health
curl -X POST localhost:8077/api/plan -H 'Content-Type: application/json' \
  -d '{"goal": "Team snacks", "budget_usd": 100}'
```

## Configure PayPal Sandbox (real payments)

1. Go to <https://developer.paypal.com> and log in (or create an account).
2. **Apps & Credentials → Sandbox** → **Create App** (e.g. "Agentic Pay").
3. Copy the app's **Client ID** and **Secret**.
4. Create a sandbox *buyer* account under **Sandbox → Accounts** — you use
   it to approve orders as the payer.
5. In this project: `cp .env.example .env` and fill in
   `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` (or export them). Never
   commit `.env`; never share the secret.
6. Restart the server. The UI banner turns green ("Connected to PayPal
   Sandbox"). Paying now creates a real sandbox order: click
   **Approve in PayPal Sandbox**, log in with the sandbox buyer, approve,
   then **capture** back in the demo to get a real receipt.

## Currency handling (KRW → USD)

PayPal Sandbox orders here are in USD and catalog prices are USD, to keep
the payment path exact (no rounding between plan total and captured
amount). The UI lets the user enter the budget in **KRW** (₩100,000-style
budgets are the natural way to state the goal); it is converted to USD at a
fixed **demo rate of ₩1,470 = $1**, shown in the UI next to the input, and
the converted USD budget is what the guard enforces and what the API
receives (`budget_usd`). A production version would fetch a live FX rate at
plan time and re-check it at payment time.

## Demo script (3 minutes)

1. **0:00 — The idea.** "Delegating purchases is easy; delegating them
   *safely* is the product. The agent gets a goal and a budget — not a
   shopping list."
2. **0:30 — Within budget.** Goal "Team snacks for the office", budget
   $100 → *Ask the agent to shop*. Show the ranked bundle ($95.93) and the
   agent's explanation → *Pay with PayPal* → receipt.
3. **1:40 — Over budget.** Budget $50 → same bundle, now $45.93 over.
   Payment is **stopped**; no order exists. Show the approval screen.
4. **2:20 — Approval.** *I approve — pay anyway* → payment proceeds →
   receipt. (Or *Cancel* → nothing is paid.)
5. **2:50 — Wrap.** "Budget guard first, payment second — that's Agentic
   Pay." Mention sandbox vs. simulated banner if running without
   credentials.

## Track

Agentic Payments — the differentiator is delegated payment under a budget
guard with explicit human approval, not storefront UX.

## License

MIT — see `LICENSE`.

## Verified Sandbox run (2026-11-11)

End-to-end run against the real PayPal Sandbox (no simulated mode):
goal "team snacks", budget $100 -> plan total $95.93 -> order
`2P79157997934611P` approved by the sandbox buyer -> capture
`9DX20792JS936453D` COMPLETED, $95.93. With a $50 budget the same plan
stops at `AWAITING_HUMAN_APPROVAL` and `/api/pay` returns 403 until a
human approves. Set `RETURN_URL` to control where PayPal returns the
buyer after approval (defaults to this repository page).
