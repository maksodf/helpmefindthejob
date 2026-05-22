# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Per-phase help-surface contract tests (phase2-backlog #70).

Closes phase2-backlog item #70: "Help-surface for clarifying
questions in journey phases".

Before this slice, help-seeking inputs ("?" / "huh" / "what" /
"help" / "hilfe" / etc.) landed in the generic help branch which
just re-shows a "you're mid-journey, cancel/back/answer" reminder.
Now each interactive journey phase emits a phase-tailored
explanation followed by the original re-prompt.

Tests pin:
1. Help-seeking detection covers the full token set (EN + DE,
   colloquial + explicit, single-char + word-level).
2. Each phase has its own help text (not the generic).
3. Discover sub-steps have their own help text (more specific
   than the discover-phase generic).
4. `advance()` integration: typing "?" at each phase produces
   the phase's tailored help text.
5. Greet phase keeps its bespoke menu (router intentionally
   skips help-seeking there).
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    DISCOVER_ASK_LOCATION,
    DISCOVER_ASK_ROLE,
    DISCOVER_ASK_YEARS,
    DISCOVER_SUB_HELP_TEXT,
    PHASE_CV_CHECK,
    PHASE_CV_CONSULT,
    PHASE_DISCOVER,
    PHASE_DRILL,
    PHASE_GREET,
    PHASE_HELP_TEXT,
    PHASE_INSPIRE,
    PHASE_LETTER,
    PHASE_PREFS,
    PHASE_REVIEW,
    PHASE_TAILOR,
    UserJourney,
    advance,
    help_text_for,
    is_help_seeking,
    is_help_token,
)


# ---------------------------------------------------------------------------
# Help-seeking detection
# ---------------------------------------------------------------------------


class HelpSeekingDetection(unittest.TestCase):
    """The expanded predicate covers /help, ?, huh, what (EN +
    DE) without false-positives on real answers."""

    def test_question_mark_alone(self):
        self.assertTrue(is_help_seeking("?"))

    def test_double_question_mark(self):
        self.assertTrue(is_help_seeking("??"))

    def test_question_mark_with_bang(self):
        self.assertTrue(is_help_seeking("?!"))

    def test_huh(self):
        self.assertTrue(is_help_seeking("huh"))
        self.assertTrue(is_help_seeking("huh?"))

    def test_what(self):
        self.assertTrue(is_help_seeking("what"))
        self.assertTrue(is_help_seeking("what?"))

    def test_de_was(self):
        self.assertTrue(is_help_seeking("was"))
        self.assertTrue(is_help_seeking("was?"))

    def test_de_wie(self):
        self.assertTrue(is_help_seeking("wie"))

    def test_legacy_tokens_still_recognised(self):
        self.assertTrue(is_help_seeking("/help"))
        self.assertTrue(is_help_seeking("help"))
        self.assertTrue(is_help_seeking("hilfe"))

    def test_dont_understand_en(self):
        self.assertTrue(is_help_seeking("I don't understand"))

    def test_dont_understand_de(self):
        self.assertTrue(is_help_seeking("verstehe nicht"))

    def test_explain(self):
        self.assertTrue(is_help_seeking("explain"))
        self.assertTrue(is_help_seeking("erkläre"))

    def test_case_insensitive(self):
        self.assertTrue(is_help_seeking("HELP"))
        self.assertTrue(is_help_seeking("HuH?"))

    def test_real_answer_is_not_help_seeking(self):
        """Real answers must not be detected as help-seeking."""

        for msg in ("frontend developer", "Berlin", "5 years", "yes", "no", "skip"):
            with self.subTest(msg=msg):
                self.assertFalse(
                    is_help_seeking(msg),
                    f"{msg!r} false-positives as help-seeking",
                )

    def test_empty_is_not_help_seeking(self):
        self.assertFalse(is_help_seeking(""))
        self.assertFalse(is_help_seeking("   "))


class IsHelpTokenIsStillStrictSubset(unittest.TestCase):
    """The legacy ``is_help_token`` predicate continues to work
    and is a strict subset of ``is_help_seeking`` (colloquial
    extensions only flow through the new predicate)."""

    def test_explicit_help_token_passes_both(self):
        self.assertTrue(is_help_token("/help"))
        self.assertTrue(is_help_seeking("/help"))

    def test_colloquial_only_passes_help_seeking(self):
        self.assertFalse(is_help_token("?"))
        self.assertTrue(is_help_seeking("?"))


