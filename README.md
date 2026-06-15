# CVForge — backend

Multi-user SaaS. Stores one structured base CV per user. Generates ATS-friendly,
job-tailored CV + human-sounding cover letter as DOCX and PDF. Uses DeepSeek + Gemini.

## Stack
FastAPI + SQLAlchemy + JWT auth. SQLite default, MySQL via `DATABASE_URL`.
Renderers pure-python (`python-docx`, `fpdf2`) — no system libs, cloud-friendly.

## Run (backend + frontend)

First-time setup:

```bash
cd backend && pip install -r requirements.txt && cp .env.example .env  # fill SECRET_KEY + provider keys
cd ../frontend && npm install
```

Then, from the project root, start both with one command (opens two windows):

```powershell
Start-Process powershell -ArgumentList '-NoExit','-Command','cd backend; uvicorn app.main:app --reload' ; Start-Process powershell -ArgumentList '-NoExit','-Command','cd frontend; npm run dev'
```

Backend docs at <http://localhost:8000/docs>, frontend at the URL Vite prints (usually <http://localhost:5173>).

## LLM roles (env)
- `DRAFTER_PROVIDER` writes tailored CV + cover letter.
- `CRITIC_PROVIDER` (the other model) scores ATS fit + flags AI-sounding tone.
- Defaults: drafter=gemini (`gemini-3.5-flash`/`gemini-3.1-pro`), critic=deepseek (`deepseek-v4-flash`/`deepseek-v4-pro`).
- Swap freely. Models are env-config so no code change when names change.

## Flow / endpoints
1. `POST /auth/register`, `POST /auth/login` -> bearer token.
2. `POST /cv/import` {raw_text} — paste current CV once, parsed into structured base CV.
3. `POST /cv/qualification` {text} — dump new qualification anytime, merged into base CV.
4. `PUT /cv` — direct structured edit / manual correction.
5. `GET /cv` — current base CV.
6. `POST /generate` {job_description, company, job_title} -> tailored CV + cover letter + ATS critique. Saved as an Application.
7. `GET /applications`, `GET /applications/{id}`.
8. `GET /applications/{id}/download?doc=cv|cover&fmt=pdf|docx` — download files.

## ATS rules baked into renderers
Single column, standard headings, real selectable text, no tables/graphics/text-boxes,
common fonts. The tailoring prompt mirrors JD keywords and forbids fabrication.

## Deploy notes (cloud)
- Set `DATABASE_URL` to managed MySQL. Set a strong `SECRET_KEY`.
- Tighten CORS `allow_origins` to the frontend domain.
- Containerise: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- For SaaS billing/usage metering + per-user rate limits: add next iteration.

## TODO (next iterations)
- React frontend.
- Billing + usage meter (credits/tokens) per user.
- Dockerfile + cloud deploy config.
- PDF template variants / DOCX styling themes.
- Async generation + job queue for long JDs.
