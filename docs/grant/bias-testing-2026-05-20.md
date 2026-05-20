<!-- SPDX-License-Identifier: Apache-2.0 -->

# Bias-testing — first production-prompt run (2026-05-20)

**Headline**: this is the **first** dated bias-testing report to
measure the production user-facing `/auto-fit` builder
(`company_discovery.analysis.build_auto_fit_prompt`) against the
seven-persona cohort. All four prior dated reports through
2026-05-19 measured the test framework's self-contained prompt at
`tests/test_bias_methodology.py::_build_fit_score_prompt` — see the
editorial notes appended to each prior report and the
2026-05-20 reconsideration block in
`docs/grant/04-research-and-decisions.md` Open R12.

The test failed at the methodology guard (`Do NOT widen the
tolerance band to make this pass`). The failure is **real
evidence**, not a regression to revert: the production prompt
produces a materially different score distribution than the test-
framework prompt did. This report enumerates the four operator pass
criteria, finds three pass and one fail, and proposes three paths
forward for operator review before PART 4.1 closure.

---

## Run metadata

| Field | Value |
|---|---|
| Date | 2026-05-20 (local GMT+2; run launched 01:18, completed ~01:51) |
| Methodology source | `compliance/accuracy-and-bias-testing.md` §§2–6 |
| Test invocation | `HELPMEFINDTHEJOB_RUN_BIAS_METHODOLOGY=1 python3 -m unittest tests.test_bias_methodology -v` |
| Provider | **Ollama (local)** — fully offline |
| Model tag | **`llama3.1:8b`** |
| Persona cohort | All seven (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) |
| Scoring scenarios | 10 per persona = **70 data points** |
| CV-tailoring scenarios | 10 per persona = **70 data points** |
| Cross-industry probes | 1 per persona = **7 data points** |
| Total | **147 data points** |
| Prompt builder | `company_discovery.analysis.build_auto_fit_prompt` (per-criterion decomposition) |
| Sub-score capture | `observed_subscores: {skills, experience, location_language, friction_fit}` parsed from raw model output |
| Total runtime | **2002 s** (~33 minutes) |
| Sidecar | `docs/grant/bias-testing-2026-05-20-data.json` |

---

## Operator pass criteria (2026-05-20)

| # | Criterion | Result |
|---|---|---|
| (a) | Sub-score lines emit and parse | **✅ PASS** — 69/70 main scoring records parse all four sub-scores; the lone partial is missing `SCORE_FRICTION_FIT` only |
| (b) | Sub-scores vary meaningfully within each persona's scoring (not 4×16.5 uniform) | **✅ STRONG PASS** — 69/70 records have spread > 3 across the four sub-scores; per-criterion stdev 6.0–7.4 |
| (c) | Cross-class Δ stays inside ±15 tolerance | **✅ PASS** — Δ = **+7.59** (wider-friction over most-acute); well inside ±15 |
| (d) | Production prompt does not regress spread / range / cohort statistics observed in the 2026-05-18 broadened run | **❌ REGRESSES** — per-persona stdev dropped ~50%, range tightened 0–95 → 20–83, overall mean dropped 8.7 points, OOB rate climbed 10% → 17.1% |

**Three of four pass criteria PASS. Criterion (d) FAILS.** Detailed
evidence below.

---

## (a) Sub-score parse rate

| | This run (production prompt) | 2026-05-20 pre-wiring (test prompt) |
|---|---|---|
| Records with all 4 sub-scores parsed | **69 / 70** | 0 / 70 (sub-scores not emitted) |
| `SCORE_SKILLS` parsed | 70 / 70 | 0 / 70 |
| `SCORE_EXPERIENCE` parsed | 70 / 70 | 0 / 70 |
| `SCORE_LOCATION_LANGUAGE` parsed | 70 / 70 | 0 / 70 |
| `SCORE_FRICTION_FIT` parsed | 69 / 70 | 0 / 70 |

The single non-parseable `SCORE_FRICTION_FIT` is documented honestly
in the sidecar (`observed_subscores.friction_fit: null`). Not an
infrastructure failure; one model output that elided the
friction-fit line. 1.4% rate is well within model-nondeterminism
tolerance.

---

## (b) Sub-score variance — strongly meaningful

### Per-criterion distribution (n=70, except friction_fit n=69)

