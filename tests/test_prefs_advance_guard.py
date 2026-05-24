# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug B regression test — preferences phase advance guard.

Origin: Aïcha shape-test (2026-05-20) drove the full 12-phase journey
and surfaced Bug B at turn 8: sending "1" at the preferences prompt
(intended as a category-pick from a not-yet-shown menu) silently
advanced to PHASE_SEARCH and fired the aggregator. The diagnostic
test matrix confirmed _advance_prefs auto-advanced on 100% of 38
tested inputs — empty string, gibberish ("huh"), category-pick
attempts, and real preferences all triggered the same path.

Fix shape (operator-approved):
  1. Empty / whitespace-only inputs always re-ask (explicit early-
     return at top of _advance_prefs).
  2. Advance only when (a) explicit advance token, OR (b) at least
     one recognized preference extracted (remote / salary / size).
     Otherwise re-ask, do NOT silently advance.
  3. Salary regex widened from \\d{2,3} to \\d{2,5} so real €
     amounts (1000, 50000) parse correctly.

This test pins the behavioural invariant: each input category lands
in the correct branch (advance / preference-extract / re-ask).
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    PHASE_PREFS,
    PHASE_SEARCH,
    UserJourney,
    _advance_prefs,
)


def _fresh_journey() -> UserJourney:
    j = UserJourney(phase=PHASE_PREFS)
    j.target_roles = ["Registered nurse"]
    j.location = "Berlin"
    return j


class EmptyInputReasksTests(unittest.TestCase):
    """Operator-required explicit guard: empty / whitespace-only
    inputs MUST re-ask, never advance."""

    def test_empty_string_reasks(self) -> None:
        result = _advance_prefs(_fresh_journey(), "")
        self.assertEqual(
            result.journey.phase,
            PHASE_PREFS,
            "empty string must NOT advance phase",
        )
        self.assertIsNone(result.run_search_with)
        self.assertFalse(result.persist)

    def test_whitespace_only_reasks(self) -> None:
        for ws in (" ", "   ", "\t", "\n", "  \t \n  "):
            with self.subTest(ws=repr(ws)):
                result = _advance_prefs(_fresh_journey(), ws)
                self.assertEqual(
                    result.journey.phase,
                    PHASE_PREFS,
                    f"whitespace-only {ws!r} must NOT advance",
                )
                self.assertIsNone(result.run_search_with)


class AdvanceTokenTests(unittest.TestCase):
    """Each widened advance token must clear the preferences phase
    without setting any preference (user explicitly declined)."""

    ADVANCE_TOKENS = (
        # Pre-Bug-B tokens (regression-pinned):
        "none",
        "skip",
        "no preference",
        "nothing",
        # Added in Bug B fix (operator spec 2026-05-20):
        "nope",
        "no thanks",
        "keine",
        "nichts",
        "kein bedarf",
        "nein danke",
        "weiter",
        "next",
        "move on",
        "go",
        "fertig",
        "done",
        "proceed",
    )

    def test_each_token_advances_cleanly(self) -> None:
        for token in self.ADVANCE_TOKENS:
            with self.subTest(token=token):
                result = _advance_prefs(_fresh_journey(), token)
                self.assertEqual(
                    result.journey.phase,
                    PHASE_SEARCH,
                    f"token {token!r} must advance to PHASE_SEARCH",
                )
                self.assertIsNotNone(
                    result.run_search_with,
                    f"token {token!r} must fire the search dispatch",
                )
                # No preference set when advance was explicit
                self.assertIsNone(result.journey.remote_required)
                self.assertIsNone(result.journey.salary_floor)
                self.assertEqual(result.journey.company_size, "")


