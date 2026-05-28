# Company Discovery Pilot Runbook

## Start

```bash
python3 app.py --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

The app stores local pilot state in:

```text
data/company_discovery.sqlite3
data/ai_provider.json
data/watchlist_schedule.json
```

Set `HELPMEFINDTHEJOB_DATA_DIR=/path/to/profile` to use a separate local pilot profile.

For another machine, either copy the project folder and run the command above, or use:

```bash
docker compose up --build
```

The default host is `127.0.0.1`. Use `--host 0.0.0.0` only for a trusted LAN or a reverse-proxy setup with access control.

## Pilot Flow

The redesigned UI walks the tester through this flow with sidebar navigation: **Today → Companies → Discovered Jobs → AI Brief → Settings → Admin** (admin only).

1. Sign in. On a fresh install only, the login screen also offers "Create the first account"; that account becomes the admin.
2. As admin, open **Admin → Tester accounts** and create one account per tester.
3. New tester: open **Today**, then click **Add a company**, or **Try a demo company** for a local fixture without any live network access.
4. **Companies** view: paste a company website. Click **Find career page** if you don't already have the career URL. Use **Suggestions** to add curated healthcare employers.
5. **Settings → AI Provider**: pick a provider.
   - Save only a credential *reference* such as `OPENAI_API_KEY`, not a raw key.
   - For a tester's own API subscription, paste their key into the **AI Brief → Session API key** field before clicking **Analyze fit**; it is sent only with that one request and not saved.
   - Manual / handoff mode always works.
6. **Companies** view: click **Check for new roles** on a company, or **Today → Check for new roles** to scan the whole watchlist.
7. **Discovered Jobs** view: review roles, then **Import** the ones you want.
8. **AI Brief** view: open a brief for the imported role, then **Analyze fit** if you have a configured provider, or **Copy** the brief and paste it into your own AI tool.

## Admin Tester Management

Open **Admin → Tester accounts** to:

- Create a tester account (email + initial password, role).
- Reset a tester's password (signs them out everywhere).
- Deactivate or reactivate a tester (deactivation signs them out).
- Promote / demote between Tester and Admin.

Destructive actions show a confirmation dialog. You can't change your own role or deactivate yourself, and the last active admin can never be demoted or deactivated.

All admin actions are recorded in `data/admin_audit.log` (one JSON object per line).

## Forgot password

The auth gate has a **Forgot password?** action that emails a single-use
reset link to the user. Links expire after one hour. If SMTP is not
configured the link is written to `data/email_outbox.log` for the
operator to deliver manually. As a fallback an admin can still reset a
tester from **Admin → Tester accounts** without an email round-trip.

## Email invitations

Admins can email a single-use invite from **Admin → Send invitation**.
Invitees receive a `/accept-invite?token=…` link that lets them set
their own password (12+ characters) and signs them in.

## Quotas

Each tester sees their daily usage in **Settings → Your usage today**:
scans / AI calls / active scans against the configured limits. Hitting
a limit returns a friendly toast and a 429 from the API. Admin
override is via `HELPMEFINDTHEJOB_QUOTA_*` env vars.

## Supported AI Provider Modes

- Manual / no AI: prompt handoff only.
- OpenAI / ChatGPT: OpenAI-compatible `/chat/completions`, key from env var reference or session-only key.
- DeepSeek: OpenAI-compatible `/chat/completions`, key from env var reference or session-only key.
- OpenRouter: OpenAI-compatible `/chat/completions`, key from env var reference or session-only key.
- Google Gemini: `generateContent`, key from env var reference or session-only key.
- Ollama: local `http://127.0.0.1:11434/api/generate`.
- Codex CLI / Claude Code / custom CLI: guarded local command execution with prompt on stdin.

## MCP Server

Run the local stdio MCP bridge with:

```bash
python3 mcp_server.py
```

It exposes the company-discovery tools from `company_discovery/mcp_tools.py` and uses the same local SQLite data store as the web pilot.

## Operations

- Health endpoint: `GET /api/health`
- In-app backup: **Settings → Backup &amp; restore → Export backup**, or `GET /api/data/export`.
- In-app restore: **Settings → Backup &amp; restore → Import backup**, or `POST /api/data/import`.
- Docker packaging: `Dockerfile` and `docker-compose.yml`.
- Server-side smoke: `APP_BASE_URL=https://YOUR_DOMAIN ./scripts/production-smoke.sh` (anonymous-only by default; admin probe enabled by setting `ADMIN_EMAIL`/`ADMIN_PASSWORD`).
- Server-side backup: `./scripts/backup-production.sh` (writes a timestamped tarball to `./backups/`).
- Admin audit log: `data/admin_audit.log` — JSON Lines record of every admin user-management action.

## Safety Guarantees

- Career-page fetches reject localhost/private/internal hosts.
- Authentication is required for app data APIs.
- Mutating requests require CSRF tokens.
- User records are isolated by authenticated user id.
- Admin-only tester management supports account creation, password reset, role changes, and deactivation.
- Career-page fetches reject restricted platform domains.
- `robots.txt` is checked before a page fetch.
- Redirect targets are checked against their own `robots.txt` before fetching.
- Scans are bounded by max pages, response size, and redirect limits.
- Raw-looking AI secrets are rejected in saved provider settings.
- Session-only AI keys are accepted only for a single analysis request and are not persisted.
- Scan runs are asynchronous and persisted.
- Watchlist scans remain bounded to known career pages and can be run manually or on an explicit schedule.

## Known Pilot Limits

- Email invite + forgot/reset password flows are wired (default
  `console` transport writes to `data/email_outbox.log`; switch to SMTP
  via env vars before commercial pilot).
- Search-provider discovery is curated + configurable feed providers
  (Greenhouse, Lever) only; no general-web crawling by design.
- The watchlist scheduler persists in `data/scheduler.sqlite3` with
  orphan recovery and failure backoff; replace with a dedicated worker
  if scan volume grows past a single host.
- CLI provider execution is intentionally restrictive.
- Company suggestions combine a small curated healthcare employer list with category-level suggestions; this is not a live company database.
- Browser smoke tests are skipped automatically if the sandbox blocks local port binding; manual server smoke is still available.
- Account deletion is two-step: user requests, admin confirms via
  `Admin → Tester accounts → Delete`. Last admin cannot be deleted.
