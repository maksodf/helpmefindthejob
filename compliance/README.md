<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# EU AI Act Compliance Pack

**Status**: shipped as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Living documentation — updated alongside any change to system behaviour that affects the obligations under Regulation (EU) 2024/1689.

This directory is the **DirectJob Scout EU AI Act compliance pack**. It documents how the project meets the high-risk-AI obligations applicable to employment-related AI systems under [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) (the "AI Act"), with general high-risk-AI obligations becoming enforceable on **2 August 2026**.

DirectJob Scout is squarely within Annex III §4 of the AI Act:

> *recruitment or selection of natural persons, in particular to place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates, as well as AI systems intended to be used to make decisions affecting terms of work-related relationships*

Any institution deploying DirectJob Scout inherits the AI Act high-risk-system obligations as the **deployer** (Article 26). DirectJob Scout maintainers are the **provider** (Article 16). The two roles have distinct obligations; this pack covers the provider's obligations in full and ships **pre-fillable templates** for the deployer-specific obligations so a deployer's compliance work is reduced to local-context completion rather than from-scratch engineering.

For the strategic and historical context behind this work, see [`../docs/grant/10-ai-act-compliance.md`](../docs/grant/10-ai-act-compliance.md). For the cost-saving mechanism this pack underpins, see [`../docs/grant/08-cost-saving-doctrine.md`](../docs/grant/08-cost-saving-doctrine.md) §"Mechanism 5".

---

## What's in this directory

| File | Article(s) | Audience | What it is |
|---|---|---|---|
| [`risk-management-plan.md`](risk-management-plan.md) | Art. 9 | Provider | Identified risks specific to civic employment AI, mitigation measures, residual risks, review cycle, incident escalation. |
| [`data-governance.md`](data-governance.md) | Art. 10 | Provider | What data flows through the system, what is logged, prompt-construction and fit-scoring bias testing methodology, data-quality controls. |
| [`technical-documentation.md`](technical-documentation.md) | Art. 11 + Annex IV | Provider + deployer | The complete Annex IV technical documentation in all 9 sections. |
| [`audit-log-schema.md`](audit-log-schema.md) | Art. 12 | Provider + deployer | JSON Lines schema for the audit log, retention controls, query examples, PII-hashing default. Pairs with the running [`../company_discovery/audit_log.py`](../company_discovery/audit_log.py) emitter. |
| [`transparency-notice.md`](transparency-notice.md) | Art. 13 | **End user** | First-run and settings-screen disclosure: what is AI-assisted, what data is sent to AI providers, opt-out rights, oversight contact, right to explanation. |
| [`deployer-operating-manual.md`](deployer-operating-manual.md) | Art. 13 | **Deployer** | What the deployer needs to operate the system in compliance with Article 26: configuration, human-oversight setup, retention controls, data-subject-request handling, incident reporting. |
| [`human-oversight-guide.md`](human-oversight-guide.md) | Art. 14 | Deployer + oversight person | How effective human oversight is achieved: kill-switch, advisor review mode, override and annotation, default-off-for-final-decisions. Pairs with the `/api/admin/oversight/queue` admin endpoint. |
| [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md) | Art. 15 | Provider | Accuracy metrics, bias-testing methodology grounded in the seven-persona panel, robustness and cybersecurity controls. |
| [`eu-database-registration-template.md`](eu-database-registration-template.md) | Art. 49 | **Deployer** | Pre-filled template for registration of the high-risk AI system in the EU AI database. Deployer completes deployment-specific fields. |
| [`fundamental-rights-impact-assessment-template.md`](fundamental-rights-impact-assessment-template.md) | Art. 27 | **Public-authority deployer** | Pre-filled FRIA template for public-sector deployers. Deployer completes affected-population, governance-context, and remediation-channel sections. |

---

## Who this pack is for

The pack distinguishes three audiences. Each file's header repeats this for the reader who lands on it directly.

- **Provider** (DirectJob Scout maintainers under the Commons Conservancy). Obligations: Articles 9–15, 11+Annex IV technical documentation, post-market monitoring under Article 72.
- **Deployer** (the institution that deploys DirectJob Scout — a Beratungsstelle, IQ-Netzwerk regional office, Optionskommune Jobcenter, university career service, NGO, individual self-hoster). Obligations under Article 26: input-data appropriateness, monitoring under Article 26(5), human oversight per Article 14, AI database registration per Article 49, FRIA for public-authority deployers per Article 27, post-incident notification per Article 73.
- **End user** (the jobseeker using DirectJob Scout). Rights under Articles 86 and 50: right to an explanation of an individual decision affecting them, right to know they are interacting with an AI system.