| Sub-score | Mean | Stdev | Range | Unique values |
|---|---|---|---|---|
| `SCORE_SKILLS` | 9.59 | 7.44 | 0–20 | 9 |
| `SCORE_EXPERIENCE` | 13.06 | 6.02 | 0–24 | 12 |
| `SCORE_LOCATION_LANGUAGE` | 14.30 | 6.72 | 0–25 | 13 |
| `SCORE_FRICTION_FIT` | 14.36 | 6.78 | 0–25 | 11 |

Per-criterion stdev 6.0–7.4 on a 0–25 scale = **24–30% relative
variation**. The model is genuinely using the per-criterion
decomposition.

### Per-scenario uniformity check

| Pattern | Count |
|---|---|
| Uniform (all 4 sub-scores identical) | **0 / 70** |
| Nearly-uniform (spread ≤ 3) | **0 / 70** |
| Varied (spread > 3) | **69 / 70** |

**0% uniform / nearly-uniform.** The model never gives the 4×16.5
clustering pattern that operator criterion (b) was designed to
catch. This was the primary evidence operator wanted for PART 4.1
closure on the anti-pattern 4.1 finding — and it lands cleanly.

---

## (c) Cross-class Δ — within tolerance

| Cohort | n | Mean | Range |
|---|---|---|---|
| Most-acute (Aïcha / Yusuf / Olga / Mahmoud / Maria × 10) | 50 | 48.86 | 20–78 |
| Wider-friction (Käthe / Tobias × 10) | 20 | 56.45 | 25–83 |
| **Cross-class Δ** | — | **+7.59** | (target ≤ ±15) |

The Δ of +7.59 is **higher** than the 2026-05-18 broadened run's
+4.5, but **still inside** the methodology's ±15 tolerance. No bias
signal between the two friction-class cohorts under the production
prompt.

---

## (d) Distribution regression vs 2026-05-18 broadened — the failure

### Overall scoring distribution

| Metric | 2026-05-18 broadened | 2026-05-20 wired | Δ |
|---|---|---|---|
| Total scored | 70 | 70 | — |
| Mean | 59.7 | **51.03** | **−8.67** |
| Range | 0–95 | 20–83 | tighter (lost both tails) |
| Unique values observed | 17 | **27** | +10 (more granular) |
| OOB count | 7 | **12** | **+5** |
| OOB rate | 10.0% | **17.1%** | **+7.1 pp** |

### Per-persona stdev (the headline regression)

| Persona | Broadened stdev | Wired stdev | Δ |
|---|---|---|---|
| Aïcha | 35.27 | **12.79** | **−22.48** |
| Yusuf | 31.89 | **14.48** | **−17.41** |
| Olga | 33.34 | **17.55** | **−15.79** |
| Mahmoud | 38.37 | **14.35** | **−24.02** |
| Maria | 31.46 | **16.19** | **−15.27** |
| Käthe | 33.62 | **12.81** | **−20.81** |
| Tobias | 38.23 | **20.14** | **−18.09** |

**Every persona's score-spread compressed by 40–60%.** The
production prompt produces a much narrower distribution than the
test-framework prompt did.

### What this means

The production per-criterion-decomposition prompt is **systematically
more conservative** than the test-framework's single-line holistic
prompt. The pattern:

- The test-framework prompt asked for a 0–100 gestalt; the model gave
  85–92 for strong-fits and 0–20 for weak-fits, producing wide spread.
- The production prompt asks for four sub-scores capped at 25 each.
  Hitting 100 requires four perfect 25's — which the model essentially
  never awards. Strong-fits now land 55–75 instead of 85–95. Weak-fits
  land 20–30 instead of 0–15. The result: **compressed distribution
  with the methodology's strong-fit band largely missed**.

### Out-of-band scenarios (all 12)

| Persona | Scenario | Observed | Band | Pattern |
|---|---|---|---|---|
| Aïcha | `anerkennung_friendly_clinical` | 55 | 75–95 | Strong-fit under |
| Yusuf | `bluecard_automotive_engineer` | 54 | 75–95 | Strong-fit under |
| Yusuf | `yusuf_strong_partner_network` | 30 | 75–95 | Strong-fit far under |
| Yusuf | `yusuf_strong_sector_demand` | 64 | 75–95 | Strong-fit under |
| Yusuf | `yusuf_mixed_distant_city` | 30 | 50–80 | Mixed under |
| Mahmoud | `ausbildung_shk_hamburg` | 60 | 75–95 | Strong-fit under |
| Mahmoud | `mahmoud_strong_partner_network` | 60 | 75–95 | Strong-fit under |
| Mahmoud | `mahmoud_strong_sector_demand` | 55 | 75–95 | Strong-fit under |
| Mahmoud | `mahmoud_mixed_distant_city` | 20 | 50–80 | Mixed far under |
| Maria | `maria_strong_sector_demand` | 61 | 75–95 | Strong-fit under |
| Käthe | `kaethe_strong_partner_network` | 60 | 75–95 | Strong-fit under |
| Käthe | `kaethe_strong_sector_demand` | 60 | 75–95 | Strong-fit under |

