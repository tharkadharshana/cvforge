#!/usr/bin/env bash
# End-to-end smoke test for a deployed CVForge backend.
#
# Exercises the full user journey against a live deployment: register, login,
# base CV + writing style profile, job fit scoring, the 4-step generation
# pipeline (LLM), credit deduction, application tracker, ATS text-layer
# verification, PDF/DOCX downloads, and billing/subscription (checkout,
# webhook credit grants, idempotency, signature security, subscription
# cancellation).
#
# Usage:
#   BASE_URL=https://cvforge-backend.vercel.app ./smoke-test.sh
#
# Optional env:
#   POLAR_WEBHOOK_SECRET — same secret configured on the deployment. If set,
#     webhook-driven billing steps (credit grant, idempotency, forged/unsigned
#     rejection, subscription cancel) are exercised by signing payloads
#     locally and POSTing them to /billing/webhook — no real Polar payment is
#     completed. If unset, those steps are skipped (not failed).
#
# What this does NOT cover (needs a human / admin access, run those via the
# local `pytest` suite instead — see backend/tests/test_billing.py):
#   - out-of-credits blocking (needs an admin account to drain credits)
#   - completing a real Polar checkout (needs a browser + test card)
#
# Exits non-zero on the first failed step. Requires: curl, jq, python3 (or python).

set -euo pipefail

BASE_URL="${BASE_URL:-https://cvforge-backend.vercel.app}"
BASE_URL="${BASE_URL%/}"

# Pick whichever of python3/python actually has standardwebhooks importable —
# a machine can have more than one Python on PATH with the package in only one.
PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import standardwebhooks" >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }
skip() { echo "SKIP: $1"; }

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

# 6. Fit scoring blocked before a base CV exists
req POST /generate/fit-score "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"job_description":"We need a Software Engineer with Python and AWS experience for a growing team."}'
[ "$STATUS" = "400" ] || fail "fit-score (no base CV) -> expected 400, got $STATUS: $BODY"
pass "fit-score blocked without a base CV"

# 7. Import a CV (LLM call: parses raw text -> structured CV)
CV_TEXT="John Doe\nSoftware Engineer\n5 years experience in Python, FastAPI, React, and AWS.\nWorked at TechCorp 2019-2024 building backend APIs.\nBSc Computer Science, University of Colombo, 2019."
req POST /cv/import "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"raw_text\":\"$CV_TEXT\"}"
[ "$STATUS" = "200" ] || fail "cv/import -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r '.experience | length')" -gt 0 ] || fail "cv/import: no experience parsed: $BODY"
IMPORTED_CV="$BODY"   # save before any other req() call overwrites $BODY
pass "cv/import (LLM parse)"

# cv/import charges 1 credit (same charge_generation() as the main pipeline) —
# distinct from the 1 credit the generation pipeline charges later.
req GET /billing/summary "${AUTH[@]}"
CREDITS_AFTER_IMPORT=$(echo "$BODY" | jq -r .credits)
[ "$CREDITS_AFTER_IMPORT" -eq $((CREDITS_BEFORE - 1)) ] || fail "cv/import: expected $((CREDITS_BEFORE - 1)) credits after import charge, got $CREDITS_AFTER_IMPORT"
pass "cv/import charged 1 credit ($CREDITS_BEFORE -> $CREDITS_AFTER_IMPORT)"

# 8. Writing style profile: set via PUT /cv, verify it round-trips via GET /cv
CV_JSON=$(echo "$IMPORTED_CV" | jq '.style_profile = {"tone":"confident","dos":["Use specific numbers and metrics"],"donts":["Never say team player"],"avoid_phrases":["synergy"]}')
req PUT /cv "${AUTH[@]}" -H "Content-Type: application/json" -d "$CV_JSON"
[ "$STATUS" = "200" ] || fail "cv PUT (style_profile) -> $STATUS: $BODY"
req GET /cv "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "cv GET -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .style_profile.tone)" = "confident" ] || fail "style_profile did not round-trip: $BODY"
pass "writing style profile (round-trip)"

# 9. Job fit scoring (LLM call), free, no job_id yet
JD="We are looking for a Software Engineer with strong Python and FastAPI experience, AWS cloud knowledge, and React frontend skills."
req POST /generate/fit-score "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"job_description\":\"$JD\"}"
[ "$STATUS" = "200" ] || fail "fit-score -> $STATUS: $BODY"
RECOMMENDATION=$(echo "$BODY" | jq -r .recommendation)
echo "$RECOMMENDATION" | grep -qE "STRONG_MATCH|GOOD_MATCH|WEAK_MATCH|SKIP" || fail "fit-score: unexpected recommendation: $BODY"
pass "generate/fit-score (LLM, recommendation=$RECOMMENDATION)"

