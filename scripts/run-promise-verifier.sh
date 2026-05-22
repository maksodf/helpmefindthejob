#!/usr/bin/env sh
# Boot app on a free port with clean SQLite, then run the
# promise-verifier against it. Exits non-zero on any FAIL.
#
# Optional env:
#   E2E_PORT=18900   pin port

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
SERVER_LOG="$DATA_DIR/server.log"
trap 'kill %1 2>/dev/null || true; rm -rf "$DATA_DIR"' EXIT

echo "[promise] booting app on http://127.0.0.1:$PORT  (data: $DATA_DIR)"
HELPMEFINDTHEJOB_DATA_DIR="$DATA_DIR" \
  HELPMEFINDTHEJOB_ENV=development \
  HELPMEFINDTHEJOB_ALLOW_REGISTRATION=true \
  HELPMEFINDTHEJOB_REQUIRE_EMAIL_VERIFICATION=false \
  "$PYTHON_BIN" app.py --host 127.0.0.1 --port "$PORT" >"$SERVER_LOG" 2>&1 &

ready=0
for _ in $(seq 1 60); do
  if curl -sS -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.2
done
if [ "$ready" != "1" ]; then
  echo "[promise] app failed to start; tail of log:" >&2
  tail -40 "$SERVER_LOG" >&2 || true
  exit 1
fi
echo "[promise] app up"

E2E_BASE_URL="http://127.0.0.1:$PORT" \
  HELPMEFINDTHEJOB_DATA_DIR="$DATA_DIR" \
  E2E_PROMISE_REPORT="${E2E_PROMISE_REPORT:-tests/e2e/promise_report.json}" \
  "$PYTHON_BIN" tests/e2e/promise_verifier_agent.py
