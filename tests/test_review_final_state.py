# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 6 (2026-05-20) - final-state recovery tests.

Pins the operator-approved Q-G test invariants (1-11) for the
exhausted-widening recovery flow.
"""
from __future__ import annotations

import unittest

from company_discovery.journey import (
    DISCOVER_ASK_ROLE,
    PHASE_DISCOVER,
    PHASE_DONE,
    PHASE_REVIEW,
    UserJourney,
    _advance_review_empty,
    _format_applied_widening_bullet,
    _format_review_empty_reply,
    _reset_for_fresh_search,
)
from company_discovery.widening import (
    DROP_SENIORITY,
    TRY_LATERALS,
    WIDEN_LOCATION,
    WIDENING_LABEL,
)


def _make_exhausted_olga() -> UserJourney:
    """Olga §24 after exhausting all 3 widenings.

    Walks the cumulative widening sequence:
      - Start: "Senior DevOps Engineer" in Berlin
      - Applied WIDEN_LOCATION: location cleared
      - Applied DROP_SENIORITY: target_roles[0] = "DevOps Engineer"
      - Applied TRY_LATERALS: target_roles extended with laterals
    """
    return UserJourney(
        phase=PHASE_REVIEW,
        review_substate="empty",
        role_text="DevOps Engineer",
        bucket_key="devops",
        matched_token="devops",
        location="",
        visa_constrained=True,
        target_roles=[
            "DevOps Engineer", "sre", "platform engineer",
            "infrastructure engineer",
        ],
        applied_widenings=[
            WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS,
        ],
        proposed_laterals=[],
        diagnostic_text=(
            "No live postings found for 'DevOps Engineer' "
            "(plus 3 lateral roles) across the 8 connected providers."
        ),
        years_experience=8,
        languages=["english"],
        cv_status="uploaded",
        cv_build_step="done",
        salary_floor=60000,
        company_size="mid",
        remote_required=False,
    )


# Q-G invariant 1: trigger -- final-state activates when available_
# affordances returns empty AND applied_widenings non-empty.
class TriggerConditionTests(unittest.TestCase):
    def test_renders_summary_block_when_offered_empty_and_applied_non_empty(self):
        j = _make_exhausted_olga()
        reply = _format_review_empty_reply(j, diagnostic_text=j.diagnostic_text)
        self.assertIn("You've tried these widenings:", reply)
        self.assertIn("All returned 0 matches.", reply)

    def test_summary_lists_every_applied_widening(self):
        j = _make_exhausted_olga()
        reply = _format_review_empty_reply(j, diagnostic_text=j.diagnostic_text)
        for wid in [WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS]:
            self.assertIn(WIDENING_LABEL[wid], reply,
                f"summary missing label for {wid}:\n{reply}")


# Q-G invariant 8 (added): no premature trigger when offered != [].
class NoPrematureTriggerTests(unittest.TestCase):
    def test_offered_non_empty_does_not_render_summary(self):
        j = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="Senior DevOps Engineer",
            location="Berlin",
            visa_constrained=True,
            target_roles=["Senior DevOps Engineer"],
            applied_widenings=[],
        )
        reply = _format_review_empty_reply(j)
        self.assertNotIn("You've tried these widenings:", reply)

    def test_offered_non_empty_with_one_applied_does_not_render_summary(self):
        j = UserJourney(
            phase=PHASE_REVIEW, review_substate="empty",
            role_text="Senior DevOps Engineer", location="Berlin",
            visa_constrained=True,
            target_roles=["Senior DevOps Engineer"],
            applied_widenings=[WIDEN_LOCATION],
        )
        j.location = ""  # widen-location was applied
        reply = _format_review_empty_reply(j)
        # Drop-seniority + try_laterals may still be offered;
        # therefore no final-state summary.
        self.assertNotIn("You've tried these widenings:", reply)


# Q-G invariant 9 (added): edge case -- legitimately constrained
# role from turn 1 (no qualifier, no location, no laterals) does
# NOT render the summary block (no widenings tried).
class LegitimatelyConstrainedEdgeCaseTests(unittest.TestCase):
    def test_offered_empty_and_applied_empty_no_summary(self):
        j = UserJourney(
            phase=PHASE_REVIEW, review_substate="empty",
            role_text="Pflegehelfer",
            bucket_key="pflegehelfer",
            location="",
            visa_constrained=False,
            target_roles=["Pflegehelfer"],
            applied_widenings=[],
        )
        reply = _format_review_empty_reply(j)
        self.assertNotIn("You've tried these widenings:", reply)
        self.assertNotIn("**Start fresh**", reply)
        # Retry + give-up only.
        self.assertIn("**Retry**", reply)
        self.assertIn("**Give up**", reply)


# Q-G invariant 2 (start-fresh preserves profile + prefs, resets
# discover/search/review state, routes to PHASE_DISCOVER).
class StartFreshResetSemanticsTests(unittest.TestCase):
    def test_preserves_cv_status(self):
        j = _make_exhausted_olga()
        _reset_for_fresh_search(j)
        self.assertEqual(j.cv_status, "uploaded")
        self.assertEqual(j.cv_build_step, "done")

    def test_preserves_preferences_phase_output(self):
        j = _make_exhausted_olga()
        _reset_for_fresh_search(j)
        self.assertEqual(j.salary_floor, 60000)
        self.assertEqual(j.company_size, "mid")
        self.assertEqual(j.remote_required, False)

    def test_preserves_visa_constrained(self):
        j = _make_exhausted_olga()
        _reset_for_fresh_search(j)
        self.assertTrue(j.visa_constrained)

    def test_resets_role_text_and_taxonomy(self):
        j = _make_exhausted_olga()
        _reset_for_fresh_search(j)
        self.assertEqual(j.role_text, "")
        self.assertEqual(j.bucket_key, "")
        self.assertEqual(j.matched_token, "")

    def test_resets_location(self):
        j = _make_exhausted_olga()
        j.location = "Berlin"
        j.location_canonical = "berlin"
        _reset_for_fresh_search(j)
        self.assertEqual(j.location, "")
        self.assertEqual(j.location_canonical, "")

    def test_resets_years_and_languages(self):
        j = _make_exhausted_olga()
        _reset_for_fresh_search(j)
        self.assertIsNone(j.years_experience)
        self.assertEqual(j.languages, [])

    def test_resets_target_and_lateral_roles(self):
        j = _make_exhausted_olga()
        j.lateral_roles = ["something"]
        _reset_for_fresh_search(j)
        self.assertEqual(j.target_roles, [])
        self.assertEqual(j.lateral_roles, [])

    def test_resets_widening_state(self):
        j = _make_exhausted_olga()
        j.auto_relax_active = True
        j.auto_relax_declined = ["foo"]
        j.auto_relax_offered_id = "bar"
        j.proposed_laterals = ["baz"]
        _reset_for_fresh_search(j)
        self.assertEqual(j.applied_widenings, [])
        self.assertEqual(j.proposed_laterals, [])
        self.assertFalse(j.auto_relax_active)
        self.assertEqual(j.auto_relax_declined, [])
        self.assertEqual(j.auto_relax_offered_id, "")
        self.assertEqual(j.review_substate, "")
        self.assertEqual(j.diagnostic_text, "")

    def test_resets_search_results(self):
        j = _make_exhausted_olga()
        j.search_results_by_category = {"good_fit": ["a", "b"]}
        j.search_jobs_by_id = {"a": {"title": "x"}}
        j.picked_category = "good_fit"
        j.picked_job_id = "a"
        _reset_for_fresh_search(j)
        self.assertEqual(j.search_results_by_category, {})
        self.assertEqual(j.search_jobs_by_id, {})
        self.assertEqual(j.picked_category, "")
        self.assertEqual(j.picked_job_id, "")

    def test_routes_to_phase_discover(self):
        j = _make_exhausted_olga()
        _reset_for_fresh_search(j)
        self.assertEqual(j.phase, PHASE_DISCOVER)
        self.assertEqual(j.discover_step, DISCOVER_ASK_ROLE)


# Q-G invariant 3 (give-up routes to PHASE_DONE; covered by piece
# 1 but verify in final-state context).
class GiveUpFromFinalStateTests(unittest.TestCase):
    def test_give_up_token_routes_to_done(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "give up")
        self.assertTrue(result.done)
        self.assertEqual(result.journey.phase, PHASE_DONE)

    def test_give_up_numeric_routes_to_done(self):
        j = _make_exhausted_olga()
        # Final-state menu indices: 1=Start fresh, 2=Retry, 3=Give up
        result = _advance_review_empty(j, "3")
        self.assertTrue(result.done)
        self.assertEqual(result.journey.phase, PHASE_DONE)


# Q-G invariant 4 (summary mentions each applied widening). Tests
# the _format_applied_widening_bullet helper directly so we don't
# need to construct a journey that triggers final-state for each
# single widening (which would require the other 2 to also be
# excluded -- doable but noisy). The full-rendering invariant is
# already covered by TriggerConditionTests.test_summary_lists_
# every_applied_widening using the exhausted-Olga fixture.
class SummaryEnumeratesAppliedWideningsTests(unittest.TestCase):
    def test_widen_location_bullet(self):
        j = UserJourney(
            role_text="Pflegehelfer", location="",
            target_roles=["Pflegehelfer"],
        )
        bullet = _format_applied_widening_bullet(j, WIDEN_LOCATION)
        self.assertIn("**Widened location**", bullet)
        self.assertIn("searched without the location filter", bullet)

    def test_drop_seniority_bullet_includes_stripped_role(self):
        j = UserJourney(
            role_text="DevOps Engineer", location="Berlin",
            target_roles=["DevOps Engineer"],
        )
        bullet = _format_applied_widening_bullet(j, DROP_SENIORITY)
        self.assertIn("**Dropped seniority qualifier**", bullet)
        self.assertIn('"DevOps Engineer"', bullet)

    def test_try_laterals_bullet_lists_laterals(self):
        j = UserJourney(
            role_text="DevOps Engineer", location="Berlin",
            target_roles=[
                "DevOps Engineer", "sre", "platform engineer",
            ],
        )
        bullet = _format_applied_widening_bullet(j, TRY_LATERALS)
        self.assertIn("**Tried lateral roles**", bullet)
        self.assertIn("sre", bullet)
        self.assertIn("platform engineer", bullet)

    def test_try_laterals_bullet_when_no_laterals_in_target_roles(self):
        # Edge case: TRY_LATERALS in applied_widenings but
        # target_roles has only the primary -- can happen if the
        # user picked numbered subset that got de-duplicated to 0
        # additions, theoretically. Bullet should still render
        # without crashing.
        j = UserJourney(
            role_text="DevOps Engineer", location="Berlin",
            target_roles=["DevOps Engineer"],
        )
        bullet = _format_applied_widening_bullet(j, TRY_LATERALS)
        self.assertIn("**Tried lateral roles**", bullet)


# Q-G invariant 5: cache state honored (no per-widening counts in
# final-state summary per Q-C verdict C-alpha).
class NoPerWideningCountsInFinalStateTests(unittest.TestCase):
    def test_summary_has_no_count_parentheticals(self):
        j = _make_exhausted_olga()
        reply = _format_review_empty_reply(j, diagnostic_text=j.diagnostic_text)
        summary_section = reply.split("What next?")[0]
        # Per Q-C verdict (C-alpha): no per-widening counts at
        # final-state render -- cumulative-drift makes per-widening
        # cache counts mathematically misleading.
        self.assertNotIn("postings)", summary_section,
            "summary block leaked count parenthetical:\n" + summary_section)


# Q-G invariant 6: never silently routes to PHASE_DONE; unknown
# input re-asks instead.
class NeverSilentDoneFromFinalStateTests(unittest.TestCase):
    def test_unknown_input_re_asks_summary(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "asdjkfh random gibberish")
        self.assertFalse(result.done)
        self.assertEqual(result.journey.phase, PHASE_REVIEW)
        self.assertIn("You've tried these widenings:", result.reply)

    def test_empty_input_re_asks_summary(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "")
        self.assertFalse(result.done)
        self.assertEqual(result.journey.phase, PHASE_REVIEW)
        self.assertIn("You've tried these widenings:", result.reply)


# Q-G invariant 7: cross-persona panel -- each of the 7 personas
# can reach exhausted state and see the summary correctly formatted.
class CrossPersonaPanelTests(unittest.TestCase):
    PERSONAS = [
        # (persona_name, role_text, visa_constrained, location)
        ("Aicha", "Krankenschwester", True, "Berlin"),
        ("Yusuf", "Senior backend developer", True, "Munich"),
        ("Olga", "Senior DevOps Engineer", True, "Berlin"),
        ("Mahmoud", "Lagerhelfer", True, "Frankfurt"),
        ("Maria", "Bartender", False, "Hamburg"),
        ("Kaethe", "Returning Krankenschwester", False, "Leipzig"),
        ("Tobias", "Former banker", False, "Frankfurt"),
    ]

    def test_all_7_personas_render_final_state(self):
        for name, role, constrained, loc in self.PERSONAS:
            with self.subTest(persona=name):
                j = UserJourney(
                    phase=PHASE_REVIEW,
                    review_substate="empty",
                    role_text=role,
                    location=loc,
                    visa_constrained=constrained,
                    target_roles=[role, "lateral_a", "lateral_b"],
                    applied_widenings=[
                        WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS,
                    ],
                )
                # Simulate widening application effects on state
                # (DROP_SENIORITY stripped qualifier; WIDEN_LOCATION
                # cleared location; TRY_LATERALS extended targets).
                j.location = ""
                reply = _format_review_empty_reply(j)
                self.assertIn("You've tried these widenings:", reply,
                    f"{name}: missing summary block")
                self.assertIn("**Start fresh**", reply,
                    f"{name}: missing start-fresh affordance")
                self.assertIn("**Retry**", reply,
                    f"{name}: missing retry affordance")
                self.assertIn("**Give up**", reply,
                    f"{name}: missing give-up affordance")


# Q-G invariant 10 (added): parse-precedence collision -- numeric
# / start-fresh / retry / give-up don't interfere with one another.
class ParsePrecedenceTests(unittest.TestCase):
    def test_numeric_1_routes_to_start_fresh_in_final_state(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "1")
        self.assertEqual(result.journey.phase, PHASE_DISCOVER)
        self.assertEqual(result.journey.discover_step, DISCOVER_ASK_ROLE)

    def test_numeric_2_routes_to_retry_in_final_state(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "2")
        self.assertEqual(result.journey.phase, PHASE_REVIEW)
        self.assertIsNotNone(result.run_search_with)
        self.assertFalse(result.done)

    def test_numeric_3_routes_to_give_up_in_final_state(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "3")
        self.assertTrue(result.done)
        self.assertEqual(result.journey.phase, PHASE_DONE)

    def test_start_fresh_token_en(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "start fresh")
        self.assertEqual(result.journey.phase, PHASE_DISCOVER)
        self.assertEqual(result.journey.discover_step, DISCOVER_ASK_ROLE)

    def test_start_fresh_token_de(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "neu starten")
        self.assertEqual(result.journey.phase, PHASE_DISCOVER)

    def test_restart_token(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "restart")
        self.assertEqual(result.journey.phase, PHASE_DISCOVER)

    def test_retry_token_does_not_collide_with_start_fresh(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "retry")
        self.assertEqual(result.journey.phase, PHASE_REVIEW)
        self.assertIsNotNone(result.run_search_with)

    def test_stop_routes_to_give_up_not_start_fresh(self):
        # "stop" is in _REVIEW_EMPTY_GIVE_UP_TOKENS; ensure no
        # collision with the new start-fresh token set.
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "stop")
        self.assertTrue(result.done)


# Q-G invariant 11 (added): post-start-fresh discover routing --
# after start-fresh, the next user message at _advance_discover
# lands at DISCOVER_ASK_ROLE.
class PostStartFreshDiscoverRoutingTests(unittest.TestCase):
    def test_bridge_reply_contains_role_question(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "start fresh")
        self.assertIn("What kind of role this time", result.reply)
        self.assertIn("Pflegehelfer", result.reply)  # role example

    def test_post_start_fresh_discover_handler_treats_input_as_role(self):
        from company_discovery.journey import _advance_discover
        j = _make_exhausted_olga()
        _advance_review_empty(j, "start fresh")
        # Simulate the next user turn: typing a fresh role.
        result = _advance_discover(j, "Bartender")
        self.assertEqual(j.role_text, "Bartender")
        # After role, discover advances to ask_location.
        self.assertIn("Where", result.reply)


class StartFreshBridgeReplyShapeTests(unittest.TestCase):
    def test_bridge_acknowledges_clearing_old_search(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "start fresh")
        self.assertIn("clearing your old search", result.reply)

    def test_bridge_emits_role_prompt_for_discover_re_entry(self):
        j = _make_exhausted_olga()
        result = _advance_review_empty(j, "start fresh")
        # The reply ends with the standard DISCOVER_ASK_ROLE prompt
        # shape so the user recognizes the discover pattern.
        self.assertIn("**1. What kind of role this time?**", result.reply)


if __name__ == "__main__":
    unittest.main()
