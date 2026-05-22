#!/usr/bin/env sh
# production-smoke.sh
#
# Black-box smoke check for a deployed Helpmefindthejob instance.
#
# Usage:
#   ./scripts/production-smoke.sh
#   APP_BASE_URL=https://app.helpmefindthejob.org ./scripts/production-smoke.sh
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

APP_BASE_URL="${APP_BASE_URL:-https://app.helpmefindthejob.org}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${HELPMEFINDTHEJOB_ADMIN_EMAIL:-}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${HELPMEFINDTHEJOB_ADMIN_PASSWORD:-}}"
COOKIE_JAR="$(mktemp -t helpmefindthejob-smoke.XXXXXX)"
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

# 5. Unauthenticated landing mission block renders. Without this
# block the apex shows only a sign-in gate — a wasted first
# impression for NLnet reviewers + first-time visitors. We use
# shell pattern matching instead of echo|grep -q to avoid the
# broken-pipe noise under `set -eu` (grep -q closes the pipe
# early; echo then complains to stderr but the test outcome is
# fine — the cleaner idiom is `case`).
step "Landing mission block on $APP_BASE_URL/"
INDEX_BODY="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/")"
case "$INDEX_BODY" in
  *'class="auth-mission"'*) ;;
  *) fail "landing mission block missing from / — visitors see only the sign-in gate" ;;
esac
case "$INDEX_BODY" in
  *'data-i18n="landing.headline"'*) ;;
  *) fail "landing headline missing" ;;
esac

# 6. Dynamic SEO surfaces (phase2-backlog #10 / SSR for SEO)
step "GET $APP_BASE_URL/sitemap.xml"
SITEMAP="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/sitemap.xml")"
echo "$SITEMAP" | grep -q '<urlset' || fail "/sitemap.xml is not a valid sitemap"
if echo "$SITEMAP" | grep -q 'khalo.org'; then
  fail "/sitemap.xml leaked legacy khalo.org domain (sanitization regression)"
fi

step "GET $APP_BASE_URL/robots.txt"
ROBOTS="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/robots.txt")"
echo "$ROBOTS" | grep -iq 'sitemap:' || fail "/robots.txt missing Sitemap: line"

# 7. MCP catalogue surface (phase2-backlog §2.2 deferred items)
step "GET $APP_BASE_URL/mcp/version"
MCP_VERSION="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/mcp/version")"
echo "$MCP_VERSION" | grep -q '"protocolVersion"' \
  || fail "/mcp/version missing protocolVersion"
echo "$MCP_VERSION" | grep -q '"helpmefindthejob"' \
  || fail "/mcp/version serverInfo.name not 'helpmefindthejob'"

step "GET $APP_BASE_URL/mcp/schemas.json"
MCP_SCHEMAS="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/mcp/schemas.json")"
echo "$MCP_SCHEMAS" | grep -q '"tools"' \
  || fail "/mcp/schemas.json missing tools array"

# 8. Uptime history surface (phase2-backlog #30)
step "GET $APP_BASE_URL/api/health/history"
HISTORY="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/api/health/history?window=1")"
echo "$HISTORY" | grep -q '"windowHours"' \
  || fail "/api/health/history missing windowHours"
echo "$HISTORY" | grep -q '"snapshots"' \
  || fail "/api/health/history missing snapshots array"

# 9. Prometheus metrics endpoint (phase2-backlog #17 observability)
step "GET $APP_BASE_URL/api/metrics"
METRICS="$(curl -sS --fail --max-time 10 "$APP_BASE_URL/api/metrics")"
echo "$METRICS" | grep -q 'helpmefindthejob_http_requests_total' \
  || fail "/api/metrics missing http_requests_total counter"
# Use -D to capture response headers from a GET (HEAD isn't
# supported on this endpoint by design — Prometheus scrapers
# always GET).
METRICS_CT="$(curl -sS -D - -o /dev/null --max-time 10 "$APP_BASE_URL/api/metrics" | grep -i '^content-type:')"
echo "$METRICS_CT" | grep -iq 'text/plain' \
  || fail "/api/metrics not in Prometheus exposition content-type (got: $METRICS_CT)"

# 10. Optional authenticated probe
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
