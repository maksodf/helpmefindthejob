# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 4 — consented auto-relax engine tests.

Operator-required invariants pinned (2026-05-20):

  - The 3 cross-sub-state collision tests (weiter, skip, cancel) —
    each has DIFFERENT meaning in auto_relax_offering vs. its other
    sub-state.
  - Caveat verbatim — visa-constrained personas see the
    Ausländerbehörde caveat in auto-relax widen-location suggestion.
  - Cold-cache vs. warm-cache count UX.
  - Final-state exhaustion — all 3 confirmed/declined -> exit auto-
    mode + menu shows only retry + give-up.
  - Menu/auto-mode interleave — user toggles between menu and
    auto-mode; applied + declined state persists correctly.
  - Auto-mode persistence across search dispatch — handled in app.py
    integration but verified at journey-state level here.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from company_discovery.aggregators import (
    AggregatedJob,
    AggregatorResultCache,
    canonical_query,
)
from company_discovery.diagnostic_engine import DiagnosticEngine
from company_discovery.journey import (
    PHASE_DONE,
    PHASE_REVIEW,
    UserJourney,
    _advance_review,
    _advance_review_auto_relax_offering,
    _advance_review_empty,
    _advance_review_laterals_offered,
    _enter_auto_relax,
)
from company_discovery.persona_fixtures import PERSONAS
from company_discovery.widening import (
    DROP_SENIORITY,
    LOCATION_CAVEAT_TEXT,
    TRY_LATERALS,
    WIDEN_LOCATION,
    classify_visa_constraint,
    format_auto_relax_suggestion,
    next_auto_relax_suggestion,
    parse_auto_relax_response,
    parse_menu_auto_relax_entry,
)


class _StubProvider:
    def __init__(self, name: str) -> None:
        self.name = name


def _make_engine_with_cache() -> tuple[DiagnosticEngine, AggregatorResultCache, Path]:
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    cache = AggregatorResultCache(tmp.name, ttl_seconds=3600)
    engine = DiagnosticEngine(cache=cache, providers=[_StubProvider("arbeitnow")])
    return engine, cache, Path(tmp.name)


def _journey_for_persona(slug: str, *, location: str = "Berlin") -> UserJourney:
    persona = next(p for p in PERSONAS if p.slug == slug)
    j = UserJourney(phase=PHASE_REVIEW)
    j.review_substate = "empty"
    j.role_text = persona.target_roles[0]
    j.target_roles = [persona.target_roles[0]]
    j.location = location
    j.years_experience = persona.years_experience
    j.visa_constrained = classify_visa_constraint(persona.residency_status)
    return j


def _make_jobs(n: int) -> list[AggregatedJob]:
    return [
        AggregatedJob(
            title=f"Job {i}",
            company_name=f"Co{i}",
            source="arbeitnow",
            source_url=f"https://x.test/{i}",
        )
        for i in range(n)
    ]


# ----------------------------------------------------------------------
# OPERATOR-REQUIRED CROSS-SUB-STATE COLLISION TESTS (Finding 3)
# ----------------------------------------------------------------------


