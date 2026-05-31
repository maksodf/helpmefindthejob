<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Tobias (Hamburg, backend developer, commercial → civic-tech pivot)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Tobias** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-30.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `tobias` |
| Cohort | wider friction-class (architectural demonstration per Decision 21) |
| Origin → destination | Hamburg → Hamburg (no migration) |
| Profession | Senior backend developer (Python, Go, distributed systems), 11 yrs at a Hamburg fintech startup; led a team of four |
| Residency status | EU citizen (German national) |
| Languages | DE native; EN C1-business |
| Friction context | Pivoting from commercial fintech to public-sector / civic-tech; the friction is the language-and-format gap between commercial-tech CV conventions and TVöD-aware public-sector hiring conventions (pay grades, formal Bewerbungsmappen, civic-service vocabulary) |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[6]` + `docs/grant/07-personas.md` §7 + `docs/persona-walks/tobias.md` |

## 2. Affected population

Tobias-class users are EU-citizen senior IC professionals making a commercial → public-sector / civic-tech career pivot. Typical scale at a Hamburg + national civic-tech community (Code for Hamburg, GovTech-adjacent networks) and public-sector digital hiring channels: 50–100 candidates per quarter. Vulnerability factors: pivot-narrative-coherence pressure (is the commercial-tech professional "serious" about lower-paid civic work); TVöD-grade-calibration mismatch with prior commercial bands; commercial → civic vocabulary-translation difficulty.

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Tobias | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | The pivot is the dignity-fragility area; the AI must frame the move as evidence-of-ROI / public-service motivation, not as a "step down" or a sign the candidate could not cut it commercially | The cv_summary scaffolds: "Senior backend developer pivoting commercial → civic-tech; evidence-of-ROI orientation, TVöD-grade-aware"; the Anschreiben prompt scaffolds the civic-service-motivation framing | Advisor reviews any score that appears to penalise the pivot |
| Art. 15 (Free choice of occupation) | Tobias is German-credentialed (no Anerkennung needed); the question is JD-language-alignment between commercial and public-sector conventions, not credentials | The friction-fit scale awards JDs that explicitly signal openness ("Quereinsteiger", "career changer welcome", "diverse Hintergründe willkommen") | Deployer maintains the public-sector / civic-tech employer list (GovTech Campus, Sovereign Tech Fund-affiliated projects, Code for Germany, Prototype Fund-adjacent organisations, federal IT, civic-NGO digital teams) |
| Art. 21 (Non-discrimination) | Career-pivot CVs face documented skepticism in German recruiting ("will a commercial-tech person stay in TVöD-paid civic work?"). Tobias is the persona where the pivot-coherence question is most-tested | Bias-comparative-report shows Tobias at mean SCORE 74.3 (deepseek) — the highest of the cohort, reflecting good architectural fit | Quarterly bias re-run with Tobias-class as a specific monitored cohort |
| Art. 31 (Fair working conditions) | TVöD-grade-aware roles are bound by collective-bargaining; the project does NOT mediate TVöD-band disputes | Out-of-scope by design | n/a |
| Art. 33 (Family + professional life) | n/a (Tobias-specific) | n/a | n/a |
| Art. 41 (Good administration) | The public-sector procurement / hiring cycle is a deployer-adjacent factor; agencies' hiring windows align differently with commercial timelines | Maintainer recommendation: surface the procurement-cycle (Section 2.6 deferred) | Deployer advisor pulls agency-specific hiring windows |

## 4. R1–R8 risk modulation for Tobias

| Risk | Modulation for Tobias | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | The commercial → civic pivot is the methodology's test surface; Tobias's high mean score in the comparative report suggests the architecture handles this well | L×M |
| R2 Language-based filtering | Tobias is DE-native + EN C1; n/a | VL×L |
| R3 Foreign-credential bias | n/a (Tobias is German-credentialed) | VL×L |
| R4 Scoring opacity | Per-criterion breakdown helps Tobias distinguish "pivot-mismatch" from "fit-issue" — important for the civic-tech onboarding narrative | L×M |
| R5 Automation | Confirmation gates intact | VL×M |
| R6 Data-egress | Tobias's data is less sensitive than asylum-stage; standard data-egress disciplines | L×L |
| R7 Compliance-pack-as-shield | Standard | L×L |
| R8 Drift | TVöD bargaining updates annually; the civic-tech employer landscape updates as agencies launch new programmes | M×L |

## 5. Top concern + compensating control

**Top concern**: Art 1 dignity + R1 fit-scoring on commercial → civic pivot-coherence. The risk: AI outputs that mechanistically read the pivot as "couldn't make it commercially" reinforce the dignity-fragility surface the user is already navigating, rather than crediting the public-service motivation.

**Compensating control**: the friction-fit anchor scale's "evidence-of-ROI framing for non-linear careers" guidance + the per-criterion breakdown helping Tobias understand WHY a low fit-score happened. The civic-tech volunteer-portfolio-as-pivot-evidence framing (recommended in the persona walk's cover-letter section) is the user-side compensating control.

## 6. Article 22 escalation pathway for Tobias

A Hamburg civic-tech community coordinator (e.g., Code for Hamburg) OR the deployer's public-sector-hiring advisor receives escalation. Communication in DE OR EN per Tobias's preference. The civic-tech volunteer-portfolio is the deployer-adjacent record; the advisor pulls it as part of the appeal review.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`support@helpmefindthejob.org`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA + R1–R8 modulation + Top-concern (Art 1 dignity + R1 commercial→civic pivot-coherence) + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `compliance/fundamental-rights-impact-assessment-template.md` + `docs/persona-walks/tobias.md` |
