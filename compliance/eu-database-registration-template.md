<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# EU AI Database Registration Template

**Audience**: **the deployer**, completing registration of the high-risk AI system in the EU AI database before placing it into service.
**Article**: AI Act Article 49 (registration of high-risk AI systems).
**Status**: living template. Updated when the European AI Office publishes refinements to the database schema.

---

## What this is

Article 49 requires that high-risk AI systems be registered in the EU AI database **before they are placed into service** (or used by a deployer, for public-authority deployers). This template is a **pre-filled draft** of the provider-side fields you can use to complete your registration. The deployer fills in the deployment-specific fields and submits.

Once registration is complete, the deployer retains a copy of the submission and the EU-issued registration identifier. The identifier is reproduced in the deployer's transparency-notice addendum (`[Deployer-managed addendum]` section of [`transparency-notice.md`](transparency-notice.md)).

This template is structured against the publicly-known schema of the EU AI database as of the writing of this document. The European AI Office publishes refinements; the deployer verifies the current schema at the time of submission and adapts the registration accordingly.

---

## Section A — Provider information

Pre-filled by the project. Verify at submission time against the current state of the repository.

| Field | Value |
|---|---|
| Provider name | [Deployer/maintainer to confirm: the project maintainer today; The Commons Conservancy only if and when its admission is accepted — admission is currently pending] |
| Provider organisation type | [To confirm: sole maintainer today; Foundation (Stichting) under Dutch law only if Commons Conservancy admission is accepted] |
| Provider country of establishment | Netherlands |
| Provider primary contact | `[TBD: maintainer to fill once Commons Conservancy admission lands]` |
| Provider authorised representative in the Union | Not applicable (provider is EU-established) |
| Provider VAT or registration identifier | `[TBD: Commons Conservancy to provide]` |
| Provider website | `[TBD: to be set once Commons Conservancy Programme page lands]` |
| Provider repository URL | `https://github.com/maksodf/helpmefindthejob` |

---

## Section B — High-risk AI system identification

Pre-filled by the project. Verify against the current release.

| Field | Value |
|---|---|
| AI system trade name | Helpmefindthejob |
| AI system version | `[TBD: deployer to specify the deployed version at registration time, e.g., v0.1.0]` |
| Annex III category | §4 — Employment, workers' management and access to self-employment |
| Specific high-risk use case description | Recruitment / selection support: AI-assisted fit-scoring of job postings against user CV, CV tailoring, motivation-letter drafting, application-outcome analysis. Outputs are advisory; no automated decisions. |
| Intended purpose (one-sentence) | An open-source civic-employment copilot that captures specialist HR and bureaucratic-navigation knowledge into modular, MCP-composable tools and puts it in the hands of users facing structural labor-market friction. |
| Intended populations (cf. Decision 21 + persona panel) | Anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work. Migrants and EU-mobile workers are the most acute use case; the same architecture also serves career changers, returning workers after caregiving, the long-term unemployed re-entering, returning expats, older workers facing implicit-bias filtering, and first-generation graduates. |
| Geographic scope at provider level | EU + Horizon-associated countries; first reference deployment in Germany; architecture is country-neutral. |
| Geographic scope at deployer level | `[TBD: deployer to specify their actual deployment territory]` |
| Sectoral scope | Civic employment services (Beratungsstellen, IQ-Netzwerk, Optionskommune Jobcenter, university career services, NGOs) and individual self-hosting. |

---

## Section C — Conformity assessment