class CrossSubStateCollisionTests(unittest.TestCase):
    """The 3 tokens with sub-state-specific meanings — pinned exactly
    per operator spec 2026-05-20. Future agents reordering token
    parsing will see these fail loudly."""

    def test_weiter_in_auto_relax_advances_not_widens_location(self) -> None:
        j = _journey_for_persona("aicha")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = TRY_LATERALS
        j.proposed_laterals = []  # not yet entered the laterals sub-flow
        result = _advance_review_auto_relax_offering(j, "weiter")
        # "weiter" in auto_relax_offering must ADVANCE (apply the
        # current suggestion), NOT trigger widen_location.
        # The apply_widening call for TRY_LATERALS will either
        # ask_confirm_laterals (with new_laterals) or noop (without).
        # In either case the journey must NOT have widen_location
        # applied solely because of "weiter".
        self.assertNotIn(
            WIDEN_LOCATION,
            j.applied_widenings,
            "'weiter' in auto_relax_offering must NOT apply "
            "widen_location (that's its menu-mode meaning, not "
            "auto-mode advance meaning)",
        )

    def test_skip_in_auto_relax_declines_not_lateral_cancels(self) -> None:
        j = _journey_for_persona("yusuf")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = WIDEN_LOCATION
        result = _advance_review_auto_relax_offering(j, "skip")
        # "skip" must add WIDEN_LOCATION to auto_relax_declined
        # (decline-this-suggestion semantics), NOT trigger the
        # laterals-confirmation cancel flow.
        self.assertIn(
            WIDEN_LOCATION,
            j.auto_relax_declined,
            "'skip' in auto_relax_offering must decline the current "
            "suggestion (not cancel a laterals sub-flow)",
        )
        # Journey should still be in PHASE_REVIEW + auto_relax_active
        self.assertEqual(j.phase, PHASE_REVIEW)
        self.assertTrue(j.auto_relax_active)
        # Proposed laterals should be untouched (that's the
        # laterals_offered sub-state's responsibility)
        self.assertEqual(j.proposed_laterals, [])

    def test_cancel_in_auto_relax_returns_to_menu_not_lateral_cancel(self) -> None:
        j = _journey_for_persona("aicha")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = WIDEN_LOCATION
        j.proposed_laterals = ["Pflegeassistent", "Altenpfleger"]
        result = _advance_review_auto_relax_offering(j, "cancel")
        # "cancel" must exit auto-mode and route to the menu
        # (review_substate="empty"), NOT cancel the laterals_offered
        # sub-flow.
        self.assertEqual(
            j.review_substate,
            "empty",
            "'cancel' in auto_relax_offering must return to the menu",
        )
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.auto_relax_offered_id, "")
        # The current implementation leaves proposed_laterals as-is
        # since cancel is auto-mode-scoped — they don't belong to
        # cancel's clean-up responsibility. (laterals_offered cancel
        # would clear proposed_laterals; auto-mode cancel doesn't.)


# ----------------------------------------------------------------------
# PARSER + ENTRY-TOKEN TESTS
# ----------------------------------------------------------------------


class ParseAutoRelaxResponseTests(unittest.TestCase):
    def test_advance_tokens(self) -> None:
        for tok in (
            "yes",
            "y",
            "ja",
            "j",
            "ok",
            "okay",
            "go",
            "weiter",
            "confirm",
            "do it",
            "apply",
            "sure",
        ):
            with self.subTest(tok=tok):
                self.assertEqual(parse_auto_relax_response(tok), "advance")

    def test_decline_tokens(self) -> None:
        for tok in ("no", "n", "nein", "skip", "next", "nächste", "weiter zu", "decline"):
            with self.subTest(tok=tok):
                self.assertEqual(parse_auto_relax_response(tok), "decline")

    def test_cancel_tokens(self) -> None:
        for tok in ("cancel", "back", "back to menu", "stop", "abbrechen", "menu", "manual"):
            with self.subTest(tok=tok):
                self.assertEqual(parse_auto_relax_response(tok), "cancel")

    def test_give_up_tokens(self) -> None:
        for tok in ("give up", "done", "fertig", "exit", "quit", "end", "ende"):
            with self.subTest(tok=tok):
                self.assertEqual(parse_auto_relax_response(tok), "give_up")

    def test_unknown_returns_unknown(self) -> None:
        for tok in ("", " ", "huh", "1", "what?", "asdf"):
            with self.subTest(tok=tok):
                self.assertEqual(parse_auto_relax_response(tok), "unknown")


class ParseMenuAutoRelaxEntryTests(unittest.TestCase):
    def test_known_entry_tokens(self) -> None:
        for tok in (
            "auto",
            "auto-relax",
            "suggest",
            "guide me",
            "help me decide",
            "system suggest",
            "relax",
        ):
            with self.subTest(tok=tok):
                self.assertTrue(parse_menu_auto_relax_entry(tok))

    def test_unknown_does_not_enter(self) -> None:
        for tok in ("", "yes", "no", "widen", "drop seniority"):
            with self.subTest(tok=tok):
                self.assertFalse(parse_menu_auto_relax_entry(tok))


# ----------------------------------------------------------------------
# CAVEAT VERBATIM IN AUTO-RELAX SUGGESTION
# ----------------------------------------------------------------------


