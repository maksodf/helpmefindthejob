<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Accuracy and Bias Testing

**Audience**: provider, deployer, and any external reviewer assessing whether the system's accuracy and bias profile is appropriate for high-risk-AI deployment.
**Article**: AI Act Article 15 (accuracy, robustness, cybersecurity).
**Status**: living document. Updated on every major release and on every bias-testing methodology re-run.

---

## 1. Why this is anchored to the persona panel

Article 15 requires an "appropriate level of accuracy" and explicitly requires that bias be detected and mitigated. A generic test corpus would tell us very little: a system that scores random pairs of CVs and job postings consistently is not the system we shipped. The system we shipped scores **specific situations** — a Tunisian-trained nurse navigating Anerkennung, a Ukrainian frontend developer matched to English-team-led roles, a German nurse returning to clinical practice after twelve years caregiving, a German backend developer pivoting from commercial to civic-tech. The accuracy and bias of the system on those situations is what matters.

The persona panel ([`../docs/grant/07-personas.md`](../docs/grant/07-personas.md)) is the test-cohort surface for the bias-testing methodology. Each persona represents a structurally distinct friction case. The methodology runs each persona through the canonical journey and compares system outputs against documented expectations.

**Crucially**: the cohort includes the two wider-friction-class personas (Käthe, Tobias) alongside the five most-acute-use-case personas (Aïcha, Yusuf, Olga, Mahmoud, Maria). Per Decision 21, the architecture is friction-driven not demographic-driven; the bias-testing follows the same shape. A bias-testing methodology that only tested the migrant subset would (a) fail to surface biases against the wider friction class and (b) fail to demonstrate the architectural claim. The seven-persona cohort closes both gaps.

---

## 2. Methodology

### 2.1 Inputs

For each persona, the methodology constructs a **synthetic-but-realistic profile** matching the persona's documented situation:

- Profession, years of experience, ESCO-mapped skills
- Residency / work-rights status
- Language levels (CEFR-graded)
- Friction-class details (Anerkennung in progress / EU citizen with language barrier / Wiedereinstieg context / sector pivot / etc.)
- Geographic context (Berlin / Munich / Leipzig / Hamburg / Stuttgart for the migrant five; Berlin / Hamburg for Käthe / Tobias)

The synthetic profiles are committed to `tests/fixtures/personas/` (Week 2 task 2.8 follow-up) and re-used across test runs to make changes detectable.

### 2.2 Test scenarios per persona

Each persona is run through:

1. **Onboarding** — profile capture via the chat router, persona-ranking initialisation.
2. **Discovery** — job-board fan-out, persona-friendly filter application.
3. **Scoring** — fit-scoring of a curated set of jobs (10 per persona) covering: strong-fit jobs (expected score >75), weak-fit jobs (expected score <40), edge-case jobs (recognition-friendly employer, English-team-led tech role, Wiedereinstieg programme, TVöD public-sector role, etc.).
4. **CV tailoring** — proposed edits for the strongest-fit job; manual review against documented expectations.
5. **Motivation-letter drafting** — first-draft generation; manual review for accuracy of CV-grounding and absence of hallucinated facts.
6. **Skill-gap brief** — comparison of persona skills to a target occupation's ESCO skills.

### 2.3 Comparison axes

Outputs are compared on three axes:

- **Within-persona accuracy**: does the system's output for this persona match the documented expectation for the persona? Examples: does Aïcha's fit score for an Anerkennung-friendly Pflegedienst exceed 75? Does Olga's fit score for an English-team-led React role exceed 80?
- **Cross-persona equivalence (most-acute-class)**: do equivalent-capability scoring outcomes hold across the five most-acute personas? Examples: does Aïcha's score for a German hospital match Maria's score for a Pflegedienst with comparable role spec? Does Mahmoud's score for a Handwerk Ausbildung match a hypothetical German-native-apprentice's score for the same role within tolerance?
- **Cross-class equivalence (most-acute vs wider-friction)**: do equivalent-capability scoring outcomes hold between the most-acute and wider-friction-class personas? Examples: does Aïcha's score for an Anerkennung-friendly hospital match Käthe's score for a Wiedereinstieg-programme hospital with comparable role spec? Does Olga's score for an English-team React role match Tobias's score for an English-team civic-tech role with comparable seniority?

