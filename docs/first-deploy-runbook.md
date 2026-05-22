<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# First-deploy runbook

Single-page operator checklist for taking Helpmefindthejob live at
`helpmefindthejob.com`. Sequenced for a fast, safe initial cutover
before the NLnet submission window closes (1 June 2026, noon CEST).

This runbook stitches together the existing pieces — it does NOT
duplicate them. The substrate docs live at
[`deployment-recipe.md`](./deployment-recipe.md) (generic recipe) +
[`production-deployment.md`](./production-deployment.md) (production
specifics). This file is the actual ordering.

---

## Phase 0 — Pre-flight (30 minutes, before touching the server)

### 0.1 Confirm the build is green

```bash
git checkout claude/project-analysis-bpHCo   # the working branch
git log --oneline | head -5                  # confirm latest commit
python -m unittest discover -s tests 2>&1 | tail -3   # 2925+ tests, 0 failures
```

Last confirmed at `aee1536`: **2925 tests / 0 failures / 14 skipped**.

### 0.2 Decide the deployment target

Two reasonable choices:

| Option | URL | Best for |
|---|---|---|
| **A. Subdomain first** (recommended) | `demo.helpmefindthejob.com` | Lower-risk shakedown; apex stays parked for landing-page work later |
| **B. Apex direct** | `helpmefindthejob.com` | Maximum NLnet-narrative impact; submission can link directly |

Tradeoff: A gives you a recoverable testbed; B gives you the
reviewer click-through but a misconfigured TLS cert sends real
users to a broken page. **Recommendation: A first, B within
24-48h after smoke is green.**

### 0.3 Confirm production env values are ready

