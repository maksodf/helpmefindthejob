#!/usr/bin/env sh
# backup-retention.sh
#
# Prune local backup tarballs older than $BACKUP_RETENTION_DAYS days.
#
# Usage:
#   BACKUP_DIR=./backups BACKUP_RETENTION_DAYS=30 ./scripts/backup-retention.sh
#
# Default: keep the last 30 days of tarballs in ./backups.

set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DAYS="${BACKUP_RETENTION_DAYS:-30}"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "retention: $BACKUP_DIR does not exist; nothing to do"
  exit 0
fi

echo "retention: pruning *.tar.gz older than $DAYS days from $BACKUP_DIR"
find "$BACKUP_DIR" -type f -name 'helpmefindthejob-*.tar.gz' -mtime +"$DAYS" -print -delete
echo "retention: done"
