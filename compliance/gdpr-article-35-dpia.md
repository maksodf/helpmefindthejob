<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# GDPR Article 35 — Data Protection Impact Assessment

**Article**: GDPR Article 35 (Data Protection Impact Assessment for high-risk processing). Pairs with AI Act Article 27 (Fundamental Rights Impact Assessment) — see [`fundamental-rights-impact-assessment-template.md`](fundamental-rights-impact-assessment-template.md). Where the two assessments overlap, you can satisfy both via a combined GDPR-Art-35 + AI-Act-Art-27 instrument (the European Data Protection Board recommends this convergence — see EDPB Guidelines 04/2024 on Article 35).
**Audience**: deployer's Data Protection Officer (DPO); provider's maintainer for the project-side reference assessment.
**Status**: living document. Updated alongside every major release that changes a processing operation.
**Scope**: GDPR Article 35 DPIA for the production deployment with real numbers (a tracked post-grant deliverable; currently a reference/template). The text below is BOTH the project-side reference DPIA (anchored to the maintainer's own self-host as a worked example) AND a template the institutional deployer instantiates for their deployment context.

---

## Why this DPIA exists

GDPR Article 35(1) requires a DPIA when processing is "likely to result in a high risk to the rights and freedoms of natural persons". The Article 29 Working Party (now EDPB) Guidelines list nine criteria; processing that meets **two or more** triggers the mandatory DPIA. Helpmefindthejob's processing meets at least three:

- **Evaluation or scoring**: AI-assisted fit-scoring of job applicants against roles (Article 35(3)(a)).
- **Sensitive data / special categories**: Profile data includes residency status, language proficiency, employment history; in DACH context the residency-status field can carry quasi-sensitive information (visa class, asylum stage).
- **Data concerning vulnerable data subjects**: Migrants in active visa proceedings, returnees from caregiving absence, long-term unemployed users.

Therefore: DPIA is mandatory before going live. This document is the assessment.

---

## 1. Systematic description of the processing

### 1.1 Nature of the processing

Helpmefindthejob is a self-hostable open-source web application that supports a user (the data subject) through a job-search journey. The journey covers: profile creation (persona, target roles, location, languages, CV text), discovered-job ingestion (via aggregators or per-company watchlist scans), AI-assisted fit-scoring + tailored CV editing + motivation-letter drafting, and application tracking.

### 1.2 Scope (categories of data subjects + categories of personal data)

| Category | Examples | Source |
|---|---|---|
| **Profile fields** | Email, display name, persona slug, language, target roles, target location, residency status (free text), friction notes | User-entered |
| **CV text** | Free-text CV body (encrypted-at-rest under ChaCha20-Poly1305 AEAD) | User-entered or pasted from PDF |
| **Discovered + imported jobs** | URL, title, company, location, source-attribution metadata, AI-derived fit score + reason + gaps | Aggregator scans + AI-call results |
| **Chat session state** | Last 6 turns of chat history, journey-phase state, slash-command history | User-session-derived |
| **Audit log** | Per-event opaque user ID (HMAC-salted), action class, model + provider + cost-cap context, ISO-8601 timestamp | System-derived, GDPR Art. 32 + AI Act Art. 12 |
| **Workspace memberships** | Workspace ID, role (admin/member/owner) | Operator-assigned |
| **Application outcomes** | Mark-applied, response received, offer received | User-entered, optional |

### 1.3 Purpose of the processing

To support the user's job-search journey with knowledge that is otherwise locked behind paid advisors. The cost-saving doctrine ([`../docs/grant/08-cost-saving-doctrine.md`](../docs/grant/08-cost-saving-doctrine.md)) explicitly frames this as institutional-cost reduction without diminishing user outcomes — i.e., processing is *necessary* for the stated public-interest purpose (Article 6(1)(e) when deployed by a public authority) or *legitimate interest balanced against the user's expectation* (Article 6(1)(f) in non-public-authority deployments).

### 1.4 Context

| Field | Value |
|---|---|
| Data controller | The deployer (NOT the project) — see `deployer-operating-manual.md` |
| Data processor | (a) The deployer (host-side processing); (b) the BYO-AI provider chosen by the deployer (if any); (c) the maintainer for issue-reporting only via consented support data |
| Storage location | Deployer-controlled (default: SQLite file in the deployer's data directory; PostgreSQL also supported per `compliance/data-governance.md`) |
| Retention | 180 days default for audit log; user-controlled for profile data (right of erasure via `/api/account/deletion-request`); deployer-controlled per their organisational retention policy |
| Cross-border transfers | Deployer-side decision. Default deployment carries no cross-border element; BYO-AI providers may introduce one (e.g., OpenAI API → US transfer). The `transparency-notice.md` discloses this; the deployer's DPA template (`dpa-template.md`) handles processor-side compliance. |
| Special categories | CV text can include health information (declared illness in employment-gap explanation); residency status field may carry asylum-stage information. Both are user-entered; the user is informed at entry that these fields will be processed. |

### 1.5 Necessity and proportionality

The processing meets Article 5 GDPR principles:

- **Lawfulness, fairness, transparency** (Art. 5(1)(a)): User consents to AI processing at first profile creation; `transparency-notice.md` is shown at first run.
- **Purpose limitation** (Art. 5(1)(b)): Data is used only for the job-search purpose described to the user.
- **Data minimisation** (Art. 5(1)(c)): The profile fields are the minimum needed for persona-aware ranking; optional fields are clearly marked.
- **Accuracy** (Art. 5(1)(d)): User can edit any field at any time.
- **Storage limitation** (Art. 5(1)(e)): 180-day default retention + Art. 17 right of erasure.
- **Integrity and confidentiality** (Art. 5(1)(f)): AEAD encryption at rest for CV text + audit-log HMAC chain.
- **Accountability** (Art. 5(2)): This DPIA + the deployer-side `deployer-operating-manual.md` + the audit-log infrastructure.

---

## 2. Assessment of necessity and proportionality

### 2.1 Lawful basis

| Deployer type | Lawful basis | Notes |
|---|---|---|
| Public authority (Jobcenter, MBE, BAMF-coordinated NGO) | Art. 6(1)(e) — public interest task | The cost-saving doctrine establishes the necessity for the public-interest task |
| NGO non-public-authority | Art. 6(1)(f) — legitimate interest balanced | Document the LIA (legitimate interest assessment) per Article 6(1)(f) — template at `dpa-template.md` Annex IV |
| Self-hoster (individual) | Art. 6(1)(b) — performance of contract OR Art. 6(1)(a) — consent | The user is the controller for their own self-host; the user-as-data-subject overlap collapses the lawful-basis analysis |

### 2.2 Necessity test

Can the purpose be achieved with less data? Analysis per processing operation:

| Processing | Necessity? | Alternative considered |
|---|---|---|
| Profile fields | Yes — needed for persona-aware ranking | A profile-less mode exists but degrades the journey-friction-class lens (the design forcing function) |
| CV text (full) | Yes — needed for tailored CV editing + cover-letter drafting | A skills-only mode exists (manual entry, no free text) |
| Audit log | Yes — AI Act Article 12 mandatory | n/a |
| AI call logging | Yes — Article 22 right-to-human-review + Article 26(6) deployer obligation | n/a |
| Cross-session memory | Optional — opt-out via `/forget`-class chat verbs | "Cross-session memory" deferred to a post-grant release |

---

## 3. Risks to the rights and freedoms of natural persons

| Risk | Likelihood | Severity | Score (L×S, max 25) | Mitigation |
|---|---|---|---|---|
| Unauthorised access to CV text (data breach) | Low (2) | High (4) | 8 | ChaCha20-Poly1305 AEAD at rest; key in env var; no plaintext on disk; per-deployment HMAC-salted user IDs in audit log |
| AI provider exfiltrates data sent for fit-scoring | Medium (3) — BYO-AI providers are third parties | Medium (3) | 9 | BYO-AI architecture means the deployer chooses; manual + Ollama paths require zero data egress; `transparency-notice.md` lists each provider's data-flow disclosure |
| Bias-against-friction-class user produces harmful AI output | Medium (3) | High (4) | 12 | `accuracy-and-bias-testing.md` methodology + the 10-vector prompt-injection guard (`prompt-injection-testing.md`) + Article 22 right-to-human-review surface (`deployer-operating-manual.md` §8.1) |
| User cannot exercise Art. 15/16/17/20 rights | Low (2) | Medium (3) | 6 | `/api/data/export` (Art. 20), `/api/account/deletion-request` (Art. 17), `/api/profile` POST (Art. 16); validated end-to-end in `compliance/article-20-export-proof.md` |
| Audit-log key compromise enables linkage attack | Low (1) | High (4) | 4 | Key rotation playbook at `compliance/audit-log-key-rotation.md` + annual schedule + 6 incident-triggered rotation classes |
| Stale CV data persists beyond retention | Low (2) | Low (2) | 4 | Default 180-day retention; deployer-configurable; explicit `/api/account/deletion-request` |
| Migrant-status field discloses asylum stage to a non-EU AI provider | Medium (3) | High (5) — could affect asylum proceedings | 15 — **CRITICAL** | (a) `transparency-notice.md` warns user at the residency-status field; (b) deployer's BYO-AI choice can be restricted to EU-hosted Ollama; (c) deployer can disable the residency-status field via env-var override (a post-grant enhancement) |
| Deployer's operator account becomes admin-only without redundancy | Low (1) | High (4) | 4 | The role system supports multiple admins per workspace; deployer's onboarding flow recommends ≥2 admins |
| AI hallucination causes user to pursue wrong-fit role | Medium (3) | Medium (3) | 9 | Per-criterion scoring + the score-clamp parser layer + the "AI outputs are suggestions, not decisions" framing in `transparency-notice.md` §"Limitations" |

**Highest residual risks** (≥ 12 after mitigation): bias-against-friction-class (12), migrant-status-disclosure-to-non-EU-AI (15). Both are addressed in compensating layers; both are explicitly disclosed to the user; both require deployer-side ongoing monitoring (the quarterly bias-test re-run + the BYO-AI provider review).

---

## 4. Measures to mitigate the risks

### 4.1 Technical measures

- **Encryption at rest**: ChaCha20-Poly1305 AEAD for CV text + profile-section bodies. Key in env var, never logged.
- **HMAC-chained audit log**: Per-deployment salt; key-rotation playbook documents the lifecycle.
- **Per-call cost cap**: `cost_cap_context_for` chokepoint; prevents runaway AI spend that could indicate a compromise.
- **Per-user quota**: 50 scans / 50 AI calls / 3 active scans per day default; quota-breach alerts the operator.
- **Score-clamp parser layer**: `parse_auto_fit_output` clamps AI scores to [0, 1]; out-of-range AI output surfaces as "no score" rather than a misleading value.
- **Prompt-injection defence**: 10-vector structural-defence test at `tests/test_prompt_injection_vectors.py`; pinned at parse-layer not AI-compliance-layer.
- **Kill switch**: `HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true` disables every AI code path; deployer reaches for this on any AI-class incident.
- **TLS in transit**: Caddy auto-issues Let's Encrypt certificates; HSTS preload-ready.
- **CSP + CORS**: `script-src 'self'` + restrictive CORS prevent client-side data exfiltration via injection.

### 4.2 Organisational measures

- **Named oversight person**: `human-oversight-guide.md` §"Appointment record" — deployer fills in.
- **Article 22 / Article 86 procedure**: `deployer-operating-manual.md` §8.1 — 8-step operational workflow for user appeals to human review.
- **DPA per processor**: `dpa-template.md` is the template; deployer signs per BYO-AI provider, per backup-storage provider, per any third-party processor.
- **Annual bias-test re-run**: `accuracy-and-bias-testing.md` §3 — operator-side procedure.
- **Quarterly key rotation drill**: `audit-log-key-rotation.md` §3 — scheduled cadence.
- **Incident-response runbook**: `deployer-operating-manual.md` §10 — 5-step incident workflow; quarterly drill recommended.
- **User transparency**: `transparency-notice.md` is shown at first run + linked from every AI-output surface.

### 4.3 Compensating controls for the highest-residual risks

**Bias-against-friction-class (residual 12)**:
- The seven-persona panel in `company_discovery/persona_fixtures.py` is the bias-test cohort; results are recorded in `docs/grant/bias-comparative-report-*.md`.
- The Article 22 right-to-human-review (`deployer-operating-manual.md` §8.1) gives the affected user a structured appeal path with a 1-month SLA.
- The deployer's quarterly bias re-run (Section 4.2) catches drift over time.

**Migrant-status disclosure to non-EU AI provider (residual 15)**:
- The residency-status field carries an explicit warning in the SPA UI before entry.
- The deployer can restrict BYO-AI providers to EU-hosted options (Ollama at the deployer's own EU datacentre; future EU-only managed options).
- The `transparency-notice.md` `[Deployer-managed addendum]` slot is where the deployer specifies which provider(s) the user's data may reach.
- A future enhancement (a post-grant Article 22 in-app surface) will let the user toggle "do NOT send my residency-status field to AI" — currently this is an all-or-nothing AI-disable choice.

---

## 5. Consultation

### 5.1 Data subject consultation

The seven-persona panel is the project-level proxy for data-subject consultation: each persona's friction context is documented in `docs/grant/07-personas.md` and validated via the dated journey-walks at `docs/grant/journey-walks-2026-05-20/`. The maintainer recruits external readers per `docs/grant/external-reader-recruit-message-2026-05-19.md` for substantive feedback before public launch.

The institutional deployer SHOULD also conduct local data-subject consultation (e.g., via the deployer's existing client-feedback mechanism) before going live in their specific context.

### 5.2 Data Protection Officer

For the project-side reference: the maintainer (sole maintainer pre-Conservancy-admission) is the de facto DPO for the project's own self-host. The maintainer is contactable at the email in `SECURITY.md`.

For the institutional deployer: their organisational DPO is the named owner of the deployer-side DPIA. The DPO signs off on the deployer-instantiated version of this template before the deployer goes live.

### 5.3 Supervisory authority

This DPIA is the project-side reference. The institutional deployer's supervisory authority is the German Landesdatenschutzbeauftragte for the state where they operate (or the Bundesbeauftragte für den Datenschutz und die Informationsfreiheit for federal-level deployers). The deployer-side DPIA is lodged with their supervisory authority per Article 36 GDPR if residual risk remains high.

---

## 6. Maintenance + review

| Trigger | Action |
|---|---|
| Major release (v0.X+1.0) | Re-run the assessment; append a new dated row to §7 |
| New processing operation introduced | Re-assess the affected risk row; append a new dated row |
| Bias re-test reveals new failure class | Re-assess the bias-against-friction-class row; record the new residual score |
| AI provider added to the catalogue | Re-assess the migrant-status-disclosure row; document the deployer-side mitigation |
| Supervisory-authority guidance changes | Re-read this DPIA against the new guidance; document any gap |
| Annual cadence | Even if nothing else triggers, the deployer's DPO re-reads this DPIA every 12 months |

---

## 7. Append log

| Date | Trigger | Assessor | Highest residual risk | Notes |
|---|---|---|---|---|
| 2026-05-24 | Initial DPIA | Maintainer (project-side reference) | 15 (migrant-status disclosure to non-EU AI provider) | First substantive version; replaces the prior "template-only" state. Deployer-side instantiation is the next step at each institutional adoption. |

Future assessments append below this row. Never overwrite a prior row; the audit trail is part of the deployer's accountability evidence under Art. 5(2).

---

## Cross-references

- AI Act Article 27 FRIA template: [`fundamental-rights-impact-assessment-template.md`](fundamental-rights-impact-assessment-template.md)
- Deployer operating manual: [`deployer-operating-manual.md`](deployer-operating-manual.md)
- Audit log schema: [`audit-log-schema.md`](audit-log-schema.md)
- Audit log key rotation: [`audit-log-key-rotation.md`](audit-log-key-rotation.md)
- Accuracy + bias methodology: [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md)
- Prompt-injection methodology: [`prompt-injection-testing.md`](prompt-injection-testing.md)
- Article 20 export proof: [`article-20-export-proof.md`](article-20-export-proof.md)
- Transparency notice: [`transparency-notice.md`](transparency-notice.md)
- DPA template: [`dpa-template.md`](dpa-template.md)
- EU AI database registration template: [`eu-database-registration-template.md`](eu-database-registration-template.md)
- Compliance INDEX: [`INDEX.md`](INDEX.md)
