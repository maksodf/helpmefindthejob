# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #69 — Cost-saving doctrine measurement substrate
contract tests."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.cost_saving_metrics import (
    ALL_MECHANISMS,
    MECHANISM_AI_BYO_SAVINGS,
    MECHANISM_FEWER_WRONG_FIT_APPS,
    MECHANISM_PERSISTENT_INDEX_REUSE,
    MECHANISM_SHORTER_JOURNEY,
    PLAUSIBLE_EVENT_THRESHOLD,
    PROVEN_EVENT_THRESHOLD,
    CostSavingMetricsLog,
    MetricsEvent,
    _env_enabled,
    _hash_user_id,
)


def _make_log(enabled: bool = True) -> tuple[CostSavingMetricsLog, TemporaryDirectory]:
    tmp = TemporaryDirectory()
    log = CostSavingMetricsLog(
        path=Path(tmp.name) / "cost_metrics.jsonl",
        salt=b"test-salt-for-csm-69" + b"0" * 32,
        enabled=enabled,
    )
    return log, tmp


class OptInGate(unittest.TestCase):
    def test_disabled_by_default_via_constructor(self) -> None:
        log, tmp = _make_log(enabled=False)
        self.addCleanup(tmp.cleanup)
        wrote = log.record(
            MECHANISM_SHORTER_JOURNEY,
            value=12.5,
            unit="minutes_saved",
            user_id="u-1",
        )
        self.assertFalse(wrote)
        # File must not be created when disabled
        self.assertFalse(log.path.exists())

    def test_enabled_writes_to_jsonl(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        wrote = log.record(
            MECHANISM_SHORTER_JOURNEY,
            value=12.5,
            unit="minutes_saved",
            user_id="u-1",
        )
        self.assertTrue(wrote)
        self.assertTrue(log.path.exists())
        # File contents are JSONL — one event per line
        lines = log.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)


class UserHashing(unittest.TestCase):
    def test_same_user_id_same_salt_same_hash(self) -> None:
        salt = b"test-salt-aaa-bbb-ccc-ddd-eee-fff-ggg-hhh-iii"
        self.assertEqual(_hash_user_id("alice", salt), _hash_user_id("alice", salt))

    def test_different_user_id_different_hash(self) -> None:
        salt = b"test-salt-aaa-bbb-ccc-ddd-eee-fff-ggg-hhh-iii"
        self.assertNotEqual(_hash_user_id("alice", salt), _hash_user_id("bob", salt))

    def test_different_salt_different_hash(self) -> None:
        a = _hash_user_id("alice", b"salt-A" + b"0" * 32)
        b = _hash_user_id("alice", b"salt-B" + b"0" * 32)
        self.assertNotEqual(a, b)

    def test_hash_length_is_16_hex_chars(self) -> None:
        h = _hash_user_id("alice", b"salt-X" + b"0" * 32)
        self.assertEqual(len(h), 16)
        int(h, 16)  # must parse as hex


