<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Deployment recipe — parallel public demo instance

**Audience**: a contributor or institutional deployer who wants a public demo
of Helpmefindthejob running against any Docker Compose + Caddy host.
**Companion to**: [`production-deployment.md`](production-deployment.md) (the
general production guide) and `docs/grant/02-execution-plan.md` §3.4 (the
grant-sprint planning context).
**Status**: living document; reviewed alongside every §3.4 / §3.5 ship.

This recipe is **host-agnostic**. It does not commit the project to a
specific hosting provider, registrar, monitoring vendor, or domain
name. The example values below use placeholders (`<your-domain>`,
`/srv/directjob-demo`) that the deployer replaces with their own
choices.

---

## 1. Why "parallel public instance" rather than "expose the existing
instance"?

Per Decision 17 in `docs/grant/04-research-and-decisions.md`, the
project has an **existing private deployment** that serves a single
tester (the maintainer's partner). That deployment carries real
session data, real CV facts, and a real admin account; it is **not**
the right surface to point NLnet reviewers, partner NGOs, or curious
contributors at.

The §3.4 public demo (Maintainer decision 2026-05-18 — Finding A
posture (b)) is a **parallel public instance** that:

- Runs from the same Git checkout and the same Docker image.
- Uses the same `scripts/deploy.sh` toolchain.
- Has its own `.env` with separate `DIRECTJOB_SECRET_KEY`,
  `DIRECTJOB_AUDIT_SALT`, admin credentials.
- Uses its own Docker named volume (`directjob_data_demo`) so it
  cannot read or write the private instance's data.
- Has its own Caddy site block answering a separate subdomain.
- Is pre-seeded with the seven-persona panel via
  `scripts/seed-personas.py`.

Both instances can live on the same VM, or on separate hosts — the
recipe is the same either way.

---

## 2. Prerequisites

- A host (VM, dedicated server, or local machine) running Docker
  Compose v2.
- A domain or subdomain pointing at the host (Caddy will request a
  Let's Encrypt cert automatically on first run; HTTP-only also
  works for local development).
- SSH access to the host (for production); for local development the
  recipe runs on `localhost` without SSH.
- The repo cloned into the deployer's working tree.

---

## 3. One-command bring-up (local development)

For a local-development demo on the deployer's own machine, with
HTTP-only and no Let's Encrypt cert:

```bash
git clone https://github.com/maksodf/helpmefindthejob.git
cd helpmefindthejob

# Copy the env template and fill in placeholders.
cp deploy/production.env.template .env.demo
${EDITOR:-vi} .env.demo
# At minimum, fill in:
#   DIRECTJOB_DOMAIN=localhost
#   DIRECTJOB_PUBLIC_URL=http://localhost:8765
#   DIRECTJOB_SECRET_KEY=<32-byte base64; python3 -c "import secrets; print(secrets.token_urlsafe(32))">
#   DIRECTJOB_AUDIT_SALT=<32-byte base64; python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())">
#   DIRECTJOB_ADMIN_EMAIL=<your demo admin>
#   DIRECTJOB_ADMIN_PASSWORD=<your demo admin password>

# Start the parallel-instance compose project. The ``-p directjob-demo``
# project name is what isolates it from any pre-existing private
# instance on the same host.
docker compose -p directjob-demo \
  -f docker-compose.prod.yml --env-file .env.demo \
  up -d --build

# Wait a few seconds for the healthcheck to register, then verify.
sleep 5
curl -fsS http://localhost:8765/api/health | python3 -m json.tool

# Seed the seven personas. The script accepts the demo password at
# runtime; it is never written to disk.
python3 scripts/seed-personas.py --password '<demo-password>'

# Open the demo in a browser.
open http://localhost:8765
```

---

## 4. Production bring-up (parallel public instance on a remote host)

For a public-facing demo with TLS via Let's Encrypt, on a remote VM
already reachable via SSH:

### 4.1 On the host (one-time)

```bash
# Provision the demo's app directory.
sudo mkdir -p /srv/directjob-demo
sudo chown "$USER:$USER" /srv/directjob-demo
cd /srv/directjob-demo
git clone https://github.com/maksodf/helpmefindthejob.git .

# Generate the demo's secrets — these must be different from the
# private instance's secrets.
python3 -c "import secrets; print('DIRECTJOB_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets, base64; print('DIRECTJOB_AUDIT_SALT=' + base64.b64encode(secrets.token_bytes(32)).decode())"

# Copy the env template and fill in.
cp deploy/production.env.template .env
${EDITOR:-vi} .env
# Fill in at minimum:
#   DIRECTJOB_DOMAIN=demo.<your-domain>
#   DIRECTJOB_PUBLIC_URL=https://demo.<your-domain>
#   DIRECTJOB_SECRET_KEY=<from above>
#   DIRECTJOB_AUDIT_SALT=<from above>
#   DIRECTJOB_ADMIN_EMAIL=<demo-admin@your-domain>
#   DIRECTJOB_ADMIN_PASSWORD=<long random password>
#   DIRECTJOB_ALLOW_REGISTRATION=false   # demo is invite-only

# Set restrictive permissions on the env file.
chmod 0600 .env
```

If the host also runs the private instance, ensure the two `.env`
files live in separate directories and the two compose projects use
**different** named volumes and **different** Caddy site blocks.

### 4.2 On the local machine (every deploy)

The existing `scripts/deploy.sh` is generic and works against any
SSH-accessible host. For the demo instance, point it at the demo's
app directory:

```bash
TAG=$(git rev-parse --short HEAD) \
SSH_HOST=<user>@<demo-host> \
SSH_KEY=~/.ssh/<your-key> \
PUBLIC_URL=https://demo.<your-domain> \
APP_DIR=/srv/directjob-demo \
SERVICE_NAME=helpmefindthejob \
COMPOSE_FILE=docker-compose.prod.yml \
./scripts/deploy.sh
```

The script:

1. Verifies the prod compose file exists on the remote.
2. Takes a WAL-aware sqlite snapshot of the running container (the
   demo instance's existing state, if any).
3. Tags the previous image as `previous-<TAG>` for one-command
   rollback.
4. Rebuilds the image.
5. Restarts the service via Docker Compose.
6. Curls `/api/health` and asserts the new `version` is live.

After the first deploy, run the persona seed once via SSH:

```bash
ssh <user>@<demo-host> \
  "cd /srv/directjob-demo && \
   docker compose exec -T helpmefindthejob \
     python3 scripts/seed-personas.py --password '<demo-password>'"
```

The seed is idempotent — re-running is a no-op if the seven personas
are already present.

---

## 5. Verifying the deployment

### 5.1 Health check

```bash
curl -fsS https://demo.<your-domain>/api/health | python3 -m json.tool
```

Expected output includes `"status": "ok"`, the current `version`, and
the `environment: production` marker. The healthcheck is also baked
into `docker-compose.prod.yml`; `docker ps` will show the container
as `healthy` once the start-period elapses.

### 5.2 Persona seed verification

```bash
docker compose -p directjob-demo exec helpmefindthejob python3 -c "
from app import build_state
state = build_state()
users = state.auth_store.list_users()
print('seeded users:', sorted(u.email for u in users))
"
```

The output should include all seven persona emails (one per persona;
the canonical email shape is `<persona-slug>@demo.<your-domain>`,
chosen by the seed script).

### 5.3 Smoke probe

The existing `scripts/production-smoke.sh` runs a representative
end-to-end smoke probe. Adapt the URL and invoke against the demo
instance.

---

## 6. If Caddy can't get a TLS certificate

Most common cause: the demo's domain DNS A/AAAA record does not yet
point at the host's public IP, so Let's Encrypt's HTTP-01 challenge
fails.

Diagnostics:

```bash
# 1. Confirm DNS points at the host.
dig +short A demo.<your-domain>
# Should return the host's public IP.

# 2. Confirm port 80 is open from the public Internet (Let's Encrypt
# needs HTTP-01 challenge).
sudo ss -ltnp | grep ':80 '
# Caddy should be listening; if ufw blocks 80, open it.

# 3. Check Caddy logs.
docker compose -p directjob-demo logs caddy | tail -50
```

Most issues resolve once DNS propagates. If the recipe must serve
HTTP-only as a fallback during a short DNS window, set
`DIRECTJOB_PUBLIC_URL=http://demo.<your-domain>:80` and Caddy will
serve plain HTTP without attempting cert issuance.

---

## 7. Backup procedure

Once-a-day cron, on the host:

```bash
cd /srv/directjob-demo && \
  DIRECTJOB_BACKUP_BACKEND=local \
  BACKUP_DIR=/var/backups/directjob-demo \
  BACKUP_RETENTION_DAYS=30 \
  ./scripts/backup-production.sh
```

`scripts/backup-production.sh` supports `local`, `rclone`, and `s3`
backends (S3-compatible — DigitalOcean Spaces, Backblaze B2,
Cloudflare R2, AWS S3 all work). The `local` backend is the simplest
to set up and stores tarballs on the host filesystem. Off-host
backup is the right move once the demo carries real partner-NGO
data; until then `local` is acceptable.

The existing `scripts/restore-drill.sh` exercises a restore from a
recent backup. Run it at least quarterly.

---

## 8. Firewall (recommended)

The recipe is firewall-vendor-neutral. A minimal rule set:

- Inbound TCP 22 (SSH).
- Inbound TCP 80 (HTTP, for Let's Encrypt HTTP-01).
- Inbound TCP 443 (HTTPS).
- Block everything else inbound.

Configure with whatever firewall the host already uses — `ufw`,
`firewalld`, iptables direct, a cloud-provider security group, or a
managed firewall service. The project does not bind to a specific
firewall vendor.

---

## 9. Log locations

- Application logs: `docker compose -p directjob-demo logs
  helpmefindthejob`.
- Caddy access + error logs: `docker compose -p directjob-demo logs
  caddy`.
- AI Act audit log: inside the container at
  `${DIRECTJOB_DATA_ROOT}/ai_act_audit.log`, or on the host inside the
  named volume `directjob_data_demo`. Inspect via
  `docker compose -p directjob-demo exec helpmefindthejob cat
  /app/data/ai_act_audit.log`.
- Admin-action log (separate from the AI Act log): same location,
  filename `admin_audit.log`.

---

## 10. Swap-file note (optional)

Helpmefindthejob's runtime memory footprint is modest. The encryption-
at-rest layer, the sqlite WAL, and the embedded Python image all fit
under 1 GiB at idle. The AI provider runs out-of-process (when
configured) or off-host, so RAM is not the bottleneck.

If the host has less than 4 GiB RAM and sqlite VACUUM (during
backup-and-restore drills) is observed to OOM, add a 2 GiB swap file:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 0600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

This is **optional** and not a §3.4 requirement.

---

## 11. Upgrading

```bash
cd <local-working-tree>
git pull origin main
TAG=$(git rev-parse --short HEAD) \
SSH_HOST=<user>@<demo-host> \
APP_DIR=/srv/directjob-demo \
PUBLIC_URL=https://demo.<your-domain> \
./scripts/deploy.sh
```

The script handles snapshot + image-tag-for-rollback + restart +
health-check assertion. A failed deploy can be rolled back with the
`previous-<TAG>` Docker image tag.

---

## 12. Reproducible builds (Nix flake)

Helpmefindthejob ships a `flake.nix` at the repo root that pins the
Python interpreter + OS-level dev toolchain to a specific
`nixos-25.05` nixpkgs commit (captured in `flake.lock`). A reviewer
running `nix develop` six months from now gets the same shell — same
Python ABI, same `git`, same `pkg-config`, same OpenSSL headers.

**Why**: build provenance for the EU AI Act Article 11 technical-
documentation surface; one-command reproducibility for any NGI0
reviewer or downstream re-deployer; trivial onboarding for
contributors who already use Nix.

**Requirements**: Nix with flakes enabled. One-line install on macOS
or Linux:

```bash
curl --proto '=https' --tlsv1.2 -sSf -L \
  https://install.determinate.systems/nix | sh -s -- install
```

Determinate's installer enables flakes out of the box. Upstream Nix
users add `experimental-features = nix-command flakes` to
`~/.config/nix/nix.conf`.

**Commands**:

```bash
# Drop into a reproducible dev shell. First entry bootstraps a
# .venv inside the repo from the pinned Python + pinned
# requirements.txt + requirements-dev.txt; subsequent entries are
# instant (the sentinel `.venv/.deps_installed` short-circuits).
nix develop

# Run the app via the flake (same env, same Python).
nix run

# Refresh the pinned inputs (nixpkgs commit + flake-utils).
# Commit the updated flake.lock alongside any code change that
# depends on the new pin.
nix flake update

# Verify the flake's contract is intact (CI-callable).
nix flake check
```

**Hybrid approach (why this isn't pure-Nix)**: the runtime + dev
deps remain pinned in `requirements.txt` + `requirements-dev.txt`
(single source of truth shared with the bare-host pip workflow).
The flake bootstraps Python 3.12 + `pip` from nixpkgs, then `pip`
resolves the deps inside a project-local `.venv/`. The pip resolver
is deterministic against the pinned version ranges; aligning every
transitive pip dep into a Nix derivation would multiply maintenance
overhead without adding reproducibility.

A future slice can convert the runtime to a pure-Nix
`buildPythonApplication` if the Conservancy / NixOS Foundation
packaging support engages.

**Pinned input commit**: `flake.lock` records the resolved commit
hashes. View them with `nix flake metadata`.

**Verified on**: aarch64-darwin (Determinate Nix 3.20.0 / Nix
2.34.6) at slice ship time. The `eachDefaultSystem` flake-utils
helper extends outputs to `x86_64-linux`, `aarch64-linux`,
`x86_64-darwin` without per-system copy-paste; CI verification on
those systems is tracked as a Phase 2 enhancement (the
fresh-clone-install workflow already covers Linux pip-path
reproducibility).

---

## 13. Decommissioning

```bash
ssh <user>@<demo-host> \
  "cd /srv/directjob-demo && \
   docker compose -p directjob-demo down && \
   docker volume rm directjob_data_demo"
```

Followed by a final backup-export of the volume's contents if the
deployer wants to preserve the audit log + user data per their
retention policy (see `compliance/audit-log-schema.md` §6).

---

## Append log

- **2026-05-18**: initial recipe drafted as part of the §3.4 deployment
  artefacts slice (Step 2 of `docs/grant/next-steps-2026-05-18.md`).
  Parallel-public-instance posture per Finding A maintainer decision.
