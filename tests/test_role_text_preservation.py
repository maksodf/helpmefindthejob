# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 (2026-05-20) — role_text preservation invariant.

Origin: walk #3 (Olga, "Senior frontend developer") surfaced that the
journey state machine was storing role_text as the taxonomy-matched
canonical substring ("frontend developer") instead of the user's
verbatim input. Modifier prefixes — "Senior", "Returning", "Former",
"ex-", and similar — were silently dropped when the role phrase
contained a taxonomy entry. The data loss propagated into:
  - aggregator queries (seniority filter lost)
  - AI prompts (CV-tailoring + auto-fit + Anschreiben lost the signal)
  - user-facing summary (echo masked the loss)

Pinning the BEHAVIOURAL INVARIANT here — role_text always equals the
user's verbatim input — keeps the test meaningful as the taxonomy
expands. Future taxonomy additions (Krankenschwester, Pflegehelferin,
Anlagenmechaniker, SHK — see Phase 2 backlog #68) must not re-introduce
the strip.

Inputs covered:
  - "Senior frontend developer" — taxonomy match today (software_engineer)
  - "Returning Krankenschwester" — bucket=None today; once
    Krankenschwester is added, this test pins preservation
  - "Former senior backend developer" — multi-modifier
  - "ex-banker" — prefix modifier
  - "Junior engineer" — taxonomy miss today; pins preservation
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    DISCOVER_ASK_ROLE,
    PHASE_DISCOVER,
    UserJourney,
    _advance_discover,
)


class RoleTextPreservationTests(unittest.TestCase):
    """role_text MUST equal the user's verbatim input — taxonomy
    matches go to bucket_key + matched_token, never overwriting
    role_text."""

    def _walk_role(self, user_message: str) -> UserJourney:
        """Helper: advance a fresh journey through the role question
        with the supplied message and return the resulting journey."""
        journey = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_ROLE)
        result = _advance_discover(journey, user_message)
        return result.journey

    def test_senior_frontend_developer_preserves_modifier(self) -> None:
        """The canonical Olga case: taxonomy match exists for
        'frontend developer' as a substring; the 'Senior' qualifier
        MUST stay attached to role_text."""
        journey = self._walk_role("Senior frontend developer")
        self.assertEqual(
            journey.role_text,
            "Senior frontend developer",
            "role_text must preserve the 'Senior' qualifier verbatim",
        )
        self.assertEqual(
            journey.bucket_key,
            "software_engineer",
            "bucket_key must still extract the taxonomy hit",
        )
        self.assertEqual(
            journey.matched_token,
            "frontend developer",
            "matched_token must capture the canonical substring for aggregator-query widening",
        )

    def test_returning_krankenschwester_preserves_modifier_today(self) -> None:
        """Käthe-class friction-class input. Today no taxonomy bucket
        matches 'Krankenschwester' so role_text falls through to msg
        — the invariant we pin is that 'Returning' stays attached
        regardless. Once Phase 2 backlog #68 lands the
        Krankenschwester bucket, this test will continue to pass
        because role_text is now decoupled from taxonomy hits."""
        journey = self._walk_role("Returning Krankenschwester")
        self.assertEqual(
            journey.role_text,
            "Returning Krankenschwester",
            "role_text must preserve the Wiedereinstieg signal "
            "('Returning') regardless of taxonomy state",
        )

    def test_former_senior_backend_developer_multi_modifier(self) -> None:
        """Multi-modifier input — both 'Former' (career-changer) and
        'senior' (seniority) qualifiers must survive. Tobias-class
        signal."""
        journey = self._walk_role("Former senior backend developer")
        self.assertEqual(
            journey.role_text,
            "Former senior backend developer",
            "Both qualifier modifiers must stay attached",
        )

    def test_ex_banker_prefix_modifier_preserved(self) -> None:
        """Prefix-modifier shape. Tobias-class career-changer signal."""
        journey = self._walk_role("ex-banker")
        self.assertEqual(
            journey.role_text,
            "ex-banker",
            "Prefix qualifier 'ex-' must stay attached",
        )

    def test_junior_engineer_preserves_today_pins_future(self) -> None:
        """No taxonomy hit on 'Junior engineer' today, but the
        invariant — role_text equals the verbatim input — must hold
        regardless of future taxonomy expansion."""
        journey = self._walk_role("Junior engineer")
        self.assertEqual(
            journey.role_text,
            "Junior engineer",
            "Junior qualifier must stay attached regardless of "
            "future bucket-key resolution for 'engineer'",
        )


if __name__ == "__main__":
    unittest.main()
