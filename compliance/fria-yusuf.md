<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Yusuf (Turkey → Stuttgart, EU Blue Card pending)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Yusuf** persona-class. PlanTowardPerfection box 2.10.4.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-24.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `yusuf` |
| Cohort | most-acute migrant (primary anchor) |
| Origin → destination | Turkey → Stuttgart |
| Profession | Mechanical engineer, 9 yrs in automotive R&D + manufacturing |
| Residency status | EU Blue Card pending (qualifies under §18b AufenthG; salary-threshold gate) |
| Languages | TR native; EN C1; DE A2 → B1 |
| Friction context | Blue Card requires a qualifying job offer at the BMI Blue-Card salary threshold; needs lateral-engineering fallbacks visible alongside specialist-track roles |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[1]` + `docs/persona-walks/yusuf.md` |

## 2. Affected population

Yusuf-class users are non-EU credentialed engineers in active Blue Card application. Typical scale at a TU career service: 50–150 active alumni-pipeline + early-career international graduates per advisor per semester. Vulnerability factors: contract-window pressure (~6 weeks Blue Card processing) + salary-threshold gate (€58,400 for shortage-occupations 2025) + language-gate (German A2-B1 limits non-English-team Stuttgart automotive employers).

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Yusuf | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | A "low fit" verdict on a Blue-Card-friendly role that the candidate genuinely qualifies for communicates rejection at the EXACT moment the Blue Card processing window is most stressful | Per-criterion `SCORE_FRICTION_FIT` anchor scale awards 22+ for explicitly-Blue-Card-sponsorship JDs; lateral-fallback widens the option-set | Advisor reviews any high-spread cell (deepseek vs ollama) before showing low-end to candidate |
| Art. 15 (Free choice of occupation) | Blue Card salary threshold structurally narrows the employer set; bad fit-scoring narrows it further | Lateral-engineering fallback (shipped 0.79.5) suggests adjacent roles (Manufacturing engineer / Process engineer) that satisfy the salary threshold | Advisor maintains the manufacturing-vs-specialist preference per Yusuf's own intent |
| Art. 21 (Non-discrimination) | National-origin + language-proficiency proxies; the German automotive sector has historical default of German-only working language | Bias-comparative-report 2026-05-21 measured `yusuf + bluecard_automotive_engineer` at SCORE 90 (deepseek) / 75 (ollama) — top-spread cell but above 75 verification gate when deepseek is used | Deployer chooses the live provider per honesty-matrix |
| Art. 31 (Fair working conditions) | Indirect: the Blue Card system itself is the structural framework; the project does NOT mediate working-conditions disputes | Out-of-scope by design | n/a |
| Art. 41 (Good administration) | The Blue Card application is the deployer's adjacent-bureaucracy; the journey supports Yusuf through the deadline pacer | Blue-Card-deadline countdown surface (Section 2.6 deliverable) | Deployer DSGVO export channel for audit-log slice on request |

## 4. R1–R8 risk modulation for Yusuf

| Risk | Modulation for Yusuf | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | Friction-fit + Blue-Card-pathway lens keeps this LOW for Stuttgart automotive; Yusuf is a good case for the methodology | L×M |
| R2 Language-based filtering | Yusuf's German A2 means many Stuttgart roles list "fluent German required" — over-exclusion risk; English-team alternative-suggestions surface helps | **M×M** |
| R3 Foreign-credential bias | Yusuf has a Turkish engineering degree; Anerkennung is not required (engineering degrees from EU-equivalent universities like Boğaziçi are auto-recognised); the model must not auto-apply Anerkennung-friction logic to him | L×M |
| R4 Scoring opacity | Per-criterion breakdown helps Yusuf understand whether the score is salary-threshold-driven or skills-driven | L×M |
| R5 Automation of consequential decisions | Confirmation gates intact | VL×M |
| R6 Data-egress beyond consent | Yusuf's Blue Card status is less politically sensitive than Aïcha's §16d, but he's still a non-EU candidate; deployer chooses provider scope | L×M |
| R7 Compliance-pack misuse as shield | The R7 logic applies to ANY persona — Yusuf is no exception | L×L |
| R8 Drift as standards evolve | Blue Card salary threshold updates annually (BMI); deployer's quarterly review catches drift | M×L |

## 5. Top concern + compensating control

**Top concern**: R2 (language-based filtering) at residual M×M = 9. Yusuf's A2 German on Stuttgart automotive job board over-excludes from roles where the actual team-language is English. JD-language-policy parsing is keyword-only ("English-speaking team", "international working language"); a JD that says "team language is English in practice but we sometimes do meetings in German" doesn't trip the boost.

**Compensating control**: the deployer's TU career service has direct relationships with Stuttgart automotive HR; for high-fit roles where the JD is ambiguous about language, the advisor's intervention to confirm directly with the employer is a known workaround. Plus the §16d/Blue Card residency-friendliness flag is operator-curated, not AI-derived.

## 6. Article 22 escalation pathway for Yusuf

The TU Berlin Career Service (or equivalent) is the deployer-side advisor. Escalation flows: AI output → advisor review against Yusuf's Blue Card + salary-threshold + language context → verdict (in EN or DE per Yusuf's preference) → log via `/api/admin/oversight/review`.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`franfreeedo@gmail.com`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA template + R1–R8 modulation + Top-concern + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `compliance/fundamental-rights-impact-assessment-template.md` + `docs/persona-walks/yusuf.md` |
