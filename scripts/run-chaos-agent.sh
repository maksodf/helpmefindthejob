#!/usr/bin/env sh
# Boot app on a free port with clean SQLite, then run the chaos agent
# against it. Exits non-zero on any FAIL.

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

echo "[chaos] booting app on http://127.0.0.1:$PORT  (data: $DATA_DIR)"
COMPANY_DISCOVERY_DATA_DIR="$DATA_DIR" \
  COMPANY_DISCOVERY_ENV=development \
  DIRECTJOB_ALLOW_REGISTRATION=true \
  DIRECTJOB_REQUIRE_EMAIL_VERIFICATION=false \
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
  echo "[chaos] app failed to start; tail of log:" >&2
  tail -40 "$SERVER_LOG" >&2 || true
  exit 1
fi
echo "[chaos] app up"

E2E_BASE_URL="http://127.0.0.1:$PORT" \
  E2E_CHAOS_REPORT="${E2E_CHAOS_REPORT:-tests/e2e/chaos_report.json}" \
  "$PYTHON_BIN" tests/e2e/chaos_agent.py
status=$?
if [ "$status" != "0" ]; then
  echo "[chaos] server tail on failure:" >&2
  tail -60 "$SERVER_LOG" >&2 || true
fi
exit $status
