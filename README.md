# DirectJob Scout

DirectJob Scout is a small self-hosted app for finding jobs from direct company career pages, reviewing them, and creating provider-neutral Job Decision Briefs.

It is designed for a controlled pilot:

- The user adds or accepts companies into a watchlist.
- The app scans only known public career pages with robots.txt checks and page limits.
- Discovered jobs are reviewed before import.
- AI analysis works with the user's own provider subscription, or manual handoff mode.

The current build is a working hosted MVP. It is **not yet sellable-ready** — see [`docs/sellable-readiness-gap-analysis.md`](docs/sellable-readiness-gap-analysis.md) for the open work.

## Workflow

After signing in you land on **Today**, then move through:

1. **Companies** — add a company, find or paste its career page URL.
2. **Today / Companies** — Check for new roles.
3. **Discovered Jobs** — review what was found.
4. **AI Brief** — prepare a provider-neutral brief and analyze fit with your own AI subscription.

Settings holds AI provider config, account security, backup/restore, and scan history. Admins also see a Tester Accounts panel.

## Run With Python

Requires Python 3.11+.

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:8765
```

Optional configuration:

```bash
COMPANY_DISCOVERY_DATA_DIR=./data \
COMPANY_DISCOVERY_HOST=127.0.0.1 \
COMPANY_DISCOVERY_PORT=8765 \
python3 app.py
```

## Run With Docker

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8765
```

Data is stored in `./data` by default.

On first local run, create the first account from the sign-in screen. For production, set `DIRECTJOB_ADMIN_EMAIL` and `DIRECTJOB_ADMIN_PASSWORD` instead.

## Deploy Online

Use the production Compose stack with Caddy HTTPS:

```bash
cp .env.example .env
# fill .env with domain, admin email/password, and DIRECTJOB_SECRET_KEY
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Full checklist: [docs/production-deployment.md](docs/production-deployment.md).

For a public deployment, the app requires login, secure cookies, CSRF protection, per-user data isolation, and production startup checks.

## Tester Accounts

The first production account is the admin account from `DIRECTJOB_ADMIN_EMAIL` / `DIRECTJOB_ADMIN_PASSWORD`. After signing in as an admin, open `Tester Accounts` to create tester logins, reset tester passwords, activate/deactivate accounts, or grant/revoke admin role. Testers only need the app URL plus their email/password; they never need SSH or server commands.

## AI Providers

The app does not require one fixed AI vendor. Users can select manual handoff, OpenAI-compatible APIs, Gemini, DeepSeek, OpenRouter, Ollama, Codex CLI, Claude Code, or a custom provider path.

For API providers, users can either reference a server environment variable such as `OPENAI_API_KEY` or enter a session-only API key before clicking `Run AI`. Session keys are sent only with the analysis request and are not saved in the app database or backup export.

## Safety Model

- Password login is required for API access.
- Mutating requests require CSRF tokens.
- User data is scoped by authenticated user.
- No broad crawling.
- No login/CAPTCHA bypass.
- No restricted-platform scraping.
- robots.txt is checked before page fetches.
- Redirect targets are checked independently.
- Scans are bounded by pages, response size, redirects, and delay.

## Backup

Use **Settings → Backup &amp; restore** to export/import a JSON backup. The backup contains watchlist, discovery runs, scans, discovered jobs, imported jobs, schedule settings, and non-secret AI provider configuration.

For server-side snapshots (raw SQLite + JSON), use:

```bash
./scripts/backup-production.sh
```

This produces a timestamped tarball in `./backups/` using SQLite's online backup API for WAL-safe copies.

## Operations Scripts

- `scripts/start.sh` — start the app with the configured host/port.
- `scripts/production-smoke.sh` — black-box smoke check against the deployed URL (anonymous probes plus optional admin-authenticated bootstrap when `ADMIN_EMAIL`/`ADMIN_PASSWORD` are set).
- `scripts/backup-production.sh` — Docker-volume snapshot to a local tarball.
- `scripts/backup-retention.sh` — prune local tarballs older than `BACKUP_RETENTION_DAYS` (default 30).
- `scripts/restore-drill.sh path/to/backup.tar.gz` — restore-drill rehearsal: spins up a sidecar container, restores the backup into a throwaway volume, runs the smoke script, tears down.
- `scripts/run-e2e.sh` — boot the app on a free port and run the Playwright E2E suite. Requires a one-time `pip install playwright && playwright install chromium`.

## Email transport

DirectJob Scout sends invites and password-reset links via the configured
transport. With no SMTP env vars set it defaults to `ConsoleTransport`,
which records every send to `data/email_outbox.log`. To wire up SMTP for
production, set:

```bash
DIRECTJOB_EMAIL_BACKEND=smtp
DIRECTJOB_SMTP_HOST=smtp.example.com
DIRECTJOB_SMTP_PORT=587
DIRECTJOB_SMTP_USERNAME=...
DIRECTJOB_SMTP_PASSWORD=...
DIRECTJOB_SMTP_STARTTLS=true
DIRECTJOB_EMAIL_FROM=no-reply@your-domain.example
DIRECTJOB_PUBLIC_URL=https://app.khalo.org
```

Without `DIRECTJOB_PUBLIC_URL`, links use relative paths and only resolve
when the recipient opens the app on the same domain they were sent from.

## Quotas

Each tester is capped per UTC day at 50 scans and 50 AI analyses by
default. They can run up to 3 concurrent scans, and any one career-page
domain is limited to 30 scans per hour across the whole workspace.
Tune via `DIRECTJOB_QUOTA_*` env vars; see `company_discovery/quotas.py`.

## Legal pages

`/privacy`, `/terms`, `/data-retention` are served as static HTML and
linked from the auth gate footer and Settings. They are written as
product-honest summaries; **counsel must review them before commercial
sale.**

## Admin Audit Log

Admin actions (create user, change role, change active state, reset password) are appended to `data/admin_audit.log` as one JSON object per line. Each entry records the action, actor, target, and timestamp.
