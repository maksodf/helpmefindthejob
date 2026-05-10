# Production Deployment Checklist

## What You Need To Provide

Required:

- A domain or subdomain, for example `scout.example.com`.
- DNS access so the domain can point to your server IP.
- A VPS/cloud server with Docker and Docker Compose.
- `DIRECTJOB_SECRET_KEY`: a stable random secret.
- `DIRECTJOB_ADMIN_EMAIL`: the first admin/tester email.
- `DIRECTJOB_ADMIN_PASSWORD`: a long random password, 12+ characters.

Optional:

- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENROUTER_API_KEY` if you want server-side AI execution.
- Otherwise users can use manual handoff, local provider modes where appropriate, or a session-only API key in the web UI.

Generate a secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Deploy

1. Copy `.env.example` to `.env`.
2. Fill in required values.
3. Point DNS `A` record for `DIRECTJOB_DOMAIN` to the server IP.
4. On the server, run:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

5. Check:

```bash
curl https://YOUR_DOMAIN/api/health
```

## Security Controls Implemented

- Password login with PBKDF2 hashing.
- Basic failed-login rate limiting.
- HttpOnly session cookies.
- Secure cookies in production.
- SameSite=Lax cookies.
- CSRF token required for mutating API calls.
- Per-user data isolation through `user_id`.
- Registration closed by default after the first/admin setup.
- Production startup fails without required secrets.
- Security headers and CSP.
- HTTPS reverse proxy via Caddy.
- No raw AI secrets stored by the app UI; session-only API keys are passed only with the `Run AI` request.
- No broad crawling, login bypass, CAPTCHA bypass, or restricted-platform scraping.
- Public career-page fetches reject localhost/private/internal targets.

## Operational Notes

- In-app JSON backups are available in **Settings → Backup &amp; restore**.
- Server-side data-volume snapshots: run `./scripts/backup-production.sh` on the host. The script uses SQLite's online backup API for WAL-safe snapshots and writes a timestamped tarball to `./backups/`.
- Admins can create and manage tester accounts in the **Admin → Tester accounts** panel after signing in. All admin user-management actions are written to `data/admin_audit.log` (one JSON object per line).
- App data is stored in the Docker volume `directjob_data`.
- Caddy stores certificates in `caddy_data`.
- Keep `.env` out of version control.
- Rotate tester passwords from the admin-only **Admin → Tester accounts** panel.

## Smoke Test After Deploy

Run the smoke script against the live URL:

```bash
APP_BASE_URL=https://YOUR_DOMAIN ./scripts/production-smoke.sh
# Optional: include an authenticated probe
ADMIN_EMAIL=... ADMIN_PASSWORD=... \
  APP_BASE_URL=https://YOUR_DOMAIN ./scripts/production-smoke.sh
```

The script verifies `/api/health`, security headers, anonymous bootstrap rejection, and (when admin credentials are supplied) authenticated bootstrap and logout. It never writes to the deployment.

## Restore From Backup

Restore from a tarball produced by `scripts/backup-production.sh`:

```bash
docker compose -f docker-compose.prod.yml stop directjob-scout
SCRATCH=$(mktemp -d)
tar -xzf backups/directjob-scout-YYYYMMDDTHHMMSSZ.tar.gz -C "$SCRATCH"
# Replace the live volume contents
docker run --rm \
  -v directjob_data:/dst \
  -v "$SCRATCH/data":/src \
  alpine sh -c 'rm -rf /dst/* && cp -a /src/. /dst/'
