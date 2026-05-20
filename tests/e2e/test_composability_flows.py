# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""PART 7 Loop 22 unittest wrapper: composability flows in the regular suite.

Imports the flow drivers from ``tests.e2e.composability_flows`` and runs
each one inside an MCPHarness, asserting every step passes its
postcondition. Keeps the flows in the regular test suite (CI catches
regressions) while the standalone ``scripts/run-mcp-composability-flows.sh``
captures evidence markdown for the grant pack.
"""

from __future__ import annotations

import io
import unittest

from tests.e2e.composability_flows import (
    run_aicha_flow,
    run_esco_eures_flow,
)
from tests.e2e.mcp_client_harness import MCPHarness


class CompositionFlowAichaE2E(unittest.TestCase):
    def test_full_seven_step_chain(self) -> None:
        sink = io.StringIO()
        with MCPHarness() as harness:
            harness.initialize()
            summary = run_aicha_flow(harness, sink)
        self.assertEqual(summary["persona"], "aicha")
        self.assertEqual(len(summary["steps"]), 7)
        for step in summary["steps"]:
            self.assertTrue(step["ok"], msg=f"step {step['n']} ({step['tool']}) failed")


class CompositionFlowEscoEuresE2E(unittest.TestCase):
    def test_full_four_step_chain(self) -> None:
        sink = io.StringIO()
        with MCPHarness() as harness:
            harness.initialize()
            summary = run_esco_eures_flow(harness, sink)
        self.assertEqual(summary["flow"], "esco_eures")
        self.assertEqual(len(summary["steps"]), 4)
        for step in summary["steps"]:
            self.assertTrue(step["ok"], msg=f"step {step['n']} ({step['tool']}) failed")


if __name__ == "__main__":
    unittest.main()
