# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""CACP portability proof — a SECOND, independent server passes conformance.

The reference server (``mcp_server.py``) and a deliberately-minimal, from-scratch
implementation (``examples/independent_cacp_server.py``) BOTH pass the same
unmodified CACP v0.1 conformance suite. That is the claim a real interoperability
standard must earn: not "the author's one server conforms", but "an independent
party can implement the protocol from the published spec + schema and conform".

``tests/test_cacp_conformance.py`` pins the reference server; this pins the
independent one + asserts it shares no application code.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from conformance.cacp.harness import run_conformance

_SERVER = Path(__file__).resolve().parent.parent / "examples" / "independent_cacp_server.py"


class IndependentServerIsConformant(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_conformance(server_path=_SERVER)

    def test_conformant_on_all_14_checks(self) -> None:
        failed = [c.id for c in self.report.checks if not c.passed]
        self.assertEqual(failed, [], f"non-conformant: {failed}\n{self.report.summary()}")
        self.assertEqual(len(self.report.checks), 14)
        self.assertTrue(self.report.ok)

    def test_all_three_levels_pass(self) -> None:
        self.assertEqual(self.report.levels(), {"L1": True, "L2": True, "L3": True})


class ServerIsTrulyIndependent(unittest.TestCase):
    def test_imports_no_application_code(self) -> None:
        # The portability claim is only meaningful if this server shares no
        # implementation with the reference — only the published wire contracts.
        src = _SERVER.read_text(encoding="utf-8")
        offending = re.search(
            r"^\s*(?:from|import)\s+(?:company_discovery|mcp_server|app|conformance)\b",
            src,
            re.MULTILINE,
        )
        self.assertIsNone(
            offending,
            "the independent server must not import application/reference code "
            f"(found: {offending.group(0).strip() if offending else None})",
        )


if __name__ == "__main__":
    unittest.main()