docker compose -f docker-compose.prod.yml start directjob-scout
APP_BASE_URL=https://YOUR_DOMAIN ./scripts/production-smoke.sh
```

Re-test login and bootstrap before re-opening to testers. We recommend a monthly restore drill against a staging instance.

## Rollback

Two rollback paths:

1. **App image only** — re-deploy the prior image:
   ```bash
   docker compose -f docker-compose.prod.yml pull directjob-scout
   docker compose -f docker-compose.prod.yml up -d --no-build directjob-scout
   ```
   Use this when only application code changed.

2. **Code + data** — when a release reshapes data, also restore the latest backup tarball using the Restore section above before starting the rolled-back image.

After any rollback, run the smoke script.

## Recommended Cron

Add host-level cron entries for daily backup + retention pruning + a
weekly restore drill against the most recent tarball:

```cron
15 3 * * *  cd /opt/directjob-scout && DIRECTJOB_BACKUP_BACKEND=rclone DIRECTJOB_BACKUP_REMOTE=$BACKUP_REMOTE ./scripts/backup-production.sh >> backups/backup.log 2>&1
20 4 * * *  cd /opt/directjob-scout && BACKUP_RETENTION_DAYS=30 ./scripts/backup-retention.sh >> backups/retention.log 2>&1
30 5 * * 0  cd /opt/directjob-scout && ./scripts/restore-drill.sh "$(ls -t backups/directjob-scout-*.tar.gz | head -1)" >> backups/restore-drill.log 2>&1
*/5 * * * * cd /opt/directjob-scout && APP_BASE_URL=https://$DIRECTJOB_DOMAIN ./scripts/uptime-check.sh >> backups/uptime.log 2>&1
0 7 * * *   cd /opt/directjob-scout && DOMAIN=$DIRECTJOB_DOMAIN WARN_DAYS=14 ./scripts/tls-expiry-check.sh >> backups/tls.log 2>&1
```

Switch `DIRECTJOB_BACKUP_BACKEND` to `local`, `rclone`, or `s3` based
on what you have available. `local` is fine for the pilot but you
should move backups off-host before commercial pilot.

External uptime + TLS monitoring is intentionally provider-neutral. We
recommend hitting `https://YOUR_DOMAIN/api/health` every 5 minutes from
UptimeRobot, Better Stack, Pingdom, or the operator's own probe. The
`/api/admin/metrics` endpoint additionally exposes user counts, quota
counters, and scheduler state for in-app dashboards.

## Monitoring fields surfaced today

- `GET /api/health` (anonymous) — `status`, `version`, `environment`,
  `registrationOpen`, `schedulerActiveJobs`. Authenticated callers also
  see `quotas` and per-user counts.
- `GET /api/admin/metrics` (admin) — totals across users, scheduler
  records per user, quota usage in the last 24 h, the busiest scan
  domain in the current hour, and any open invitations.

## Email + invitations + password resets

DirectJob Scout uses a provider-neutral email transport. By default the
`ConsoleTransport` records every send to `data/email_outbox.log` and
makes no network call. To enable SMTP in production:

```bash
DIRECTJOB_EMAIL_BACKEND=smtp
DIRECTJOB_SMTP_HOST=smtp.example.com
DIRECTJOB_SMTP_PORT=587
DIRECTJOB_SMTP_USERNAME=apikey-username
DIRECTJOB_SMTP_PASSWORD=apikey-password
DIRECTJOB_SMTP_STARTTLS=true
DIRECTJOB_EMAIL_FROM=no-reply@your-domain.example
DIRECTJOB_PUBLIC_URL=https://YOUR_DOMAIN
```

`DIRECTJOB_PUBLIC_URL` is what we put inside invite and reset emails;
without it, links default to a relative path that only works when the
user opens the email in the same browser session as the app.

## Quotas (env-tunable)

```bash
DIRECTJOB_QUOTA_SCANS_PER_DAY=50
DIRECTJOB_QUOTA_AI_PER_DAY=50
DIRECTJOB_QUOTA_DOMAIN_PER_HOUR=30
DIRECTJOB_QUOTA_ACTIVE_SCANS=3
```

Quota state is persisted in `data/quotas.sqlite3`. Counters are per UTC
day; the per-domain bucket is per UTC hour.

## Known Boundaries

- This is a single-process app; scaling out to multiple replicas would
  need a shared sqlite alternative (Postgres or similar). The pilot is
  fine on a single VPS.
- Email invite + forgot/reset password flows are wired (see Email
  section above). They run on whichever transport you configure
  (`console` or `smtp`).
- Billing has a working manual backend and a Stripe Checkout backend
  (`/api/admin/billing/checkout`). Real Stripe charges still require
  a Stripe account and the env vars listed above.
- The watchlist scheduler runs inside the app process but persists
  state in `data/scheduler.sqlite3` and is crash-safe via WAL +
  orphan recovery. Replace with a dedicated worker if scan volume
  grows past a single host.
- All secrets stay in env vars or session-scoped variables. Backups
  contain hashed credentials; treat tarballs as production data.
