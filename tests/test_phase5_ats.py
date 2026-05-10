"""Phase 5 — Recruitee, Ashby, BambooHR ATS adapters."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.ats_adapters import detect_ats, extract_jobs
from company_discovery.models import Company


def _company(host: str) -> Company:
    return Company(
        user_id="u1",
        name="Stub",
        website_url=f"https://{host}/",
        career_page_url=f"https://{host}/jobs",
    )


class DetectExpansionTests(unittest.TestCase):
    def test_recruitee(self) -> None:
        self.assertEqual(detect_ats("https://acme.recruitee.com/"), "recruitee")

    def test_ashby(self) -> None:
        self.assertEqual(detect_ats("https://jobs.ashbyhq.com/acme"), "ashby")

    def test_bamboohr(self) -> None:
        self.assertEqual(detect_ats("https://acme.bamboohr.com/jobs/"), "bamboohr")


class RecruiteeAdapterTests(unittest.TestCase):
    def test_json_feed_extracts_jobs(self) -> None:
        body = json.dumps({"offers": [
            {"id": 1, "slug": "backend-eng", "title": "Backend Engineer",
             "careers_url": "https://acme.recruitee.com/o/backend-eng",
             "location": "Berlin",
             "description": "<p>build it</p>"},
            {"id": 2, "slug": "frontend-eng", "title": "Frontend Engineer",
             "careers_url": "https://acme.recruitee.com/o/frontend-eng",
             "location": "Munich",
             "description": "<p>react</p>"},
        ]})
        company = _company("acme.recruitee.com")
        result = extract_jobs(company, "https://acme.recruitee.com/api/offers/", body)
        assert result is not None
        self.assertEqual(len(result.jobs), 2)
        first = result.jobs[0]
        self.assertEqual(first.title, "Backend Engineer")
        self.assertEqual(first.location, "Berlin")
        assert first.structured_data is not None
        self.assertEqual(first.structured_data["ats"], "recruitee")
        self.assertEqual(first.structured_data["ats_id"], "1")
        self.assertEqual(first.confidence_score, 0.85)

    def test_html_anchor_fallback(self) -> None:
        body = """
        <ul>
          <a href="/o/backend-eng" class="vacancy">Backend Engineer</a>
          <a href="/o/frontend" class="vacancy-row">Frontend Engineer</a>
        </ul>
        """
        company = _company("acme.recruitee.com")
        result = extract_jobs(company, "https://acme.recruitee.com/jobs", body)
        assert result is not None
        self.assertGreaterEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].title, "Backend Engineer")


class AshbyAdapterTests(unittest.TestCase):
    def test_graphql_payload_extracts(self) -> None:
        body = json.dumps({"data": {"jobBoard": {"jobPostings": [
            {"id": "abc", "title": "Senior Engineer",
             "slug": "senior-engineer", "organizationSlug": "acme",
             "locationName": "Remote — Worldwide",
             "descriptionHtml": "<p>desc</p>"},
        ]}}})
        company = _company("jobs.ashbyhq.com")
        result = extract_jobs(company, "https://jobs.ashbyhq.com/acme", body)
        assert result is not None
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].title, "Senior Engineer")
        self.assertIn("acme/senior-engineer", result.jobs[0].source_url)
        assert result.jobs[0].structured_data is not None
        self.assertEqual(result.jobs[0].structured_data["ats"], "ashby")


class BambooHRAdapterTests(unittest.TestCase):
    def test_json_variant(self) -> None:
        body = json.dumps({"result": [
            {"id": 11, "jobOpeningName": "QA Engineer",
             "jobOpeningURL": "https://acme.bamboohr.com/jobs/view.php?id=11",
             "location": "Berlin",
             "jobOpeningDescription": "<p>QA work</p>"},
        ]})
        company = _company("acme.bamboohr.com")
        result = extract_jobs(company, "https://acme.bamboohr.com/jobs/embed2.php?json=true", body)
        assert result is not None
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].title, "QA Engineer")
        assert result.jobs[0].structured_data is not None
        self.assertEqual(result.jobs[0].structured_data["ats_id"], "11")

    def test_html_embed_anchor(self) -> None:
        body = '<a href="?id=42" class="BambooHR-ATS-Jobs-Item">Backend Engineer</a>'
        company = _company("acme.bamboohr.com")
        result = extract_jobs(company, "https://acme.bamboohr.com/jobs/embed2.php", body)
        assert result is not None
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].title, "Backend Engineer")
        assert result.jobs[0].structured_data is not None
        self.assertEqual(result.jobs[0].structured_data["ats_id"], "42")


if __name__ == "__main__":
    unittest.main()
