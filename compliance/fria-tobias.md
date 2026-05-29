<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Tobias (Berlin, long-term unemployed, commercial→civic-tech pivot)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Tobias** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-24.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `tobias` |
| Cohort | wider friction-class (architectural demonstration per Decision 21) |
| Origin → destination | Berlin → Berlin (no migration) |
| Profession | Senior product / growth (10 yrs); pivoting commercial → civic-tech |
| Residency status | EU citizen (German national) |
| Languages | DE native; EN C1 |
| Friction context | 14-month unemployment gap after startup-fold; pivot is the actual friction (language + format gap between Berlin startup CV conventions and TVöD-aware civic-tech conventions) |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[6]` + `docs/persona-walks/tobias.md` |

## 2. Affected population

Tobias-class users are EU-citizen senior IC professionals in long-term unemployment + career-pivot. Typical scale at a Berlin civic-tech community Slack / CityLAB Berlin / Bundesdruckerei innovation-team alumni network: 50–100 candidates per quarter (the civic-tech Berlin community is concentrated). Vulnerability factors: gap-shame (the 14-month gap as a CV scar); pivot-narrative-coherence pressure; TVöD-grade-calibration mismatch with prior commercial bands.

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Tobias | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | The 14-month gap is the dignity-fragility area; the AI must frame the gap honestly without being apologetic, AND the pivot must be framed as evidence-of-ROI not as desperation | The cv_summary scaffolds: "Senior product professional pivoting commercial → civic-tech after a startup-end transition window. Evidence-of-ROI orientation, TVöD-grade-aware"; the Anschreiben prompt scaffolds the evidence-of-ROI framing | Advisor reviews any score that appears to penalise the gap |
| Art. 15 (Free choice of occupation) | Tobias is licensed (no Anerkennung needed); the question is JD-language-alignment, not credentials | The friction-fit scale awards JDs that explicitly signal openness ("Quereinsteiger", "career changer welcome", "diverse Hintergründe willkommen") | Deployer maintains Berlin civic-tech employer list (CityLAB Berlin, Senatskanzlei Berlin digital, BBSR DLZ-IT, Bundesdruckerei innovation, Code for Germany alumni) |
| Art. 21 (Non-discrimination) | Long-term-unemployment is a structural-friction factor; documented bias against gapped CVs in German recruiting. Tobias is the persona where the pivot-and-gap combination is most-tested | Bias-comparative-report shows Tobias at mean SCORE 74.3 (deepseek) — second-highest of the cohort, reflecting good architectural fit | Quarterly bias re-run with Tobias-class as a specific monitored cohort |
| Art. 31 (Fair working conditions) | TVöD-grade-aware roles are bound by collective-bargaining; the project does NOT mediate TVöD-band disputes | Out-of-scope by design | n/a |
| Art. 33 (Family + professional life) | n/a (Tobias-specific) | n/a | n/a |
| Art. 41 (Good administration) | The public-sector procurement-cycle awareness is a deployer-adjacent factor; some Bundesländer / Bundesländer-equivalent procurement windows align differently with hiring | Maintainer recommendation: surface the procurement-cycle (Section 2.6 deferred) | Deployer advisor pulls Bundesland-specific procurement windows |

## 4. R1–R8 risk modulation for Tobias

| Risk | Modulation for Tobias | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | The pivot-and-gap combination is the methodology's test surface; Tobias's high mean score in the comparative report suggests the architecture handles this well | L×M |
| R2 Language-based filtering | Tobias is DE-native + EN C1; n/a | VL×L |
| R3 Foreign-credential bias | n/a (Tobias is German-credentialed) | VL×L |
| R4 Scoring opacity | Per-criterion breakdown helps Tobias distinguish "pivot-mismatch" from "fit-issue" — important for the civic-tech onboarding narrative | L×M |
| R5 Automation | Confirmation gates intact | VL×M |
| R6 Data-egress | Tobias's data is less sensitive than asylum-stage; standard data-egress disciplines | L×L |
| R7 Compliance-pack-as-shield | Standard | L×L |
| R8 Drift | TVöD bargaining updates annually; civic-tech employer landscape updates as Bundesländer launch new programmes | M×L |

## 5. Top concern + compensating control

**Top concern**: Art 1 dignity + R1 fit-scoring combination on long-term-unemployment-stigma. The risk: AI outputs that mechanistically penalise the 14-month gap reinforce the dignity-fragility surface the user is already navigating.

**Compensating control**: the friction-fit anchor scale's "evidence-of-ROI framing for non-linear careers" guidance + the per-criterion breakdown helping Tobias understand WHY a low fit-score happened. The civic-tech volunteer-portfolio-as-pivot-evidence framing (recommended in the persona walk's cover-letter section) is the user-side compensating control.

## 6. Article 22 escalation pathway for Tobias

Berlin civic-tech community moderator OR CityLAB Berlin alumni-coordinator receives escalation. Communication in DE OR EN per Tobias's preference. The civic-tech volunteer-portfolio is the deployer-adjacent record; the advisor pulls it as part of the appeal review.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`franfreeedo@gmail.com`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA + R1–R8 modulation + Top-concern (Art 1 dignity + R1 long-term-unemployment-stigma) + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `compliance/fundamental-rights-impact-assessment-template.md` + `docs/persona-walks/tobias.md` |
