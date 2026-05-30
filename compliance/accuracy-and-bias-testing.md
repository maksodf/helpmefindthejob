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

The synthetic profiles are defined in [`../company_discovery/persona_fixtures.py`](../company_discovery/persona_fixtures.py) (the `PERSONAS` cohort) and re-used across test runs to make changes detectable.

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

Each bias-testing run produces a structured report (the interim dated reports were consolidated into `04-research-and-decisions.md` Part B; `bias-comparative-report-2026-05-21.md` is the surviving standalone artefact) with:

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

The standard test suite (`tests/test_bias_methodology.py`) generates a fresh report and asserts that the divergence-from-tolerance count is below the deployment threshold.

If the test fails, the deployer:

1. Reviews the divergence details.
2. Adjusts AI provider or prompt-template configuration if a tuning issue is identified.
3. Re-runs the test.
4. If the divergence persists, escalates to the provider via a GitHub Issue tagged `bias-report`.

---

## 4. Accuracy metrics

### 4.1 Fit-scoring accuracy

The fit-scoring algorithm has two components:

1. **AI per-criterion fit-scoring**: the AI returns four sub-scores (skills, experience, location/language, friction-fit; each 0–25) summing to a 0–100 SCORE; expected to track human-judgement ranking within ±10 fit-score points.
2. **Deterministic guardrails + ranking**: `parse_auto_fit_output` clamps the score to range and rejects malformed output (no fabricated score reaches the user); the rule-based persona-aware job ranking (`company_discovery/persona_ranking.py`) is verified by unit test.

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

When the configured AI provider is unavailable or errors, AI-assisted features fall back to their no-AI path: motivation/cover-letter drafting returns a deterministic templated skeleton (`company_discovery/motivation_letter.py`), while fit-scoring and CV-tailoring return a BYO-AI handoff prompt. The failure is recorded as an `ai_invocation` audit event with a non-`ok` outcome (`declined` for a handoff, `error` for a provider error). Covered by `tests/test_mcp_no_ai_fallback.py` and `tests/test_motivation_letter.py`.

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
- Dependency scanning (`pip-audit`) in CI ([`../.github/workflows/quality.yml`](../.github/workflows/quality.yml)).
- Audit log itself protected by file-system permissions on the deployer's host; PII-hashed by default.

---

## 7. Performance ratios (cost-saving claim grounding)

The cost-saving doctrine claims certain efficiency improvements per advisor visit. The metrics that ground each claim:

| Claim | Metric | Source |
|---|---|---|
| 20 minutes of routine work absorbed per advisor session | Median time spent on the journey phases the agent handles (profile capture, CV format guidance, fit-scoring, application drafting) | Pilot data from the post-grant partner-NGO pilot (2026 Q4) |
| 33% advisor caseload capacity expansion | Derived from the 20-minutes-out-of-60-minutes absorption ratio | Same |
| 30-day reduction in time-to-employment | Self-reported by pilot participants vs comparison cohort | Same |
| €30–200k AI-Act-compliance saving for deployer | Avoidance of external consultant fees at typical EU rates for high-risk-AI compliance engineering | Industry benchmarks; tagged `plausible` in [`../docs/grant/08-cost-saving-doctrine.md`](../docs/grant/08-cost-saving-doctrine.md) §"Mechanism 5" |

Each claim is tagged `proven` / `plausible` / `aspirational` in the cost-saving doctrine document. The accuracy-and-bias methodology feeds the "proven" column as pilot data lands.

---

## 8. Current results

**As of 2026-05-19**: the methodology is documented and **partially executed** via synthetic-cohort interim runs (2 of 6 scenario classes; 147 data points covering 70 scoring + 70 CV-tailoring + 7 cross-industry probes). The dated interim reports were consolidated into [`04-research-and-decisions.md`](../docs/grant/04-research-and-decisions.md) Part B and removed from the tree in commit `e85946b`; the surviving dated report is [`bias-comparative-report-2026-05-21.md`](../docs/grant/bias-comparative-report-2026-05-21.md). The standing unit-test suite (3,342 tests as of 2026-05-30) covers the deterministic-component accuracy (rule-based scoring, schema validation, locale parsing, encryption-at-rest). The remaining 4 scenario classes (onboarding, discovery, motivation-letter drafting, skill-gap brief) execute as part of the partner-NGO pilot in 2026 Q4 per [`ROADMAP.md`](../ROADMAP.md); results will be captured in dated reports under `docs/grant/`.

