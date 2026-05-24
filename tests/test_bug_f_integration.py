# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 10.3 — Bug F Option B end-to-end integration tests.

Pins the full chain (regression suite, no Ollama / no HTTP):
  CV-paste -> classifier -> profile.friction_class write ->
  empty-state dispatcher reads friction_class -> _persona_fixture_
  for() returns fixture -> classify_visa_constraint() returns True
  -> journey.visa_constrained=True -> Bug C piece-3 constrained
  ordering + Ausländerbehörde caveat activate.

The chain is independently covered:
  - friction_classifier: tests/test_friction_classifier.py
  - cv_check hook + field: tests/test_friction_class_field.py
  - empty-state routing: tests/test_review_routing.py +
    test_review_empty_state.py + test_review_final_state.py
  - dispatcher visa_constrained classification: app.py 3858-3876
    integration via Loop 9.3 walk

This file pins the END-TO-END contract by direct unit-level
simulation of the dispatcher's classification chain. Future
refactors that break ANY link in the chain fail loudly here.
"""

from __future__ import annotations

import unittest

from company_discovery.analysis import _persona_fixture_for
from company_discovery.friction_classifier import classify
from company_discovery.journey import (
    PHASE_CV_CHECK,
    PHASE_REVIEW,
    UserJourney,
    _format_review_empty_reply,
    advance,
)
from company_discovery.models import UserProfile
from company_discovery.widening import (
    WIDEN_LOCATION,
    classify_visa_constraint,
)


def _aicha_cv() -> str:
    return (
        "Aïcha (Tunisia → Berlin)\n"
        "Email: aicha+integration@example.test\n"
        "Phone: +49 30 1234-5678\n"
        "Residency status: §16d AufenthG (visa for purpose of "
        "recognition of foreign qualification)\n\n"
        "Profile: Registered nurse with seven years of hospital "
        "experience in Tunisia, including two years in geriatric "
        "care. Currently in §16d Anerkennung process with BIBB / "
        "Anabin recognition databases.\n\n"
        "Experience:\n"
        "  - 2019 - 2026 — Geriatric ward, Tunis\n"
    )


def _maria_cv() -> str:
    """Maria — EU citizen, NOT visa-constrained."""
    return (
        "Maria (Spain → Hamburg)\n"
        "Email: maria@example.test\n"
        "Phone: +49 40 1234-5678\n"
        "Residency status: EU citizen, Freizügigkeitsrecht\n\n"
        "Profile: Native Spanish speaker, EU-Bürger from Spain. "
        "Hospitality / bartender background.\n\n"
        "Experience:\n"
        "  - 2020 - 2025 — Bar Reina, Madrid\n"
    )


def _neutral_cv() -> str:
    """CV that does NOT classify — confirms unconstrained UX."""
    return (
        "Generic candidate\n"
        "Email: x@example.test\n"
        "Phone: +49 30 0000-0000\n\n"
        "Software engineer with 5 years experience.\n\n"
        "Experience:\n  - 2019 - 2024 — TechCo (Berlin)\n"
    )


# ─── End-to-end: paste -> profile_updates -> dispatcher chain ────


class CvPasteWritesFrictionClassEndToEndTests(unittest.TestCase):
    """First link: cv_check paste -> profile_updates['friction_class']
    set by classifier. Already pinned by Loop 10.2 tests; re-pinned
    here in the integration suite to fail loudly if the chain
    breaks."""

    def test_aicha_paste_sets_friction_class(self):
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        result = advance(journey, _aicha_cv())
        self.assertEqual(
            result.profile_updates.get("friction_class"),
            "aicha",
        )

    def test_maria_paste_sets_friction_class(self):
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        result = advance(journey, _maria_cv())
        self.assertEqual(
            result.profile_updates.get("friction_class"),
            "maria",
        )

    def test_neutral_paste_writes_empty_friction_class(self):
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        result = advance(journey, _neutral_cv())
        self.assertEqual(
            result.profile_updates.get("friction_class"),
            "",
        )


# ─── _persona_fixture_for reads friction_class slug ──────────────


class FixtureLookupUsesFrictionClassTests(unittest.TestCase):
    """Second link: _persona_fixture_for(slug) returns the right
    fixture for fixture slugs. Bug F Option B (Loop 10.3) rewired
    callers to pass profile.friction_class instead of
    profile.persona_id."""

    def test_lookup_resolves_aicha(self):
        fixture = _persona_fixture_for("aicha")
        self.assertIsNotNone(fixture)
        self.assertEqual(fixture.slug, "aicha")
        self.assertIn("§16d", fixture.residency_status)

    def test_lookup_resolves_maria(self):
        fixture = _persona_fixture_for("maria")
        self.assertIsNotNone(fixture)
        self.assertEqual(fixture.slug, "maria")

    def test_lookup_returns_none_for_empty_string(self):
        # friction_class="" (unclassified) — lookup must return None
        # so downstream falls back to unconstrained UX.
        self.assertIsNone(_persona_fixture_for(""))

    def test_lookup_returns_none_for_registry_persona_id(self):
        # The pre-Bug-F-Option-B failure mode: callers pass a
        # 15-registry persona_id, never a fixture slug, so the
        # lookup always returned None. Post-fix this branch is
        # the unclassified case (registry IDs shouldn't reach
        # _persona_fixture_for under the new wiring, but if they
        # do, return None safely).
        self.assertIsNone(_persona_fixture_for("healthcare-management"))


# ─── classify_visa_constraint reads fixture.residency_status ────


class VisaConstraintActivationTests(unittest.TestCase):
    """Third link: friction_class -> fixture -> residency_status ->
    classify_visa_constraint -> journey.visa_constrained. Each
    persona's fixture residency_status correctly classifies."""

    def test_aicha_residency_is_visa_constrained(self):
        fixture = _persona_fixture_for("aicha")
        self.assertTrue(classify_visa_constraint(fixture.residency_status))

    def test_maria_residency_is_NOT_visa_constrained(self):
        # EU citizen — unconstrained (Freizügigkeitsrecht).
        fixture = _persona_fixture_for("maria")
        self.assertFalse(classify_visa_constraint(fixture.residency_status))

    def test_unclassified_friction_class_is_unconstrained(self):
        # friction_class="" -> fixture=None -> residency_status=""
        # -> visa_constrained=False.
        fixture = _persona_fixture_for("")
        residency = getattr(fixture, "residency_status", "") or ""
        self.assertFalse(classify_visa_constraint(residency))


