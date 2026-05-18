<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Fundamental Rights Impact Assessment (FRIA) Template

**Audience**: **public-authority deployers**. Article 27 requires a FRIA before the system is placed into service or used by a deployer that is a body, office, or agency governed by public law, or a private entity providing public services.
**Article**: AI Act Article 27 (fundamental rights impact assessment for high-risk AI).
**Status**: living template. Updated when the European AI Office publishes refinements to the FRIA methodology.

---

## What this is

A FRIA is a structured assessment of how a high-risk AI system may affect the fundamental rights of the natural persons it serves, before the system is put into operational use. The assessment surfaces foreseeable risks to fundamental rights, the mitigation measures in place, the governance arrangements supporting oversight, and the remediation channels available to affected users.

This template is **pre-filled** at the provider level with the architectural mitigations the project has designed in. The deployer completes the deployment-specific sections (your specific affected population, your specific governance context, your specific remediation channels) and lodges the completed FRIA with the relevant supervisory authority per Article 27.

---

## Part 1 — Identification

### 1.1 Deployer

`[TBD: deployer to fill — organisation name, legal status (e.g., Optionskommune Jobcenter, Migrationsberatungsstelle operated by Caritas, university career service at <Hochschule>), contact information for the FRIA process owner]`

### 1.2 AI system

| Field | Value |
|---|---|
| AI system name | DirectJob Scout |
| Version | `[TBD: deployer to fill — e.g., v0.1.0]` |
| Provider | The Commons Conservancy, hosting the DirectJob Scout Programme |
| Repository | `https://github.com/maksodf/directjob-scout` |
| Annex III classification | §4(a) and §4(b) — recruitment / selection support |

### 1.3 Intended use in this deployment

`[TBD: deployer to fill — a paragraph describing how the system will be used in this specific deployment context: which advisor workflows it augments, which user populations it serves, which integrations are activated, which AI provider is configured.]`

### 1.4 Period covered by this assessment

`[TBD: deployer to fill — typically the first 12 months of deployment, with a scheduled review at the end of the period.]`

---

## Part 2 — Affected population

This section uses the friction-class framing established in Decision 21 of the project's planning workspace ([`../docs/grant/04-research-and-decisions.md`](../docs/grant/04-research-and-decisions.md)).

### 2.1 General description

The DirectJob Scout architecture serves **anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work**. The architecture is friction-driven, not demographic-driven.

Migrants and EU-mobile workers face this friction most acutely — language barriers, foreign-credential opacity through Anerkennung, residency-status complexities, bureaucratic fragmentation — and they are the most-acute use case the design is anchored on. The same structural friction also affects: career changers, workers returning after caregiving or extended absence, the long-term unemployed re-entering the system, returning expats, older workers facing implicit-bias filtering, and first-generation graduates without family-networked guidance.

### 2.2 Specific affected population in this deployment

`[TBD: deployer to fill — a specific description of the affected population in this deployment, with realistic demographic and friction-class composition. Examples by deployer type:`

- *Migrationsberatungsstelle*: ~95% migrant clients (with the full range of residency statuses); ~5% non-migrant family members or partners using the service in conjunction with primary clients.
- *Optionskommune Jobcenter*: all Bürgergeld recipients in the catchment; migrant proportion varies by region (typically 25–40%); the rest are non-migrant Bürgergeld recipients with diverse friction patterns (returning to work after caregiving, long-term unemployment, sector pivots after layoffs, etc.).
- *University career service*: international graduates (the migrant-graduate subset of the affected population), first-generation domestic graduates, and career changers among alumni — all three friction-class subgroups are represented.
- *NGO operating in Wiedereinstieg / return-to-work programmes*: typically German-native women returning to clinical professions or technical professions after extended caregiving leave; the wider-friction-class personas (Käthe) anchor this case.
- *NGO operating in civic-tech career-change support*: typically commercial-tech professionals (German-native or migrant) pivoting to public-sector or NGO digital roles; Tobias anchors this case for the wider-friction-class subset; Olga anchors the migrant subset.

`The deployer specifies the actual composition with reference to documented caseload demographics, not speculation.]`

### 2.3 Vulnerability assessment within the affected population

Certain subgroups within the affected population may experience elevated fundamental-rights risk:

- **Users with limited host-language fluency** — risk that language-based filtering excludes them from legitimate opportunities. Mitigated by per-criterion language-fit scoring and team-language-aware matching (see [`risk-management-plan.md`](risk-management-plan.md) R2).
- **Users with foreign credentials in process of recognition (Anerkennung)** — risk that fit-scoring under-weights their credentials. Mitigated by ESCO mapping and the recognition-friendly-employer cohort (see R3).
- **Users in regulated professions (healthcare, education, legal)** — risk that profession-specific licensure friction is not surfaced. Mitigated by persona-aware messaging.
- **Users with limited digital literacy** — risk that the conversational interface is itself a barrier. Mitigated by the deterministic-template fallback, the option of advisor-assisted use, and locale-aware parsing of yes/no synonyms.
- **Users in protected residency categories (refugees, subsidiary protection, temporary protection)** — risk that the residency-status field is mishandled. Mitigated by treating the field as informational metadata; no fit-scoring criterion uses residency-status as a hard filter on jobs the user is legally permitted to apply for.

`[TBD: deployer to specify which of these vulnerability factors are present in their caseload and add any additional ones specific to their context.]`

---

## Part 3 — Identification of fundamental rights at stake

The following Charter of Fundamental Rights of the European Union (CFR) articles are most relevant to a high-risk-AI employment system. The deployer reviews each and notes the deployment-specific assessment.

| CFR Article | Right | Relevance to deployment | Provider-level mitigation |
|---|---|---|---|
| Art. 1 | Human dignity | Outputs respectful of user; no dehumanising labels | Persona-aware messaging; no demographic-label filtering |
| Art. 7 | Respect for private and family life | Encryption-at-rest, data minimisation, audit log | ChaCha20-Poly1305 AEAD; prompt minimisation per data-governance.md §4 |
| Art. 8 | Protection of personal data | GDPR-aligned; user-sovereign data; AI-provider choice | BYO-AI; Ollama for offline-only; per-user opaque IDs |
| Art. 10 | Freedom of thought, conscience and religion | No employment recommendation based on protected belief | No protected-attribute field in user profile schema |
| Art. 15 | Freedom to choose an occupation and right to engage in work | Tool **supports** this right by reducing friction | Persona panel; recognition-friendly matching; multilingual |
| Art. 21 | Non-discrimination | Risk of algorithmic discrimination — central concern | Bias-testing methodology; per-criterion scoring; tolerance bands |
| Art. 22 | Cultural, religious and linguistic diversity | Multilingual; locale-aware; persona-anchored | EN+DE shipped; Arabic/Ukrainian/Turkish/Romanian roadmap |
| Art. 26 | Integration of persons with disabilities | Accessibility scope; alternative input paths | WCAG 2.2 AA target; advisor-handoff path |
| Art. 31 | Fair and just working conditions | Tool supports access; does not affect terms unilaterally | No automated decisions; user confirmation gates |
| Art. 38 | Consumer protection | Tool is free; no consumer-protection issues at user level | Open-source; no commercial gate |
| Art. 41 | Right to good administration | Right to explanation in public-authority context | Per-criterion fit-score breakdown; `/api/jobs/{id}/explain` |
| Art. 47 | Right to an effective remedy and to a fair trial | Remediation channels documented | Complaint channels via deployer + supervisory authority |

`[TBD: deployer reviews each CFR article and adds context-specific notes where relevant. If a CFR article is not relevant to this deployment, note "Not applicable" with brief rationale.]`

---

## Part 4 — Risks and mitigations

This section maps the project-level risks (from [`risk-management-plan.md`](risk-management-plan.md)) to the deployment context.

