<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Operator runbook — project-maintainer's own self-host

**Audience**: the project maintainer running the canonical `helpmefindthejob.org` deployment + the `demo.helpmefindthejob.org` subdomain. For **deployer-side** operating procedures (Beratungsstellen / IQ-Netzwerk / Optionskommunen Jobcenter / NGO / university career service), the load-bearing doc is `compliance/deployer-operating-manual.md` (AI Act Article 26 obligations + the full operational chain).

**Status**: living document. Append a dated quarterly review row to §3 on every cadence checkpoint.

---

## 1. Cadence summary (the table the maintainer prints + checks against)

This is the consolidated maintenance cadence the maintainer runs against the project's own self-host. It pulls together items scattered across the compliance pack so the next-cadence checklist is a single read.

| Item | Cadence | Source-of-truth | Next due |
|---|---|---|---|
| Audit-log key rotation | Annual (calendar) + 6 incident classes | [`compliance/audit-log-key-rotation.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/audit-log-key-rotation.md) §3 | 2027-Q2 |
| Bias re-test | Annual minimum; pre-release on `v*.0.0` | [`compliance/accuracy-and-bias-testing.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/accuracy-and-bias-testing.md) §3 + §10 (v2 scaffold) | 2026-Q4 (with the first NGO pilot) |
| Prompt-injection live-provider re-test | Quarterly + pre-release | [`compliance/prompt-injection-testing.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/prompt-injection-testing.md) §4 | 2026-Q3 (alongside v0.80.0 sign) |
| Incident-response drill | Quarterly | [`compliance/incident-response-drill.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/incident-response-drill.md) §3 | 2026-Q4 (Scenario A, with first NGO pilot) |
| Backup + restore drill | Quarterly | [`compliance/deployer-operating-manual.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/deployer-operating-manual.md) §9.3 | 2026-Q3 |
| TLS renewal verification | Continuous (Caddy auto-renews); spot-check monthly | [`compliance/deployer-operating-manual.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/deployer-operating-manual.md) §9.4 | rolling |
| Article 22 quarterly aggregate review | Quarterly | [`compliance/deployer-operating-manual.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/deployer-operating-manual.md) §8.1 step 8 | 2026-Q3 (no requests received yet — review is "zero requests this quarter") |
| DPIA review | Annual + on triggers | [`compliance/gdpr-article-35-dpia.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/gdpr-article-35-dpia.md) §6 | 2027-Q2 |
| Source-class hierarchy re-verification | 30-day freshness window | [`docs/grant/14-source-class-hierarchy.md`](grant/14-source-class-hierarchy.md) append log | 2026-06-23 (30 days after last pass) |
| Quality dashboard re-run | Pre-release on `v*.X.0` | (the standing 3199-test unit suite + the dated `bias-testing-*.md` reports) | 2026-Q4 |

If the deployer has a tracked-issue board (GitHub Projects / Linear / Jira), each cadence item lives on the board with the next-due date pinned.

---

## 2. Pre-launch maintainer checklist (already done as of 2026-05-24)

This is the checklist the maintainer ran before the v0.80.0 NLnet-submission tag. Everything below is closed; the table is preserved for audit-trail continuity.

