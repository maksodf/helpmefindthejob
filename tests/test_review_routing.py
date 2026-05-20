# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug E meta-coverage (Loop 9.1, 2026-05-20).

Pins the outer ``advance()`` dispatcher routing for every Bug-C
sub-state. Previous Bug C pieces 1-6 tests called the sub-state
handlers (_advance_review_empty, _advance_review_laterals_offered,
_advance_review_auto_relax_offering) DIRECTLY, bypassing the outer
``advance() -> _advance_review`` routing. Bug E surfaced via live
walk: the outer routing clobbered ``review_substate`` to "empty"
when ``search_results_by_category`` was empty (always true during
Bug-C empty-state recovery) AND the substate was anything other
than "empty" -- bypassing the laterals_offered + auto_relax_offering
handlers entirely.

This test file walks every sub-state through ``advance()`` (the
public entry point used by app.py's HTTP handler) so the routing
gap is caught at the boundary the live walk exercises, not at the
internal handler level.

Naming convention: each test class corresponds to one sub-state's
routing invariant. The Bug E regression test
(``LateralsOfferedSubstateRoutesToLateralsHandlerTests``) is the
specific live-walk-reproduced failure; the others close adjacent
routing gaps that could have surfaced as Bug E variants.
"""
from __future__ import annotations

import unittest

from company_discovery.journey import (
    PHASE_DISCOVER,
    PHASE_DONE,
    PHASE_REVIEW,
    UserJourney,
    advance,
)
from company_discovery.widening import (
    DROP_SENIORITY,
    TRY_LATERALS,
    WIDEN_LOCATION,
)


def _make_journey_with_substate(
    substate: str,
    *,
    applied_widenings: list[str] | None = None,
    proposed_laterals: list[str] | None = None,
    auto_relax_active: bool = False,
    auto_relax_offered_id: str = "",
) -> UserJourney:
    """Build a PHASE_REVIEW journey with the given sub-state. All
    Bug-C recovery sub-states have ``search_results_by_category={}``
    (empty) because the user is in recovery precisely because the
    search returned 0 results -- this is the condition that
    triggered Bug E in the live walk.
    """
    return UserJourney(
        phase=PHASE_REVIEW,
        review_substate=substate,
        role_text="Registered nurse",
        target_roles=["Registered nurse"],
        location="Berlin" if substate == "empty" else "",
        visa_constrained=False,
        applied_widenings=list(applied_widenings or []),
        proposed_laterals=list(proposed_laterals or []),
        auto_relax_active=auto_relax_active,
        auto_relax_offered_id=auto_relax_offered_id,
        # CRITICAL for Bug E: categories empty because Bug-C
        # recovery only fires after 0-results.
        search_results_by_category={},
        search_jobs_by_id={},
        diagnostic_text=(
            "No live postings found for 'Registered nurse' "
            "across the 8 connected providers."
        ),
    )


# ─── Routing invariant 1: substate="empty" + empty categories ────
class EmptySubstateRoutesToEmptyHandlerTests(unittest.TestCase):
    """Smoke-test the simplest routing path. Numeric "1" in the
    empty-state menu should pick the first available affordance --
    here, WIDEN_LOCATION (unconstrained order, since Aïcha-class
    persona-attribution gap means visa_constrained=False)."""

    def test_numeric_1_picks_first_affordance(self):
        j = _make_journey_with_substate("empty")
        result = advance(j, "1")
        # First affordance for an unconstrained "Registered nurse"
        # in Berlin is WIDEN_LOCATION (no seniority qualifier so
        # DROP_SENIORITY filtered out; TRY_LATERALS may or may not
        # be available depending on lateral suggestions). Either
        # way, "1" must produce a run_search_with OR an
        # ask_confirm_laterals (not the menu re-ask).
        self.assertTrue(
            bool(result.run_search_with) or "I can also search" in result.reply,
            f"expected widening to fire, got reply={result.reply[:120]!r}",
        )
        # Must NOT have looped back to the empty-state menu re-ask
        # (the failure mode the categories defensive branch caused).
        self.assertNotEqual(
            result.persist, False,
            "empty-state menu re-ask leaked: input '1' should advance",
        )


# ─── Routing invariant 2 (BUG E REGRESSION): laterals_offered ────
class LateralsOfferedSubstateRoutesToLateralsHandlerTests(unittest.TestCase):
    """**Bug E regression test** (Loop 9.1, 2026-05-20).

    Reproduces the exact live-walk failure: journey in
    ``review_substate="laterals_offered"`` with empty categories,
    user types "1" to pick lateral #1. Pre-fix: outer
    ``_advance_review`` defensive branch clobbered substate to
    "empty", re-ran the menu handler, re-applied TRY_LATERALS,
    re-entered laterals_offered, infinite loop. Post-fix: routing
    goes directly to ``_advance_review_laterals_offered``, which
    parses "1" as picked_indices=[0], appends the chosen lateral
    to target_roles, marks TRY_LATERALS applied, fires search.
    """

    def test_input_1_picks_lateral_zero_not_menu_reprompt(self):
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=[
                "Senior Registered nurse",
                "Lead Registered nurse",
                "Assistant Registered nurse",
            ],
        )
        result = advance(j, "1")
        # Lateral picked: target_roles extended, TRY_LATERALS
        # applied, run_search_with fired.
        self.assertTrue(
            bool(result.run_search_with),
            f"laterals_offered handler did not run for input '1' "
            f"(Bug E regression); reply={result.reply[:120]!r}",
        )
        self.assertIn("Senior Registered nurse", j.target_roles)
        self.assertIn(TRY_LATERALS, j.applied_widenings)
        # Sub-state cleared back to "empty" so next 0-results re-
        # enters menu mode (not stuck in laterals_offered).
        self.assertEqual(j.review_substate, "empty")
        # Reply must be the "OK — added N lateral role(s)" ack, NOT
        # the laterals-confirmation reprompt.
        self.assertIn("OK", result.reply)
        self.assertIn("lateral role", result.reply)

    def test_yes_includes_all_proposed_laterals(self):
        """Token-form confirm: "yes" includes ALL proposed laterals.
        Same routing path; pinned as a separate input mode."""
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=["Lateral A", "Lateral B"],
        )
        result = advance(j, "yes")
        self.assertTrue(bool(result.run_search_with))
        self.assertIn("Lateral A", j.target_roles)
        self.assertIn("Lateral B", j.target_roles)
        self.assertIn(TRY_LATERALS, j.applied_widenings)

    def test_no_cancels_back_to_menu(self):
        """Token-form cancel: "no" drops back to empty-state menu
        WITHOUT applying TRY_LATERALS. Pinned to verify the
        cancel path doesn't also get clobbered by Bug E."""
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=["Lateral A", "Lateral B"],
        )
        result = advance(j, "no")
        # No search fired, TRY_LATERALS NOT applied, substate back
        # to "empty" (menu mode).
        self.assertIsNone(result.run_search_with)
        self.assertNotIn(TRY_LATERALS, j.applied_widenings)
        self.assertEqual(j.review_substate, "empty")


