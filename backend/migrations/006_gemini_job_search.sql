-- Migration 006: Gemini job discovery (google_search grounding).
--
-- Auto-enabled whenever GEMINI_API_KEY is configured -- no ToS-risk opt-in
-- flag needed like migration 005's LinkedIn tables. Fully separate from the
-- LinkedIn tables by design: independent quota, independent cache, so the
-- two job sources can't interfere with each other.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS gemini_jobs_cache (
  job_id VARCHAR(64) PRIMARY KEY,
  title VARCHAR(255) NOT NULL DEFAULT '',
  company VARCHAR(255) NOT NULL DEFAULT '',
  location VARCHAR(255) NOT NULL DEFAULT '',
  posted_at VARCHAR(40) NOT NULL DEFAULT '',
  url VARCHAR(500) NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  cached_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gemini_search_usage (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  date VARCHAR(10) NOT NULL,
  search_count INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT uq_gemini_search_usage_user_date UNIQUE (user_id, date)
);
CREATE INDEX IF NOT EXISTS ix_gemini_search_usage_user_id ON gemini_search_usage (user_id);

CREATE TABLE IF NOT EXISTS gemini_search_results (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  job_id VARCHAR(64) NOT NULL REFERENCES gemini_jobs_cache(job_id),
  search_keywords VARCHAR(255) NOT NULL DEFAULT '',
  saved BOOLEAN NOT NULL DEFAULT FALSE,
  dismissed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_gemini_search_results_user_job UNIQUE (user_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_gemini_search_results_user_id ON gemini_search_results (user_id);
CREATE INDEX IF NOT EXISTS ix_gemini_search_results_job_id ON gemini_search_results (job_id);
