# DirectJob Scout — Deployment handoff

Last updated: 2026-05-09. App version target: **0.4.0**.

This document is the operator's runbook for taking the local Pass-4-complete
workspace live on `https://app.khalo.org`. It assumes:

- You have SSH to the production VPS: `root@161.35.76.8`.
- Production currently lives under `/opt/directjob-scout`.
- The local workspace can be copied to the host with `scp`/`rsync` or, if
  you later put this project under git, pulled on the host.
- `docker compose -f docker-compose.prod.yml` already brought the older
  build live previously.

Before any change to production, **run the readiness check locally** and the
**restore drill** in a sidecar (both documented below). Do not deploy until
the operator + user explicitly approves.

## 1. Pre-flight on your laptop

```bash
# 1. Validate the local workspace you are about to deploy
python3 -m py_compile app.py mcp_server.py company_discovery/*.py tests/*.py tests/e2e/*.py
node --check static/app.js
for f in scripts/*.sh; do sh -n "$f"; done
docker compose -f docker-compose.prod.yml --env-file .env.example config >/dev/null
python3 -m unittest discover -s tests
```

All commands must exit clean. The unittest run is expected to show
`OK (skipped=9)` — those 9 are the Playwright suite, which runs separately.

```bash
# 3. Optional: run the Playwright suite
pip install playwright
playwright install chromium
./scripts/run-e2e.sh    # should print "Ran 9 tests in <X>s — OK"
```

```bash
# 4. Readiness check against the live env-file
ENV_FILE=/path/to/production.env ./scripts/production-readiness-check.sh
```

The script prints each signal with status `ok | partial | missing` and
exits 0 / 1 / 2 accordingly.

What to do when the script exits non-zero:

- **Exit 2 (missing)** — at least one critical operator input is not
  set. Resolve every `missing` row before deploying. Common cases are
  no `DIRECTJOB_MONITORING_URL` and no off-host backup target.
- **Exit 1 (partial)** — every input is set but at least one is in a
  pilot-grade state (e.g. ConsoleTransport email, manual billing,
  `DIRECTJOB_LEGAL_REVIEWED=false`). You can deploy, but plan the
  follow-up to flip those rows to `ok` before commercial sale.
- **Exit 0 (ok)** — green to deploy.

If you only want to confirm the *script itself* is wired correctly and
do not have real credentials yet, run it against the all-green sample:

```bash
ENV_FILE=deploy/readiness-fake.env ./scripts/production-readiness-check.sh
# expected: every row OK and exit 0 — but never deploy with this file.
```

The fake env sets `DIRECTJOB_READINESS_ALLOW_UNINITIALIZED_RUNTIME=true`
so the scheduler DB and audit log can be treated as OK before any app
process has created them. Do not set that flag in production.

## 2. Where production credentials live

The operator owns **one** `.env` file on the server. For the current
DigitalOcean droplet, keep it at:

```text
/opt/directjob-scout/.env
```

Use owner `root:root`, mode `0600`. It contains:

- `DIRECTJOB_DOMAIN`, `DIRECTJOB_PUBLIC_URL`
- `DIRECTJOB_SECRET_KEY` — generate with
  `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`
- `DIRECTJOB_ADMIN_EMAIL`, `DIRECTJOB_ADMIN_PASSWORD` — initial admin login
- `DIRECTJOB_EMAIL_BACKEND=smtp` + the four `DIRECTJOB_SMTP_*` vars +
  `DIRECTJOB_EMAIL_FROM`
- `DIRECTJOB_BACKUP_BACKEND=rclone` (or `s3` / `local`) +
  `DIRECTJOB_BACKUP_REMOTE`
- `DIRECTJOB_MONITORING_URL` (the URL to ping or push to) and
  `DIRECTJOB_LOG_TARGET`
- `DIRECTJOB_LEGAL_REVIEWED=true` only after counsel review
- `DIRECTJOB_BILLING_BACKEND=manual` (default) or `stripe` plus the
  Stripe env vars (api key, price IDs, success/cancel URLs)
- Optional AI provider env keys

The Caddyfile uses `DIRECTJOB_DOMAIN`. The compose file uses every
variable above.

## 3. Backup the live server first

```bash
ssh -i ~/.ssh/directjob_scout root@161.35.76.8
cd /opt/directjob-scout
./scripts/backup-production.sh         # local tarball under ./backups
# Optional: push off-host if rclone/aws is configured
DIRECTJOB_BACKUP_BACKEND=rclone DIRECTJOB_BACKUP_REMOTE=remote:bucket/dj-scout \
  ./scripts/backup-production.sh
ls -lh backups/ | head
```

Capture the tarball path before continuing. Restore-drill it locally if you
have the budget (Stage A below).

## 4. Roll out

From your laptop, sync the updated app files to the server. Do not copy
`data/`, `backups/`, local caches, or `.env`.

```bash
rsync -az --delete \
  --exclude '.env' --exclude 'data/' --exclude 'backups/' \
  --exclude '__pycache__/' --exclude '.DS_Store' \
  ./ root@161.35.76.8:/opt/directjob-scout/
```

If `rsync` is unavailable, use `scp -r` for the project files and preserve the
server-side `/opt/directjob-scout/.env`, `/opt/directjob-scout/data`, and
`/opt/directjob-scout/backups`.

```bash
ssh -i ~/.ssh/directjob_scout root@161.35.76.8
cd /opt/directjob-scout
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f directjob-scout | head -80
```

Watch for the line `Company Discovery app running at http://0.0.0.0:8765`
and exit the log tail.

## 5. Verify (smoke + readiness)

