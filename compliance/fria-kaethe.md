<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Käthe (Munich, Wiedereinsteigerin, 12-year caregiving gap)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Käthe** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-24.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `kaethe` |
| Cohort | wider friction-class (architectural demonstration per Decision 21) |
| Origin → destination | Munich → Munich (no migration) |
| Profession | Registered nurse pre-gap (Krankenschwester certified 2010); 12-year caregiving sabbatical concluded |
| Residency status | EU citizen (German national) |
| Languages | DE native; EN B1 |
| Friction context | 12-year career gap; need for Wiedereinstiegsprogramme that bridge currency-gap without treating her as junior |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[5]` + `docs/persona-walks/kaethe.md` |

## 2. Affected population

Käthe-class users are EU-citizen returners after extended caregiving / parental absence. Typical scale at a Bayerischer Wohlfahrtsverband returner-network + Klinikum HR Wiedereinstiegs-coordination: 40–100 active candidates per coordinator per year. Vulnerability factors: implicit age + gender bias against women returning after caregiving; clinical-currency-gap anxiety; part-time-shift coupling to childcare obligations.

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Käthe | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | The 12-year gap is THE dignity-fragility area; AI outputs must frame the gap positively (caregiving = continuous-skill maintenance) not as a deficiency | The cv_summary frames the gap as "primary-caregiving sabbatical concluded; intensive 2026 update via Bayerische Pflegeakademie refresher course; ready for clinical re-entry"; the Anschreiben prompt steers against apologetic framing | Advisor reviews any score that appears to penalise the gap |
| Art. 15 (Free choice of occupation) | Käthe is licensed; the question is currency-update, not credentials. AI must distinguish "needs Wiedereinstieg programme" from "lacks certification" | The friction-fit scale awards 22+ for Wiedereinstiegs-programme-explicit JDs (Wiedereinsteigerin / Wiedereinstiegspflege / Mentor-Programm) | Deployer maintains Munich + Bavaria Wiedereinstiegs-programme employer list |
| Art. 21 (Non-discrimination) | **HIGH** — age + gender; the German nursing labour market has documented bias against women returning after caregiving (per Bertelsmann Stiftung reports). Käthe is the persona where Art 21 is most-engaged | Bias-comparative-report shows Käthe at mean SCORE 70.0 (deepseek) — among the highest in the cohort, reflecting good architectural fit | Quarterly bias re-run with Käthe-class as a specific monitored cohort |
| Art. 23 (Equality between women and men) | Wiedereinstieg is structurally gendered (women bear disproportionate caregiving burden); the project's recognition of Wiedereinstieg as a friction-class IS the structural mitigation | The seven-persona panel includes Käthe specifically to surface this | Deployer's gender-equality officer reviews aggregate outcomes |
| Art. 32 (Prohibition of child labour) | n/a (out-of-scope) | n/a | n/a |
| Art. 33 (Family + professional life) | Direct — Käthe's re-entry IS family-and-professional-life integration; part-time + flexible-shift JDs preserve this | The discover-review surface flags part-time / flexible-shift roles | Advisor verifies part-time-conversation-openness with employers where JD-language is rigid |
| Art. 41 (Good administration) | The Pflegeakademie refresher course IS deployer-adjacent administration; the project could surface the refresher-course catalogue (Section 2.6 deferred) | Currently maintainer-side recommendation; deployer-side credentials-currency module is the long-term home | Deployer maintains regional Pflegeakademie catalogue |

## 4. R1–R8 risk modulation for Käthe

| Risk | Modulation for Käthe | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | The 12-year gap is the dignity-fragility surface; AI must NOT over-penalise based on gap length; the friction-fit anchor scale awards Wiedereinstiegs-explicit JDs at 22+ | M×M |
| R2 Language-based filtering | Käthe is DE-native; n/a | VL×L |
| R3 Foreign-credential bias | n/a (Käthe is German-credentialed) | VL×L |
| R4 Scoring opacity | Per-criterion breakdown helps Käthe distinguish "gap-penalty" from "fit-issue" | L×M |
| R5 Automation | Confirmation gates intact | VL×M |
| R6 Data-egress | Käthe's data is less sensitive than asylum-stage; standard data-egress disciplines apply | L×L |
| R7 Compliance-pack-as-shield | Standard | L×L |
| R8 Drift | Wiedereinstiegs-programme funding (BMFSFJ / Land-level) updates periodically | M×L |

## 5. Top concern + compensating control

**Top concern**: combined Art 21 + Art 23 (non-discrimination + women-equality) is a societal-level concern beyond the project's direct controls. The risk: AI fit-scoring trained on prior hiring data reflects past hiring bias against women returning after caregiving.

**Compensating control**: the friction-fit anchor scale explicitly awards Wiedereinstiegs-programme JDs at 22+; the deployer's quarterly bias re-run includes Käthe-class as a specific monitored cohort; the advisor reviews any pattern of low-fit on Wiedereinstiegs-friendly roles. The "what felt broken" notes at `docs/persona-walks/kaethe.md` document the residual roughnesses.

## 6. Article 22 escalation pathway for Käthe

Bayerischer Wohlfahrtsverband returner-network coordinator OR Klinikum Wiedereinstiegs-coordinator receives escalation. Communication in DE. The Pflegeakademie refresher-course-completion-date is a deployer-adjacent record; the advisor pulls it as part of the appeal review.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`franfreeedo@gmail.com`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA + R1–R8 modulation + Top-concern (Art 21 + Art 23 societal-bias surface) + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `compliance/fundamental-rights-impact-assessment-template.md` + `docs/persona-walks/kaethe.md` |
