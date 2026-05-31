#!/usr/bin/env sh
# probe-journey-ai.sh
#
# Operator-runnable verification of the journey's AI paths against a
# REAL LLM. Required env (do NOT commit a real key — pass at shell):
#   HELPMEFINDTHEJOB_MANAGED_AI_KEY      — Anthropic / OpenAI / etc. key
#   HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER — anthropic | openai | google_gemini | deepseek | openrouter
#   HELPMEFINDTHEJOB_MANAGED_AI_MODEL    — (optional) model id; defaults sane per provider
#
# Probes:
#   1. Inspire lateral-roles prompt — JSON list of 3-5 strings
#   2. Motivation letter prompt — well-formed DACH letter
#   3. CV-consult prompt — JSON list of {gap, question}
#   4. Prompt-injection resistance — CV contains "ignore previous
#      instructions"; agent must still produce a letter, not leak
#      the system prompt
#
# Cost: ~3-5 LLM calls × ~600 input tokens × ~300 output tokens.
# At claude-haiku-4-5 pricing (~$0.25/$1.25 per M), well under 1 cent.

set -eu

if [ -z "${HELPMEFINDTHEJOB_MANAGED_AI_KEY:-}" ]; then
  echo "ERROR: HELPMEFINDTHEJOB_MANAGED_AI_KEY must be set in your shell." >&2
  exit 2
fi
if [ -z "${HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER:-}" ]; then
  echo "ERROR: HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER must be set." >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"

HELPMEFINDTHEJOB_MANAGED_AI_KEY="$HELPMEFINDTHEJOB_MANAGED_AI_KEY" \
  HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER="$HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER" \
  HELPMEFINDTHEJOB_MANAGED_AI_MODEL="${HELPMEFINDTHEJOB_MANAGED_AI_MODEL:-}" \
  "$PYTHON_BIN" tests/e2e/journey_ai_probe.py