# 10. Start a generation job
req POST /generate/start "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"job_description\":\"$JD\",\"company\":\"Acme Inc\",\"job_title\":\"Software Engineer\"}"
[ "$STATUS" = "200" ] || fail "generate/start -> $STATUS: $BODY"
JOB_ID=$(echo "$BODY" | jq -r .job_id)
[ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ] || fail "generate/start: no job_id in $BODY"
pass "generate/start (job_id=$JOB_ID)"

# 11. Fit score persisted onto the job when job_id is passed
req POST /generate/fit-score "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"job_description\":\"$JD\",\"job_id\":$JOB_ID}"
[ "$STATUS" = "200" ] || fail "fit-score (with job_id) -> $STATUS: $BODY"
pass "generate/fit-score persisted onto job $JOB_ID"

# 12. Tailor (LLM call; feeds style_profile + fit_score into the prompt)
req POST "/generate/$JOB_ID/tailor" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "generate/tailor -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .status)" = "tailored" ] || fail "generate/tailor: unexpected status: $BODY"
pass "generate/tailor (LLM)"

# 13. Cover letter (LLM call)
req POST "/generate/$JOB_ID/cover" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "generate/cover -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .status)" = "covered" ] || fail "generate/cover: unexpected status: $BODY"
pass "generate/cover (LLM)"

# 14. Critique + ATS score (LLM call; charges 1 credit)
req POST "/generate/$JOB_ID/critique" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "generate/critique -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .status)" = "done" ] || fail "generate/critique: unexpected status: $BODY"
APPLICATION_ID=$(echo "$BODY" | jq -r .application_id)
ATS_SCORE=$(echo "$BODY" | jq -r .ats_score)
pass "generate/critique (LLM, application_id=$APPLICATION_ID, ats_score=$ATS_SCORE)"

# 15. Generation charged exactly 1 more credit (fit-score calls are free, must not have charged)
req GET /billing/summary "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "billing/summary (after) -> $STATUS: $BODY"
CREDITS_AFTER=$(echo "$BODY" | jq -r .credits)
[ "$CREDITS_AFTER" -eq $((CREDITS_AFTER_IMPORT - 1)) ] || fail "billing: expected $((CREDITS_AFTER_IMPORT - 1)) credits, got $CREDITS_AFTER"
pass "billing/summary (generation charged 1 credit: $CREDITS_AFTER_IMPORT -> $CREDITS_AFTER; fit-score stayed free)"

# 16. Applications list includes tracker_status
req GET /applications "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "applications -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq "length")" -gt 0 ] || fail "applications: expected at least 1, got $BODY"
[ "$(echo "$BODY" | jq -r ".[0].tracker_status")" = "not_applied" ] || fail "applications: expected tracker_status=not_applied, got $BODY"
pass "applications list (tracker_status present)"

# 17. Application tracker: set status
req PATCH "/applications/$APPLICATION_ID/tracker" "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"tracker_status":"applied"}'
[ "$STATUS" = "200" ] || fail "tracker PATCH -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .tracker_status)" = "applied" ] || fail "tracker PATCH: status not updated: $BODY"
pass "application tracker (set to applied)"

# 18. Tracker stats
req GET /applications/stats "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "applications/stats -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .applied)" -ge 1 ] || fail "applications/stats: expected applied >= 1, got $BODY"
pass "applications/stats"

# 19. Tracker filter
req GET "/applications?tracker_status=applied" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "applications?tracker_status=applied -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq "length")" -ge 1 ] || fail "applications filter: expected >=1 applied row, got $BODY"
req GET "/applications?tracker_status=rejected" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "applications?tracker_status=rejected -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq "length")" -eq 0 ] || fail "applications filter: expected 0 rejected rows, got $BODY"
pass "application tracker filter (?tracker_status=)"

# 20. ATS text-layer verification of the rendered PDF
req GET "/applications/$APPLICATION_ID/verify" "${AUTH[@]}"
[ "$STATUS" = "200" ] || fail "applications/verify -> $STATUS: $BODY"
[ "$(echo "$BODY" | jq -r .machine_readable)" = "true" ] || fail "applications/verify: expected machine_readable=true, got $BODY"
pass "applications/verify (machine_readable=true)"

# 21. Download CV as PDF
PDF_FILE="$(mktemp)"
STATUS=$(curl -s -o "$PDF_FILE" -w "%{http_code}" "${AUTH[@]}" \
  "$BASE_URL/applications/$APPLICATION_ID/download?doc=cv&fmt=pdf")
