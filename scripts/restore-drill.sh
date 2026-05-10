#!/usr/bin/env sh
# restore-drill.sh
#
# Disaster-recovery rehearsal: spin up a sidecar app instance, restore a
# backup tarball into a fresh Docker volume, run the smoke script
# against the sidecar, then tear it down.
#
# This script never touches the live container or its data volume.
#
# Usage:
#   ./scripts/restore-drill.sh ./backups/directjob-scout-YYYY...tar.gz
#   BACKUP_FILE=...tar.gz ./scripts/restore-drill.sh
#
# Exit codes:
#   0  drill passed
#   1  drill failed
#   2  required tooling or input missing

set -eu

BACKUP_FILE="${1:-${BACKUP_FILE:-}}"
SIDECAR_NAME="${SIDECAR_NAME:-directjob-scout-restore-drill}"
SIDECAR_VOLUME="${SIDECAR_VOLUME:-directjob_data_restore_drill}"
SIDECAR_PORT="${SIDECAR_PORT:-18765}"
IMAGE="${IMAGE:-nassermcpserver-directjob-scout}"

if [ -z "$BACKUP_FILE" ]; then
  echo "drill: provide a backup file path (or set BACKUP_FILE)" >&2
  exit 2
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "drill: backup file not found: $BACKUP_FILE" >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "drill: docker is required" >&2
  exit 2
fi

cleanup() {
  docker rm -f "$SIDECAR_NAME" >/dev/null 2>&1 || true
  docker volume rm "$SIDECAR_VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "drill: provisioning sidecar volume $SIDECAR_VOLUME"
docker volume create "$SIDECAR_VOLUME" >/dev/null

SCRATCH="$(mktemp -d)"
trap 'cleanup; rm -rf "$SCRATCH"' EXIT
echo "drill: extracting $BACKUP_FILE to scratch"
tar -xzf "$BACKUP_FILE" -C "$SCRATCH"

if [ ! -d "$SCRATCH/data" ]; then
  echo "drill: extracted archive does not contain a data/ directory" >&2
  exit 1
fi

echo "drill: copying snapshot into sidecar volume"
docker run --rm \
  -v "$SIDECAR_VOLUME":/dst \
  -v "$SCRATCH/data":/src \
  alpine sh -c 'cp -a /src/. /dst/'

echo "drill: starting sidecar app on port $SIDECAR_PORT"
DIRECTJOB_SECRET_KEY="${DIRECTJOB_SECRET_KEY:-restore-drill-secret-key-with-enough-bytes-1234}"
docker run -d --name "$SIDECAR_NAME" \
  -e COMPANY_DISCOVERY_ENV=development \
  -e COMPANY_DISCOVERY_DATA_DIR=/app/data \
  -e COMPANY_DISCOVERY_HOST=0.0.0.0 \
  -e COMPANY_DISCOVERY_PORT=8765 \
  -e DIRECTJOB_SECRET_KEY="$DIRECTJOB_SECRET_KEY" \
  -e DIRECTJOB_COOKIE_SECURE=false \
  -p "$SIDECAR_PORT":8765 \
  -v "$SIDECAR_VOLUME":/app/data \
  "$IMAGE" >/dev/null || {
    echo "drill: failed to start sidecar; image '$IMAGE' missing? Build with 'docker compose -f docker-compose.prod.yml build'" >&2
    exit 1
  }

echo "drill: waiting for sidecar /api/health"
ready=0
for _ in $(seq 1 40); do
  if curl -sS -m 2 "http://127.0.0.1:$SIDECAR_PORT/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done
if [ "$ready" != "1" ]; then
  echo "drill: sidecar did not become healthy" >&2
  docker logs "$SIDECAR_NAME" 2>&1 | tail -50 >&2 || true
  exit 1
fi

echo "drill: running smoke against sidecar"
APP_BASE_URL="http://127.0.0.1:$SIDECAR_PORT" "$(dirname "$0")/production-smoke.sh"

echo "drill: passed"
