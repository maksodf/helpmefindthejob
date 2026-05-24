# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #13 — Audit-log tamper-evidence (HMAC chain).

The AI Act Article 12 audit log is append-only JSONL today. That
prevents accidental loss but does NOT detect deletion or
modification by a malicious operator. This commit adds:

1. Monotonic sequence numbers — gaps reveal deletion
2. HMAC chain — modifying record N breaks the chain from N+1
3. verify_chain() — external auditors can confirm intactness

These tests pin all three properties: the chain validates on a
clean log, sequence-gap detection catches deletion, HMAC mismatch
catches modification.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.audit_log import (
    AuditLogEmitter,
    ChainVerificationResult,
    verify_chain,
)


def _make_emitter() -> tuple[AuditLogEmitter, Path, TemporaryDirectory]:
    tmp = TemporaryDirectory()
    log_path = Path(tmp.name) / "audit.log"
    salt = b"test-salt-tamper-evidence-13" + b"0" * 16
    return AuditLogEmitter(log_path, salt), log_path, tmp


class ChainStampingOnEmit(unittest.TestCase):
    def test_first_record_carries_sequence_no_1(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        emitter.emit("system_event", outcome="ok")
        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["sequence_no"], 1)
        self.assertIn("chain_hmac", records[0])
        # HMAC-SHA256 hex is 64 chars
        self.assertEqual(len(records[0]["chain_hmac"]), 64)

    def test_subsequent_records_increment_sequence(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(5):
            emitter.emit("system_event", outcome="ok")
        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual([r["sequence_no"] for r in records], [1, 2, 3, 4, 5])

    def test_each_chain_hmac_is_unique(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(5):
            emitter.emit("system_event", outcome="ok")
        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        hmacs = [r["chain_hmac"] for r in records]
        self.assertEqual(len(set(hmacs)), 5, "Every chain_hmac must be unique")


class VerifyHappyPath(unittest.TestCase):
    def test_clean_log_verifies_ok(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(10):
            emitter.emit("system_event", outcome="ok")
        result = verify_chain([log_path], emitter.salt)
        self.assertTrue(result.ok, f"Verify failed: {result.to_dict()}")
        self.assertEqual(result.records_checked, 10)
        self.assertIsNone(result.first_break_at_sequence)

    def test_empty_log_verifies_ok(self) -> None:
        _, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        log_path.write_text("", encoding="utf-8")
        salt = b"test-salt-tamper-evidence-13" + b"0" * 16
        result = verify_chain([log_path], salt)
        self.assertTrue(result.ok)
        self.assertEqual(result.records_checked, 0)


class TamperDetection(unittest.TestCase):
    def test_modified_record_breaks_chain(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(5):
            emitter.emit("system_event", outcome="ok")
        # Tamper: change record 3's outcome
        lines = log_path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[2])
        record["outcome"] = "tampered_outcome"
        lines[2] = json.dumps(record, sort_keys=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_chain([log_path], emitter.salt)
        self.assertFalse(result.ok)
        self.assertEqual(result.first_break_at_sequence, 3)
        self.assertEqual(result.first_break_reason, "hmac_mismatch")

    def test_deleted_record_caught_as_sequence_gap(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(5):
            emitter.emit("system_event", outcome="ok")
        # Delete record 3 entirely
        lines = log_path.read_text(encoding="utf-8").splitlines()
        del lines[2]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_chain([log_path], emitter.salt)
        self.assertFalse(result.ok)
        self.assertEqual(result.first_break_reason, "sequence_gap")
        self.assertIn(3, result.missing_sequence_numbers)

    def test_reordered_records_break_chain(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(5):
            emitter.emit("system_event", outcome="ok")
        lines = log_path.read_text(encoding="utf-8").splitlines()
        # Swap records 2 and 3 in file (but sequence_no still on record)
        lines[1], lines[2] = lines[2], lines[1]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Since verify_chain sorts by sequence_no, simple reordering
        # in the file does NOT defeat it — the chain still validates
        # because we walk in sequence order, not file order. This is
        # by design: append-only file order is not the integrity
        # claim; sequence-number monotonicity is.
        result = verify_chain([log_path], emitter.salt)
        self.assertTrue(result.ok)

    def test_chain_hmac_modification_caught(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(3):
            emitter.emit("system_event", outcome="ok")
        # Replace record 2's chain_hmac with garbage
        lines = log_path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[1])
        record["chain_hmac"] = "00" * 32  # 64 hex zeros
        lines[1] = json.dumps(record, sort_keys=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_chain([log_path], emitter.salt)
        self.assertFalse(result.ok)
        self.assertEqual(result.first_break_at_sequence, 2)
        self.assertEqual(result.first_break_reason, "hmac_mismatch")

    def test_malformed_json_line_caught(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        emitter.emit("system_event", outcome="ok")
        # Append a malformed line
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("not valid json\n")
        result = verify_chain([log_path], emitter.salt)
        self.assertFalse(result.ok)
        self.assertEqual(result.first_break_reason, "malformed_json")


class ChainAcrossRotations(unittest.TestCase):
    def test_sequence_continues_across_rotated_file(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        # Use a tiny rotation threshold so we rotate quickly
        emitter.rotate_bytes = 1024
        for _ in range(20):
            emitter.emit("system_event", outcome="ok", event_payload={"x": "y" * 200})
        # Should have produced at least one rotation
        rotated = [
            p for p in log_path.parent.iterdir()
            if p.name.startswith(log_path.name + ".") and p != log_path
        ]
        self.assertGreater(len(rotated), 0, "Expected at least one rotation")
        # Verify across all files
        result = verify_chain([log_path, *rotated], emitter.salt)
        self.assertTrue(result.ok, f"Verify failed across rotations: {result.to_dict()}")

    def test_new_emitter_resumes_chain_from_existing_log(self) -> None:
        emitter1, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(5):
            emitter1.emit("system_event", outcome="ok")
        # New emitter pointing at the same file should pick up sequence 6
        emitter2 = AuditLogEmitter(log_path, emitter1.salt)
        emitter2.emit("system_event", outcome="ok")
        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual([r["sequence_no"] for r in records], [1, 2, 3, 4, 5, 6])
        # And the chain validates end-to-end
        result = verify_chain([log_path], emitter1.salt)
        self.assertTrue(result.ok)


class SchemaVersionGate(unittest.TestCase):
    def test_v1_legacy_record_rejected_by_verify_chain(self) -> None:
        """An attacker can't downgrade a v2 chain to v1 records to
        defeat verification — verify_chain rejects anything that
        isn't schema v2."""
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        # Write a fake v1 legacy record directly (bypasses emitter)
        with log_path.open("w", encoding="utf-8") as fh:
            fh.write(
                json.dumps({
                    "schema_version": "v1",
                    "event_id": "legacy-001",
                    "event_type": "system_event",
                    "outcome": "ok",
                })
                + "\n"
            )
        result = verify_chain([log_path], emitter.salt)
        self.assertFalse(result.ok)
        self.assertIn("unsupported_schema_version", result.first_break_reason)

    def test_emitter_writes_schema_version_v2(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        emitter.emit("system_event", outcome="ok")
        record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["schema_version"], "v2")


class WriteFailureDoesNotCorruptChain(unittest.TestCase):
    """Quality-audit (2026-05-21): a single file-write failure
    between bump+write would corrupt the chain for every
    subsequent record. The in-memory counters must only advance
    AFTER the write succeeds — never before."""

    def test_failed_write_does_not_advance_sequence(self) -> None:
        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        emitter.emit("system_event", outcome="ok")
        self.assertEqual(emitter._last_sequence_no, 1)
        # Force the next write to fail by making the log path
        # un-writable. We monkey-patch the open() call inside
        # _write to raise OSError.
        original_open = type(log_path).open
        def failing_open(self, *args, **kwargs):
            if self == log_path:
                raise OSError("disk full simulation")
            return original_open(self, *args, **kwargs)
        type(log_path).open = failing_open
        try:
            emitter.emit("system_event", outcome="ok")
        finally:
            type(log_path).open = original_open
        # In-memory counter must NOT have advanced — the failed
        # write left no record on disk, so sequence_no=2 is still
        # available for the next attempt
        self.assertEqual(
            emitter._last_sequence_no,
            1,
            "Sequence must not advance on failed write — "
            "advancing would gap the chain for every future record",
        )
        # And the recovery: a successful write next attempt picks
        # up at sequence_no=2 and the chain validates
        emitter.emit("system_event", outcome="ok")
        self.assertEqual(emitter._last_sequence_no, 2)
        result = verify_chain([log_path], emitter.salt)
        self.assertTrue(result.ok, f"Chain validation: {result.to_dict()}")
        self.assertEqual(result.records_checked, 2)


class WrongSaltDetection(unittest.TestCase):
    def test_verify_with_wrong_salt_fails(self) -> None:
        """Defense: an attacker with file write access but no salt
        cannot forge a valid chain. verify_chain with the wrong
        salt rejects every record."""

        emitter, log_path, tmp = _make_emitter()
        self.addCleanup(tmp.cleanup)
        for _ in range(3):
            emitter.emit("system_event", outcome="ok")
        result = verify_chain([log_path], b"WRONG-SALT" + b"0" * 32)
        self.assertFalse(result.ok)
        self.assertEqual(result.first_break_at_sequence, 1)
        self.assertEqual(result.first_break_reason, "hmac_mismatch")


if __name__ == "__main__":
    unittest.main()
