#!/usr/bin/env sh
# pre-deploy-snapshot.sh
#
# Take a *consistent* snapshot of every SQLite database that lives in the
# running production container, *before* a redeploy. Writes the snapshot
# to /app/data/<dbname>.pre-<TAG>.bak inside the container so a rollback
# is one `mv` away.
#
# Why this exists:
#   `cp /app/data/auth.sqlite3 /app/data/auth.sqlite3.bak` is wrong when
#   sqlite is in WAL mode — the main file may only contain schema; the
#   recent rows are in the -wal sidecar. `sqlite3 .backup` (or its
#   Python equivalent, ``conn.backup(other)``) checkpoints first and
#   then produces a single self-contained file.
#
# Usage (run from the operator's laptop):
#   ./scripts/pre-deploy-snapshot.sh                # tag = current UTC date
#   TAG=0.6.0 ./scripts/pre-deploy-snapshot.sh
#
# Environment overrides:
#   COMPOSE_FILE        defaults to docker-compose.prod.yml when present,
#                       otherwise docker-compose.yml.
#   SERVICE_NAME        defaults to helpmefindthejob.
#   DATA_DIR            defaults to /app/data (path inside the container).
#   SSH_HOST            if set, runs the snapshot remotely over ssh
#                       (e.g. SSH_HOST="root@161.35.76.8").
#   SSH_KEY             optional ssh -i identity file.
#
# Exit codes:
#   0  one snapshot per discovered .sqlite3 file written successfully
#   1  could not reach the container or one of the .backup calls failed
#   2  required tooling missing
set -eu