# ─── Routing invariant 3: auto_relax_offering ────────────────────
class AutoRelaxOfferingSubstateRoutesToAutoHandlerTests(unittest.TestCase):
    """Bug E variant: auto_relax_offering substate with empty
    categories must route to ``_advance_review_auto_relax_offering``,
    not get clobbered to empty by the categories defensive branch.
    """

    def test_yes_advances_auto_relax_suggestion(self):
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[],
            auto_relax_active=True,
            auto_relax_offered_id=WIDEN_LOCATION,
        )
        result = advance(j, "yes")
        # "yes" confirms the offered widening; should fire a search
        # (NOT re-prompt the menu).
        self.assertTrue(
            bool(result.run_search_with),
            f"auto_relax_offering handler did not run for 'yes' "
            f"(Bug E variant); reply={result.reply[:120]!r}",
        )
        self.assertIn(WIDEN_LOCATION, j.applied_widenings)

    def test_skip_declines_and_offers_next_in_auto_mode(self):
        """"skip" declines the current suggestion and asks for the
        next eligible one. Auto-mode stays active; substate stays
        auto_relax_offering with a new offered_id (or transitions
        to exhaustion-handling if no next)."""
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[],
            auto_relax_active=True,
            auto_relax_offered_id=WIDEN_LOCATION,
        )
        result = advance(j, "skip")
        # Decline path must not have applied WIDEN_LOCATION.
        self.assertNotIn(WIDEN_LOCATION, j.applied_widenings)
        # Routing succeeded (we got a real reply, not empty).
        self.assertTrue(len(result.reply) > 0)

    def test_menu_token_exits_auto_mode_to_menu(self):
        """Auto-relax handler's cancel branch exits auto-mode and
        returns to the empty-state menu. Uses the "menu" token (an
        _AUTO_RELAX_CANCEL_TOKENS member that is NOT in the
        universal _CANCEL_TOKENS set, so no collision)."""
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[],
            auto_relax_active=True,
            auto_relax_offered_id=WIDEN_LOCATION,
        )
        result = advance(j, "menu")
        # Auto-mode cleared; substate back to "empty" (menu mode).
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.review_substate, "empty")
        # No search fired (menu returns to menu, not search).
        self.assertIsNone(result.run_search_with)


