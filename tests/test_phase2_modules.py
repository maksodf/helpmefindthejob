# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Unit tests for Phase 2/3 modules.

Covers structured_analysis, persona_ranking, discovery_providers,
exports, onboarding, watchlist_templates, digests.
"""

from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.ai_providers import AIProviderConfig
from company_discovery.digests import build_digest
from company_discovery.discovery_providers import (
    CuratedSearchProvider,
    DiscoveryEngine,
    DiscoveryResult,
    GreenhouseFeedProvider,
    LeverFeedProvider,
    MockSearchProvider,
)
from company_discovery.exports import (
    discovered_jobs_to_csv,
    discovered_jobs_to_markdown,
    imported_jobs_to_csv,
    imported_jobs_to_markdown,
)
from company_discovery.models import Company, DiscoveredJob, ImportedJob
from company_discovery.onboarding import build_checklist, checklist_progress
from company_discovery.persona_ranking import rank_candidates
from company_discovery.structured_analysis import parse_freeform
from company_discovery.watchlist_templates import get_template, list_templates


class StructuredAnalysisTests(unittest.TestCase):
    def test_parse_json_block(self) -> None:
        output = """Here's my read.
        {"fitScore": 0.78, "recommendation": "apply", "tools": ["JIRA","SAP"], "risks": "tight deadlines",
         "healthcareRelevance": "Strong", "juniorSuitability": "Suitable",
         "requiredExperience": "2-4 years", "languageRequirements": "DE C1"}
        Final note: looks good."""
        parsed = parse_freeform(output)
        self.assertAlmostEqual(parsed.fit_score, 0.78)
        self.assertEqual(parsed.recommendation, "apply")
        self.assertEqual(parsed.tools, ["JIRA", "SAP"])
        self.assertEqual(parsed.risks, ["tight deadlines"])
        self.assertEqual(parsed.healthcare_relevance, "Strong")
        self.assertEqual(parsed.junior_suitability, "Suitable")

    def test_parse_freeform_fallbacks(self) -> None:
        output = "Fit Score: 65\nRecommendation: consider"
        parsed = parse_freeform(output)
        self.assertAlmostEqual(parsed.fit_score, 0.65)
        self.assertEqual(parsed.recommendation, "consider")

    def test_parse_handles_empty(self) -> None:
        parsed = parse_freeform("")
        self.assertIsNone(parsed.fit_score)
        self.assertIsNone(parsed.recommendation)


class PersonaRankingTests(unittest.TestCase):
    def test_ranking_prefers_digital_health_for_digital_roles(self) -> None:
        candidates = [
            {"name": "Acme Hospital", "sector": "Hospital", "type": "company"},
            {"name": "BetaHealth", "sector": "Digital Health", "type": "company"},
            {"name": "Gamma Insurance", "sector": "Statutory health insurer", "type": "company"},
        ]
        ranked = rank_candidates(
            candidates,
            target_roles=["Digital Health", "Project Manager"],
            industry="Healthcare",
        )
        self.assertEqual(ranked[0]["name"], "BetaHealth")
        self.assertIn("relevanceBreakdown", ranked[0])
        self.assertIn("persona", ranked[0]["relevanceReason"])

    def test_location_boost(self) -> None:
        candidates = [
            {
                "name": "BerlinCo",
                "sector": "Hospital",
                "location_hint": "Berlin",
                "type": "company",
            },
            {
                "name": "MunichCo",
                "sector": "Hospital",
                "location_hint": "Munich",
                "type": "company",
            },
        ]
        ranked = rank_candidates(
            candidates, target_roles=["Project Manager"], industry="Healthcare", location="Berlin"
        )
        self.assertEqual(ranked[0]["name"], "BerlinCo")


class DiscoveryProviderTests(unittest.TestCase):
    def test_mock_provider_filters_and_scores(self) -> None:
        provider = MockSearchProvider(
            fixture_companies=[
                DiscoveryResult(
                    name="DigitalHealthCo",
                    website_url="https://digital.example",
                    sector="Digital Health",
                    relevance_score=0.5,
                    relevance_reason="Digital health products",
                ),
                DiscoveryResult(
                    name="GenericCo",
                    website_url="https://generic.example",
                    sector="Other",
                    relevance_score=0.5,
                    relevance_reason="general business",
                ),
            ]
        )
        results = provider.discover(
            target_roles=["Digital Health"], industry="Healthcare", location=None, limit=10
        )
        self.assertEqual(results[0].name, "DigitalHealthCo")

    def test_greenhouse_feed_provider_counts_matches(self) -> None:
        body = json.dumps(
            {
                "jobs": [
                    {
                        "title": "Healthcare Project Manager",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    },
                    {
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                    },
                ]
            }
        )
        provider = GreenhouseFeedProvider(
            company_name="Acme", board_url="https://boards.greenhouse.io/acme"
        )
        results = provider.discover(
            target_roles=["healthcare"],
            industry="Healthcare",
            location=None,
            limit=5,
            body=body,
        )
        self.assertEqual(results[0].source, "greenhouse_feed")
        self.assertGreater(results[0].relevance_score, 0.55)
        self.assertEqual(results[0].raw["match_count"], 1)

    def test_lever_feed_provider(self) -> None:
        body = json.dumps(
            [
                {"text": "Health Consultant", "categories": {"location": "Berlin"}},
                {"text": "Designer", "categories": {"location": "Remote"}},
            ]
        )
        provider = LeverFeedProvider(company_name="Acme", board_url="https://jobs.lever.co/acme")
        results = provider.discover(
            target_roles=["health"],
            industry="Healthcare",
            location="Berlin",
            limit=5,
            body=body,
        )
        self.assertEqual(results[0].source, "lever_feed")

    def test_engine_dedups_by_host(self) -> None:
        a = MockSearchProvider(
            fixture_companies=[
                DiscoveryResult(
                    name="Same",
                    website_url="https://same.example",
                    sector="Hospital",
                    relevance_score=0.8,
                    relevance_reason="...",
                ),
            ]
        )
        b = MockSearchProvider(
            fixture_companies=[
                DiscoveryResult(
                    name="Same Twin",
                    website_url="https://same.example",
                    sector="Hospital",
                    relevance_score=0.7,
                    relevance_reason="...",
                ),
            ]
        )
        engine = DiscoveryEngine(providers=[a, b])
        results = engine.discover(target_roles=[], industry="Healthcare", location=None, limit=5)
        self.assertEqual(len(results), 1)


class ExportsTests(unittest.TestCase):
    def _job(self) -> ImportedJob:
        return ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://example.org/j",
            title="Healthcare Project Manager",
            company_name="Demo",
            location="Berlin",
            description="role",
            application_status="applied",
            fit_score=0.72,
            recommendation="apply",
        )

    def test_imported_jobs_csv_has_header_and_row(self) -> None:
        csv_text = imported_jobs_to_csv([self._job()])
        lines = csv_text.strip().splitlines()
        self.assertEqual(lines[0].split(",")[0], "ID")
        self.assertIn("Healthcare Project Manager", lines[1])
        self.assertIn("applied", lines[1])

    def test_imported_jobs_markdown(self) -> None:
        md = imported_jobs_to_markdown([self._job()])
        self.assertIn("Healthcare Project Manager", md)
        self.assertIn("applied", md)
        self.assertIn("72%", md)

    def test_discovered_jobs_csv_has_header(self) -> None:
        job = DiscoveredJob(
            user_id="u1",
            company_id="c1",
            source_url="https://example.org/j",
            title="Junior Healthcare",
            confidence_score=0.75,
        )
        csv_text = discovered_jobs_to_csv([job])
        self.assertIn("Junior Healthcare", csv_text)
        self.assertIn("75%", csv_text)

    def test_csv_injection_prefix_is_neutralised(self) -> None:
        job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://example.org/j",
            title="=cmd|' /C calc'!A0",
            company_name="@evil-corp",
            location="-1",
            description="role",
        )
        csv_text = imported_jobs_to_csv([job])
        # Title cell must start with a leading single quote so spreadsheets
        # render the text as literal, not as a formula. We assert against
        # the rendered csv_text directly; no per-row split needed since
        # the apostrophe-prefix check is a string-contains.
        self.assertIn("'=cmd", csv_text)
        self.assertIn("'@evil-corp", csv_text)
        self.assertIn("'-1", csv_text)
        # Discovered jobs path should also neutralise.
        discovered = DiscoveredJob(
            user_id="u1",
            company_id="c1",
            source_url="https://example.org/j",
            title="+SUM(1,2)",
        )
        csv_text2 = discovered_jobs_to_csv([discovered])
        self.assertIn("'+SUM", csv_text2)


class OnboardingTests(unittest.TestCase):
    def test_checklist_marks_completion_correctly(self) -> None:
        company = Company(
            user_id="u1",
            name="X",
            website_url="https://x.example",
            career_page_url="https://x.example/c",
        )
        discovered = DiscoveredJob(
            user_id="u1",
            company_id=company.id,
            source_url="https://x.example/j",
            title="Healthcare",
        )
        imported = ImportedJob(
            user_id="u1",
            company_id=company.id,
            discovered_job_id=discovered.id,
            source_url="https://x.example/j",
            title="Healthcare",
            company_name="X",
            analysis_status="completed",
        )
        steps = build_checklist(
            companies=[company],
            discovered_jobs=[discovered],
            imported_jobs=[imported],
            ai_provider=AIProviderConfig(provider_id="manual"),
            schedule_enabled=True,
        )
        progress = checklist_progress(steps)
        ids_complete = {step.id for step in steps if step.complete}
        self.assertIn("add_company", ids_complete)
        self.assertIn("career_page", ids_complete)
        self.assertIn("scan", ids_complete)
        self.assertIn("import", ids_complete)
        self.assertIn("brief", ids_complete)
        self.assertIn("schedule", ids_complete)
        self.assertGreater(progress["completed"], 4)


class WatchlistTemplatesTests(unittest.TestCase):
    def test_list_templates_includes_known_ids(self) -> None:
        ids = {item["id"] for item in list_templates()}
        self.assertIn("hospital_groups_de", ids)
        self.assertIn("statutory_insurers_de", ids)
        self.assertIn("digital_health_de", ids)

    def test_get_template_unknown_returns_none(self) -> None:
        self.assertIsNone(get_template("does-not-exist"))


class DigestsTests(unittest.TestCase):
    def test_digest_uses_recent_jobs(self) -> None:
        company = Company(user_id="u1", name="X", website_url="https://x.example")
        recent = DiscoveredJob(
            user_id="u1",
            company_id=company.id,
            source_url="https://x.example/job",
            title="Healthcare Project Manager",
            location="Berlin",
            discovered_at=datetime.now(timezone.utc),
        )
        text = build_digest(
            user_email="alex@example.com", companies=[company], discovered_jobs=[recent]
        )
        self.assertIn("Hi alex", text)
        self.assertIn("Healthcare Project Manager", text)
        self.assertIn("X", text)

    def test_digest_handles_no_new_jobs(self) -> None:
        text = build_digest(user_email="alex@example.com", companies=[], discovered_jobs=[])
        self.assertIn("No new direct-company roles", text)




if __name__ == "__main__":
    unittest.main()
