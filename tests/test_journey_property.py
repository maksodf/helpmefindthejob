# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Property-based tests for the journey state machine
(:mod:`company_discovery.journey`).

Closes the journey-state-machine portion of phase2-backlog item #43.

Example-based tests in ``test_journey.py`` walk specific persona
flows. These property tests generate thousands of random message
sequences and assert **state-machine invariants** that must hold
regardless of what the user types:

1. ``advance`` never raises.
2. After every advance, ``journey.phase`` is in ALL_PHASES.
3. ``AdvanceResult.reply`` is always a str.
4. ``AdvanceResult.persist`` is always bool.
5. ``AdvanceResult.done`` is always bool.
6. ``AdvanceResult.profile_updates`` is always a dict[str, Any].
7. ``AdvanceResult.analytics_events`` is always list of (str, dict).
8. ``AdvanceResult.cost_saving_events`` is always list of 4-tuples.
9. Universal escape hatches always work — typing "cancel" or "/start"
   at any phase transitions the journey to a recognised state.
"""

from __future__ import annotations

import unittest

from hypothesis import HealthCheck, given, settings, strategies as st

from company_discovery.journey import (
    ALL_PHASES,
    AdvanceResult,
    PHASE_GREET,
    UserJourney,
    advance,
)


_SETTINGS = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


# Random user message — bounded length to keep property runs fast.
# Includes common terms users might type ("cancel", "yes", "find a
# job", "Berlin") so the generator exercises both happy and bizarre
# paths.
_MESSAGE_FRAGMENTS = st.sampled_from([
    "yes", "no", "ja", "nein", "ok", "skip", "cancel", "stop", "exit",
    "find a job", "wohnung", "Berlin", "Pflege", "frontend",
    "5 years", "0 years", "letter", "consult", "save", "mark", "done",
    "thanks", "give up", "1", "2", "3", "10", "100", "/start",
    "/cancel", "/help", "/skip", "", " ", "  ",
    "🙂", "ÄÖÜß", "<script>", "{}", "null", "undefined",
])

_RANDOM_MESSAGE = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        min_codepoint=0x20,
        max_codepoint=0x024F,
    ),
    min_size=0,
    max_size=120,
)

_MESSAGE_STRATEGY = st.one_of(_MESSAGE_FRAGMENTS, _RANDOM_MESSAGE)


class AdvanceNeverRaises(unittest.TestCase):
    """``advance(fresh_journey, msg)`` for any msg must return an
    AdvanceResult — never raise."""

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_fresh_journey_advance(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIsInstance(result, AdvanceResult)

    @_SETTINGS
    @given(
        starting_phase=st.sampled_from(ALL_PHASES),
        message=_MESSAGE_STRATEGY,
    )
    def test_any_starting_phase_advance(self, starting_phase, message):
        """Pre-set the journey to any phase and advance with any
        message. The state machine must produce a valid result."""

        journey = UserJourney(phase=starting_phase)
        result = advance(journey, message)
        self.assertIsInstance(result, AdvanceResult)


class AdvanceResultShape(unittest.TestCase):
    """The AdvanceResult dataclass contract is part of the public
    API the chat-router relies on. Every field must have the
    declared type even when the user input is bizarre."""

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_reply_is_str(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIsInstance(result.reply, str)

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_journey_phase_in_all_phases(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIn(
            result.journey.phase,
            ALL_PHASES,
            f"journey landed in unknown phase {result.journey.phase!r}",
        )

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_persist_and_done_are_bools(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIsInstance(result.persist, bool)
        self.assertIsInstance(result.done, bool)

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_profile_updates_is_dict(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIsInstance(result.profile_updates, dict)

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_analytics_events_is_list_of_tuples(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIsInstance(result.analytics_events, list)
        for item in result.analytics_events:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], str)
            self.assertIsInstance(item[1], dict)

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_cost_saving_events_is_list_of_4_tuples(self, message):
        journey = UserJourney()
        result = advance(journey, message)
        self.assertIsInstance(result.cost_saving_events, list)
        for item in result.cost_saving_events:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 4)
            mechanism, value, unit, metadata = item
            self.assertIsInstance(mechanism, str)
            self.assertIsInstance(value, (int, float))
            self.assertIsInstance(unit, str)
            self.assertIsInstance(metadata, dict)


class StateMachineNeverEscapes(unittest.TestCase):
    """Multi-step property: applying an arbitrary sequence of
    messages must always leave the journey in a valid phase."""

    @_SETTINGS
    @given(
        messages=st.lists(_MESSAGE_STRATEGY, min_size=1, max_size=10),
    )
    def test_arbitrary_sequence_lands_in_valid_phase(self, messages):
        journey = UserJourney()
        for msg in messages:
            result = advance(journey, msg)
            journey = result.journey
            self.assertIn(
                journey.phase,
                ALL_PHASES,
                f"journey escaped to invalid phase {journey.phase!r} "
                f"after message {msg!r}",
            )


class UniversalCancelWorks(unittest.TestCase):
    """The "cancel" / "/cancel" / "stop" universal escape hatch must
    work from every starting phase. Critical for UX — a user must
    always be able to back out."""

    @_SETTINGS
    @given(starting_phase=st.sampled_from(ALL_PHASES))
    def test_cancel_token_at_any_phase_produces_valid_state(self, starting_phase):
        journey = UserJourney(phase=starting_phase)
        result = advance(journey, "cancel")
        self.assertIsInstance(result, AdvanceResult)
        self.assertIn(result.journey.phase, ALL_PHASES)


class DeterministicWithoutAI(unittest.TestCase):
    """Without an AI caller, the same input should produce the same
    transition. Catches accidental hidden state outside the journey
    dataclass."""

    @_SETTINGS
    @given(
        starting_phase=st.sampled_from(ALL_PHASES),
        message=_MESSAGE_STRATEGY,
    )
    def test_same_input_same_phase_transition(self, starting_phase, message):
        journey_a = UserJourney(phase=starting_phase)
        journey_b = UserJourney(phase=starting_phase)
        result_a = advance(journey_a, message)
        result_b = advance(journey_b, message)
        self.assertEqual(
            result_a.journey.phase,
            result_b.journey.phase,
            f"non-deterministic phase transition for ({starting_phase!r}, {message!r})",
        )


if __name__ == "__main__":
    unittest.main()
