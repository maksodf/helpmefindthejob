# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Smoke + contract tests for examples/housing-stub-client/.

The stub is a runnable demonstration of MCP composition (Modes 1+2
from docs/grant/09-mcp-composition.md). These tests ensure that:

1. The demo runs end-to-end without errors.
2. Every advertised composition step actually completes (handshake,
   tools/list, propose_referral, get_user_profile_for_consent).
3. The output trace contains the structural markers a reader needs
   to follow what happened.
4. The housing-side filter logic correctly reads the
   ``currentStatus`` field from the profile (real bug caught
   during initial implementation: filter read ``status`` which is
   not a profile field — would have masked any real protocol
   change).

These tests are part of the broader "no gaps behind" sweep — the
example is documentation that compiles, and like all live
documentation we guard it against drift.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "examples" / "housing-stub-client" / "main.py"


class HousingStubDemoRuns(unittest.TestCase):
    """End-to-end: spawn the demo as a subprocess, verify it
    completes successfully and prints the expected narrative."""

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, str(DEMO_PATH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        cls.result = result
        cls.stdout = result.stdout

    def test_exit_code_zero(self):
        self.assertEqual(
            self.result.returncode,
            0,
            f"demo failed:\nSTDOUT:\n{self.stdout}\nSTDERR:\n{self.result.stderr}",
        )

    def test_handshake_completed(self):
        self.assertIn("Handshake: initialize", self.stdout)
        self.assertIn("Handshake: notifications/initialized", self.stdout)
        # Server reply contains protocol + name
        self.assertIn("2024-11-05", self.stdout)
        self.assertIn("helpmefindthejob", self.stdout)

    def test_tools_list_returned_expected_catalogue(self):
        # phase2-backlog #11 (2026-05-22) added list_referrals +
        # update_referral_status, bringing the catalogue to 15.
        self.assertIn("server advertises 15 tools", self.stdout)
        for tool in (
            "propose_referral",
            "get_user_profile_for_consent",
            "suggest_relevant_companies",
            "query_esco_skill",
        ):
            with self.subTest(tool=tool):
                self.assertIn(f"- {tool}", self.stdout)

    def test_mode_1_sequential_handoff_demonstrated(self):
        self.assertIn("Mode 1 — sequential handoff", self.stdout)
        # The propose_referral response shape — referralId is the
        # primary new identifier the housing agent gets back, and
        # userConsentRequired enforces that consent is per-invocation.
        self.assertIn("referralId", self.stdout)
        self.assertIn("userConsentRequired", self.stdout)
        self.assertIn("sourceAgent", self.stdout)
        self.assertIn("targetAgent", self.stdout)

    def test_mode_2_profile_shared_demonstrated(self):
        self.assertIn("Mode 2 — profile-shared composition", self.stdout)
        # The profile response with the employment scope
        self.assertIn("scopes=['employment']", self.stdout)
        # The scopes field appears inside the (escaped) nested-JSON
        # text content from the MCP response. Match permissively.
        self.assertRegex(self.stdout, r'\\"scopes\\":\s*\[')
        self.assertIn("employment", self.stdout)
        # And the schema-versioned profile shape
        self.assertIn("currentStatus", self.stdout)
        self.assertIn("schemaVersion", self.stdout)

    def test_filter_executed_against_real_listings(self):
        # The filter narrates how many listings it kept
        match = re.search(r"filter retained (\d+) of (\d+) listings", self.stdout)
        self.assertIsNotNone(match, "filter narration missing — demo broke silently")
        kept, total = int(match.group(1)), int(match.group(2))
        self.assertEqual(total, 3, "demo has 3 mock listings; total drift")
        # For the no-profile / unknown-status default, the filter is
        # least-harm: it excludes listings that require proof of
        # employment. That leaves exactly 1 listing.
        self.assertEqual(
            kept,
            1,
            "demo should keep only the PoE-not-required listing in "
            "the unknown-status default — if more, the filter is "
            "no longer applying least-harm defaults",
        )

    def test_no_python_exceptions_in_stdout(self):
        self.assertNotIn("Traceback", self.stdout)
        self.assertNotIn("Error", self.stderr if False else self.result.stderr)


class HousingAgentStubFilterLogic(unittest.TestCase):
    """Unit-test the filter directly — independent of subprocess
    invocation so future failures are easy to diagnose.

    Guards the bug found in initial implementation where the filter
    read ``status`` instead of ``currentStatus``."""

    def setUp(self):
        sys.path.insert(0, str(REPO_ROOT / "examples" / "housing-stub-client"))
        from main import HousingAgentStub

        # No live MCP needed for the filter unit test
        self.stub = HousingAgentStub(mcp=None, user_id="t")

    def test_unknown_status_excludes_proof_required(self):
        kept = self.stub.filter_listings_by_profile(
            {"profile": {"employment": {"currentStatus": None}}}
        )
        self.assertTrue(all(not k["requires_proof_of_employment"] for k in kept))

    def test_job_seeking_excludes_proof_required(self):
        kept = self.stub.filter_listings_by_profile(
            {"profile": {"employment": {"currentStatus": "job_seeking"}}}
        )
        self.assertTrue(all(not k["requires_proof_of_employment"] for k in kept))

    def test_employed_keeps_all_listings(self):
        kept = self.stub.filter_listings_by_profile(
            {"profile": {"employment": {"currentStatus": "employed"}}}
        )
        self.assertEqual(len(kept), 3)

    def test_filter_handles_flat_payload(self):
        """If the profile dict is the response payload directly
        (no `profile` wrapper), the filter still reads currentStatus."""

        kept = self.stub.filter_listings_by_profile({"employment": {"currentStatus": "employed"}})
        self.assertEqual(len(kept), 3)

    def test_filter_reads_currentStatus_not_status(self):
        """The Helpmefindthejob profile schema names this field
        ``currentStatus``. If someone accidentally reverts to
        reading ``status``, the demo silently always excludes
        PoE listings even for employed users. This test guards
        that."""

        # If filter erroneously reads `status`, this employed user
        # would get only 1 listing instead of 3.
        kept = self.stub.filter_listings_by_profile(
            {"profile": {"employment": {"currentStatus": "employed", "status": "ignored"}}}
        )
        self.assertEqual(
            len(kept),
            3,
            "filter is reading the wrong field (likely 'status' instead of 'currentStatus')",
        )


class HousingStubReadmeDocumentation(unittest.TestCase):
    """The README must keep claiming what the demo actually does.
    Catches doc-vs-code drift in either direction."""

    def setUp(self):
        self.readme = (REPO_ROOT / "examples" / "housing-stub-client" / "README.md").read_text(
            encoding="utf-8"
        )
        self.example_index = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")

    def test_readme_names_both_modes(self):
        self.assertIn("Mode 1", self.readme)
        self.assertIn("sequential handoff", self.readme.lower())
        self.assertIn("Mode 2", self.readme)
        self.assertIn("profile-shared", self.readme.lower())

    def test_readme_references_decision_20(self):
        self.assertIn("Decision 20", self.readme)

    def test_readme_explains_why_a_stub(self):
        self.assertIn("mock stub", self.readme.lower())

    def test_examples_index_lists_this_directory(self):
        self.assertIn("housing-stub-client", self.example_index)


if __name__ == "__main__":
    unittest.main()