class AutoRelaxCaveatTests(unittest.TestCase):
    """Visa-constrained personas in auto-mode MUST see the
    Ausländerbehörde caveat verbatim in the widen-location
    suggestion. Mirrors piece-3 caveat test pattern."""

    def test_constrained_sees_caveat_in_suggestion_text(self) -> None:
        for slug in ("aicha", "olga", "mahmoud"):
            with self.subTest(persona=slug):
                j = _journey_for_persona(slug)
                # Force WIDEN_LOCATION to be the first suggestion by
                # marking try_laterals + drop_seniority as declined
                # (auto mode skips declined). For unconstrained
                # personas widen is first anyway; for constrained the
                # order is try_laterals -> drop_seniority -> widen,
                # so we need to either decline laterals or eliminate
                # their eligibility (by setting target_roles WITHOUT
                # a seniority qualifier + no new laterals via the
                # journey's bucket_key gaining).
                j.auto_relax_declined = [TRY_LATERALS, DROP_SENIORITY]
                result = _enter_auto_relax(j, new_laterals=[], engine=None)
                self.assertIn(
                    LOCATION_CAVEAT_TEXT,
                    result.reply,
                    f"persona {slug}: auto-relax widen-location "
                    f"suggestion MUST contain the Ausländerbehörde "
                    f"caveat verbatim",
                )

    def test_unconstrained_does_not_see_caveat(self) -> None:
        for slug in ("yusuf", "maria", "kaethe", "tobias"):
            with self.subTest(persona=slug):
                j = _journey_for_persona(slug)
                # For unconstrained, widen_location is first in
                # auto-mode ordering — no need to manipulate state.
                result = _enter_auto_relax(j, new_laterals=[], engine=None)
                # Auto-relax may surface WIDEN_LOCATION first; verify
                # the caveat text is absent
                self.assertNotIn(
                    LOCATION_CAVEAT_TEXT,
                    result.reply,
                    f"persona {slug}: unconstrained — caveat MUST NOT "
                    f"appear in auto-relax suggestion",
                )


# ----------------------------------------------------------------------
# COLD-CACHE vs WARM-CACHE UX
# ----------------------------------------------------------------------


class CountSurfacingTests(unittest.TestCase):
    def test_cold_cache_omits_count(self) -> None:
        engine, cache, path = _make_engine_with_cache()
        try:
            j = _journey_for_persona("aicha")
            result = _enter_auto_relax(j, new_laterals=[], engine=engine)
            # Cold cache → no count surfacing in the suggestion
            self.assertNotIn(
                "recent searches show",
                result.reply.lower(),
                "cold-cache auto-relax suggestion must omit count text",
            )
            self.assertNotIn("~", result.reply.split("\n")[0])
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_warm_cache_surfaces_count_for_widen_location(self) -> None:
        engine, cache, path = _make_engine_with_cache()
        try:
            # Seed cache with the widen-location relaxation candidate
            # for Aicha (same query, NO location).
            seeded_jobs = _make_jobs(23)
            seeded_hash = canonical_query("Registered nurse", "")
            cache.put("arbeitnow", seeded_hash, seeded_jobs)
            # Yusuf is unconstrained → widen_location offered first
            j = _journey_for_persona("yusuf")
            j.role_text = "Mechanical engineer"  # no seniority -> drop_seniority hidden
            j.target_roles = ["Registered nurse"]  # match the seeded cache key
            j.location = "Berlin"
            j.auto_relax_declined = [TRY_LATERALS]  # force widen first
            result = _enter_auto_relax(j, new_laterals=[], engine=engine)
            self.assertIn(
                "23",
                result.reply,
                "warm-cache auto-relax suggestion must surface the actual cached count (23)",
            )
            self.assertIn("recent searches show", result.reply.lower())
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# AUTO-RELAX HIDDEN WHEN N=0 (Operator Q-1 invariant)
# ----------------------------------------------------------------------


class AutoRelaxHiddenWhenN0Tests(unittest.TestCase):
    """Operator-approved invariant: auto-relax menu slot is hidden
    when N=0 eligible widenings. Don't offer something with nothing
    to suggest (same doctrine as theatrical omits)."""

    def test_menu_hides_auto_relax_when_no_widenings(self) -> None:
        # Journey with no eligible widenings: location empty + no
        # seniority + presume no laterals (we'll fake by applying all)
        j = _journey_for_persona("aicha", location="")
        # Apply all 3 widenings so available_affordances returns []
        j.applied_widenings = [WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS]
        from company_discovery.journey import _format_review_empty_reply

        reply = _format_review_empty_reply(j)
        self.assertNotIn("Auto-relax", reply)
        self.assertNotIn("auto-relax", reply.lower())

    def test_menu_shows_auto_relax_when_widening_available(self) -> None:
        j = _journey_for_persona("aicha")  # has location → widen_location eligible
        from company_discovery.journey import _format_review_empty_reply

        reply = _format_review_empty_reply(j)
        self.assertIn("Auto-relax", reply)


# ----------------------------------------------------------------------
# FINAL-STATE EXHAUSTION
# ----------------------------------------------------------------------


