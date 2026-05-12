#!/usr/bin/env sh
# run-full-user-flow-agent.sh
#
# Boot the app, run the autonomous end-to-end verifier, dump the PDF
# on the user's Desktop, and report verdict.
#
# What it proves (concretely):
#   - photo download from a public CDN works
#   - photo upload + CV Builder fill happen via the real HTTP API
#   - the print page renders + page.pdf() captures a real PDF
#   - the PDF (parsed via pypdf) satisfies the DACH-CV norm
#   - the new strict job-type filter routes bartender / Pflegehelfer
#     correctly and applies the strict role filter
#
# Env knobs:
#   E2E_PORT             — port to bind (default: random free port)
#   E2E_PHOTO_URL        — stock photo URL (default: picsum seed=directjob)
#   E2E_DESKTOP_PDF_PATH — where the PDF lands (default: ~/Desktop/...)

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-/Users/fouad./miniconda3/bin/python3}"

PORT="${E2E_PORT:-}"
if [ -z "$PORT" ]; then
  PORT="$($PYTHON_BIN - <<'PY'
import socket
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
)"
fi

DATA_DIR="$(mktemp -d)"
trap 'kill %1 2>/dev/null || true; rm -rf "$DATA_DIR"' EXIT

echo "[full-flow] booting app on http://127.0.0.1:$PORT"
COMPANY_DISCOVERY_DATA_DIR="$DATA_DIR" \
  COMPANY_DISCOVERY_ENV=development \
  DIRECTJOB_ALLOW_REGISTRATION=true \
  DIRECTJOB_REQUIRE_EMAIL_VERIFICATION=false \
  "$PYTHON_BIN" app.py --host 127.0.0.1 --port "$PORT" >"$DATA_DIR/server.log" 2>&1 &

ready=0
for _ in $(seq 1 60); do
  if curl -sS -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.2
done
if [ "$ready" != "1" ]; then
  tail -40 "$DATA_DIR/server.log" >&2
  exit 1
fi

E2E_BASE_URL="http://127.0.0.1:$PORT" \
  "$PYTHON_BIN" tests/e2e/full_user_flow_agent.py
status=$?

if [ "$status" != "0" ]; then
  echo
  echo "[full-flow] server tail on failure:"
  tail -40 "$DATA_DIR/server.log" >&2 || true
fi

exit $status
