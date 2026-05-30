<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Yusuf (Turkey → Munich, EU Blue Card pending)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Yusuf** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-30.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `yusuf` |
| Cohort | most-acute migrant (primary anchor) |
| Origin → destination | Turkey → Munich |
| Profession | Mechanical engineer, 13 yrs in automotive supplier work (Bursa Tier-2 supplier to VW/Mercedes plants); BSc ITÜ Istanbul; ISO 9001 lead auditor |
| Residency status | EU Blue Card application in progress, supported by an employer offer at a Munich engineering firm (salary-threshold gated) |
| Languages | TR native; EN B2-business; DE A2 (learning) |
| Friction context | Has the offer; the friction is the *adjacent* navigation — comparing equivalent roles across Munich / Stuttgart / Ingolstadt, and the Anmeldung / Steuer-ID / Krankenkasse cascade in the first weeks |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[1]` + `docs/grant/07-personas.md` §2 + `docs/persona-walks/yusuf.md` |

## 2. Affected population

Yusuf-class users are non-EU credentialed engineers in active Blue Card application with a sponsoring offer. Typical scale at a Munich-area university career service or a sponsoring employer's relocation desk: 50–150 active alumni-pipeline + early-career international hires per advisor per semester. Vulnerability factors: first-months employer-switch rules under the Blue Card + salary-threshold gate (lower for shortage occupations like engineering, but still a gate) + language-gate (German A2 limits the non-English-team Munich automotive employers).

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Yusuf | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | A "low fit" verdict on a Blue-Card-friendly role that the candidate genuinely qualifies for communicates rejection at the EXACT moment the Blue Card processing window is most stressful | Per-criterion `SCORE_FRICTION_FIT` anchor scale awards 22+ for explicitly-Blue-Card-sponsorship JDs; lateral-fallback widens the option-set | Advisor reviews any high-spread cell (deepseek vs ollama) before showing the low end to the candidate |
| Art. 15 (Free choice of occupation) | Blue Card salary threshold structurally narrows the employer set; bad fit-scoring narrows it further | Lateral-engineering fallback (shipped 0.79.5) suggests adjacent roles (Manufacturing engineer / Process engineer) that satisfy the salary threshold | Advisor maintains the manufacturing-vs-specialist preference per Yusuf's own intent |
| Art. 21 (Non-discrimination) | National-origin + language-proficiency proxies; the German automotive sector has a historical default of German-only working language | Bias-comparative-report 2026-05-21 measured `yusuf + bluecard_automotive_engineer` at SCORE 90 (deepseek) / 75 (ollama) — a 15-point cross-provider spread that deepseek holds at/above the 75 verification gate (Yusuf's single largest spread is `yusuf_mixed_distant_city` at 21 points) | Deployer chooses the live provider per honesty-matrix |
| Art. 31 (Fair working conditions) | Indirect: the Blue Card system itself is the structural framework; the project does NOT mediate working-conditions disputes | Out-of-scope by design | n/a |
| Art. 41 (Good administration) | The Blue Card application is the deployer's adjacent-bureaucracy; the journey supports Yusuf through the months-1–3 timeline pacer | Post-arrival timeline + cross-city (Munich / Stuttgart / Ingolstadt) comparison surface | Deployer DSGVO export channel for audit-log slice on request |

## 4. R1–R8 risk modulation for Yusuf

| Risk | Modulation for Yusuf | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | Friction-fit + Blue-Card-pathway lens keeps this LOW for Munich automotive; Yusuf is a good case for the methodology | L×M |
| R2 Language-based filtering | Yusuf's German A2 means many Munich roles list "fluent German required" — over-exclusion risk; English-team alternative-suggestions surface helps | **M×M** |
| R3 Foreign-credential bias | Yusuf has a Turkish engineering degree (ITÜ); engineering degrees from EU-equivalent universities are generally auto-recognised, so the model must not auto-apply Anerkennung-friction logic to him | L×M |
| R4 Scoring opacity | Per-criterion breakdown helps Yusuf understand whether the score is salary-threshold-driven or skills-driven | L×M |
| R5 Automation of consequential decisions | Confirmation gates intact | VL×M |
| R6 Data-egress beyond consent | Yusuf's Blue Card status is less politically sensitive than asylum-stage, but he's still a non-EU candidate; deployer chooses provider scope | L×M |
| R7 Compliance-pack misuse as shield | The R7 logic applies to ANY persona — Yusuf is no exception | L×L |
| R8 Drift as standards evolve | The Blue Card salary threshold updates periodically (BMI); the deployer's quarterly review catches drift | M×L |

## 5. Top concern + compensating control

**Top concern**: R2 (language-based filtering) at residual M×M = 9. Yusuf's A2 German on the Munich automotive job board over-excludes from roles where the actual team-language is English. JD-language-policy parsing is keyword-only ("English-speaking team", "international working language"); a JD that says "team language is English in practice but we sometimes do meetings in German" doesn't trip the boost.

**Compensating control**: the deployer's career service / employer-relocation desk has direct relationships with Munich automotive HR; for high-fit roles where the JD is ambiguous about language, the advisor's intervention to confirm directly with the employer is a known workaround. Plus the Blue-Card-friendliness flag is operator-curated, not AI-derived.

## 6. Article 22 escalation pathway for Yusuf

The deployer-side advisor (e.g., a university career service such as TUM, or the sponsoring Munich employer's HR onboarding) is the oversight person. Escalation flows: AI output → advisor review against Yusuf's Blue Card + salary-threshold + language context → verdict (in EN or DE per Yusuf's preference) → log via `/api/admin/oversight/review`.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`support@helpmefindthejob.org`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA template + R1–R8 modulation + Top-concern + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `compliance/fundamental-rights-impact-assessment-template.md` + `docs/persona-walks/yusuf.md` |
