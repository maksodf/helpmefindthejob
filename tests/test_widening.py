# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 3 — persona-aware widening affordances tests.

Pins the doctrine-correctness invariants operator-required 2026-05-20:

  - Visa-constraint classifier: 7-persona panel all classify correctly,
    including Yusuf's EU-Blue-Card-mobility carve-out (non-EU
    nationality but NOT constrained because Blue Card is portable).
  - Theatrical-affordance-never-offered: "loosen language" and
    "loosen visa-status" never appear in any available_affordances
    result, regardless of persona / state.
  - Caveat presence/absence: visa-constrained personas see the
    Ausländerbehörde caveat under widen-location; unconstrained
    personas don't.
  - "Try laterals" hidden when no new candidates: deterministic
    _suggest_lateral_roles minus current target_roles → 0 → affordance
    omitted (no theatrical no-op).
  - "Drop seniority" hidden when target_roles[0] has no qualifier
    (taxonomy match may have already canonicalised away the prefix —
    don't offer a no-op).
  - Cumulative-shrink invariant: each applied widening drops out of
    subsequent offers; chain through widen → drop → laterals → all
    gone.
  - Numbered + token parsing: the menu accepts both forms; bad picks
    return None (caller re-asks).
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    PHASE_REVIEW,
    UserJourney,
)
from company_discovery.persona_fixtures import PERSONAS
from company_discovery.widening import (
    DROP_SENIORITY,
    LOCATION_CAVEAT_TEXT,
    TRY_LATERALS,
    WIDEN_LOCATION,
    WideningAffordance,
    apply_widening,
    available_affordances,
    classify_visa_constraint,
    has_seniority_qualifier,
    parse_affordance_choice,
    strip_seniority_prefix,
)

# Map from persona slug to expected visa-constrained flag — pinned
# here so the classifier doesn't drift as fixtures evolve.
EXPECTED_VISA_CONSTRAINED: dict[str, bool] = {
    "aicha": True,  # §16d AufenthG
    "yusuf": False,  # EU Blue Card (PORTABLE — Yusuf carve-out)
    "olga": True,  # §24 AufenthG temporary protection
    "mahmoud": True,  # §4 AsylG subsidiary protection
    "maria": False,  # EU citizen (Freizügigkeit)
    "kaethe": False,  # German citizen
    "tobias": False,  # German citizen
}


def _journey_for_persona(persona_slug: str, *, location: str = "Berlin") -> UserJourney:
    """Build a journey state matching a panel persona's empty-state
    entry. Sets visa_constrained per the panel classification."""
    persona = next(p for p in PERSONAS if p.slug == persona_slug)
    j = UserJourney(phase=PHASE_REVIEW)
    j.review_substate = "empty"
    j.role_text = persona.target_roles[0]
    # Mirror the dispatch logic: target_roles[0] is the user-stated
    # role unless an inspire-phase lateral expansion ran; for empty-
    # state entry we use the user's verbatim.
    j.target_roles = [persona.target_roles[0]]
    j.location = location
    j.years_experience = persona.years_experience
    j.visa_constrained = classify_visa_constraint(persona.residency_status)
    return j