class UnknownMechanismRejected(unittest.TestCase):
    def test_record_raises_on_unknown_mechanism(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        with self.assertRaises(ValueError) as cm:
            log.record(
                "made_up_mechanism",
                value=1.0,
                unit="x",
                user_id="u-1",
            )
        self.assertIn("unknown_mechanism", str(cm.exception))

    def test_all_mechanisms_constant_has_eight_entries(self) -> None:
        """The doctrine doc lists 8 mechanisms — drift guard."""
        self.assertEqual(len(ALL_MECHANISMS), 8)
        self.assertEqual(len(set(ALL_MECHANISMS)), 8)  # no duplicates


class JsonlRoundtrip(unittest.TestCase):
    def test_event_jsonl_serialisation(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        log.record(
            MECHANISM_AI_BYO_SAVINGS,
            value=0.12,
            unit="eur_saved",
            user_id="u-1",
            metadata={"providerId": "ollama"},
        )
        events = list(log.replay())
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e.mechanism, MECHANISM_AI_BYO_SAVINGS)
        self.assertEqual(e.value, 0.12)
        self.assertEqual(e.unit, "eur_saved")
        self.assertEqual(e.metadata.get("providerId"), "ollama")

    def test_malformed_line_is_skipped_not_crashed(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        log.record(
            MECHANISM_SHORTER_JOURNEY,
            value=5,
            unit="minutes_saved",
            user_id="u-1",
        )
        with log.path.open("a", encoding="utf-8") as fh:
            fh.write("not json at all\n")
        events = list(log.replay())
        # Good event still counted; bad line skipped
        self.assertEqual(len(events), 1)


class SnapshotConfidence(unittest.TestCase):
    def test_zero_events_is_aspirational(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        snap = log.snapshot()
        for mechanism in ALL_MECHANISMS:
            self.assertEqual(snap["mechanisms"][mechanism]["confidence"], "aspirational")

    def test_threshold_crossings(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        # 1 event → aspirational
        log.record(
            MECHANISM_SHORTER_JOURNEY,
            value=1.0,
            unit="minutes_saved",
            user_id="u-1",
        )
        snap = log.snapshot()
        self.assertEqual(
            snap["mechanisms"][MECHANISM_SHORTER_JOURNEY]["confidence"], "aspirational"
        )
        # Top up to PLAUSIBLE threshold
        for i in range(PLAUSIBLE_EVENT_THRESHOLD - 1):
            log.record(
                MECHANISM_SHORTER_JOURNEY,
                value=1.0,
                unit="minutes_saved",
                user_id=f"u-{i}",
            )
        snap = log.snapshot()
        self.assertEqual(
            snap["mechanisms"][MECHANISM_SHORTER_JOURNEY]["confidence"], "plausible"
        )
        # Top up to PROVEN threshold
        for i in range(PROVEN_EVENT_THRESHOLD - PLAUSIBLE_EVENT_THRESHOLD):
            log.record(
                MECHANISM_SHORTER_JOURNEY,
                value=1.0,
                unit="minutes_saved",
                user_id=f"u-p-{i}",
            )
        snap = log.snapshot()
        self.assertEqual(
            snap["mechanisms"][MECHANISM_SHORTER_JOURNEY]["confidence"], "proven"
        )

    def test_snapshot_counts_distinct_users(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        for uid in ("alice", "bob", "carol", "alice", "bob"):
            log.record(
                MECHANISM_PERSISTENT_INDEX_REUSE,
                value=1.0,
                unit="cache_hits",
                user_id=uid,
            )
        snap = log.snapshot()
        # 5 events, 3 distinct users
        self.assertEqual(snap["mechanisms"][MECHANISM_PERSISTENT_INDEX_REUSE]["events"], 5)
        self.assertEqual(snap["mechanisms"][MECHANISM_PERSISTENT_INDEX_REUSE]["users"], 3)
        self.assertEqual(snap["uniqueUsers"], 3)

    def test_snapshot_records_unit(self) -> None:
        log, tmp = _make_log(enabled=True)
        self.addCleanup(tmp.cleanup)
        log.record(
            MECHANISM_FEWER_WRONG_FIT_APPS,
            value=2.0,
            unit="apps_skipped",
            user_id="u-1",
        )
        snap = log.snapshot()
        self.assertEqual(
            snap["mechanisms"][MECHANISM_FEWER_WRONG_FIT_APPS]["unit"], "apps_skipped"
        )


class EnvOptIn(unittest.TestCase):
    def test_env_gate_off_when_unset(self) -> None:
        import os

        # Save / restore — the test harness shouldn't have these set
        original = {k: os.environ.pop(k, None) for k in (
            "HELPMEFINDTHEJOB_COST_METRICS",
            "HELPMEFINDTHEJOB_COST_METRICS",
        )}
        try:
            self.assertFalse(_env_enabled())
        finally:
            for k, v in original.items():
                if v is not None:
                    os.environ[k] = v

    def test_env_gate_on_with_truthy_value(self) -> None:
        import os

        os.environ["HELPMEFINDTHEJOB_COST_METRICS"] = "true"
        try:
            self.assertTrue(_env_enabled())
        finally:
            os.environ.pop("HELPMEFINDTHEJOB_COST_METRICS", None)

    def test_env_gate_legacy_alias(self) -> None:
        import os

        os.environ.pop("HELPMEFINDTHEJOB_COST_METRICS", None)
        os.environ["HELPMEFINDTHEJOB_COST_METRICS"] = "1"
        try:
            self.assertTrue(_env_enabled())
        finally:
            os.environ.pop("HELPMEFINDTHEJOB_COST_METRICS", None)


if __name__ == "__main__":
    unittest.main()
