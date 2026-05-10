#!/usr/bin/env sh
# run-e2e.sh
#
# Browser E2E entry point. Starts the app on a free local port, then
# runs the Playwright Python suite against it.
#
# Requirements (one-time):
#   pip install playwright
#   playwright install chromium
#
# Run:
#   ./scripts/run-e2e.sh
#
# Optional env vars:
#   E2E_PORT=18900           pin the local port
#   E2E_HEADLESS=false       open a visible browser
#   E2E_SCREENSHOTS=tests/e2e/screenshots
#
# Exit codes:
#   0  passed
#   1  test failure
#   2  Playwright not installed

set -eu

if ! python3 -c "import playwright" >/dev/null 2>&1; then
  cat <<'TXT' >&2
e2e: Playwright is not installed.
Install it with:
  pip install playwright
  playwright install chromium
TXT
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${E2E_PORT:-}"
if [ -z "$PORT" ]; then
  PORT="$(python3 - <<'PY'
import socket
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
)"
fi

DATA_DIR="$(mktemp -d)"
trap 'kill %1 2>/dev/null || true; rm -rf "$DATA_DIR"' EXIT

COMPANY_DISCOVERY_DATA_DIR="$DATA_DIR" \
  COMPANY_DISCOVERY_ENV=development \
  python3 app.py --host 127.0.0.1 --port "$PORT" >"$DATA_DIR/server.log" 2>&1 &

echo "e2e: app booting on http://127.0.0.1:$PORT (data dir: $DATA_DIR)"

ready=0
for _ in $(seq 1 50); do
  if curl -sS -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.2
done
if [ "$ready" != "1" ]; then
  echo "e2e: app did not start" >&2
  cat "$DATA_DIR/server.log" >&2 || true
  exit 1
fi

E2E_SCREENSHOTS="${E2E_SCREENSHOTS:-tests/e2e/screenshots}"
mkdir -p "$E2E_SCREENSHOTS"

E2E_BASE_URL="http://127.0.0.1:$PORT" \
  E2E_SCREENSHOTS="$E2E_SCREENSHOTS" \
  E2E_HEADLESS="${E2E_HEADLESS:-true}" \
  python3 -m unittest tests.e2e.test_browser_flow -v
