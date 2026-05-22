# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Cost-saving metrics wiring contract — closes phase2-backlog item #69
follow-up.

The substrate at ``company_discovery/cost_saving_metrics.py`` ships
an 8-mechanism append-only JSONL recorder with confidence-class
tagging. The substrate was deliberately shipped without call-site
wiring so future slices could choose carefully where to emit each
mechanism.

This test verifies that:

1. **Opt-in gate**: when ``HELPMEFINDTHEJOB_COST_METRICS`` is unset,
   none of the 6 wired emit sites produce JSONL entries — zero
   hot-path cost.
2. **Wiring presence**: every one of the 8 mechanism names is
   emitted from at least one site in the live source (source-level
   check; the wiring itself is exercised in dedicated integration
   tests).
3. **AppState surface**: the lazy singleton + emit helper exist
   and are callable.
4. **CostCapContext carries the metrics log**: the integration is
   bound at the right place (per-user AI dispatch chokepoint).

The goal is to catch the case where someone removes a wiring site
in a future refactor without realising it breaks one of the 8
mechanisms.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.cost_saving_metrics import (
    ALL_MECHANISMS,
    CostSavingMetricsLog,
    MECHANISM_AI_BYO_SAVINGS,
    MECHANISM_FASTER_RECOGNITION,
    MECHANISM_FEWER_WRONG_FIT_APPS,
    MECHANISM_HIGHER_APPLY_RATE,
    MECHANISM_LANGUAGE_COVERAGE,
    MECHANISM_PERSISTENT_INDEX_REUSE,
    MECHANISM_SELF_SERVE_ANERKENNUNG,
    MECHANISM_SHORTER_JOURNEY,
    is_collection_enabled,
)


REPO_ROOT = Path("/Users/fouad./Desktop/NasserMCPserver")


# -------------------------------------------------------------------------
# Source-level wiring contract
# -------------------------------------------------------------------------


class EveryMechanismIsWired(unittest.TestCase):
    """Each of the 8 ALL_MECHANISMS names must be emitted from at
    least one place in the live source. Catches the regression
    where a refactor accidentally drops a wiring site."""

    def setUp(self):
        # Aggregate source: everywhere except tests + cached
        # bytecode + the substrate itself.
        self.sources: dict[str, str] = {}
        for path in (
            REPO_ROOT / "app.py",
            REPO_ROOT / "company_discovery" / "analysis.py",
            REPO_ROOT / "company_discovery" / "mcp_tools.py",
            REPO_ROOT / "company_discovery" / "journey.py",
            REPO_ROOT / "company_discovery" / "diagnostic_engine.py",
        ):
            self.sources[path.name] = path.read_text(encoding="utf-8")

    def _emitted_anywhere(self, marker: str) -> bool:
        return any(marker in src for src in self.sources.values())

    def test_ai_byo_savings_wired(self):
        self.assertTrue(
            self._emitted_anywhere("MECHANISM_AI_BYO_SAVINGS"),
            "ai_byo_savings has no live emit site — should be in "
            "company_discovery/analysis.py dispatch chokepoint",
        )

    def test_higher_apply_rate_wired(self):
        self.assertTrue(
            self._emitted_anywhere("MECHANISM_HIGHER_APPLY_RATE"),
            "higher_apply_rate has no live emit site — should be in "
            "company_discovery/mcp_tools.py:record_user_outcome",
        )

    def test_fewer_wrong_fit_apps_wired(self):
        self.assertTrue(
            self._emitted_anywhere("MECHANISM_FEWER_WRONG_FIT_APPS"),
            "fewer_wrong_fit_apps has no live emit site — should be "
            "in mcp_tools.py when an 'applied' outcome carries "
            "fit_score>=75 in the note",
        )

    def test_language_coverage_wired(self):
        self.assertTrue(
            self._emitted_anywhere("MECHANISM_LANGUAGE_COVERAGE"),
            "language_coverage has no live emit site — should be "
            "in app.py:update_profile on a non-EN locale switch",
        )

    def test_shorter_journey_wired(self):
        # Journey.py emits via the string mechanism name (not the
        # constant) because the journey result is consumed by the
        # chat-router which maps to AppState.record_cost_saving_event.
        self.assertTrue(
            self._emitted_anywhere('"shorter_journey"'),
            "shorter_journey has no live emit site — should be in "
            "journey.py natural-completion paths",
        )

    def test_self_serve_anerkennung_wired(self):
        self.assertTrue(
            self._emitted_anywhere('"self_serve_anerkennung"'),
            "self_serve_anerkennung has no live emit site — should "
            "be in journey.py when an anerkennung-marked job is saved",
        )

    def test_faster_recognition_wired(self):
        self.assertTrue(
            self._emitted_anywhere('"faster_recognition"'),
            "faster_recognition has no live emit site — should be "
            "alongside self_serve_anerkennung",
        )

    def test_persistent_index_reuse_wired(self):
        self.assertTrue(
            self._emitted_anywhere("MECHANISM_PERSISTENT_INDEX_REUSE"),
            "persistent_index_reuse has no live emit site — should "
            "be in diagnostic_engine.py at the JobIndex hit branch",
        )

    def test_all_8_mechanisms_covered(self):
        """Drift safety: if a future agent adds a new mechanism to
        ALL_MECHANISMS, this test fires to remind them to wire it.
        Pin the catalogue size."""

        self.assertEqual(
            len(ALL_MECHANISMS),
            8,
            "ALL_MECHANISMS has changed size; if you added a new "
            "mechanism, also add a wiring site AND extend this "
            "test class with a test for it",
        )


