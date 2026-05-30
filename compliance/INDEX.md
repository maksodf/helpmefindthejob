<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Compliance pack — index

**Purpose**: single-page map of every artefact in the `compliance/` directory, the AI Act / GDPR article each one addresses, and a one-line summary of what's inside. Use this as the entry point when (a) a reviewer asks "where does the project address Article X?", (b) a deployer reads the pack end-to-end, or (c) you are linking the application narrative to specific artefacts.

**Last updated**: 2026-05-30. Append a dated note when adding, retiring, or restructuring an artefact below.

---

## How to read this index

Each row names the artefact, the primary article it addresses, and one sentence on what the file actually contains. The right-most column maps to the audience that should treat the file as load-bearing — `provider` (project maintainer), `deployer` (institutional adopter), `user` (data subject), or `auditor` (NLnet reviewer, supervisory authority, contract auditor).

The pack is designed to be **self-contained**: every regulatory obligation a deployer faces has a corresponding compliance artefact, every article a reviewer asks about has a referenceable doc. Cross-references inside each file point onward; this index is the entry point.

---

## Pack contents

| File | Primary article(s) | Purpose | Audience |
|---|---|---|---|
| [`README.md`](README.md) | (none — meta) | Overview of the pack, ordering, how to navigate. Start here on first read. | All |
| **Provider obligations** | | | |
| [`risk-management-plan.md`](risk-management-plan.md) | AI Act Article 9 | The project-level risk-management system: identified risks, mitigations, residual risk acceptance, change-management triggers. Updated on every major release. | provider, auditor |
| [`data-governance.md`](data-governance.md) | AI Act Article 10 | Data classification, processing inventory, retention policy, lawful basis, third-party transfers, security controls. The GDPR Article 30 equivalent for the project. | provider, deployer, auditor |
| [`technical-documentation.md`](technical-documentation.md) | AI Act Article 11 + Annex IV | The full Annex IV technical-doc bundle: system architecture, components, intended purpose, training-data summary (BYO-AI — empty for the project), accuracy metrics, human-oversight measures, change log. | provider, auditor |
| [`audit-log-schema.md`](audit-log-schema.md) | AI Act Article 12 | The structured schema of `ai_act_audit.log`, HMAC chaining, salt handling, retention, query examples. Pairs with `company_discovery/audit_log.py`. | provider, deployer, auditor |
| [`audit-log-key-rotation.md`](audit-log-key-rotation.md) | AI Act Article 12 + Article 26(6) + GDPR Article 32 | Operational playbook for rotating `HELPMEFINDTHEJOB_AUDIT_SALT`. When to rotate, 8-step procedure, prior-keys metadata lifecycle (active / sealed / destroyed), dated rotation log. | deployer, auditor |
| [`article-20-export-proof.md`](article-20-export-proof.md) + [`article-20-export-sample.json`](article-20-export-sample.json) | GDPR Article 20 + AI Act Article 26(6) | End-to-end runtime proof that all 5 export endpoints (imported.csv/md, discovered.csv/md, /api/data/export bundle) return HTTP 200 with valid payloads. Includes the reproducibility recipe, the verbatim 2026-05-24 run output, the 19-key Article 20 bundle schema, and a sample bundle JSON committed alongside for offline inspection. | deployer, auditor |
| [`human-oversight-guide.md`](human-oversight-guide.md) | AI Act Article 14 | The architecture of human-oversight: provider-side surfaces (`HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE`, `/api/admin/oversight/queue`), deployer-side responsibilities, the kill-switch (`HELPMEFINDTHEJOB_DETERMINISTIC_ONLY`), appointment record. | provider, deployer, auditor |
| [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md) | AI Act Article 15 (accuracy + robustness) | The persona-anchored bias-testing methodology, pre-deployment re-test framework, performance ratios, current results, dated run log. References `docs/grant/bias-comparative-report-*.md`. | provider, deployer, auditor |
| [`prompt-injection-testing.md`](prompt-injection-testing.md) | AI Act Article 15(5) (resilience to manipulation) | The 10 canonical prompt-injection vectors, surface + defence-layer mapping, structural-defence rationale, live-provider re-test procedure, new-vector intake workflow, methodology limitations. Pairs with `tests/test_prompt_injection_vectors.py`. | provider, deployer, auditor |
| **Deployer obligations** | | | |
| [`deployer-operating-manual.md`](deployer-operating-manual.md) | AI Act Article 13 (transparency to deployers) + Article 26 (deployer obligations) | The end-to-end deployer manual: who you serve, the Article 26 obligations table, pre-deployment checklist, configuration, human-oversight setup, audit log handling, transparency, **§8.1 Article 22 right-to-human-review procedure**, operational tasks, incident response, decommissioning. The single working doc the deployer needs. | deployer |
| [`fundamental-rights-impact-assessment-template.md`](fundamental-rights-impact-assessment-template.md) | AI Act Article 27 (public-authority FRIA obligation) | Eight-part FRIA template anchored to the friction-class framing: deployer profile, affected population, AI-system properties, FR-impact analysis, mitigations, monitoring, remediation channels, governance, conclusion. Maintainer-attested as a deliverable; deployer fills the deployment-specific slots. | deployer, auditor |
| [`fria-aicha.md`](fria-aicha.md), [`fria-yusuf.md`](fria-yusuf.md), [`fria-olga.md`](fria-olga.md), [`fria-mahmoud.md`](fria-mahmoud.md), [`fria-maria.md`](fria-maria.md), [`fria-kaethe.md`](fria-kaethe.md), [`fria-tobias.md`](fria-tobias.md) | AI Act Article 27 (per-persona FRIA execution) | Seven per-persona FRIA instantiations of the template above. Each: persona identity + friction context, affected-population scale, Charter-of-Fundamental-Rights engagement table (5-6 Articles per persona modulated to that persona's specific friction class), R1–R8 risk modulation, top-concern + compensating control, Article 22 escalation pathway, maintainer attestation. Mahmoud carries the highest residual risk in the cohort (R6 data-egress = M×H) due to asylum-stage information sensitivity; Olga is second-highest (R1+R2 combined = M×M each) due to cross-provider score-spread + language-gate over-exclusion. | provider, deployer, auditor |
| [`gdpr-article-35-dpia.md`](gdpr-article-35-dpia.md) | GDPR Article 35 (DPIA for high-risk processing) — pairs with AI Act Article 27 FRIA per EDPB Guidelines 04/2024 | Seven-section GDPR Article 35 DPIA: systematic description (nature + scope + purpose + context + lawfulness), necessity-and-proportionality, risk register (9 risk classes with L×S scoring + mitigations, top residuals named explicitly), mitigation measures (technical + organisational + compensating-controls for highest-residual risks), consultation flow (data subject, DPO, supervisory authority), maintenance + review triggers, dated append log. Both project-side reference assessment AND template for deployer instantiation. | deployer, auditor |
| [`incident-response-drill.md`](incident-response-drill.md) | AI Act Article 73 (serious-incident reporting) + GDPR Article 33 (breach notification 72 h) + Article 26(5) (deployer monitoring obligation) | Quarterly incident-response drill methodology + 4 canonical scenarios (A personal-data breach, B compromised audit-log key, C AI-output bias incident, D supply-chain compromise) + 4-step drill procedure (pre-setup, open, close+AAR, documented update) + maintainer-side scenarios (M1 incident-ai-act issue triage, M2 security disclosure) + dated drill log. Rehearses the `deployer-operating-manual.md` §10 5-step workflow under realistic time pressure so the deployer team is not making decisions cold during a real incident. | deployer, auditor |
| [`eu-database-registration-template.md`](eu-database-registration-template.md) | AI Act Article 49 (registration of high-risk AI systems) | The structured registration template for the EU AI database. Pre-filled with project-side fields; deployer fills deployer-side fields and submits before going live. | deployer |
| [`dpa-template.md`](dpa-template.md) | GDPR Article 28 (processor obligations) | Data Processing Agreement template for the deployer-side processor relationships (the BYO-AI provider especially). Annex II controls map to the project's actual deployment surface. | deployer |
| **User-facing** | | | |
| [`transparency-notice.md`](transparency-notice.md) | AI Act Article 13 (adapted to user-facing) + Article 50 (transparency to natural persons) | The plain-language notice users see at first run and at `/transparency`: what the system does, what data is processed, what AI providers are involved, user rights (Article 22 + Article 86), GDPR rights, complaint channels, limitations. Deployer fills the `[Deployer-managed addendum]` section. | user, deployer |

---

## Runtime mechanism status — code-wired vs deployer-operated vs planned

The pack above maps *documents* to articles. This section maps the *runtime mechanisms* to their honest implementation state, so a reviewer or deployer sees at a glance what the product enforces in code versus what is a deployer operational step, a manual procedure, or a specified-but-unbuilt Phase-2 item. This is the single consolidated "true picture" — the per-file caveats (`audit-log-schema.md` §4.4–4.6, `deployer-operating-manual.md` §6.5, `human-oversight-guide.md`) all roll up here.

**Legend**: ✅ **Code-wired** — implemented in the product and covered by automated tests · ⚙️ **Deployer-operated** — the app exposes the surface/flag; the deployer performs the step (shared obligation per Article 26) · 📋 **Manual procedure** — a written procedure exists, executed by a human (DPO/operator), not yet an automated endpoint · 🔭 **Planned** — specified in the schema/docs, not built at this version (honest alpha state).

| Mechanism | Article(s) | Status | Where it lives / what is missing |
|---|---|---|---|
| Structured audit log — JSONL, HMAC hash-chained, salted, rotating | AI Act 12 | ✅ Code-wired | `company_discovery/audit_log.py`; `tests/test_audit_log_tamper_evidence_13.py` |
| Core events — `ai_invocation`, `mcp_tool_invocation`, `system_event` | AI Act 12 | ✅ Code-wired | emitted from `analysis.py`, `mcp_server.py`, `db_errors.py` |
| `consent_event` — AI-provider consent grant/revoke (provider named in scope) | AI Act 12 / GDPR 7 | ✅ Code-wired | `app.py` `update_profile`; `tests/test_audit_consent_export_events.py` |
| `export_event` — full data export (`profile_full`), user self-export **and** admin export, recorded in the subject's slice | AI Act 12 / GDPR 15, 20 | ✅ Code-wired | `app.py` `export_data_audited`; same test |
| `consent_event` — `third_party_share` / `mcp_composition` / `audit_log_plaintext_pii` topics | AI Act 12 | 🔭 Planned | schema §4.4 reserves them; those consent surfaces are not built (a deployer enabling plaintext-PII records the justification out-of-band per DPIA) |
| `export_event` — `audit_log_self` (a user's slice of the chained log itself) | AI Act 12 / 86 | 📋 Manual procedure | DPO extracts per request; the automated extraction endpoint is not built (§4.5) |
| `override_event` — an advisor edits/rejects an AI output | AI Act 12 / 14 | 🔭 Planned | the oversight queue is review-only; the intercept/edit/reject workflow that would emit it is not built (§4.6) |
| Audit-log retention auto-prune (`HELPMEFINDTHEJOB_AUDIT_RETENTION_DAYS`) | AI Act 12 | ⚙️ Deployer-operated | flag is documented but **not read by the app**; the deployer prunes per jurisdiction |
| Human-oversight kill-switch (`HELPMEFINDTHEJOB_DETERMINISTIC_ONLY`) | AI Act 14 | ✅ Code-wired | `company_discovery/analysis.py` — forces the deterministic / no-AI path deployment-wide |
| Human-oversight review queue (env-gated) | AI Act 14 | ✅ Code-wired (MVP) | `/api/admin/oversight/queue`, in-memory; an SQLite-backed variant is Phase 2 |
| Right to human review / explanation | AI Act 22, 86 / GDPR 22 | 📋 Manual procedure | `deployer-operating-manual.md` §8.1 procedure + the user activity view at `/api/audit-log`; a per-decision "explain this score" endpoint is 🔭 planned |
| Accuracy + bias testing (persona-anchored) | AI Act 15 | ✅ Code-wired | `accuracy-and-bias-testing.md`; bias-methodology tests |
| Prompt-injection resilience | AI Act 15(5) | ✅ Code-wired | `tests/test_prompt_injection_vectors.py` |
| Right to erasure — full account + all user-scoped data | GDPR 17 | ✅ Code-wired | `repository.delete_all_user_data`; `app.py` `delete_user_account`; `tests/test_account_erasure.py` |
| Data portability — 19-key export bundle | GDPR 20 | ✅ Code-wired | `app.py` `export_data`; `article-20-export-proof.md` |

The supplementary job-list downloads at `/api/exports/*.csv` / `*.md` are operational exports of non-identity job data already covered by the logged `profile_full` export, so they deliberately do not emit their own `export_event`.

---

## What is NOT in this pack

For transparency on what reviewers should NOT expect to find in `compliance/`:

- **Pen-test reports** — scoped for a future release; first pen-test scheduled pre-v1.0.
- **DPA-signed PDFs** — `dpa-template.md` is the template; signed copies will land as `compliance/dpa-signed-*.pdf` (gitignored) on the deployer's environment, never in the public repo.
- **Per-deployer FRIA executions** — the template is project-side; each deployer's filled FRIA is private to that deployment and lives outside this repo.
- **AI Provider Honesty Matrix** — lives at [`../docs/grant/15-ai-provider-honesty-matrix.md`](../docs/grant/15-ai-provider-honesty-matrix.md) because it's grant-application supporting material, not a compliance obligation per se.
- **Bias-testing run reports** — methodology is here at `accuracy-and-bias-testing.md`; the surviving dated execution report is `../docs/grant/bias-comparative-report-2026-05-21.md` (the earlier interim `bias-testing-*` snapshots were consolidated into `../docs/grant/04-research-and-decisions.md` Part B in commit e85946b).
- **Source-class hierarchy** — `../docs/grant/14-source-class-hierarchy.md` (grant-side citation discipline; not an Article-mapped obligation).
- **Security audit (gitleaks history scan)** — `../docs/grant/SECURITY-AUDIT.md` because it's a one-off audit artefact rather than a recurring deployer artefact.

---

## Article-to-file reverse lookup

For reviewers who think in articles rather than file names:

| Regulation | Article | File(s) |
|---|---|---|
| AI Act | Article 9 (risk management) | `risk-management-plan.md` |
| AI Act | Article 10 (data governance) | `data-governance.md` |
| AI Act | Article 11 + Annex IV (technical documentation) | `technical-documentation.md` |
| AI Act | Article 12 (record-keeping) | `audit-log-schema.md`, `audit-log-key-rotation.md` |
| AI Act | Article 13 (transparency to deployers / users) | `deployer-operating-manual.md`, `transparency-notice.md` |
| AI Act | Article 14 (human oversight) | `human-oversight-guide.md` |
| AI Act | Article 15 (accuracy / robustness / cybersecurity) | `accuracy-and-bias-testing.md`, `prompt-injection-testing.md` |
| AI Act | Article 22 (user appeal right) | `deployer-operating-manual.md` §8.1, `transparency-notice.md` |
| AI Act | Article 26 (deployer obligations) | `deployer-operating-manual.md`, `audit-log-key-rotation.md` |
| AI Act | Article 27 (FRIA) | `fundamental-rights-impact-assessment-template.md` |
| AI Act | Article 49 (EU database registration) | `eu-database-registration-template.md` |
| AI Act | Article 50 (transparency to natural persons) | `transparency-notice.md` |
| AI Act | Article 73 (incident reporting) | `deployer-operating-manual.md` §10 |
| AI Act | Article 86 (right to explanation) | `transparency-notice.md`, `deployer-operating-manual.md` §8.1 |
| GDPR | Article 5 (principles) | `data-governance.md`, `audit-log-key-rotation.md` (integrity principle) |
| GDPR | Article 20 (data portability) | `deployer-operating-manual.md` §6.5, `transparency-notice.md` |
| GDPR | Article 22 (automated decisions) | `transparency-notice.md`, `deployer-operating-manual.md` §8.1 |
| GDPR | Article 28 (processor obligations) | `dpa-template.md` |
| GDPR | Article 30 (records of processing) | `data-governance.md` |
| GDPR | Article 32 (security of processing) | `audit-log-key-rotation.md`, `data-governance.md` |
| GDPR | Article 33 (breach notification) | `deployer-operating-manual.md` §10 |
| GDPR | Article 35 (DPIA) | `fundamental-rights-impact-assessment-template.md` (cross-references) |

---

## Append log

- **2026-05-24**: INDEX created. Includes the 11 pre-existing artefacts plus the 2 new ones from box 1.4.3 (audit-log-key-rotation) and box 1.4.4 (prompt-injection-testing). Article-reverse-lookup table reconciles every Article-cited obligation across the pack to its file. Maintainer reviewed for completeness against AI Act Chapter III (Articles 8-29) and the GDPR articles invoked by the data-flow.
- **2026-05-30**: Added the "Runtime mechanism status" matrix — the single consolidated code-wired vs deployer-operated vs manual vs planned picture, rolling up the per-file caveats. Reflects the M4 record-keeping work: `consent_event` (AI-provider consent) and `export_event` (`profile_full`, user + admin) are now code-wired in `app.py` (`update_profile` / `export_data_audited`) with `tests/test_audit_consent_export_events.py`, returning the `audit-log-schema.md` §4.4/§4.5 and `deployer-operating-manual.md` §6.5 claims from "specified, not yet emitted" to "emitted." `override_event` (advisor-review), `audit_log_self` extraction, the other `consent_topic` values, and retention auto-prune are documented at their honest status (planned / manual / deployer-operated). Does not touch the article-to-file reverse-lookup table, so the manifest↔INDEX drift guard (`tests/test_compliance_traceability.py`) is unaffected.
