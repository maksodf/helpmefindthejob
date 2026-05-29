<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Aïcha (Tunisia → Berlin, §16d Anerkennung)

**Article**: AI Act Article 27 (FRIA for high-risk AI systems). Instantiates `compliance/fundamental-rights-impact-assessment-template.md` for the **Aïcha** persona-class as a worked example.

**Status**: project-side reference FRIA. A deployer who serves Aïcha-class users (Migrationsberatungsstellen, IQ-Netzwerk regional offices serving §16d Anerkennung pathways, Klinikum HR teams in DACH) instantiates a deployer-side variant with their specific affected-population numbers, oversight-person identity, and deployment-context modulations.

**Last updated**: 2026-05-24.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `aicha` |
| Cohort | most-acute migrant (primary anchor) |
| Origin → destination | Tunisia → Berlin |
| Profession | Registered nurse, 7 years hospital experience incl. 2 yrs geriatric care |
| Residency status | §16d AufenthG (visa for purpose of recognition of foreign qualification) |
| Languages | FR + AR native; EN B2; DE B1 → B2 |
| Friction context | Recognition decision letter expected ~4 months from BIBB / Anabin; needs Anerkennungs-friendly employers willing to begin onboarding before the letter lands |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[0]` + `docs/grant/07-personas.md` + `docs/persona-walks/aicha.md` |

## 2. Affected population (per the deployer's deployment)

Aïcha-class users are non-EU healthcare professionals in active §16d Anerkennung proceedings. Typical scale at a Berlin MBE: 30–80 active clients per advisor per year. Vulnerability factors: visa-deadline pressure (12–18 months on §16d) + language-gate (clinical German B2 required for the recognition decision) + sectoral pressure (the German shortage-occupation list flags pflege at the highest level).

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Aïcha specifically | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | Fit-scoring that returns "low fit" on Anerkennung-friendly roles communicates "you don't belong here" to a §16d candidate already navigating a high-friction system | Per-criterion `SCORE_FRICTION_FIT` anchor scale awards 22+ for explicitly-Anerkennungs-friendly JDs; AI-output framing is "suggestion, not decision" | Advisor reviews any low-fit on an Anerkennungs-friendly role before showing it to the candidate |
| Art. 15 (Free choice of occupation) | Recognition-decision-pace structural drag is the dominant blocker; bad fit-scoring narrows the candidate's option-set further | Friction-fit lens prioritises §16d-pathway employers; lateral-fallback in `journey.py` suggests Pflegehelferin trajectory if Pflegefachkraft is mismatch | Advisor maintains the operator-overridable employer-recognition-friendliness flag |
| Art. 21 (Non-discrimination) | National-origin + language-proficiency proxies in JD-language could disadvantage non-EU nurses | Bias-comparative-report 2026-05-21 measured aicha + anerkennung_friendly_clinical at SCORE 85 (deepseek) — within target band; the OOB rate of 13% applies cohort-wide, not specifically to aicha | Quarterly bias re-test against the deployer's actual case-load distribution |
| Art. 35 (Healthcare) | Indirect: surfacing Anerkennungs-friendly clinical employers accelerates time-to-clinical-deployment which serves public-health interest (DACH nursing shortage) | The cost-saving doctrine (`docs/grant/08-cost-saving-doctrine.md`) explicitly anchors here | Advisor tracks deployment-outcome for the deployer's case-load |
| Art. 41 (Good administration) | The §16d process itself is the deployer's adjacent-bureaucracy, not the project's; but the project's recognition-deadline-aware journey supports the candidate through it | Anerkennung-deadline countdown surface (Section 2.6 deliverable); §16d context in the cv_summary fed into AI prompts | Deployer DSGVO surface for the candidate's audit-log export (Art 20 + Art 86) |

## 4. R1–R8 risk modulation for Aïcha specifically

The template's project-level R1–R8 modulated for Aïcha's friction:

| Risk | Modulation for Aïcha | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | Friction-fit anchor + Aïcha+Anerkennungs-friendly verification gate (SCORE ≥ 75) keeps this LOW | L×M |
| R2 Language-based filtering | Aïcha's B1→B2 German is on the language-gate boundary; deployer must monitor JD language vs candidate proficiency mismatch closely | M×M |
| R3 Foreign-credential bias | §16d-explicit; the recognition decision letter is the gating fact, not the AI fit-score | L×M |
| R4 Scoring opacity | Per-criterion breakdown is critical here — Aïcha + advisor BOTH need to understand WHY a Anerkennungs-friendly role scored low | L×M |
| R5 Automation of consequential decisions | The structural confirmation gates are intact; the §16d-deadline pressure does NOT bypass them | VL×M |
| R6 Data-egress beyond consent | Aïcha's §16d status is high-sensitivity — deployer should restrict BYO-AI to EU-hosted Ollama OR explicitly consent the user to non-EU AI providers | L×M |
| R7 Compliance-pack misuse as shield | Project-side: this FRIA file's existence is the accountability evidence; deployer-side: the deployer's instantiation of it | L×L |
| R8 Drift as standards evolve | §16d AufenthG text could change; the deployer's quarterly review catches drift | M×L |

## 5. Top concern + compensating control

**Top concern**: R2 (language-based filtering) at residual M×M = 9. Aïcha at the B1→B2 boundary is exactly the cohort where a JD demanding C1 German would over-exclude despite Aïcha being clinically capable in workshop-floor and patient-interaction German.

**Compensating control**: the journey's `SCORE_LOCATION_LANGUAGE` criterion is bounded 0–25 (not all-or-nothing); the deployer's advisor reviews any low-fit on language alone before discouraging Aïcha from the application. The Article 22 right-to-human-review (`deployer-operating-manual.md` §8.1) is the user-side appeal path.

## 6. Article 22 escalation pathway for Aïcha

When Aïcha (or her MBE advisor) wants to appeal a specific AI output:
1. The MBE advisor (the deployer's oversight person) receives the escalation per the §8.1 procedure.
2. The audit-log entry ID is pulled to recover the exact prompt + model + provider + cost-cap context.
3. The advisor reviews against the §16d context the candidate is in.
4. The verdict + reasoning is communicated in French OR English (Aïcha's working languages); German DPO involvement is the deployer-side process.
5. The fact-of-review is logged via `/api/admin/oversight/review` so the Article 26(6) automatic-log obligation is honoured.
6. Aggregate quarterly review catches systemic patterns affecting Aïcha-class users.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`franfreeedo@gmail.com`) |
| Role | Sole maintainer + provider of the Helpmefindthejob AI system |
| Attestation date | 2026-05-24 |
| Scope | This per-persona FRIA template + the R1–R8 modulation table above + the Top-concern + the Article-22-pathway sections. Deployment-specific slots (affected-population numbers, oversight-person identity, German-DPO involvement) are deployer-fill-ins. |
| Pairs with | `compliance/gdpr-article-35-dpia.md` (GDPR side) + `compliance/fundamental-rights-impact-assessment-template.md` (project-level template) + `docs/persona-walks/aicha.md` (operational walk-through) |