# ─── End-to-end: empty-state reply for visa-constrained user ────


class EmptyStateUxForFrictionClassifiedUserTests(unittest.TestCase):
    """Final link: a journey with visa_constrained=True (set by the
    dispatcher from profile.friction_class -> fixture chain) renders
    Bug C piece-3 constrained-order menu + Ausländerbehörde caveat.

    Pre-Bug-F-Option-B failure mode: visa_constrained=False for all
    real users, so the caveat never rendered + ordering was
    unconstrained (widen-location first instead of try-laterals).
    """

    def test_visa_constrained_journey_renders_caveat(self):
        # Simulate the post-classification journey state for an
        # Aïcha-class user. The dispatcher would have set
        # visa_constrained=True from
        # _persona_fixture_for("aicha").residency_status.
        journey = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="Krankenpfleger",
            target_roles=["Krankenpfleger"],
            location="Berlin",
            visa_constrained=True,  # ← the integration chain's output
            applied_widenings=[],
            diagnostic_text=("No live postings found for 'Krankenpfleger' in Berlin."),
        )
        reply = _format_review_empty_reply(
            journey,
            diagnostic_text=journey.diagnostic_text,
        )
        # Ausländerbehörde caveat renders under widen-location
        self.assertIn("Ausländerbehörde", reply)
        self.assertIn("Migrationsberatungsstelle", reply)

    def test_unconstrained_journey_does_not_render_caveat(self):
        # Counterfactual: Maria's friction_class="maria" resolves
        # to fixture with EU-citizen residency -> visa_constrained=
        # False. No caveat.
        journey = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="Bartender",
            target_roles=["Bartender"],
            location="Hamburg",
            visa_constrained=False,  # ← Maria
            applied_widenings=[],
        )
        reply = _format_review_empty_reply(journey)
        self.assertNotIn("Ausländerbehörde", reply)

    def test_visa_constrained_ordering_puts_laterals_first(self):
        # Bug C piece-3 constrained order:
        # TRY_LATERALS, DROP_SENIORITY, WIDEN_LOCATION
        from company_discovery.widening import (
            TRY_LATERALS,
            available_affordances,
        )

        journey = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="Krankenpfleger",
            target_roles=["Krankenpfleger"],
            location="Berlin",
            visa_constrained=True,
        )
        offered = available_affordances(journey, new_laterals_count=3)
        self.assertGreater(len(offered), 0)
        # First affordance for constrained persona is TRY_LATERALS
        self.assertEqual(offered[0].id, TRY_LATERALS)

    def test_unconstrained_ordering_puts_widen_first(self):
        # Unconstrained order: WIDEN_LOCATION first
        from company_discovery.widening import (
            available_affordances,
        )

        journey = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="Bartender",
            target_roles=["Bartender"],
            location="Hamburg",
            visa_constrained=False,
        )
        offered = available_affordances(journey, new_laterals_count=3)
        self.assertGreater(len(offered), 0)
        self.assertEqual(offered[0].id, WIDEN_LOCATION)