[ "$STATUS" = "200" ] || fail "download cv pdf -> $STATUS"
head -c4 "$PDF_FILE" | grep -q "%PDF" || fail "download cv pdf: not a PDF"
rm -f "$PDF_FILE"
pass "download CV (PDF)"

# 22. Download cover letter as DOCX
DOCX_FILE="$(mktemp)"
STATUS=$(curl -s -o "$DOCX_FILE" -w "%{http_code}" "${AUTH[@]}" \
  "$BASE_URL/applications/$APPLICATION_ID/download?doc=cover&fmt=docx")
[ "$STATUS" = "200" ] || fail "download cover docx -> $STATUS"
head -c2 "$DOCX_FILE" | grep -q "PK" || fail "download cover docx: not a zip/docx"
rm -f "$DOCX_FILE"
pass "download cover letter (DOCX)"

# ---------------------------------------------------------------------------
# Billing / subscription
# ---------------------------------------------------------------------------

# 23. Checkout: unknown plan -> 404
req POST "/billing/checkout?plan_id=nonexistent-plan" "${AUTH[@]}"
[ "$STATUS" = "404" ] || fail "checkout (unknown plan) -> expected 404, got $STATUS: $BODY"
pass "billing/checkout rejects unknown plan"

# 24. Checkout: real Polar sandbox session for the one-time plan
req POST "/billing/checkout?plan_id=starter" "${AUTH[@]}"
if [ "$STATUS" = "200" ]; then
  CHECKOUT_URL=$(echo "$BODY" | jq -r .checkout_url)
  echo "$CHECKOUT_URL" | grep -qE "^https://" || fail "checkout: expected an https checkout_url, got $BODY"
  pass "billing/checkout (starter, real Polar session created)"
else
  skip "billing/checkout (starter) -> $STATUS: $BODY (Polar not configured on this deployment?)"
fi

# 25. Portal before any purchase -> 400 (no polar_customer_id yet)
req POST /billing/portal "${AUTH[@]}"
[ "$STATUS" = "400" ] || fail "billing/portal (no purchase yet) -> expected 400, got $STATUS: $BODY"
pass "billing/portal blocked before first purchase"

# 26-30. Webhook-driven billing: only runs if we have the signing secret, a
# Python with `standardwebhooks` installed, and the secret actually parses
# (the standardwebhooks lib only auto-strips a "whsec_" prefix — a
# differently-prefixed or malformed secret raises here rather than in the
# app itself, which is worth surfacing loudly since it means the real
# deployment would also reject every genuine Polar webhook).
WEBHOOK_SECRET_OK=""
if [ -n "${POLAR_WEBHOOK_SECRET:-}" ] && [ -n "$PY" ]; then
  if "$PY" -c "
import os
from standardwebhooks import Webhook
Webhook(os.environ['POLAR_WEBHOOK_SECRET'])
" >/dev/null 2>&1; then
    WEBHOOK_SECRET_OK=1
  else
    echo "WARNING: POLAR_WEBHOOK_SECRET is set but does not parse as a valid Standard Webhooks secret." >&2
    echo "         This means the real deployment likely rejects genuine Polar webhooks too — check the Polar dashboard." >&2
  fi
