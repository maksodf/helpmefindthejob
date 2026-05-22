#!/usr/bin/env sh
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Boots a fresh dev server + drives Chromium through the Loop 14.1
# typing-label verification. Mirrors run-journey-browser-smoke.sh.

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
echo "[typing-label-smoke] booting app on http://127.0.0.1:$PORT"
HELPMEFINDTHEJOB_DATA_DIR="$DATA_DIR" \
  HELPMEFINDTHEJOB_ENV=development \
  HELPMEFINDTHEJOB_ALLOW_REGISTRATION=true \
  HELPMEFINDTHEJOB_REQUIRE_EMAIL_VERIFICATION=false \
  HELPMEFINDTHEJOB_COOKIE_SECURE=false \
  HELPMEFINDTHEJOB_AUDIT_LOG_SALT="typing-label-salt-32chars-abcd1234" \
  "$PYTHON_BIN" app.py --host 127.0.0.1 --port "$PORT" >"$DATA_DIR/server.log" 2>&1 &
ready=0
for _ in $(seq 1 60); do
  curl -sS -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1 && { ready=1; break; }
  sleep 0.2
done
[ "$ready" = "1" ] || { tail -40 "$DATA_DIR/server.log" >&2; exit 1; }
E2E_BASE_URL="http://127.0.0.1:$PORT" \
  "$PYTHON_BIN" tests/e2e/typing_label_smoke.py
status=$?
[ "$status" = "0" ] || tail -60 "$DATA_DIR/server.log" >&2 || true
exit $status
