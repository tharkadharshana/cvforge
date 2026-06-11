# Architecture

## Stack

| Layer    | Tech |
|----------|------|
| Backend  | FastAPI + SQLAlchemy 2.0 (declarative `Mapped`) + JWT auth (`python-jose`/passlib style) |
| Database | SQLite by default (`cvforge.db`), MySQL via `DATABASE_URL` |
| Frontend | React 18 + React Router 6 + Vite 6 + Tailwind CSS |
| Renderers| `python-docx` + `fpdf2` — pure Python, no system libs |
| LLMs     | DeepSeek + Gemini (Claude provider also available), roles configurable via env |
| Payments | Polar (Merchant of Record) — checkout, portal, webhooks |

## Project layout

```
backend/
  app/
    main.py            FastAPI app, CORS, request-id middleware, error handlers
    config.py          pydantic-settings — all env-driven config
    database.py        SQLAlchemy engine/session, Base
    models.py          ORM models (User, BaseCV, Application, CreditLedger, Payment, AuditEvent)
    schemas.py         Pydantic request/response models incl. canonical CVData shape
    auth.py            password hashing, JWT issue/verify, get_current_user/get_current_admin
    audit.py           audit.record(...) -> AuditEvent rows
    billing.py         credit ledger, plans, signup grants, monthly refill, purchase crediting
    logging_config.py  structured logging, request_id/client_ip context vars
    cv/
      pipeline.py      orchestrates parse/build/merge/generate via LLM providers
      prompts.py       LLM prompt templates
      extract.py       PDF/DOCX/TXT text extraction for CV uploads
      render.py        CVData -> PDF/DOCX (CV + cover letter)
    jobs/
      fetch.py         fetch + extract text from a job posting URL
    llm/
      base.py          LLMProvider ABC + safe JSON parsing of model output
      deepseek.py, gemini.py, claude.py   provider implementations
      orchestrator.py  drafter()/critic() resolve provider by role from config
    payments/
      polar.py         Polar checkout/portal/webhook verification
    routers/
      auth.py          /auth/register, /auth/login
      cv.py            /cv ... base CV CRUD, import, build, qualification merge
      generate.py      /generate, /applications...
      billing.py       /billing/...
      jobs.py          /jobs/fetch-url
      admin.py         /admin/... (support/investigation tools)

frontend/
  src/
    App.jsx, main.jsx
    lib/
      api.js           fetch wrapper + typed API client, JWT bearer auth
      auth.jsx         auth context/provider
      credits.jsx      credits/billing context
      cvstatus.jsx     base-CV status context
      theme.jsx        theme context
    pages/
      Landing, Login, Register, Onboarding, BaseCV, Generate,
      Applications, ApplicationDetail, Billing
    components/
      Layout.jsx, CVView.jsx, Questionnaire.jsx, ui.jsx
```

## Request flow (typical: tailor a CV)

1. User registers/logs in (`/auth/register`, `/auth/login`) -> JWT bearer token stored in `localStorage`.
2. User imports or builds their **base CV** (`/cv/import`, `/cv/import-file`, `/cv/build`, `PUT /cv`) -> stored as JSON in `base_cvs.data`.
3. User pastes a job description (optionally fetched via `/jobs/fetch-url`) and calls `POST /generate`.
4. Backend checks: base CV exists, user has credits (`billing.has_credits`).
5. `cv.pipeline.generate_application()` calls the **drafter** LLM (tailored CV + cover letter) and the **critic** LLM (ATS score, keyword gaps, tone notes).
6. Result saved as an `Application` row; one credit deducted (`billing.charge_generation`); `AuditEvent` recorded.
7. Frontend shows tailored CV, cover letter, and ATS critique; user can download PDF/DOCX via `/applications/{id}/download`.

## Cross-cutting concerns

- **CORS**: explicit origin allowlist (`app_url` + localhost dev origins) — required because `allow_credentials=True` forbids the `*` wildcard.
- **Request IDs**: every request gets a short `request_id` (in `X-Request-ID` response header and log lines) for tracing.
- **Audit log**: `audit_events` table records auth, CV edits, generations, billing events, admin actions — used by `/admin/audit` and `/admin/users/{id}`.
- **LLM provider abstraction**: `DRAFTER_PROVIDER` / `CRITIC_PROVIDER` env vars pick which model writes vs. critiques, so providers/models can be swapped without code changes.