class PreferenceExtractionTests(unittest.TestCase):
    """Each recognized preference signal must set the right field +
    advance the phase. Bundled adjacent fix: salary regex widened to
    \\d{2,5} so real € amounts parse correctly."""

    def test_remote_sets_required_and_advances(self) -> None:
        result = _advance_prefs(_fresh_journey(), "remote")
        self.assertEqual(result.journey.phase, PHASE_SEARCH)
        self.assertTrue(result.journey.remote_required)

    def test_salary_floor_two_digits(self) -> None:
        result = _advance_prefs(_fresh_journey(), "min 50k")
        self.assertEqual(result.journey.salary_floor, 50000)

    def test_salary_floor_three_digit_k(self) -> None:
        result = _advance_prefs(_fresh_journey(), "100k")
        self.assertEqual(result.journey.salary_floor, 100000)

    def test_salary_floor_four_digit_raw_eur(self) -> None:
        """Bug B adjacent fix: previously \\d{2,3} rejected 4-digit
        raw € amounts like '1000'. Now \\d{2,5} accepts them."""
        result = _advance_prefs(_fresh_journey(), "1000")
        self.assertEqual(result.journey.salary_floor, 1000)

    def test_salary_floor_five_digit_raw_eur(self) -> None:
        """Bug B adjacent fix: '50000' must parse as a 50000 floor,
        not silently become a no-op (pre-fix it was rejected)."""
        result = _advance_prefs(_fresh_journey(), "50000")
        self.assertEqual(result.journey.salary_floor, 50000)

    def test_startup_sets_company_size(self) -> None:
        result = _advance_prefs(_fresh_journey(), "startup")
        self.assertEqual(result.journey.company_size, "startup")

    def test_mid_sets_company_size(self) -> None:
        result = _advance_prefs(_fresh_journey(), "mid")
        self.assertEqual(result.journey.company_size, "mid")

    def test_enterprise_sets_company_size(self) -> None:
        result = _advance_prefs(_fresh_journey(), "enterprise")
        self.assertEqual(result.journey.company_size, "enterprise")

    def test_large_maps_to_enterprise(self) -> None:
        result = _advance_prefs(_fresh_journey(), "large")
        self.assertEqual(result.journey.company_size, "enterprise")

    def test_multi_token_combo(self) -> None:
        """Compound preference input still parses + advances."""
        result = _advance_prefs(_fresh_journey(), "remote min 50k startup")
        self.assertEqual(result.journey.phase, PHASE_SEARCH)
        self.assertTrue(result.journey.remote_required)
        self.assertEqual(result.journey.salary_floor, 50000)
        self.assertEqual(result.journey.company_size, "startup")


class UnrecognizedInputReasksTests(unittest.TestCase):
    """The core Bug B repro tests: ambiguous / gibberish inputs must
    re-ask, NOT silently advance into a no-preference search."""

    UNRECOGNIZED_INPUTS = (
        # Numeric ambiguity (Aïcha shape-test repro):
        "1",
        "2",
        "3",
        # Question / help-seeking (handled separately in Phase 2 #70):
        "?",
        "huh",
        "what",
        "what?",
        # Casual ack-ish but not in advance set:
        "ok",
        "okay",
        "yes",
        "yeah",
        "ja",
        "no",
        # German "I don't know" — explicit confusion signal:
        "keine Ahnung",
        "weiß nicht",
        # Random gibberish:
        "asdf",
        "xyz",
    )

    def test_each_unrecognized_reasks(self) -> None:
        for inp in self.UNRECOGNIZED_INPUTS:
            with self.subTest(inp=inp):
                result = _advance_prefs(_fresh_journey(), inp)
                self.assertEqual(
                    result.journey.phase,
                    PHASE_PREFS,
                    f"input {inp!r} must NOT advance — it's not a "
                    f"recognized preference or explicit advance token",
                )
                self.assertIsNone(
                    result.run_search_with,
                    f"input {inp!r} must NOT fire the aggregator search",
                )
                self.assertFalse(result.persist)

    def test_aicha_shape_test_repro_one_reasks(self) -> None:
        """The exact Aïcha shape-test repro: turn 8 sent '1' at
        preferences. Must re-ask, not silently advance into the
        Bug C dead-end."""
        result = _advance_prefs(_fresh_journey(), "1")
        self.assertEqual(result.journey.phase, PHASE_PREFS)
        self.assertIsNone(result.run_search_with)
        # And the re-ask must contain the menu so user can correct:
        self.assertIn("deal-breakers", result.reply)
        self.assertIn("remote", result.reply)
        self.assertIn("none", result.reply)


if __name__ == "__main__":
    unittest.main()
