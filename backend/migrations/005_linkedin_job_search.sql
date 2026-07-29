-- Migration 005: LinkedIn job discovery tables
--
-- Off by default (LINKEDIN_SEARCH_ENABLED unset) — see docs/LEGAL_NOTES.md
-- before enabling. Only run this if you intend to turn the feature on.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS linkedin_jobs_cache (
  job_id VARCHAR(40) PRIMARY KEY,
  title VARCHAR(255) NOT NULL DEFAULT '',
  company VARCHAR(255) NOT NULL DEFAULT '',
  location VARCHAR(255) NOT NULL DEFAULT '',
  posted_at VARCHAR(40) NOT NULL DEFAULT '',
  url VARCHAR(500) NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  description_hash VARCHAR(64) NOT NULL DEFAULT '',
  criteria JSONB NOT NULL DEFAULT '{}',
  cached_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_search_preferences (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
  keywords JSONB NOT NULL DEFAULT '[]',
  location VARCHAR(255) NOT NULL DEFAULT '',
  experience_level VARCHAR(20) NOT NULL DEFAULT '',
  time_filter VARCHAR(20) NOT NULL DEFAULT 'week',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_search_results (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  job_id VARCHAR(40) NOT NULL REFERENCES linkedin_jobs_cache(job_id),
  search_keywords VARCHAR(255) NOT NULL DEFAULT '',
  saved BOOLEAN NOT NULL DEFAULT FALSE,
  dismissed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_job_search_results_user_job UNIQUE (user_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_job_search_results_user_id ON job_search_results (user_id);
CREATE INDEX IF NOT EXISTS ix_job_search_results_job_id ON job_search_results (job_id);

CREATE TABLE IF NOT EXISTS job_search_usage (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  date VARCHAR(10) NOT NULL,
  search_count INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT uq_job_search_usage_user_date UNIQUE (user_id, date)
);
CREATE INDEX IF NOT EXISTS ix_job_search_usage_user_id ON job_search_usage (user_id);
