# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 1 — empty-state review phase contract.

Origin: Aïcha shape-test (2026-05-20) turn 8 surfaced that the
aggregator's 0-results outcome routed straight to PHASE_DONE,
dead-ending the user with no recovery path. Operator-approved
top-tier spec for Bug C is a 6-piece workstream (empty-state phase,
diagnostic engine, persona-aware widening, consented auto-relax,
adjacent-criterion counts, final-state recovery). Piece 1 builds
the foundation: a never-implicit-done empty-state phase that other
pieces layer onto.

This test pins the piece 1 contract:
  - 0-results → review.empty_state (NOT PHASE_DONE)
  - Explicit give-up tokens → PHASE_DONE
  - Explicit retry tokens → re-fire search (run_search_with present)
  - Empty / whitespace / gibberish → re-ask, never advance/exit
  - Loop-back invariant: retry → still 0 → back to empty_state
  - Never-implicit-done invariant: across every unrecognized
    input, journey.phase != PHASE_DONE after the turn
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    PHASE_DONE,
    PHASE_REVIEW,
    UserJourney,
    _advance_review,
    _advance_review_empty,
    _format_review_empty_reply,
)


def _empty_state_journey() -> UserJourney:
    """Journey in PHASE_REVIEW.empty — what app.py sets after the
    aggregator returns 0 results."""
    j = UserJourney(phase=PHASE_REVIEW)
    j.target_roles = ["Registered nurse"]
    j.location = "Berlin"
    j.review_substate = "empty"
    return j


class EmptyStateRoutingTests(unittest.TestCase):
    """Aggregator 0-results MUST land in review.empty_state, not
    PHASE_DONE."""

    def test_empty_state_journey_routes_to_empty_handler(self) -> None:
        """When review_substate='empty', _advance_review dispatches
        to _advance_review_empty (verified indirectly via the
        empty-state reply shape)."""
        j = _empty_state_journey()
        result = _advance_review(j, "")
        # The empty-state reply contains the action_prompt skeleton
        self.assertIn("retry", result.reply.lower())
        self.assertIn("give up", result.reply.lower())
        self.assertIn("nochmal", result.reply.lower())

    def test_empty_state_persists_phase_review(self) -> None:
        """Empty-state journey stays in PHASE_REVIEW, not PHASE_DONE,
        on any non-give-up input."""
        for inp in ("", "huh", "?", "1", "anything else"):
            with self.subTest(inp=inp):
                j = _empty_state_journey()
                result = _advance_review(j, inp)
                self.assertEqual(
                    result.journey.phase,
                    PHASE_REVIEW,
                    f"input {inp!r} must not exit PHASE_REVIEW",
                )
                self.assertNotEqual(
                    result.journey.phase,
                    PHASE_DONE,
                    f"input {inp!r} must NEVER implicitly land in PHASE_DONE",
                )


class GiveUpTokensTests(unittest.TestCase):
    """Explicit give-up tokens route to PHASE_DONE — and only those."""

    GIVE_UP_TOKENS = (
        "give up", "done", "fertig", "exit", "quit", "stop",
        "end", "ende", "abbruch", "abbrechen",
    )

    def test_each_token_lands_in_done(self) -> None:
        for token in self.GIVE_UP_TOKENS:
            with self.subTest(token=token):
                j = _empty_state_journey()
                result = _advance_review_empty(j, token)
                self.assertEqual(
                    result.journey.phase,
                    PHASE_DONE,
                    f"token {token!r} must route to PHASE_DONE",
                )
                self.assertTrue(result.done)
                # review_substate cleared on exit (hygiene)
                self.assertEqual(result.journey.review_substate, "")


class RetryTokensTests(unittest.TestCase):
    """Explicit retry tokens re-fire the search (run_search_with
    populated). Loop-back invariant: if still 0, app.py routes back
    to empty_state. We pin the re-fire shape here; the loop-back
    closure is integration-level."""

    RETRY_TOKENS = (
        "retry", "search again", "try again", "again",
        "nochmal", "noch einmal", "wieder versuchen",
        "erneut", "neu suchen",
    )

    def test_each_token_refires_search(self) -> None:
        for token in self.RETRY_TOKENS:
            with self.subTest(token=token):
                j = _empty_state_journey()
                j.salary_floor = 50000
                j.company_size = "startup"
                result = _advance_review_empty(j, token)
                self.assertIsNotNone(
                    result.run_search_with,
                    f"token {token!r} must fire the search dispatch",
                )
                # Re-fired criteria match current journey state
                self.assertEqual(
                    result.run_search_with["target_roles"],
                    ["Registered nurse"],
                )
                self.assertEqual(result.run_search_with["location"], "Berlin")
                self.assertEqual(result.run_search_with["salary_floor"], 50000)
                # Journey stays in PHASE_REVIEW pending the dispatch
                # outcome (app.py will set substate based on results)
                self.assertEqual(result.journey.phase, PHASE_REVIEW)

    def test_loop_back_invariant_shape(self) -> None:
        """If app.py's 0-results branch sets review_substate='empty'
        again after a retry, the next user turn lands here with the
        same handler. This pins that the journey state shape stays
        consistent across a retry → 0 → empty_state loop."""
        j = _empty_state_journey()
        retry_result = _advance_review_empty(j, "retry")
        # Simulate app.py: search returns 0 again, sets
        # review_substate="empty" — _advance_review must still
        # dispatch to _advance_review_empty.
        retry_result.journey.review_substate = "empty"
        next_turn = _advance_review(retry_result.journey, "")
        self.assertIn("retry", next_turn.reply.lower())
        self.assertEqual(next_turn.journey.phase, PHASE_REVIEW)


