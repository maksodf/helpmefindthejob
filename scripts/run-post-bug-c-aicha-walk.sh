#!/usr/bin/env sh
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# PART 6 Loop 9 — Boots a fresh helpmefindthejob server (cold cache,
# Ollama-backed AI), runs the Aïcha post-Bug-C walk, captures the
# transcript markdown, then tears down. Mirrors the pattern in
# run-journey-ux-expert.sh (fresh tmp data dir, ALLOW_REGISTRATION,
# health-probe wait).
#
# Pre-flight: Ollama llama3.1:8b must already be running at
# http://127.0.0.1:11434 (verified with `curl /api/tags`).

set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-/Users/fouad./miniconda3/bin/python3}"

# Pick a free port
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
WALK_LOG="$DATA_DIR/walk.log"

cleanup() {
  if [ -n "${SERVER_PID:-}" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [ -n "${KEEP_DATA_DIR:-}" ]; then
    echo "[walk] kept data dir: $DATA_DIR"
  else
    rm -rf "$DATA_DIR"
  fi
}
trap cleanup EXIT INT TERM

echo "[walk] booting helpmefindthejob server on http://127.0.0.1:$PORT  data=$DATA_DIR"
echo "[walk] Loop 10.3: friction_class classifier active (no env-hook workaround)"
HELPMEFINDTHEJOB_DATA_DIR="$DATA_DIR" \
  HELPMEFINDTHEJOB_ENV=development \
  HELPMEFINDTHEJOB_ALLOW_REGISTRATION=true \
  HELPMEFINDTHEJOB_REQUIRE_EMAIL_VERIFICATION=false \
  HELPMEFINDTHEJOB_COOKIE_SECURE=false \
  HELPMEFINDTHEJOB_AUDIT_LOG_SALT="loop9-walk-salt-32chars-abcd1234efgh" \
  HELPMEFINDTHEJOB_AI_PROVIDER=ollama \
  HELPMEFINDTHEJOB_AI_MODEL=llama3.1:8b \
  OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}" \
  HELPMEFINDTHEJOB_AI_PROVIDER=ollama \
  HELPMEFINDTHEJOB_AI_MODEL=llama3.1:8b \
  "$PYTHON_BIN" app.py --host 127.0.0.1 --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

# Wait for /api/health
ready=0
for _ in $(seq 1 80); do
  if curl -sS -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.25
done
if [ "$ready" != "1" ]; then
  echo "[walk] server failed to come up; last 60 lines of $SERVER_LOG:" >&2
  tail -60 "$SERVER_LOG" >&2 || true
  exit 1
fi

echo "[walk] server healthy; starting walk"

# Run walk (may take many minutes; Ollama latency hits per AI call)
set +e
# Loop 11 (2026-05-20): WALK_PERSONA env var picks which persona
# the walk script drives. Defaults to aicha for Loop 10.3 backwards
# compat. Walks 2-7 set WALK_PERSONA={yusuf,olga,mahmoud,maria,
# kaethe,tobias}.
WALK_PERSONA="${WALK_PERSONA:-aicha}"
"$PYTHON_BIN" scripts/post_bug_c_aicha_walk.py \
  --base "http://127.0.0.1:$PORT" \
  --persona "$WALK_PERSONA" 2>&1 | tee "$WALK_LOG"
status=$?
set -e

if [ "$status" != "0" ]; then
  echo "[walk] driver exited status=$status; tail of server log:" >&2
  tail -80 "$SERVER_LOG" >&2 || true
fi
exit "$status"