# ─── Full chain smoke test ──────────────────────────────────────


class FullChainContractSmokeTest(unittest.TestCase):
    """Single test pinning the whole chain in one place, mirroring
    what the Loop 10.3 live walk validates against the running
    server. If this fails, the substrate is broken in the
    regression suite before we ever launch a walk."""

    def test_aicha_cv_to_caveat_full_chain(self):
        # 1. classifier resolves Aïcha CV -> "aicha"
        slug = classify(_aicha_cv())
        self.assertEqual(slug, "aicha")

        # 2. profile.friction_class set (simulating the dispatcher
        # write via _journey_apply_profile_updates)
        profile = UserProfile(user_id="test-aicha", friction_class=slug)
        self.assertEqual(profile.friction_class, "aicha")

        # 3. dispatcher's empty-state path reads profile.friction_
        # class -> resolves fixture
        fixture = _persona_fixture_for(profile.friction_class)
        self.assertIsNotNone(fixture)

        # 4. fixture.residency_status -> classify_visa_constraint
        # -> visa_constrained=True
        residency = fixture.residency_status
        is_constrained = classify_visa_constraint(residency)
        self.assertTrue(is_constrained)

        # 5. journey.visa_constrained=True -> Bug C piece-3 menu
        # renders Ausländerbehörde caveat under WIDEN_LOCATION
        journey = UserJourney(
            phase=PHASE_REVIEW,
            review_substate="empty",
            role_text="Krankenpfleger",
            target_roles=["Krankenpfleger"],
            location="Berlin",
            visa_constrained=is_constrained,
        )
        reply = _format_review_empty_reply(journey)
        self.assertIn("Ausländerbehörde", reply)

    def test_maria_cv_to_unconstrained_full_chain(self):
        # 1. classifier resolves Maria CV -> "maria"
        slug = classify(_maria_cv())
        self.assertEqual(slug, "maria")

        # 2. profile.friction_class set
        profile = UserProfile(user_id="test-maria", friction_class=slug)
        # 3-5: chain resolves to NOT visa-constrained
        fixture = _persona_fixture_for(profile.friction_class)
        is_constrained = classify_visa_constraint(fixture.residency_status if fixture else "")
        self.assertFalse(is_constrained)

    def test_neutral_cv_to_unclassified_full_chain(self):
        # 1. classifier -> ""
        slug = classify(_neutral_cv())
        self.assertEqual(slug, "")

        # 2-5: empty friction_class -> no fixture -> unconstrained
        profile = UserProfile(user_id="test-neutral", friction_class=slug)
        fixture = _persona_fixture_for(profile.friction_class)
        self.assertIsNone(fixture)
        is_constrained = classify_visa_constraint(getattr(fixture, "residency_status", "") or "")
        self.assertFalse(is_constrained)


if __name__ == "__main__":
    unittest.main()
