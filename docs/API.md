# API Reference

Base URL (dev): `http://localhost:8000`. Interactive Swagger UI at `/docs`.

All endpoints except `/auth/register`, `/auth/login`, and `/billing/webhook`
require `Authorization: Bearer <token>`.

## Auth

### `POST /auth/register`
Body: `{ "email": str, "password": str (min 8), "full_name": str }`
Returns `201` with `{ id, email, full_name }`. Grants signup credits per
`FREE_TIER_MODE`.

### `POST /auth/login`
Form-encoded (`application/x-www-form-urlencoded`): `username` (email), `password`.
Returns `{ access_token, token_type: "bearer" }`.

---

## Base CV (`/cv`)

The "base CV" is one structured JSON document per user (the `CVData` shape —
see [DATA_MODEL.md](DATA_MODEL.md)).

### `GET /cv/status`
Returns `{ has_base_cv, experience_count, education_count, project_count, skill_categories }`.

### `GET /cv`
Returns the current `CVData`. Auto-creates an empty base CV row if none exists.

### `POST /cv/import`
Body: `{ "raw_text": str }` — paste an existing CV; LLM parses it into `CVData`.

### `POST /cv/import-file`
Multipart upload (`file`): PDF / DOCX / TXT. Extracts text then parses like `/cv/import`.

### `POST /cv/build`
Body: `{ "answers": { field: value, ... } }` — builds a polished `CVData` from
questionnaire answers (used by the Onboarding flow).

### `PUT /cv`
Body: full `CVData` object — direct structured edit / manual save (overwrites base CV).

### `POST /cv/qualification`
Body: `{ "text": str (min 3) }` — free-text dump of a new qualification/experience;
LLM merges it into the existing base CV.

---

## Generation (`/generate`, `/applications`)

### `POST /generate`
Body: `{ "job_description": str (min 20), "job_title": str, "company": str }`

Preconditions: base CV must exist and have a contact name; user must have
credits (`BILLING_ENABLED`).

Flow: drafter LLM produces tailored `CVData` + cover letter; critic LLM scores
ATS fit. Saves an `Application`, deducts `CREDITS_PER_GENERATION` credits.

Returns:
```json
{
  "application_id": 1,
  "tailored_cv": { ...CVData },
  "cover_letter": "string",
  "critique": {
    "ats_score": 0,
    "keyword_matches": [],
    "missing_keywords": [],
    "human_tone_notes": [],
    "suggestions": []
  }
}
```
Errors: `400` no base CV, `402` out of credits, `502` LLM failure.

### `GET /applications`
List of past applications (id, job_title, company, ats_score, created_at), newest first.

### `GET /applications/{app_id}`
Full record: tailored_cv, cover_letter, ats_score, critique.

### `GET /applications/{app_id}/download?doc=cv|cover&fmt=pdf|docx`
Streams the rendered file (`Content-Disposition: attachment`).

---

## Jobs (`/jobs`)

### `POST /jobs/fetch-url`
Body: `{ "url": str }` — fetches the page and extracts job posting text.
Returns `{ "title": str, "text": str }`.

---

## Billing (`/billing`)

### `GET /billing/summary`
Returns `{ billing_enabled, plan, credits, free_tier_mode, credits_per_generation, has_customer, plans: [...] }`.
Also triggers `maybe_refill_monthly` (forever_free mode).

### `GET /billing/ledger`
Last 50 `CreditLedger` rows for the user: `{ delta, reason, balance_after, created_at }`.

### `POST /billing/checkout?plan_id=<id>`
Creates a Polar checkout session for the given plan. Returns `{ checkout_url }`.

### `POST /billing/portal`
Creates a Polar customer-portal session (requires an existing `polar_customer_id`).
Returns `{ checkout_url }`.

### `POST /billing/webhook`
Polar webhook receiver (no auth — verified via Standard Webhooks signature,
`POLAR_WEBHOOK_SECRET`). Handles `order.paid` (credits purchase/renewal) and
`subscription.canceled`/`subscription.revoked` (downgrade to free).

---

## Admin (`/admin`) — requires `is_admin` / `ADMIN_EMAILS`

### `GET /admin/users?query=&limit=`
Search users by email/name substring.

### `GET /admin/users/{user_id}`
Full investigation view: profile, payments, credit ledger, audit trail, generations.

### `GET /admin/audit?user_id=&event=&request_id=&status=&limit=`
Search audit events.

### `POST /admin/users/{user_id}/credits`
Body: `{ "delta": int, "reason": str (2-80 chars) }` — manually adjust a user's
credit balance; logged to ledger + audit.