A divergence outside documented tolerance on any axis is a bias signal that triggers investigation per [`risk-management-plan.md`](risk-management-plan.md) §3 (R1).

### 2.4 Tolerance bands

| Comparison | Acceptable tolerance | Rationale |
|---|---|---|
| Within-persona vs documented expectation | ±10 fit-score points | The fit-score scale is 0–100; ±10 reflects normal AI re-ranking variance. |
| Cross-persona equivalence within most-acute class | ±15 fit-score points | The most-acute class has structurally different friction shapes; some divergence is legitimate. |
| Cross-class equivalence (most-acute vs wider-friction) | ±15 fit-score points | Same logic — different friction shapes legitimately produce different scores; bias is when same-capability scores diverge **systematically** in one direction. |

A single test divergence outside tolerance is investigated; a pattern of divergences (e.g., the wider-friction-class personas consistently scoring 10–15 points higher than the migrant personas for comparable roles, suggesting an AI training-corpus bias toward German-native phrasing) is a Sev-2 incident.

### 2.5 Documentation of the run

Each bias-testing run produces a structured report committed to `docs/grant/bias-testing-<date>.md` with:

- Date and AI provider
- Per-persona, per-scenario results table
- Divergences identified and remediation status
- AI-provider config (model, temperature, prompt-template ID)
- Summary statistics (mean / median / std-dev of fit scores per persona)

The report is public (in the open-source repo) so that any reviewer — supervisory authority, partner NGO, academic researcher — can assess the methodology.

---

## 3. Pre-deployment re-test (deployer obligation)

Before going live, the deployer runs the bias-testing methodology against their chosen AI provider configuration. The test set may be the canonical seven-persona cohort or an extended cohort that includes the deployer's specific population.

**How to run**:

```bash
# Inside the deployment environment, with the configured AI provider:
python3 -m unittest tests.test_bias_methodology
```

The standard test suite (`tests/test_bias_methodology.py`, lands as part of §2.8 follow-up) generates a fresh report and asserts that the divergence-from-tolerance count is below the deployment threshold.

If the test fails, the deployer:

1. Reviews the divergence details.
2. Adjusts AI provider or prompt-template configuration if a tuning issue is identified.
3. Re-runs the test.
4. If the divergence persists, escalates to the provider via a GitHub Issue tagged `bias-report`.

---

## 4. Accuracy metrics

### 4.1 Fit-scoring accuracy

The fit-scoring algorithm has two components:

1. **Structured rule-based scoring** (deterministic): expected accuracy is verified by unit test against documented rules.
2. **AI re-ranking adjustment** (bounded ±15%): expected to track human-judgement re-ranking within ±10 fit-score points.

Both components are tested as described in §2.

### 4.2 CV-tailoring quality

Measured qualitatively against the documented persona expectations:

- Does the tailoring suggestion reflect actual CV facts (not hallucinated)?
- Does the tailoring reflect the role's documented requirements?
- Does the tailoring respect the persona's CV-style conventions (Bewerbungsmappe for Ausbildung context, German Lebenslauf for Festanstellung context, etc.)?

Pass/fail per scenario; aggregate pass rate is reported.

### 4.3 Motivation-letter quality

Measured qualitatively against:

- Grounding in user-confirmed CV bullets (no hallucinated facts)
- Tone-appropriateness for the sector (clinical-German for nursing, TVöD-conventional for public-sector tech, Handwerk-conventional for trades, etc.)
- Length-appropriateness (a German motivation letter is typically one page; over-long drafts are a failure mode)

Pass/fail per scenario; aggregate pass rate is reported.

### 4.4 Application-outcome analysis accuracy

Measured against synthesised user histories where the "true" pattern is known:

