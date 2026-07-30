-- Migration 007: interview prep coaching, cached per application.
--
-- Idempotent: safe to re-run.

ALTER TABLE applications ADD COLUMN IF NOT EXISTS interview_prep JSONB;
