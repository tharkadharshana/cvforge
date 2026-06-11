# Local Development Setup

## Prerequisites

- Python 3.11+ (a `.venv` already exists in `backend/`)
- Node.js 18+ / npm

## Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env   # then fill in SECRET_KEY + provider keys
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs
- `dev.ps1` is a shortcut for the uvicorn command above.

### Database

- Default: SQLite file `backend/cvforge.db`, created automatically via
  `Base.metadata.create_all()` on startup.
- **Important**: `create_all()` only creates *missing tables* — it never adds
  columns to an existing table. If you pull model changes that add columns to
  an existing table (e.g. `users`), apply the equivalent `ALTER TABLE`
  manually (see [schema.sql](schema.sql) for the full current shape) or
  delete `cvforge.db` to start fresh (loses local data).
- For MySQL, set `DATABASE_URL=mysql+pymysql://user:pass@host:3306/cvforge` in `.env`.

### Key environment variables (see `.env.example` for the full list)

| Var | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret — set a long random string |
| `DATABASE_URL` | SQLite (default) or MySQL connection string |
| `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` | LLM provider credentials |
| `DRAFTER_PROVIDER` / `CRITIC_PROVIDER` | which provider drafts vs. critiques (`gemini` \| `deepseek`) |
| `ADMIN_EMAILS` | comma-separated emails granted `/admin/*` access |
| `BILLING_ENABLED`, `FREE_TIER_MODE`, `CREDITS_PER_GENERATION` | credit system |
| `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`, `POLAR_SERVER` | Polar payment gateway |
| `APP_URL` | frontend origin — used for CORS allowlist + checkout return URL |

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

- Dev server: http://localhost:5173
- API base URL is read from `VITE_API_URL` (defaults to `http://localhost:8000`).

## CORS note

`app/main.py` allows credentials, so `allow_origins` **must** be an explicit
list (wildcard `"*"` is rejected by browsers when `allow_credentials=True`).
The allowlist is `{settings.app_url, "http://localhost:5173", "http://127.0.0.1:5173"}`.
If you serve the frontend from a different origin, add it via `APP_URL`.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```
