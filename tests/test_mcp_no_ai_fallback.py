# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #57 — No-AI templated-fallback verification.

The honesty doctrine says: every MCP tool must work meaningfully
when no AI provider is configured. A user running the project on
Ollama-only (or no AI at all) MUST be able to use every tool with
a templated / heuristic / deterministic response — NOT a "no AI
available" error.

This file runs every one of the 13 MCP tools in the catalogue
with no AI configured and asserts:
- The response is well-formed (has 'status' field)
- The response is meaningful (not an empty 'no AI' error)
- The response shape matches the AI-configured contract

Hardcoded to the v0.2.0 catalogue. If a new tool is added, add a
matching no-AI case here.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.mcp_tools import (
    TOOL_SCHEMAS,
    CompanyDiscoveryMCPTools,
)
from company_discovery.repository import InMemoryCompanyDiscoveryRepository
from company_discovery.service import CompanyDiscoveryService, ScanConfig


class _NullResponse:
    """Minimal Response shape — service expects .text and
    .status_code. We return an empty body + 200 so "no AI" doesn't
    crash but also doesn't fetch anything real."""

    status_code = 200
    text = ""
    url = ""
    headers: dict = {}

    @property
    def content(self) -> bytes:
        return b""


class _NullFetcher:
    """No-network fetcher. Tools that try to fetch a URL get an
    immediate empty response — which is the correct no-network
    degraded path. We're testing the templated-fallback behaviour,
    not network behaviour."""

    def fetch(self, url: str, user_agent: str = "") -> _NullResponse:
        return _NullResponse()


def _make_tools() -> tuple[CompanyDiscoveryMCPTools, TemporaryDirectory]:
    tmp = TemporaryDirectory()
    repository = InMemoryCompanyDiscoveryRepository()
    service = CompanyDiscoveryService(repository, _NullFetcher(), ScanConfig())
    return CompanyDiscoveryMCPTools(service), tmp


