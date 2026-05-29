# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Smoke + contract tests for the housing reference agent
(``examples/housing-stub-client/`` — directory name is legacy).

The example is a *real* MCP composition: a second, independent civic
agent composes with Helpmefindthejob over MCP, receives real
consent-scoped profile data, drives the full referral lifecycle, and the
run proves the audit chain (``verify_chain``). These tests guard it
against drift — it is live documentation that must keep running and keep
matching what it claims.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "examples" / "housing-stub-client" / "main.py"


class HousingCompositionDemoRuns(unittest.TestCase):
    """End-to-end: spawn the demo as a subprocess and verify it completes
    successfully and prints the expected (real) composition narrative."""

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, str(DEMO_PATH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=90,
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
        self.assertIn("2024-11-05", self.stdout)
        self.assertIn("helpmefindthejob", self.stdout)

    def test_tools_list_returned_expected_catalogue(self):
        self.assertIn("server advertises 15 tools", self.stdout)
        for tool in (
            "propose_referral",
            "get_user_profile_for_consent",
            "list_referrals",
            "update_referral_status",
            "query_esco_skill",
        ):
            with self.subTest(tool=tool):
                self.assertIn(f"- {tool}", self.stdout)

    def test_mode_1_full_referral_lifecycle(self):
        self.assertIn("Mode 1 — sequential handoff", self.stdout)
        self.assertIn("referralId", self.stdout)
        self.assertIn("userConsentRequired", self.stdout)
        self.assertIn("sourceAgent", self.stdout)
        self.assertIn("targetAgent", self.stdout)
        # Full lifecycle exercised: list_referrals + advance to accepted.
        self.assertIn("list_referrals", self.stdout)
        self.assertIn('"status": "accepted"', self.stdout)

    def test_mode_2_consent_handoff_carries_real_data(self):
        self.assertIn("Mode 2", self.stdout)
        self.assertIn("profile-shared", self.stdout.lower())
        # REAL stored data must flow through the consent handoff — this is
        # the get_user_profile_for_consent bug fix (no longer null nulls).
        self.assertIn("targetRoleFamilies", self.stdout)
        self.assertIn("Krankenpfleger", self.stdout)
        self.assertIn('"preferredLocale": "de"', self.stdout)
        self.assertIn("schemaVersion", self.stdout)

    def test_audit_trail_attributed_and_chain_verifies(self):
        # Every cross-agent call is attributed to the composing agent ...
        self.assertIn("composition_source='housing-reference-agent'", self.stdout)
        # ... and the HMAC chain verifies (tamper-evident, AI Act Article 12).
        self.assertIn("verify_chain() → ok=True", self.stdout)

    def test_no_python_exceptions(self):
        self.assertNotIn("Traceback", self.stdout)
        self.assertNotIn("Traceback", self.result.stderr)


class HousingReferenceAgentRecommendLogic(unittest.TestCase):
    """Unit-test the recommendation logic directly (no subprocess) so a
    failure is easy to localise. The logic must consume the REAL consented
    employment context — clinical target roles prioritise clinic-proximate
    listings."""

    def setUp(self):
        sys.path.insert(0, str(REPO_ROOT / "examples" / "housing-stub-client"))
        from main import HousingReferenceAgent

        self.agent = HousingReferenceAgent(mcp=None, user_id="t")

    def test_clinical_profile_ranks_clinic_proximate_first(self):
        profile = {
            "profile": {
                "employment": {
                    "targetRoleFamilies": ["Krankenpfleger"],
                    "languageLevels": {"German (B1)": "self-reported"},
                }
            }
        }
        ranked = self.agent.recommend_using(profile)
        self.assertTrue(
            ranked[0]["near_clinics"],
            "a clinical profile should rank a clinic-proximate listing first",
        )
        self.assertEqual(len(ranked), 3)

    def test_non_clinical_profile_falls_back_to_rent_order(self):
        profile = {
            "profile": {"employment": {"targetRoleFamilies": ["Frontend developer"], "languageLevels": {}}}
        }
        ranked = self.agent.recommend_using(profile)
        self.assertEqual(len(ranked), 3)
        rents = [listing["rent_eur"] for listing in ranked]
        self.assertEqual(rents, sorted(rents), "non-clinical → plain rent-ascending order")

    def test_handles_empty_profile_gracefully(self):
        ranked = self.agent.recommend_using({})
        self.assertEqual(len(ranked), 3)


class HousingExampleDocumentation(unittest.TestCase):
    """The README must keep claiming what the demo actually does — catches
    doc-vs-code drift in either direction."""

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

    def test_readme_describes_real_composition_consent_and_audit(self):
        # The example is no longer a "mock stub": it is a real composition
        # that proves the consent-bound handoff + the tamper-evident audit.
        lower = self.readme.lower()
        self.assertIn("consent", lower)
        self.assertIn("audit", lower)

    def test_examples_index_lists_this_directory(self):
        self.assertIn("housing-stub-client", self.example_index)


if __name__ == "__main__":
    unittest.main()