# ---------------------------------------------------------------------------
# Per-phase help text
# ---------------------------------------------------------------------------


class PhaseHelpTextPresence(unittest.TestCase):
    """Every interactive phase has a tailored help-text entry."""

    def test_discover_has_help(self):
        self.assertIn(PHASE_DISCOVER, PHASE_HELP_TEXT)

    def test_cv_check_has_help(self):
        self.assertIn(PHASE_CV_CHECK, PHASE_HELP_TEXT)

    def test_inspire_has_help(self):
        self.assertIn(PHASE_INSPIRE, PHASE_HELP_TEXT)

    def test_prefs_has_help(self):
        self.assertIn(PHASE_PREFS, PHASE_HELP_TEXT)

    def test_review_has_help(self):
        self.assertIn(PHASE_REVIEW, PHASE_HELP_TEXT)

    def test_drill_has_help(self):
        self.assertIn(PHASE_DRILL, PHASE_HELP_TEXT)

    def test_tailor_has_help(self):
        self.assertIn(PHASE_TAILOR, PHASE_HELP_TEXT)

    def test_letter_has_help(self):
        self.assertIn(PHASE_LETTER, PHASE_HELP_TEXT)

    def test_cv_consult_has_help(self):
        self.assertIn(PHASE_CV_CONSULT, PHASE_HELP_TEXT)

    def test_phase_help_texts_are_non_empty(self):
        for phase, text in PHASE_HELP_TEXT.items():
            with self.subTest(phase=phase):
                self.assertGreater(
                    len(text.strip()),
                    20,
                    f"phase {phase} has too-short help text",
                )

    def test_discover_sub_steps_have_help(self):
        for sub in (DISCOVER_ASK_ROLE, DISCOVER_ASK_LOCATION, DISCOVER_ASK_YEARS):
            with self.subTest(sub=sub):
                self.assertIn(sub, DISCOVER_SUB_HELP_TEXT)


class HelpTextForRouter(unittest.TestCase):
    """``help_text_for(journey)`` returns the most-specific entry."""

    def test_returns_sub_step_help_for_discover_ask_role(self):
        journey = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_ROLE)
        text = help_text_for(journey)
        self.assertIn("role", text.lower())
        # Should NOT return the generic discover-phase text
        self.assertNotEqual(text, PHASE_HELP_TEXT[PHASE_DISCOVER])

    def test_returns_sub_step_help_for_discover_ask_location(self):
        journey = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_LOCATION)
        text = help_text_for(journey)
        self.assertIn("work", text.lower())

    def test_returns_sub_step_help_for_discover_ask_years(self):
        journey = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_YEARS)
        text = help_text_for(journey)
        self.assertIn("experience", text.lower())

    def test_falls_back_to_phase_help_when_no_sub_step(self):
        journey = UserJourney(phase=PHASE_DISCOVER, discover_step="unknown_step")
        text = help_text_for(journey)
        # The phase help is appended with the universal cancel-tail
        self.assertTrue(text.startswith(PHASE_HELP_TEXT[PHASE_DISCOVER]))
        self.assertIn("cancel", text.lower())

    def test_returns_phase_help_for_non_discover_phases(self):
        for phase in (PHASE_PREFS, PHASE_REVIEW, PHASE_TAILOR):
            with self.subTest(phase=phase):
                journey = UserJourney(phase=phase)
                text = help_text_for(journey)
                self.assertTrue(
                    text.startswith(PHASE_HELP_TEXT[phase]),
                    f"phase {phase}: help text doesn't start with PHASE_HELP_TEXT entry",
                )
                self.assertIn("cancel", text.lower())

    def test_every_help_text_carries_cancel_tail(self):
        """UX invariant: a user typing '?' must always learn they
        can back out via 'cancel'. The phase-specific help focuses
        on the immediate question; the tail keeps the escape hatch
        surfaced."""

        from company_discovery.journey import ALL_PHASES

        for phase in ALL_PHASES:
            if phase == PHASE_GREET:
                continue  # greet has its own bespoke menu
            with self.subTest(phase=phase):
                journey = UserJourney(phase=phase)
                self.assertIn("cancel", help_text_for(journey).lower())


