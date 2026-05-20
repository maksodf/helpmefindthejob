<!-- SPDX-License-Identifier: Apache-2.0 -->

# Aïcha post-Bug-C re-walk — IMMEDIATE-SYNC TRIGGER

**Walked**: 2026-05-20 18:42 (local, UTC+2) — partial; halted on Bug E candidate
**Persona**: Aïcha (Tunisia → Berlin), slug `aicha`, cohort most-acute
**Server**: http://127.0.0.1:60178 (fresh data dir, cold cache)
**Provider**: Ollama llama3.1:8b at http://127.0.0.1:11434
**Residency status**: §16d AufenthG (visa for purpose of recognition of foreign qualification)
**Friction notes**: Recognition decision letter expected in ~4 months; needs Anerkennung-friendly employers willing to begin onboarding before the letter lands.

## Status — HALTED

Walk halted on **immediate-sync trigger**: a new root-cause bug was
discovered in the journey state-machine. Per operator directive
2026-05-20:

> IMMEDIATE-SYNC TRIGGERS (stop walk + surface to me before continuing):
> - A new root-cause bug discovered (Bug E candidate)

The bug is **reproducible offline** (no Ollama / no HTTP needed) — see
the trace in the "Bug E root cause" section below.

## What the walk captured (turns 1–9)

| # | Phase after | User input | Elapsed | Bug-C signal |
|---|---|---|---|---|
| 1 | `discover` | `/start` | 8 ms | — |
| 2 | `discover` | `Registered nurse` | 62 ms | — |
| 3 | `discover` | `Berlin` | 2 ms | — |
| 4 | `discover` | `7` | 1 ms | — |
| 5 | `cv_check` | `FR: native, AR: native, EN: B2` | 2 ms | — |
| 6 | `inspire` | _(Aïcha CV paste, 960 chars)_ | 2 ms | cv_check advanced cleanly |
| 7 | `preferences` | `no` (decline inspire laterals) | 1 ms | Bug-A fix worked |
| 8 | `review` | `none` (skip prefs) | 2960 ms | Bug-B fix worked; first search fired |
| 9 | `review` | `1` (pick first widening affordance) | 2793 ms | **empty-state hit**; widen_location picked |

**Working pieces verified live:**
- ✅ Bug A (Loop 1) — inspire-phase decline tokens accept "no" cleanly
- ✅ Bug B (Loop 2) — preferences advance guard accepts "none"
- ✅ Bug C piece 1 (Loop 3) — empty-state engaged on 0-results, not silent advance
- ✅ Bug C piece 2 (Loop 4) — diagnostic text surfaced ("no live postings…")
- ✅ Bug C piece 3 (Loop 5) — manual widening menu rendered with numbered affordances
- ✅ Bug C piece 3 — `apply_widening(WIDEN_LOCATION)` applied + journey re-saved
- ✅ Bug C piece 4 (Loop 6) — auto-relax slot offered in menu

**Bug-C signals at halt:**
| Signal | Observed | Why |
|---|---|---|
| Diagnostic text on empty-state | YES | piece 2 working |
| Ausländerbehörde caveat on widen-location | **NO** | **Bug F candidate** — see below |
| Adjacent-criterion count parenthetical | NO | cold-cache run; piece-5 expected behavior |
| Auto-relax slot offered | YES | piece 4 working |
| Final-state summary block | NO | never reached due to Bug E |
| Start-fresh bridge → DISCOVER_ASK_ROLE | NO | never reached |

## Bug E — root cause: `_advance_review` routing gap

**Reproduction** (offline, no HTTP / no Ollama):

```python
from company_discovery.journey import (
    UserJourney, advance, PHASE_REVIEW,
)
from company_discovery.widening import WIDEN_LOCATION

# Aïcha post-WIDEN_LOCATION, post-TRY_LATERALS-offer
j = UserJourney(
    phase=PHASE_REVIEW,
    review_substate="laterals_offered",
    role_text="Registered nurse",
    target_roles=["Registered nurse"],
    location="",
    applied_widenings=["widen_location"],
    proposed_laterals=["Senior Registered nurse",
                       "Lead Registered nurse",
                       "Assistant Registered nurse"],
    # No populated categories — Aïcha hit 0 results, then
    # the laterals-confirmation sub-state.
    search_results_by_category={},
)

# User types "1" — should pick lateral #1 via laterals-offered handler
result = advance(j, "1")
print(result.reply[:60])
# Expected: "OK — added 1 lateral role(s). Re-running search ..."
# Actual:   "I can also search these related role names: ..." (loop!)
```

**Root cause** in `company_discovery/journey.py` lines ~2651-2661
(`_advance_review`):

```python
def _advance_review(journey, msg, *, engine=None):
    # Routes review_substate="empty" to the right handler.
    if journey.review_substate == "empty":
        return _advance_review_empty(journey, msg, engine=engine)
    categories = list(journey.search_results_by_category.keys())
    if not categories:
        # Defensive: should not happen under the new empty-state
        # contract ... but if it does, route to the empty-state
        # branch rather than the old direct-to-PHASE_DONE.
        journey.review_substate = "empty"   # ←─── BUG: clobbers laterals_offered + auto_relax_offering
        return _advance_review_empty(journey, msg, engine=engine)
    ...
```

When `review_substate` is `"laterals_offered"` or `"auto_relax_offering"`,
the FIRST `if` (line 2651, checks for `"empty"` only) doesn't match.
Falls through to the `categories` check. For a Bug-C empty-state
recovery, `search_results_by_category` is always empty (the user is
in empty-state recovery because there were 0 results). The defensive
branch fires, **CLOBBERS** `review_substate` to `"empty"`, then routes
to `_advance_review_empty` — which now sees `"empty"` and dispatches
to the menu-handling code instead of the laterals_offered or
auto_relax_offering handler.