| Risk ID | Description | Pre-mitigation rating | Provider-level mitigation | Deployer-level additional measures | Residual rating |
|---|---|---|---|---|---|
| R1 | Discrimination in fit scoring | H×H | Persona-anchored bias testing; per-criterion scoring; ESCO mapping; bounded ±15% AI re-ranking | `[TBD: deployer to specify additional measures: re-test cadence, advisor-review mode for high-risk subgroups, specific oversight signals]` | M×M |
| R2 | Language-based filtering | H×H | Independent role-language and user-language fields; team-language-aware matching | `[TBD: deployer to specify any language-specific advisor training or override]` | L×M |
| R3 | Foreign-credential bias | H×H | ESCO mapping; recognition-friendly employer cohort; no auto-rejection | `[TBD: deployer to specify partnership with Anerkennungsstellen or referral channels]` | M×M |
| R4 | Scoring opacity | M×H | Per-criterion breakdown; explanation endpoint; transparency notice | `[TBD: deployer to specify advisor protocol for handling explanation requests]` | L×M |
| R5 | Automation of consequential decisions | L×H | Journey-state-machine confirmation gates; no auto-submit code path; kill-switch | `[TBD: deployer to confirm no override of the structural gates]` | VL×M |
| R6 | Data-egress beyond consent | H×H | BYO-AI; Ollama option; prompt minimisation; per-AI-call audit log | `[TBD: deployer to specify the AI provider chosen and the consent flow]` | L×M |
| R7 | Compliance-pack misuse as a shield | M×M | Documentation makes accountability split visible | `[TBD: deployer to specify the legal-counsel review of this FRIA]` | L×L |
| R8 | Drift as standards evolve | H×M | Quarterly provider review; release-tagged compliance pack | `[TBD: deployer to specify their tracking cadence for European AI Office publications]` | M×L |

---

## Part 5 — Human oversight

`[TBD: deployer fills in this section by reference to `human-oversight-guide.md` §1 (appointment record) and §2 (mode chosen).]`

- Oversight person appointed: `[TBD]`
- Mode chosen for initial deployment (Mode A passive monitoring / Mode B advisor-review queue): `[TBD]`
- Reason for the chosen mode: `[TBD]`
- Schedule for review and possible mode adjustment: `[TBD]`
- Kill-switch activation policy: `[TBD]`

---

## Part 6 — Remediation channels

A user who believes their fundamental rights have been affected by a DirectJob Scout output in this deployment can use the following remediation channels:

| Channel | Description |
|---|---|
| In-application | The Settings screen's "Request explanation" and "Report a concern" buttons (Article 86 right to an explanation) |
| Deployer | Direct contact with the deployer's appointed contact: `[TBD: deployer to fill]` |
| Deployer's data-protection officer (if applicable) | `[TBD: deployer to fill]` |
| Deployer's complaints procedure | `[TBD: deployer to specify their organisation's existing complaints procedure]` |
| Supervisory authority — data protection | `[TBD: deployer to specify the relevant data-protection authority for their jurisdiction]` |
| Supervisory authority — AI Act | `[TBD: deployer to specify the relevant market-surveillance authority for the AI Act]` |
| Provider | GitHub Issue tagged `incident-ai-act` at `https://github.com/maksodf/directjob-scout/issues`, or via [`../SECURITY.md`](../SECURITY.md) for security-related concerns |

---

## Part 7 — Governance

| Field | Value |
|---|---|
| Date of FRIA completion | `[TBD: deployer to fill]` |
| Author(s) of FRIA | `[TBD: deployer to fill]` |
| Reviewer(s) | `[TBD: deployer to fill — typically the deployer's data-protection officer, legal counsel, and accountable senior individual]` |
| Date of lodging with supervisory authority | `[TBD: deployer to fill]` |
| Scheduled next review date | `[TBD: deployer to fill — typically 12 months from completion, or sooner if substantive deployment changes]` |
| Triggers for unscheduled review | Major version upgrade of DirectJob Scout; change of AI provider; addition of a new user population; any reported incident; any guidance publication from the European AI Office that affects the assessment |

---

## Part 8 — Conclusion

`[TBD: deployer to provide a one-paragraph conclusion summarising whether the residual risks are acceptable for this deployment, what mitigations are in place, and whether any conditions or limitations apply to the deployment going live.]`

Sample conclusion language (deployer adapts):

> *On the basis of the architectural mitigations described in [`risk-management-plan.md`](risk-management-plan.md), the human-oversight setup described in [`human-oversight-guide.md`](human-oversight-guide.md), and the deployer-level additional measures recorded in Part 4 above, the residual fundamental-rights risk of deploying DirectJob Scout at <deployer> for the affected population described in Part 2 is assessed as **acceptable for a controlled initial deployment** in Mode B (advisor-review queue) for the first 90 days, followed by a documented review and possible transition to Mode A (passive monitoring) once a sufficient track record is established. The deployer commits to the monitoring cadence in `human-oversight-guide.md` §4 and to a full FRIA re-review at the 12-month mark.*

---

## Append log

- **2026-05-18**: initial template drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Anchored to friction-class framing per Decision 21.