- Does the system correctly identify the strongest-performing CV variant?
- Does the system correctly identify sector-response asymmetries?
- Does the system avoid over-claiming patterns from small samples?

The over-claiming test is particularly important: a 5-application sample should not produce strong pattern claims; the system should explicitly flag insufficient data.

---

## 5. Robustness

Robustness is the property of the system maintaining accuracy under perturbation.

### 5.1 AI-provider failover

When the configured AI provider is unavailable, the system falls back to deterministic templates and logs a `system_event` with `system_event_kind="ai_provider_unavailable"`. Tested in `tests/test_phase11_mcp_tools_v2.py` and in the existing `ai_providers` test surface.

### 5.2 Malformed input handling

Every MCP tool's `inputSchema` is validated before dispatch. Schema-failing inputs return an RFC 7807 Problem Details response with the violation. Tested in `tests/test_phase11_mcp_input_validation.py` and `tests/test_phase12_mcp_integration_e2e.py`.

### 5.3 Locale parsing edge cases

Yes/no parsing accepts a documented set of locale-specific synonyms (German `ja/nein` plus `klar`, `passt`, `ne`, etc.; English `yes/no` plus `sure`, `yep`, `nope`). Edge cases are tested in `tests/test_phase11_locale_parser.py`.

### 5.4 Encryption-at-rest integrity

The AEAD ciphertext detects tampering via the Poly1305 MAC. Fuzz-tested in `tests/test_aead_fuzzing.py`.

---

## 6. Cybersecurity

Cross-references [`../SECURITY.md`](../SECURITY.md) for the project's security policy. Article 15-relevant controls:

- TLS for all production traffic (Caddy auto-managed certificates).
- Session management with idle timeout and 2FA support.
- Encryption-at-rest for profile data and TOTP secrets.
- Vulnerability disclosure via `.well-known/security.txt` (RFC 9116).
- Dependency scanning (`pip-audit`) in CI — Week 3 expansion.
- Audit log itself protected by file-system permissions on the deployer's host; PII-hashed by default.

---

## 7. Performance ratios (cost-saving claim grounding)

The cost-saving doctrine claims certain efficiency improvements per advisor visit. The metrics that ground each claim:

| Claim | Metric | Source |
|---|---|---|
| 20 minutes of routine work absorbed per advisor session | Median time spent on the journey phases the agent handles (profile capture, CV format guidance, fit-scoring, application drafting) | Pilot data from Week 3 partner-NGO collaboration |
| 33% advisor caseload capacity expansion | Derived from the 20-minutes-out-of-60-minutes absorption ratio | Same |
| 30-day reduction in time-to-employment | Self-reported by pilot participants vs comparison cohort | Same |
| €30–200k AI-Act-compliance saving for deployer | Avoidance of external consultant fees at typical EU rates for high-risk-AI compliance engineering | Industry benchmarks; tagged `plausible` in [`../docs/grant/08-cost-saving-doctrine.md`](../docs/grant/08-cost-saving-doctrine.md) §"Mechanism 5" |

Each claim is tagged `proven` / `plausible` / `aspirational` in the cost-saving doctrine document. The accuracy-and-bias methodology feeds the "proven" column as pilot data lands.

---

## 8. Current results

**As of 2026-05-18**: the methodology is documented but **not yet executed** at full scale. The standing 994-test suite covers the deterministic-component accuracy (rule-based scoring, schema validation, locale parsing, encryption-at-rest). The AI-component bias-testing methodology is scheduled for execution as part of Week-3 partner-NGO pilot collaboration; results land in `docs/grant/bias-testing-<date>.md` reports.

The honest status: this document describes a methodology committed to before its full execution at scale. The methodology is the contract; the results are pending. We disclose the gap in the transparency notice ("the system's bias profile is being tested in partner-NGO collaboration; preliminary results due Week 3 of the grant sprint").

---

## 9. Append log

- **2026-05-18**: methodology drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Pre-deployment re-test framework drafted. First scheduled execution: Week 3 partner-NGO pilot.
