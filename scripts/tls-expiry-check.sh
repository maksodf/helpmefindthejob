#!/usr/bin/env sh
# tls-expiry-check.sh
#
# Print remaining days until the configured domain's TLS cert expires.
# Exits non-zero if it expires within $WARN_DAYS days (default 14).
# Uses only OpenSSL; no provider lock-in.
#
# Usage:
#   DOMAIN=app.directjob-scout.example ./scripts/tls-expiry-check.sh
#   DOMAIN=app.directjob-scout.example WARN_DAYS=21 ./scripts/tls-expiry-check.sh
#
# Exit codes:
#   0  cert valid for more than WARN_DAYS days
#   1  cert expires within WARN_DAYS days OR check failed

set -eu

DOMAIN="${DOMAIN:-${DIRECTJOB_DOMAIN:-}}"
WARN_DAYS="${WARN_DAYS:-14}"

if [ -z "$DOMAIN" ]; then
  echo "tls: set DOMAIN or DIRECTJOB_DOMAIN" >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "tls: openssl is required" >&2
  exit 1
fi

end_date="$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null \
  | openssl x509 -noout -enddate 2>/dev/null \
  | sed -e 's/^notAfter=//')"

if [ -z "$end_date" ]; then
  echo "tls: could not retrieve cert for $DOMAIN" >&2
  exit 1
fi

end_epoch="$(date -j -f '%b %d %H:%M:%S %Y %Z' "$end_date" +%s 2>/dev/null || date -d "$end_date" +%s 2>/dev/null || echo "")"
if [ -z "$end_epoch" ]; then
  echo "tls: could not parse end-date '$end_date'" >&2
  exit 1
fi
now_epoch="$(date +%s)"
days="$(( (end_epoch - now_epoch) / 86400 ))"

echo "tls: $DOMAIN expires in $days days ($end_date)"
if [ "$days" -lt "$WARN_DAYS" ]; then
  echo "tls: WARN — within $WARN_DAYS days" >&2
  exit 1
fi
exit 0
