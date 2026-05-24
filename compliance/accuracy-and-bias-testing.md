<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

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

**As of 2026-05-19**: the methodology is documented and **partially executed** via synthetic-cohort interim runs (2 of 6 scenario classes; 147 data points covering 70 scoring + 70 CV-tailoring + 7 cross-industry probes). The four dated reports are in `docs/grant/bias-testing-*.md`. The standing 1020-test suite covers the deterministic-component accuracy (rule-based scoring, schema validation, locale parsing, encryption-at-rest). The remaining 4 scenario classes (onboarding, discovery, motivation-letter drafting, skill-gap brief) execute as part of the partner-NGO pilot in 2026 Q4 per [`ROADMAP.md`](../ROADMAP.md); results land in additional `docs/grant/bias-testing-<date>.md` reports.

The honest status: this document describes a methodology that is partially executed at synthetic-cohort scale and that will complete its remaining 4 scenario classes during the partner-NGO pilot. The methodology is the contract; the synthetic-interim results are documented in the dated bias-testing reports; the partner-NGO results are pending. We disclose the partial-execution gap in the transparency notice.

### 8.1 Cross-provider comparative results (2026-05-21 run)

A second run on 2026-05-21 layered cross-provider comparison on top of the synthetic-cohort coverage. The full report lives at [`docs/grant/bias-comparative-report-2026-05-21.md`](../docs/grant/bias-comparative-report-2026-05-21.md); the reproducible command sequence at the bottom of the report lets any deployer re-run it (replay-only by default, `--live` against their own provider keys).

**Coverage**: 7 personas × 10 scenarios × 2 providers = 140 data points. Providers exercised: `deepseek` (paid, cloud) and `ollama` (open-weights, local). The other 6 BYO-AI providers (openai, anthropic, gemini, openrouter, codex-cli, claude-code) were not exercised in this run — they are scheduled for the next release-gate run per the AI Provider Honesty Matrix at [`../docs/grant/15-ai-provider-honesty-matrix.md`](../docs/grant/15-ai-provider-honesty-matrix.md).

**Per-persona mean fit score (0–100), by provider**:

| Persona | deepseek | ollama | Spread |
|---|---|---|---|
| aicha | 56.4 | 62.2 | 5.8 |
| kaethe | 70.0 | 67.4 | 2.6 |
| mahmoud | 59.2 | 57.0 | 2.2 |
| maria | 58.9 | 60.1 | 1.2 |
| olga | 61.3 | 50.4 | 10.9 |
| tobias | 74.3 | 67.0 | 7.3 |
| yusuf | 59.9 | 52.6 | 7.3 |

**Top cross-provider disagreements** (the cells where providers scored a single scenario most differently): the largest spread was 30 points on `olga_mixed_distant_city` (deepseek=70, ollama=40), followed by 29 points on `olga_weak_wrong_industry_c` (34 vs 5), 22 points on `olga_weak_wrong_industry_b` and `tobias_weak_wrong_industry_a`. Full top-20 disagreement table in the report. The pattern is consistent: ollama scores the wrong-industry / distant-city scenarios harshly while deepseek scores them moderate-low. Both behaviours are defensible — they reflect different priors on transferability — but the spread is large enough that a single-provider deployment will bias the user-visible score in the provider's direction.

**Out-of-bounds (OOB) hit rate**: the prior 2026-05-19 polished cohort run (`docs/grant/bias-testing-2026-05-18-polish.md`, summarised in `04-research-and-decisions.md` Part B 2026-05-19 entry) measured **10 / 77 = 13.0%** scoring out-of-bounds (where the model's per-criterion sub-scores don't sum to the SCORE total, or where SCORE is outside the 0-100 range, or where the reason / gaps fields are malformed in a way the parser rejects). The 2026-05-21 comparative run did not re-measure this metric — it focused on cross-provider mean drift — so the **13.0% OOB rate stands as the most recent honest measurement** and is the figure cited in the transparency notice. PlanTowardPerfection Section 2.8 (search-quality + provider coverage) tracks driving this below 3% as a Ceiling-2 deliverable.

**Honest framing for reviewers and deployers**:

- The methodology is reproducible end-to-end. The data is checked into `data/bias_comparative_cache/` for replay; the run can be re-issued with `python -m scripts.bias_comparative_report --replay-only`.
- The 13.0% OOB rate is **not** the system's user-visible failure rate — the score-clamp (see `tests/test_prompt_injection_vectors.py::V3JdIndirectInjection`) catches out-of-range scores at the parser layer, so the user sees either a defensible score or "no fit score available" (depending on whether the OOB pattern was a value clamp or a regex miss). It is the methodology's flagged-rate for "AI output not in the expected canonical shape", which is a real quality metric for the AI provider but not a measure of harm reaching the user.
- The cross-provider spread on harsh-scenario cells is the more important reviewer-visible signal. A deployer choosing between providers should look at the per-persona mean delta + the top-disagreement table and pick the provider whose scoring profile best matches their oversight capacity.
- All of these numbers will move when the partner-NGO pilot runs the remaining 4 scenario classes; we will not retire this section's measurements until the partner-NGO scope has overwritten them.

---

## 9. Append log

- **2026-05-18**: methodology drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Pre-deployment re-test framework drafted. First scheduled execution: Week 3 partner-NGO pilot.
- **2026-05-24** (PlanTowardPerfection box 1.4.7): §8.1 added — cross-provider comparative results from the 2026-05-21 run (7 personas × 10 scenarios × 2 providers = 140 data points; per-persona mean scores deepseek vs ollama; top-spread disagreement summary; the 13.0% OOB rate carried forward from the 2026-05-19 polished cohort run with the honest-framing paragraph distinguishing OOB-rate-as-AI-output-quality-metric from user-visible-harm-rate). Cross-references the comparative report at `docs/grant/bias-comparative-report-2026-05-21.md` and the parser-layer defence at `tests/test_prompt_injection_vectors.py::V3JdIndirectInjection` so reviewers can see the chain from measurement to safety surface.
