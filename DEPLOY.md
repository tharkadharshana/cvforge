# CVForge — deploy guide

Two Vercel projects from the same repo:

- **`backend/`** (FastAPI) → Vercel project, Root Directory = `backend`. Uses Supabase
  Postgres (Supavisor pooler) via `DATABASE_URL`. Currently live at
  `https://cvforge-backend.vercel.app`.
- **`frontend/`** (Vite React SPA) → separate Vercel project, Root Directory = `frontend`.

---

## A. Backend (already deployed)

See `backend/README.md` → "Deploy notes (Vercel + Supabase)" for the full
explanation of `vercel.json`, the Supabase pooler URL format, and billing/Polar
setup. Quick summary:

1. New Vercel project, import this repo, **Root Directory = `backend`**,
   Framework Preset = **Other** (not "FastAPI" — `vercel.json` sets
   `"framework": null` and needs the classic per-file Python builder).
2. Add the Supabase integration (or bring your own Postgres) and set
   `DATABASE_URL` to the **pooler** URI (port 6543) in
   `postgresql+psycopg://...` form.
3. Set all other env vars (see `backend/.env.vercel` locally — gitignored,
   never commit it — for a ready-to-paste full set: `SECRET_KEY`,
   `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, billing/Polar vars, etc.)
4. Set `APP_URL` to the frontend's Vercel domain once you have it (step B.3) —
   this tightens CORS and sets the Polar checkout return URL. Redeploy after
   changing it.
5. Deploy. Verify with the smoke test (section C).

### Managing env vars in bulk

Vercel's **Project Settings → Environment Variables** has a "paste .env"
import box — paste the whole contents of a `.env`-formatted file and it splits
into individual `KEY=VALUE` rows for you to assign to Production/Preview/Dev.
To replace everything: delete the old vars one by one (trash icon per row, no
bulk-delete in the standard UI), then paste the new set. **Env var changes
require a redeploy** (Deployments tab → "..." on latest → Redeploy) to take
effect.

---

## B. Frontend — deploy to Vercel (A to Z)

1. **Push the repo to GitHub** (if not already) — Vercel deploys from a Git repo.
2. **Vercel dashboard → Add New → Project → Import** your `cvforge` repo.
3. **Configure the project**:
   - **Root Directory**: click "Edit" → select `frontend`.
   - **Framework Preset**: Vercel auto-detects **Vite**. Leave Build Command
     (`npm run build` / `vite build`) and Output Directory (`dist`) as
     defaults — `frontend/package.json` and `frontend/vercel.json` already
     match these.
4. **Add the environment variable** (Settings → Environment Variables, or in
   the "Configure Project" screen before first deploy):
   - `VITE_API_URL` = `https://cvforge-backend.vercel.app` (no trailing slash)
   - Apply to Production, Preview, and Development.
5. **Deploy**. Vercel builds `npm run build` and serves `frontend/dist`.
   `frontend/vercel.json` rewrites all paths to `/` so React Router deep links
   (e.g. `/applications/3`) don't 404 on refresh.
6. **Note the deployed URL**, e.g. `https://cvforge-frontend.vercel.app` (or
   your custom domain).
7. **Update backend CORS**: go back to the **backend** Vercel project → Settings
   → Environment Variables → set `APP_URL` to the frontend URL from step 6 →
   Redeploy the backend. (`app/main.py` builds `allow_origins` from `APP_URL`
   plus localhost dev origins — without this step the deployed frontend's
   `fetch()` calls will be blocked by CORS.)
8. **Smoke test the frontend**: open the deployed URL, register a user, import
   a CV, paste a job description on the Generate screen, and download the
   resulting PDF/DOCX. This is the same flow the backend smoke test
   automates (section C) but exercised through the UI.

### Custom domain (optional)

Vercel Project → Settings → Domains → add your domain, follow the DNS
instructions. If you do this for the frontend, also update `APP_URL` on the
backend (step 7) to the custom domain and redeploy.

---

## C. Automated smoke test (CI/CD)

`backend/scripts/smoke-test.sh` runs the full user journey against a **live
deployment**: register → login → CV import (LLM) → 4-step generation pipeline
(LLM, tailor/cover/critique) → credit deduction check → PDF + DOCX download.
It's the script form of the manual verification done after each backend deploy.

Run it locally against any deployment:

```bash
BASE_URL=https://cvforge-backend.vercel.app backend/scripts/smoke-test.sh
```

Requires `curl` and `jq`. Exits non-zero on the first failed step, with a
`PASS:`/`FAIL:` line per check.

### GitHub Actions workflow

`.github/workflows/smoke-test.yml` runs this script:

- **Manually** via the Actions tab → "Backend smoke test (deployed)" → "Run
  workflow" (optionally override the target URL) — run this right after a
  backend deploy.
- **Weekly** (Monday 06:00 UTC) as a regression check that the live deployment,
  Supabase DB, and both LLM providers (DeepSeek + Gemini) are still healthy.

It's deliberately **not** run on every push: each run creates a real user,
makes real LLM calls, and spends 1 real credit. The existing
`.github/workflows/ci.yml` (unit tests + build, on every push/PR) is the fast
feedback loop; this smoke test is the "is production actually alive" check.

### What's covered vs. what isn't

| Layer | Covered by |
|---|---|
| Backend unit tests (auth, credits, webhooks, renderers, extraction) | `ci.yml` → `pytest` (every push/PR) |
| Frontend build (`vite build` succeeds) | `ci.yml` → `npm run build` (every push/PR) |
| Live backend: DB, auth, both LLM providers, full generation pipeline, billing, downloads | `smoke-test.yml` → `smoke-test.sh` (manual / weekly) |
| Live frontend UI | Manual (section B.8) — no automated browser test yet |

---

## Still TODO for production SaaS

- Rate limiting + async job queue for long generations.
- Automated frontend E2E test (e.g. Playwright) against the deployed UI.
