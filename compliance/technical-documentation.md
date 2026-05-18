<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Technical Documentation (Article 11 + Annex IV)

**Audience**: provider, deployer, supervisory authority, and notified body if conformity assessment is sought under Article 43.
**Article**: AI Act Article 11 and Annex IV (technical documentation).
**Status**: living document. Updated on every major release.

---

## How to read this document

Article 11 of [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) requires the **provider** of a high-risk AI system to maintain comprehensive technical documentation in the structure of Annex IV. This document is organised in the nine sections of Annex IV in order. The section numbers below match Annex IV section numbers.

References to specific files in the codebase are stable across releases; if a referenced file is renamed, this document is updated in the same commit.

---

## 1. General description of the AI system

### 1.1 Intended purpose

DirectJob Scout is a conversational copilot that helps users navigate the European job market with attention to the bureaucratic-navigation friction structurally present for users facing language-fluency gaps, foreign-credential opacity, work-rights complexity, career transitions, and re-entry after extended absence. The first reference deployment targets Germany; the architecture is country-neutral.

The system performs the following AI-assisted functions, each of which is an Annex III §4 activity:

- **Job-to-CV fit scoring** ("filter job applications") — given a discovered job and a user's CV, compute a fit score with per-criterion breakdown.
- **Recommendation of recognition-friendly employers** ("place targeted job advertisements") — rank discovered jobs for the user, weighted by the user's situation (Anerkennung status, language level, persona-friendly employer cohort).
- **CV tailoring per role** — propose edits to the user's CV to better surface relevant experience for a specific role.
- **Motivation-letter drafting** — propose a first-draft motivation letter grounded in user-confirmed CV facts and the role's description.
- **Application-outcome analysis** — surface patterns across the user's application history (which CV variants get replies, which sectors are responding).

The system does **not** perform automated decisions affecting the terms of work-related relationships. Every consequential action (sending an application, accepting an offer) requires explicit user confirmation per Article 14 (human oversight).

### 1.2 Persons or groups of persons on whom the system is intended to be used

Per Decision 21 in [`../docs/grant/04-research-and-decisions.md`](../docs/grant/04-research-and-decisions.md), the intended end-users are anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work. The persona panel anchoring the design covers seven situations:

- Most-acute migrant subset: Aïcha (Tunisia → Berlin, nursing/Anerkennung), Yusuf (Turkey → Munich, engineering/Blue Card), Olga (Ukraine → Leipzig, tech/§24), Mahmoud (Syria → Hamburg, trades/subsidiary protection), Maria (Romania → Stuttgart, care/EU-citizen-with-language-barrier).
- Wider friction class: Käthe (Germany, nursing re-entrant after caregiving), Tobias (Germany, commercial→civic-tech career change).

Full profiles at [`../docs/grant/07-personas.md`](../docs/grant/07-personas.md).

The intended deployer-users are: civic-employment institutions (Migrationsberatungsstellen, IQ-Netzwerk regional offices, Optionskommune Jobcenter, university career services), individual self-hosters, and NGOs operating in the civic-employment space.

### 1.3 Form in which the AI system is placed on the market

The system is distributed as **open-source software under Apache 2.0** (with a Contributor License Agreement; see [`../cla.md`](../cla.md)). Distribution channels:

- **Primary**: public Git repository at `https://github.com/maksodf/directjob-scout` (mirrored to Codeberg for European-sovereignty resilience starting Phase 2).
- **Deployment artefacts**: Dockerfile, `docker-compose.prod.yml`, Caddy HTTPS configuration, backup/restore scripts. Nix flake for reproducible builds lands Week 3.
- **MCP server**: stdio-spawned subprocess; composable with other open civic agents over JSON-RPC.

No hosted SaaS distribution is operated by the provider. A future hosted-support offering is anticipated post-Phase-1 (see [`../docs/grant/03-post-grant.md`](../docs/grant/03-post-grant.md)) but is not part of the provider's current obligations.

### 1.4 Computing infrastructure

The system runs on commodity hardware: a single VM with 2 vCPU and 4 GiB RAM is sufficient for a Beratungsstelle-scale deployment. AI inference is delegated to a third-party provider chosen by the user (or by the deployer in an institutional configuration), via the BYO-AI abstraction at [`../company_discovery/ai_providers.py`](../company_discovery/ai_providers.py). Supported providers: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama (fully offline), manual handoff, Claude Code.

