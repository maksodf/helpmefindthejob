# EU AI Act Compliance Pack

**Status**: technical-spine document. Drives Week 2–3 work in `02-execution-plan.md` and the cost-saving claim in `08-cost-saving-doctrine.md` §"Mechanism 5".

**Implementation status (2026-05-18)**: §2.8 of the execution plan shipped — the live compliance pack is at [`/compliance/`](../../compliance/) in the repository, with the Article 12 audit-log emitter at [`../../company_discovery/audit_log.py`](../../company_discovery/audit_log.py) and integration into [`../../mcp_server.py`](../../mcp_server.py) and [`../../company_discovery/analysis.py`](../../company_discovery/analysis.py). The Article 14 minimum-viable human-oversight admin endpoint is at `/api/admin/oversight/queue` in `app.py` (admin-gated, controlled by `HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE`). Tests in `tests/test_phase13_audit_log.py` (20 tests covering emitter, caller-context, convenience wrappers, MCP integration, analysis integration, and the tail helper).

This document describes how Helpmefindthejob is designed to be compliant with the EU AI Act high-risk-AI obligations applicable to employment-related AI systems, with deadline **2 August 2026**.

The work in this document is not optional. It is the single largest piece of regulatory differentiation the project offers — and the largest reason institutions will adopt our open-source tool rather than build their own.

---

## Why this matters

The EU AI Act (Regulation (EU) 2024/1689) classifies as **high-risk** any AI system used for:

> *recruitment or selection of natural persons, in particular to place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates, as well as AI systems intended to be used to make decisions affecting terms of work-related relationships, the promotion or termination of work-related contractual relationships, to allocate tasks based on individual behaviour or personal traits or characteristics or to monitor and evaluate the performance and behaviour of persons in such relationships.*
>
> — AI Act Annex III, §4(a) and §4(b)

Helpmefindthejob is squarely inside this definition. We score job-to-CV fit, we filter and recommend roles, we draft motivation letters that are sent to recruiters. Every institution that deploys our agent inherits the AI Act high-risk-system obligations.

The full set of obligations becomes enforceable on **2 August 2026** — roughly 2.5 months from the writing of this document. Public-sector deployers (Jobcenter, Beratungsstellen, Agentur für Arbeit) will be looking for tools that already meet the obligations on day one of enforcement.

**This is our moat.** Most commercial AI job tools are still scrambling. We ship compliance-supporting controls, templates, audit logging, transparency surfaces, and deployer guidance by default; each deployer retains its own context-specific legal review.

---

## The six high-risk-AI obligations and how we meet each

The high-risk-AI obligations under the AI Act break down into six concrete technical and documentation requirements. Each is matched to a specific deliverable in our compliance pack.

### Obligation 1: Risk management system (Article 9)

**Requirement**: A documented, ongoing risk-management process covering risks the AI system may pose to health, safety, and fundamental rights.

**Our deliverable**: `compliance/risk-management-plan.md` documenting:
- Identified risks specific to job-matching AI (discrimination, language-based filtering, foreign-credential bias, scoring opacity, automation of decisions affecting work life)
- Mitigation measures built into the system (audit logs, human oversight, transparency, opt-out, no auto-decision)
- Residual risks acknowledged
- Review cycle (every 6 months, every major release, every reported incident)
- Incident escalation procedure

### Obligation 2: Data and data governance (Article 10)

**Requirement**: Training, validation, and testing data sets must be relevant, representative, free of errors, and complete. Documented bias detection.

