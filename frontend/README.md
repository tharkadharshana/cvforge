# CVForge — frontend

Vite + React + Tailwind SPA. Talks to the CVForge FastAPI backend.

## Run locally

```bash
npm install
cp .env.example .env        # set VITE_API_URL to your backend
npm run dev                 # http://localhost:5173
```

## Env

- `VITE_API_URL` — base URL of the deployed FastAPI backend, no trailing slash.
  Local: `http://localhost:8000`. Prod: e.g. `https://cvforge-backend.vercel.app`.

## Screens

- `/login`, `/register` — JWT auth (token in localStorage).
- `/cv` — Base CV: import raw text once, view structured, add qualifications over time.
- `/generate` — paste job description → tailored CV + cover letter + ATS critique.
- `/applications` — history; `/applications/:id` — detail + downloads (CV/letter × PDF/DOCX).

## Deploy to Vercel

1. Push repo. In Vercel, import it as a **separate project** from the backend.
2. **Root Directory** = `frontend`. Framework auto-detects **Vite**.
   Build = `npm run build`, Output = `dist` (defaults).
3. Add env var `VITE_API_URL` = your backend's Vercel URL (e.g.
   `https://cvforge-backend.vercel.app`, no trailing slash).
4. `vercel.json` already handles SPA routing (deep links don't 404).
5. After deploy, set `APP_URL` on the **backend** project to this frontend's
   URL and redeploy the backend (tightens CORS — see `../DEPLOY.md`).

Full step-by-step (including backend setup) is in `../DEPLOY.md`.
