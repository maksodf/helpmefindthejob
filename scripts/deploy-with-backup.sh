#!/usr/bin/env sh
# deploy-with-backup.sh — wrapper around deploy.sh that sources
# .deploy-env.local first so off-host S3 snapshot uploads have keys.
#
# Usage:
#   TAG=0.46.0 ./scripts/deploy-with-backup.sh
#
# Falls back to plain deploy.sh if .deploy-env.local is missing.
set -eu

if [ -f .deploy-env.local ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.deploy-env.local
  set +a
else
  echo "deploy-with-backup: .deploy-env.local not found — running deploy.sh without S3 upload." >&2
fi

: "${TAG:?TAG is required (e.g. TAG=0.46.0)}"
: "${SSH_HOST:=root@161.35.76.8}"
: "${SSH_KEY:=$HOME/.ssh/helpmefindthejob}"
: "${PUBLIC_URL:=https://app.helpmefindthejob.org}"

export TAG SSH_HOST SSH_KEY PUBLIC_URL

exec ./scripts/deploy.sh