---

## Friction-class framing (Decision 21)

DirectJob Scout serves **anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work**. Migrants and EU-mobile workers are the most acute use case and provide the densest concentration of friction per user; the same architecture also serves career changers, returning workers after caregiving or extended absence, the long-term unemployed re-entering, and others. The architecture is friction-driven, not demographic-driven. See [`../docs/grant/04-research-and-decisions.md`](../docs/grant/04-research-and-decisions.md) Decision 21 for the binding decision, and [`../docs/grant/07-personas.md`](../docs/grant/07-personas.md) for the seven-persona panel that anchors the framing.

This framing is embedded in:
- The user-facing transparency notice's "who this is for" section
- The deployer operating manual's "who you can serve" section (so a Jobcenter understands the tool fits their full caseload, not only the migrant subset)
- The accuracy-and-bias testing methodology (testing covers the wider-friction-class personas Käthe and Tobias alongside the most-acute five)
- The FRIA template's "affected population" section

The remaining compliance documents (risk management, data governance, technical documentation, audit log schema, human-oversight guide, EU database registration template) describe technical and regulatory mechanisms that are population-neutral and apply identically regardless of who is served.

---

## What this pack does not claim

- **It is not an AI Act certification.** The AI Act does not have a self-certification mark for open-source providers. Where a deployment is high-risk (Annex III §4 employment), the formal conformity-assessment route is typically Annex VII internal control (Art. 43(1)) or notified-body involvement; this is a deployer-context determination, not something the project asserts unilaterally.
- **It does not transfer the deployer's responsibility.** A deployer remains accountable for their specific deployment context, the FRIA, AI database registration, and ongoing operational monitoring under Article 26.
- **It is not legal advice.** Where a deployer has specific legal questions, those go to their counsel. The pack reduces the technical and documentation burden; it does not replace legal review of the deployment in context.
- **It does not freeze the obligations as of the current date.** The European AI Office continues to publish guidance, and ISO/IEC 23894 has yet to be ratified at the time of this writing. We re-review the pack every quarter and on every European AI Office publication of relevance.

---

## How this pack is maintained

- **Living documents**: every file is plain Markdown under Apache-2.0 with SPDX headers, editable via PR.
- **Review cadence**: full pack reviewed every six months and on every major release (per `risk-management-plan.md` §6).
- **Change log**: substantive changes append an entry to each file's bottom section. Cross-cutting changes are logged once in [`../docs/grant/10-ai-act-compliance.md`](../docs/grant/10-ai-act-compliance.md).
- **Audit log code**: the `company_discovery/audit_log.py` emitter has a separate test suite under `tests/test_phase13_audit_log.py`; integration tests exercise the MCP-tool and AI-invocation surfaces.

---

## How to use this pack as a deployer

Read in this order:

1. [`deployer-operating-manual.md`](deployer-operating-manual.md) — orient yourself on what you are responsible for as the deployer.
2. [`human-oversight-guide.md`](human-oversight-guide.md) — set up the oversight person and decide on review-mode configuration.
3. [`audit-log-schema.md`](audit-log-schema.md) — understand what the system logs and configure retention to match your jurisdiction's requirements.
4. [`transparency-notice.md`](transparency-notice.md) — review what end users will be shown; tailor the local-context fields.
5. [`eu-database-registration-template.md`](eu-database-registration-template.md) — complete the deployment-specific blanks and submit the EU AI database registration before going live.
6. (Public-authority deployers only) [`fundamental-rights-impact-assessment-template.md`](fundamental-rights-impact-assessment-template.md) — complete the FRIA and lodge it with the relevant supervisory authority per Article 27.

The other files document the provider-side compliance and exist for reference and for any audit or supervisory review.

---

## Cross-references

- [`../docs/grant/10-ai-act-compliance.md`](../docs/grant/10-ai-act-compliance.md) — the strategic plan that drove this pack.
- [`../docs/grant/08-cost-saving-doctrine.md`](../docs/grant/08-cost-saving-doctrine.md) §"Mechanism 5" — the cost-saving claim this pack underpins.
- [`../STANDARDS.md`](../STANDARDS.md) — full list of standards we cite, including Regulation (EU) 2024/1689.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — system architecture; the audit-log layer is rendered in the Mermaid diagram.
- [`../docs/grant/07-personas.md`](../docs/grant/07-personas.md) — the seven-persona panel referenced in user-base-facing files.

---

## License

This pack is licensed under the **Apache License 2.0** (SPDX: `Apache-2.0`). See [`../LICENSE`](../LICENSE) and [`../NOTICE`](../NOTICE).

Copyright (c) 2026 DirectJob Scout contributors.