class TemplatedFallbackForEveryTool(unittest.TestCase):
    """13 tests: one per tool in the v0.2.0 catalogue."""

    def setUp(self) -> None:
        self.tools, self.tmp = _make_tools()
        self.addCleanup(self.tmp.cleanup)
        # Seed a company so tools that need one have something to work
        # with. companyId is captured for downstream calls.
        company_payload = self.tools.add_company_to_watchlist(
            userId="u-no-ai",
            name="Acme GmbH",
            websiteUrl="https://acme.example.com",
            careerPageUrl="https://acme.example.com/careers",
            sector="tech",
            notes="seed",
            watchEnabled=True,
        )
        self.company_id = company_payload["company"]["id"]

    def test_schema_catalogue_has_expected_tool_count(self) -> None:
        # Drift guard: any time the catalogue size changes, this
        # test fails so the operator must explicitly update the
        # fallback verification coverage below.
        # phase2-backlog #11 (2026-05-22) added list_referrals +
        # update_referral_status, bringing the catalogue to 15.
        self.assertEqual(len(TOOL_SCHEMAS), 15, "catalogue size after #11")

    def test_suggest_relevant_companies_no_ai(self) -> None:
        out = self.tools.suggest_relevant_companies(
            targetRoles=["Backend Engineer"],
            industry="tech",
            location="Berlin",
        )
        self.assertEqual(out["status"], "ok")
        self.assertIsInstance(out["suggestions"], list)
        # Persona category suggestions are pure-heuristic
        self.assertGreater(len(out["suggestions"]), 0)

    def test_add_company_to_watchlist_no_ai(self) -> None:
        out = self.tools.add_company_to_watchlist(
            userId="u2",
            name="Test Co",
            websiteUrl="https://test.example.com",
            careerPageUrl=None,
            sector="health",
            notes=None,
            watchEnabled=True,
        )
        self.assertEqual(out["status"], "ok")
        self.assertIn("company", out)

    def test_find_company_career_page_no_ai(self) -> None:
        # Even with no network, this should return a structured
        # response — never crash. Status may be ok/blocked/error/
        # not_found depending on the seed company state.
        out = self.tools.find_company_career_page(userId="u-no-ai", companyId=self.company_id)
        self.assertIn("status", out)
        self.assertIn(out["status"], {"ok", "blocked", "error", "not_found"})

    def test_scan_company_career_page_no_ai(self) -> None:
        out = self.tools.scan_company_career_page(userId="u-no-ai", companyId=self.company_id)
        self.assertIn("status", out)
        # Status may be "blocked", "completed", "error" depending on
        # whether the URL resolves — but must be a string
        self.assertIsInstance(out["status"], str)

    def test_extract_direct_jobs_no_ai_with_html(self) -> None:
        # Deterministic ATS / JSON-LD parser — no AI
        sample_html = """
        <html><body>
            <script type="application/ld+json">{
                "@type": "JobPosting",
                "title": "Senior Backend Engineer",
                "description": "Build payments infra"
            }</script>
        </body></html>
        """
        out = self.tools.extract_direct_jobs_from_company_site(
            userId="u-no-ai",
            companyId=self.company_id,
            pageUrl="https://acme.example.com/jobs",
            html=sample_html,
        )
        self.assertEqual(out["status"], "ok")
        self.assertIsInstance(out["jobs"], list)
        # Heuristic extractor must find the JSON-LD job
        self.assertGreaterEqual(len(out["jobs"]), 1)
        self.assertEqual(out["jobs"][0]["title"], "Senior Backend Engineer")

    def test_import_discovered_job_no_ai(self) -> None:
        # Need a discovered_job first — seed one via service
        from datetime import datetime, timezone

        from company_discovery.models import DiscoveredJob

        discovered = DiscoveredJob(
            user_id="u-no-ai",
            company_id=self.company_id,
            source_url="https://acme.example.com/jobs/1",
            title="Backend Eng",
            raw_snippet="Backend Eng @ Acme",
        )
        saved = self.tools.service.repository.save_discovered_job(discovered)
        out = self.tools.import_discovered_job(userId="u-no-ai", discoveredJobId=saved.id)
        self.assertEqual(out["status"], "ok")
        self.assertIn("job", out)

    def test_deduplicate_discovered_jobs_no_ai(self) -> None:
        out = self.tools.deduplicate_discovered_jobs(userId="u-no-ai")
        self.assertEqual(out["status"], "ok")

    def test_get_company_watchlist_summary_no_ai(self) -> None:
        out = self.tools.get_company_watchlist_summary(userId="u-no-ai")
        self.assertEqual(out["status"], "ok")
        self.assertIn("summary", out)

    def test_get_user_profile_for_consent_no_ai(self) -> None:
        # Catalogue v0.2.0 composition tool — pure portable profile
        out = self.tools.get_user_profile_for_consent(
            userId="u-no-ai",
            scopes=["identity", "residence", "employment"],
        )
        self.assertEqual(out["status"], "ok")
        profile = out["profile"]
        self.assertEqual(profile["userId"], "u-no-ai")
        self.assertIn("identity", profile)
        self.assertIn("residence", profile)
        self.assertIn("employment", profile)

    def test_propose_referral_no_ai(self) -> None:
        out = self.tools.propose_referral(
            userId="u-no-ai",
            targetAgent="housing-agent",
            reason="needs_housing_in_berlin",
            context={"city": "Berlin"},
        )
        self.assertEqual(out["status"], "ok")
        referral = out["referral"]
        self.assertEqual(referral["targetAgent"], "housing-agent")
        self.assertEqual(referral["reasonCode"], "needs_housing_in_berlin")
        self.assertTrue(referral["userConsentRequired"])

    def test_query_esco_skill_no_ai(self) -> None:
        # ESCO is a curated reference dataset; no AI
        out = self.tools.query_esco_skill(query="python")
        self.assertEqual(out["status"], "ok")
        self.assertIn("matches", out)
        self.assertIsInstance(out["matches"], list)

    def test_export_eures_compatible_no_ai(self) -> None:
        # Need a discovered job to export
        from company_discovery.models import DiscoveredJob

        discovered = DiscoveredJob(
            user_id="u-no-ai",
            company_id=self.company_id,
            source_url="https://acme.example.com/jobs/eures-1",
            title="Krankenpflegerin",
            location="Berlin, DE",
            raw_snippet="Pflege job",
        )
        saved = self.tools.service.repository.save_discovered_job(discovered)
        out = self.tools.export_eures_compatible(userId="u-no-ai", discoveredJobId=saved.id)
        self.assertEqual(out["status"], "ok")
        self.assertIn("eures", out)

    def test_record_user_outcome_no_ai(self) -> None:
        out = self.tools.record_user_outcome(
            userId="u-no-ai",
            jobId="job-test-1",
            outcomeType="interviewing",
            note="Recruiter reached out",
        )
        self.assertEqual(out["status"], "ok")

    def test_list_referrals_no_ai(self) -> None:
        # phase2-backlog #11: empty-state path returns [] cleanly
        out = self.tools.list_referrals(userId="u-no-ai")
        self.assertEqual(out["status"], "ok")
        self.assertIsInstance(out["referrals"], list)

    def test_update_referral_status_no_ai(self) -> None:
        # phase2-backlog #11: not_found path returns gracefully
        # rather than crashing when the referral doesn't exist
        out = self.tools.update_referral_status(
            userId="u-no-ai",
            referralId="ref-does-not-exist",
            status="accepted",
        )
        self.assertEqual(out["status"], "not_found")

    def test_every_tool_response_has_status_field(self) -> None:
        """Contract: every tool response is a dict with a 'status'
        field. Frontends and downstream agents key on this."""
        # We can't run every tool reflectively because they take
        # different parameters; this test just verifies the pattern
        # for the tools we exercise above. The OTHER tools have
        # been tested individually for their status shape.
        sample_outputs = [
            self.tools.suggest_relevant_companies(["Backend"], "tech"),
            self.tools.get_company_watchlist_summary(userId="u-no-ai"),
            self.tools.query_esco_skill(query="python"),
        ]
        for output in sample_outputs:
            self.assertIn("status", output, f"Missing status: {output}")


if __name__ == "__main__":
    unittest.main()