class VisaConstraintClassifierTests(unittest.TestCase):
    """All 7 panel personas must classify correctly. The classifier
    pattern-matches against residency_status strings; future fixtures
    that add new permit classes must extend _CONSTRAINED_PATTERNS or
    _UNCONSTRAINED_PATTERNS in widening.py."""

    def test_all_seven_panel_personas(self) -> None:
        for persona in PERSONAS:
            with self.subTest(persona=persona.slug):
                actual = classify_visa_constraint(persona.residency_status)
                expected = EXPECTED_VISA_CONSTRAINED[persona.slug]
                self.assertEqual(
                    actual,
                    expected,
                    f"persona {persona.slug} (residency_status="
                    f"{persona.residency_status!r}) must classify as "
                    f"visa_constrained={expected}, got {actual}",
                )

    def test_yusuf_blue_card_carve_out(self) -> None:
        """Pin the subtle case explicitly. Yusuf is a non-EU national
        on a portable EU Blue Card. The classifier MUST NOT gate on
        nationality — Blue Card mobility makes him unconstrained for
        empty-state widening purposes."""
        yusuf = next(p for p in PERSONAS if p.slug == "yusuf")
        self.assertIn(
            "Blue Card",
            yusuf.residency_status,
            "fixture sanity: Yusuf's residency_status must reference Blue Card",
        )
        self.assertFalse(
            classify_visa_constraint(yusuf.residency_status),
            "Yusuf's Blue Card residency MUST classify as unconstrained "
            "(Blue Card is portable across EU employers)",
        )

    def test_empty_and_unknown_default_unconstrained(self) -> None:
        for bad in (None, "", "   ", "free-text gibberish"):
            with self.subTest(input=repr(bad)):
                self.assertFalse(
                    classify_visa_constraint(bad),
                    f"input {bad!r} should default to unconstrained (don't add unnecessary caveat)",
                )


class TheatricalAffordancesNeverOfferedTests(unittest.TestCase):
    """The 2 spec'd affordances OMITTED as theatrical (loosen language,
    loosen visa-status) MUST NEVER appear in any available_affordances
    result. Verified across the 7-persona panel + various state
    permutations."""

    _FORBIDDEN_LABELS = (
        "loosen language",
        "language requirement",
        "loosen visa",
        "visa-status",
        "visa status",
    )

    def test_no_language_or_visa_affordance_for_any_persona(self) -> None:
        for persona_slug in EXPECTED_VISA_CONSTRAINED:
            for laterals in (0, 3):
                with self.subTest(persona=persona_slug, laterals=laterals):
                    j = _journey_for_persona(persona_slug)
                    offered = available_affordances(j, new_laterals_count=laterals)
                    for a in offered:
                        label_lc = a.label.lower()
                        for forbidden in self._FORBIDDEN_LABELS:
                            self.assertNotIn(
                                forbidden,
                                label_lc,
                                f"persona {persona_slug}: affordance "
                                f"label {a.label!r} contains forbidden "
                                f"theatrical pattern {forbidden!r}",
                            )

    def test_no_language_or_visa_affordance_ids(self) -> None:
        """The affordance IDs (stable strings used in applied_widenings
        + parser tokens) MUST NOT include language / visa-status."""
        for persona_slug in EXPECTED_VISA_CONSTRAINED:
            j = _journey_for_persona(persona_slug)
            offered = available_affordances(j, new_laterals_count=3)
            ids = {a.id for a in offered}
            forbidden_ids = {
                "loosen_language",
                "language",
                "loosen_visa",
                "loosen_visa_status",
                "visa_status",
            }
            self.assertFalse(
                ids & forbidden_ids,
                f"persona {persona_slug}: theatrical affordance IDs "
                f"{ids & forbidden_ids} must never appear",
            )