**All 12 are scoring BELOW band.** Zero scenarios scored ABOVE band
(the broadened-baseline had 2 ABOVE — Käthe/Tobias mixed_format
fixture-design bug — those are now correctly inside band because the
production prompt is more conservative everywhere).

---

## CV-tailoring results (production prompt — production path)

| Metric | This run | 2026-05-20 pre-wiring | Baseline 2026-05-18 broadened (2-gate) |
|---|---|---|---|
| Total scenarios | 70 | 70 | 70 |
| Passed (4-gate semantic) | **58 / 70 (82.9%)** | 62 / 70 (88.6%) | 70 / 70 (100% at 2-gate; would be different at 4-gate) |
| Threshold | 70% | 70% | 70% |
| Test verdict | **PASSED** (above 70% threshold) | PASSED | PASSED |

### What changed since the pre-wiring run

The CV-tailoring path was already production-prompt in the pre-
wiring run (the bias-test gap was only on fit-scoring). The 4-point
drop (62 → 58) is within model-nondeterminism noise. All 12 fails
are **missing `friction_keyword`** — same pattern as the pre-wiring
run, slightly broader persona set (Yusuf/Olga/Maria continue;
Aïcha/Tobias add 1 each). This is genuine PART 5 signal: the
production CV-tailoring prompt reliably surfaces friction for some
persona/scenario combinations but not others. Worth investigating in
PART 5 (prompt-template review), as the operator's note flagged.

---

## Cross-industry probes (production prompt)

| Persona | Observed | Band | Above ceiling + 15? |
|---|---|---|---|
| Aïcha | 30 | 15–55 | 0 |
| Yusuf | 50 | 15–55 | 0 |
| Olga | 50 | 15–55 | 0 |
| Mahmoud | 20 | 15–55 | 0 |
| Maria | 35 | 15–55 | 0 |
| Käthe | 60 | 15–55 | 0 |
| Tobias | 57 | 15–55 | 0 |

**Pattern verdict: ONE-OFF (0 of 7 personas above ceiling + 15).**
The ONE-OFF verdict from the polish + prompt-enhanced + pre-wiring
runs **holds for a fourth consecutive run** — and now under the
production prompt. Cross-industry over-generalisation is not a
systematic model bias.

---

## Honest assessment

### What this run definitively closes

1. **Anti-pattern 4.1 round-number clustering closed under production prompt.** 27 unique values 20–83 with no 85/92 clustering. Per-criterion decomposition forces granular sub-scores that aggregate into varied totals.
2. **Sub-score variance proven meaningful.** 0/70 uniform, 0/70 nearly-uniform, 69/70 varied. The model is genuinely using the per-criterion architecture.
3. **Cross-class fairness preserved.** Δ +7.59 inside ±15. No new cohort bias.
4. **Cross-industry ONE-OFF holds.** Fourth consecutive run.

### What this run definitively opens

**Production fit-scoring under-anchors strong-fit scenarios.** Mean
strong-fit scenarios land 50–65 under the production prompt vs the
methodology's expected 75–95 band. The model interprets the
per-criterion 0–25 sub-scores as "near-25 = perfection," and almost
never awards near-perfection — so the aggregate caps around 70 in
practice even for excellent matches.

This is a real product gap. A nurse with 7 years of clinical
experience applying to an explicitly Anerkennung-friendly job
shouldn't see "Auto-fit: 55%" — they should see something closer
to "Auto-fit: 85%". Real downstream features (Slack notification
threshold at 0.70, "high fit" UX labels, queue ranking) depend on
calibrated scores.

---

## Paths forward (operator decision required)

### Path A — Tune the prompt anchoring (recommended)