if [ -z "${COMPOSE_FILE:-}" ]; then
  if [ -f docker-compose.prod.yml ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
  else
    COMPOSE_FILE="docker-compose.yml"
  fi
fi
SERVICE_NAME="${SERVICE_NAME:-helpmefindthejob}"
DATA_DIR="${DATA_DIR:-/app/data}"
TAG="${TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
SSH_HOST="${SSH_HOST:-}"
SSH_KEY="${SSH_KEY:-}"
SSH_CTL="${SSH_CTL:-}"  # set by deploy.sh to reuse the ControlMaster socket
SSH_OPTS_BASE="-o StrictHostKeyChecking=no"
if [ -n "$SSH_CTL" ]; then
  SSH_OPTS_BASE="$SSH_OPTS_BASE -o ControlMaster=auto -o ControlPath=$SSH_CTL -o ControlPersist=60s"
fi

run_remote() {
  cmd="$1"
  if [ -n "$SSH_HOST" ]; then
    if [ -n "$SSH_KEY" ]; then
      ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_HOST" "$cmd"
    else
      ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$cmd"
    fi
  else
    sh -c "$cmd"
  fi
}

if ! command -v docker >/dev/null 2>&1 && [ -z "$SSH_HOST" ]; then
  echo "snapshot: docker is required (or set SSH_HOST to a remote host that has it)" >&2
  exit 2
fi

# Single-SSH-call snapshot. Earlier versions ran one ssh per DB which
# tripped fail2ban during deploys. Now we generate the whole shell
# program once and run it in a single ssh exec.
echo "snapshot: tag=$TAG dir=$DATA_DIR (single-ssh)"

REMOTE_PROGRAM=$(cat <<'EOF'
set -eu
SERVICE_NAME="__SERVICE__"
DATA_DIR="__DATA__"
TAG="__TAG__"
CONTAINER_ID="$(docker ps --filter name=${SERVICE_NAME} --format '{{.ID}}' | head -n 1)"
if [ -z "$CONTAINER_ID" ]; then
  echo "snapshot: no running container matching '$SERVICE_NAME'" >&2
  exit 1
fi
echo "snapshot: container=$CONTAINER_ID"
DB_LIST="$(docker exec "$CONTAINER_ID" sh -c "ls $DATA_DIR/*.sqlite3 2>/dev/null")"
if [ -z "$DB_LIST" ]; then
  echo "snapshot: no .sqlite3 files in $DATA_DIR" >&2
  exit 1
fi
docker exec -i "$CONTAINER_ID" python - "$TAG" "$DATA_DIR" <<'PYEOF'
import os, sqlite3, sys, glob
tag = sys.argv[1]
data_dir = sys.argv[2]
ok = 0
for src_path in sorted(glob.glob(os.path.join(data_dir, "*.sqlite3"))):
    name = os.path.basename(src_path)
    dst_path = src_path + f".pre-{tag}.bak"
    if os.path.exists(dst_path):
        os.remove(dst_path)
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dst_path)
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close(); dst.close()
    sys.stdout.write(f"snapshot: {name} -> {os.path.basename(dst_path)}\n")
    ok += 1
sys.stdout.write(f"snapshot: {ok} db(s) backed up\n")
PYEOF
docker exec "$CONTAINER_ID" sh -c "ls -la $DATA_DIR/*.pre-$TAG.bak"
EOF
)

# Substitute env values into the heredoc'd program.
REMOTE_PROGRAM="$(printf '%s' "$REMOTE_PROGRAM" \
  | sed "s|__SERVICE__|$SERVICE_NAME|g; s|__DATA__|$DATA_DIR|g; s|__TAG__|$TAG|g")"

if [ -n "$SSH_HOST" ]; then
  if [ -n "$SSH_KEY" ]; then
    printf '%s\n' "$REMOTE_PROGRAM" | ssh -i "$SSH_KEY" $SSH_OPTS_BASE "$SSH_HOST" sh -s
  else
    printf '%s\n' "$REMOTE_PROGRAM" | ssh $SSH_OPTS_BASE "$SSH_HOST" sh -s
  fi
else
  printf '%s\n' "$REMOTE_PROGRAM" | sh -s
fi

# Off-host backup (optional). Operator sets these env vars to enable
# upload to any S3-compatible target (DigitalOcean Spaces, Backblaze
# B2, Cloudflare R2, AWS S3). Uses awscli inside the container so we
# don't add a dependency to the host.
#
#   DIRECTJOB_BACKUP_S3_BUCKET   target bucket (required to enable)
#   DIRECTJOB_BACKUP_S3_PREFIX   key prefix, e.g. "helpmefindthejob/"
#   DIRECTJOB_BACKUP_S3_ENDPOINT --endpoint-url override (optional)
#   AWS_ACCESS_KEY_ID            forwarded into the container
#   AWS_SECRET_ACCESS_KEY        forwarded into the container
#   AWS_DEFAULT_REGION           e.g. "fra1" for DO Spaces
if [ -n "${DIRECTJOB_BACKUP_S3_BUCKET:-}" ]; then
  echo "snapshot: uploading off-host to s3://$DIRECTJOB_BACKUP_S3_BUCKET"
  UPLOAD_PROGRAM=$(cat <<'EOF'
set -eu
SERVICE_NAME="__SERVICE__"
DATA_DIR="__DATA__"
TAG="__TAG__"
BUCKET="__BUCKET__"
PREFIX="__PREFIX__"
ENDPOINT_FLAG="__ENDPOINT_FLAG__"
CONTAINER_ID="$(docker ps --filter name=${SERVICE_NAME} --format '{{.ID}}' | head -n 1)"
docker exec "$CONTAINER_ID" sh -c "command -v aws || pip install --quiet awscli >&2"
for f in $(docker exec "$CONTAINER_ID" sh -c "ls $DATA_DIR/*.pre-$TAG.bak"); do
  name="$(basename "$f")"
  echo "snapshot: -> s3://$BUCKET/$PREFIX$name"
  docker exec -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION "$CONTAINER_ID" \
    aws $ENDPOINT_FLAG s3 cp "$f" "s3://$BUCKET/$PREFIX$name"
done
EOF
)
  endpoint_flag=""
  if [ -n "${DIRECTJOB_BACKUP_S3_ENDPOINT:-}" ]; then
    endpoint_flag="--endpoint-url $DIRECTJOB_BACKUP_S3_ENDPOINT"
  fi
  prefix="${DIRECTJOB_BACKUP_S3_PREFIX:-helpmefindthejob/}"
  UPLOAD_PROGRAM="$(printf '%s' "$UPLOAD_PROGRAM" \
    | sed "s|__SERVICE__|$SERVICE_NAME|g; s|__DATA__|$DATA_DIR|g; s|__TAG__|$TAG|g; s|__BUCKET__|$DIRECTJOB_BACKUP_S3_BUCKET|g; s|__PREFIX__|$prefix|g; s|__ENDPOINT_FLAG__|$endpoint_flag|g")"
  if [ -n "$SSH_HOST" ]; then
    if [ -n "$SSH_KEY" ]; then
      printf '%s\n' "$UPLOAD_PROGRAM" | ssh -i "$SSH_KEY" $SSH_OPTS_BASE "$SSH_HOST" \
        env AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
            AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
            AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-}" \
        sh -s
    else
      printf '%s\n' "$UPLOAD_PROGRAM" | ssh $SSH_OPTS_BASE "$SSH_HOST" \
        env AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
            AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
            AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-}" \
        sh -s
    fi
  else
    printf '%s\n' "$UPLOAD_PROGRAM" | sh -s
  fi
fi
