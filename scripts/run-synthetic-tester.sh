#!/usr/bin/env sh
# run-synthetic-tester.sh
#
# Boots app.py on a free port with a clean data dir, then runs the
# synthetic-tester agent against it. The agent registers a fresh
# account per persona, walks the onboarding wizard, runs a real
# Find-jobs search, scrapes the queue, and produces a JSON report
# under tests/e2e/synthetic_report.json plus per-persona screenshots
# under tests/e2e/screenshots/.
#
# Run:
#   ./scripts/run-synthetic-tester.sh
#
# Optional env vars:
#   E2E_HEADLESS=false     visible browser (good for debugging)
#   E2E_PORT=18900         pin port
#   PYTHON_BIN=/path/python3   override Python (default: miniconda Python that has Playwright)

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c "import playwright" >/dev/null 2>&1; then
  echo "ERROR: Playwright is not importable under $PYTHON_BIN" >&2
  echo "Install with:  $PYTHON_BIN -m pip install playwright && $PYTHON_BIN -m playwright install chromium" >&2
  exit 2
fi

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

echo "[synth] booting app on http://127.0.0.1:$PORT  (data: $DATA_DIR)"
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
  echo "[synth] app failed to start; tail of log:" >&2
  tail -40 "$SERVER_LOG" >&2 || true
  exit 1
fi
echo "[synth] app up. tail of boot log:"
tail -5 "$SERVER_LOG" || true

E2E_BASE_URL="http://127.0.0.1:$PORT" \
  E2E_SCREENSHOTS="${E2E_SCREENSHOTS:-tests/e2e/screenshots}" \
  E2E_HEADLESS="${E2E_HEADLESS:-true}" \
  E2E_REPORT="${E2E_REPORT:-tests/e2e/synthetic_report.json}" \
  "$PYTHON_BIN" tests/e2e/synthetic_tester_agent.py
