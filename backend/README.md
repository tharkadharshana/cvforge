# CVForge — backend

Multi-user SaaS. Stores one structured base CV per user. Generates ATS-friendly,
job-tailored CV + human-sounding cover letter as DOCX and PDF. Uses DeepSeek + Gemini.

## Stack
FastAPI + SQLAlchemy + JWT auth. SQLite for local dev/tests, Supabase Postgres
(via Supavisor pooler) in production via `DATABASE_URL`. Stateless backend —
no local disk, runs as a Vercel serverless function.
Renderers pure-python (`python-docx`, `fpdf2`) — no system libs, cloud-friendly.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill SECRET_KEY + provider keys
uvicorn app.main:app --reload
```
Docs at http://localhost:8000/docs

## LLM roles (env)
- `DRAFTER_PROVIDER` writes tailored CV + cover letter.
- `CRITIC_PROVIDER` (the other model) scores ATS fit + flags AI-sounding tone.
- Defaults: drafter=gemini (`gemini-3.5-flash`/`gemini-3.1-pro`), critic=deepseek (`deepseek-v4-flash`/`deepseek-v4-pro`).
- Swap freely. Models are env-config so no code change when names change.

## Flow / endpoints
1. `POST /auth/register`, `POST /auth/login` -> bearer token.
2. New user must set up a base CV one of two ways:
   - `POST /cv/import` {raw_text} — paste current CV text.
   - `POST /cv/import-file` (multipart `file`) — upload **PDF / DOCX / TXT**; text extracted then parsed.
   - `POST /cv/build` {answers} — guided questionnaire answers -> polished CV.
3. `GET /cv/status` -> {has_base_cv, counts}. Frontend gates generation on this.
4. `PUT /cv` — full structured edit (the editor saves here).
5. `POST /cv/qualification` {text} — dump a new qualification anytime, merged in.
6. `GET /cv` — current base CV.
7. Generation is a 4-step job, each step one HTTP request (so each stays well under any serverless time limit):
   - `POST /generate/start` {job_description, company, job_title} -> `{job_id, status}` (blocked until base CV exists / out of credits).
   - `POST /generate/{job_id}/tailor` -> tailored CV.
   - `POST /generate/{job_id}/cover` -> cover letter.
   - `POST /generate/{job_id}/critique` -> ATS critique + score; charges 1 credit on first success.
   - `GET /generate/{job_id}` -> current job state (for resume/poll/refresh).
8. `GET /applications` (completed jobs only), `GET /applications/{id}`, `GET /applications/{id}/download?doc=cv|cover&fmt=pdf|docx`.

## Logging / dev visibility
Every request gets a short `req=` id threaded through all logs:
extraction (pages/chars) -> pipeline stage -> LLM call (model tier, char counts, latency, token usage) -> errors with full traceback -> response status + ms.
- `LOG_LEVEL=DEBUG` adds LLM prompt/response previews.
- `LOG_FILE=...` also writes to a file.
Tail backend stdout to see exactly where a slow CV parse / generation is sitting.

## ATS rules baked into renderers
Single column, standard headings, real selectable text, no tables/graphics/text-boxes,
common fonts. The tailoring prompt mirrors JD keywords and forbids fabrication.

## Deploy notes (Vercel + Supabase)
- Deploy this `backend/` directory as its own Vercel project (Root Directory = `backend`).
  `api/index.py` exports the FastAPI `app`; `vercel.json` rewrites all paths to it.
- `DATABASE_URL` must be the Supabase **transaction-mode pooler** URI on **port 6543**
  (`...pooler.supabase.com:6543`), not the direct 5432 connection — serverless +
  an in-app pool on top of a direct connection exhausts Postgres connections fast.
  `database.py` uses `NullPool` for Postgres for this reason.
- Set a strong `SECRET_KEY`.
- `GENERATION_TIER=fast` (default) keeps every LLM call comfortably under 60s,
  since `/generate/*` now does exactly one LLM call per request. Do not set
  `GENERATION_TIER=quality` on Vercel Hobby.
- Set `APP_URL` to the frontend's Vercel domain (tightens CORS + sets the Polar return URL).
- For SaaS billing/usage metering + per-user rate limits: add next iteration.

## TODO (next iterations)
- React frontend.
- Billing + usage meter (credits/tokens) per user.
- Dockerfile + cloud deploy config.
- PDF template variants / DOCX styling themes.
- Async generation + job queue for long JDs.

## Billing / credits
Credits gate CV generation (`CREDITS_PER_GENERATION` each). All knobs live in `.env`:
- `FREE_TIER_MODE=trial` grants `FREE_TRIAL_CREDITS` once on signup. `forever_free` refills `FREE_MONTHLY_CREDITS` every 30 days.
- Plans come from `BILLING_PLANS_JSON` (id, name, price_usd, credits, checkout_url). Edit price/credits to set your margin; `COST_PER_GENERATION_USD` is your cost, used to compute the margin shown in `/billing/summary` (server-side only, never shown to users).
- `/generate/start` blocks with **402** when credits run out; a credit is charged exactly once, at the final `/generate/{job_id}/critique` step on first success (idempotent on retry). Failed or abandoned jobs are not charged.
- Endpoints: `GET /billing/summary`, `GET /billing/ledger`, `POST /billing/checkout?plan_id=`, `POST /billing/webhook`.

### Payments via Polar (Merchant of Record)
Polar collects the money, handles tax + PCI, and pays out to Sri Lanka. Cards never touch this server.

**Manual setup (fill these into `.env`):**
1. Sign up at polar.sh. Use the **Sandbox** first (sandbox.polar.sh) to test, then repeat in production.
2. Create your **products** — one-time and/or subscription — each with a price. Copy each product's ID into `BILLING_PLANS_JSON` -> `polar_product_id`. Keep `price_usd`/`credits` in sync with the product (they set how many credits a payment grants and your displayed price).
3. Settings -> create an **Organization Access Token** -> `POLAR_ACCESS_TOKEN` (server-side only; never in the frontend).
4. Webhooks -> add endpoint `https://YOUR_BACKEND/billing/webhook`, subscribe to **order.paid**, copy the signing secret -> `POLAR_WEBHOOK_SECRET`.
5. Set `POLAR_SERVER=sandbox` (or `production`) and `POLAR_SUCCESS_URL` to your frontend, e.g. `https://app.example.com/billing?status=success`.

**How it flows:** user clicks a plan -> `POST /billing/checkout` creates a Polar checkout server-side (product id comes from your config, never the client) -> user pays on Polar's hosted page (one-time or recurring) -> Polar calls `POST /billing/webhook` -> we verify and credit. `order.paid` fires for purchases AND subscription renewals, so renewals top up automatically. Customers manage saved cards / cancel via `POST /billing/portal`.

**Security controls implemented:**
- Webhook signature verified via Standard Webhooks (HMAC-SHA256, base64 secret, replay-protected timestamp). Fails closed — bad/missing/forged signature -> 401; missing secret -> 503.
- Idempotent: credits keyed on Polar's order id (`payments.provider_ref` unique), so Polar's retries never double-credit.
- Server-side authority: credit amounts come from your `BILLING_PLANS_JSON`, never from the webhook payload, so a tampered payload can't inflate credits. Checkout product id is resolved server-side from `plan_id`.
- The access token is never sent to the browser; cards are entered only on Polar (PCI handled by Polar/Stripe).
- Tested end-to-end: valid signed event credits once; replay is ignored; forged and unsigned events are rejected 401.


## Job URL fetch
`POST /jobs/fetch-url {url}` fetches a posting and extracts the text with a lightweight HTML-tag-stripping
extractor (kept dependency-free for Vercel's function size limit). Works on most job boards/company pages.
LinkedIn often needs login / renders via JS, so it may fail there — the user is told to paste the text instead.

## Logging, audit & support (investigate any complaint)
Two layers:

**1. Durable audit trail (`audit_events` table).** Every meaningful action writes one queryable, permanent row: `register`, `login`, `login_failed`, `cv_import`, `cv_import_file`, `cv_build`, `cv_qualification`, `cv_edit`, `generate_start`, `generate_tailor`, `generate_cover`, `generate_done`, `generate_failed`, `generate_improve`, `checkout_started`, `portal_opened`, `webhook_received` (ok / rejected), `purchase`, `subscription_canceled`, `admin_credit_adjust`. Each row has `user_id`, `request_id`, `event`, `status`, `ip`, non-PII `meta`, and timestamp. Written via an independent DB session, so a failed/rolled-back request still leaves its trail.

**2. Operational logs.** Per-request `request_id` threads through extraction → pipeline stage → LLM call (model, latency, tokens) → errors with full traceback → response. Set `LOG_JSON=true` for structured JSON (Better Stack / Axiom / Loki). `LOG_FILE` to also write to disk.

**Request id everywhere.** Every response carries `X-Request-ID`; error bodies include `request_id`. A user can quote it and you jump straight to their trace: `GET /admin/audit?request_id=...`.

**Admin / support endpoints** (access via `ADMIN_EMAILS` or `users.is_admin`):
- `GET /admin/users?query=` — find a user by email/name.
- `GET /admin/users/{id}` — full investigation view: profile, payments, credit ledger, audit trail, generations.
- `GET /admin/audit?user_id=&event=&request_id=&status=` — filtered event search.
- `POST /admin/users/{id}/credits {delta, reason}` — manual grant/refund (itself audited).

**Privacy / redaction.** Audit `meta` and logs never store CV text, job descriptions, or cover letters — only counts, ids, scores, and outcomes. Blocked keys (raw_text, job_description, cover_letter, password, …) are stripped automatically.

**Retention.** Audit rows live in Postgres indefinitely by default. If you need a retention window for compliance, periodically delete `audit_events` older than N days.