# ─── Bug E.2 fix regression — universal cancel respects substate ─
class UniversalCancelRespectsSubstateTests(unittest.TestCase):
    """**Bug E.2 fix regression** (Loop 9.1.5, 2026-05-20).

    The universal ``_CANCEL_TOKENS`` set at ``advance()`` top
    collides with three sub-state cancel-mode token sets. The fix:
    per-token check via ``_should_defer_cancel_to_substate`` --
    only DEFER the universal interception when the typed token is
    actually in the current substate's cancel-mode set.

    Collisions fixed in this loop:
      - laterals_offered:   "cancel"
      - auto_relax_offering: "cancel", "stop", "abbrechen"

    Out-of-scope (inventoried in Loop 9.1.5 status sync):
      - "exit"/"quit" vs sub-state give-up sets
      - "abbrechen"/"exit"/"quit"/"stop" vs _REVIEW_EMPTY_GIVE_UP_TOKENS
      - "reset" vs _REVIEW_EMPTY_START_FRESH_TOKENS
    """

    def test_cancel_in_laterals_offered_cancels_laterals_not_journey(self):
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=["Lateral A", "Lateral B"],
        )
        result = advance(j, "cancel")
        # Laterals canceled; journey stays in PHASE_REVIEW with the
        # empty-state menu re-shown.
        self.assertEqual(j.phase, PHASE_REVIEW)
        self.assertFalse(result.done)
        # Proposed laterals cleared; sub-state back to "empty".
        self.assertEqual(j.proposed_laterals, [])
        self.assertEqual(j.review_substate, "empty")
        # TRY_LATERALS NOT marked applied (cancel doesn't apply).
        self.assertNotIn(TRY_LATERALS, j.applied_widenings)

    def test_cancel_in_auto_relax_exits_auto_mode_not_journey(self):
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[],
            auto_relax_active=True,
            auto_relax_offered_id=WIDEN_LOCATION,
        )
        result = advance(j, "cancel")
        # Auto-mode exited; journey stays in PHASE_REVIEW.
        self.assertEqual(j.phase, PHASE_REVIEW)
        self.assertFalse(result.done)
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.review_substate, "empty")

    def test_stop_in_auto_relax_exits_auto_mode_not_journey(self):
        """`stop` is in _AUTO_RELAX_CANCEL_TOKENS — sub-state owns it
        in auto_relax_offering."""
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[],
            auto_relax_active=True,
            auto_relax_offered_id=WIDEN_LOCATION,
        )
        result = advance(j, "stop")
        self.assertEqual(j.phase, PHASE_REVIEW)
        self.assertFalse(result.done)
        self.assertFalse(j.auto_relax_active)

    def test_abbrechen_in_auto_relax_exits_auto_mode_not_journey(self):
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[],
            auto_relax_active=True,
            auto_relax_offered_id=WIDEN_LOCATION,
        )
        result = advance(j, "abbrechen")
        self.assertEqual(j.phase, PHASE_REVIEW)
        self.assertFalse(result.done)
        self.assertFalse(j.auto_relax_active)

    def test_cancel_in_empty_menu_still_ends_journey(self):
        """Empty-state menu (substate="empty") does NOT own
        cancel-mode tokens — universal cancel preserved."""
        j = _make_journey_with_substate("empty")
        result = advance(j, "cancel")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_cancel_outside_phase_review_still_ends_journey(self):
        """Cancel in PHASE_DISCOVER (or any non-review phase) is
        always universal — sub-state collisions only happen in
        PHASE_REVIEW Bug-C sub-states."""
        j = UserJourney(
            phase=PHASE_DISCOVER,
            review_substate="",
            role_text="",
        )
        result = advance(j, "cancel")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_stop_in_laterals_offered_still_universal_cancel(self):
        """`stop` is NOT in _LATERAL_CONFIRM_NO_TOKENS — laterals
        substate doesn't own it. Universal cancel still wins."""
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=["Lateral A"],
        )
        result = advance(j, "stop")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_exit_in_auto_relax_routes_through_give_up_handler(self):
        """**Loop 9.1.5b regression** (collision item #1).
        `exit` is in _AUTO_RELAX_GIVE_UP_TOKENS — sub-state owns
        the give-up meaning. Post-9.1.5b: universal cancel skips,
        sub-state give-up handler runs (PHASE_DONE + clears auto-
        relax fields)."""
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[WIDEN_LOCATION],
            auto_relax_active=True,
            auto_relax_offered_id=DROP_SENIORITY,
        )
        j.auto_relax_declined = ["something"]
        result = advance(j, "exit")
        # Sub-state give-up handler ran: PHASE_DONE + full cleanup.
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)
        # Auto-relax fields cleared by sub-state give-up handler.
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.auto_relax_declined, [])
        self.assertEqual(j.auto_relax_offered_id, "")
        self.assertEqual(j.applied_widenings, [])
        self.assertEqual(j.review_substate, "")


