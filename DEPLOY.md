# CVForge — deploy guide

Two pieces, two hosts:

- **frontend/** (Vite React SPA) → **Vercel**
- **backend/** (FastAPI) → **Railway / Render / Fly** (Vercel can't run it well)

## Why not backend on Vercel
Vercel is serverless. FastAPI here uses a long-lived process, a SQL connection
pool, and slow LLM calls (DeepSeek/Gemini) — a poor fit for short-lived functions.
Run it on a normal container host. Frontend on Vercel is the right split.

## 1. Backend (Railway example)
1. New project → deploy `backend/` from repo.
2. Add a MySQL plugin (or use SQLite for a quick test — not for real multi-user).
3. Set env vars (from `backend/.env.example`):
   - `SECRET_KEY` (long random string)
   - `DATABASE_URL` = `mysql+pymysql://user:pass@host:3306/cvforge`
   - `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`
   - `DRAFTER_PROVIDER`, `CRITIC_PROVIDER` (defaults: gemini / deepseek)
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Note the public URL, e.g. `https://cvforge-api.up.railway.app`.

## 2. Frontend (Vercel)
1. Import repo. **Root Directory** = `frontend`. Preset = Vite.
2. Env var `VITE_API_URL` = the backend URL from step 1 (no trailing slash).
3. Deploy. `vercel.json` handles SPA deep-link routing.

## 3. Wire CORS
In `backend/app/main.py`, replace `allow_origins=["*"]` with your Vercel domain:
```python
allow_origins=["https://your-app.vercel.app"]
```
Redeploy backend.

## Smoke test after deploy
Register → import a CV → paste a JD on Generate → download the PDF/DOCX.

## Still TODO for production SaaS
- Billing + per-user usage meter (token/credits).
- Rate limiting + async job queue for long generations.
- Dockerfile (optional; most hosts build from requirements.txt directly).