**Our deliverable**: `compliance/data-governance.md` documenting:
- The AI Act applies to *training* data when the system is provider-trained. Our system does not train models on user data — we use third-party general-purpose AI providers through the BYO-AI abstraction. The user (or operator) supplies the AI provider; we orchestrate prompts, not training.
- This shifts our data-governance scope: we document what user data flows through prompts, what is logged, what is retained, and the bias-testing of our *prompt construction* and *fit-scoring logic*.
- We publish the prompts used in fit-scoring and CV-tailoring so they are auditable.
- We publish bias-testing methodology (e.g., do we score Aïcha's Tunisia-trained nursing experience equivalently to a German-trained nurse with the same skills? Tested.)

### Obligation 3: Technical documentation (Article 11 + Annex IV)

**Requirement**: Comprehensive technical documentation that allows authorities to assess compliance.

**Our deliverable**: `compliance/technical-documentation.md` covering all 9 sections of Annex IV:
1. General description (what the system does, where it's deployed, who operates it)
2. Detailed description (architecture, modules, AI components, dependencies)
3. Development process and quality management
4. Performance and accuracy metrics, including bias-testing results
5. Risk management plan (see Obligation 1)
6. Changes through lifecycle
7. Compliance with harmonised standards (we cite ISO/IEC 23894 once published, and schema.org / ESCO / EURES for data interop)
8. EU declaration of conformity (template included for operators)
9. Post-market monitoring plan (see Obligation 6)

**Important**: this documentation is for the operator who deploys our agent. We provide the template + the system-specific content; the operator fills in the deployment-specific blanks (their organisation, their oversight contacts, their incident-reporting channel).

### Obligation 4: Record-keeping (Article 12)

**Requirement**: The system must automatically record events ("logs") that allow traceability.

**Our deliverable**: an audit log layer integrated into the MCP server and the web app, recording:
- Every AI invocation (timestamp, user opaque ID, AI provider, prompt template ID, tokens in/out, response summary)
- Every job-fit-scoring event
- Every CV tailoring or motivation-letter draft
- Every persistence action requiring user confirmation
- Every export of personal data
- Every consent grant or revocation

Logs are JSON Lines, structured, and queryable. Default retention is 6 months; configurable per operator. PII is hashed unless the operator opts in to plaintext logging.

### Obligation 5: Transparency and provision of information to deployers (Article 13)

**Requirement**: The system must be designed to enable deployers to understand its functioning, limitations, and how to interpret its outputs.

**Our deliverables**:
- A **transparency notice for users**, shown at first run and in settings, explaining: (a) the system is AI-assisted; (b) which actions invoke AI; (c) what data is sent to the AI provider; (d) the user's right to opt out of AI-assisted features; (e) the human-oversight contact; (f) the right to obtain an explanation of any AI-influenced decision.
- A **deployer-facing operating manual** explaining: what each component does, what the AI does and does not decide, how to configure human oversight, how to set retention, how to respond to data-subject requests, how to report incidents.

### Obligation 6: Human oversight (Article 14)

**Requirement**: High-risk systems must be designed for effective human oversight, allowing oversight persons to understand the system, monitor its operation, override its output, and decide not to use it.

**Our deliverables**:
- A **human-oversight UI** for institutional deployers — an advisor can review the agent's outputs (fit scores, CV drafts, letter drafts) before they are presented to the user, with the ability to edit, reject, or annotate.
- A **default-off-for-final-decisions mode**: the agent never automatically submits an application, accepts a contract, or makes any binding decision. Every consequential action is gated by user confirmation.
- A **kill-switch**: institutions can disable AI features entirely via configuration, falling back to a templated, deterministic agent. Confirms with Article 14's requirement that the human oversight person be able to "decide, in any particular situation, not to use the high-risk AI system."

### Obligation 7 (implicit): Accuracy, robustness, cybersecurity (Article 15)

**Requirement**: Appropriate level of accuracy, robustness, and cybersecurity throughout the lifecycle.

**Our deliverables**:
- Accuracy: published metrics for fit-scoring against a labelled test set (built and published during Week 3)
- Robustness: error handling, graceful degradation when AI providers are unavailable, deterministic fallback paths
- Cybersecurity: encrypted-at-rest user data (ChaCha20-Poly1305), Apache 2.0 dependency audit (`pip-audit` in CI), `security.txt` (RFC 9116) at `/.well-known/security.txt`, SECURITY.md vulnerability-reporting channel

---

## Additional obligations specific to deployers

The AI Act distinguishes between *providers* (us, the project) and *deployers* (operators of the system). Some obligations fall on the deployer, not us:

- **EU database registration** (Article 49): high-risk AI systems must be registered in the EU AI Act database before being put into service. This is the deployer's responsibility, not ours. We provide a pre-filled registration template.
- **Fundamental Rights Impact Assessment (FRIA)** (Article 27, specific to public-authority deployers): public bodies must conduct a FRIA before deploying. We provide a template.
- **Notification to data subjects in deployment context**: the deployer informs users in their specific local context. We provide the user-facing transparency notice; the deployer adds their organisation-specific information.
- **Logging retention and review**: the deployer keeps logs for the legally-required period (typically 6 months minimum) and reviews them. We provide the log infrastructure; the deployer decides retention and review cadence.

The pack we ship makes the deployer's compliance burden small but does not eliminate it. We are explicit about this.

---

## The cost-saving argument tied to AI Act compliance

This is the largest single cost-saving mechanism in the project. For an institution adopting AI in employment context after 2 August 2026, the alternatives are:

1. **Buy a commercial tool and hope it's compliant.** Most commercial job-AI tools are scrambling to retrofit compliance. The risk to the institution is significant — fines under the AI Act can reach €15M or 3% of global turnover.

2. **Build internal AI tooling and do the compliance engineering.** Estimated cost: €30–200k in consultant time + internal staff effort + ongoing legal review. Most institutions cannot absorb this.

3. **Deploy Helpmefindthejob (or a comparable open-source compliant tool) and inherit the compliance pack.** Cost: deployment time + the operator's local-context fill-in work, typically a small fraction of options 1 or 2.

We make option 3 viable for the first time.

---

## The compliance pack as a deliverable bundle

The compliance pack is shipped as a coherent set of files in `/compliance/`:

- `compliance/risk-management-plan.md` (Obligation 1)
- `compliance/data-governance.md` (Obligation 2)
- `compliance/technical-documentation.md` (Obligation 3 + Annex IV)
- `compliance/audit-log-schema.md` + the running audit log infrastructure (Obligation 4)
- `compliance/transparency-notice.md` (user-facing) + `compliance/deployer-operating-manual.md` (Obligation 5)
- `compliance/human-oversight-guide.md` + the UI itself (Obligation 6)
- `compliance/accuracy-and-bias-testing.md` (Obligation 7)
- `compliance/eu-database-registration-template.md` (deployer pre-fill)
- `compliance/fundamental-rights-impact-assessment-template.md` (deployer pre-fill)

All under Apache 2.0, all in plain Markdown, all updateable by anyone via PR.

---

## What we explicitly do not claim

- **We do not claim our system is "AI Act certified."** The AI Act does not have a self-certification mark for open-source providers. Conformity assessment for high-risk systems typically involves a notified body (third-party certification) or, for systems sufficiently low-risk in a specific deployment context, self-assessment by the deployer.
- **We do not claim each deployer is compliant by deploying us.** The deployer remains responsible for their specific deployment context, the FRIA, the EU database registration, and ongoing operational compliance.
- **We do not claim our compliance pack replaces legal advice.** Operators with specific legal questions consult their counsel.

What we *do* claim is that we have **substantially reduced the technical compliance burden** for any institution wanting to deploy AI-assisted employment-services tooling under the AI Act.

---

## Phase 2 work

- Engage with a notified body to explore conformity assessment for the "core deployment configuration" of Helpmefindthejob — this would let deployers in some configurations rely on the upstream assessment.
- Track the publication of ISO/IEC 23894 (AI risk management standard) and align documentation accordingly.
- Track the European AI Office's published guidance and update the pack with each significant publication.
- Apply for NLnet's offered security audit as a follow-on milestone.

---

## Sources

- [EU AI Act, Annex III](https://artificialintelligenceact.eu/annex/3/)
- [EU AI Act, Article 6 (classification of high-risk AI)](https://artificialintelligenceact.eu/article/6/)
- [EU AI Act, Article 9–15 (high-risk AI obligations)](https://artificialintelligenceact.eu/)
- [EU AI Act, Annex IV (technical documentation)](https://artificialintelligenceact.eu/annex/4/)
- [European AI Office](https://digital-strategy.ec.europa.eu/en/policies/ai-office)
- [Regulation (EU) 2024/1689 — official text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Knowlee: AI Act Annex III HR & Employment Compliance Guide](https://www.knowlee.ai/blog/ai-act-annex-iii-hr-employment)
- [DLA Piper EU AI Act high-risk uses tracker](https://intelligence.dlapiper.com/artificial-intelligence/?t=06-high-risk-uses&c=EU)
