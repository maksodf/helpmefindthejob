# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Tests for the AI Act Article 12 audit-log emitter.

Coverage:

- Direct ``AuditLogEmitter.emit`` writes valid JSONL with the schema-v1
  envelope fields.
- Hash determinism: same value + same salt produces the same opaque ID.
- Hash isolation: different salt produces different opaque ID for the
  same value.
- Plaintext-PII opt-in: when ``plaintext_pii=True`` the fields hold the
  raw value.
- Rotation: when the log file exceeds ``rotate_bytes`` the file is
  renamed with a timestamp suffix and a new file is started.
- Caller-context propagation: ``set_caller_context`` values are read
  by subsequent ``emit`` calls; explicit ``emit(...)`` kwargs override
  the context.
- ``emit_ai_invocation`` convenience helper produces an
  ``event_type="ai_invocation"`` record with the expected payload.
- ``emit_mcp_tool_invocation`` produces an ``event_type="mcp_tool_invocation"``
  record with the expected payload.
- ``emit_system_event`` produces an ``event_type="system_event"`` record.
- Integration via the MCP server: spawning ``handle_request`` with a
  ``tools/call`` dispatch causes one ``mcp_tool_invocation`` record to
  be written.
- Integration via the analysis pipeline: calling
  ``_dispatch_provider`` (with the manual-handoff short-circuit) causes
  one ``ai_invocation`` record to be written.

The tests do not require any external AI provider; they exercise the
short-circuit paths and direct emitter calls.
"""

from __future__ import annotations

import contextvars
import json
import tempfile
import unittest
from pathlib import Path

from company_discovery import audit_log
from company_discovery.audit_log import (
    AuditLogEmitter,
    emit_ai_invocation,
    emit_mcp_tool_invocation,
    emit_system_event,
    reset_caller_context,
    reset_default_emitter,
    set_caller_context,
    set_default_emitter,
)


def _read_log_lines(log_path: Path) -> list[dict]:
    """Read all JSONL records from a log file (and its rotated siblings)."""
    records: list[dict] = []
    if log_path.exists():
        with log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    for sibling in sorted(log_path.parent.glob(log_path.name + ".*")):
        with sibling.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


class AuditLogEmitterTests(unittest.TestCase):
    """Direct unit tests of the AuditLogEmitter class."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = Path(self.tmp.name) / "ai_act_audit.log"
        self.salt = b"\x01" * 32
        self.emitter = AuditLogEmitter(
            log_path=self.log_path,
            salt=self.salt,
            plaintext_pii=False,
            rotate_bytes=64 * 1024 * 1024,
        )

    def test_emit_writes_jsonl_with_schema_v1_envelope(self) -> None:
        self.emitter.emit(
            "ai_invocation",
            outcome="ok",
            duration_ms=42,
            user_opaque_id="user-1",
            session_opaque_id="sess-1",
            caller="web",
            ai_provider="openai",
            tokens_in=120,
            tokens_out=80,
            event_payload={"purpose": "fit_score"},
        )
        records = _read_log_lines(self.log_path)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["schema_version"], "v1")
        self.assertEqual(rec["event_type"], "ai_invocation")
        self.assertEqual(rec["outcome"], "ok")
        self.assertEqual(rec["duration_ms"], 42)
        self.assertEqual(rec["caller"], "web")
        self.assertEqual(rec["ai_provider"], "openai")
        self.assertEqual(rec["tokens_in"], 120)
        self.assertEqual(rec["tokens_out"], 80)
        self.assertEqual(rec["event_payload"], {"purpose": "fit_score"})
        self.assertEqual(len(rec["user_opaque_id"]), 64)  # SHA-256 hex
        self.assertEqual(len(rec["session_opaque_id"]), 64)
        self.assertIn("event_id", rec)
        self.assertIn("timestamp", rec)

    def test_hash_is_deterministic_with_same_salt(self) -> None:
        h1 = self.emitter.hash_id("user-42")
        h2 = self.emitter.hash_id("user-42")
        self.assertEqual(h1, h2)

    def test_hash_differs_with_different_salt(self) -> None:
        other = AuditLogEmitter(log_path=self.log_path, salt=b"\x02" * 32)
        self.assertNotEqual(self.emitter.hash_id("user-42"), other.hash_id("user-42"))

    def test_hash_id_returns_none_for_none(self) -> None:
        self.assertIsNone(self.emitter.hash_id(None))

    def test_plaintext_pii_opt_in_disables_hashing(self) -> None:
        plain = AuditLogEmitter(
            log_path=self.log_path, salt=self.salt, plaintext_pii=True
        )
        self.assertEqual(plain.hash_id("user-42"), "user-42")

    def test_short_hash_is_16_hex_chars(self) -> None:
        h = self.emitter.short_hash("the-prompt-value")
        self.assertIsNotNone(h)
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_rotation_when_exceeds_threshold(self) -> None:
        # Build a tight-rotation emitter so we can trigger rotation
        # without writing megabytes.
        small_emitter = AuditLogEmitter(
            log_path=self.log_path, salt=self.salt, rotate_bytes=128
        )
        for i in range(20):
            small_emitter.emit(
                "system_event",
                outcome="ok",
                event_payload={"system_event_kind": "ping", "i": i},
            )
        # At least one rotated sibling should exist now.
        rotated = list(self.log_path.parent.glob(self.log_path.name + ".*"))
        self.assertGreaterEqual(len(rotated), 1)
        # All records (live + rotated) should still be readable and
        # JSON-valid.
        all_records = _read_log_lines(self.log_path)
        self.assertEqual(len(all_records), 20)

    def test_error_outcome_includes_error_class_field(self) -> None:
        self.emitter.emit(
            "ai_invocation",
            outcome="error",
            duration_ms=15,
            error_class="ConnectionTimeout",
        )
        records = _read_log_lines(self.log_path)
        self.assertEqual(records[-1]["error_class"], "ConnectionTimeout")