| Field | Value |
|---|---|
| Conformity assessment procedure used | `[TBD: deployer to specify — typically Annex VII internal control for the Annex III §4 employment use case unless the deployer is required to engage a notified body]` |
| Notified body involvement | `[TBD: deployer to specify — typically none for Annex VII internal control]` |
| Conformity assessment date | `[TBD: deployer to fill at the date of completion]` |
| Reference to technical documentation | `compliance/technical-documentation.md` in the project repository (or the deployer's archived copy thereof) |
| Reference to risk-management documentation | `compliance/risk-management-plan.md` in the project repository (or the deployer's archived copy thereof) |
| Reference to audit-log schema | `compliance/audit-log-schema.md` in the project repository (or the deployer's archived copy thereof) |

---

## Section D — Deployer information (deployer to complete)

| Field | Value |
|---|---|
| Deployer name | `[TBD: deployer to fill]` |
| Deployer organisation type | `[TBD: deployer to fill — e.g., Migrationsberatungsstelle, Optionskommune Jobcenter, university career service, NGO, individual self-hoster]` |
| Deployer country of establishment | `[TBD: deployer to fill]` |
| Deployer primary contact | `[TBD: deployer to fill]` |
| Deployer data-protection officer (if applicable) | `[TBD: deployer to fill or mark "Not applicable"]` |
| Deployer's appointed human-oversight person | `[TBD: deployer to fill — same as `human-oversight-guide.md` §1]` |
| Deployer's reference to the FRIA | `[TBD: deployer to fill if public-authority — file reference or URL to the lodged FRIA]` |
| Deployer's intended date of putting into service | `[TBD: deployer to fill]` |

---

## Section E — Operational specifics (deployer to complete)

| Field | Value |
|---|---|
| Number of users expected per year | `[TBD: deployer's estimate]` |
| Whether the system is used for any decision affecting access to or denial of employment, work conditions, promotion, termination | No (per the technical documentation §3.1 and the journey-state-machine design; no automated decisions). |
| Whether the system uses data not anticipated in the technical documentation | `[TBD: deployer to confirm — typically "No" unless the deployer has added a data source]` |
| Whether AI-provider configuration differs from defaults | `[TBD: deployer to confirm — specify AI provider chosen]` |
| Whether human-oversight mode is enabled or disabled | `[TBD: deployer to specify — `enabled` / `disabled` / hybrid]` |
| Retention period for the audit log | `[TBD: deployer to specify — default 180 days]` |

---

## Section F — Pre-submission checklist

The deployer verifies each item before submitting the registration.

- [ ] Section A is current with the latest repository state.
- [ ] Section B specifies the deployed version of Helpmefindthejob.
- [ ] Section C specifies the conformity-assessment procedure used.
- [ ] Section D is complete with the deployer's information.
- [ ] Section E specifies the operational configuration in this deployment.
- [ ] The FRIA (if applicable) has been completed and lodged with the relevant supervisory authority.
- [ ] The transparency notice's `[Deployer-managed addendum]` is complete and the rendered notice has been verified at the deployment URL.
- [ ] The human-oversight person has been appointed and the appointment record is complete in `human-oversight-guide.md` §1.
- [ ] The bias-testing methodology has been run against the chosen AI provider configuration and the results are filed.
- [ ] An initial backup-and-restore drill has been completed and documented.
- [ ] The provider has been informed of the deployment so it can be included in the post-market monitoring plan's known-deployers list.

---

## Section G — Submission record (deployer to complete after submission)

| Field | Value |
|---|---|
| Date of submission | `[TBD: deployer to fill]` |
| EU AI database registration identifier | `[TBD: deployer to fill upon receipt]` |
| Confirmation receipt reference | `[TBD: deployer to fill]` |
| Date of next scheduled review of this registration | `[TBD: deployer to fill — typically 12 months from submission, or sooner if substantive changes]` |

---

## Section H — Change management

When a substantive change happens at provider level (new AI surface added, MCP tool catalogue expansion changing the scope, AI provider list changed, encryption-at-rest scheme changed, audit-log schema version bump), the provider publishes a release note explicitly flagging the change as a candidate for deployer-side registration update.

The deployer assesses whether the change is substantive enough to require an update to their EU AI database entry. The default posture is conservative: any change that affects the intended-purpose description, the affected-population description, the conformity-assessment basis, the risk register, or the technical-documentation Annex IV content is substantive. Purely internal refactors and bugfixes are not substantive.

---

## Section I — Notes

- This template is a **starting point**, not a complete registration. The European AI Office may extend or alter the schema between the writing of this document and your submission. Verify the current schema at submission time.
- The template assumes Annex III §4 (employment) classification. If a specific deployment falls into a different or additional category, the deployer adds the relevant sections.
- The provider does not submit on behalf of deployers. Each deployer submits their own registration; the provider supports with the upstream pre-fills in this template.

---

## Append log

- **2026-05-18**: initial template drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint.
