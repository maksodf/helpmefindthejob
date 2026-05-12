#!/usr/bin/env sh
# probe-ai-router.sh
#
# Operator-side end-to-end verification of the chat AI router against
# a REAL LLM. Run this once after setting the env vars below — it
# proves the integration works without any synthetic mocks.
#
# Required env (do NOT commit a real key — pass at the shell):
#   DIRECTJOB_MANAGED_AI_KEY      — your Anthropic / OpenAI / etc. key
#   DIRECTJOB_MANAGED_AI_PROVIDER — anthropic | openai | google_gemini | deepseek | openrouter
#   DIRECTJOB_MANAGED_AI_MODEL    — (optional) model id; defaults to a
#                                    sane choice per provider in the app
#
# What it does:
#   1. Boots a fresh app instance with DIRECTJOB_CHAT_AI_ROUTER=true and
#      the env vars you provided.
#   2. Registers a synthetic tester via the admin-bypass path.
#   3. Sends 5 natural-language probes through /api/chat/message and
#      observes which command the LLM classified into.
#   4. Prints per-probe verdict (correct command id? correct args?).
#   5. Exits 0 if ≥4/5 probes route to the expected command.
#
# Cost guidance: 5 probes × ~250 input tokens × ~5 output tokens. With
# claude-haiku-4-5 at $0.25/$1.25 per M, this is well under 1 cent.

set -eu

if [ -z "${DIRECTJOB_MANAGED_AI_KEY:-}" ]; then
  echo "ERROR: DIRECTJOB_MANAGED_AI_KEY must be set in your shell." >&2
  echo "       Example: export DIRECTJOB_MANAGED_AI_KEY=sk-ant-..." >&2
  exit 2
fi
if [ -z "${DIRECTJOB_MANAGED_AI_PROVIDER:-}" ]; then
  echo "ERROR: DIRECTJOB_MANAGED_AI_PROVIDER must be set." >&2
  echo "       One of: anthropic | openai | google_gemini | deepseek | openrouter" >&2
  exit 2
fi

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

echo "[probe] booting app on http://127.0.0.1:$PORT"
echo "[probe] provider=${DIRECTJOB_MANAGED_AI_PROVIDER} model=${DIRECTJOB_MANAGED_AI_MODEL:-default}"
DIRECTJOB_CHAT_AI_ROUTER=true \
  DIRECTJOB_MANAGED_AI_KEY="$DIRECTJOB_MANAGED_AI_KEY" \
  DIRECTJOB_MANAGED_AI_PROVIDER="$DIRECTJOB_MANAGED_AI_PROVIDER" \
  DIRECTJOB_MANAGED_AI_MODEL="${DIRECTJOB_MANAGED_AI_MODEL:-}" \
  COMPANY_DISCOVERY_DATA_DIR="$DATA_DIR" \
  COMPANY_DISCOVERY_ENV=development \
  DIRECTJOB_ALLOW_REGISTRATION=true \
  DIRECTJOB_REQUIRE_EMAIL_VERIFICATION=false \
  "$PYTHON_BIN" app.py --host 127.0.0.1 --port "$PORT" >"$DATA_DIR/server.log" 2>&1 &

ready=0
for _ in $(seq 1 60); do
  curl -sS -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1 && { ready=1; break; }
  sleep 0.2
done
[ "$ready" = "1" ] || { tail -40 "$DATA_DIR/server.log" >&2; exit 1; }

E2E_BASE_URL="http://127.0.0.1:$PORT" \
  "$PYTHON_BIN" tests/e2e/real_llm_probe.py
status=$?
[ "$status" = "0" ] || { echo "[probe] server tail on failure:"; tail -40 "$DATA_DIR/server.log" >&2 || true; }
exit $status
