# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""The CACP conformance suite has teeth — it REJECTS non-conformant servers.

A conformance suite that only ever passes is a rubber stamp. The independent
server (``examples/independent_cacp_server.py``) supports env-gated, default-off
violations (``HELPMEFINDTHEJOB_CACP_BREAK``); each injects exactly ONE CACP
violation. This test proves the suite fails at the corresponding numbered check
— and only there — so it genuinely discriminates conformant from non-conformant
implementations rather than vacuously passing everything.
"""

from __future__ import annotations

import os
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from conformance.cacp.harness import run_conformance

_SERVER = Path(__file__).resolve().parent.parent / "examples" / "independent_cacp_server.py"
_ENV = "HELPMEFINDTHEJOB_CACP_BREAK"

#: violation mode -> the single CACP check it must trip.
_CASES = {
    "drop_tool": "CACP-L1-04",  # a required composition tool is absent
    "bad_semver": "CACP-L1-03",  # a tool version is not SemVer
    "accept_bad_scope": "CACP-L3-02",  # an unknown consent scope is NOT rejected
    "leak_tenant": "CACP-L2-05",  # cross-tenant referral mutation succeeds
}


@contextmanager
def _injected_break(mode: str) -> Iterator[None]:
    prev = os.environ.get(_ENV)
    os.environ[_ENV] = mode
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = prev


class ConformanceSuiteRejectsViolations(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop(_ENV, None)  # never inherit a stray break

    def test_control_run_is_conformant(self) -> None:
        # with no violation injected, the same server is fully conformant —
        # so a failure below is the break, not a broken server.
        report = run_conformance(server_path=_SERVER)
        self.assertTrue(report.ok, "control run must be conformant\n" + report.summary())

    def test_each_violation_trips_exactly_its_check(self) -> None:
        for mode, expected in _CASES.items():
            with self.subTest(violation=mode), _injected_break(mode):
                report = run_conformance(server_path=_SERVER)
                failed = {c.id for c in report.checks if not c.passed}
                self.assertFalse(report.ok, f"{mode}: suite PASSED a non-conformant server")
                self.assertIn(
                    expected, failed, f"{mode}: expected {expected}; failed={sorted(failed)}"
                )
                # discrimination: it trips the targeted check and not unrelated ones
                self.assertEqual(
                    failed, {expected}, f"{mode}: should trip only {expected}; got {sorted(failed)}"
                )


if __name__ == "__main__":
    unittest.main()