class CallerContextTests(unittest.TestCase):
    """Caller-context propagation via contextvars."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = Path(self.tmp.name) / "ai_act_audit.log"
        self.emitter = AuditLogEmitter(log_path=self.log_path, salt=b"\x03" * 32)

    def test_set_caller_context_propagates_to_emit(self) -> None:
        token = set_caller_context(
            user_id="user-99",
            session_id="sess-99",
            caller="web",
            journey_phase="phase_3_scope",
        )
        try:
            self.emitter.emit("ai_invocation", outcome="ok")
        finally:
            reset_caller_context(token)
        records = _read_log_lines(self.log_path)
        rec = records[-1]
        self.assertIsNotNone(rec["user_opaque_id"])
        self.assertIsNotNone(rec["session_opaque_id"])
        self.assertEqual(rec["caller"], "web")
        self.assertEqual(rec.get("journey_phase"), "phase_3_scope")

    def test_explicit_emit_kwargs_override_context(self) -> None:
        token = set_caller_context(user_id="user-99", caller="web")
        try:
            self.emitter.emit(
                "ai_invocation",
                outcome="ok",
                caller="mcp",  # explicit override
            )
        finally:
            reset_caller_context(token)
        records = _read_log_lines(self.log_path)
        # The caller field should reflect the explicit override
        self.assertEqual(records[-1]["caller"], "mcp")

    def test_context_isolation_across_contextvars_runs(self) -> None:
        """Context is correctly scoped: when reset, prior emit reads
        an empty context."""

        # Establish a context, emit (record 1), reset.
        token = set_caller_context(user_id="user-A", caller="web")
        self.emitter.emit("ai_invocation", outcome="ok")
        reset_caller_context(token)

        # No context now; emit (record 2) reads empty.
        self.emitter.emit("ai_invocation", outcome="ok")

        records = _read_log_lines(self.log_path)
        # Record 1 had user-A → non-None hashed id
        # Record 2 had no context → None
        self.assertIsNotNone(records[0]["user_opaque_id"])
        self.assertIsNone(records[1]["user_opaque_id"])


class ConvenienceWrappersTests(unittest.TestCase):
    """Tests for the emit_ai_invocation / emit_mcp_tool_invocation /
    emit_system_event helpers."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = Path(self.tmp.name) / "ai_act_audit.log"
        self.emitter = AuditLogEmitter(log_path=self.log_path, salt=b"\x04" * 32)

    def test_emit_ai_invocation_produces_event_payload(self) -> None:
        emit_ai_invocation(
            purpose="fit_score",
            ai_provider="openai",
            prompt_template_id="abcd1234",
            duration_ms=123,
            outcome="ok",
            tokens_in=200,
            tokens_out=150,
            prompt_hash="0123456789abcdef",
            response_hash="fedcba9876543210",
            score_adjustment_factor=0.05,
            emitter=self.emitter,
        )
        rec = _read_log_lines(self.log_path)[-1]
        self.assertEqual(rec["event_type"], "ai_invocation")
        self.assertEqual(rec["event_payload"]["purpose"], "fit_score")
        self.assertEqual(rec["event_payload"]["prompt_hash"], "0123456789abcdef")
        self.assertEqual(rec["event_payload"]["response_hash"], "fedcba9876543210")
        self.assertAlmostEqual(
            rec["event_payload"]["score_adjustment_factor"], 0.05
        )
        self.assertEqual(rec["ai_provider"], "openai")
        self.assertEqual(rec["prompt_template_id"], "abcd1234")
        self.assertEqual(rec["tokens_in"], 200)
        self.assertEqual(rec["tokens_out"], 150)

    def test_emit_mcp_tool_invocation_records_tool_name(self) -> None:
        emit_mcp_tool_invocation(
            tool_name="find_company_career_page",
            arguments_hash="aaaa1111bbbb2222",
            response_size_bytes=1024,
            duration_ms=8,
            outcome="ok",
            emitter=self.emitter,
        )
        rec = _read_log_lines(self.log_path)[-1]
        self.assertEqual(rec["event_type"], "mcp_tool_invocation")
        self.assertEqual(rec["event_payload"]["tool_name"], "find_company_career_page")
        self.assertEqual(rec["event_payload"]["arguments_hash"], "aaaa1111bbbb2222")
        self.assertEqual(rec["event_payload"]["response_size_bytes"], 1024)
        self.assertEqual(rec["caller"], "mcp")

    def test_emit_system_event_records_kind(self) -> None:
        emit_system_event(
            system_event_kind="kill_switch_activated",
            details={"reason": "manual_operator_action"},
            emitter=self.emitter,
        )
        rec = _read_log_lines(self.log_path)[-1]
        self.assertEqual(rec["event_type"], "system_event")
        self.assertEqual(
            rec["event_payload"]["system_event_kind"], "kill_switch_activated"
        )
        self.assertEqual(rec["event_payload"]["details"]["reason"], "manual_operator_action")


