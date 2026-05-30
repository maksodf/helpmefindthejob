<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Olga (Ukraine → Leipzig, §24 protection)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Olga** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-30.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `olga` |
| Cohort | most-acute migrant (primary anchor) |
| Origin → destination | Ukraine → Leipzig |
| Profession | Senior frontend developer (React, TypeScript), 9 yrs at a Kyiv startup |
| Residency status | §24 AufenthG (temporary protection — Ukraine displaced-persons directive) |
| Languages | UK + RU native; EN C1; DE A2-conversational |
| Friction context | Clean residency + work-permit; the labor market reads "Ukrainian refugee" before reading her CV, and the host-language gate compounds it — English-team + remote-EU tech employers are the target market |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[2]` + `docs/grant/07-personas.md` §3 + `docs/persona-walks/olga.md` |

## 2. Affected population

Olga-class users are Ukrainian-displaced senior IC engineers / designers / PMs with §24 status. Typical scale at a Leipzig NGO + IQ-Netzwerk Saxony office: 100–250 active clients per advisor per year (the §24 displaced-persons cohort is regionally concentrated). Vulnerability factors: war-stress + single-parent constraints; language-gate (DE A2 vs German tech employers' historical default of German-only); §24-to-permanent-residency pathway uncertainty.

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Olga | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | Olga is a senior IC engineer; a low fit-score that misreads her seniority as junior (gap between Ukrainian title conventions and German hierarchical mapping) is a dignity violation at the seniority-band level | The cv_builder captures seniority via a structured field (`senior` vs `mid` vs `tech-lead-adjacent`); the prompt scaffolding respects it | Advisor reviews any title-translation mismatch |
| Art. 14 (Right to education) | The language-gate friction couples to language-course pairing; right-to-education engages when the deployer routes Olga to VHS / Goethe / state-sponsored courses | The journey surfaces language-course pairing as a Section 2.6 deferred deliverable; until then the deployer surfaces it manually | Deployer maintains course-catalogue list for Leipzig + Saxony |
| Art. 15 (Free choice of occupation) | §24 protection allows full work without restriction; the AI must not under-rank Olga because of the §24 marker | The friction-fit scale anchors for §24 + senior-IC as "neutral-positive" not "high-friction" | Quarterly bias re-run should test §24 + tech-senior cells specifically |
| Art. 21 (Non-discrimination) | National-origin + language; the gap between Ukrainian-native and DE-A2 is the discrimination vector | Bias-comparative-report measured aspects of Olga's cohort; some scenarios show cross-provider disagreement (deepseek=70 vs ollama=40 on `olga_mixed_distant_city`) | Provider choice matters here; deepseek scores Olga's harsh-cohort scenarios less harshly |
| Art. 33 (Family + professional life) | Olga is a single mother with a 7-year-old in a German Grundschule; remote-friendly or predictable-hours roles preserve childcare | Remote-EU JD prioritisation lens; the friction-fit scale awards for "international working language" + "remote-EU compatible" | Advisor confirms Olga's remote-vs-on-site preference given childcare |
| Art. 18 (Right to asylum / temporary protection) | §24 is the temporary-protection legal basis; the project does NOT mediate refugee-status disputes | Out-of-scope by design | n/a |

## 4. R1–R8 risk modulation for Olga

| Risk | Modulation for Olga | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | Cross-provider spread on harsh-cohort scenarios IS concerning; deepseek (mean 61.3) scores Olga's cohort less harshly than ollama (mean 50.4) and is the safer default per the comparative report | **M×M** |
| R2 Language-based filtering | Olga's DE A2 + English-team JD-keyword-only-detection misses "team language EN in practice" JDs | **M×M** |
| R3 Foreign-credential bias | Olga's Ukrainian CS background is not an Anerkennung-friction case; the model must NOT auto-apply Anerkennung-friction to her | L×M |
| R4 Scoring opacity | Per-criterion breakdown is critical for Olga to understand whether the score is language-gated or skills-gated | L×M |
| R5 Automation | Confirmation gates intact | VL×M |
| R6 Data-egress | §24 status is documented in profile; deployer should restrict BYO-AI provider scope to keep this off non-EU providers | L×M |
| R7 Compliance-pack-as-shield | The §24 status is sensitive but the project's discipline applies uniformly | L×L |
| R8 Drift | §24 + the Ukraine TPD extension framework is politically dynamic; deployer's quarterly review catches drift | **M×L** |

## 5. Top concern + compensating control

**Top concern**: combined R1 + R2 (cross-provider disagreement on harsh-cohort cells + language-gate over-exclusion) gives Olga the **highest cross-provider disagreement** of the seven personas in the comparative report — a 30-point spread on `olga_mixed_distant_city` (deepseek=70, ollama=40), the report's single largest disagreement cell.

**Compensating control**: the deployer's choice of `deepseek` over `ollama` for the Olga cohort; advisor reviews any score-spread > 20 points; the Article 22 right-to-human-review is the user-side appeal path. The §2.8 search-quality fixes (JD-language-policy parser improvement) will close part of R2 in the next round.

## 6. Article 22 escalation pathway for Olga

A Leipzig Ukrainian-cohort NGO or IQ-Netzwerk Saxony advisor receives escalation. The communication can be in EN or UK (per Olga's preference); German DPO involvement is the deployer-side process. Especially important: if the AI under-ranked a remote-EU role Olga is qualified for, the appeal must escalate to recovery (not just denial).

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`support@helpmefindthejob.org`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA + R1–R8 modulation + Top-concern (highest cross-provider disagreement of the cohort) + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `docs/persona-walks/olga.md` + `docs/grant/bias-comparative-report-2026-05-21.md` (Olga rows) |
