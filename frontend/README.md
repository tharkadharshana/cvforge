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
  Local: `http://localhost:8000`. Prod: e.g. `https://cvforge-api.up.railway.app`.

## Screens
- `/login`, `/register` — JWT auth (token in localStorage).
- `/cv` — Base CV: import raw text once, view structured, add qualifications over time.
- `/generate` — paste job description → tailored CV + cover letter + ATS critique.
- `/applications` — history; `/applications/:id` — detail + downloads (CV/letter × PDF/DOCX).

## Deploy to Vercel
1. Push repo. In Vercel, import it.
2. **Root Directory** = `frontend`. Framework auto-detects **Vite**.
   Build = `npm run build`, Output = `dist` (defaults).
3. Add env var `VITE_API_URL` = your backend URL.
4. `vercel.json` already handles SPA routing (deep links don't 404).
5. After deploy, set the backend CORS `allow_origins` to your Vercel domain.

Note: only the frontend goes on Vercel. The FastAPI backend runs elsewhere
(Railway / Render / Fly). See ../DEPLOY.md.