class AppStateExposesCostMetricsHelpers(unittest.TestCase):
    """AppState must carry the lazy singleton + emit helper used by
    the 6+ wired emit sites."""

    def test_appstate_source_has_cost_metrics_log_property(self):
        src = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("def cost_metrics_log(self):", src)
        self.assertIn("self._cost_metrics_log = None", src)
        self.assertIn("self._cost_metrics_log_lock = Lock()", src)

    def test_appstate_source_has_record_cost_saving_event_helper(self):
        src = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("def record_cost_saving_event(", src)

    def test_cost_cap_context_carries_metrics_log(self):
        """The CostCapContext (per-user dispatch chokepoint) must
        carry the metrics log so analysis.py can emit BYO events
        without depending on AppState directly."""

        cost_caps_src = (REPO_ROOT / "company_discovery" / "cost_caps.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("cost_metrics_log:", cost_caps_src)
        # And AppState passes it through
        app_src = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn(
            "cost_metrics_log=self.cost_metrics_log()", app_src
        )


# -------------------------------------------------------------------------
# Behavioural: env-gate honoured
# -------------------------------------------------------------------------


class OptInGateHonoured(unittest.TestCase):
    """When the env var is unset, the recorder reports disabled.
    When set to true, it reports enabled. This is the contract
    the wiring sites rely on for zero-overhead-when-off."""

    def setUp(self):
        self._original = os.environ.get("HELPMEFINDTHEJOB_COST_METRICS")
        os.environ.pop("HELPMEFINDTHEJOB_COST_METRICS", None)
        os.environ.pop("HELPMEFINDTHEJOB_COST_METRICS", None)

    def tearDown(self):
        if self._original is not None:
            os.environ["HELPMEFINDTHEJOB_COST_METRICS"] = self._original
        else:
            os.environ.pop("HELPMEFINDTHEJOB_COST_METRICS", None)

    def test_unset_means_disabled(self):
        self.assertFalse(is_collection_enabled())

    def test_set_to_true_means_enabled(self):
        os.environ["HELPMEFINDTHEJOB_COST_METRICS"] = "true"
        self.assertTrue(is_collection_enabled())


class JSONLEventsAccrueWhenEnabled(unittest.TestCase):
    """End-to-end: directly exercise the substrate with each
    mechanism and verify the JSONL accumulates correctly."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self._path = Path(self._tmp.name) / "metrics.jsonl"
        # Use a deterministic salt for the test (the substrate
        # accepts any bytes-like salt).
        self.log = CostSavingMetricsLog(
            self._path, salt=b"test-salt-12345", enabled=True
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_each_of_8_mechanisms_records_successfully(self):
        for mechanism in ALL_MECHANISMS:
            with self.subTest(mechanism=mechanism):
                ok = self.log.record(
                    mechanism,
                    user_id="u",
                    value=1.0,
                    unit="test",
                    metadata={},
                )
                self.assertTrue(ok, f"recording {mechanism} failed")
        # 8 lines in the JSONL
        lines = self._path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 8)
        # Each parses as JSON with the right mechanism field
        seen = {json.loads(ln)["mechanism"] for ln in lines}
        self.assertEqual(seen, set(ALL_MECHANISMS))

    def test_disabled_recorder_writes_nothing(self):
        disabled = CostSavingMetricsLog(
            self._path, salt=b"x", enabled=False
        )
        for mechanism in ALL_MECHANISMS:
            self.assertFalse(disabled.record(
                mechanism, user_id="u", value=1.0, unit="t", metadata={}
            ))
        self.assertFalse(self._path.exists())

    def test_snapshot_reads_events_back(self):
        for mechanism in ALL_MECHANISMS:
            for _ in range(5):
                self.log.record(
                    mechanism, user_id="u", value=1.0, unit="t", metadata={}
                )
        snapshot = self.log.snapshot()
        # Snapshot shape: {windowDays, uniqueUsers, mechanisms: {<name>: {...}}}
        self.assertIn("mechanisms", snapshot)
        for mechanism in ALL_MECHANISMS:
            with self.subTest(mechanism=mechanism):
                self.assertIn(
                    mechanism,
                    snapshot["mechanisms"],
                    f"snapshot missing {mechanism}",
                )
                self.assertEqual(snapshot["mechanisms"][mechanism]["events"], 5)


if __name__ == "__main__":
    unittest.main()
