# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 10.2 — UserProfile.friction_class field + cv_check
classification hook + telemetry-event emission.

Pins:
  - UserProfile.friction_class defaults to "" (serialization sanity)
  - cv_check paste-branch writes friction_class via classifier
  - Re-paste with unclassifiable CV CLEARS stale classification
  - Analytics event emitted per classification call (loose contract)
  - Backward compat: existing JSON without the field deserializes to ""
"""
from __future__ import annotations

import dataclasses
import json
import unittest

from company_discovery.journey import (
    PHASE_CV_CHECK,
    PHASE_GREET,
    AdvanceResult,
    UserJourney,
    advance,
)
from company_discovery.models import UserProfile


def _aicha_cv() -> str:
    """CV that the friction_classifier resolves as aicha/strong.
    Same shape as scripts/post_bug_c_aicha_walk._aicha_cv_paste()
    but inlined here to avoid the script import."""
    return (
        "Aïcha (Tunisia → Berlin)\n"
        "Email: aicha+test@example.test\n"
        "Phone: +49 30 1234-5678\n"
        "Residency status: §16d AufenthG (visa for purpose of "
        "recognition of foreign qualification)\n\n"
        "Profile: Registered nurse with seven years of hospital "
        "experience in Tunisia, including two years in geriatric care. "
        "Currently in §16d Anerkennung process with BIBB / Anabin.\n\n"
        "Experience:\n"
        "  - 2019 - 2026 — Geriatric ward, Tunis\n"
    )


def _neutral_cv() -> str:
    """CV that the friction_classifier does NOT classify (no strong
    markers, no scored hits >= 2)."""
    return (
        "Generic Candidate\n"
        "Email: someone@example.test\n"
        "Phone: +49 30 0000-0000\n\n"
        "Profile: software engineer with 5 years of experience in "
        "distributed systems and cloud platforms.\n\n"
        "Experience:\n"
        "  - 2019 - 2024 — TechCo, Berlin\n"
    )


def _build_paste_journey() -> UserJourney:
    """Journey in PHASE_CV_CHECK ready for the paste branch.
    cv_status='unknown' triggers the path that detects the paste."""
    return UserJourney(
        phase=PHASE_CV_CHECK,
        cv_status="unknown",
        role_text="Registered nurse",
        location="Berlin",
    )


# ─── UserProfile field default + serialization ───────────────────


class FrictionClassFieldDefaultTests(unittest.TestCase):
    def test_default_is_empty_string(self):
        profile = UserProfile(user_id="u1")
        self.assertEqual(profile.friction_class, "")

    def test_field_is_str_type(self):
        profile = UserProfile(user_id="u1")
        self.assertIsInstance(profile.friction_class, str)

    def test_field_explicit_assignment_works(self):
        profile = UserProfile(user_id="u1", friction_class="aicha")
        self.assertEqual(profile.friction_class, "aicha")


class FrictionClassBackwardCompatTests(unittest.TestCase):
    """Operator-specified invariant: existing UserProfile entries
    serialized BEFORE this field existed must deserialize cleanly.
    Default "" via dataclass default. No migration script."""

    def test_dataclass_field_exists_in_fields_list(self):
        field_names = {f.name for f in dataclasses.fields(UserProfile)}
        self.assertIn("friction_class", field_names)

    def test_serialized_profile_without_field_deserializes_to_empty(self):
        # Simulate a stored profile JSON shape from before the
        # friction_class field existed. Construct UserProfile with
        # the legacy field set; new field falls to default.
        legacy_payload = {
            "user_id": "legacy-user",
            "persona_id": "tech",
            "location": "Berlin",
        }
        profile = UserProfile(**legacy_payload)
        self.assertEqual(profile.friction_class, "")
        # Other fields unaffected
        self.assertEqual(profile.persona_id, "tech")
        self.assertEqual(profile.location, "Berlin")

    def test_dataclass_asdict_includes_new_field(self):
        profile = UserProfile(user_id="u1", friction_class="aicha")
        d = dataclasses.asdict(profile)
        self.assertIn("friction_class", d)
        self.assertEqual(d["friction_class"], "aicha")


# ─── cv_check paste-branch classification hook ───────────────────


class CvCheckPasteClassificationTests(unittest.TestCase):
    """Operator-specified: cv_check paste-branch writes
    friction_class via classifier."""

    def test_aicha_cv_paste_writes_friction_class(self):
        journey = _build_paste_journey()
        result = advance(journey, _aicha_cv())
        self.assertIn("friction_class", result.profile_updates)
        self.assertEqual(result.profile_updates["friction_class"], "aicha")

    def test_neutral_cv_paste_writes_empty_friction_class(self):
        journey = _build_paste_journey()
        result = advance(journey, _neutral_cv())
        # Classifier returns "" for unclassifiable; field UPDATES
        # to "" (not omitted -- the write must overwrite stale).
        self.assertIn("friction_class", result.profile_updates)
        self.assertEqual(result.profile_updates["friction_class"], "")

    def test_paste_also_writes_cv_text(self):
        """Pre-existing cv_text write must still fire alongside the
        new friction_class write."""
        journey = _build_paste_journey()
        result = advance(journey, _aicha_cv())
        self.assertIn("cv_text", result.profile_updates)


# ─── Re-classification semantics (operator subtle behavior) ──────


class ReClassificationSemanticsTests(unittest.TestCase):
    """Operator-specified subtle behavior: if a user pastes CV-1
    that classifies (e.g., "aicha"), then later re-pastes CV-2 that
    doesn't classify, friction_class must CLEAR to "" (not retain
    the stale "aicha"). Stale classification drives wrong UX in
    Bug C piece-3 + analysis.py — worse than no classification."""

    def test_reclassification_to_empty_clears_stale_value(self):
        # First paste — classifies as aicha
        j1 = _build_paste_journey()
        r1 = advance(j1, _aicha_cv())
        self.assertEqual(r1.profile_updates["friction_class"], "aicha")

        # Second paste — does NOT classify; friction_class must
        # OVERWRITE to "" (not be omitted from profile_updates).
        j2 = _build_paste_journey()
        r2 = advance(j2, _neutral_cv())
        self.assertIn(
            "friction_class", r2.profile_updates,
            "friction_class must be in profile_updates on every paste "
            "(unconditional write); otherwise stale prior values leak",
        )
        self.assertEqual(r2.profile_updates["friction_class"], "")

    def test_reclassification_to_different_persona_overwrites(self):
        # First paste — aicha
        j1 = _build_paste_journey()
        r1 = advance(j1, _aicha_cv())
        self.assertEqual(r1.profile_updates["friction_class"], "aicha")

        # Second paste — yusuf-shaped CV. friction_class must
        # update to "yusuf".
        yusuf_cv = (
            "Mechanical engineer, ITÜ Istanbul, 13 years in automotive "
            "Tier-2 supplier work in Bursa. EU Blue Card application "
            "in progress, employer-sponsored at a Munich firm. CATIA, "
            "SolidWorks.\nEmail: yusuf@x.de\nPhone: +49 89 1234"
        )
        j2 = _build_paste_journey()
        r2 = advance(j2, yusuf_cv)
        self.assertEqual(r2.profile_updates["friction_class"], "yusuf")


# ─── Telemetry event emission (OQ-2 contract) ────────────────────


class TelemetryEventEmissionTests(unittest.TestCase):
    """OQ-2 verdict: single analytics event per classification call.
    Loose contract — fires once with the expected event name; payload
    shape includes resolved/confidence/match_count fields. Caller
    (app.py dispatcher) writes via log_analytics."""

    def test_event_emitted_on_paste(self):
        journey = _build_paste_journey()
        result = advance(journey, _aicha_cv())
        # One event emitted with the expected name.
        event_names = [name for (name, _) in result.analytics_events]
        self.assertIn("friction_class_classified", event_names)

    def test_event_payload_contains_expected_fields(self):
        journey = _build_paste_journey()
        result = advance(journey, _aicha_cv())
        # Locate the friction_class_classified event
        events = [
            (n, p) for (n, p) in result.analytics_events
            if n == "friction_class_classified"
        ]
        self.assertEqual(len(events), 1)
        _, payload = events[0]
        for key in ("resolved", "confidence", "match_count"):
            self.assertIn(key, payload)
        # Resolved matches the classifier's output for this CV
        self.assertEqual(payload["resolved"], "aicha")
        self.assertEqual(payload["confidence"], "strong")
        self.assertEqual(payload["match_count"], 1)

    def test_event_emitted_even_when_unclassified(self):
        """Telemetry fires regardless of classifier outcome.
        Phase 2 UX design needs to know how often classification
        falls through to '' — that requires the event firing on
        non-matches too."""
        journey = _build_paste_journey()
        result = advance(journey, _neutral_cv())
        events = [
            (n, p) for (n, p) in result.analytics_events
            if n == "friction_class_classified"
        ]
        self.assertEqual(len(events), 1)
        _, payload = events[0]
        self.assertEqual(payload["resolved"], "")
        self.assertEqual(payload["confidence"], "none")
        self.assertEqual(payload["match_count"], 0)


# ─── AdvanceResult.analytics_events shape ────────────────────────


class AdvanceResultAnalyticsChannelTests(unittest.TestCase):
    """The new analytics_events channel is symmetric with
    profile_updates. Defaults to empty list; dispatcher iterates."""

    def test_default_is_empty_list(self):
        # Construct an AdvanceResult without analytics_events arg
        result = AdvanceResult(reply="x", journey=UserJourney())
        self.assertEqual(result.analytics_events, [])

    def test_entries_are_tuple_of_name_and_payload(self):
        result = AdvanceResult(
            reply="x",
            journey=UserJourney(),
            analytics_events=[("event_a", {"k": 1}), ("event_b", {})],
        )
        self.assertEqual(len(result.analytics_events), 2)
        name, payload = result.analytics_events[0]
        self.assertEqual(name, "event_a")
        self.assertEqual(payload, {"k": 1})


# ─── Hook does NOT fire on non-paste cv_check inputs ─────────────


class HookFiresOnlyOnPasteTests(unittest.TestCase):
    """The classification hook lives INSIDE the paste branch of
    _advance_cv_check. Non-paste inputs (reuse, build, ambiguous
    text) must NOT emit the event."""

    def test_reuse_branch_no_classification(self):
        from company_discovery.journey import _advance_cv_check
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        result = _advance_cv_check(journey, "reuse", has_existing_cv=True)
        event_names = [n for (n, _) in result.analytics_events]
        self.assertNotIn("friction_class_classified", event_names)

    def test_build_branch_no_classification(self):
        from company_discovery.journey import _advance_cv_check
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        result = _advance_cv_check(journey, "build", has_existing_cv=False)
        event_names = [n for (n, _) in result.analytics_events]
        self.assertNotIn("friction_class_classified", event_names)

    def test_unparseable_input_no_classification(self):
        from company_discovery.journey import _advance_cv_check
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        result = _advance_cv_check(journey, "???", has_existing_cv=False)
        event_names = [n for (n, _) in result.analytics_events]
        self.assertNotIn("friction_class_classified", event_names)


if __name__ == "__main__":
    unittest.main()