class CaveatPresenceTests(unittest.TestCase):
    """Visa-constrained personas (Aïcha §16d, Olga §24, Mahmoud §4
    AsylG) MUST see the Ausländerbehörde caveat under the widen-
    location affordance. Unconstrained personas MUST NOT see it."""

    def test_constrained_personas_see_caveat(self) -> None:
        for slug in ("aicha", "olga", "mahmoud"):
            with self.subTest(persona=slug):
                j = _journey_for_persona(slug)
                offered = available_affordances(j, new_laterals_count=2)
                widen = next((a for a in offered if a.id == WIDEN_LOCATION), None)
                self.assertIsNotNone(widen, f"persona {slug} must have widen_location offered")
                self.assertEqual(
                    widen.caveat,
                    LOCATION_CAVEAT_TEXT,
                    f"persona {slug}: visa-constrained, must see the "
                    f"Ausländerbehörde caveat on widen_location",
                )

    def test_unconstrained_personas_do_not_see_caveat(self) -> None:
        for slug in ("yusuf", "maria", "kaethe", "tobias"):
            with self.subTest(persona=slug):
                j = _journey_for_persona(slug)
                offered = available_affordances(j, new_laterals_count=2)
                widen = next((a for a in offered if a.id == WIDEN_LOCATION), None)
                self.assertIsNotNone(widen)
                self.assertEqual(
                    widen.caveat,
                    "",
                    f"persona {slug}: unconstrained, must NOT see the Ausländerbehörde caveat",
                )

    def test_caveat_text_is_operator_verbatim(self) -> None:
        """The caveat text matters — operator-verbatim wording avoids
        inventing legal claims. Pin the exact string."""
        self.assertIn("Ausländerbehörde", LOCATION_CAVEAT_TEXT)
        self.assertIn("Migrationsberatungsstelle", LOCATION_CAVEAT_TEXT)
        # Doctrine: no invented legal specifics
        forbidden = (
            "you must report",
            "within 14 days",
            "you may lose",
            "you will need",
            "permit revocation",
        )
        for f in forbidden:
            self.assertNotIn(
                f.lower(),
                LOCATION_CAVEAT_TEXT.lower(),
                f"caveat must not invent legal specific {f!r}",
            )


class PersonaAwareOrderingTests(unittest.TestCase):
    """Visa-constrained personas see laterals first → seniority →
    widen LAST (with caveat). Unconstrained personas see neutral
    ordering: widen → seniority → laterals."""

    def test_constrained_order_laterals_first(self) -> None:
        j = _journey_for_persona("aicha")
        j.role_text = "Senior Registered nurse"
        j.target_roles = ["Senior Registered nurse"]
        offered = available_affordances(j, new_laterals_count=3)
        ids = [a.id for a in offered]
        # All 3 should be present (Aïcha is constrained + seniority
        # qualifier present in target_roles[0] + laterals exist)
        self.assertEqual(len(ids), 3)
        # Order: laterals, drop_seniority, widen_location
        self.assertEqual(ids[0], TRY_LATERALS)
        self.assertEqual(ids[1], DROP_SENIORITY)
        self.assertEqual(ids[2], WIDEN_LOCATION)

    def test_unconstrained_order_widen_first(self) -> None:
        j = _journey_for_persona("yusuf")
        j.role_text = "Senior Mechanical engineer"
        j.target_roles = ["Senior Mechanical engineer"]
        offered = available_affordances(j, new_laterals_count=3)
        ids = [a.id for a in offered]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids[0], WIDEN_LOCATION)
        self.assertEqual(ids[1], DROP_SENIORITY)
        self.assertEqual(ids[2], TRY_LATERALS)


class TryLateralsHiddenWhenNoNewTests(unittest.TestCase):
    """try_laterals MUST be hidden when there are 0 new lateral
    candidates (after dedup against current target_roles). Operator-
    required: don't offer affordances that would do nothing."""

    def test_zero_new_laterals_hides_affordance(self) -> None:
        j = _journey_for_persona("aicha")
        offered = available_affordances(j, new_laterals_count=0)
        ids = [a.id for a in offered]
        self.assertNotIn(TRY_LATERALS, ids)

    def test_positive_new_laterals_shows_affordance(self) -> None:
        j = _journey_for_persona("aicha")
        offered = available_affordances(j, new_laterals_count=3)
        ids = [a.id for a in offered]
        self.assertIn(TRY_LATERALS, ids)