# ---------------------------------------------------------------------------
# advance() integration
# ---------------------------------------------------------------------------


class AdvanceRoutesHelpSeekingToPhaseSpecificText(unittest.TestCase):
    """End-to-end: typing "?" at each phase produces the phase's
    tailored help text, not the generic re-ask."""

    def _help_reply(self, phase: str, discover_step: str = "") -> str:
        journey = UserJourney(phase=phase, discover_step=discover_step or "")
        result = advance(journey, "?")
        return result.reply

    def test_help_at_prefs_returns_prefs_help(self):
        reply = self._help_reply(PHASE_PREFS)
        self.assertIn("preferences are optional", reply.lower())

    def test_help_at_review_returns_review_help(self):
        reply = self._help_reply(PHASE_REVIEW)
        self.assertIn("grouped", reply.lower())

    def test_help_at_drill_returns_drill_help(self):
        reply = self._help_reply(PHASE_DRILL)
        self.assertIn("number of the job", reply.lower())

    def test_help_at_letter_returns_letter_help(self):
        reply = self._help_reply(PHASE_LETTER)
        self.assertIn("letter", reply.lower())

    def test_help_at_discover_ask_role_returns_role_help(self):
        reply = self._help_reply(PHASE_DISCOVER, DISCOVER_ASK_ROLE)
        self.assertIn("role", reply.lower())

    def test_help_at_discover_ask_location_returns_location_help(self):
        reply = self._help_reply(PHASE_DISCOVER, DISCOVER_ASK_LOCATION)
        self.assertIn("work", reply.lower())

    def test_help_at_greet_does_not_use_phase_router(self):
        """Greet phase has its own bespoke menu; the help router
        intentionally skips greet. Typing "?" at greet should not
        produce a PHASE_HELP_TEXT-style reply."""

        journey = UserJourney(phase=PHASE_GREET)
        result = advance(journey, "?")
        # The greet handler decides what to do; we just verify it
        # doesn't bounce to the generic "you're mid-journey" text
        # (which is the WRONG response when the user hasn't even
        # started a journey yet).
        self.assertNotIn("cancel to stop the journey", result.reply.lower())

    def test_help_does_not_advance_phase(self):
        """Help-seeking emits text + persist=False without changing
        the journey state. Critical: a user typing '?' should not
        accidentally skip forward."""

        journey = UserJourney(phase=PHASE_PREFS)
        result = advance(journey, "?")
        self.assertEqual(result.journey.phase, PHASE_PREFS)
        self.assertFalse(result.persist)

    def test_huh_routes_through_help(self):
        """Colloquial 'huh' should hit the same router as '?'."""

        journey = UserJourney(phase=PHASE_PREFS)
        result = advance(journey, "huh")
        self.assertIn("preferences are optional", result.reply.lower())

    def test_german_was_routes_through_help(self):
        """DE colloquial 'was' should produce phase-tailored help."""

        journey = UserJourney(phase=PHASE_REVIEW)
        result = advance(journey, "was?")
        # The reply must be the review help, not a re-ask
        self.assertIn("grouped", result.reply.lower())


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


class DriftGuards(unittest.TestCase):
    def test_every_interactive_phase_has_help(self):
        """Drift guard: if a new interactive phase is added to
        ALL_PHASES, the maintainer is reminded to add a help text
        entry. Greet + done are non-interactive and excluded."""

        from company_discovery.journey import ALL_PHASES, PHASE_SEARCH

        # Phases that don't need help text (non-interactive /
        # transient states).
        non_interactive = {PHASE_GREET, PHASE_SEARCH, "done"}
        for phase in ALL_PHASES:
            if phase in non_interactive:
                continue
            with self.subTest(phase=phase):
                self.assertIn(
                    phase,
                    PHASE_HELP_TEXT,
                    f"phase {phase!r} is interactive but has no help text",
                )


if __name__ == "__main__":
    unittest.main()
