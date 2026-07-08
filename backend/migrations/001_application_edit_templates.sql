-- Migration 001: manual editing + template selection (Features 1 & 2)
--
-- The app auto-creates tables only for the local SQLite dev DB (see app/main.py);
-- the production Supabase Postgres schema is migrated by hand. Run this once against
-- the production database when deploying the templates/editing/jobs features.
--
-- Idempotent: safe to re-run.

ALTER TABLE applications ADD COLUMN IF NOT EXISTS ats_stale BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS template_id VARCHAR(50) NOT NULL DEFAULT 'ats_classic';
ALTER TABLE applications ADD COLUMN IF NOT EXISTS template_overrides JSONB;
