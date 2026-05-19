#!/usr/bin/env sh
# uptime-check.sh
#
# Provider-neutral uptime probe. Hits /api/health on the configured URL
# and returns non-zero on failure or non-ok body. Suitable as a cron
# entry that pages on non-zero exit (most monitoring providers
# integrate this way).
#
# Usage:
#   ./scripts/uptime-check.sh
#   APP_BASE_URL=https://app.helpmefindthejob.com TIMEOUT=10 ./scripts/uptime-check.sh
#
# Env:
#   APP_BASE_URL  defaults to http://127.0.0.1:8765
#   TIMEOUT       seconds, defaults to 10
#
# Exit codes:
#   0  /api/health returns "status":"ok"
#   1  HTTP request failed
#   2  body did not match expected status

set -eu

URL="${APP_BASE_URL:-http://127.0.0.1:8765}"
TIMEOUT="${TIMEOUT:-10}"

body="$(curl -sS --fail --max-time "$TIMEOUT" "$URL/api/health" 2>&1)" || {
  echo "uptime: $URL/api/health unreachable" >&2
  echo "$body" >&2
  exit 1
}

if echo "$body" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  echo "uptime: ok"
  exit 0
fi

echo "uptime: unexpected body" >&2
echo "$body" >&2
exit 2
