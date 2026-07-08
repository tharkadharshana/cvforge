-- Migration 002: index audit_events.ip
--
-- The public ATS checker's per-IP daily quota counts audit rows by
-- (event, ip, created_at); without an index on ip that count scans the
-- table. Run once against production Postgres when deploying the checker.
--
-- Idempotent: safe to re-run.

CREATE INDEX IF NOT EXISTS ix_audit_events_ip ON audit_events (ip);