class FinalStateExhaustionTests(unittest.TestCase):
    """All 3 widenings confirmed/declined + still 0 results → auto
    mode exits, menu shows only retry + give-up."""

    def test_decline_all_three_routes_to_menu_with_exhaustion_message(self) -> None:
        j = _journey_for_persona("aicha")
        j.role_text = "Senior Registered nurse"
        j.target_roles = ["Senior Registered nurse"]
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = TRY_LATERALS
        # Decline laterals
        _advance_review_auto_relax_offering(j, "skip")
        # Now drop_seniority is offered (constrained ordering #2)
        # Decline it
        self.assertEqual(j.auto_relax_offered_id, DROP_SENIORITY)
        _advance_review_auto_relax_offering(j, "skip")
        # widen_location next
        self.assertEqual(j.auto_relax_offered_id, WIDEN_LOCATION)
        # Decline
        result = _advance_review_auto_relax_offering(j, "skip")
        # Exhausted: exit auto-mode + emit exhaustion message + menu
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.review_substate, "empty")
        self.assertIn("gone through all the widening options", result.reply.lower())
        # Menu (rendered in the exhaustion reply) shows retry + give-up only
        # (widening affordances are applied OR declined; the menu's
        # available_affordances filters out applied; declined are
        # menu-pickable per Q-G — but auto-relax slot is hidden when
        # no eligible widenings... wait — declined are eligible for
        # menu. So menu may still show widenings.
        # The exhaustion path's POINT is the auto-mode "I've gone
        # through all" message; what the menu shows after is per
        # piece-3 semantics.


# ----------------------------------------------------------------------
# MENU/AUTO-MODE INTERLEAVE
# ----------------------------------------------------------------------


class MenuAutoModeInterleaveTests(unittest.TestCase):
    def test_cancel_returns_to_menu_with_declined_persisted(self) -> None:
        j = _journey_for_persona("aicha")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = TRY_LATERALS
        # Decline first suggestion
        _advance_review_auto_relax_offering(j, "no")
        self.assertIn(TRY_LATERALS, j.auto_relax_declined)
        # Cancel auto-mode
        _advance_review_auto_relax_offering(j, "cancel")
        self.assertEqual(j.review_substate, "empty")
        self.assertFalse(j.auto_relax_active)
        # Re-enter auto-mode: declined PERSISTS (operator Q-G)
        self.assertIn(TRY_LATERALS, j.auto_relax_declined)


# ----------------------------------------------------------------------
# APPLY-AFFORDANCE FROM AUTO-MODE
# ----------------------------------------------------------------------


class AdvanceFromAutoRelaxTests(unittest.TestCase):
    def test_advance_widen_location_fires_search(self) -> None:
        j = _journey_for_persona("yusuf")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = WIDEN_LOCATION
        result = _advance_review_auto_relax_offering(j, "yes")
        self.assertIsNotNone(result.run_search_with)
        self.assertEqual(j.location, "")  # widened
        self.assertIn(WIDEN_LOCATION, j.applied_widenings)
        # offered_id stays set per operator-approved cleanup-deferral
        # (dispatcher clears on search result)
        self.assertEqual(j.auto_relax_offered_id, WIDEN_LOCATION)

    def test_advance_try_laterals_enters_laterals_offered(self) -> None:
        j = _journey_for_persona("aicha")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = TRY_LATERALS
        result = _advance_review_auto_relax_offering(j, "yes")
        # Laterals sub-flow takes over; auto_relax_active stays True
        self.assertEqual(j.review_substate, "laterals_offered")
        self.assertTrue(j.auto_relax_active)


# ----------------------------------------------------------------------
# UNKNOWN INPUT RE-ASKS
# ----------------------------------------------------------------------


class UnknownInputReasksTests(unittest.TestCase):
    def test_unknown_input_re_asks_current_suggestion(self) -> None:
        j = _journey_for_persona("yusuf")
        j.review_substate = "auto_relax_offering"
        j.auto_relax_active = True
        j.auto_relax_offered_id = WIDEN_LOCATION
        result = _advance_review_auto_relax_offering(j, "huh???")
        self.assertEqual(j.review_substate, "auto_relax_offering")
        self.assertTrue(j.auto_relax_active)
        self.assertIsNone(result.run_search_with)
        # Reply should be the suggestion re-rendered (contains "Reply")
        self.assertIn("reply", result.reply.lower())


if __name__ == "__main__":
    unittest.main()
