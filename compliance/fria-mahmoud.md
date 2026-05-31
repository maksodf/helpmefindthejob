<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Mahmoud (Syria → Hamburg, §4 Subsidiärer Schutz, trade Ausbildung)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Mahmoud** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-24.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `mahmoud` |
| Cohort | most-acute migrant (primary anchor) |
| Origin → destination | Syria → Hamburg |
| Profession | Pre-flight HVAC + plumbing background; targeting trade-apprenticeship pathway (Ausbildung) |
| Residency status | §4 AsylG Subsidiärer Schutz (subsidiary protection holder) |
| Languages | AR native; DE B2 in trades-context, B1 in admin-form-context |
| Friction context | Ausbildung pathway (NOT direct hire); HVAC/plumbing employers + Berufsschule alignment + IHK-recognised programme constraints |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[3]` + `docs/persona-walks/mahmoud.md` |

## 2. Affected population

Mahmoud-class users are §4-AsylG subsidiary-protection holders seeking trade Ausbildung. Typical scale at Hamburg AWO + Caritas integration-services + Handwerkskammer Ausbildung coordination: 60–120 active clients per coordinator per year. Vulnerability factors: trauma + asylum-stage uncertainty; pre-Ausbildung integration-course window (Berufsschule Vorqualifizierung); IHK-recognised programme gating; lower per-month income during Ausbildung.

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Mahmoud | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | A "low fit" verdict on an Ausbildung-friendly employer that explicitly accepts Quereinsteiger sends the wrong signal; Mahmoud's pre-flight workshop experience IS the entry-level fit | The friction-fit calibration recognises Ausbildung-entry as "candidate has foundational potential" not "lacks professional credentials" — per the `build_auto_fit_prompt` anchor scale "Entry-level / training-program JDs" guidance | Advisor reviews any low-fit on a Quereinsteiger-friendly Ausbildung role |
| Art. 14 (Right to education) | Ausbildung IS a right-to-education-engagement scenario; the project's surfacing of IHK-recognised programmes is the route to this right | Berufsschule-pairing data + Ausbildung-keyword filter | Deployer maintains the Hamburg SHK Berufsschule list + EQ pre-Ausbildung options |
| Art. 15 (Free choice of occupation) | §4 status grants full work + Ausbildung rights; the AI must not under-rank Mahmoud because of the §4 marker | Friction-fit anchor scale: §4 + Ausbildung = "CLEAN pathway" 22+ band | Quarterly bias re-run on §4 + Ausbildung cells specifically |
| Art. 21 (Non-discrimination) | National-origin + asylum-stage; the integration-course-completion-record is the structural factor | The cv_summary captures the BAMF integration-course certificate as a structured field; the AI prompt reads it | Advisor reviews if any low-fit appears to over-weigh asylum-stage |
| Art. 26 (Integration of persons) | The CFR's Art 26 is technically about persons with disabilities, but the principle (integration of persons facing structural exclusion) maps analogically; the project's friction-class architecture honours this | The persona panel includes Mahmoud as a primary anchor — the system serves this population by design | Deployer monitors Mahmoud-class outcomes specifically |
| Art. 41 (Good administration) | The Ausbildung-application timeline (Berufsschule + employer + IHK certification window) is a Berufsschule-deadline-aware journey opportunity | The journey's `auf 1. August / 1. September start` calendar pacer (Section 2.6 deliverable) | Deployer maintains regional Berufsschule deadline catalogue |

## 4. R1–R8 risk modulation for Mahmoud

| Risk | Modulation for Mahmoud | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | Ausbildung calibration in the anchor scale keeps this LOW for trade roles; the model must distinguish Ausbildung from direct-hire | L×M |
| R2 Language-based filtering | Mahmoud's trades-DE B2 + admin-DE B1 = JDs that demand admin-form German over-exclude; trade-floor JDs are well-served | L×M |
| R3 Foreign-credential bias | Mahmoud's HVAC background is informal (pre-flight); the model treats Ausbildung as "entry-level" not "lacking credentials" per the anchor scale | L×M |
| R4 Scoring opacity | Per-criterion breakdown important so Mahmoud understands the Ausbildung-vs-direct-hire distinction | L×M |
| R5 Automation | Confirmation gates intact | VL×M |
| R6 Data-egress | §4 status is sensitive — deployer restricts BYO-AI to EU-hosted Ollama for Mahmoud's deployer-cohort | **M×H** (asylum-stage info) |
| R7 Compliance-pack-as-shield | Mahmoud is the persona where the friction-class architecture is most-tested; project-side discipline applies | L×L |
| R8 Drift | §4 AsylG framework + Ausbildung-friendly-employer Förderung programmes change per Bundesland; deployer's quarterly review catches drift | M×L |

## 5. Top concern + compensating control

**Top concern**: R6 (data-egress beyond consent) at residual M×H = 12. Mahmoud's §4 status is asylum-stage information; if the deployer's BYO-AI choice routes the prompt through a non-EU provider, the residency-status field reaches that provider.

**Compensating control**: the transparency notice warns at the residency-status field; the deployer's BYO-AI policy SHOULD restrict to EU-hosted options (Ollama or future EU-only managed). The future Article 22 in-app surface (Section 2.10.2) will let Mahmoud opt out of sending the residency-status field to AI on a per-call basis.

## 6. Article 22 escalation pathway for Mahmoud

Hamburg AWO MBE-coordinator OR Caritas Integration-Hilfe advisor receives escalation. Communication in DE OR EN OR AR (Mahmoud may prefer AR for sensitive topics). The Berufsschule + employer + IHK chain involves three separate deployer-adjacent bureaucracies; the advisor's role is to route the appeal to the right one.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`support@helpmefindthejob.org`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA + R1–R8 modulation + Top-concern (R6 data-egress) + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` (Mahmoud's R6 is the DPIA's "migrant-status-disclosure-to-non-EU-AI" highest-residual risk) + `docs/persona-walks/mahmoud.md` |
