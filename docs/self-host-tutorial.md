<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Self-host tutorial

**Audience**: an individual or small organisation who wants to run their own Helpmefindthejob instance. Not for institutional deployers — see [`compliance/deployer-operating-manual.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/deployer-operating-manual.md) for the AI-Act-Article-26 deployer recipe. Not for the public-demo subdomain — see [`deployment-recipe.md`](deployment-recipe.md).

**Time budget**: 30 minutes from a clean machine to a running instance. Most of that is Docker pulling images.

**What you need**:
- A Linux / macOS / Windows machine with Docker installed (any recent release; `docker --version` returning `Docker version 20.10+` is fine)
- 4 GB RAM minimum, 8 GB recommended (the AI workloads happen on the deployer's chosen provider, not locally — so RAM is for the app + SQLite + browser cache)
- 10 GB free disk (the SQLite database grows ~1 MB per user; backups add ~3× live size)
- A free TCP port (default 8765; the tutorial uses 8765)
- Optional: a domain name + DNS access for the public route + a static IP for TLS issuance via Caddy

---

## Path A — five-minute trial (Docker only, localhost-only)

The fastest path to verify the project runs end-to-end on your machine.

```bash
# 1. Clone the repo
git clone https://github.com/maksodf/helpmefindthejob.git
cd helpmefindthejob

# 2. Generate the deployment secrets (one-time)
export HELPMEFINDTHEJOB_SECRET_KEY="$(python3 -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
export HELPMEFINDTHEJOB_AUDIT_SALT="$(python3 -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
export HELPMEFINDTHEJOB_ADMIN_EMAIL="you@example.com"
export HELPMEFINDTHEJOB_ADMIN_PASSWORD="$(python3 -c 'import secrets,string; alpha=string.ascii_letters+string.digits; print("".join(secrets.choice(alpha) for _ in range(32)))')"
echo "ADMIN PASSWORD (save this): $HELPMEFINDTHEJOB_ADMIN_PASSWORD"

# 3. Build the image + run
HELPMEFINDTHEJOB_ENV=production \
HELPMEFINDTHEJOB_DOMAIN=localhost \
HELPMEFINDTHEJOB_HSTS=0 \
HELPMEFINDTHEJOB_COOKIE_SECURE=false \
docker compose -f docker-compose.prod.yml up -d --build helpmefindthejob

# 4. Verify
sleep 8
curl -sS http://127.0.0.1:8765/api/health
```

Expected response shape: `{"ok": true, "version": "0.80.0", ...}`. If you see that, the instance is running. Open `http://127.0.0.1:8765` in a browser; sign in with the admin email + password above.

To stop: `docker compose -f docker-compose.prod.yml down`. To clean: `docker compose -f docker-compose.prod.yml down -v` (removes the SQLite volume — data is gone).

---

## Path B — public host with TLS (Caddy auto-issues Let's Encrypt)

For a real persistent self-host on a VPS / dedicated server / home server with a public IP.

### B.1 Provision a host

Any provider works. Tested on:
- **DigitalOcean** — €4 / month basic droplet (1 vCPU, 1 GB RAM, 25 GB SSD). Frankfurt region (FRA1) for German latency.
- **Hetzner Cloud** — €4.50 / month CX11 (1 vCPU, 4 GB RAM, 40 GB SSD). German DC, EU-jurisdiction.
- **AWS** — `t4g.small` (€10–15 / month on demand, less with reserved). Frankfurt or Stockholm region.
- **GCP** — `e2-small` (€10 / month). europe-west3 (Frankfurt).
- **Self-owned hardware** — any modest Linux box + a static public IP.

For the rest of this section we'll use a DigitalOcean droplet as the example. Same pattern works on every other provider — only the SSH key + IP differ.

```bash
# Create + ssh in
ssh root@<your-droplet-ip>

# Install Docker + git
apt update && apt install -y docker.io docker-compose-plugin git
systemctl enable --now docker
```

### B.2 Point your domain at the host

In your registrar's DNS panel (United Domains, Cloudflare, Hetzner, …):

- Create an A record: `<your-domain>` → `<your-droplet-ip>`. TTL 300.
- Wait ~2 minutes for propagation (`dig <your-domain>` should return the droplet IP).

### B.3 Pull and configure

```bash
cd /opt
git clone https://github.com/maksodf/helpmefindthejob.git
cd helpmefindthejob

# Create the .env file
cat > .env <<EOF
HELPMEFINDTHEJOB_ENV=production
HELPMEFINDTHEJOB_DOMAIN=<your-domain>
HELPMEFINDTHEJOB_PUBLIC_URL=https://<your-domain>
HELPMEFINDTHEJOB_SECRET_KEY=$(python3 -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')
HELPMEFINDTHEJOB_AUDIT_SALT=$(python3 -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')
HELPMEFINDTHEJOB_ADMIN_EMAIL=you@example.com
HELPMEFINDTHEJOB_ADMIN_PASSWORD=$(python3 -c 'import secrets,string; alpha=string.ascii_letters+string.digits; print("".join(secrets.choice(alpha) for _ in range(32)))')
HELPMEFINDTHEJOB_ALLOW_REGISTRATION=true
EOF

# Save the admin credentials somewhere safe NOW
grep -E 'EMAIL|PASSWORD' .env
```

### B.4 Build, start, verify

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
sleep 30
docker compose -f docker-compose.prod.yml logs caddy | grep -i 'certificate'
curl -sS https://<your-domain>/api/health
```

Expected: a `200 OK` with the `{"ok": true}` health payload. Caddy auto-issues a Let's Encrypt cert on first HTTPS request; the first request can take ~20 seconds. Subsequent requests are normal-fast.

### B.5 First-run admin tasks

- Open `https://<your-domain>` in a browser, sign in as the admin
- Settings → Profile → set your timezone, language, AI provider
- Settings → Workspace → invite collaborators if applicable
- Settings → Backups → confirm the backup destination + retention

### B.6 Updating

```bash
cd /opt/helpmefindthejob
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

The app supports zero-downtime restarts (Docker rolls the new image up, then drains the old one). Database migrations are applied on container start.

---

## Path C — non-Docker (bare metal Python)

For environments where Docker isn't available (some shared-hosting providers, locked-down corporate machines, lightweight Pi-class hardware).

```bash
git clone https://github.com/maksodf/helpmefindthejob.git
cd helpmefindthejob

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export HELPMEFINDTHEJOB_DATA_DIR=$HOME/.helpmefindthejob-data
export HELPMEFINDTHEJOB_SECRET_KEY="$(python3 -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
export HELPMEFINDTHEJOB_AUDIT_SALT="$(python3 -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"

python3 app.py --port 8765
```

You'll need a reverse-proxy (nginx, Caddy, Apache) in front for TLS. The project does NOT terminate TLS itself in Path C.

---

## Backups + restore

`scripts/backup-production.sh` runs nightly via cron (or on-demand). Restore drill: `scripts/restore-drill.sh` (runs against a sidecar container so the live instance is never touched). Schedule the drill at least quarterly; document the result in your operations runbook.

```bash
# Set up the nightly backup cron (Linux)
echo '0 3 * * * cd /opt/helpmefindthejob && bash scripts/backup-production.sh' | crontab -

# Manually trigger
docker compose -f docker-compose.prod.yml exec helpmefindthejob bash scripts/backup-production.sh
```

---

## AI provider configuration (BYO-AI)

The app starts in **manual** AI mode (every AI suggestion goes through your clipboard rather than calling out to a provider). To enable automatic AI:

- Settings → Profile → AI provider → choose one of: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama (local), Codex CLI, Claude Code, or "managed" (operator-side key)
- For API providers: paste your API key into the same screen (encrypted-at-rest)
- For Ollama: point at your local `http://localhost:11434` endpoint
- For Codex CLI / Claude Code: the app shells out to your local installation; no key needed

The bias-comparative-report at [`docs/grant/bias-comparative-report-2026-05-21.md`](grant/bias-comparative-report-2026-05-21.md) measures per-provider behaviour; the AI Provider Honesty Matrix at [`docs/grant/15-ai-provider-honesty-matrix.md`](grant/15-ai-provider-honesty-matrix.md) documents what's been verified live vs mocked.

---

## What if something breaks?

1. **`docker compose logs helpmefindthejob`** — the app's stderr is the first place to look
2. **`docker compose logs caddy`** — TLS issuance failures show here (most common cause: DNS not yet pointing at the host)
3. **`/api/health?detailed=1`** — structured health surface naming exactly which subsystem is degraded
4. **`compliance/audit-log-schema.md`** — if you suspect a tampered audit log, the schema doc shows the verification recipe
5. **[GitHub issues](https://github.com/maksodf/helpmefindthejob/issues)** — file a bug with the relevant logs; the maintainer aims to triage within 5 working days

---

## What this tutorial does NOT cover

- Multi-tenancy beyond the single-workspace model — use the institutional-deployer recipe instead
- AI Act Article 26 deployer obligations — read [`compliance/deployer-operating-manual.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/deployer-operating-manual.md)
- GDPR-Article-22 right-to-human-review procedure — see deployer-operating-manual.md §8.1
- Sustainability / contributor pathway — see [`SUSTAINABILITY.md`](https://github.com/maksodf/helpmefindthejob/blob/main/SUSTAINABILITY.md) + [`CONTRIBUTING.md`](https://github.com/maksodf/helpmefindthejob/blob/main/CONTRIBUTING.md)
- Production-grade monitoring + alerting — that's `docs/observability-runbook.md`