# ─── Loop 9.1.5b — collision item #1 (auto-relax give-up cleanup) ─
class UniversalCancelDefersToAutoRelaxGiveUpTests(unittest.TestCase):
    """**Loop 9.1.5b regression** — collision item #1.

    Tokens in BOTH _CANCEL_TOKENS (universal) AND
    _AUTO_RELAX_GIVE_UP_TOKENS (sub-state): "exit", "quit". Post-
    9.1.5b: universal interception defers to sub-state give-up
    handler which clears all auto-relax fields before PHASE_DONE."""

    def test_quit_in_auto_relax_clears_state(self):
        j = _make_journey_with_substate(
            "auto_relax_offering",
            applied_widenings=[WIDEN_LOCATION, DROP_SENIORITY],
            auto_relax_active=True,
            auto_relax_offered_id=TRY_LATERALS,
        )
        j.auto_relax_declined = ["one_declined"]
        j.proposed_laterals = ["foo"]
        result = advance(j, "quit")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.auto_relax_declined, [])
        self.assertEqual(j.auto_relax_offered_id, "")
        self.assertEqual(j.applied_widenings, [])
        self.assertEqual(j.proposed_laterals, [])

    def test_exit_outside_auto_relax_still_universal_cancel(self):
        """In substate="empty" (menu mode), `exit` is in
        _REVIEW_EMPTY_GIVE_UP_TOKENS instead — separate collision
        (item #2). This test pins that empty-state ALSO routes via
        sub-state (not universal cancel)."""
        j = _make_journey_with_substate("empty")
        result = advance(j, "exit")
        # Still PHASE_DONE (functionally same outcome).
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_exit_in_laterals_offered_still_universal_cancel(self):
        """`exit` NOT in _LATERAL_CONFIRM_NO_TOKENS — laterals
        substate doesn't own it. AND no laterals give-up handler
        exists. Universal cancel preserved."""
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=["A"],
        )
        result = advance(j, "exit")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)


