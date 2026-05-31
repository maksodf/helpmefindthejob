# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 3 (CACP) — the reference MCP server passes its own conformance suite.

This is the "reference implementation conforms to the spec it publishes" proof:
``run_conformance()`` spawns ``mcp_server.py`` and runs the L1/L2/L3 battery
(catalogue, referral lifecycle, consent + audit). Every numbered assertion must
pass — so ``docs/protocol/cacp-v0.1.md`` + the conformance runner are backed by
a working implementation, not aspirational prose. A third party can run the
exact same suite against their own server via ``python -m conformance.cacp``.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from conformance.cacp.harness import REQUIRED_TOOLS, run_conformance

_SPEC_PATH = Path(__file__).resolve().parent.parent / "docs" / "protocol" / "cacp-v0.1.md"


class ReferenceServerIsConformant(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_conformance()

    def test_overall_conformant(self) -> None:
        self.assertTrue(self.report.ok, "\n" + self.report.summary())

    def test_all_three_levels_pass(self) -> None:
        self.assertEqual(self.report.levels(), {"L1": True, "L2": True, "L3": True})

    def test_every_numbered_check_passed(self) -> None:
        failed = [c.id for c in self.report.checks if not c.passed]
        self.assertEqual(failed, [], f"non-conformant checks: {failed}\n{self.report.summary()}")

    def test_full_battery_present(self) -> None:
        # 5 (L1 catalogue) + 5 (L2 referral lifecycle) + 4 (L3 consent+audit).
        self.assertEqual(len(self.report.checks), 14)
        ids = {c.id for c in self.report.checks}
        self.assertIn("CACP-L1-01", ids)
        self.assertIn("CACP-L2-05", ids)
        self.assertIn("CACP-L3-04", ids)
        self.assertGreaterEqual(len(REQUIRED_TOOLS), 7)

    def test_report_serialises(self) -> None:
        payload = self.report.to_dict()
        self.assertEqual(payload["cacpVersion"], "0.1")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["passed"], payload["total"])

    def test_spec_and_conformance_do_not_drift(self) -> None:
        """Every numbered requirement in docs/protocol/cacp-v0.1.md has a
        conformance check, and every check maps to a spec requirement — the
        normative spec and the runnable suite cannot drift apart."""
        harness_ids = {c.id for c in self.report.checks}
        spec_ids = set(re.findall(r"CACP-L\d-\d\d", _SPEC_PATH.read_text(encoding="utf-8")))
        self.assertEqual(
            harness_ids,
            spec_ids,
            f"spec↔harness id mismatch — harness-only={sorted(harness_ids - spec_ids)}, "
            f"spec-only={sorted(spec_ids - harness_ids)}",
        )


if __name__ == "__main__":
    unittest.main()
