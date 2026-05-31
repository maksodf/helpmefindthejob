# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 6 — typed specialist contracts + the deterministic planner.

Proves the gate from docs/agent-architecture.md §2:
- every specialist contract validates a good payload and rejects a bad one;
- the planner's goal → plan decomposition is deterministic + canonically ordered
  (the no-AI fallback), with no network / AI;
- a canonical goal replays as a fixed golden trace whose per-step trust receipts
  land in the Article-12 HMAC audit chain (verify_chain passes) and are
  anchorable (Phase-5a verify_anchor passes);
- a contract violation or missing handler is caught, recorded, AND receipted —
  never allowed to corrupt downstream state silently.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from civic_agents import (
    CANONICAL_ORDER,
    CONTRACTS,
    ContractViolation,
    Goal,
    decompose,
    get_contract,
    run,
)
from company_discovery.audit_anchor import compute_anchor, verify_anchor
from company_discovery.audit_log import AuditLogEmitter, verify_chain

_SALT = b"agents-planner-test-salt-00000000"


def _mock_handlers() -> dict:
    """Contract-valid output for each specialist (no network, no AI)."""
    return {
        "cv_agent": lambda p: {"cv_text": "Lebenslauf …", "cv_sections": {"summary": "…"}},
        "search_agent": lambda p: {"discovered_jobs": [{"title": "Krankenschwester"}]},
        "anerkennung_agent": lambda p: {
            "recognition_steps": [{"step": "submit-diploma"}],
            "missing_documents": ["Diplom-Übersetzung"],
        },
        "letter_agent": lambda p: {"letter_text": "Sehr geehrte Damen und Herren …"},
        "housing_agent": lambda p: {"referral_payload": {"to": "housing-agent"}},
        "compliance_agent": lambda p: {
            "audit_log_entry_id": 1,
            "escalation_path": "human-review",
        },
    }


_CANONICAL_GOAL = Goal(
    goal_id="aicha-healthcare-berlin",
    persona_slug="aicha",
    needs=("letter", "cv", "anerkennung", "search"),  # deliberately unordered
    context={
        "role": "Krankenschwester",
        "location": "Berlin",
        "target_lang": "de",
        "current_status": "drittstaat",
        "target_profession": "nurse",
        "job": {"title": "Krankenschwester"},
        "profile": {"persona_slug": "aicha"},
    },
)


class ContractValidation(unittest.TestCase):
    def test_all_six_specialist_contracts_present(self):
        self.assertEqual(
            set(CONTRACTS),
            {
                "cv_agent",
                "search_agent",
                "anerkennung_agent",
                "letter_agent",
                "housing_agent",
                "compliance_agent",
            },
        )

    def test_built_inputs_satisfy_their_contracts(self):
        all_needs = ("cv", "search", "anerkennung", "letter", "housing", "compliance")
        for step in decompose(Goal("g", "aicha", needs=all_needs)).steps:
            get_contract(step.specialist).validate_input(step.input_payload)  # must not raise

    def test_mock_outputs_satisfy_their_contracts(self):
        for name, handler in _mock_handlers().items():
            get_contract(name).validate_output(handler({}))  # must not raise

    def test_missing_required_input_is_rejected(self):
        with self.assertRaises(ContractViolation) as ctx:
            get_contract("cv_agent").validate_input({"target_lang": "de"})  # no persona_slug
        self.assertEqual(ctx.exception.direction, "input")

    def test_wrong_type_output_is_rejected(self):
        with self.assertRaises(ContractViolation):
            get_contract("search_agent").validate_output({"discovered_jobs": "not-an-array"})

    def test_unknown_specialist_raises(self):
        with self.assertRaises(KeyError):
            get_contract("language_course_agent")


class DeterministicDecomposition(unittest.TestCase):
    def test_needs_routed_into_canonical_order(self):
        steps = [s.specialist for s in decompose(_CANONICAL_GOAL).steps]
        self.assertEqual(steps, ["cv_agent", "search_agent", "anerkennung_agent", "letter_agent"])
        # the plan order follows CANONICAL_ORDER, not the needs order
        self.assertEqual(steps, [s for s in CANONICAL_ORDER if s in set(steps)])

    def test_decomposition_is_deterministic(self):
        a, b = decompose(_CANONICAL_GOAL), decompose(_CANONICAL_GOAL)
        self.assertEqual(
            [(s.specialist, s.input_payload) for s in a.steps],
            [(s.specialist, s.input_payload) for s in b.steps],
        )

    def test_unknown_need_is_dropped(self):
        plan = decompose(Goal("g", "aicha", needs=("cv", "banana")))
        self.assertEqual([s.specialist for s in plan.steps], ["cv_agent"])