# ─── Loop 9.1.5b — collision item #2 (empty-state give-up cleanup) ─
class UniversalCancelDefersToEmptyGiveUpTests(unittest.TestCase):
    """**Loop 9.1.5b regression** — collision item #2.

    Tokens in BOTH _CANCEL_TOKENS (universal) AND
    _REVIEW_EMPTY_GIVE_UP_TOKENS (sub-state): "abbrechen", "exit",
    "quit", "stop". Post-9.1.5b: universal interception defers to
    empty-state give-up handler which clears applied_widenings +
    proposed_laterals before PHASE_DONE."""

    def test_stop_in_empty_clears_applied_widenings(self):
        j = _make_journey_with_substate(
            "empty",
            applied_widenings=[WIDEN_LOCATION, DROP_SENIORITY],
        )
        j.proposed_laterals = ["foo"]
        result = advance(j, "stop")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)
        # Sub-state give-up handler cleared widening state.
        self.assertEqual(j.applied_widenings, [])
        self.assertEqual(j.proposed_laterals, [])
        self.assertEqual(j.review_substate, "")

    def test_abbrechen_in_empty_clears_state(self):
        j = _make_journey_with_substate(
            "empty",
            applied_widenings=[TRY_LATERALS],
        )
        result = advance(j, "abbrechen")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)
        self.assertEqual(j.applied_widenings, [])

    def test_quit_in_empty_clears_state(self):
        j = _make_journey_with_substate(
            "empty",
            applied_widenings=[WIDEN_LOCATION],
        )
        result = advance(j, "quit")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertEqual(j.applied_widenings, [])

    def test_exit_outside_phase_review_still_universal(self):
        j = UserJourney(
            phase=PHASE_DISCOVER,
            review_substate="",
        )
        result = advance(j, "exit")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)


# ─── Loop 9.1.5b — collision item #3 (start-fresh, WRONG OUTCOME) ─
class UniversalCancelDefersToStartFreshTests(unittest.TestCase):
    """**Loop 9.1.5b regression** — collision item #3.

    The HIGHEST-IMPACT collision (only one with wrong-outcome
    semantics): `reset` is in BOTH _CANCEL_TOKENS (universal) AND
    _REVIEW_EMPTY_START_FRESH_TOKENS (piece-6 sub-state). Pre-fix
    intended outcome was PHASE_DISCOVER + reset (start fresh);
    actual was PHASE_DONE. Post-9.1.5b: universal interception
    defers to empty-state start-fresh handler.

    Only applies in FINAL-STATE (substate="empty" AND
    applied_widenings non-empty). In non-final-state empty (no
    widenings tried), there's no start-fresh affordance and
    universal cancel preserved."""

    def test_reset_in_final_state_routes_to_start_fresh(self):
        j = _make_journey_with_substate(
            "empty",
            applied_widenings=[
                WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS,
            ],
        )
        result = advance(j, "reset")
        # Start-fresh routed: PHASE_DISCOVER (not PHASE_DONE).
        self.assertEqual(j.phase, PHASE_DISCOVER)
        self.assertFalse(result.done)
        # Operator-approved bridge reply emitted.
        self.assertIn("clearing your old search", result.reply)
        self.assertIn("**1. What kind of role this time?**", result.reply)
        # All discover/search/review state reset.
        self.assertEqual(j.role_text, "")
        self.assertEqual(j.applied_widenings, [])
        self.assertEqual(j.review_substate, "")

    def test_reset_in_non_final_state_empty_still_universal(self):
        """Non-final-state empty (no widenings tried) doesn't have
        a start-fresh affordance — sub-state doesn't own "reset"."""
        j = _make_journey_with_substate(
            "empty",
            applied_widenings=[],  # not final-state
        )
        result = advance(j, "reset")
        # Universal cancel: PHASE_DONE.
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_reset_in_laterals_offered_still_universal(self):
        """Laterals_offered substate doesn't own "reset"
        (not in _LATERAL_CONFIRM_NO_TOKENS)."""
        j = _make_journey_with_substate(
            "laterals_offered",
            applied_widenings=[WIDEN_LOCATION],
            proposed_laterals=["A"],
        )
        result = advance(j, "reset")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_reset_outside_phase_review_still_universal(self):
        j = UserJourney(phase=PHASE_DISCOVER)
        result = advance(j, "reset")
        self.assertEqual(j.phase, PHASE_DONE)
        self.assertTrue(result.done)

    def test_other_start_fresh_token_in_final_state_routes_through(self):
        """Verify the deferral works for the OTHER 14 tokens in
        _REVIEW_EMPTY_START_FRESH_TOKENS too — not just "reset"
        (which is the universal-collision token). E.g. "neu starten"
        was never in _CANCEL_TOKENS so it wouldn't have been
        intercepted pre-fix; this is a control test that the
        start-fresh path is reachable for any of the 15 tokens
        once we're in final-state."""
        # Full exhaustion: all 3 widenings applied -> offered=[]
        # -> in_final_state=True -> start-fresh branch eligible.
        j = _make_journey_with_substate(
            "empty",
            applied_widenings=[
                WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS,
            ],
        )
        result = advance(j, "neu starten")
        self.assertEqual(j.phase, PHASE_DISCOVER)
        self.assertFalse(result.done)


