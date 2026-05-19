#!/usr/bin/env sh
# log-redaction-check.sh
#
# Scan a recent slice of container logs + the data/ directory's text
# files for tokens that should never appear in operator logs. The
# checker exits non-zero on any match so it can sit in a cron or a
# pre-deploy smoke.
#
# Usage:
#   ./scripts/log-redaction-check.sh
#   COMPOSE_FILE=docker-compose.prod.yml SERVICE_NAME=helpmefindthejob \
#     ./scripts/log-redaction-check.sh
#   LOG_LINES=2000 ./scripts/log-redaction-check.sh
#
# Exit codes:
#   0  no leakage found
#   1  one or more forbidden patterns matched (the matches are printed
#      to stderr — review and rotate credentials immediately)
#   2  required tooling missing
#
# Patterns we look for:
#   - DIRECTJOB_SMTP_PASSWORD value
#   - DIRECTJOB_STRIPE_API_KEY value
#   - PBKDF2 password hashes ("pbkdf2_sha256$")
#   - Stripe live keys ("sk_live_", "rk_live_")
#   - Common bearer-token prefixes ("Authorization: Bearer ")
#   - Invitation / reset-token raw values are 32-byte url-safe; we
#     match the exact substring "?token=" because that's how the app
#     sends them via email — the email outbox is the only legitimate
#     home; logs must not include it.

set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
SERVICE_NAME="${SERVICE_NAME:-helpmefindthejob}"
LOG_LINES="${LOG_LINES:-1000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v grep >/dev/null 2>&1; then
  echo "log-redaction: grep is required" >&2
  exit 2
fi

scan_text() {
  pattern="$1"
  description="$2"
  if printf '%s' "$BUNDLE" | grep -E -- "$pattern" >/dev/null 2>&1; then
    echo "log-redaction: FAIL — $description" >&2
    printf '%s' "$BUNDLE" | grep -nE -- "$pattern" >&2 | head -5
    return 1
  fi
  return 0
}

BUNDLE=""

# 1. Container logs (best-effort; skip if compose isn't running).
if command -v docker >/dev/null 2>&1 && [ -f "$ROOT/$COMPOSE_FILE" ]; then
  CONTAINER_ID="$(docker compose -f "$ROOT/$COMPOSE_FILE" ps -q "$SERVICE_NAME" 2>/dev/null || true)"
  if [ -n "$CONTAINER_ID" ]; then
    BUNDLE="$BUNDLE\n$(docker logs --tail "$LOG_LINES" "$CONTAINER_ID" 2>&1 || true)"
  fi
fi

# 2. Filesystem files that operators commonly look at.
for path in "$ROOT/data/admin_audit.log" "$ROOT/data/email_outbox.log"; do
  if [ -f "$path" ]; then
    BUNDLE="$BUNDLE\n$(tail -n "$LOG_LINES" "$path" 2>/dev/null || true)"
  fi
done

failed=0

scan_text 'pbkdf2_sha256\$[0-9]+\$[0-9a-f]+\$[0-9a-f]+' \
  "PBKDF2 password hash present in logs" || failed=1
scan_text 'sk_live_[A-Za-z0-9]{16,}' \
  "Stripe live secret key prefix found" || failed=1
scan_text 'rk_live_[A-Za-z0-9]{16,}' \
  "Stripe live restricted key prefix found" || failed=1
scan_text 'Authorization:[[:space:]]*Bearer[[:space:]]+[A-Za-z0-9._-]+' \
  "Authorization header logged with bearer token" || failed=1

if [ -n "${DIRECTJOB_SMTP_PASSWORD:-}" ]; then
  scan_text "$DIRECTJOB_SMTP_PASSWORD" "DIRECTJOB_SMTP_PASSWORD literal value" || failed=1
fi
if [ -n "${DIRECTJOB_STRIPE_API_KEY:-}" ]; then
  scan_text "$DIRECTJOB_STRIPE_API_KEY" "DIRECTJOB_STRIPE_API_KEY literal value" || failed=1
fi

# Email-outbox tokens are expected; don't flag them when scanning the
# outbox itself. We only flag if `?token=` appears in container logs,
# which would mean a redact path is missing.
if command -v docker >/dev/null 2>&1 && [ -f "$ROOT/$COMPOSE_FILE" ]; then
  CONTAINER_ID="$(docker compose -f "$ROOT/$COMPOSE_FILE" ps -q "$SERVICE_NAME" 2>/dev/null || true)"
  if [ -n "$CONTAINER_ID" ]; then
    LOG_ONLY="$(docker logs --tail "$LOG_LINES" "$CONTAINER_ID" 2>&1 || true)"
    if printf '%s' "$LOG_ONLY" | grep -E '\?token=[A-Za-z0-9_-]{16,}' >/dev/null 2>&1; then
      echo "log-redaction: FAIL — invite/reset token leaked into container logs" >&2
      printf '%s' "$LOG_ONLY" | grep -nE '\?token=[A-Za-z0-9_-]{16,}' >&2 | head -5
      failed=1
    fi
  fi
fi

if [ "$failed" -ne 0 ]; then
  echo "log-redaction: leakage detected — rotate any exposed credentials and patch the offending log path." >&2
  exit 1
fi

echo "log-redaction: OK (no forbidden patterns matched in the last $LOG_LINES log lines)"
