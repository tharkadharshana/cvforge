-- Migration 003: applications.fit_score
--
-- Job fit scoring (POST /generate/fit-score) evaluates a job description
-- against the candidate's base CV before generation starts. When it's run
-- against an already-created generation job, the result is persisted here
-- so the application history keeps a record of why the user applied.
--
-- Idempotent: safe to re-run.

ALTER TABLE applications ADD COLUMN IF NOT EXISTS fit_score JSONB;