```bash
APP_BASE_URL=https://app.khalo.org ./scripts/production-smoke.sh
APP_BASE_URL=https://app.khalo.org ADMIN_EMAIL=$DIRECTJOB_ADMIN_EMAIL \
  ADMIN_PASSWORD=$DIRECTJOB_ADMIN_PASSWORD ./scripts/production-smoke.sh

ENV_FILE=.env ./scripts/production-readiness-check.sh

DOMAIN=app.khalo.org WARN_DAYS=14 ./scripts/tls-expiry-check.sh
APP_BASE_URL=https://app.khalo.org ./scripts/uptime-check.sh

curl -s https://app.khalo.org/api/health | python3 -m json.tool | head
# `version` should now show "0.4.0"
```

Sign in to `https://app.khalo.org` as the admin and:

1. Open **Admin → Production readiness** — every signal should be `ok` or
   `partial` with explanation. No `missing`.
2. Click **Send test email** with your own address → confirm receipt
   (or, in console mode, confirm the line in `data/email_outbox.log`
   inside the container).
3. Open **Admin → Tester accounts**, create a test invite to your own
   address, click the magic link, set a password, sign in. Then delete
   that test account from the admin panel.
4. Click **Settings → Privacy → Request deletion** as the test account
   to verify the deletion-request UX (admin sees it under Support tickets).
5. Confirm the friend you onboarded in the previous deployment can still
   sign in (their session may have expired; have them sign in fresh).

## 6. Rollback

If anything looks wrong:

```bash
docker compose -f docker-compose.prod.yml down
# Re-tag the prior image and roll forward:
docker tag nassermcpserver-directjob-scout:previous nassermcpserver-directjob-scout:latest
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

If you need to restore data (a release reshaped persistence — none of
the changes in this pass do, but treat it as a possibility):

```bash
docker compose -f docker-compose.prod.yml stop directjob-scout
SCRATCH=$(mktemp -d)
tar -xzf backups/<tarball>.tar.gz -C "$SCRATCH"
docker run --rm -v directjob_data:/dst -v "$SCRATCH/data":/src alpine \
  sh -c 'rm -rf /dst/* && cp -a /src/. /dst/'
docker compose -f docker-compose.prod.yml start directjob-scout
APP_BASE_URL=https://app.khalo.org ./scripts/production-smoke.sh
```

## 7. After-deploy checklist

- [ ] Live `/api/health` reports `version: 0.4.0`
- [ ] Smoke script (anonymous + authenticated) passes
- [ ] Readiness check exits with the expected status
- [ ] TLS expiry > 14 days
- [ ] External uptime monitor green for 15 min
- [ ] Backup cron configured and tested
- [ ] Admin can send a test email
- [ ] Friend can log in
- [ ] Audit log (`docker compose exec directjob-scout cat /app/data/admin_audit.log`)
  shows your admin actions
- [ ] `./scripts/log-redaction-check.sh` exits 0 (no SMTP password / Stripe
  key / pbkdf2 hash / bearer token / invitation token leaked into
  container logs)

If any item fails, treat it as a deploy failure and roll back.

### Privacy: data export before deletion

If a tester requests deletion (Settings → Privacy → Request deletion),
the admin should:

1. Take a JSON archive of the user's data:
   `curl -b cookies -H "X-CSRF-Token: $CSRF" \
        https://app.khalo.org/api/admin/users/<id>/export > export.json`
2. Hand the archive to the tester for their records.
3. Delete the account: `Admin → Tester accounts → Delete user`.
4. Confirm the audit log shows `export_user_data` and `delete_user`
   for that user.

## 8. Operator quick reference

| Task | Command |
|---|---|
| Backup now | `./scripts/backup-production.sh` |
| Restore drill (sidecar) | `./scripts/restore-drill.sh backups/<tarball>.tar.gz` |
| Smoke | `APP_BASE_URL=https://app.khalo.org ./scripts/production-smoke.sh` |
| Readiness | `ENV_FILE=.env ./scripts/production-readiness-check.sh` |
| TLS check | `DOMAIN=app.khalo.org ./scripts/tls-expiry-check.sh` |
| Uptime check | `APP_BASE_URL=https://app.khalo.org ./scripts/uptime-check.sh` |
| Tail audit log | `docker compose exec directjob-scout tail -f /app/data/admin_audit.log` |
| Verify SMTP | Admin → Email backend → Send test email |
| Verify backup | `./scripts/backup-production.sh && ls -lh backups | head` |
| Verify friend can log in | Visit `https://app.khalo.org`, ask them to sign in |
| Log redaction check | `./scripts/log-redaction-check.sh` |
| Backup dry-run | `DIRECTJOB_BACKUP_DRY_RUN=1 DIRECTJOB_BACKUP_BACKEND=rclone DIRECTJOB_BACKUP_REMOTE=... ./scripts/backup-production.sh` |
| Export user before delete | `curl -b cookies -H "X-CSRF-Token: $CSRF" $URL/api/admin/users/<id>/export > export.json` |
| Sample readiness fixture | `ENV_FILE=deploy/readiness-fake.env ./scripts/production-readiness-check.sh` |

## 9. What's still external-only

| Item | Required from |
|---|---|
| SMTP credentials | Operator |
| Off-host encrypted backup destination | Operator |
| Uptime + log shipping vendor account | Operator |
| Stripe API key + price IDs (if billing live) | Operator |
| Counsel review of legal pages → set `DIRECTJOB_LEGAL_REVIEWED=true` | Counsel |
| External penetration test | Pen-test vendor |
| Production deployment approval | User |
