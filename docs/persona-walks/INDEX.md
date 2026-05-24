<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walks — INDEX

**Purpose**: per-persona end-to-end walk-throughs proving the system serves each of the seven canonical personas in `docs/grant/07-personas.md` from sign-up through application-tracked. The walks are the load-bearing reviewer evidence that the friction-class architecture (Decision 21) is implemented, not just claimed.

**Last updated**: 2026-05-24. PlanTowardPerfection Ceiling 2 boxes 2.5.1–2.5.8 close in this slice; box 2.5.9 (Playwright `tests/e2e/persona_*_smoke.py` suite) is queued for the next batch.

---

## What a persona walk contains

Each `docs/persona-walks/<persona>.md` file has six sections:

1. **Persona identity** — slug, cohort, residency status, friction notes, languages, primary anchor role. Sourced from `company_discovery/persona_fixtures.py` and `docs/grant/07-personas.md`.
2. **Sign-up + onboarding** — what the user types, what they see, the journey state after each turn. References the detailed chat-router transcripts in `docs/grant/journey-walks-2026-05-20/<persona>.md`.
3. **CV preparation** — DE/EN handling, persona-friendly fields, the CV builder's sectional interview pattern.
4. **Job matching** — search → discover → fit-score → top-5 surfaced. Cross-references the persona's bias-test scenarios in `company_discovery/persona_fixtures.py::PERSONAS`.
5. **Letter drafting** — Anschreiben that proactively names the friction context (e.g., explains §16d to a recruiter). References `docs/grant/anschreiben-quality-walks-2026-05-20/<persona>.md`.
6. **Application tracked** — mark-applied → follow-up reminder → response logged. Final state proves the journey loops on first iteration.

Plus a per-walk **"what felt broken"** notes section so each walk's residual roughness is documented honestly (the NLnet-winner discipline of being explicit about alpha state).

## Cohort split (Decision 21)

| Cohort | Personas | Narrative role |
|---|---|---|
| Most-acute migrant (primary anchor) | Aïcha · Yusuf · Olga · Mahmoud · Maria | Strongest specific evidence the system serves the friction class. Named first in every public-facing artefact. |
| Wider friction-class (architectural demonstration) | Käthe · Tobias | Demonstrate the friction-class architectural claim without diluting the primary narrative. |

## Methodology

The walks are **scripted end-to-end walkthroughs** grounded in the production product surface (the `company_discovery.chat_router`, `company_discovery.journey`, `company_discovery.cv_builder`, `company_discovery.analysis` modules). They are NOT manual handcrafted demos; the input shapes are sourced from `PERSONAS` fixtures so the same input produces the same downstream behaviour in the bias-methodology test suite (`tests/test_bias_methodology.py`).

For each persona, the walk references the persona's:
- `cv_summary` (used as the CV preparation seed)
- `target_roles` (used as the job-search input)
- `location` (used as the city filter)
- `residency_status` + `friction_notes` (surfaced through the journey's persona-friction-class lens)
- `bias_scenarios` (the 10 synthetic jobs used in the cross-provider comparative report)
- `cv_tailoring_scenarios` (the per-criterion CV-tailoring assertions)

A future agent re-running these walks against a live instance can replay each step via `python3 scripts/seed-personas.py --dry-run` (proves the persona records still resolve) then `bash scripts/probe-journey-ai.sh aicha` (replays Aïcha's journey against the live AI providers).

## Cross-references

- Persona source-of-truth: `company_discovery/persona_fixtures.py`
- Narrative source-of-truth: `docs/grant/07-personas.md`
- Detailed turn-by-turn journey transcripts: `docs/grant/journey-walks-2026-05-20/`
- Anschreiben quality walks: `docs/grant/anschreiben-quality-walks-2026-05-20/`
- MCP composition walks: `docs/grant/mcp-walks-2026-05-21/`
- Aïcha pass-3 smoke harness output: `docs/grant/product-quality-walks/aicha-pass3-smoke-2026-05-20.json`
- Bias-methodology cross-provider results: `docs/grant/bias-comparative-report-2026-05-21.md`

## What this index is NOT

This is not a step-by-step tutorial for a new user of the system; for that, see the SPA's in-app `/help` page. This is also not a marketing demo; for that, see the README hero and the Field-8 demo URL block in `docs/grant/application-draft-2026-05-19.md`.

This is the **reviewer's evidence** that each persona has been thought-through end-to-end and that the system's behaviour for each persona has been documented at a depth a NLnet reviewer can audit.

## Append log

- **2026-05-24** (PlanTowardPerfection box 2.5.8): persona-walks directory created with INDEX + 7 per-persona walk docs (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias). All walks reference the prior dated source artefacts in `docs/grant/journey-walks-2026-05-20/` and `docs/grant/anschreiben-quality-walks-2026-05-20/` rather than duplicating the substantive transcript bodies; the per-persona walk doc is the navigational entry point + the "what felt broken" notes + the friction-class lens.
