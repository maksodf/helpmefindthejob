# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug A regression test — inspire phase decline tokens.

Origin: Aïcha shape-test (2026-05-20) drove the full 12-phase
journey and surfaced that "none" — a natural-English decline at
the inspire-suggestion prompt — silently fell through to the
free-text-role-parsing branch and got appended to target_roles,
producing aggregator queries like "Registered nurse, none".
Cross-persona: every persona who declined with "none"/"keine"/
"nope"/etc would hit this.

This test pins the behavioural invariant: every common decline
token (English + German + colloquial) sets target_roles to the
single aggregator_role, no extra decline-word leakage.
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    PHASE_INSPIRE,
    UserJourney,
    _advance_inspire,
)


_DECLINE_TOKENS = (
    # Pre-Bug-A tokens (already worked, regression-pinned here):
    "no",
    "n",
    "nein",
    "skip",
    "stick",
    # Added in the Bug A fix (2026-05-20):
    "none",
    "keine",
    "nope",
    "no thanks",
    "nein danke",
    "decline",
    "pass",
)


class InspireDeclineTokenTests(unittest.TestCase):
    """Each decline token must set target_roles to exactly the user's
    aggregator_role — no decline-word leakage."""

    def _walk_inspire_with(self, decline_token: str) -> UserJourney:
        journey = UserJourney(phase=PHASE_INSPIRE)
        journey.role_text = "Registered nurse"
        # Simulate the inspire-suggestion offer state: lateral_roles
        # exist but the user is choosing to decline them.
        journey.lateral_roles = ["Senior Registered nurse", "Lead Registered nurse"]
        result = _advance_inspire(
            journey, decline_token, ai_available=False, ai_caller=None
        )
        return result.journey

    def test_all_decline_tokens_set_single_target(self) -> None:
        for token in _DECLINE_TOKENS:
            with self.subTest(token=token):
                journey = self._walk_inspire_with(token)
                self.assertEqual(
                    journey.target_roles,
                    ["Registered nurse"],
                    f"token {token!r} must result in target_roles == "
                    f"['Registered nurse'] (no decline-word leakage); "
                    f"got {journey.target_roles!r}",
                )

    def test_none_does_not_become_a_role(self) -> None:
        """The exact Aïcha shape-test repro: 'none' must not appear
        in target_roles."""
        journey = self._walk_inspire_with("none")
        self.assertNotIn(
            "none",
            journey.target_roles,
            "the literal string 'none' must never appear in target_roles "
            "as a result of the user declining lateral suggestions",
        )

    def test_yes_still_adds_laterals(self) -> None:
        """Regression-pin the accept path stays intact."""
        journey = UserJourney(phase=PHASE_INSPIRE)
        journey.role_text = "Registered nurse"
        journey.lateral_roles = ["Senior Registered nurse"]
        result = _advance_inspire(
            journey, "yes", ai_available=False, ai_caller=None
        )
        self.assertEqual(
            result.journey.target_roles,
            ["Registered nurse", "Senior Registered nurse"],
        )


if __name__ == "__main__":
    unittest.main()
