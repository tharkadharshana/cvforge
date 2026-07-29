# Legal notes (internal — not a substitute for a lawyer)

## Job listing sourcing

CVForge surfaces job listings from third-party public web sources (Adzuna's
API, and optionally LinkedIn's public/unauthenticated `jobs-guest` pages).

**What a Terms of Service clause can and cannot do here:**
- It can tell *your users* that listings are sourced from third parties,
  provided "as-is," and that they should verify details on the original
  posting before applying. That's a normal, useful disclaimer.
- It **cannot** protect CVForge from LinkedIn (or any source site) pursuing
  a claim against CVForge directly for violating *their* Terms of Service.
  Your users are not a party to LinkedIn's ToS — you are, the moment your
  server requests their pages. No wording in *your* ToS changes that.

If LinkedIn scraping is enabled, treat the legal exposure (ToS/breach-of-
contract risk, not a user-facing risk) as a real, standing business
decision — not something resolved by adding text below. Get an actual
lawyer's read before relying on this at scale.

## Draft clause (starting point only — have a lawyer review before publishing)

> **Job Listings.** Job listings displayed through the Service are sourced
> from third-party job boards and publicly accessible web pages, including
> but not limited to Adzuna and LinkedIn. CVForge does not control, verify,
> or guarantee the accuracy, completeness, or continued availability of
> any listing. Listings are provided "as is" for your convenience only.
> You are solely responsible for verifying job details, including
> application instructions, directly with the original source or employer
> before applying. CVForge is not affiliated with, endorsed by, or
> sponsored by LinkedIn Corporation or any third-party job board.

## Where this lives today

- No public Terms of Service page exists yet in this repo (checked
  `frontend/src/pages/` and `docs/` — neither has one). This clause is a
  starting point for whenever one is drafted, not a replacement for one.
- An in-product disclaimer banner was added directly to the job search UI
  (see `frontend/src/pages/JobSearch.jsx`) so users see the sourcing
  disclosure at the point of use, independent of whether a formal ToS page
  exists yet.
