# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for the populated-review category-pick bug.

`_advance_review` matched the category with `lc in c.lower()`, which is true for
the empty string (and any single stray char) — so a blank/zero-width message or
a fat-finger keystroke silently drilled into the wrong category and persisted the
wrong state. Such input must now re-ask (stay in review); a real category
fragment must still drill.
"""

from __future__ import annotations

import unittest

from company_discovery.journey import PHASE_REVIEW, UserJourney, advance


def _fresh_review() -> UserJourney:
    j = UserJourney(phase=PHASE_REVIEW, review_substate="")
    j.search_results_by_category = {"Tech / Engineering": ["u1"], "Operations / Admin": ["u2"]}
    return j


class PopulatedReviewInputTests(unittest.TestCase):
    def test_blank_and_stray_input_reask_not_drill(self) -> None:
        for msg in ("​​", "o", "ad", "  \t "):
            j = _fresh_review()
            advance(j, msg)
            self.assertEqual(
                j.phase,
                PHASE_REVIEW,
                f"{msg!r} must re-ask (stay in review), not drill into a category",
            )

    def test_real_category_fragment_still_drills(self) -> None:
        j = _fresh_review()
        advance(j, "tech")
        self.assertNotEqual(j.phase, PHASE_REVIEW, "a real category fragment must still drill")


if __name__ == "__main__":
    unittest.main()