The user's `"1"` is then re-interpreted as picking the first menu
affordance (which is still TRY_LATERALS because the laterals_offered
handler never ran to mark TRY_LATERALS applied). `apply_widening(TRY_LATERALS)`
re-fires, returns `ask_confirm_laterals`, sets `review_substate="laterals_offered"`
again. Next turn the same loop fires.

**Severity**: blocks Bug C piece 3 (try_laterals confirmation flow) and
Bug C piece 4 (auto-relax confirmation flow) end-to-end. Pieces 5 and 6
also unreachable because the journey can't escape the laterals_offered
sub-state. Unit tests for Bug C passed because they call
`_advance_review_laterals_offered` / `_advance_review_auto_relax_offering`
directly, bypassing the outer `_advance_review` routing gap. Direct
sub-state tests pass; integration through `advance()` was never tested.

**Proposed fix** (one-line):

```python
def _advance_review(journey, msg, *, engine=None):
    # Any Bug-C sub-state routes to _advance_review_empty, which
    # owns the in-state dispatch. Categories check below is for
    # the populated-results review only (substate "").
    if journey.review_substate in (
        "empty", "laterals_offered", "auto_relax_offering",
    ):
        return _advance_review_empty(journey, msg, engine=engine)
    categories = list(journey.search_results_by_category.keys())
    if not categories:
        # True defensive: only fires when substate is "" AND
        # categories is empty (legitimate "broken state" recovery).
        journey.review_substate = "empty"
        return _advance_review_empty(journey, msg, engine=engine)
    ...
```

Plus a regression test pinning the exact scenario: substate=
"laterals_offered" + categories=[] + input "1" → laterals-offered
handler runs, not the menu handler.

## Bug F — persona_id-to-residency_status flow gap

**What I observed**: Aïcha's `visa_constrained` field stayed `False`
throughout the walk. This means:

- The Ausländerbehörde caveat on widen-location did NOT render
- The persona-aware affordance ordering (try_laterals first for
  constrained personas) was NOT applied — the unconstrained order
  was used (widen-location first)

**Root cause**: `UserProfile` has `persona_id` but no `residency_status`
field. The dispatcher at `app.py` ~line 3870-3877 looks up the
PersonaFixture for the user's `persona_id`, then reads its
`residency_status`, then classifies. But for a freshly-registered
test user:

- Default `persona_id = "healthcare-management"` (generic registry,
  not in the 7-persona fixture panel)
- `_persona_fixture_for("healthcare-management")` returns None or a
  non-migrant fixture with empty `residency_status`
- `classify_visa_constraint("")` returns False
- `journey.visa_constrained = False`

For a real production user typing "Registered nurse", the auto-
persona-switch at `app.py` ~line 3353 calls
`persona_for_bucket(bucket_key)` to map the role bucket to a persona.
If "nursing" bucket maps to a generic persona (e.g., "healthcare-
management"), the fixture won't have residency_status set.

**Severity**: Bug C piece 3's persona-aware design (constrained
ordering + Ausländerbehörde caveat) is silently inactive for live
users. The piece works correctly in unit tests where `visa_constrained=True`
is set directly on the test journey, but the production data flow
from registration → persona_id → residency_status → classify never
arrives at `True` for any persona without explicit `residency_status`
configuration.

**Possible fixes** (need operator direction):
1. Add `residency_status` field to `UserProfile`; populate via
   onboarding question + persist
2. Extend `_persona_fixture_for` so it falls through to a curated
   default residency lookup when no exact match (e.g., persona_id
   maps to constrained/unconstrained class)
3. Move the visa_constrained classification UPSTREAM into a profile-
   level field set during registration or first-search, not
   re-computed per empty-state entry

## What this means for Loop 9 / Loop 10

The original Aïcha shape-test (`aicha-shape-test.md`, pre-Bug-C) hit
the empty-state at turn 8 and routed to PHASE_DONE — that surface
behavior was Bug C piece 1's never-implicit-done gap. Bug C pieces
1-6 fixed the journey logic at the sub-state level, AND unit tests
(149 piece tests) verify each sub-state handler works correctly when
called directly.

**But the live walk surfaced that the OUTER routing in `_advance_review`
clobbers sub-state on the way IN** — so users in laterals_offered or
auto_relax_offering never reach the handlers piece 3 and piece 4
shipped.

This is the kind of evidence the operator predicted live walks
would surface vs. unit tests alone. Bug C pieces 1-6 close the
intended doctrine; Bug E + Bug F gap the live integration.

## Walk-script note (separate finding, low severity)

The walk's markdown writer crashed on Python 3.10's lack of `dt.UTC`
(introduced in 3.11+). Already fixed in
`scripts/post_bug_c_aicha_walk.py` (use `dt.timezone.utc`). The walk
itself ran to 60 turns and captured the loop; the crash was after
data capture during MD rendering.

## Direction needed

Pause Loop 9 closure pending operator verdict on:

1. **Bug E** — apply the one-line fix to `_advance_review` + regression
   test, then re-walk Aïcha? Or accept and defer to a coordinated fix
   slice?
2. **Bug F** — surface the persona_id-to-residency_status gap as a
   separate root-cause investigation (which fix path: profile field,
   fixture fallback, or upstream classify)?
3. **Loop 9 closure framing** — does this evidence file close Loop 9
   as-is (with Bug E + Bug F surfaced), with re-walk gated on the
   fixes? Or extend Loop 9 to also include the fixes inline before
   the re-walk?

Walk script + harness are working correctly; the dt.UTC crash is fixed.
A second walk can be launched immediately once Bug E lands.
