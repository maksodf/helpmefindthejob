#!/usr/bin/env sh
set -eu

HOST="${COMPANY_DISCOVERY_HOST:-127.0.0.1}"
PORT="${COMPANY_DISCOVERY_PORT:-8765}"

exec python3 app.py --host "$HOST" --port "$PORT" "$@"
