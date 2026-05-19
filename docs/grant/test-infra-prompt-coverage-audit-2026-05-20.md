<!-- SPDX-License-Identifier: Apache-2.0 -->

# Test-infrastructure prompt-coverage audit — 2026-05-20

**Trigger**: operator discipline nudge issued during the bias-methodology
re-run diagnosis (2026-05-20). Standing rule for the rest of the
product-quality sweep:

> "Does the test that claims to validate behaviour X actually exercise
> the production code path for X, or a test-local copy?"

This audit applies that filter across the entire `tests/` tree to
surface any other instances of the "looks-like-it-tests-X,
actually-tests-X-copy" pattern that prompted the rule.

---

## Method

1. Enumerate all production prompt builders in `company_discovery/` —
   functions named `build_*_prompt` that emit a prompt string or
   `(system, user)` tuple destined for an AI provider.
2. For each builder, locate references inside `tests/` (direct import
   or string match).
3. For each test that imports `_dispatch_provider` directly, classify:
   (a) intercepts the dispatch boundary to capture the production-
   builder-produced prompt (CORRECT — tests production), (b) calls
   `_dispatch_provider` with a literal short string as a routing /
   audit-log smoke check (CORRECT — not testing model behaviour), or
   (c) constructs its own prompt string inline (GAP — measures the
   test's copy, not production).
4. For each test that has its own `_build_*` helper, classify:
   (a) builds non-prompt test fixtures (docx/pdf/state — CORRECT),
   or (b) builds a parallel prompt that diverges from production (GAP).
5. For builders with no direct reference in tests, follow the call
   chain to confirm whether transitive coverage exists via end-to-end
   route invocations + dispatch-boundary patches.

---

## Production prompt builders inventoried (9)

| Builder | File | Coverage shape |
|---|---|---|
| `build_job_decision_brief_prompt` | `analysis.py:142` | Direct import in tests |
| `build_cover_letter_brief_prompt` | `analysis.py:200` | Direct import in tests |
| `build_auto_fit_prompt` | `analysis.py:255` | **NEWLY** wired to bias-methodology test 2026-05-20 (gap closure below) + already had direct test coverage in other test files |
| `build_cv_query_expansion_prompt` | `analysis.py:323` | Direct import in tests |
| `build_cv_tailoring_prompt` | `analysis.py:491` | Direct import in tests + bias-methodology test CV-tailoring slice |
| `build_ai_router_prompt` | `chat_router.py:794` | Transitive via `AppState.chat_ai_route` invocations in `test_chat_ai_router.py` (11 call sites) + `_dispatch_provider` patches that capture the prompt |
| `build_format_prompt` | `cv_builder.py:339` | Direct import in tests |
| `build_consult_prompt` | `cv_consult.py:61` | Direct import in `test_journey_edge_cases.py` + `test_cv_consult.py` |
| `build_letter_prompt` | `motivation_letter.py:84` | Direct import in tests |

**Verdict**: every production prompt builder has either direct test
coverage or end-to-end transitive coverage via a dispatch-boundary
patch. No untested production prompts.

---

## Test files invoking `_dispatch_provider` directly (5)

| Test file | Pattern | Verdict |
|---|---|---|
| `tests/test_ai_quality_e2e.py` | Context manager patches `_dispatch_provider` and captures the prompt argument; production builders generate the prompt. | CORRECT — tests production builder output via boundary capture. |
| `tests/test_bias_methodology.py` | Was self-contained `_build_fit_score_prompt` until 2026-05-20; NOW delegates to `build_auto_fit_prompt`. | **GAP — closed 2026-05-20.** See "Closed gap" below. |
| `tests/test_chat_ai_router.py` | `patch.object(analysis_mod, "_dispatch_provider", side_effect=fake_dispatch)`; production chat router generates the prompt via `build_ai_router_prompt`. | CORRECT — boundary patch, production builder invoked. |
| `tests/test_phase13_audit_log.py` | `_dispatch_provider("hi", ..., purpose="manual_handoff")` — literal `"hi"` is a routing smoke probe to verify audit-log record emission, not a model-behaviour test. | CORRECT — not a behaviour test; literal prompt is intentional. |
| `tests/test_phase2_managed_ai.py` | `_dispatch_provider("hi", self._config(), ...)` — literal `"hi"` is a managed-AI-routing smoke probe; tests routing, not model output. | CORRECT — not a behaviour test; literal prompt is intentional. |

---

## Test files with their own `_build_*` helpers (4)

| Test file | Helper | Verdict |
|---|---|---|
| `tests/test_bias_methodology.py` | `_build_fit_score_prompt(persona, scenario) -> str` | Was prompt builder pre-2026-05-20; now delegates to production. |
| `tests/test_round2.py` | `_build_minimal_docx(text: str) -> bytes` | Test fixture builder (docx bytes for upload tests). Not a prompt builder. |
| `tests/test_round3.py` | `_build_minimal_pdf(text: str) -> bytes` | Test fixture builder (pdf bytes for upload tests). Not a prompt builder. |
| `tests/test_seed_personas.py` | `_build_state_in_tmpdir(tmpdir: Path)` | Test fixture builder (AppState in a tempdir). Not a prompt builder. |

---

## Closed gap: bias-methodology fit-scoring (2026-05-20)

**Before**:
`tests/test_bias_methodology.py::_build_fit_score_prompt` was a self-
contained prompt that emitted `FIT_SCORE: <int>` + optional rationale.
That prompt had no production caller. The `/auto-fit` feature in
production (`build_auto_fit_prompt` in `company_discovery/analysis.py`)
emits four per-criterion sub-scores summed to a holistic SCORE.

Four dated bias-testing reports through 2026-05-19 therefore measured
the test framework's prompt, not the production prompt. The CV-
tailoring side of every report (which went through production
`build_cv_tailoring_prompt`) remains intact as production-prompt
evidence.

**After**:
- `_build_fit_score_prompt(persona, scenario)` now constructs a
  `UserProfile` from the persona and a `DiscoveredJob` from the
  scenario, then calls `build_auto_fit_prompt(...)` and returns its
  `["prompt"]` field. The bias-methodology test now exercises the
  production prompt byte-for-byte.
- Sub-score extractor `_extract_subscores(response_text)` added
  alongside `_extract_fit_score`. Per-record sidecar now carries
  `observed_subscores: {"skills", "experience", "location_language",
  "friction_fit"}`.
- `raw_output_head` slice bumped `[:200] → [:500]` at both scoring
  loops so the four sub-score lines + the SCORE line fit safely in
  the captured head.
- Sidecar filename now ISO-date-stamped (previously hardcoded as
  `bias-testing-2026-05-19-data.json`, which caused the 2026-05-20
  run to silently overwrite the May 19 file). Override via
  `HELPMEFINDTHEJOB_BIAS_REPORT_DATE` env var for replay use.
- May 19 sidecar restored from HEAD; the May 20 pre-wiring run's data
  preserved at `bias-testing-2026-05-20-pre-wiring-data.json` for
  audit trail.

**Smoke proof** (Aïcha + `anerkennung_friendly_clinical` strong-fit
scenario, Ollama llama3.1:8b, 16.3 s elapsed):

```
SCORE_SKILLS: 15
SCORE_EXPERIENCE: 13
SCORE_LOCATION_LANGUAGE: 20
SCORE_FRICTION_FIT: 10
SCORE: 58
```

Sub-scores parse cleanly; sum (15+13+20+10) equals SCORE (58); all
four sub-score lines + the SCORE line fit inside `raw_output_head[:500]`.

---

## Audit closure

**Test-local-prompt-copy gaps found**: 1 (bias-methodology — closed).
**Other prompt-coverage issues found**: 0.
**Production prompt builders with no test coverage**: 0.
**Test files with parallel-prompt patterns posing as production tests**: 0.

The discipline-nudge filter has been applied to the entire `tests/`
tree and the matching production code. The pattern is contained to the
single gap surfaced and closed in this slice.

Future-test policy (binding for the rest of the product-quality
sweep and post-grant Phase 2): any new test that claims to validate
AI-driven product behaviour must either (a) import the production
prompt builder directly, or (b) intercept the `_dispatch_provider`
boundary while invoking the production caller that internally
constructs the prompt. Inline test-local prompt strings are
acceptable only for routing / audit-log smoke probes where the
prompt content is not the subject under test.