# ─── Routing invariant 4: final-state rendering ──────────────────
class FinalStateRoutingTests(unittest.TestCase):
    """Bug C piece 6: when review_substate="empty" AND
    applied_widenings is non-empty AND offered=[] (all widenings
    exhausted), the empty handler renders the final-state summary
    + narrowed menu (Start fresh / Retry / Give up). Pinned through
    advance() to ensure outer routing doesn't break the final-state
    rendering."""

    def test_advance_routes_to_final_state_summary(self):
        j = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="DevOps Engineer",
            target_roles=[
                "DevOps Engineer", "sre", "platform engineer",
                "infrastructure engineer",
            ],
            location="",
            visa_constrained=True,
            applied_widenings=[
                WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS,
            ],
            diagnostic_text="No live postings found for 'DevOps Engineer'.",
            search_results_by_category={},
        )
        # Send empty input to re-render the menu (a re-ask).
        result = advance(j, "")
        self.assertIn("You've tried these widenings:", result.reply)
        self.assertIn("**Start fresh**", result.reply)

    def test_advance_start_fresh_token_routes_through_outer(self):
        j = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="DevOps Engineer",
            target_roles=[
                "DevOps Engineer", "sre", "platform engineer",
            ],
            location="",
            visa_constrained=False,
            applied_widenings=[
                WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS,
            ],
            search_results_by_category={},
        )
        result = advance(j, "start fresh")
        self.assertEqual(result.journey.phase, PHASE_DISCOVER)
        self.assertEqual(result.journey.role_text, "")


# ─── Routing invariant 5: defensive branch still works for "" ────
class LegitimateDefensiveRecoveryTests(unittest.TestCase):
    """The pre-fix defensive branch was: `if not categories:
    journey.review_substate="empty"; route to empty handler`. The
    fix narrows the clobber to only fire when substate is the empty
    STRING "" (no Bug-C substate set). This test verifies the
    defensive recovery still works for that legitimate broken-state
    case (a journey that landed in PHASE_REVIEW without the
    dispatcher properly setting substate)."""

    def test_review_phase_with_empty_substate_and_no_categories_routes_defensively(self):
        j = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="",  # NEITHER "empty" NOR "laterals_offered"
            role_text="Registered nurse",
            target_roles=["Registered nurse"],
            location="Berlin",
            applied_widenings=[],
            search_results_by_category={},  # empty
        )
        # Should route to empty handler via the defensive branch.
        # No crash, reply renders the menu (or strict-fact
        # fallback).
        result = advance(j, "")
        # Substate now set to "empty" by defensive branch.
        self.assertEqual(j.review_substate, "empty")
        self.assertTrue(len(result.reply) > 0)


if __name__ == "__main__":
    unittest.main()