### 1.5 Description of the user interface

Two surfaces:

- **Web app** ([`../app.py`](../app.py)): browser-facing chat UI with a 12-phase journey state machine. Mobile-responsive. EN and DE i18n with locale-aware parsing.
- **MCP server** ([`../mcp_server.py`](../mcp_server.py) + [`../company_discovery/mcp_tools.py`](../company_discovery/mcp_tools.py)): JSON-RPC over stdio. 13 tools published with JSON Schema for inputs and outputs. Public catalogue documented at [`../docs/mcp-server.md`](../docs/mcp-server.md).

---

## 2. Detailed description of the elements of the AI system and the development process

### 2.1 Methods and steps in development

The project is a single-maintainer codebase with a co-maintainer being formalised (see Decision 17). Development follows:

- **Conventional Git workflow**: feature branches → PRs → reviewed merge to `claude/project-analysis-bpHCo` (the active working branch during the grant sprint) or `main`.
- **Test-driven development** where applicable: 994+ tests across 76+ test files; full suite runs in ~20 s on bare host.
- **CI**: GitHub Actions matrix on Python 3.11 + 3.12; MCP integration test workflow at [`.github/workflows/mcp-integration.yml`](../.github/workflows/mcp-integration.yml).
- **Linting and security**: planned Week 3 (CI expansion in `02-execution-plan.md` §3.2): ruff, mypy, pip-audit, codespell.
- **Documentation co-evolves**: every architectural change updates [`../ARCHITECTURE.md`](../ARCHITECTURE.md); every standards-relevant change updates [`../STANDARDS.md`](../STANDARDS.md); every AI-Act-relevant change updates this compliance pack.

### 2.2 Design specifications

