#!/usr/bin/env sh
set -eu

HOST="${HELPMEFINDTHEJOB_HOST:-127.0.0.1}"
PORT="${HELPMEFINDTHEJOB_PORT:-8765}"

exec python3 app.py --host "$HOST" --port "$PORT" "$@"
