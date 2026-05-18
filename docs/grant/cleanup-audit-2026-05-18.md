<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Advisory false-dependency cleanup — audit report

**Date**: 2026-05-18.
**Trigger**: maintainer flagged that the prior advisory prompt (the "§3.4 owned" message that pre-decided Hetzner CX21 / `directjob-scout.eu` / Cloudflare Registrar / UptimeRobot / a new VM) introduced infrastructure dependencies the maintainer never asked for, in violation of `13-lessons-learned.md` Rules 1, 4, 5, and 10.
**Status**: read-only audit. Cleanup commit follows.

---

## TL;DR

**No false-dependency code or scripts ever landed in the repo.** The uncommitted Hetzner-shaped Edit to `deploy/.env.production.template` was rejected by the maintainer before persistence; the working tree is clean. **One file rename was made and reverted** (`deploy/production.env.template` → `.env.production.template` and back). No new files were created.

The audit therefore narrows to **pre-existing planning-doc passages** that the prior advisory prompt either misread as commitments (Hetzner / `.eu` enumeration in placeholder lists) or correctly identified as draft text that needs re-anchoring (`§3.4`'s "Pick hosting provider" task list).

Below: the seven audit categories the maintainer enumerated, with specific file:line citations.

---

## 1. Hetzner-specific deployment artifacts

| File | Line | Quote | Verdict |
|---|---|---|---|
| `docs/grant/02-execution-plan.md` | 354 | `[ ] Pick hosting provider (Hetzner Cloud, OVH, Scaleway — all EU-anchored)` | **Pre-existing planning placeholder** — lists three EU-anchored examples. The prior advisory prompt promoted one (Hetzner) to a commitment without authority. The list itself is option-enumeration, not a commitment. Cleanup: keep the enumeration; update the surrounding §3.4 task framing so this option list reads as "Phase 2 polish / for institutional deployers" rather than "a §3.4 prerequisite the maintainer must act on now." |
| `docs/grant/05-risks-and-stakeholders.md` | 92 | `set up the demo with health-check monitoring; use a reliable hosting provider (Hetzner Cloud, OVH, Scaleway are EU-anchored choices)` | Same shape — enumeration, not commitment. Acceptable as-is. |

No `scripts/deploy-to-hetzner.sh`, no `Dockerfile` Hetzner customisation, no compose overlay, no recipe document, no `.env` Hetzner-specific block exists in the repo. **None were committed; none were created.**

## 2. New-domain artifacts (`directjob-scout.eu` / `directjob-scout.org`)

| File | Line | Quote | Verdict |
|---|---|---|---|
| `docs/grant/02-execution-plan.md` | 355 | `[ ] Secure domain (`directjob-scout.eu` or similar)` | **Pre-existing planning placeholder** — explicit "or similar." Cleanup: remove the speculative `.eu` and re-anchor to the existing-infrastructure framing per Part D below. |
| `docs/grant/05-risks-and-stakeholders.md` | 90 | `Reviewer visits `demo.directjob-scout.eu` and sees a 500 error or down page. Bad signal.` | Pre-existing risk-register language using `.eu` as the hypothetical demo URL. Cleanup: change to a placeholder-style URL (`demo.<your-existing-subdomain>`) so the risk-register stays domain-neutral. |

No `directjob-scout.org` references found. No code references either.

## 3. Third-party-service introductions

### Cloudflare Registrar

**Zero references.** Not in code, not in planning workspace, not in docs. The prior advisory prompt invented this as a registrar choice; nothing landed.

### UptimeRobot

| File | Line | Quote | Verdict |
|---|---|---|---|
| `docs/production-deployment.md` | 135 | `External uptime + TLS monitoring is intentionally provider-neutral. We recommend hitting [...] from UptimeRobot, Better Stack, Pingdom, or the operator's own probe.` | **Pre-existing planning text — explicitly provider-neutral.** Lists four options. Not a commitment. Acceptable as-is. |

The prior advisory prompt promoted UptimeRobot to a commitment ("Monitoring: external uptime via UptimeRobot free tier (maintainer-configured post-deploy)") — that promotion was never written to the repo.

### Other introduced services

**Zero**. Better Stack and Pingdom appear only in the same enumeration as UptimeRobot. No accounts, no API keys, no integration code, no recipe step.

## 4. Infrastructure-provisioning instructions as §3.4 prerequisites

| File | Line | Quote | Verdict |
|---|---|---|---|
| `docs/grant/02-execution-plan.md` | 354 | `[ ] Pick hosting provider` | **Treat as Phase 2 polish, not §3.4 prerequisite.** The maintainer has existing deployment infrastructure (see Part C below); §3.4 should re-anchor to that, not provision new. |
| `docs/grant/02-execution-plan.md` | 355 | `[ ] Secure domain (directjob-scout.eu or similar)` | Same — existing subdomain already in use. |
| `docs/grant/02-execution-plan.md` | 356 | `[ ] Deploy the canonical reference implementation` | This is the existing-infrastructure scope. The maintainer's `scripts/deploy.sh` already exists and is mature. Re-anchor §3.4 around using it. |
| `docs/grant/02-execution-plan.md` | 357 | `[ ] Pre-seed with the persona-panel example users (Aïcha, Yusuf, Olga, Mahmoud, Maria)` | Pre-Decision-21 persona list (five). Needs updating to seven personas per Decision 21. Persona seeding itself is in-scope for §3.4 (a real deliverable that doesn't depend on new infrastructure). |
| `docs/grant/02-execution-plan.md` | 358 | `[ ] Add health-check monitoring` | Generic. Can stay; the existing `scripts/production-smoke.sh` and `/api/health` give the maintainer what they need. |
| `docs/grant/02-execution-plan.md` | 359 | `[ ] Document the deployment recipe in docs/deployment-recipe.md` | Recipe document is in-scope — and should be a **generic recipe**, not Hetzner-specific. |
| `docs/grant/02-execution-plan.md` | 360 | `[ ] Add the demo URL to README and to the application package` | In-scope. Wait on the maintainer's existing-subdomain decision (see Part C). |

## 5. Confused or contradictory planning-doc passages

| File | Issue |
|---|---|
| `docs/grant/02-execution-plan.md` §3.4 (lines 352–360) | The unchecked task list reads as if the maintainer needs to provision hosting + a domain + deploy from scratch. The maintainer's existing infrastructure (`scripts/deploy.sh` referencing `SSH_HOST` and `PUBLIC_URL`) shows a live deployment process already exists. The §3.4 task list needs re-anchoring to acknowledge the existing-infrastructure baseline. |
| `docs/grant/02-execution-plan.md` §3.4 persona list | Five personas listed (`Aïcha, Yusuf, Olga, Mahmoud, Maria`); per Decision 21 the panel is seven. |
| `docs/grant/05-risks-and-stakeholders.md:90` | Hardcoded `demo.directjob-scout.eu` placeholder URL; should be domain-neutral. |
| `docs/mcp-server.md:212, 215, 248` | Hardcoded `https://demo.directjob-scout.example` URLs in §2.2 docs. These match the **Week 1 task 1.4 sanitisation convention** (`.example` TLD per RFC 2606) and are NOT false dependencies. Leave as-is. |
| `README.md:288` | `demo.<public-domain>` template-style placeholder; correct. Leave as-is. |
| `docs/grant/12-application-package.md:107` | `demo.<domain>` template placeholder; correct. |
| `docs/grant/04-research-and-decisions.md:441` (Open R8) | `Demo deployment in Week 3 needs a stable URL (`demo.<domain>` or similar)`. Template placeholder; correct. **However, the question itself is now resolved by the existing-infrastructure framing — see Part C/D.** |

## 6. Stale §2.5 housing-agent / friend-response references

| File | Line | Status |
|---|---|---|
| `CLAUDE.md` | 67 | Decision-table row reflects Decision 20 correctly. |
| `CHANGELOG.md` | 165 | Mentions Decision 20 partially superseding Decision 11; correct. |
| `docs/releases/v0.1.0.md` | 171–174 | "2026-05-23 outreach window" — that window is **active until 2026-05-23**; not stale yet. |
| `docs/grant/02-execution-plan.md` | 248 (§2.5 guardrail) | Decision 20 guardrail correctly stated; in-scope. |
| `docs/grant/11-institutional-outreach.md` | 288 | Template H references Decision 20 correctly. |
| `docs/grant/04-research-and-decisions.md` | 244 (Decision 11 forward-pointer) | Forward-pointer to Decision 20 correctly placed. |

**No stale §2.5 references found.** The friend-response window has not yet closed (today is 2026-05-18; window closes ~2026-05-23). No action needed in this cleanup.

## 7. Artifacts created in the last 48 h that exist to support an unintended dependency

**Files created or substantially modified in the last 48 h** (per `git log --since="48 hours ago" --name-only`):

- `Week 3 task 3.3 (74f98f4)`: `CHANGELOG.md`, `README.md`, `ROADMAP.md`, `docs/grant/02-execution-plan.md`, `docs/releases/v0.1.0.md` — release-discipline deliverables. **None tied to Hetzner / .eu / Cloudflare / UptimeRobot.**
- `d4844a9 ci: narrow tests matrix to ubuntu`: tests workflow scope narrowing. Not infrastructure-related.
- `95c0ab7 ci: upgrade pypdf`: dependency upgrade. Not infrastructure-related.
- `11c9542 mcp-integration: fix post-success step PYTHONPATH`: CI bug fix. Not infrastructure-related.
- `Week 3 task 3.2 (c79f68e)`: CI expansion. Not infrastructure-related.
- `Week 3 task 3.1 (63b55c8)`: pin cryptography. Not infrastructure-related.
- `Week 2 task 2.8 (275e55e)`: AI Act compliance pack. Not infrastructure-related.

**Verdict**: zero artifacts created to support the false dependencies. The uncommitted work that was rejected by the maintainer (rename + edits to `deploy/.env.production.template`) was reverted to the clean baseline.

---

## Existing infrastructure baseline — what is actually here today

These files document the maintainer's existing deployment infrastructure and have been in the repo since before the grant sprint. **None of these need to change** in the cleanup; they ARE the existing infrastructure.

| File | Purpose |
|---|---|
| `docker-compose.prod.yml` | Production Compose with `directjob-scout` + `caddy` services, named volumes, healthcheck on `/api/health`, env-var driven configuration. |
| `deploy/Caddyfile` | Generic Caddy config with `${DIRECTJOB_DOMAIN}` and `${DIRECTJOB_ADMIN_EMAIL}` env-var substitution; reverse-proxies to `directjob-scout:8765` with HSTS. |
| `deploy/production.env.template` | Generic production `.env` template covering domain + crypto, initial admin, hardening, email, quotas, backups, monitoring, legal, billing, AI provider keys. **Generic — not Hetzner-specific.** |
| `scripts/deploy.sh` | Incremental redeploy script (rsync + docker compose) with WAL-aware snapshot, image tagging for rollback, SSH multiplexing, health-check assertion. Generic — works against any SSH-accessible deployment target. |
| `scripts/deploy-with-backup.sh` | Wrapper that adds a pre-deploy backup step. |
| `scripts/pre-deploy-snapshot.sh` | WAL-aware sqlite snapshot before deploy. |
| `scripts/backup-production.sh` | Backup script supporting `local`, `rclone`, `s3` backends. |
| `scripts/production-smoke.sh` | Post-deploy smoke test. |
| `scripts/production-readiness-check.sh` | Pre-deploy readiness gate that reads `.env`. |
| `scripts/restore-drill.sh` | Restore drill from backup. |
| `docs/production-deployment.md` | Existing production-deployment documentation. Generic. |

The cleanup must not introduce a parallel Hetzner-specific stack; the existing stack is generic and sufficient.

---

## Findings summary

| Category | False-dependency artifact in repo? |
|---|---|
| Hetzner-specific scripts / Dockerfile / compose / recipe | **No** (zero artifacts created or committed) |
| `directjob-scout.eu` hardcoded as registered domain | **No** (zero code; two pre-existing planning-text placeholders to clean) |
| Cloudflare Registrar | **No** (zero references) |
| UptimeRobot promoted to commitment | **No** (one pre-existing option-enumeration, acceptable) |
| Infrastructure-provisioning instructions in §3.4 critical path | **Partial** (§3.4 planning text needs re-anchoring to existing infrastructure) |
| Confused / contradictory planning passages | **Yes**, in `docs/grant/02-execution-plan.md` §3.4 + persona-list staleness + `docs/grant/05-risks-and-stakeholders.md:90` |
| Stale §2.5 housing-agent references | **No** (Decision 20 framing consistent; friend-response window still active) |
| New artifacts created for false dependencies | **No** (all recent commits are real grant-sprint deliverables) |

**Net cleanup scope**: documentation-only changes in 2–3 planning-workspace files, plus the §3.4 re-anchoring. **Zero code changes. Zero new files created. Zero file deletions.**

The repo is in better shape than the prior advisory prompt's framing implied. The "advisory failure" was an **advisory-prompt-text** failure, not a **repo-state** failure — the uncommitted Edit was rejected before it could land.