| Item | Done | Where to verify |
|---|---|---|
| Repo flipped to public | ✅ 2026-05-24 | `gh repo view maksodf/helpmefindthejob --json visibility` → `"PUBLIC"` |
| Repo description sanitised (no `khalo.org` residue) | ✅ 2026-05-24 | `gh repo view maksodf/helpmefindthejob --json description` |
| 12 canonical topic tags added | ✅ 2026-05-24 | `gh repo view maksodf/helpmefindthejob --json repositoryTopics` |
| README hero with screenshots + value props | ✅ 2026-05-24 | `head -90 README.md` |
| CI workflows green on main (tests, fresh-clone-install, mcp-integration, quality, scorecard, docs-publish) | ✅ 2026-05-24 | `gh run list --branch main --limit 10` (all `completed success`) |
| CHANGELOG cut to `[0.80.0] — 2026-05-24` | ✅ 2026-05-24 | `grep '^## \[' CHANGELOG.md` |
| v0.80.0 release artefacts authored | ✅ 2026-05-24 | `ls docs/releases/v0.80.0*` |
| Cosign signing recipe documented | ✅ 2026-05-24 | `docs/releases/v0.80.0-signing.md` |
| CycloneDX SBOM generated (8 direct deps) | ✅ 2026-05-24 | `docs/releases/v0.80.0-sbom.json` |
| Gitleaks full-history scan + audit summary | ✅ 2026-05-24 | `docs/grant/SECURITY-AUDIT.md` (17 false-positive hits, 0 real secrets) |
| Compliance pack INDEX (14 docs) | ✅ 2026-05-24 | `compliance/INDEX.md` |
| AI-Act-Article-22 right-to-human-review procedure | ✅ 2026-05-24 | `compliance/deployer-operating-manual.md` §8.1 |
| AI-Act-Article-15(5) prompt-injection methodology + 8 unit tests | ✅ 2026-05-24 | `compliance/prompt-injection-testing.md` + `tests/test_prompt_injection_vectors.py` |
| GDPR-Article-20 export end-to-end proof | ✅ 2026-05-24 | `compliance/article-20-export-proof.md` |
| GDPR-Article-35 DPIA | ✅ 2026-05-24 | `compliance/gdpr-article-35-dpia.md` |
| Incident-response drill methodology | ✅ 2026-05-24 | `compliance/incident-response-drill.md` |
| Source-class hierarchy 30-day re-verification | ✅ 2026-05-24 | `docs/grant/14-source-class-hierarchy.md` append log |
| Per-persona walks (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) | ✅ 2026-05-24 | `docs/persona-walks/` |
| Self-host tutorial | ✅ 2026-05-24 | `docs/self-host-tutorial.md` |
| MCP integration guide | ✅ 2026-05-24 | `docs/mcp-integration-guide.md` |
| API client examples | ✅ 2026-05-24 | `docs/api-client-examples.md` |
| Public roadmap page | ✅ 2026-05-24 | `static/roadmap.html` |
| OpenGraph card audit | ✅ 2026-05-24 | internal QA log |

---

## 3. Quarterly review log

The maintainer appends a dated row here every 3 months (the cadence stays even when there are zero incidents — "nothing happened this quarter" is itself accountability evidence under Article 5(2) GDPR + Article 13 AI Act).

| Quarter | Cadence items run | Incidents | Notes |
|---|---|---|---|
| 2026-Q3 | (will land after v0.80.0 is cut + the NLnet submission goes in; first checkpoint planned 2026-08-31 to align with the AI Act 2026-08-02 enforcement date) | n/a | Initial scaffold — append the first real entry at quarter end. |

Append below this row at each quarter-end. Never overwrite a prior row.

---

## 4. Where this file does NOT apply

This file is the **maintainer's own** project-self-host runbook. It does NOT govern:

- Deployer-side operations at a Beratungsstelle / Jobcenter / NGO / university career service — see `compliance/deployer-operating-manual.md` (the AI Act Article 26 deployer manual) for that audience.
- Production-hardening cadence for the deployment infrastructure itself (Docker / Caddy / SQLite / cron-based backups) — see `docs/observability-runbook.md` for that.
- The AI-Act-and-GDPR compliance pack itself — see `compliance/INDEX.md` for the full file × Article reverse-lookup.
- The grant application + post-grant roadmap — see `docs/grant/00-START-HERE.md` for the planning workspace + `docs/grant/03-post-grant.md` for the Phase-2 roadmap.

---

## 5. Cross-references

- Deployer operating manual: [`compliance/deployer-operating-manual.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/deployer-operating-manual.md)
- Compliance INDEX: [`compliance/INDEX.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/INDEX.md)
- v0.80.0 release notes + signing recipe: [`releases/v0.80.0.md`](releases/v0.80.0.md) + [`releases/v0.80.0-signing.md`](releases/v0.80.0-signing.md)
- ROADMAP: [`https://github.com/maksodf/helpmefindthejob/blob/main/ROADMAP.md`](https://github.com/maksodf/helpmefindthejob/blob/main/ROADMAP.md)
- PlanTowardPerfection (active backlog): [`https://github.com/maksodf/helpmefindthejob/blob/main/PlanTowardPerfection.MD`](https://github.com/maksodf/helpmefindthejob/blob/main/PlanTowardPerfection.MD)
- Security disclosure channel: [`https://github.com/maksodf/helpmefindthejob/blob/main/SECURITY.md`](https://github.com/maksodf/helpmefindthejob/blob/main/SECURITY.md)
