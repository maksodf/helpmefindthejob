# Incident playbook

One page. Read this when prod is on fire. Last updated 2026-05-10.

## Roles

| Role | Owner | Contact |
|---|---|---|
| Incident commander | Operator | (whoever opens the playbook) |
| Comms lead | Operator | same person, solo for now |
| Tech lead | Operator | same person, solo for now |

When team grows past 1 human, split these. Until then: one phone, one runbook.

## Severity ladder

- **SEV-1** — site down, login broken, or active data loss. Comms within 15 min.
- **SEV-2** — major feature broken (discovery, AI) but workarounds exist. Comms within 60 min.
- **SEV-3** — minor degradation, cosmetic, single-user. No comms required; track in support.

## First five minutes — triage

1. **Confirm the report.** Hit `https://app.helpmefindthejob.org/api/health`. If 200, go look at what the user was actually doing. If 5xx or timeout, treat as SEV-1 and continue.
2. **Check Better Stack.** Open the source `helpmefindthejob-prod`. Recent error spikes? Container restart loops? OOM lines?
3. **SSH and get container state.**
   ```sh
   ssh -i ~/.ssh/helpmefindthejob root@161.35.76.8 \
     'cd /opt/helpmefindthejob && docker compose -f docker-compose.prod.yml ps && docker compose -f docker-compose.prod.yml logs --tail=200 helpmefindthejob'
   ```
4. **Decide:** restart, rollback, or hold. Restart is safe; rollback is faster than fixing forward when the bad release was just deployed.

## Rollback to previous image

The deploy script tags `:previous-<TAG>` before each build, so:

```sh
ssh -i ~/.ssh/helpmefindthejob root@161.35.76.8 'bash -s' <<'EOF'
set -eu
cd /opt/helpmefindthejob
PREV=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep ':previous-' | head -1)
[ -n "$PREV" ] || { echo "no previous tag found" >&2; exit 1; }
docker tag "$PREV" helpmefindthejob:latest
docker compose -f docker-compose.prod.yml up -d --wait --wait-timeout 60
EOF
```

If `--wait` fails, check `docker compose logs` and either let the previous container keep serving or manually tag a known-good earlier image.

## Restart only

```sh
ssh -i ~/.ssh/helpmefindthejob root@161.35.76.8 \
  'cd /opt/helpmefindthejob && docker compose -f docker-compose.prod.yml restart helpmefindthejob'
```

## Restore from backup

If data is corrupted, do **not** restart — that compounds. Use the sidecar restore drill against a recent off-host backup:

```sh
# Pull most recent backup tarball locally first
rclone copy "b2:${B2_BACKUP_BUCKET:?set B2_BACKUP_BUCKET}/$(rclone ls "b2:${B2_BACKUP_BUCKET}" | sort -k 2 | tail -1 | awk '{print $2}')" ./backups/
./scripts/restore-drill.sh ./backups/<that-tarball>
```

Drill verifies the backup is good. Once drill passes, **stop live traffic** (Caddy maintenance page or 503), switch the named volume in compose, restart.

## Common failures

| Symptom | Probable cause | First action |
|---|---|---|
| 502 Bad Gateway | App container down or unhealthy | `docker compose ps`, then logs, then restart |
| 5xx spike but app up | Upstream provider 429/down (Brave/Adzuna) | Check `/api/admin/readiness` provider statuses; degrade if needed |
| `account_deletion_pending` not running | Cron not installed or container can't write to volume | `crontab -l`; check `data/admin_audit.log` for write errors |
| Login broken for everyone | Bad migration or env var; secret-key change | Rollback. Always rollback. Don't try to fix login forward. |
| TLS expiry | Caddy auto-renew failed | `docker logs caddy`; if ACME bounce, check CAA records and DNS |
| Backup cron silent failure | rclone creds rotated, or B2 bucket renamed | `tail /var/log/helpmefindthejob-backup.log`; re-test with `--dry-run` |

## Comms templates

### SEV-1 user-facing (status page + email):

> **Investigating** — Some users are reporting issues with Helpmefindthejob. We are looking into it now and will update within 30 minutes.

### SEV-1 resolution:

> **Resolved** — Helpmefindthejob was unavailable from <start UTC> to <end UTC>. Cause: <one-line>. We have <fix one-line>. Sorry for the disruption.

### SEV-2 user-facing:

> **Degraded** — <specific feature, e.g. "AI analysis"> is currently unavailable. The rest of the app works. We expect a fix within <hours>. No data was lost.

Keep the language calm. No "thrilled to announce", no marketing voice. People who hit a status page are stressed.

## Post-incident

Within 48 h of SEV-1 or SEV-2:

1. Write a 1-page note in `docs/incidents/YYYY-MM-DD-<slug>.md` (folder created on first incident).
2. **What broke. Why. What we changed to prevent recurrence.** Three sections, no preamble.
3. If a memory-worthy lesson came out of it (deploy gotcha, infra gotcha, vendor weirdness), add a one-liner to the project memory under `gotchas`.
4. Public post-mortems are optional at this stage; a private incident note is sufficient.

## When NOT to act

- **The user is the only report and you can't reproduce.** Investigate calmly. Don't restart prod for a single un-reproduced report.
- **You're outside your normal hours and the issue is SEV-3.** It can wait.
- **You have not slept and the impulse is to ship a fix.** This is how data gets corrupted. Restart, hand off, sleep, fix tomorrow.
