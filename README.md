# DirectJob Scout

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

DirectJob Scout is a self-hosted, chat-driven job-hunting copilot. You talk to an assistant, it pulls roles from multiple sources, and walks you through a guided journey from discovery to a tailored CV and motivation letter — using your own AI provider subscription, or a managed Pro tier.

It combines three parallel discovery rails:

- **Career-page monitoring** of companies you add to your watchlist (with robots.txt checks and page limits).
- **Live job-aggregator search** across Adzuna, Indeed, LinkedIn, and other configurable providers.
- **Bookmarklet captures** for saving roles you find on third-party sites.

Discovered jobs flow into a review queue, then into an AI-assisted pipeline that scores fit, tailors your CV per role, drafts cover letters, and tracks which CV variant gets replies.

The current build is a working hosted MVP. It is **not yet sellable-ready** — see [`docs/sellable-readiness-gap-analysis.md`](docs/sellable-readiness-gap-analysis.md) for the open work, and [`keepbuildingtill100%tracker.MD`](keepbuildingtill100%tracker.MD) for the live roadmap.

## How It Works

After signing in you land on **Today** with a chat sidebar as the primary interface. Type a slash command or natural language and the assistant handles the rest:

- `/find a job` — starts the 12-phase journey wizard
- `add Charité` — adds a company to your watchlist
- `/profile`, `/applied`, `/new-search`, `/help` — direct commands
- Natural language ("suche stelle in Berlin", "find data engineer roles") is routed via keyword + AI intent fallback

### The Job-Search Journey (12 phases)

1. **Greet** — clarify what you're looking for
2. **Discover** — role, location, seniority
3. **CV inspect** — pull facts from your stored CV
4. **Inspiration** — suggest lateral roles you might not have considered
5. **Preferences** — remote, salary, company size
6. **Aggregator search** — fan out across job boards in parallel
7. **Review & categorize** — accept / reject / save for later
8. **Drill** — deeper analysis on a chosen role
9. **Tailor CV** — generate a role-specific CV variant
10. **Draft letter** — motivation letter grounded in CV facts
11. **CV coaching** — gap analysis and improvement suggestions
12. **Done** — outcome captured for tracking

Every AI write is gated by a confirmation prompt. Missing parameters trigger multi-turn elicitation ("Which location?") rather than failing.

### Other Built-in Flows

- **CV builder** — 5-question sectional interview (header → summary → experience → education → skills); AI reformats your raw text with fact-grounding to avoid hallucination; encrypted at rest (ChaCha20-Poly1305).
- **CV variant tracking** — tracks which tailored CV gets replies; recommends your best-performing variant for new roles.
- **Skill-gap atlas** — extracts gaps from job descriptions ("JD wants Kubernetes, your CV doesn't mention it") and aggregates into a "Top 3 skills holding you back" dashboard card with "add this → unlocks N more roles" hints.
- **Persona system** — five personas (healthcare-management, tech, marketing, finance, product-management) carry sector weights and role suggestions; auto-selected from your job-type choice; drives ranking.
- **Outcome tracking** — Applied / Replied / Interviewing / Offer / Rejected timeline with reply-rate analytics ("small companies <50 reply 3× more").
- **Workspaces** — multi-seat with admin invites and role-based membership.
- **Account stack** — email verification, TOTP 2FA, 7-day deletion grace, encrypted profile data.
- **i18n** — full English + German, including a German Impressum (§5 TMG) and locale-aware date / yes-no parsing (ja/nein).
- **SEO pages** — auto-generated `/jobs/<slug>` landing pages for organic discovery, configured via `data/seo-pages.json`.
- **MCP server** — `mcp_server.py` exposes the toolset as a Claude-native MCP server (JSON-RPC over stdio).

## Plans

- **Free** — 3 saved searches, manual / bring-your-own AI, 30-day retention.
- **Pro** (€5/mo or €40/year) — unlimited searches, managed AI, 90-day retention, daily digest. Stripe checkout, webhooks, and customer portal are wired in.

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

When the journey or chat router needs AI but no provider is set, it falls back to templated responses so the flow still works end-to-end.

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
- Aggregator providers respect source attribution for ToS compliance.

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

`/privacy`, `/terms`, `/data-retention`, and the German `/impressum` are
served as static HTML and linked from the auth gate footer and Settings.
They are written as product-honest summaries; **counsel must review them
before commercial sale.**

## Admin Audit Log

Admin actions (create user, change role, change active state, reset password) are appended to `data/admin_audit.log` as one JSON object per line. Each entry records the action, actor, target, and timestamp.

## Code Map

| Path | Role |
|---|---|
| `app.py` | HTTP handler, session management, chat/journey dispatch |
| `company_discovery/chat_router.py` | Slash commands, intent routing, multi-turn state machine |
| `company_discovery/journey.py` | 12-phase job-search wizard |
| `company_discovery/aggregators.py`, `aggregator_providers.py` | Job-board fan-out, dedup, source attribution |
| `company_discovery/personas.py` | Persona definitions, sector weights, ranking |
| `company_discovery/cv_builder.py` | Sectional CV interview, fact-grounding |
| `company_discovery/analysis.py` | AI calls: fit, tailor, cover letter, decision brief |
| `company_discovery/auth.py` | Users, 2FA, invites, email verify, deletion |
| `company_discovery/billing.py` | Stripe, plan gates, quotas |
| `company_discovery/service.py` | Watchlist scan orchestration |
| `mcp_server.py` | Claude-native MCP server (JSON-RPC over stdio) |
| `static/i18n/{en,de}.json` | Translation bundles |