The honest status: this document describes a methodology that is partially executed at synthetic-cohort scale and that will complete its remaining 4 scenario classes during the partner-NGO pilot. The methodology is the contract; the synthetic-interim results are consolidated in `04-research-and-decisions.md` Part B; the partner-NGO results are pending. We disclose the partial-execution gap in the transparency notice.

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

**Out-of-bounds (OOB) hit rate**: the prior 2026-05-19 polished cohort run (narrated in `04-research-and-decisions.md` Part B 2026-05-19 entry; the dated snapshot itself was consolidated there in the e85946b docs cleanup) measured **10 / 77 = 13.0%** scoring out-of-bounds (where the model's per-criterion sub-scores don't sum to the SCORE total, or where SCORE is outside the 0-100 range, or where the reason / gaps fields are malformed in a way the parser rejects). The 2026-05-21 comparative run did not re-measure this metric — it focused on cross-provider mean drift — so the **13.0% OOB rate stands as the most recent honest measurement** and is the figure cited in the transparency notice. Driving this below 3% (search-quality + provider coverage) is a tracked post-grant deliverable (see `03-post-grant.md`).

**Honest framing for reviewers and deployers**:

- The methodology is reproducible end-to-end. The data is checked into `data/bias_comparative_cache/` for replay; the run can be re-issued with `python -m scripts.bias_comparative_report --replay-only`.
- The 13.0% OOB rate is **not** the system's user-visible failure rate — the score-clamp (see `tests/test_prompt_injection_vectors.py::V3JdIndirectInjection`) catches out-of-range scores at the parser layer, so the user sees either a defensible score or "no fit score available" (depending on whether the OOB pattern was a value clamp or a regex miss). It is the methodology's flagged-rate for "AI output not in the expected canonical shape", which is a real quality metric for the AI provider but not a measure of harm reaching the user.
- The cross-provider spread on harsh-scenario cells is the more important reviewer-visible signal. A deployer choosing between providers should look at the per-persona mean delta + the top-disagreement table and pick the provider whose scoring profile best matches their oversight capacity.
- All of these numbers will move when the partner-NGO pilot runs the remaining 4 scenario classes; we will not retire this section's measurements until the partner-NGO scope has overwritten them.

---

## 9. Append log

- **2026-05-18**: methodology drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Pre-deployment re-test framework drafted. First scheduled execution: the post-grant partner-NGO pilot (2026 Q4 per `../ROADMAP.md`).
- **2026-05-24**: §8.1 added — cross-provider comparative results from the 2026-05-21 run (7 personas × 10 scenarios × 2 providers = 140 data points; per-persona mean scores deepseek vs ollama; top-spread disagreement summary; the 13.0% OOB rate carried forward from the 2026-05-19 polished cohort run with the honest-framing paragraph distinguishing OOB-rate-as-AI-output-quality-metric from user-visible-harm-rate). Cross-references the comparative report at `docs/grant/bias-comparative-report-2026-05-21.md` and the parser-layer defence at `tests/test_prompt_injection_vectors.py::V3JdIndirectInjection` so reviewers can see the chain from measurement to safety surface.

---

## 10. Bias-comparative-report v2 — methodology scaffold

The v2 re-run is gated on the post-grant search-quality fixes (see `03-post-grant.md`) landing first (EURES real API integration, full ESCO taxonomy, multi-language ESCO lookup, smart provider routing, friction-aware result re-ranking). This section scaffolds the v2 methodology so a future agent re-running the bias panel knows the contract.

### 10.1 What changes between v1 (current) and v2

**v1 baseline** (`docs/grant/bias-comparative-report-2026-05-21.md`):

- 7 personas × 10 scenarios × 2 providers (`deepseek`, `ollama`) = **140 data points**
- 13.0 % AI-output OOB rate measured on the prior 2026-05-19 polished cohort (10 / 77)
- Top-spread disagreement: 30 / 29 / 22 / 22 points on `olga` + `tobias` wrong-industry cells
- Methodology: pin `build_auto_fit_prompt` (production prompt; per-criterion anchor scale + score-clamp parser); replay-only path checked into `data/bias_comparative_cache/`

**v2 expansion target**:

- 7 personas × **30** scenarios × **6** providers (`deepseek`, `ollama`, `openai`, `anthropic`, `gemini`, `openrouter`) = **1260 data points** (~9× v1 coverage)
- Per-persona scenario set expanded from 10 to 30 to include the friction-class edge cases that the search-quality fixes are designed to handle (e.g., `aicha_anerkennungs_friendly_employer_specialty_match`, `yusuf_blue_card_lateral_engineering_with_relocation`, `olga_english_team_remote_eu_with_vhs_pairing`, `mahmoud_eq_pre_ausbildung_with_berufsschule`, `maria_language_friendly_pflegedienst_with_course_pairing`, `kaethe_wiedereinstieg_with_paired_mentor`, `tobias_civic_tech_with_volunteer_portfolio`)
- OOB-rate target: **below 3 %** (down from 13.0 %). Achieved by: (a) per-criterion sub-score validation in the prompt builder, (b) score-clamp regex tightening to reject out-of-range integers earlier, (c) JD-friction-keyword corpus expansion so anchor-scale recognition rate goes up
- Friction-aware result re-ranking (§2.8 deliverable) is exercised explicitly: for each persona, the top-5 surfaced scores after re-ranking should weight `SCORE_FRICTION_FIT` more heavily; v2 measures the delta vs v1

### 10.2 New per-provider rows

In addition to the deepseek + ollama rows already populated, v2 adds:

| Provider | Live-key required? | Cost-cap budget | Notes |
|---|---|---|---|
| openai | Yes (`OPENAI_API_KEY`) | €5.00 per full run | First-class API; expect lowest OOB rate |
| anthropic | Yes (`ANTHROPIC_API_KEY`) | €8.00 per full run | Claude family; expect best per-criterion reasoning |
| gemini | Yes (`GEMINI_API_KEY`) | €3.00 per full run | Lower cost; expect higher OOB rate (Gemini follows JSON-output rules less rigidly per the AI Provider Honesty Matrix) |
| openrouter | Yes (`OPENROUTER_API_KEY`) | varies — routes to whichever model the operator pins | Use it as the BYO-many-providers shim |

The other two BYO-AI providers in the catalogue (`codex_cli`, `claude_code`) are local-CLI shims, not network APIs; v2 exercises them via subprocess-mocked tests rather than a full bias panel run (their behaviour is the user's local CLI behaviour, not a provider-comparable measurement).

### 10.3 Reproducibility recipe

```bash
# Pre-flight: confirm the search-quality fixes have landed
python3 -m unittest discover -s tests -t . -k 'test_search_quality' -v
# Expected: all green (otherwise v2 measurements would compare against
# a moving target). If any fail, the v2 run is premature.

# Cache-only replay first (no API calls)
python3 -m scripts.bias_comparative_report \
  --version v2 \
  --replay-only \
  --providers deepseek,ollama,openai,anthropic,gemini,openrouter \
  --output docs/grant/bias-comparative-report-v2-<YYYY-MM-DD>.md

# If cache is incomplete, populate live with cost-cap enforcement
python3 -m scripts.bias_comparative_report \
  --version v2 \
  --live \
  --cost-cap-eur-per-provider deepseek=2,ollama=0,openai=5,anthropic=8,gemini=3,openrouter=3 \
  --abort-on-cap-breach
```

### 10.4 Acceptance criteria

The v2 report is acceptance-ready when:

- All 1260 data points have a parser-validated score in [0, 100] OR a documented OOB reason (the < 3 % target is on the OOB-but-clamped class, not the rejected-by-parser class).
- The per-persona mean spread between providers does NOT widen vs v1 (i.e., the search-quality fixes don't introduce new disagreement); spreads can shrink (a good outcome).
- Every friction-class anchor-scale band has at least one verified hit (so the per-persona Anerkennungs-friendly / Blue-Card-aware / Wiedereinstiegs-mentor / civic-tech-Quereinsteiger detection is empirically exercised, not just declared).
- The full diff vs v1 is rendered as a per-persona × per-provider delta table; rows with > 10-point swings get a one-line maintainer-narrative explaining whether the swing is "search-quality-fix improvement" or "regression" or "model-vendor drift between v1 and v2 dates".

### 10.5 Honest framing for the report

v2 should retain the v1 honesty-discipline framing:

- "OOB rate" is the AI-output-quality metric, NOT the user-visible-harm metric (the parser-layer score-clamp catches OOB outputs before they reach the user).
- "Top-spread disagreement" is the cross-provider divergence metric, which informs deployer provider-choice but is not itself a "failure" (both providers may be defensibly scoring the same scenario differently).
- "Mean per-persona score" is sensitive to scenario-corpus design — expansion to 30 scenarios per persona means v2 means are NOT directly comparable to v1 means (different denominators); the report calls this out explicitly.

This methodology section is the contract; the v2 execution is the deliverable. Until v2 runs, v1 stands as the authoritative cross-provider measurement.