class MCPServerIntegrationTests(unittest.TestCase):
    """Integration test: an in-process call to ``handle_request`` for a
    ``tools/call`` dispatch emits one ``mcp_tool_invocation`` record."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = Path(self.tmp.name) / "ai_act_audit.log"
        self.test_emitter = AuditLogEmitter(
            log_path=self.log_path, salt=b"\x05" * 32
        )
        # Install the test emitter as the process-wide default for the
        # duration of this test, then reset.
        set_default_emitter(self.test_emitter)
        self.addCleanup(reset_default_emitter)

    def _run_in_isolated_context(self, fn) -> None:
        """Run ``fn`` in a fresh contextvars.Context so the test does
        not leak caller-context state into other tests."""
        ctx = contextvars.copy_context()
        ctx.run(fn)

    def test_tools_call_emits_one_mcp_tool_invocation(self) -> None:
        # Use a tool name that is NOT in TOOL_SCHEMAS so the inputSchema
        # validator returns None (vacuously satisfied) and the dispatch
        # path falls through to the unknown_tool branch — the
        # deterministic path that exercises the audit-log emit without
        # depending on a real tool implementation or schema-required
        # arguments.
        from mcp_server import handle_request

        class _FakeTools:
            pass  # no attribute named "this_tool_does_not_exist"

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "this_tool_does_not_exist",
                "arguments": {},
            },
        }

        def _run() -> None:
            response = handle_request(message, _FakeTools())  # type: ignore[arg-type]
            self.assertIsNotNone(response)

        self._run_in_isolated_context(_run)

        records = _read_log_lines(self.log_path)
        tool_records = [r for r in records if r["event_type"] == "mcp_tool_invocation"]
        self.assertEqual(len(tool_records), 1)
        rec = tool_records[0]
        self.assertEqual(rec["event_payload"]["tool_name"], "this_tool_does_not_exist")
        self.assertEqual(rec["caller"], "mcp")
        self.assertEqual(rec["outcome"], "declined")
        self.assertEqual(rec["error_class"], "UnknownTool")


class AnalysisIntegrationTests(unittest.TestCase):
    """Integration test: a manual-handoff dispatch through
    ``_dispatch_provider`` emits one ``ai_invocation`` record."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = Path(self.tmp.name) / "ai_act_audit.log"
        self.test_emitter = AuditLogEmitter(
            log_path=self.log_path, salt=b"\x06" * 32
        )
        set_default_emitter(self.test_emitter)
        self.addCleanup(reset_default_emitter)

    def test_dispatch_provider_emits_ai_invocation_for_manual_handoff(self) -> None:
        from company_discovery.ai_providers import AIProviderConfig
        from company_discovery.analysis import _dispatch_provider

        manual_provider = AIProviderConfig(
            provider_id="manual",
            invocation_mode="manual",
            model="",
            credential_reference="",
            base_url="",
            command="",
            notes="manual",
        )

        result = _dispatch_provider(
            "fake prompt body",
            manual_provider,
            "",
            purpose="fit_score",
        )
        self.assertEqual(result.status, "handoff_required")

        records = _read_log_lines(self.log_path)
        ai_records = [r for r in records if r["event_type"] == "ai_invocation"]
        self.assertEqual(len(ai_records), 1)
        rec = ai_records[0]
        self.assertEqual(rec["event_payload"]["purpose"], "fit_score")
        # Manual-handoff status maps to outcome="declined"
        self.assertEqual(rec["outcome"], "declined")
        # The provider id is "manual"
        self.assertEqual(rec["ai_provider"], "manual")
        # The prompt_template_id is a short hash; non-empty
        self.assertIsNotNone(rec.get("prompt_template_id"))
        self.assertEqual(len(rec["prompt_template_id"]), 8)


