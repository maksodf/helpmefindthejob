<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Risk Management Plan

**Audience**: provider (Helpmefindthejob maintainers) and any deployer reviewing the upstream risk posture before deployment.
**Article**: AI Act Article 9 (risk management system).
**Status**: living document. Reviewed every six months, on every major release, and on every reported incident.

---

## 1. Purpose

Article 9 of [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) requires every high-risk AI system to have a documented, continuous risk-management process covering risks to health, safety, and fundamental rights. This plan captures Helpmefindthejob's risk identification, mitigation, residual-risk acknowledgement, review cycle, and incident escalation.

The risks documented here are the risks specific to **a civic-employment AI system that scores job-to-CV fit, drafts motivation letters, and routes users through a 12-phase journey**. Generic AI-safety risks not specific to this domain are referenced where relevant but not enumerated.

---

## 2. Methodology

We use a modified [ISO 31000](https://www.iso.org/iso-31000-risk-management.html)-style approach adapted for high-risk AI:

1. **Identify** the risks: catalogued in §3 below.
2. **Analyse** the likelihood and severity of each risk against the affected users (Article 9(2)(b)).
3. **Evaluate** which risks require mitigation as "reasonably foreseeable" under Article 9(2)(a) vs which are residual risks that can be accepted with disclosure.
4. **Treat** through technical mitigations (architecture and code), procedural mitigations (deployer obligations), and disclosure mitigations (transparency notice; FRIA template).
5. **Monitor** through the audit-log layer (Article 12) and the post-market monitoring plan (Article 72).
6. **Review** every six months, on every major release, and on every reported incident.

Residual risks remain on the register with a stated acceptance rationale.

---

## 3. Identified risks

Each risk is rated **Likelihood** (low / medium / high) × **Severity** (low / medium / high). The residual rating reflects the rating after the listed mitigations are applied. The severity rating reflects the impact on the affected user, not on the project.

### R1. Discrimination in fit scoring

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | High |
| Severity (pre-mitigation) | High |
| Likelihood (residual) | Medium |
| Severity (residual) | Medium |

**Description**: The fit-scoring model (in [`company_discovery/analysis.py`](../company_discovery/analysis.py)) may systematically rank one demographic lower than another for reasons not related to capability — e.g., favouring German-trained nursing credentials over Tunisian-trained credentials with equivalent ESCO mapping, or favouring native-German CV phrasings over learner-German equivalents.

**Mitigation**:
- The persona panel (see [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md)) drives a bias-testing methodology covering the seven personas, with comparable-capability scoring expected within a documented tolerance.
- ESCO mapping is the canonical layer; foreign credentials map to the same ESCO occupation codes as domestic credentials of equivalent scope (e.g., Aïcha's Tunisian nursing experience maps to ISCO 2221 the same as a German Krankenschwester would).
- The fit score is presented to the user with the **per-criterion breakdown**, not as a single opaque number. The user can challenge or override the score.
- The BYO-AI architecture means the deployer can swap providers if a specific provider exhibits unacceptable bias against their caseload demographics.

**Residual risk**: AI provider models may carry training-corpus bias outside our control. We disclose this in the transparency notice and recommend deployers re-run the bias-testing methodology against their chosen AI provider before going live.

### R2. Language-based filtering

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | High |
| Severity (pre-mitigation) | High |
| Likelihood (residual) | Low |
| Severity (residual) | Medium |

**Description**: The system might filter users out of legitimately-accessible roles based on the user's German level alone (e.g., excluding Olga from any tech role because her German is A2, when the actual role is English-speaking-team-led).

**Mitigation**:
- Persona-aware matching: Olga's English-team-friendly preferences are part of her profile, and roles are matched on the team-language criterion, not blanket German requirement.
- The user-language and role-language fields are independent in the data model; the matching algorithm uses both, not one as a proxy for the other.
- The transparency notice discloses how language is used in matching.

**Residual risk**: A minority of roles may have host-language requirements that the matching cannot override (e.g., regulated-profession licensure requirements). These are surfaced to the user with explanation.

### R3. Foreign-credential bias (Anerkennung opacity)

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | High |
| Severity (pre-mitigation) | High |
| Likelihood (residual) | Medium |
| Severity (residual) | Medium |

**Description**: The German Anerkennung (foreign-credential recognition) process is opaque, variable across Bundesländer, and slow. A user with capability equivalent to a domestic worker may be filtered out of roles requiring Anerkennung simply because their recognition letter has not yet landed.

**Mitigation**:
- The system distinguishes between **recognition-friendly employers** (those willing to begin the recognition pipeline before the letter lands — Anerkennung-friendly Pflegedienste, hospitals running formal Wiedereinstieg programmes, Triple Win partner employers) and other employers, and surfaces the friendly-employer subset to users in Anerkennung-in-progress status.
- The ESCO mapping bridges the foreign-credential and German-credential vocabularies, so a Tunisian-trained nurse's CV does not read as "non-equivalent" to a German recruiter.
- We do **not** auto-reject users from any role; we recommend, the user decides.

**Residual risk**: Anerkennung-process opacity is a structural feature of the German labour market that the system cannot resolve unilaterally. The system makes the user's situation legible to recognition-friendly employers; it cannot make non-friendly employers friendly.

### R4. Scoring opacity

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | Medium |
| Severity (pre-mitigation) | High |
| Likelihood (residual) | Low |
| Severity (residual) | Medium |

**Description**: A fit score that the user cannot interpret is a fundamental-rights concern: the user has the right to understand the basis of any individual decision affecting them (Article 86 of the AI Act and Article 22 of GDPR).

**Mitigation**:
- Every fit score is presented with **per-criterion breakdown** — four sub-scores (skills-match, experience/seniority-fit, location+language-fit, friction-fit), each 0–25 and summing to the 0–100 total (`build_auto_fit_prompt` / `parse_auto_fit_output`). Each score carries a one-sentence rationale and a gap list from the model.
- Each fit score is surfaced with a one-line AI rationale and a gap list (`parse_auto_fit_output`). A fuller explanation — including the underlying ESCO mappings — is available from the deployer's oversight person on request (Article 86); a self-service explanation endpoint is a Phase-2 roadmap item.
- The transparency notice tells the user about this right at first run.

**Residual risk**: The underlying AI model's contribution to scoring is partially opaque (it is a learned model). We mitigate by anchoring the user-visible explanation to structured rule-based criteria and using the AI only for re-ranking and free-text rationale generation, not as the score's source of truth.

### R5. Automation of consequential decisions

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | Low |
| Severity (pre-mitigation) | High |
| Likelihood (residual) | Very low |
| Severity (residual) | Medium |

**Description**: A high-risk AI system that auto-submits applications, auto-accepts offers, or auto-makes contractual decisions on the user's behalf is squarely in Annex III §4 territory and creates fundamental-rights risk.

**Mitigation**:
- The system **never** auto-submits an application. Every external action — sending an application to a recruiter, accepting an interview slot, signing an agreement — requires explicit user confirmation, mediated by the 12-phase journey state machine ([`company_discovery/journey.py`](../company_discovery/journey.py)).
- The MCP server's `record_user_outcome` tool requires user-confirmed input and is logged in the audit log.
- The kill-switch (Article 14, see [`human-oversight-guide.md`](human-oversight-guide.md)) lets the deployer disable all app-initiated AI; each AI-assisted feature then falls back to its no-AI path (a deterministic templated skeleton for letter drafting; a BYO-AI handoff prompt for fit-scoring and CV-tailoring).

**Residual risk**: A deployer mis-configuring the system could theoretically introduce auto-submit behaviour. We prevent this by removing the code path entirely; the journey state machine cannot transition to "submitted" without a user-confirmation event in the audit log.

### R6. Data-egress beyond user consent

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | High |
| Severity (pre-mitigation) | High |
| Likelihood (residual) | Low |
| Severity (residual) | Medium |

**Description**: A user's CV, profile, and history are sensitive personal data. Sending them to an external AI provider without consent or without minimisation is both a fundamental-rights risk and a GDPR violation.

**Mitigation**:
- The BYO-AI architecture lets the user (or deployer) choose the AI provider, including fully-offline operation via Ollama. No AI provider is forced.
- Profile data is **encrypted at rest** using ChaCha20-Poly1305 (see [`data-governance.md`](data-governance.md) §3).
- AI invocations send the **minimum prompt necessary** for the requested task — not the full profile. Specifically: fit-scoring sends only the job posting and the relevant CV section, not the full profile; motivation-letter drafting sends only the role description and the user-confirmed CV bullets.
- Every AI invocation is logged in the audit log (Article 12), so the user and deployer have a complete record of what data flowed externally.
- The transparency notice discloses the AI-provider choice and consequences.

**Residual risk**: A user who explicitly opts in to a third-party AI provider accepts that provider's terms. We make this an informed choice via the transparency notice and let the user revoke at any time.

### R7. Misuse of an open-source compliance pack as a compliance shield

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | Medium |
| Severity (pre-mitigation) | Medium |
| Likelihood (residual) | Low |
| Severity (residual) | Low |

**Description**: A deployer might use the existence of this compliance pack as evidence that *their* deployment is compliant, without doing the deployer-side work (FRIA, EU AI database registration, local-context disclosure tailoring).

**Mitigation**:
- Every deployer-facing file (deployer operating manual, FRIA template, EU AI database registration template) is explicit that the deployer is responsible for their deployment context.
- The provider→deployer accountability split is explained in the [README](README.md) "Who this pack is for" section.
- Letters of support from partner deployers are conditional on the partner having reviewed this pack with their counsel.

**Residual risk**: Open-source artefacts can be misused. We disclose, we document, we make the deployer's responsibilities visible; we cannot force compliance.

### R8. Drift away from compliance as standards evolve

| Dimension | Value |
|---|---|
| Likelihood (pre-mitigation) | High |
| Severity (pre-mitigation) | Medium |
| Likelihood (residual) | Medium |
| Severity (residual) | Low |

**Description**: The AI Act is new. The European AI Office continues to publish guidance. ISO/IEC 23894 (AI risk management) has yet to be ratified. The pack as shipped today will partially drift out of date.

**Mitigation**:
- Every-six-months review of the full pack (see §6 below).
- Every-release review against the audit log of changes since the last review.
- ISO/IEC 23894 alignment tracked as an open item; we re-cite when ratified.
- The Phase 2 work plan (see [`../docs/grant/10-ai-act-compliance.md`](../docs/grant/10-ai-act-compliance.md) §"Phase 2 work") includes notified-body engagement and ongoing-guidance tracking.

**Residual risk**: A six-month review cadence is insufficient for a fast-moving guidance environment. We mitigate by tracking the European AI Office's publication feed and adjusting cadence if a high-impact publication lands.

---

## 4. Risk register summary

| ID | Risk | Pre-mit L×S | Post-mit L×S | Owner |
|---|---|---|---|---|
| R1 | Discrimination in fit scoring | H×H | M×M | Provider; Deployer re-tests pre-deployment |
| R2 | Language-based filtering | H×H | L×M | Provider |
| R3 | Foreign-credential bias | H×H | M×M | Provider; Deployer aware |
| R4 | Scoring opacity | M×H | L×M | Provider |
| R5 | Automation of consequential decisions | L×H | VL×M | Provider |
| R6 | Data-egress beyond consent | H×H | L×M | Provider; User informed |
| R7 | Compliance-pack misuse as a shield | M×M | L×L | Provider documents; Deployer accountable |
| R8 | Drift as standards evolve | H×M | M×L | Provider |

---

## 5. Incident escalation

If a deployer, user, oversight person, or external researcher reports an incident involving Helpmefindthejob that may involve any of R1–R8 (or a previously-unidentified risk):

1. **Reporter**: file via [`../SECURITY.md`](../SECURITY.md) or open a GitHub issue tagged `incident-ai-act`.
2. **Triage** (within 5 working days): provider acknowledges receipt and classifies severity (Sev-1: ongoing fundamental-rights breach; Sev-2: pattern bias affecting a documented persona class; Sev-3: single-event misfire; Sev-4: documentation gap).
3. **Notify**: for Sev-1 and Sev-2, the provider notifies all current deployers known to the project (via the AUTHORS.md contact list and via the public GitHub Discussions thread that affected deployers subscribe to). Deployers in turn meet their Article 73 post-incident-notification obligations to their supervisory authority within the regulatory window.
4. **Remediate**: technical fix or documentation update, with a public post-incident analysis appended to this register.
5. **Review**: next scheduled risk-register review includes the incident's lessons.

---

## 6. Review cadence

- **Quarterly**: lightweight review — check the European AI Office publication feed and the ISO 23894 ratification status; update §3 if new risks have emerged from operational experience.
- **Every six months**: full review — re-examine likelihood and severity ratings, re-run the bias-testing methodology, update the register.
- **Every major release**: review changes to the code surface against this register; any new AI surface (new MCP tool, new analysis call) is mapped to existing risks or added as a new one.
- **Every reported incident**: as per §5 above, the post-incident review feeds the register.

---

## 7. Append log

- **2026-05-18**: initial risk register drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Authored by the project maintainers. First scheduled review: November 2026.