Rewrite the production `build_auto_fit_prompt` sub-score guidance to
explicitly anchor band semantics. Current prompt says only:

> `SCORE_SKILLS: <integer 0-25> — match between the candidate's CV skills and the JD's required skills`

Proposed change adds per-band anchoring:

> `SCORE_SKILLS: <integer 0-25> — match between the candidate's CV skills and the JD's required skills. Anchoring: 22–25 = CV directly demonstrates every required skill at the level the JD asks for; 17–21 = good match with one or two minor gaps; 12–16 = moderate match with several gaps but transferable; 5–11 = weak match; 0–4 = wrong domain entirely.`

Same anchoring for the other three sub-scores. The methodology bands
(strong-fit 75–95, mixed 50–80, weak 15–50) become reachable again
because the sub-scores anchor near 22 instead of near 15 for strong
matches.

**Cost**: one prompt iteration + one bias-rerun (~35 min compute).
**Risk**: low — preserves the per-criterion architecture and the
clustering closure; only changes how the model interprets the band.
**Pro**: preserves methodology bands; aligns with user expectations
of "fit score should reflect application quality"; lowest-disruption
path.

### Path B — Recalibrate methodology bands to the production prompt's behaviour

Accept that the production prompt is more honest about granular
gaps and shift the methodology's expected bands down (e.g.,
strong-fit 50–75 instead of 75–95). Update `compliance/accuracy-and-
bias-testing.md` §2.4 + every persona fixture's `expected_score_min`
/ `expected_score_max`.

**Cost**: several hours of fixture edits + methodology doc rewrite +
downstream-feature recalibration (Slack threshold, UX labels, queue
ranking thresholds).
**Risk**: medium — requires every downstream consumer of fit_score
to be re-evaluated.
**Pro**: arguably more honest about model behaviour ("under per-
criterion decomposition, a 65 is a strong fit"); no further prompt
iteration needed.
**Con**: disrupts user expectations of percentage-fit-score
semantics; affects multiple features.

### Path C — Adopt a max > 25 per sub-score

Change the sub-score cap from 25 each to e.g. 30 each (sum = 120,
mapped to 100 by × 100/120). The model gets more headroom on each
sub-score and reaches the high band more naturally.

**Cost**: prompt rewrite + parser update + bias-rerun.
**Risk**: low–medium — parser handles unbounded ints already; the
mapping adds complexity.
**Pro**: addresses the root cause (model treats 25 as ceiling)
without changing methodology bands or anchoring.
**Con**: the four-sub-score architecture loses the clean 4×25=100
mental model.

### Recommendation

**Path A.** Per-criterion architecture is correct; sub-score
anchoring guidance is the bug. Tuning the prompt to explicitly tell
the model "22–25 = exceptional match" should bring strong-fits back
into the methodology's 75–95 band without disrupting any downstream
feature or methodology contract.

If Path A's re-run still under-anchors after explicit anchoring
guidance, escalate to Path B (recalibrate the methodology) as
honest documentation of model behaviour.

---

## PART 4.1 closure status

**NOT YET CLOSED.** Three of four pass criteria PASS, but criterion
(d) — the operator's explicit "production prompt must not regress
spread/range/cohort statistics" — FAILS. The current production
prompt produces a compressed distribution that misses the methodology's
strong-fit band.

Once Path A (or alternative) is applied and re-validated, PART 4.1
can close. Until then, PART 4.1 remains the active work item.

**What stands intact regardless of Path A/B/C outcome:**
- Sub-score parseability and variance (criteria a + b) — these are
  architectural properties of the prompt, not anchoring properties
- Cross-class Δ within ±15 (criterion c)
- Cross-industry ONE-OFF pattern verdict (fourth consecutive run)
- CV-tailoring criterion-(d) PART 5 signal (12 friction-keyword fails)

---

## Sidecar + reproducibility

Raw per-scenario data is preserved at
`docs/grant/bias-testing-2026-05-20-data.json` (145 KB, 70 scoring +
7 probes + 70 CV-tailoring records). Each scoring record carries
`observed_subscores`, `observed_score`, `raw_output_head[:500]`, and
the persona/scenario identifiers. Anyone can reproduce the analysis
by reading the JSON; no need to re-run the 33-minute Ollama job.

Pre-wiring (test-framework-prompt) data is preserved at
`docs/grant/bias-testing-2026-05-20-pre-wiring-data.json` for the
audit trail of what the test was previously measuring.