class AuditLogTailHelperTests(unittest.TestCase):
    """Tests for the ``_read_ai_act_audit_tail`` helper in app.py used by
    the ``/api/admin/oversight/queue`` endpoint."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = Path(self.tmp.name) / "ai_act_audit.log"
        self.emitter = AuditLogEmitter(log_path=self.log_path, salt=b"\x07" * 32)

    def _write_record(self, event_type: str, timestamp: str, **extra) -> None:
        """Write a record with a chosen timestamp so we can verify
        ordering deterministically."""
        record = {
            "schema_version": "v1",
            "event_id": "id-" + timestamp,
            "event_type": event_type,
            "timestamp": timestamp,
            "user_opaque_id": None,
            "session_opaque_id": None,
            "caller": "test",
            "duration_ms": 0,
            "outcome": "ok",
            **extra,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            json.dump(record, handle, sort_keys=True, ensure_ascii=False)
            handle.write("\n")

    def test_tail_returns_most_recent_first(self) -> None:
        from app import _read_ai_act_audit_tail

        self._write_record("system_event", "2026-05-18T12:00:00.000000Z")
        self._write_record("ai_invocation", "2026-05-18T12:00:01.000000Z")
        self._write_record("mcp_tool_invocation", "2026-05-18T12:00:02.000000Z")
        tail = _read_ai_act_audit_tail(self.log_path, 10, None)
        self.assertEqual(len(tail), 3)
        # Most recent timestamp first
        self.assertEqual(tail[0]["timestamp"], "2026-05-18T12:00:02.000000Z")
        self.assertEqual(tail[2]["timestamp"], "2026-05-18T12:00:00.000000Z")

    def test_tail_respects_limit(self) -> None:
        from app import _read_ai_act_audit_tail

        for i in range(20):
            ts = f"2026-05-18T12:00:{i:02d}.000000Z"
            self._write_record("ai_invocation", ts)
        tail = _read_ai_act_audit_tail(self.log_path, 5, None)
        self.assertEqual(len(tail), 5)

    def test_tail_filters_by_event_type(self) -> None:
        from app import _read_ai_act_audit_tail

        self._write_record("ai_invocation", "2026-05-18T12:00:00.000000Z")
        self._write_record("mcp_tool_invocation", "2026-05-18T12:00:01.000000Z")
        self._write_record("ai_invocation", "2026-05-18T12:00:02.000000Z")
        ai_only = _read_ai_act_audit_tail(self.log_path, 10, "ai_invocation")
        self.assertEqual(len(ai_only), 2)
        for rec in ai_only:
            self.assertEqual(rec["event_type"], "ai_invocation")

    def test_tail_returns_empty_when_log_missing(self) -> None:
        from app import _read_ai_act_audit_tail

        nonexistent = Path(self.tmp.name) / "no-such-log.log"
        tail = _read_ai_act_audit_tail(nonexistent, 10, None)
        self.assertEqual(tail, [])


if __name__ == "__main__":
    unittest.main()
