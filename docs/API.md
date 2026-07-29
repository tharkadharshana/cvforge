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

`CVData` also carries a `style_profile` (`{ tone, dos, donts, avoid_phrases }`) —
user-declared writing preferences, edited via `PUT /cv` like the rest of the base
CV. Spliced into the `tailor_cv`/`cover_letter` system prompts when present.

---

## Job fit scoring

### `POST /generate/fit-score`

Body: `{ "job_description": str (min 20), "job_id": int | null }`

Scores a job description against the user's base CV across 5 weighted
dimensions before generation starts. Free — no credit charge. If `job_id`
refers to an existing `Application` owned by the user, the result is also
persisted onto `applications.fit_score`.

Returns:
```json
{
  "score": 0,
  "dimensions": { "skills_match": 0, "experience_level": 0, "culture_fit": 0, "location": 0, "career_alignment": 0 },
  "deal_breakers": [],
  "strengths": [],
  "gaps": [],
  "recommendation": "STRONG_MATCH | GOOD_MATCH | WEAK_MATCH | SKIP"
}
```
Deal-breakers cap `score` at 30 and force `recommendation: "SKIP"`. When a
job's `fit_score` is already stored, `tailor`/`cover` splice its
strengths/gaps into their prompts. Errors: `400` no base CV, `502` LLM failure.

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

### `GET /applications?tracker_status=`
List of past applications (id, job_title, company, ats_score, created_at,
tracker_status, tracker_updated_at), newest first. Optional `tracker_status`
query param filters to one status.

### `GET /applications/stats`
`{ status: count, ... }` — counts of the caller's applications grouped by
`tracker_status`.

### `GET /applications/{app_id}`
Full record: tailored_cv, cover_letter, ats_score, critique, tracker_status.

### `PATCH /applications/{app_id}/tracker`
Body: `{ "tracker_status": str }` — one of `not_applied`, `applied`,
`screening`, `interview_1`, `interview_2`, `offer`, `hired`, `rejected`,
`withdrawn`, `ghosted`. Separate from the generation pipeline's internal
`status` field (`pending|tailored|covered|done|failed`) — this only tracks
what happened after the CV was sent. Stamps `tracker_updated_at`.

### `GET /applications/{app_id}/verify`
Deterministic (non-LLM) check that the rendered CV PDF's text layer is
machine-readable: contact details present as literal text, no garbled
characters, section headings in the expected order. Combined with the
keyword coverage already computed by the critique step. Free — no credit
charge, reuses `pdfplumber` (already a dependency) instead of poppler/pdftotext.

Returns:

```json
{ "machine_readable": true, "issues": [], "keyword_matches": [], "missing_keywords": [] }
```

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
