# CVForge Autofill Assistant (browser extension)

A small Manifest V3 Chrome/Edge extension that fills job application forms with your
CVForge **tailored CV** so you don't retype the same fields on every site.

## What it does (and deliberately does not do)

- **Fills** the fields on the application form you're currently looking at (name, email,
  phone, links, current role, summary, cover letter, …).
- **Does not** click Submit. You review every field and submit on the site yourself.
- **Does not** touch LinkedIn's data or automate LinkedIn. It only serves *your own*
  tailored CV back to you. This keeps it compliant with each site's terms — the same
  fill-only model used by tools like Simplify and JobWizard.

> On LinkedIn Easy Apply specifically: the extension fills fields only. Use the per-job
> resume-upload step to attach your **tailored** CV (download it from CVForge first),
> then submit yourself.

## Install (unpacked, for development)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select this `extension/` folder.

## Use

1. In the CVForge web app, generate/open an application and note its **Application ID**
   (the number in the `/applications/{id}` URL).
2. Get your **access token**: in the web app, open DevTools → Application → Local Storage →
   copy the value of `cvforge_token`.
3. Click the extension icon and fill in:
   - **API base URL** — your backend, e.g. `https://cvforge-backend.vercel.app`
   - **Access token** — the token from step 2
   - **Application ID** — from step 1
4. Open a job application page and click **Autofill this page**. Review, attach your
   tailored CV/cover PDF (download links come from the same profile), and submit yourself.

## How it works

The popup fetches `GET /applications/{id}/autofill-profile` (bearer auth) and injects the
flat profile into the page via `content.js`, which heuristically matches form inputs by
their name/label/placeholder text. Nothing is submitted automatically.
