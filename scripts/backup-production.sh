#!/usr/bin/env sh
# backup-production.sh
#
# Snapshot the persisted SQLite/JSON data volume of the production
# Helpmefindthejob deployment to a local archive.
#
# Usage:
#   ./scripts/backup-production.sh
#   BACKUP_DIR=/var/backups/helpmefindthejob ./scripts/backup-production.sh
#   COMPOSE_FILE=docker-compose.prod.yml SERVICE_NAME=helpmefindthejob \
#     ./scripts/backup-production.sh
#   HELPMEFINDTHEJOB_BACKUP_BACKEND=rclone HELPMEFINDTHEJOB_BACKUP_REMOTE=s3:my-bucket/dj-scout \
#     ./scripts/backup-production.sh
#   HELPMEFINDTHEJOB_BACKUP_BACKEND=s3 HELPMEFINDTHEJOB_BACKUP_REMOTE=s3://my-bucket/dj-scout \
#     ./scripts/backup-production.sh
#   HELPMEFINDTHEJOB_BACKUP_DRY_RUN=1 ./scripts/backup-production.sh
#
# Off-host backends (set HELPMEFINDTHEJOB_BACKUP_BACKEND):
#   local   (default) — leave tarball under $BACKUP_DIR
#   rclone           — also `rclone copy` to $HELPMEFINDTHEJOB_BACKUP_REMOTE
#   s3 / aws         — also `aws s3 cp` to $HELPMEFINDTHEJOB_BACKUP_REMOTE
#
# Encryption + secrets warning:
#   * Tarballs include sqlite databases with hashed credentials. Treat
#     them like production data.
#   * Rotate AWS / rclone credentials by environment, never commit them.
#   * For at-rest encryption, store the bucket with KMS or GPG-encrypt
#     the tarball before upload (`gpg --symmetric` is one option).
#
# Exit codes:
#   0  archive written (and uploaded if requested)
#   1  backup failed
#   2  required tooling missing

set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
SERVICE_NAME="${SERVICE_NAME:-helpmefindthejob}"
DATA_DIR_IN_CONTAINER="${DATA_DIR_IN_CONTAINER:-/app/data}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKEND="${HELPMEFINDTHEJOB_BACKUP_BACKEND:-local}"
REMOTE="${HELPMEFINDTHEJOB_BACKUP_REMOTE:-}"
DRY_RUN="${HELPMEFINDTHEJOB_BACKUP_DRY_RUN:-0}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE_NAME="helpmefindthejob-${TIMESTAMP}.tar.gz"

if [ "$DRY_RUN" = "1" ]; then
  echo "backup: DRY RUN — backend=$BACKEND remote=${REMOTE:-(none)} dir=$BACKUP_DIR"
  case "$BACKEND" in
    local) echo "backup: would write tarball to $BACKUP_DIR/$ARCHIVE_NAME" ;;
    rclone)
      command -v rclone >/dev/null 2>&1 || { echo "backup: rclone not installed" >&2; exit 2; }
      [ -n "$REMOTE" ] || { echo "backup: HELPMEFINDTHEJOB_BACKUP_REMOTE missing" >&2; exit 2; }
      echo "backup: would 'rclone copy <tarball> $REMOTE'"
      ;;
    s3|aws)
      command -v aws >/dev/null 2>&1 || { echo "backup: aws CLI not installed" >&2; exit 2; }
      [ -n "$REMOTE" ] || { echo "backup: HELPMEFINDTHEJOB_BACKUP_REMOTE missing" >&2; exit 2; }
      echo "backup: would 'aws s3 cp <tarball> $REMOTE'"
      ;;
    *) echo "backup: unknown HELPMEFINDTHEJOB_BACKUP_BACKEND='$BACKEND'" >&2; exit 2 ;;
  esac
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "backup: docker is required" >&2
  exit 2
fi

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "backup: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

CONTAINER_ID="$(docker compose -f "$COMPOSE_FILE" ps -q "$SERVICE_NAME" || true)"
if [ -z "$CONTAINER_ID" ]; then
  echo "backup: service '$SERVICE_NAME' not running in $COMPOSE_FILE" >&2
  exit 1
fi

echo "backup: snapshotting $DATA_DIR_IN_CONTAINER from $SERVICE_NAME ($CONTAINER_ID)"

# Ask SQLite to write WAL frames back into the main DB file before we copy.
# `.backup` produces a single consistent file per DB.
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

for DB_NAME in company_discovery.sqlite3 auth.sqlite3; do
  echo "backup: dumping $DB_NAME"
  docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" \
    sh -c "test -f $DATA_DIR_IN_CONTAINER/$DB_NAME && \
      python3 - <<'PY' || true
import sqlite3, sys
src = sqlite3.connect('$DATA_DIR_IN_CONTAINER/$DB_NAME')
dst = sqlite3.connect('$DATA_DIR_IN_CONTAINER/$DB_NAME.snapshot')
with dst:
    src.backup(dst)
src.close(); dst.close()
PY"
done

# Pull every relevant file out via docker cp.
echo "backup: copying snapshot files out of the container"
docker cp "$CONTAINER_ID:$DATA_DIR_IN_CONTAINER/." "$SCRATCH/data"

# Drop the snapshot copies inside the container so the volume stays clean.
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" \
  sh -c "rm -f $DATA_DIR_IN_CONTAINER/*.snapshot"

ARCHIVE_PATH="$BACKUP_DIR/$ARCHIVE_NAME"
tar -C "$SCRATCH" -czf "$ARCHIVE_PATH" data
echo "backup: wrote $ARCHIVE_PATH"

echo "backup: contents:"
tar -tzf "$ARCHIVE_PATH" | head -30

case "$BACKEND" in
  local)
    ;;
  rclone)
    if ! command -v rclone >/dev/null 2>&1; then
      echo "backup: rclone is required for backend=rclone" >&2
      exit 2
    fi
    if [ -z "$REMOTE" ]; then
      echo "backup: HELPMEFINDTHEJOB_BACKUP_REMOTE is required for backend=rclone" >&2
      exit 1
    fi
    echo "backup: rclone copy → $REMOTE"
    rclone copy "$ARCHIVE_PATH" "$REMOTE"
    ;;
  s3|aws)
    if ! command -v aws >/dev/null 2>&1; then
      echo "backup: aws CLI is required for backend=$BACKEND" >&2
      exit 2
    fi
    if [ -z "$REMOTE" ]; then
      echo "backup: HELPMEFINDTHEJOB_BACKUP_REMOTE is required (e.g. s3://bucket/prefix)" >&2
      exit 1
    fi
    echo "backup: aws s3 cp → $REMOTE"
    aws s3 cp "$ARCHIVE_PATH" "$REMOTE/$(basename "$ARCHIVE_PATH")"
    ;;
  *)
    echo "backup: unknown HELPMEFINDTHEJOB_BACKUP_BACKEND='$BACKEND'" >&2
    exit 1
    ;;
esac

echo "backup: done"
