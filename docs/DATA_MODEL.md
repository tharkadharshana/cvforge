# Data Model

See [schema.sql](schema.sql) for the full DDL.

## Tables

### `users`
One row per account.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| email | VARCHAR(255) UNIQUE | login |
| hashed_password | VARCHAR(255) | bcrypt/passlib hash |
| full_name | VARCHAR(255) | default "" |
| credits | INTEGER | current balance, default 0 |
| plan | VARCHAR(50) | "free" or a `plan.id` from `BILLING_PLANS_JSON` |
| polar_customer_id | VARCHAR(255) NULL | set after first Polar purchase |
| is_admin | BOOLEAN | grants `/admin/*` access |
| monthly_refill_at | DATETIME NULL | next refill date (forever_free mode) |
| created_at | DATETIME | |

Relationships: 1:1 `base_cvs`, 1:N `applications`, `credit_ledger`, `payments`.

### `base_cvs`
One row per user — the canonical "master" CV.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK -> users.id, UNIQUE | |
| data | JSON | `CVData` shape (see below) |
| updated_at | DATETIME | auto-updated |

### `applications`
One row per `/generate` call — a tailored CV + cover letter for one job.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK -> users.id, indexed | |
| job_title | VARCHAR(255) | |
| company | VARCHAR(255) | |
| job_description | TEXT | original JD pasted/fetched |
| tailored_cv | JSON | `CVData` shape, tailored for this JD |
| cover_letter | TEXT | |
| ats_score | INTEGER | 0-100 from critic LLM |
| critique | JSON | `CritiqueOut` shape |
| created_at | DATETIME | |

### `credit_ledger`
Append-only audit trail of every credit grant/spend.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK -> users.id, indexed | |
| delta | INTEGER | positive = granted, negative = spent |
| reason | VARCHAR(80) | e.g. `signup_trial`, `generation`, `monthly_refill`, `purchase:<plan>`, `admin:<reason>` |
| balance_after | INTEGER | snapshot of `users.credits` after this delta |
| ref | VARCHAR(255) | e.g. application id, order id, `admin:<email>` |
| created_at | DATETIME | |

### `payments`
One row per confirmed Polar order (idempotent on `provider_ref`).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK -> users.id, indexed | |
| provider | VARCHAR(40) | "polar" |
| provider_ref | VARCHAR(255) UNIQUE | Polar order id (dedup key) |
| plan_id | VARCHAR(50) | matches `BILLING_PLANS_JSON[].id` |
| amount_usd | FLOAT | |
| credits | INTEGER | credits granted by this payment |
| status | VARCHAR(20) | default "paid" |
| created_at | DATETIME | |

### `audit_events`
Durable log of meaningful actions (auth, CV edits, generations, billing, admin).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK -> users.id, NULL, indexed | NULL for unauthenticated events (e.g. failed login of unknown email) |
| request_id | VARCHAR(16) | correlates to `X-Request-ID` |
| event | VARCHAR(60), indexed | e.g. `register`, `login`, `login_failed`, `cv_import`, `generate`, `webhook_received`, `purchase`, `admin_credit_adjust` |
| status | VARCHAR(20) | `ok` \| `failed` \| `blocked` \| `rejected` |
| ip | VARCHAR(64) | |
| meta | JSON | non-PII context |
| created_at | DATETIME, indexed | |

---

## `CVData` JSON shape (used in `base_cvs.data` and `applications.tailored_cv`)

```jsonc
{
  "contact": {
    "full_name": "", "email": "", "phone": "", "location": "",
    "linkedin": "", "github": "", "website": ""
  },
  "summary": "",
  "skills": { "Languages": ["Python", "Go"], "...category": ["..."] },
  "experience": [
    { "title": "", "company": "", "location": "", "start": "", "end": "", "bullets": ["..."] }
  ],
  "projects": [
    { "name": "", "description": "", "tech": ["..."], "bullets": ["..."], "link": "" }
  ],
  "education": [
    { "degree": "", "institution": "", "location": "", "start": "", "end": "", "details": ["..."] }
  ],
  "certifications": ["..."],
  "awards": ["..."],
  "languages": ["..."]
}
```

`CritiqueOut` shape (in `applications.critique`):
```jsonc
{
  "ats_score": 0,
  "keyword_matches": ["..."],
  "missing_keywords": ["..."],
  "human_tone_notes": ["..."],
  "suggestions": ["..."]
}
```

## Entity relationship summary

```
users 1───1 base_cvs
users 1───N applications
users 1───N credit_ledger
users 1───N payments
users 1───N audit_events (nullable user_id)
```
