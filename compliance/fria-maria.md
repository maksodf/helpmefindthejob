<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Maria (Romania → Stuttgart, EU citizen, language-gated nurse)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Maria** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-30.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `maria` |
| Cohort | most-acute migrant / EU-mobile (primary anchor) |
| Origin → destination | Romania → Stuttgart |
| Profession | Krankenschwester (registered nurse), trained Romania 1991; 28 years hospital experience, then elderly home-care |
| Residency status | EU citizen (Freizügigkeitsrecht under §2 FreizügG/EU) — no permit needed |
| Languages | RO + HU native; IT B1 (one year in Italy, 2015); DE A2 |
| Friction context | Full legal work rights, but the host-language gate is the dominant friction: most Pflegedienst employers demand B1 formally, and Maria (age 52, widowed) cannot demonstrate her clinical quality through a German-language interview |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[4]` + `docs/grant/07-personas.md` §5 + `docs/persona-walks/maria.md` |

## 2. Affected population (per the deployer's deployment)

Maria-class users are EU-citizen, qualified care/health professionals operating below their qualification level in the destination country because of a language gate, not a legal one. Typical scale at a Stuttgart Wohlfahrtsverband Pflege-integration channel (Caritas / AWO / DRK Altenpflege coordination): 40–100 active candidates per advisor per year. Vulnerability factors: age (older workers face documented re-entry bias) + language-gate (DE A2 vs the B1 most home-care employers formally require) + sole-income widowhood + sectoral pressure (the Pflege shortage means demand exists but is language-gated at the interview).

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Maria specifically | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | A "low fit" verdict that reads Maria's A2 German as low professional competence erases 28 years of excellent clinical care — a dignity harm to an experienced nurse reduced to a language test | Per-criterion scoring separates `SCORE_LOCATION_LANGUAGE` from `SCORE_SKILLS`/`SCORE_EXPERIENCE`, so language friction does not silently sink a strong-experience candidate; AI-output framing is "suggestion, not decision" | Advisor reviews any low-fit driven by the language sub-score before discouraging Maria from applying |
| Art. 15 (Free choice of occupation) | Maria has full EU work rights; it is the language gate, not the law, that narrows her from Krankenschwester-level roles toward the Altenpflegehelferin track | The friction-fit lens prioritises Pflegedienst employers who integrate non-fluent carers; lateral framing surfaces both full-Pflegefachkraft and Altenpflege roles so the choice stays hers | Advisor maintains the operator-overridable language-integration-friendly employer flag |
| Art. 21 (Non-discrimination) | Language-proficiency proxy **plus age** (52): older non-native speakers face a documented double bind in German Pflege recruiting | Bias-comparative-report 2026-05-21 measured Maria's deepseek mean fit-score at 58.9; the language-friendly scenario `language_friendly_pflegedienst` scores 86 (deepseek) while `maria_mixed_language_barrier` scores 53 (deepseek; "C1 required vs A2 actual") — the model rewards integration-friendly employers and penalises the language gate, which is the behaviour to monitor | Quarterly bias re-test against the deployer's actual case-load, watching age + language interaction |
| Art. 35 (Healthcare) | Indirect-positive: Maria is supply to the acute German elderly-care shortage; surfacing language-friendly Pflegedienst employers accelerates a qualified carer into the sector | The cost-saving doctrine (`docs/grant/08-cost-saving-doctrine.md`) anchors here — language-integration matching reduces sectoral vacancy cost | Deployer tracks placement outcomes for the Pflege case-load |
| Art. 41 (Good administration) | The Anerkennung of Maria's Romanian nursing diploma for full Krankenpflege practice (vs. the easier Altenpflegehelferin track) is the deployer's adjacent bureaucracy; the journey supports her through it without pretending to adjudicate it | Anerkennung status captured in the `cv_summary` so AI prompts frame her as a 28-year RN seeking recognition, not as uncredentialed | Deployer DSGVO surface for the candidate's audit-log export (Art 20 + Art 86) |

## 4. R1–R8 risk modulation for Maria specifically

The template's project-level R1–R8 modulated for Maria's friction:

| Risk | Modulation for Maria | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | 28 years of clinical experience scores strongly on skills/experience sub-scores; the deepseek mean of 58.9 reflects the language drag, not a skills penalty | L×M |
| R2 Language-based filtering | Maria's DE A2 against home-care JDs that formally demand B1 is the dominant over-exclusion risk; `maria_mixed_language_barrier` at 53 (deepseek) shows the gate biting | **M×M** |
| R3 Foreign-credential bias | The Romanian RN diploma needs Anerkennung for full Krankenpflege, but the Altenpflegehelferin entry works without it; the model must NOT treat an EU-trained RN as uncredentialed | L×M |
| R4 Scoring opacity | Per-criterion breakdown is critical so Maria sees whether a low score is language-driven or fit-driven, not "you are not a good enough nurse" | L×M |
| R5 Automation of consequential decisions | The structural confirmation gates are intact; the language sub-score never auto-rejects | VL×M |
| R6 Data-egress beyond consent | Maria is an EU citizen; her data is less sensitive than asylum-stage status, but standard BYO-AI provider-scope discipline applies | L×M |
| R7 Compliance-pack misuse as shield | Project-side: this FRIA file's existence is the accountability evidence; deployer-side: the deployer's instantiation of it | L×L |
| R8 Drift as standards evolve | EU-mobility recognition rules + Pflege-integration Förderung programmes change; the deployer's quarterly review catches drift | M×L |

## 5. Top concern + compensating control

**Top concern**: R2 (language-based filtering) at residual M×M = 9. Maria is exactly the cohort where a Pflegedienst JD demanding B1/C1 German over-excludes despite 28 years of excellent clinical practice, because A2 German cannot showcase that competence in a written application or interview.

**Compensating control**: the journey's `SCORE_LOCATION_LANGUAGE` criterion is bounded 0–25 (not all-or-nothing), so a language gap reduces but does not zero the fit; the `language_friendly_pflegedienst` scenario (deepseek = 86) confirms the model rewards employers who integrate non-fluent carers; the deployer's advisor reviews any low-fit on language alone before discouraging the application; the Article 22 right-to-human-review (`deployer-operating-manual.md` §8.1) is the user-side appeal path.

## 6. Article 22 escalation pathway for Maria

When Maria (or her Pflege-integration advisor) wants to appeal a specific AI output:
1. The Stuttgart Wohlfahrtsverband Pflege-integration advisor (the deployer's oversight person) receives the escalation per the §8.1 procedure.
2. The audit-log entry ID is pulled to recover the exact prompt + model + provider + cost-cap context.
3. The advisor reviews against Maria's actual clinical record and the language-integration friendliness of the target employer.
4. The verdict + reasoning is communicated in Romanian OR Italian OR simplified German (Maria's working languages).
5. The fact-of-review is recorded in the deployer's oversight log (the in-app `/api/admin/oversight/queue` surfaces the underlying audit events read-only; a dedicated review-logging endpoint is a Phase-2 item) so the Article 26(6) obligation is honoured.
6. Aggregate quarterly review catches systemic patterns affecting Maria-class users (age + language interaction).

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`support@helpmefindthejob.org`) |
| Role | Sole maintainer + provider of the Helpmefindthejob AI system |
| Attestation date | 2026-05-24 |
| Scope | This per-persona FRIA + the R1–R8 modulation table above + the Top-concern (R2 language-based filtering) + the Article-22-pathway section. Deployment-specific slots (affected-population numbers, oversight-person identity, German-DPO involvement) are deployer-fill-ins. |
| Pairs with | `compliance/gdpr-article-35-dpia.md` (GDPR side) + `compliance/fundamental-rights-impact-assessment-template.md` (project-level template) + `docs/persona-walks/maria.md` (operational walk-through) |