class GoldenTraceReplay(unittest.TestCase):
    def test_canonical_plan_receipts_land_in_the_audit_chain(self):
        with TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            audit = AuditLogEmitter(log, _SALT)
            trace = run(_CANONICAL_GOAL, _mock_handlers(), audit)

            # golden trace: 4 ok steps, canonical order, all receipted
            self.assertTrue(trace.ok, trace.to_dict())
            self.assertEqual(
                [r.specialist for r in trace.results],
                ["cv_agent", "search_agent", "anerkennung_agent", "letter_agent"],
            )
            self.assertTrue(all(r.receipt_emitted for r in trace.results))

            # the receipts are in the tamper-evident HMAC chain ...
            self.assertTrue(verify_chain([log], audit.salt).ok)
            records = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
            receipts = [r for r in records if r.get("event_type") == "planner_step"]
            self.assertEqual(
                [r["event_payload"]["specialist"] for r in receipts],
                ["cv_agent", "search_agent", "anerkennung_agent", "letter_agent"],
            )
            # ... carry digests, never raw payloads (no PII in the chain) ...
            for r in receipts:
                self.assertIn("inputDigest", r["event_payload"])
                self.assertNotIn("input_payload", r["event_payload"])
            # ... and are externally anchorable (Phase-5a integration).
            anchor = compute_anchor([log], created_at="2026-05-29T00:00:00+00:00")
            self.assertTrue(verify_anchor([log], anchor).ok)

    def test_trace_is_byte_stable_across_replays(self):
        with TemporaryDirectory() as tmp:
            first = run(
                _CANONICAL_GOAL, _mock_handlers(), AuditLogEmitter(Path(tmp) / "a.jsonl", _SALT)
            )
            second = run(
                _CANONICAL_GOAL, _mock_handlers(), AuditLogEmitter(Path(tmp) / "b.jsonl", _SALT)
            )
        self.assertEqual(first.to_dict(), second.to_dict())


class ContractEnforcementInPlanner(unittest.TestCase):
    def test_bad_handler_output_is_caught_and_still_receipted(self):
        with TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            audit = AuditLogEmitter(log, _SALT)
            handlers = _mock_handlers()
            handlers["cv_agent"] = lambda p: {"wrong": "shape"}  # missing cv_text/cv_sections
            trace = run(Goal("g", "aicha", needs=("cv",)), handlers, audit)
            self.assertFalse(trace.ok)
            self.assertEqual(trace.results[0].status, "output_violation")
            self.assertTrue(trace.results[0].receipt_emitted)
            # a failed step is STILL a receipted, chain-intact audit record
            self.assertTrue(verify_chain([log], audit.salt).ok)

    def test_missing_handler_is_a_handler_error(self):
        with TemporaryDirectory() as tmp:
            audit = AuditLogEmitter(Path(tmp) / "audit.jsonl", _SALT)
            trace = run(Goal("g", "aicha", needs=("cv",)), {}, audit)
            self.assertEqual(trace.results[0].status, "handler_error")
            self.assertTrue(trace.results[0].receipt_emitted)

    def test_stop_on_failure_halts_the_plan(self):
        with TemporaryDirectory() as tmp:
            audit = AuditLogEmitter(Path(tmp) / "audit.jsonl", _SALT)
            handlers = _mock_handlers()
            handlers["cv_agent"] = lambda p: {"wrong": "shape"}
            from civic_agents import execute
            from civic_agents.planner import decompose as _decompose

            trace = execute(
                _decompose(Goal("g", "aicha", needs=("cv", "search"))),
                handlers,
                audit,
                stop_on_failure=True,
            )
            self.assertEqual(len(trace.results), 1)  # halted after cv_agent failed


if __name__ == "__main__":
    unittest.main()