class EmptyAndWhitespaceReasksTests(unittest.TestCase):
    """Mirror Bug B's empty-input guard at this phase too."""

    def test_empty_string_reasks(self) -> None:
        j = _empty_state_journey()
        result = _advance_review_empty(j, "")
        self.assertEqual(result.journey.phase, PHASE_REVIEW)
        self.assertIsNone(result.run_search_with)
        self.assertFalse(result.persist)
        self.assertIn("retry", result.reply.lower())

    def test_whitespace_only_reasks(self) -> None:
        for ws in (" ", "   ", "\t", "\n", "  \t \n  "):
            with self.subTest(ws=repr(ws)):
                j = _empty_state_journey()
                result = _advance_review_empty(j, ws)
                self.assertEqual(result.journey.phase, PHASE_REVIEW)
                self.assertIsNone(result.run_search_with)


class UnrecognizedInputReasksTests(unittest.TestCase):
    """Gibberish / question-marks / numeric ambiguity — re-ask,
    never silently advance, never silently exit."""

    # Inputs that have NO piece-3 menu meaning. Numeric inputs (1, 2,
    # 3, ...) are deliberately omitted: piece 3 numbers them as
    # widening / retry / give-up menu choices, so a numeric "1" is
    # potentially a valid menu pick depending on what's offered.
    # See test_each_persona_expected_affordance_list in
    # test_widening.py for per-persona numeric semantics; this test
    # focuses on text inputs that should still re-ask.
    UNRECOGNIZED = (
        "?", "huh", "what", "what?", "help",
        "ok", "okay", "yes", "yeah", "ja", "no", "nein",
        "asdf", "xyz", "keine Ahnung", "weiß nicht",
        # Preference-phase tokens that should NOT advance from
        # empty_state (they belong in PHASE_PREFS):
        "min 50k", "startup",
        # "remote" is in widening's _WIDEN_LOCATION_TOKENS to handle
        # the "anywhere" remote-search intent inline — but it would
        # only match when WIDEN_LOCATION is in offered affordances.
        # For test fixtures with location set, widen_location IS
        # offered, so "remote" would match. Omit from this test.
    )

    def test_each_reasks(self) -> None:
        for inp in self.UNRECOGNIZED:
            with self.subTest(inp=inp):
                j = _empty_state_journey()
                result = _advance_review_empty(j, inp)
                self.assertEqual(
                    result.journey.phase,
                    PHASE_REVIEW,
                    f"input {inp!r} must not exit PHASE_REVIEW",
                )
                self.assertIsNone(
                    result.run_search_with,
                    f"input {inp!r} must not fire the search",
                )
                self.assertFalse(result.persist)

    def test_never_implicit_done_invariant(self) -> None:
        """Operator's headline invariant: across every unrecognized
        input, journey.phase != PHASE_DONE after the turn."""
        for inp in self.UNRECOGNIZED:
            with self.subTest(inp=inp):
                j = _empty_state_journey()
                result = _advance_review_empty(j, inp)
                self.assertNotEqual(
                    result.journey.phase,
                    PHASE_DONE,
                    f"input {inp!r} caused implicit PHASE_DONE — violates "
                    f"the never-implicit-done invariant",
                )


class DiagnosticSeamTests(unittest.TestCase):
    """Piece 2 attachment point — the helper accepts a diagnostic
    text prefix and composes correctly. Pinned in piece 1 so piece 2
    only needs to fill the value, not restructure the reply."""

    def test_empty_diagnostic_omits_prefix(self) -> None:
        j = _empty_state_journey()
        reply = _format_review_empty_reply(j, diagnostic_text="")
        # No leading newlines from an empty diagnostic
        self.assertFalse(reply.startswith("\n"))
        # Piece 2 wording: "No matches found" (strict-fact fallback)
        self.assertIn("No matches found", reply)

    def test_diagnostic_text_replaces_fallback(self) -> None:
        """Piece 2 contract change: when diagnostic_text is provided,
        it REPLACES the strict-fact fallback (it doesn't prepend to
        it). Pre-piece-2 the action prompt embedded the 'No jobs
        found' line; piece 2 split lead vs. action so the diagnostic
        is the lead when present, fallback otherwise."""
        j = _empty_state_journey()
        diag = (
            "No matches found for **Registered nurse** in **Berlin**. "
            "Recent searches without the seniority qualifier returned "
            "**47 posting(s)** for **nurse** in **Berlin**."
        )
        reply = _format_review_empty_reply(j, diagnostic_text=diag)
        # Diagnostic appears first
        self.assertTrue(reply.startswith(diag))
        # Action prompt is appended after a blank line
        self.assertIn("What next?", reply)
        self.assertIn("retry", reply)


if __name__ == "__main__":
    unittest.main()
