# DirectJob Scout — Operator package (Pass 5.3)

This document is the single sheet you hand the operator before
deploying 0.4.0 to `https://app.khalo.org`. It complements
`docs/deployment-handoff.md` (the rollout sequence). Use both.

Last updated: 2026-05-09. App version target: **0.4.0**.

## Production env template

`deploy/production.env.template` is the only file that should be
copied to the host as the basis for `/opt/directjob-scout/.env`. It
contains placeholders only — no fake secrets. Never deploy
`deploy/readiness-fake.env`; that file is for offline readiness tests
only.

## A. Credential checklist

Before deploy, an operator must collect or decide:

- [ ] **DIRECTJOB_DOMAIN + DIRECTJOB_PUBLIC_URL** — the live domain
      (e.g. `app.khalo.org` and `https://app.khalo.org`).
- [ ] **DIRECTJOB_SECRET_KEY** — generate with
      `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
      Store once; rotate only via a planned admin reset.
- [ ] **DIRECTJOB_ADMIN_EMAIL + DIRECTJOB_ADMIN_PASSWORD** — initial
      admin. The password must be ≥ 12 chars.
- [ ] **SMTP**: `DIRECTJOB_EMAIL_BACKEND=smtp` plus
      `DIRECTJOB_SMTP_HOST`, `DIRECTJOB_SMTP_PORT`,
      `DIRECTJOB_SMTP_USERNAME`, `DIRECTJOB_SMTP_PASSWORD`,
      `DIRECTJOB_SMTP_STARTTLS=true`, `DIRECTJOB_EMAIL_FROM`. Until
      these are set, invites + reset links go to
      `data/email_outbox.log` only.
- [ ] **Off-host backup**: `DIRECTJOB_BACKUP_BACKEND` (`local` |
      `rclone` | `s3`) plus `DIRECTJOB_BACKUP_REMOTE`. The matching
      CLI (`rclone`, `aws`) must be installed on the host.
- [ ] **Monitoring**: `DIRECTJOB_MONITORING_URL` and
      `DIRECTJOB_LOG_TARGET`. Any vendor that pings HTTPS + accepts
      log lines.
- [ ] **Legal**: counsel review of `static/{privacy,terms,
      data-retention}.html`, then `DIRECTJOB_LEGAL_REVIEWED=true`.
- [ ] **Billing**: confirm `DIRECTJOB_BILLING_BACKEND=manual` for the
      pilot, or set `=stripe` plus the four Stripe values.
- [ ] **Optional AI keys**: `OPENAI_API_KEY` etc. Only if you want
      server-side AI execution; otherwise testers paste a session-only
      key in the UI.

Leave **`DIRECTJOB_READINESS_ALLOW_UNINITIALIZED_RUNTIME`** unset in
production. It is a preflight-only readiness escape hatch.

## B. Deployment checklist

Run from your laptop, in order:

- [ ] Pull the verified branch into the local workspace.
- [ ] `python3 -m py_compile app.py mcp_server.py company_discovery/*.py tests/*.py tests/e2e/*.py`
- [ ] `node --check static/app.js`
- [ ] `for f in scripts/*.sh; do sh -n "$f"; done`
- [ ] `docker compose -f docker-compose.prod.yml --env-file .env.example config >/dev/null`
- [ ] `python3 -m unittest discover -s tests` — expect `Ran 134 tests, OK (skipped=9)`.
- [ ] `env PATH=/private/tmp/directjob-e2e-venv/bin:$PATH ./scripts/run-e2e.sh` — expect 9 specs OK.
- [ ] `ENV_FILE=/path/to/production.env ./scripts/production-readiness-check.sh` — read the exit code:
      - `0` go,
      - `1` go but plan follow-ups,
      - `2` stop and fix every `missing` row.
- [ ] `ssh -i ~/.ssh/directjob_scout root@161.35.76.8`, then on the
      host: `cd /opt/directjob-scout && ./scripts/backup-production.sh`.
      Capture the tarball path.
- [ ] Back on your laptop:
      `rsync -az --delete --exclude '.env' --exclude 'data/' --exclude 'backups/' --exclude '__pycache__/' --exclude '.DS_Store' ./ root@161.35.76.8:/opt/directjob-scout/`
- [ ] On the host:
      `docker compose -f docker-compose.prod.yml --env-file .env up -d --build`
- [ ] Wait for the log line "Company Discovery app running at http://0.0.0.0:8765".

## C. Rollback checklist

Trigger immediately if any post-deploy check below fails.

- [ ] `docker compose -f docker-compose.prod.yml down`
- [ ] If a previous image tag exists:
      `docker tag nassermcpserver-directjob-scout:previous nassermcpserver-directjob-scout:latest`
      then `docker compose -f docker-compose.prod.yml --env-file .env up -d`.
- [ ] If data shape changed (no current 0.4.0 changes do):
      stop, restore the latest backup tarball:
      ```
      docker compose -f docker-compose.prod.yml stop directjob-scout
      SCRATCH=$(mktemp -d)
      tar -xzf backups/<tarball>.tar.gz -C "$SCRATCH"
      docker run --rm -v directjob_data:/dst -v "$SCRATCH/data":/src alpine \
        sh -c 'rm -rf /dst/* && cp -a /src/. /dst/'
      docker compose -f docker-compose.prod.yml start directjob-scout
      ```
- [ ] `APP_BASE_URL=https://app.khalo.org ./scripts/production-smoke.sh`
- [ ] Confirm `curl -s https://app.khalo.org/api/health` reports the
      previous version.
- [ ] Tell the user (clearly) what failed and what was rolled back.

## D. Post-deploy verification checklist

- [ ] `APP_BASE_URL=https://app.khalo.org ./scripts/production-smoke.sh` — anonymous probes pass.
- [ ] `APP_BASE_URL=https://app.khalo.org ADMIN_EMAIL=$DIRECTJOB_ADMIN_EMAIL ADMIN_PASSWORD=$DIRECTJOB_ADMIN_PASSWORD ./scripts/production-smoke.sh` — authenticated probe passes.
- [ ] `ENV_FILE=/opt/directjob-scout/.env ./scripts/production-readiness-check.sh` — all rows `ok`/`partial`. Resolve any `missing`.
- [ ] `DOMAIN=app.khalo.org WARN_DAYS=14 ./scripts/tls-expiry-check.sh` — exits 0.
- [ ] `APP_BASE_URL=https://app.khalo.org ./scripts/uptime-check.sh` — exits 0.
- [ ] `./scripts/log-redaction-check.sh` (on the host, against the live container) — exits 0.
- [ ] `curl -s https://app.khalo.org/api/health` shows `version: 0.4.0`.
- [ ] Sign in as the admin and open **Admin → Production readiness** — every row green or `partial` with explanation.
- [ ] Click **Admin → Email backend → Send test email** to your own address — confirm receipt.
- [ ] Click **Admin → Tester accounts → Send invite** to a personal address; click the invite link, set a password, sign in.
- [ ] As that tester, click **Settings → Privacy → Request deletion** — confirm a ticket appears under **Admin → Support**.
- [ ] Audit log shows `send_invite`, `send_test_email`, and `update_active`/`delete_user` actions you triggered.
- [ ] External uptime monitor shows green for at least 15 minutes.

If any item fails, **roll back per §C**.

## E. Friend-tester acceptance checklist

For each friend-tester invited to the pilot:

- [ ] You created their account via **Admin → Send invitation**.
- [ ] They received the email at the configured `DIRECTJOB_EMAIL_FROM`
      domain (or you handed the link manually if the SMTP backend is
      `console`).
- [ ] They successfully clicked the link, set a password, and signed
      in.
- [ ] The Today view loads, the onboarding checklist renders, and the
      Companies / Discovered Jobs / AI Brief / Settings views are all
      reachable.
- [ ] They cannot see the Admin sidebar item (member role only).
- [ ] They added a company, ran a manual scan, and either reviewed a
      discovered role or hit the "paste jobs manually" fallback
      successfully.
- [ ] They prepared an AI brief (manual mode at minimum) and could
      copy the prompt.
- [ ] They were able to log out and log back in.
- [ ] On their phone, the sidebar collapses correctly to the top tab
      bar and the dashboard is usable.
- [ ] You verified their daily quotas are intact in **Admin →
      Workspace metrics**.

## F. Sellable-ready definition

We may call DirectJob Scout **sellable-ready** only when every row
below is YES. Until then, the headline of the final report stays
**Sellable-ready: NO**.

| Item | Required value |
|---|---|
| Live `https://app.khalo.org/api/health` `version` field | `0.4.0` (or newer) |
| Anonymous + authenticated `production-smoke.sh` | both pass |
| `production-readiness-check.sh` against the live `.env` | exit 0 (or exit 1 with every `partial` row formally accepted) |
| TLS expiry | > 14 days |
| Uptime probe | green for ≥ 24 h |
| `log-redaction-check.sh` on the live container | exit 0 |
| SMTP path | confirmed by **Send test email** + a real invite + reset round-trip |
| Off-host backup | configured, last tarball uploaded, restore drill rehearsed |
| Monitoring + log target | configured at the chosen vendor; alarms documented |
| Legal pages | counsel-reviewed; `DIRECTJOB_LEGAL_REVIEWED=true` |
| Billing | manual accepted **or** Stripe configured + first checkout session created |
| External pen-test | engagement done OR formally deferred for unpaid pilot only |
| Friend-tester acceptance | at least one tester completes the §E list |

If any single row is NO, the product is a high-quality pilot — not
sellable-ready — and the operator package above stays the live source
of truth.

## G. Where to look first when something breaks

| Symptom | First place to look |
|---|---|
| Live `/api/health` not 0.4.0 | Did `rsync` succeed? Did `docker compose up -d --build` finish? Tail container logs. |
| Smoke fails on `/api/auth/status` | App didn't start. Check container logs for "production_config_error". |
| Smoke fails on security headers | Caddy not in front of the app or HTTPS not terminated. Check Caddyfile. |
| Readiness shows `missing` | A required env var is absent in the live `.env`. Compare against `deploy/production.env.template`. |
| Readiness shows `partial` | Pilot-grade default (e.g. console email, manual billing). Decide whether to accept or upgrade. |
| Test email not delivered | Inspect `data/email_outbox.log`. If empty, SMTP not connecting; if populated, your provider rejected the From-domain. |
| Backup script complains about CLI missing | Install `rclone` or `aws` on the host, or set `DIRECTJOB_BACKUP_BACKEND=local`. |
| Restore drill fails | Build the production image first (`docker compose ... build directjob-scout`); the drill needs `nassermcpserver-directjob-scout:latest`. |
| Friend cannot log in | They are deactivated (admin re-activates) or password rate-limited (10 / 10 minutes per IP). |
| Audit log empty | Admin actions create the file on first action. The "partial" readiness state for `admin_audit` is expected on day one. |
