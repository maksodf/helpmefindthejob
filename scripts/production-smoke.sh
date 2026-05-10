#!/usr/bin/env sh
# production-smoke.sh
#
# Black-box smoke check for a deployed DirectJob Scout instance.
#
# Usage:
#   ./scripts/production-smoke.sh
#   APP_BASE_URL=https://app.khalo.org ./scripts/production-smoke.sh
#   ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=... \
#     ./scripts/production-smoke.sh
#
# Exit codes:
#   0  all checks passed
#   1  a check failed; the failing line is printed before exit
#   2  required tooling missing
#
# The script never writes to the deployment. It only issues GET
# requests and an authenticated bootstrap fetch when an admin
# email/password are provided.

set -eu

APP_BASE_URL="${APP_BASE_URL:-https://app.khalo.org}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${DIRECTJOB_ADMIN_EMAIL:-}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${DIRECTJOB_ADMIN_PASSWORD:-}}"
COOKIE_JAR="$(mktemp -t directjob-smoke.XXXXXX)"
trap 'rm -f "$COOKIE_JAR"' EXIT

if ! command -v curl >/dev/null 2>&1; then
  echo "smoke: curl is required" >&2
  exit 2
fi

step() {
  printf 'smoke: %s\n' "$1"
}

fail() {
  printf 'smoke: FAIL %s\n' "$1" >&2
  exit 1
}

require_status() {
  expected="$1"
  actual="$2"
  description="$3"
  if [ "$expected" != "$actual" ]; then
    fail "$description (expected HTTP $expected, got $actual)"
  fi
}

# 1. /api/health
step "GET $APP_BASE_URL/api/health"
HEALTH_BODY="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/api/health")"
echo "$HEALTH_BODY" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' || fail "/api/health did not return status=ok"
echo "$HEALTH_BODY" | grep -q '"version"' || fail "/api/health did not include a version"

# 2. /api/auth/status as anonymous
step "GET $APP_BASE_URL/api/auth/status (anonymous)"
ANON_BODY="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/api/auth/status")"
echo "$ANON_BODY" | grep -Eq '"authenticated"[[:space:]]*:[[:space:]]*false' || fail "anonymous auth status was not false"

# 3. /api/bootstrap unauthenticated -> must be 401
step "GET $APP_BASE_URL/api/bootstrap (anonymous, expect 401)"
ANON_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$APP_BASE_URL/api/bootstrap")"
require_status "401" "$ANON_STATUS" "/api/bootstrap should reject anonymous"

# 4. Required security headers on the public index
step "Security headers on $APP_BASE_URL/"
HEADERS="$(curl -sS -I --max-time 10 "$APP_BASE_URL/")"
echo "$HEADERS" | grep -iq '^x-content-type-options: nosniff' || fail "X-Content-Type-Options missing"
echo "$HEADERS" | grep -iq '^x-frame-options: DENY' || fail "X-Frame-Options missing"
echo "$HEADERS" | grep -iq '^content-security-policy' || fail "Content-Security-Policy missing"
echo "$HEADERS" | grep -iq '^referrer-policy' || fail "Referrer-Policy missing"

# 5. Optional authenticated probe
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
  step "Authenticated bootstrap probe as $ADMIN_EMAIL"
  LOGIN_PAYLOAD="$(printf '{"email":"%s","password":"%s"}' "$ADMIN_EMAIL" "$ADMIN_PASSWORD")"
  LOGIN_BODY="$(curl -sS --fail --max-time 10 \
    -c "$COOKIE_JAR" \
    -H 'Content-Type: application/json' \
    -d "$LOGIN_PAYLOAD" \
    "$APP_BASE_URL/api/auth/login")"
  echo "$LOGIN_BODY" | grep -q '"csrfToken"' || fail "login did not return csrfToken"
  CSRF="$(printf '%s' "$LOGIN_BODY" | sed -n 's/.*"csrfToken":"\([^"]*\)".*/\1/p')"

  AUTH_STATUS="$(curl -sS --fail --max-time 10 -b "$COOKIE_JAR" \
    "$APP_BASE_URL/api/bootstrap" -o /dev/null -w '%{http_code}')"
  require_status "200" "$AUTH_STATUS" "authenticated /api/bootstrap"

  step "Logout"
  curl -sS --fail --max-time 10 -b "$COOKIE_JAR" \
    -H "X-CSRF-Token: $CSRF" \
    -H 'Content-Type: application/json' \
    -d '{}' \
    "$APP_BASE_URL/api/auth/logout" >/dev/null
else
  step "Skipping authenticated probe (set ADMIN_EMAIL and ADMIN_PASSWORD to enable)"
fi

step "All checks passed against $APP_BASE_URL"