The architectural choices are documented in [`../docs/grant/01-project-brief.md`](../docs/grant/01-project-brief.md) §8 and rendered visually in [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Key choices:

- **Structured journey state machine**: every AI invocation is gated to a phase ([`../company_discovery/journey.py`](../company_discovery/journey.py)).
- **BYO-AI provider abstraction**: pluggable AI provider; no vendor lock-in ([`../company_discovery/ai_providers.py`](../company_discovery/ai_providers.py)).
- **MCP composition surface**: civic-agent interoperability via Model Context Protocol ([`../company_discovery/mcp_tools.py`](../company_discovery/mcp_tools.py)).
- **Encryption-at-rest**: ChaCha20-Poly1305 AEAD for profile-at-rest ([`../company_discovery/crypto_kit.py`](../company_discovery/crypto_kit.py)).
- **Audit log**: structured JSONL emitter for all AI invocations and MCP tool calls ([`../company_discovery/audit_log.py`](../company_discovery/audit_log.py)).

### 2.3 System architecture

See [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for the full Mermaid diagram and component map. Summary layers:

| Layer | Components | Files |
|---|---|---|
| Entry surfaces | Web app, MCP server | `app.py`, `mcp_server.py` |
| Application logic | Chat router, journey state machine, persona ranking | `company_discovery/chat_router.py`, `journey.py`, `persona_ranking.py` |
| Domain services | Aggregators, AI providers, analysis, CV builder, motivation letter | `company_discovery/aggregators.py`, `ai_providers.py`, `analysis.py`, `cv_builder.py`, `motivation_letter.py` |
| Persistence + crypto | Local DB, AEAD profile-at-rest | `company_discovery/persistence.py`, `crypto_kit.py` |
| Cross-cutting | Audit log, locale parser, i18n | `company_discovery/audit_log.py`, `locale_parser.py`, `static/i18n/` |
| External | Job-board APIs, AI provider APIs, MCP-composing civic agents | (third-party) |

### 2.4 Algorithm specification

The fit-scoring algorithm is the only AI-driven scoring component. It is composed of:

1. **Rule-based pre-filter**: ESCO occupation-code match (binary), location-fit (binary), work-rights-fit (binary). Excludes jobs that fail any hard criterion.
2. **Structured criterion scoring**: per-criterion numerical scores (0–100) for skill-overlap, seniority-overlap, language-fit, recognition-fit, sector-shortage-fit. Each criterion has a published rule (e.g., language-fit is `min(role_language_required, user_language_actual) * 100`).
3. **AI re-ranking**: the structured-criterion scores are passed to the AI provider as context alongside the job and CV slice; the AI returns a re-ranking rationale and a possible adjustment factor (bounded to ±15% of the structured score).
4. **User-visible breakdown**: the per-criterion scores plus the AI rationale are displayed; the user can dispute or override.

The bounded-adjustment design means the AI cannot fundamentally override the structured scoring; it can only re-rank within a documented tolerance. This is a deliberate constraint to keep the system interpretable for Article 14 oversight purposes.

### 2.5 Validation and testing

See [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md) for the validation methodology and current results. Summary: persona-anchored testing across all seven personas, per-call comparison against documented expectations, bias detection by cross-persona divergence.

### 2.6 Cybersecurity controls

See [`../SECURITY.md`](../SECURITY.md) for the project's security policy. Key controls:

- Encryption-at-rest (ChaCha20-Poly1305 AEAD) for profile data and TOTP secrets
- TLS (Caddy auto-managed certificates) for all production traffic
- Session management with idle timeout and explicit logout
- Two-factor authentication (TOTP) for admin and optional for users
- Vulnerability disclosure via `.well-known/security.txt` per [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)
- Dependency scanning via pip-audit (CI expansion in Week 3)

---

## 3. Detailed information about the monitoring, functioning, and control of the AI system

### 3.1 Capabilities and limitations

**Capabilities**:

- Fit-scoring with per-criterion breakdown
- CV tailoring per role
- Motivation-letter drafting
- Application-outcome analysis
- Persona-aware role recommendation
- Multi-language operation (EN + DE; Arabic / Ukrainian / Turkish / Romanian on roadmap)
- MCP composition with other open civic agents

**Limitations** (disclosed in transparency notice):

- AI outputs are suggestions, not decisions. The user always confirms before any consequential action.
- Foreign-credential recognition (Anerkennung) is a structural bureaucratic process the system cannot expedite — it can only help the user navigate it.
- The system does not have access to closed-employer ATS data; matching is against publicly-discoverable job postings and bookmarklet-captured ones.
- AI-provider model quality varies; offline-only (Ollama) operation produces lower-quality fit scoring than commercial providers, with the trade-off documented in the transparency notice.

### 3.2 Performance metrics

See [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md) §"Metrics".

### 3.3 Foreseeable misuse

- **Auto-application spam**: out of scope by design; the journey state machine does not permit auto-submission.
- **Employer impersonation**: a malicious deployer could in principle present an internal-recruiter-facing surface as a user-facing one. Mitigation: the deployer accountability split (Article 26 obligations), the transparency-notice requirement, and the audit-log surface that lets users detect anomalous behaviour.
- **Bias amplification via prompt tuning**: a deployer could in principle tune prompts to introduce bias. Mitigation: prompt-template ID logging in the audit log surfaces tuning changes; the bias-testing methodology re-runs at deployment.

### 3.4 Human oversight

See [`human-oversight-guide.md`](human-oversight-guide.md) for the full guide. Summary:

- Default-off advisor-review mode (config flag `DIRECTJOB_HUMAN_OVERSIGHT_MODE`)
- When enabled, AI outputs queue for advisor review at `/api/admin/oversight/queue`
- Kill-switch: any deployer can disable AI features and fall back to deterministic templates
- No auto-decision paths in the codebase

---

## 4. Description of the appropriateness of the performance metrics for the specific AI system

The performance metrics for fit-scoring are anchored to the persona panel rather than to a generic labour-market test set. The rationale: a generic test set (e.g., comparing scoring against random pairs of CVs and job postings) would not surface the friction-class biases the system is most likely to introduce. Persona-anchored testing forces the bias-detection question into the open: does Aïcha's Tunisian-trained nursing experience score equivalently to a German-trained nurse with the same ESCO skills?

The persona panel covers the seven situations the project's design is anchored on; the metrics test what the system actually does, not what a labour-market-economics benchmark would test.

---

## 5. Detailed description of the risk management system

See [`risk-management-plan.md`](risk-management-plan.md).

---

## 6. Description of any change made to the system through its lifecycle

The Git history of the public repository is the canonical change record. Substantive changes:

- New tools added to the MCP catalogue: append a row to the catalogue table in [`../docs/mcp-server.md`](../docs/mcp-server.md), with the change visible in the catalogue version bump.
- New AI invocation surfaces: documented in §1.1 of this file and in [`../company_discovery/analysis.py`](../company_discovery/analysis.py).
- Compliance-relevant changes: appended to the change log of the relevant compliance file.

Release tagging follows semantic versioning. The first public release is `v0.1.0` (target: Week 4 of the grant sprint).

---

## 7. List of harmonised standards applied

| Standard | Where applied |
|---|---|
| ISO/IEC 27001 (information security) | Referenced for general security posture; no formal certification |
| ISO/IEC 23894 (AI risk management) | **Pending**: not yet ratified at the time of this document. Will be aligned and cited when ratified. |
| ISO 8601 (date/time) | All timestamps in the audit log and tool outputs |
| ISO 639-1 (language codes) | i18n language selection (`en`, `de`, future Arabic/Ukrainian/Turkish/Romanian) |
| ISO 3166-1 alpha-2 (country codes) | Persona, role, and EURES export fields |
| schema.org JobPosting | Canonical structure for job records |
| ESCO (Skills, Competences, Qualifications, Occupations) | Occupation and skill taxonomy; ISCO-based |
| EURES schema | Cross-EU job-data interoperability |
| JSON Schema (Draft 2020-12 in tool registry; Draft 7 in catalogue export per `02-execution-plan.md` §2.6) | MCP tool input/output schemas |
| Model Context Protocol (MCP, version `2024-11-05`) | Composition surface |
| RFC 7807 (Problem Details for HTTP APIs) | Error payload format |
| RFC 9116 (`.well-known/security.txt`) | Vulnerability disclosure |
| WCAG 2.2 AA | Accessibility target — audit in Week 3 (`02-execution-plan.md` §3.6) |

Full list and rationale: [`../STANDARDS.md`](../STANDARDS.md).

---

## 8. Copy of the EU declaration of conformity

The EU declaration of conformity (Article 47 + Annex V) is a **deployer-completed** document, not a provider-issued one, because conformity is established in the deployment context. We provide a template that the deployer pre-fills as part of `eu-database-registration-template.md`. The provider commits to maintaining the technical documentation in this directory as the substrate the deployer's declaration relies on.

---

## 9. Detailed description of the system in place to evaluate the AI system performance in the post-market phase (post-market monitoring plan per Article 72)

Article 72 of the AI Act requires a documented post-market monitoring plan. Our plan:

### 9.1 Active monitoring

- **Audit log**: every AI invocation, MCP tool call, and persistence-confirmation event is logged in JSONL format with a stable schema (see [`audit-log-schema.md`](audit-log-schema.md)). Deployers retain logs per their retention policy (default 6 months).
- **Bias-testing methodology re-run**: deployers are expected to re-run the bias-testing methodology against their chosen AI provider at deployment, on every AI-provider switch, and at least every 12 months.
- **Pilot-deployment feedback**: Week-3 partner-NGO pilots collect structured feedback on output quality and bias; results feed `accuracy-and-bias-testing.md`.

### 9.2 Passive monitoring

- **GitHub Issues** tagged `incident-ai-act` and `bias-report` are monitored continuously by the provider.
- **SECURITY.md** disclosure channel is monitored continuously.
- **The European AI Office publication feed** is monitored quarterly for relevant guidance.

### 9.3 Response to issues

- **Triage**: 5 working days for acknowledgement.
- **Sev-1 (ongoing fundamental-rights breach)**: notify all known deployers within 48 h.
- **Sev-2 (pattern bias affecting a documented persona class)**: notify within 5 working days; remediation in next major release.
- **Sev-3 (single-event misfire)**: documented; remediation as part of regular release cycle.
- **Sev-4 (documentation gap)**: documented; resolved in next compliance-pack review.

### 9.4 Reporting to authorities

Where an incident requires notification under Article 73, the deployer notifies their supervisory authority. The provider supports the deployer with the technical details (audit-log extract, prompt-template diff, persona-cohort impact analysis) on request.

---

## Append log

- **2026-05-18**: initial technical documentation drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Next major release scheduled v0.1.0 in Week 4.