class DropSeniorityHiddenWhenNoQualifierTests(unittest.TestCase):
    """drop_seniority MUST be hidden when target_roles[0] has no
    seniority prefix. Pinned because the taxonomy match (fix #3)
    may have already canonicalised the qualifier out of target_roles[0]
    even when role_text retains it (Olga's "Senior frontend developer"
    -> matched_token "frontend developer")."""

    def test_no_qualifier_in_target_roles_hides_drop(self) -> None:
        j = _journey_for_persona("olga")
        # Simulate the post-fix-3 state: role_text retains the
        # qualifier; target_roles[0] is the canonical form
        j.role_text = "Senior frontend developer"
        j.target_roles = ["frontend developer"]
        offered = available_affordances(j, new_laterals_count=0)
        ids = [a.id for a in offered]
        self.assertNotIn(
            DROP_SENIORITY,
            ids,
            "target_roles[0] has no qualifier — dropping seniority "
            "would be a no-op for the aggregator, must be hidden",
        )

    def test_qualifier_in_target_roles_shows_drop(self) -> None:
        j = _journey_for_persona("aicha")
        j.role_text = "Senior Registered nurse"
        j.target_roles = ["Senior Registered nurse"]
        offered = available_affordances(j, new_laterals_count=0)
        ids = [a.id for a in offered]
        self.assertIn(DROP_SENIORITY, ids)


class CumulativeShrinkInvariantTests(unittest.TestCase):
    """Each applied widening drops out of subsequent offered lists.
    Chain through widen → drop → laterals → all gone."""

    def test_widen_then_drop_then_laterals_shrinks_one_at_a_time(self) -> None:
        j = _journey_for_persona("aicha")
        j.role_text = "Senior Registered nurse"
        j.target_roles = ["Senior Registered nurse"]

        # Initial: all 3 offered
        offered = available_affordances(j, new_laterals_count=3)
        self.assertEqual(len(offered), 3)

        # Apply widen
        outcome = apply_widening(j, WIDEN_LOCATION)
        self.assertEqual(outcome.action, "fire_search")
        self.assertIn(WIDEN_LOCATION, j.applied_widenings)

        # Now: 2 offered (widen dropped out; location now empty so the
        # eligibility check would also remove it from a fresh build)
        offered = available_affordances(j, new_laterals_count=3)
        ids = [a.id for a in offered]
        self.assertNotIn(WIDEN_LOCATION, ids)
        self.assertEqual(len(offered), 2)

        # Apply drop_seniority
        outcome = apply_widening(j, DROP_SENIORITY)
        self.assertEqual(outcome.action, "fire_search")

        # Now: only try_laterals
        offered = available_affordances(j, new_laterals_count=3)
        ids = [a.id for a in offered]
        self.assertEqual(ids, [TRY_LATERALS])

        # Apply try_laterals → enters laterals_offered sub-state
        outcome = apply_widening(j, TRY_LATERALS, new_laterals=["Pflegeassistent", "Altenpfleger"])
        self.assertEqual(outcome.action, "ask_confirm_laterals")
        self.assertEqual(j.review_substate, "laterals_offered")
        self.assertEqual(j.proposed_laterals, ["Pflegeassistent", "Altenpfleger"])

    def test_re_apply_idempotent(self) -> None:
        """Applying the same affordance twice is a noop the second time."""
        j = _journey_for_persona("yusuf")
        outcome = apply_widening(j, WIDEN_LOCATION)
        self.assertEqual(outcome.action, "fire_search")
        outcome2 = apply_widening(j, WIDEN_LOCATION)
        self.assertEqual(outcome2.action, "noop")


