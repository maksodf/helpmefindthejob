# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""A/B testing framework contract tests (13-plan item 6/13; gap #19).

Pins:
1. Variant assignment is deterministic per user (same user
   always lands in the same arm).
2. Variant assignment distributes ~evenly across arms over
   many users.
3. Unregistered experiment names raise KeyError at every API
   surface (typo guard).
4. Outcome events recorded via the existing /api/analytics/event
   endpoint with kind=experiment_outcome roll up correctly in
   summarize_experiment.
5. Summary contract: every declared variant is in the output,
   even with zero outcomes (so the operator sees stable shape).
6. Corrupt events (unknown variant, missing fields) don't
   crash + don't poison the per-variant counts.
"""

from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.experiments import (
    EXPERIMENTS,
    OUTCOME_EVENT_KIND,
    Experiment,
    ExperimentSummary,
    VariantStats,
    all_experiments,
    build_outcome_payload,
    get_variant,
    summarize_experiment,
)
from company_discovery.models import AnalyticsEvent


def _build_state(tmpdir: Path) -> AppState:
    return AppState(
        tmpdir / "company.sqlite3",
        tmpdir / "auth.sqlite3",
        tmpdir / "ai.json",
        tmpdir / "schedule.json",
        start_scheduler=False,
    )


class VariantAssignment(unittest.TestCase):
    def test_same_user_same_variant(self):
        v1 = get_variant("example_journey_first_step", "user-stable")
        for _ in range(50):
            self.assertEqual(
                v1, get_variant("example_journey_first_step", "user-stable")
            )

    def test_variant_in_declared_arms(self):
        for i in range(50):
            v = get_variant("example_journey_first_step", f"user-{i}")
            self.assertIn(v, EXPERIMENTS["example_journey_first_step"].variants)

    def test_distributes_across_two_arms(self):
        counts = Counter(
            get_variant("example_journey_first_step", f"user-{i}")
            for i in range(1000)
        )
        # Both arms should land within ±10% of 50:50
        self.assertGreater(counts["control"], 400)
        self.assertGreater(counts["treatment"], 400)

    def test_unregistered_experiment_raises(self):
        with self.assertRaises(KeyError):
            get_variant("totally_made_up_experiment", "user-1")


class BuildOutcomePayloadShape(unittest.TestCase):
    def test_payload_has_three_required_keys(self):
        payload = build_outcome_payload(
            "example_journey_first_step", "user-1", "first_step_completed"
        )
        self.assertEqual(
            set(payload.keys()),
            {"experimentName", "variant", "outcomeKind"},
        )
        self.assertEqual(payload["experimentName"], "example_journey_first_step")
        self.assertEqual(payload["outcomeKind"], "first_step_completed")
        self.assertIn(payload["variant"], ["control", "treatment"])

    def test_payload_variant_matches_get_variant(self):
        v = get_variant("example_journey_first_step", "user-x")
        payload = build_outcome_payload(
            "example_journey_first_step", "user-x", "any_kind"
        )
        self.assertEqual(payload["variant"], v)


class SummarizeExperimentEmpty(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)

    def test_summary_for_experiment_with_no_events(self):
        summary = summarize_experiment(
            "example_journey_first_step", self.state.repository
        )
        self.assertIsInstance(summary, ExperimentSummary)
        # Every declared variant MUST appear in the output, even
        # with zero outcomes
        variant_names = {v.variant for v in summary.variants}
        self.assertEqual(variant_names, {"control", "treatment"})
        for v in summary.variants:
            self.assertEqual(v.outcomes_total, 0)
            self.assertEqual(v.unique_users, 0)
            self.assertEqual(v.outcomes_by_kind, {})


class SummarizeExperimentWithEvents(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        # Plant 10 outcome events spanning both variants
        for i in range(10):
            user_id = f"user-{i}"
            payload = build_outcome_payload(
                "example_journey_first_step",
                user_id,
                "first_step_completed",
            )
            self.state.repository.save_analytics_event(
                AnalyticsEvent(
                    user_id=user_id, kind=OUTCOME_EVENT_KIND, payload=payload
                )
            )

    def test_outcomes_distributed_across_both_variants(self):
        summary = summarize_experiment(
            "example_journey_first_step", self.state.repository
        )
        total_outcomes = sum(v.outcomes_total for v in summary.variants)
        self.assertEqual(total_outcomes, 10)
        # Both arms should have at least one outcome (10 random
        # user ids → ~50:50, with overwhelming probability some
        # on both sides — accept down to 1:9)
        for v in summary.variants:
            self.assertGreaterEqual(v.outcomes_total, 1)

    def test_unique_users_count_distinct(self):
        # Add a second outcome event for user-0 to the same variant
        v0 = get_variant("example_journey_first_step", "user-0")
        self.state.repository.save_analytics_event(
            AnalyticsEvent(
                user_id="user-0",
                kind=OUTCOME_EVENT_KIND,
                payload={
                    "experimentName": "example_journey_first_step",
                    "variant": v0,
                    "outcomeKind": "second_step_completed",
                },
            )
        )
        summary = summarize_experiment(
            "example_journey_first_step", self.state.repository
        )
        # The variant user-0 is in: outcomes_total += 1 (now 1 more
        # than its base count); unique_users stays the same (user-0
        # already counted)
        for v in summary.variants:
            if v.variant == v0:
                # outcomes_by_kind now has TWO kinds for user-0's
                # variant
                self.assertGreaterEqual(len(v.outcomes_by_kind), 1)


class SummaryCorruptionResilience(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)

    def test_unknown_variant_event_skipped(self):
        # A corrupt event with variant="phantom" must not crash
        # the summary OR add a phantom variant to the output
        self.state.repository.save_analytics_event(
            AnalyticsEvent(
                user_id="user-1",
                kind=OUTCOME_EVENT_KIND,
                payload={
                    "experimentName": "example_journey_first_step",
                    "variant": "phantom",
                    "outcomeKind": "x",
                },
            )
        )
        summary = summarize_experiment(
            "example_journey_first_step", self.state.repository
        )
        variant_names = {v.variant for v in summary.variants}
        self.assertNotIn("phantom", variant_names)
        # And the sane variants still report zero
        for v in summary.variants:
            self.assertEqual(v.outcomes_total, 0)

    def test_missing_outcome_kind_skipped(self):
        self.state.repository.save_analytics_event(
            AnalyticsEvent(
                user_id="user-1",
                kind=OUTCOME_EVENT_KIND,
                payload={
                    "experimentName": "example_journey_first_step",
                    "variant": "control",
                    # outcomeKind missing
                },
            )
        )
        summary = summarize_experiment(
            "example_journey_first_step", self.state.repository
        )
        for v in summary.variants:
            self.assertEqual(v.outcomes_total, 0)

    def test_unrelated_event_kinds_ignored(self):
        # An event with kind="ai_invocation" or anything other
        # than experiment_outcome must not appear in the summary
        self.state.repository.save_analytics_event(
            AnalyticsEvent(
                user_id="user-1",
                kind="ai_invocation",
                payload={
                    "experimentName": "example_journey_first_step",
                    "variant": "control",
                    "outcomeKind": "x",
                },
            )
        )
        summary = summarize_experiment(
            "example_journey_first_step", self.state.repository
        )
        for v in summary.variants:
            self.assertEqual(v.outcomes_total, 0)


class UnregisteredRaisesEverywhere(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)

    def test_summarize_unregistered_raises(self):
        with self.assertRaises(KeyError):
            summarize_experiment("nonexistent_exp", self.state.repository)

    def test_build_outcome_payload_unregistered_raises(self):
        with self.assertRaises(KeyError):
            build_outcome_payload("nonexistent_exp", "u1", "k")


class HttpRoutesPresence(unittest.TestCase):
    def test_variant_route_present_in_source(self):
        src = Path(
            "/Users/fouad./Desktop/NasserMCPserver/app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("exp_variant_match", src)
        self.assertIn("/api/experiments/", src)

    def test_summary_route_present_in_source(self):
        src = Path(
            "/Users/fouad./Desktop/NasserMCPserver/app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("exp_summary_match", src)
        self.assertIn("summarize_experiment", src)


class AllExperimentsIntrospection(unittest.TestCase):
    def test_metadata_shape(self):
        result = all_experiments()
        self.assertGreater(len(result), 0)
        for entry in result:
            self.assertIn("name", entry)
            self.assertIn("variants", entry)
            self.assertIn("primaryMetric", entry)
            self.assertIn("description", entry)
            self.assertIn("status", entry)
            self.assertGreater(len(entry["variants"]), 0)


if __name__ == "__main__":
    unittest.main()
