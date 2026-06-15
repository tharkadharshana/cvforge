#!/usr/bin/env bash
# End-to-end smoke test for a deployed CVForge backend.
#
# Exercises the full user journey against a live deployment: register, login,
# CV import (LLM), the 4-step generation pipeline (LLM), credit deduction,
# applications list, and PDF/DOCX downloads.
#
# Usage:
#   BASE_URL=https://cvforge-backend.vercel.app ./smoke-test.sh
#
# Exits non-zero on the first failed step. Requires: curl, jq.

set -euo pipefail

BASE_URL="${BASE_URL:-https://cvforge-backend.vercel.app}"
BASE_URL="${BASE_URL%/}"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

req() {
  # req METHOD PATH [curl-extra-args...] -> writes status to $STATUS, body to $BODY
  local method="$1" path="$2"; shift 2
  local tmp; tmp="$(mktemp)"
  STATUS=$(curl -s -o "$tmp" -w "%{http_code}" -X "$method" "$BASE_URL$path" "$@")
  BODY="$(cat "$tmp")"
  rm -f "$tmp"
}

EMAIL="smoketest.$(date +%s)@cvforge.dev"
PASSWORD="SmokeTest123!"

echo "Target: $BASE_URL"
echo "Test user: $EMAIL"
echo

# 1. App is up
req GET /openapi.json
[ "$STATUS" = "200" ] || fail "openapi.json -> $STATUS"
pass "app is up (openapi.json)"

# 2. Register
req POST /auth/register -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Smoke Test\"}"
[ "$STATUS" = "201" ] || fail "register -> $STATUS: $BODY"
pass "register"

# 3. Login
req POST /auth/login \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD"
[ "$STATUS" = "200" ] || fail "login -> $STATUS: $BODY"
TOKEN=$(echo "$BODY" | jq -r .access_token)
[ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] || fail "login: no access_token in $BODY"
pass "login"

AUTH=(-H "Authorization: Bearer $TOKEN")

# 4. CV status (fresh user -> no base CV yet)
req GET /cv/status "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "cv/status -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .has_base_cv)" = "false" ] || fail "cv/status: expected has_base_cv=false, got $BODY"
pass "cv/status (no base CV yet)"

# 5. Billing summary -> trial credits granted
req GET /billing/summary "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "billing/summary -> $STATUS: $BODY"
CREDITS_BEFORE=$(echo "$BODY" | jq -r .credits)
[ "$CREDITS_BEFORE" -gt 0 ] || fail "billing/summary: expected credits > 0, got $BODY"
pass "billing/summary (credits=$CREDITS_BEFORE)"

# 6. Import a CV (LLM call: parses raw text -> structured CV)
CV_TEXT="John Doe\nSoftware Engineer\n5 years experience in Python, FastAPI, React, and AWS.\nWorked at TechCorp 2019-2024 building backend APIs.\nBSc Computer Science, University of Colombo, 2019."
req POST /cv/import "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"raw_text\":\"$CV_TEXT\"}"
[ "$STATUS" = "200" ] || fail "cv/import -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r '.experience | length')" -gt 0 ] || fail "cv/import: no experience parsed: $BODY"
pass "cv/import (LLM parse)"

# 7. Start a generation job
JD="We are looking for a Software Engineer with strong Python and FastAPI experience, AWS cloud knowledge, and React frontend skills."
req POST /generate/start "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"job_description\":\"$JD\",\"company\":\"Acme Inc\",\"job_title\":\"Software Engineer\"}"
[ "$STATUS" = "200" ] || fail "generate/start -> $STATUS: $BODY"
JOB_ID=$(echo "$BODY" | jq -r .job_id)
[ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ] || fail "generate/start: no job_id in $BODY"
pass "generate/start (job_id=$JOB_ID)"

# 8. Tailor (LLM call)
req POST "/generate/$JOB_ID/tailor" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "generate/tailor -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .status)" = "tailored" ] || fail "generate/tailor: unexpected status: $BODY"
pass "generate/tailor (LLM)"

# 9. Cover letter (LLM call)
req POST "/generate/$JOB_ID/cover" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "generate/cover -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .status)" = "covered" ] || fail "generate/cover: unexpected status: $BODY"
pass "generate/cover (LLM)"

# 10. Critique + ATS score (LLM call; charges 1 credit)
req POST "/generate/$JOB_ID/critique" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "generate/critique -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .status)" = "done" ] || fail "generate/critique: unexpected status: $BODY"
APPLICATION_ID=$(echo "$BODY" | jq -r .application_id)
ATS_SCORE=$(echo "$BODY" | jq -r .ats_score)
pass "generate/critique (LLM, application_id=$APPLICATION_ID, ats_score=$ATS_SCORE)"

# 11. Credit was deducted exactly once
req GET /billing/summary "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "billing/summary (after) -> $STATUS: $BODY"
CREDITS_AFTER=$(echo "$BODY" | jq -r .credits)
[ "$CREDITS_AFTER" -eq $((CREDITS_BEFORE - 1)) ] || fail "billing: expected $((CREDITS_BEFORE - 1)) credits, got $CREDITS_AFTER"
pass "billing/summary (credit deducted: $CREDITS_BEFORE -> $CREDITS_AFTER)"

# 12. Applications list
req GET /applications "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "applications -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq "length")" -gt 0 ] || fail "applications: expected at least 1, got $BODY"
pass "applications list"

# 13. Download CV as PDF
PDF_FILE="$(mktemp)"
STATUS=$(curl -s -o "$PDF_FILE" -w "%{http_code}" "${AUTH[@]}" \
  "$BASE_URL/applications/$APPLICATION_ID/download?doc=cv&fmt=pdf")
[ "$STATUS" = "200" ] || fail "download cv pdf -> $STATUS"
head -c4 "$PDF_FILE" | grep -q "%PDF" || fail "download cv pdf: not a PDF"
rm -f "$PDF_FILE"
pass "download CV (PDF)"

# 14. Download cover letter as DOCX
DOCX_FILE="$(mktemp)"
STATUS=$(curl -s -o "$DOCX_FILE" -w "%{http_code}" "${AUTH[@]}" \
  "$BASE_URL/applications/$APPLICATION_ID/download?doc=cover&fmt=docx")
[ "$STATUS" = "200" ] || fail "download cover docx -> $STATUS"
head -c2 "$DOCX_FILE" | grep -q "PK" || fail "download cover docx: not a zip/docx"
rm -f "$DOCX_FILE"
pass "download cover letter (DOCX)"

echo
echo "All smoke tests passed against $BASE_URL"