class ApplyWideningEffectsTests(unittest.TestCase):
    """Each applied widening must produce the right journey-state
    mutation + emit run_search_with with the new criteria."""

    def test_widen_location_clears_journey_location(self) -> None:
        j = _journey_for_persona("aicha")
        self.assertEqual(j.location, "Berlin")
        outcome = apply_widening(j, WIDEN_LOCATION)
        self.assertEqual(j.location, "")
        self.assertEqual(outcome.search_criteria["location"], None)

    def test_drop_seniority_strips_role_text_and_target(self) -> None:
        j = _journey_for_persona("yusuf")
        j.role_text = "Senior Mechanical engineer"
        j.target_roles = ["Senior Mechanical engineer"]
        outcome = apply_widening(j, DROP_SENIORITY)
        self.assertEqual(j.role_text, "Mechanical engineer")
        self.assertEqual(j.target_roles[0], "Mechanical engineer")
        self.assertIn("Mechanical engineer", outcome.search_criteria["target_roles"][0])

    def test_try_laterals_enters_laterals_offered(self) -> None:
        j = _journey_for_persona("aicha")
        outcome = apply_widening(
            j,
            TRY_LATERALS,
            new_laterals=["Pflegeassistent", "Altenpfleger", "OTA"],
        )
        self.assertEqual(outcome.action, "ask_confirm_laterals")
        self.assertIn("Pflegeassistent", outcome.reply)
        self.assertIn("yes", outcome.reply.lower())
        self.assertIn("no", outcome.reply.lower())
        self.assertEqual(j.review_substate, "laterals_offered")
        self.assertEqual(
            j.proposed_laterals,
            ["Pflegeassistent", "Altenpfleger", "OTA"],
        )
        # TRY_LATERALS is NOT yet in applied_widenings — that happens
        # when the user confirms in the sub-state handler
        self.assertNotIn(TRY_LATERALS, j.applied_widenings)

    def test_try_laterals_with_empty_list_is_noop(self) -> None:
        j = _journey_for_persona("aicha")
        outcome = apply_widening(j, TRY_LATERALS, new_laterals=[])
        self.assertEqual(outcome.action, "noop")
        self.assertNotEqual(j.review_substate, "laterals_offered")


class ParseAffordanceChoiceTests(unittest.TestCase):
    """The user can pick by number or token. Bad picks return None
    so the caller re-asks."""

    def test_numbered_pick_in_range(self) -> None:
        a1 = WideningAffordance(id="x", label="X", description="x")
        a2 = WideningAffordance(id="y", label="Y", description="y")
        offered = [a1, a2]
        self.assertEqual(parse_affordance_choice("1", offered), a1)
        self.assertEqual(parse_affordance_choice("2", offered), a2)

    def test_numbered_pick_out_of_range(self) -> None:
        a1 = WideningAffordance(id="x", label="X", description="x")
        self.assertIsNone(parse_affordance_choice("0", [a1]))
        self.assertIsNone(parse_affordance_choice("5", [a1]))

    def test_token_pick_widen(self) -> None:
        offered = [
            WideningAffordance(id=WIDEN_LOCATION, label="Widen location", description="..."),
        ]
        for tok in ("widen", "widen location", "anywhere"):
            self.assertEqual(parse_affordance_choice(tok, offered).id, WIDEN_LOCATION)

    def test_token_pick_unknown_returns_none(self) -> None:
        offered = [
            WideningAffordance(id=WIDEN_LOCATION, label="Widen location", description="..."),
        ]
        self.assertIsNone(parse_affordance_choice("huh", offered))
        self.assertIsNone(parse_affordance_choice("", offered))


class SeniorityPrefixHelpersTests(unittest.TestCase):
    def test_has_seniority_qualifier_positive(self) -> None:
        for text in (
            "Senior frontend developer",
            "Lead Krankenpfleger",
            "Junior engineer",
            "Principal architect",
            "Staff engineer",
            "Head of design",
            "Chief data officer",
        ):
            with self.subTest(text=text):
                self.assertTrue(has_seniority_qualifier(text))

    def test_has_seniority_qualifier_negative(self) -> None:
        for text in (
            "Registered nurse",
            "Mechanical engineer",
            "Altenpflegerin",
            "Krankenschwester (Wiedereinstieg)",  # parens preserve, no prefix
            "",
            None,
        ):
            with self.subTest(text=text):
                self.assertFalse(has_seniority_qualifier(text))

    def test_strip_seniority_prefix_idempotent_when_absent(self) -> None:
        for text in ("Registered nurse", "Mechanical engineer", "Altenpflegerin"):
            self.assertEqual(strip_seniority_prefix(text), text)

    def test_strip_seniority_prefix_removes_when_present(self) -> None:
        self.assertEqual(
            strip_seniority_prefix("Senior frontend developer"),
            "frontend developer",
        )
        self.assertEqual(strip_seniority_prefix("Lead Krankenpfleger"), "Krankenpfleger")


if __name__ == "__main__":
    unittest.main()