fi
if [ -n "$WEBHOOK_SECRET_OK" ]; then
  sign_webhook() {
    # sign_webhook <json-body> -> writes headers to $WH_HEADERS_FILE, signed body to stdout
    local body="$1"
    "$PY" - "$body" <<'PYEOF'
import sys, json, datetime
from standardwebhooks import Webhook

body = sys.argv[1]
secret = __import__("os").environ["POLAR_WEBHOOK_SECRET"]
wh = Webhook(secret)
msg_id = "msg_smoketest_" + str(int(datetime.datetime.now().timestamp()))
ts = datetime.datetime.now(datetime.timezone.utc)
sig = wh.sign(msg_id, ts, body)
print(json.dumps({"webhook-id": msg_id, "webhook-timestamp": str(int(ts.timestamp())), "webhook-signature": sig}))
PYEOF
  }

  # We don't have the user's numeric id without an admin route; the webhook
  # payload omits metadata.user_id and relies on the customer-email fallback
  # in _handle_order_paid/_handle_subscription_end (same as a real Polar buyer).
  ORDER_ID="order_smoketest_$(date +%s)"
  ORDER_BODY=$(jq -nc --arg id "$ORDER_ID" --arg email "$EMAIL" \
    '{"type":"order.paid","data":{"id":$id,"product_id":"prod_smoketest","customer":{"id":("cust_"+$id),"email":$email},"metadata":{"plan_id":"starter"}}}')
  WH_HEADERS_JSON=$(sign_webhook "$ORDER_BODY")
  WH_ID=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-id"')
  WH_TS=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-timestamp"')
  WH_SIG=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-signature"')

  req POST /billing/webhook -H "Content-Type: application/json" \
    -H "webhook-id: $WH_ID" -H "webhook-timestamp: $WH_TS" -H "webhook-signature: $WH_SIG" \
    -d "$ORDER_BODY"
  [ "$STATUS" = "200" ] || fail "webhook order.paid -> $STATUS: $BODY"
  req GET /billing/summary "${AUTH[@]}"
  CREDITS_POST_PURCHASE=$(echo "$BODY" | jq -r .credits)
  [ "$CREDITS_POST_PURCHASE" -eq $((CREDITS_AFTER + 100)) ] || fail "webhook order.paid: expected $((CREDITS_AFTER + 100)) credits (starter=100), got $CREDITS_POST_PURCHASE"
  [ "$(echo "$BODY" | jq -r .plan)" = "starter" ] || fail "webhook order.paid: expected plan=starter, got $BODY"
  pass "billing/webhook order.paid (credits: $CREDITS_AFTER -> $CREDITS_POST_PURCHASE, plan=starter)"

  # 27. Replay the same order -> idempotent, no double credit (needs a fresh valid signature/timestamp)
  WH_HEADERS_JSON=$(sign_webhook "$ORDER_BODY")
  WH_ID=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-id"')
  WH_TS=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-timestamp"')
  WH_SIG=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-signature"')
  req POST /billing/webhook -H "Content-Type: application/json" \
    -H "webhook-id: $WH_ID" -H "webhook-timestamp: $WH_TS" -H "webhook-signature: $WH_SIG" \
    -d "$ORDER_BODY"
  [ "$STATUS" = "200" ] || fail "webhook replay -> $STATUS: $BODY"
  req GET /billing/summary "${AUTH[@]}"
  [ "$(echo "$BODY" | jq -r .credits)" -eq "$CREDITS_POST_PURCHASE" ] || fail "webhook replay: credits changed, expected idempotent no-op: $BODY"
  pass "billing/webhook order.paid replay is idempotent"

  # 28. Forged signature -> 401
  req POST /billing/webhook -H "Content-Type: application/json" \
    -H "webhook-id: forged" -H "webhook-timestamp: $(date +%s)" -H "webhook-signature: v1,ZmFrZQ==" \
    -d "$ORDER_BODY"
  [ "$STATUS" = "401" ] || fail "webhook forged signature -> expected 401, got $STATUS: $BODY"
  pass "billing/webhook rejects forged signature"

  # 29. Unsigned -> 401
  req POST /billing/webhook -H "Content-Type: application/json" -d "$ORDER_BODY"
  [ "$STATUS" = "401" ] || fail "webhook unsigned -> expected 401, got $STATUS: $BODY"
  pass "billing/webhook rejects unsigned request"

  # 30. Subscription cancellation -> plan reverts to free, credits untouched
  CANCEL_BODY=$(jq -nc --arg email "$EMAIL" \
    '{"type":"subscription.canceled","data":{"customer":{"email":$email},"metadata":{}}}')
  WH_HEADERS_JSON=$(sign_webhook "$CANCEL_BODY")
  WH_ID=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-id"')
  WH_TS=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-timestamp"')
  WH_SIG=$(echo "$WH_HEADERS_JSON" | jq -r '."webhook-signature"')
  req POST /billing/webhook -H "Content-Type: application/json" \
    -H "webhook-id: $WH_ID" -H "webhook-timestamp: $WH_TS" -H "webhook-signature: $WH_SIG" \
    -d "$CANCEL_BODY"
  [ "$STATUS" = "200" ] || fail "webhook subscription.canceled -> $STATUS: $BODY"
  req GET /billing/summary "${AUTH[@]}"
  [ "$(echo "$BODY" | jq -r .plan)" = "free" ] || fail "webhook subscription.canceled: expected plan=free, got $BODY"
  [ "$(echo "$BODY" | jq -r .credits)" -eq "$CREDITS_POST_PURCHASE" ] || fail "webhook subscription.canceled: credits should be untouched: $BODY"
  pass "billing/webhook subscription.canceled (plan -> free, credits kept)"
else
  skip "billing/webhook order.paid, idempotency, signature checks, subscription.canceled (no usable POLAR_WEBHOOK_SECRET/Python — see warning above if one was printed)"
fi

echo
echo "All smoke tests passed against $BASE_URL"
