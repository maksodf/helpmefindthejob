<!-- SPDX-License-Identifier: Apache-2.0 -->

# Data layer coverage — structural honesty note (2026-05-20)

Surfaced during PART 6 Bug C piece 2 read-through. Goes into the
PART 6 closure report's "Honesty notes" section + flags a PART 10
honesty-matrix row when PART 10 begins.

## The structural insight

The Helpmefindthejob job-discovery layer fans out to a set of
free-tier aggregator providers configured in
`default_no_auth_providers()` (defined in
`company_discovery/aggregator_providers.py`):

- **Arbeitnow** — DACH-focused but heavily tech-skewed
- **EURES** — EU-wide, weighted toward cross-border professional roles
- **Bundesagentur** — broad DE coverage; ramping up but data-sparse
  for many friction-relevant job classes
- **Muse** — US/UK-skewed, English-language, tech-heavy
- **Remotive** / **WeWorkRemotely** — fully-remote, tech-skewed
- **HackerNewsHiring** — tech-only, English-language

Adzuna is also wired in but quota-limited (250 calls/month free tier);
treated as opt-in for deployer configurations.

The aggregate coverage of this provider set skews systematically
toward **English-speaking, tech-class, fully-remote-or-Berlin-Munich**
postings. Coverage is **weaker** for:

- **Pflege / Krankenschwester / Altenpflegerin** (the role classes for
  Aïcha, Maria, Käthe)
- **Wiedereinstieg / Wiedereinstiegspflege** (Käthe-class friction
  context)
- **Anlagenmechaniker SHK / Auszubildender SHK** (Mahmoud's trades
  Ausbildung path)
- **Civic-tech, public-sector, NGO / sovereign-tech** in German
  (Tobias's civic-tech career-change target)
- **Anerkennung-friendly clinical** postings (Aïcha's strong-fit
  scenario)

Five of the seven panel personas hit data-layer coverage gaps. The
two with the cleanest coverage are Yusuf (Munich + automotive
engineer + EU Blue Card matches the free-tier sweet spot) and Olga
(Senior frontend developer + English-team in Leipzig matches the
remote-tech sweet spot).

**The personas the project is explicitly built to serve are
under-represented in the data layer at the moment.**

## How Bug C piece 2 was designed around this

The `DiagnosticEngine` is **architecturally bias-safe**:

- **Cache-only**, never live-probes the skewed free-tier index. Live-
  probing only the free providers would compute relaxation-candidate
  counts from the biased set — under-reporting opportunities for
  exactly the migrant personas the diagnostic is meant to serve.
- **Returns None when the cache has no relaxation-candidate data**,
  so the caller substitutes a strict-fact fallback message ("No
  matches found for X in Y with these preferences"). The fallback
  contains **zero hedging language** (verified by the
  `_FORBIDDEN_HEDGING` pattern test in
  `tests/test_diagnostic_engine.py`).
- **Forward-compatible** with a persistent job index (Phase 2 backlog
  #71). When the index lands, `DiagnosticEngine.generate()` plugs in
  without restructuring — the seam already exists.

On a cold-cache deploy (the common case for a low-traffic civic-
commons MVP), the engine returns the strict-fact fallback for every
persona. This is the doctrine-correct outcome: the system does not
invent diagnostics it can't substantiate.

## What this means for grant submission framing

Honest read for the NLnet application + PART 10 honesty matrix:

- The PART 6 empty-state recovery architecture is **top-tier within
  open-source civic-commons scope**: never-implicit-done, no
  hallucination, no LLM in the diagnostic path, no live-probing of
  biased providers.
- Real-world diagnostic substance for the migrant-five personas will
  **improve as the data layer expands** — via Phase 2 backlog #71
  (persistent index) and/or via paid-tier providers (Adzuna premium
  tier, Bundesagentur full-data partnership) that may close the
  current coverage gap.
- This is **not a deficiency we mask** — it's a documented structural
  property of the current free-tier provider mix, with a clear path
  to address it.

## PART 10 honesty-matrix row (to be added when PART 10 begins)

| Surface | Top-tier within civic-commons scope | Top-tier with paid-tier providers |
|---|---|---|
| Data layer / job-board coverage | **Partial** — free-tier skew under-represents Pflege / Krankenschwester / Anlagenmechaniker SHK / German civic-tech postings; migrant-five personas affected | **TBD** — depends on whether paid providers (Adzuna premium, Bundesagentur full-data partnership) close the gap; Phase 2 backlog #71 is the in-house alternative |

## Cross-references

- `company_discovery/diagnostic_engine.py` — the cache-only,
  deterministic implementation
- `tests/test_diagnostic_engine.py::NoLLMInvocationTests` — static
  no-LLM-imports assertion
- `tests/test_diagnostic_engine.py::ColdCachePanelMatrixTests::test_cold_cache_fallback_contains_no_hedging`
  — pattern-matches against `_FORBIDDEN_HEDGING` to keep the
  strict-fact fallback honest
- `docs/grant/phase2-backlog-2026-05-19.md` items #71 (persistent
  index), #67 (cloud-AI re-validation), #68 (bucket taxonomy
  expansion for the same migrant-five role classes)
