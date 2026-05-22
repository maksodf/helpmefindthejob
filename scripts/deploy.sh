#!/usr/bin/env sh
# deploy.sh
#
# Single, opinionated deploy command for Helpmefindthejob production.
# Replaces the ad-hoc rsync + docker compose sequence that bit us on
# 2026-05-09 (deploys ran with the dev compose file, which has a bind
# mount to ./data and a fresh-empty database — silently masking the
# real production named volume `helpmefindthejob_data`).
#
# What it does, in order:
#   1. Sanity-check that ``docker-compose.prod.yml`` exists in the cwd.
#      Refuse to continue otherwise — production *must* use that file.
#   2. Take a WAL-aware sqlite snapshot in the running container
#      (scripts/pre-deploy-snapshot.sh, written into /app/data/*.bak).
#   3. Tag the running image as ``:previous-<TAG>`` so a rollback is
#      one ``docker tag`` away.
#   4. ``docker compose -f docker-compose.prod.yml build helpmefindthejob``.
#   5. ``docker compose -f docker-compose.prod.yml up -d helpmefindthejob``.
#   6. Curl /api/health and assert it reports the new APP_VERSION.
#
# Usage (from this repo on the operator's laptop):
#   TAG=0.7.0 SSH_HOST=root@161.35.76.8 SSH_KEY=~/.ssh/helpmefindthejob \
#     PUBLIC_URL=https://app.helpmefindthejob.com ./scripts/deploy.sh
#
# Required environment:
#   TAG          version tag, e.g. "0.7.0"
#   SSH_HOST     deploy target, e.g. "root@161.35.76.8"
#
# Optional:
#   SSH_KEY      ssh -i identity file
#   PUBLIC_URL   for the post-deploy health-check assertion
#   COMPOSE_FILE override (default: docker-compose.prod.yml)
#   SERVICE_NAME override (default: helpmefindthejob)
#   APP_DIR      remote app directory (default: /opt/helpmefindthejob)
set -eu

TAG="${TAG:?TAG is required (e.g. TAG=0.7.0)}"
SSH_HOST="${SSH_HOST:?SSH_HOST is required (e.g. SSH_HOST=root@161.35.76.8)}"
SSH_KEY="${SSH_KEY:-}"
PUBLIC_URL="${PUBLIC_URL:-https://app.helpmefindthejob.com}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
SERVICE_NAME="${SERVICE_NAME:-helpmefindthejob}"
APP_DIR="${APP_DIR:-/opt/helpmefindthejob}"

# SSH multiplexing — one TCP connection shared across the whole deploy
# (ssh probe + snapshot + 5 rsyncs + docker compose). Without this,
# fail2ban on the droplet bans us partway through. Cleanup trap below.
SSH_CONTROL_DIR="$(mktemp -d -t djs-deploy-XXXXXX)"
SSH_CTL="$SSH_CONTROL_DIR/cm.sock"
SSH_OPTS="-o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPath=$SSH_CTL -o ControlPersist=60s"

cleanup() {
  if [ -S "$SSH_CTL" ]; then
    if [ -n "$SSH_KEY" ]; then
      ssh -i "$SSH_KEY" -o ControlPath="$SSH_CTL" -O exit "$SSH_HOST" >/dev/null 2>&1 || true
    else
      ssh -o ControlPath="$SSH_CTL" -O exit "$SSH_HOST" >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$SSH_CONTROL_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ssh_cmd() {
  if [ -n "$SSH_KEY" ]; then
    ssh -i "$SSH_KEY" $SSH_OPTS "$SSH_HOST" "$@"
  else
    ssh $SSH_OPTS "$SSH_HOST" "$@"
  fi
}

rsync_cmd() {
  if [ -n "$SSH_KEY" ]; then
    rsync -avz -e "ssh -i $SSH_KEY $SSH_OPTS" "$@"
  else
    rsync -avz -e "ssh $SSH_OPTS" "$@"
  fi
}

echo "deploy: tag=$TAG host=$SSH_HOST app_dir=$APP_DIR compose=$COMPOSE_FILE"

# 1. The prod compose file MUST exist on the remote — otherwise we'd
#    fall back to the dev compose with a bind mount to an empty ./data.
#    This call also opens the SSH ControlMaster socket so subsequent
#    rsync + ssh calls reuse the same TCP connection (avoids fail2ban).
if ! ssh_cmd "test -f $APP_DIR/$COMPOSE_FILE"; then
  echo "deploy: $APP_DIR/$COMPOSE_FILE missing on $SSH_HOST. Refusing to deploy." >&2
  exit 2
fi

# 2. Pre-deploy snapshot (WAL-aware). Pass the ControlMaster socket
#    through so the snapshot reuses the same connection.
echo "deploy: taking WAL-aware snapshot tagged $TAG"
SSH_HOST="$SSH_HOST" SSH_KEY="$SSH_KEY" TAG="$TAG" \
  SSH_CTL="$SSH_CTL" \
  ./scripts/pre-deploy-snapshot.sh

# 3. Sync code.
echo "deploy: rsyncing app code"
rsync_cmd app.py "$SSH_HOST:$APP_DIR/app.py"
rsync_cmd --delete --exclude="__pycache__" company_discovery/ "$SSH_HOST:$APP_DIR/company_discovery/"
rsync_cmd --delete static/ "$SSH_HOST:$APP_DIR/static/"
if [ -f Dockerfile ]; then
  rsync_cmd Dockerfile "$SSH_HOST:$APP_DIR/Dockerfile"
fi
if [ -f requirements.txt ]; then
  rsync_cmd requirements.txt "$SSH_HOST:$APP_DIR/requirements.txt"
fi
# Sync the prod compose file so healthcheck/env additions reach the server.
# (.env values stay on the server only; we only ship the structural file.)
if [ -f "$COMPOSE_FILE" ]; then
  rsync_cmd "$COMPOSE_FILE" "$SSH_HOST:$APP_DIR/$COMPOSE_FILE"
fi

# 4. Tag old image, build new, restart with prod compose.
echo "deploy: tagging previous image, rebuilding, restarting via $COMPOSE_FILE"
ssh_cmd "cd $APP_DIR && \
  docker tag ${SERVICE_NAME}-${SERVICE_NAME}:latest ${SERVICE_NAME}-${SERVICE_NAME}:previous-${TAG} 2>/dev/null || true; \
  docker compose -f $COMPOSE_FILE build $SERVICE_NAME && \
  docker compose -f $COMPOSE_FILE up -d --wait --wait-timeout 60 $SERVICE_NAME"

# 5. Health check.
echo "deploy: waiting for health endpoint"
sleep 4
HEALTH="$(curl -fs "$PUBLIC_URL/api/health" || true)"
echo "deploy: $HEALTH"
case "$HEALTH" in
  *"\"version\": \"$TAG\""*)
    echo "deploy: ok ($TAG live at $PUBLIC_URL)"
    ;;
  *)
    echo "deploy: WARNING — version assertion failed; expected $TAG in /api/health" >&2
    exit 1
    ;;
esac
