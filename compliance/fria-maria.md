<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# FRIA — Maria (Spain → Munich, EU Blue Card, underemployed architect)

**Article**: AI Act Article 27. Instantiates the FRIA template for the **Maria** persona-class.
**Status**: project-side reference FRIA. Deployer instantiates with own context.
**Last updated**: 2026-05-24.

---

## 1. Persona identity + friction context

| Field | Value |
|---|---|
| Persona slug | `maria` |
| Cohort | most-acute migrant (primary anchor) |
| Origin → destination | Spain → Munich |
| Profession | Architect-by-training (Spanish license); currently drafter / Tekla + AutoCAD specialist |
| Residency status | EU citizen → EU Blue Card downshifted to Drafter role |
| Languages | ES + CA native; EN B2; DE A2 |
| Friction context | Underemployment — Spanish architect license + Architektenkammer registration pending; needs roles that preserve Blue Card eligibility while building toward licensure |
| Source-of-truth | `company_discovery/persona_fixtures.py::PERSONAS[4]` + `docs/persona-walks/maria.md` |

## 2. Affected population

Maria-class users are EU-mobile licensed professionals operating below licensure level in destination country. Typical scale at a Munich Bayerische Architektenkammer + AiP (Architekt-im-Praktikum) channel: 30–80 active candidates per advisor per year (smaller cohort but high-skill density). Vulnerability factors: Architektenkammer-registration pace (uncertain timeline; 9–24 months); Blue-Card-salary-threshold dependency; identity-tension between "drafter" and "architect" framing.

## 3. Charter of Fundamental Rights — engagement table

| CFR Article | Engaged how for Maria | Project mitigation | Deployer-side action |
|---|---|---|---|
| Art. 1 (Dignity) | The "downshifted-to-drafter" framing is itself a dignity-fragility area; AI outputs must preserve the architect-trajectory identity while honestly describing current role | The cv_summary names the Spanish architectural credentials + the Architektenkammer-registration-in-flight explicitly; the prompt scaffolds frame as "deep Tekla specialist with architect-class spatial reasoning" | Advisor reviews any low-fit on AiP-track roles |
| Art. 15 (Free choice of occupation) | The Architektenkammer-registration is the gating fact for architect-trajectory roles; bad fit-scoring narrows the option set | The Munich AiP-programme employer dataset (Auer Weber, Henn, Allmann Sattler Wappner) is curated; lateral fallback to drafter+BIM-coordinator preserves Blue Card eligibility | Quarterly bias re-run on Maria's adjacency cases |
| Art. 21 (Non-discrimination) | EU-internal mobility friction: Spanish architecture-school equivalence + Architektenkammer registration pace is the structural factor | The cross-credential cv-summary framing helps; advisor relationship with Bayerische Architektenkammer surfaces the equivalence pace | Advisor maintains AiP-programme-friendly employer list |
| Art. 31 (Fair working conditions) | Underemployment dignity-fragility area; "Maria works as drafter while licensed as architect" — the project's role is to surface the architect-trajectory roles, NOT to mediate the broader underemployment issue | Out-of-scope mediation; in-scope surface of architect-trajectory roles | n/a |
| Art. 41 (Good administration) | The Architektenkammer registration IS a deployer's adjacent-bureaucracy; the project could track the registration-pace deadline (Section 2.6 deferred deliverable — credentials-equivalence lookup) | Maintainer-side tracking of Bayerische Architektenkammer typical registration windows | Deployer advisor proactively pulls Architektenkammer status updates |

## 4. R1–R8 risk modulation for Maria

| Risk | Modulation for Maria | Residual |
|---|---|---|
| R1 Discrimination in fit scoring | EU-internal mobility friction is well-recognised; the friction-fit scale honours the AiP-pathway anchor | L×M |
| R2 Language-based filtering | Maria's DE A2 limits her to Munich English-team architecture firms; the JD-language-policy parser detects this for top-tier firms with documented international programmes | L×M |
| R3 Foreign-credential bias | Spanish architect license IS subject to Architektenkammer review; the model recognises "in-flight" status and recommends preserving Blue Card while waiting | L×M |
| R4 Scoring opacity | Per-criterion breakdown helps Maria understand whether the score reflects credentials-equivalence concerns or fit-genuine concerns | L×M |
| R5 Automation | Confirmation gates intact | VL×M |
| R6 Data-egress | Maria's status (EU Blue Card downshift) is less sensitive than asylum-stage; standard data-egress disciplines apply | L×M |
| R7 Compliance-pack-as-shield | Standard | L×L |
| R8 Drift | Bayerische Architektenkammer practice + Spanish architect-degree equivalence list updates periodically | M×L |

## 5. Top concern + compensating control

**Top concern**: R4 (scoring opacity) at residual L×M for Maria. The risk: Maria sees a low fit-score on an AiP role and interprets it as "I'm not architect enough" — a dignity-impact specific to underemployed professionals — when the real driver might be a salary-threshold or location filter.

**Compensating control**: the per-criterion breakdown surface (already shipped) IS the mitigation; Maria can see whether the low score is salary or language or credentials-equivalence. The Article 22 right-to-human-review is the user-side appeal path.

## 6. Article 22 escalation pathway for Maria

Munich Bayerische Architektenkammer advisor OR the deployer's AiP-programme-coordinator receives escalation. Communication in ES OR EN OR DE per Maria's preference. The Architektenkammer-registration-status is a deployer-adjacent record; the advisor pulls it as part of the appeal review.

## 7. Maintainer attestation

| Field | Value |
|---|---|
| Attested by | Fouad, project maintainer (`franfreeedo@gmail.com`) |
| Role | Sole maintainer + provider |
| Attestation date | 2026-05-24 |
| Scope | Per-persona FRIA + R1–R8 modulation + Top-concern (R4 scoring opacity) + Article-22 path |
| Pairs with | `compliance/gdpr-article-35-dpia.md` + `compliance/fundamental-rights-impact-assessment-template.md` + `docs/persona-walks/maria.md` |
