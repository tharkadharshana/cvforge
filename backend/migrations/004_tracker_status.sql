-- Migration 004: applications tracker_status
--
-- Application tracking (applied/interview/offer/etc) is a separate concept
-- from the generation pipeline's `status` column (pending|tailored|covered|
-- done|failed) — do not repurpose that column, generate.py's step guards
-- depend on it. This adds a second, independent status alongside it.
--
-- Idempotent: safe to re-run.

ALTER TABLE applications ADD COLUMN IF NOT EXISTS tracker_status VARCHAR(20) NOT NULL DEFAULT 'not_applied';
ALTER TABLE applications ADD COLUMN IF NOT EXISTS tracker_updated_at TIMESTAMPTZ;