You'll need real values for these (template at
[`deploy/production.env.template`](https://github.com/maksodf/helpmefindthejob/blob/main/deploy/production.env.template)):

**Required for boot** (production refuses to start without them):

- `HELPMEFINDTHEJOB_AUDIT_SALT` — 32 random bytes base64 (`openssl rand -base64 32`)
- `HELPMEFINDTHEJOB_SECRET_KEY` — session signing (`openssl rand -hex 32`)
- `HELPMEFINDTHEJOB_ENV=production`
- `HELPMEFINDTHEJOB_DOMAIN=helpmefindthejob.com` (or `demo.helpmefindthejob.com`)
- `HELPMEFINDTHEJOB_PUBLIC_URL=https://helpmefindthejob.com`
- `HELPMEFINDTHEJOB_ADMIN_EMAIL` + `HELPMEFINDTHEJOB_ADMIN_PASSWORD` for bootstrap
- `HELPMEFINDTHEJOB_COOKIE_SECURE=1`
- `HELPMEFINDTHEJOB_HSTS=1`

**Strongly recommended** (degraded UX without them):

- `HELPMEFINDTHEJOB_SMTP_*` (email send for password reset, 2FA recovery, invites)
- `HELPMEFINDTHEJOB_VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` / `VAPID_CONTACT` (web-push)

**Optional opt-in observability** (zero-overhead when off — phase2 #17):

- `HELPMEFINDTHEJOB_SENTRY_DSN` (errors)
- `HELPMEFINDTHEJOB_POSTHOG_KEY` + `HELPMEFINDTHEJOB_POSTHOG_HOST` (events; EU host by default)
- `HELPMEFINDTHEJOB_COST_METRICS=true` (8-mechanism doctrine measurement)

**Optional billing** (Stripe — only if you're charging):

- `HELPMEFINDTHEJOB_BILLING_BACKEND=stripe`
- `HELPMEFINDTHEJOB_STRIPE_API_KEY` + `STRIPE_WEBHOOK_SECRET` + price IDs

---

## Phase 1 — Server prep (15 minutes, on the host)

### 1.1 Inventory

The maintainer already has Docker Compose + Caddy infrastructure
(per `CONTRIBUTORS-NOTE.md` and the existing deploy paths). Confirm:

```bash
docker --version       # >= 20.10
docker compose version # v2 plugin
which caddy            # or check Caddy is in the compose stack
```

### 1.2 Pre-existing `directjob-scout` container (phase2 #51)

If a prior `directjob-scout` deployment is running on this host:

```bash
docker compose -p directjob-scout down
# Confirm the helpmefindthejob compose project starts clean.
```

### 1.3 Place env file

```bash
sudo install -m 600 -o root -g root /dev/null /opt/helpmefindthejob/.env
sudo $EDITOR /opt/helpmefindthejob/.env   # paste filled-in template
```

### 1.4 Pre-deploy readiness check (no traffic yet)

```bash
ENV_FILE=/opt/helpmefindthejob/.env \
  ./scripts/production-readiness-check.sh
```

This validates every required env var is set + non-default. **Do
not proceed if it fails.**

---

## Phase 2 — Deploy (5 minutes)

### 2.1 Pull + start

```bash
cd /opt/helpmefindthejob
git pull origin claude/project-analysis-bpHCo  # or main after merge
docker compose up -d --build
docker compose ps   # all services healthy
docker compose logs --tail=50 helpmefindthejob
```

### 2.2 Local-only smoke (before DNS / TLS)

From the host:

```bash
curl -s http://127.0.0.1:8765/api/health | jq .
# expect: {"status":"ok", "storage":"sqlite", ...}
```

If `storage` is `sqlite` and you intended `postgres`, the
`HELPMEFINDTHEJOB_DATABASE_URL` env var isn't being read.

---

## Phase 3 — DNS + TLS (10 minutes)

### 3.1 DNS A/AAAA records

In your DNS provider:

```
demo.helpmefindthejob.com  A     <server-ipv4>
demo.helpmefindthejob.com  AAAA  <server-ipv6>   # if dual-stack
```

(Or `@` for apex — see Phase 0.2.)

Wait for DNS propagation (`dig demo.helpmefindthejob.com` returns
the right IP). Typically 1-5 minutes.

### 3.2 Caddy auto-TLS

The `deploy/Caddyfile` already has the auto-TLS directive (Let's
Encrypt). Restart Caddy:

```bash
docker compose restart caddy
docker compose logs caddy --tail=30
# look for: "certificate obtained successfully"
```

If you see a rate-limit error from Let's Encrypt, use the staging
endpoint first (`acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`)
to validate, then switch back to production.

---

## Phase 4 — Smoke test the live URL (10 minutes)

```bash
./scripts/production-smoke.sh
APP_BASE_URL=https://demo.helpmefindthejob.com ./scripts/production-smoke.sh
```

The script now covers **10 surface checks**:

1. `/api/health` returns `status: ok`
2. `/api/auth/status` returns anonymous
3. `/api/bootstrap` returns 401 anonymous
4. Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) present on `/`
5. Landing mission block renders on `/`
6. `/sitemap.xml` valid XML + no khalo.org regression
7. `/robots.txt` has `Sitemap:` line
8. `/mcp/version` + `/mcp/schemas.json` MCP catalogue
9. `/api/health/history` uptime-window endpoint
10. `/api/metrics` Prometheus exposition + content-type

All must pass before declaring the deploy live.

---

## Phase 5 — Manual sanity (15 minutes)

Things the smoke can't cover:

1. **Browser load**: open `https://demo.helpmefindthejob.com/` in
   an incognito window. See the landing mission block + sign-in
   form. No console errors. TLS cert is valid (green padlock).
2. **Sign-up flow**: register a test account. Email arrives (if
   SMTP configured). Login succeeds.
3. **Persona pick + journey**: pick Aïcha. Type `find a job`.
   Walk through discover → CV check → preferences. AI calls
   succeed if a provider is configured; otherwise sees the
   honest fallback messaging.
4. **Mobile**: load on a real phone (closes phase2 #2 / #31
   partial). The mission block stacks. The chat is usable.
5. **/status page**: shows `Uptime (24h)` + `Uptime (7d)` cards
   accumulating data (#30).
6. **/help page**: loads. Renders the help content. (#70 panel
   help is auth-gated, not relevant here.)

---

## Phase 6 — Backup + monitoring (15 minutes)

### 6.1 Schedule backups

```bash
crontab -e
# Add:
# 0 2 * * * /opt/helpmefindthejob/scripts/backup-production.sh >> /var/log/helpme-backup.log 2>&1
```

Confirm with a manual run + verify the backup file is written
to the configured `HELPMEFINDTHEJOB_BACKUP_REMOTE` location.

### 6.2 External uptime monitor

Subscribe a free-tier uptime monitor to:

```
https://demo.helpmefindthejob.com/api/health
```

Recommended: UptimeRobot or Better Uptime. Check every 5 minutes.
Required notification email goes to your incident contact (per
SLA template Appendix B).

### 6.3 (Optional) Wire Sentry + PostHog + Prometheus

If you set the observability env vars in Phase 0.3, those are
already firing. Confirm by:

- Triggering an exception (e.g., POST malformed JSON to a
  protected endpoint while signed in) → should appear in Sentry
- Walking the journey → events appear in PostHog (if EU host
  reachable)
- Scrape `/api/metrics` from your Prometheus → counters
  accumulate

---

## Phase 7 — Apex cutover (if Phase 2.0 was "A. Subdomain first")

After 24-48 hours of clean smoke on the subdomain:

1. Update DNS for the apex `helpmefindthejob.com` to the same IP.
2. Caddy auto-issues the apex cert.
3. Re-run `APP_BASE_URL=https://helpmefindthejob.com ./scripts/production-smoke.sh`.
4. Update `HELPMEFINDTHEJOB_PUBLIC_URL` to the apex if changed.

---

## Phase 8 — NLnet narrative integration (5 minutes)

Once the live URL is solid:

1. Update `docs/grant/application-draft-2026-05-19.md` Field 8
   (Website) with the live URL.
2. Add a screenshot of the apex landing block to the application
   attachments (Field 17 — optional but high-impact).
3. Re-run the `test_application_draft_numerical_claims` contract
   to confirm nothing broke.

---

## Rollback plan

If Phase 4 smoke fails OR Phase 5 sanity reveals a serious issue:

1. **DNS rollback**: lower TTL preemptively (Phase 3.1) so you can
   revert in minutes.
2. **Container rollback**: `docker compose -f docker-compose.yml -p helpmefindthejob down`.
3. **DB rollback**: restore from last good backup
   (`scripts/restore-from-backup.sh BACKUP_FILE` — verify it exists
   AND test it on a non-prod DB first per phase2-backlog #50).
4. **Cert rollback**: not usually needed — Caddy storage persists across restarts.

---

## What this runbook deliberately doesn't cover

- **Internal architecture**: see `ARCHITECTURE.md` at repo root
- **Compliance details**: see `compliance/` and the SLA template
- **MCP catalogue specifics**: see `docs/mcp-server.md`
- **The 12-phase journey**: see `docs/grant/01-project-brief.md`
- **Per-persona ranking + bias methodology**: see
  `compliance/accuracy-and-bias-testing.md`

---

## Provenance

Authored 2026-05-22, post-#3 / #11 / #17 / #30 / #37 closes, as the
"single-page sequencing" doc the user asked for when ready to
deploy. Mirrors the order the agent will follow autonomously once
SSH + DNS credentials are shared.
