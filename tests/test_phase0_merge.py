"""Phase 0 — merge-semantics + tracking-param canonicalization tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.dedup import effective_freshness_at, normalize_url
from company_discovery.models import DiscoveredJob
from company_discovery.repository import InMemoryCompanyDiscoveryRepository
from company_discovery.service import CompanyDiscoveryService, ScanConfig, StaticFetcher


class TrackingParamCanonTests(unittest.TestCase):
    def test_strips_gclid_fbclid_msclkid(self) -> None:
        url = "https://acme.example/jobs/42?gclid=ABC&fbclid=DEF&msclkid=XYZ&utm_source=foo"
        normalized = normalize_url(url)
        self.assertNotIn("gclid", normalized)
        self.assertNotIn("fbclid", normalized)
        self.assertNotIn("msclkid", normalized)
        self.assertNotIn("utm_source", normalized)

    def test_strips_indeed_vjk(self) -> None:
        url = "https://indeed.example/viewjob?jk=keep&vjk=ephemeral&from=share&promoted=1"
        normalized = normalize_url(url)
        self.assertIn("jk=keep", normalized)
        self.assertNotIn("vjk", normalized)
        self.assertNotIn("from=share", normalized)
        self.assertNotIn("promoted", normalized)

    def test_strips_linkedin_trackers(self) -> None:
        url = "https://example.com/job?trk=public_jobs_topcard&trkInfo=blah&li_fat_id=zzz"
        normalized = normalize_url(url)
        self.assertNotIn("trk=", normalized)
        self.assertNotIn("trkInfo", normalized)
        self.assertNotIn("li_fat_id", normalized)


class MergeSemanticsTests(unittest.TestCase):
    """Re-discovering a job adds to also_seen_at instead of dropping it silently."""

    def setUp(self) -> None:
        self.repo = InMemoryCompanyDiscoveryRepository()
        # Seed a fake fetcher for the service's _fetch_allowed_page calls.
        self.fetcher = StaticFetcher(routes={})
        self.service = CompanyDiscoveryService(self.repo, self.fetcher, ScanConfig())

        from company_discovery.models import Company

        self.company = Company(
            user_id="u1",
            name="Acme",
            website_url="https://acme.example",
            career_page_url="https://acme.example/careers",
        )
        self.repo.save_company(self.company)

    def test_merge_adds_source_to_also_seen_at(self) -> None:
        # Pre-existing job
        original = DiscoveredJob(
            user_id="u1",
            company_id=self.company.id,
            source_url="https://acme.example/jobs/42",
            title="Backend Engineer",
            raw_description="We build great things.",
        )
        self.repo.save_discovered_job(original)

        # Candidate with same URL → dedup matches
        candidate = DiscoveredJob(
            user_id="u1",
            company_id=self.company.id,
            source_url="https://acme.example/jobs/42?utm_source=newsletter",
            title="Backend Engineer",
            raw_description="We build great things.",
        )

        # Simulate the in-scan merge directly
        from datetime import datetime, timezone
        from urllib.parse import urlparse

        duplicate = self.repo.find_duplicate_discovered_job(candidate)
        self.assertIsNotNone(duplicate, "URL canon should match the existing job")
        host = urlparse(candidate.source_url).hostname or "direct"
        existing_map = dict(duplicate.also_seen_at or {})
        existing_map[host] = {
            "url": candidate.source_url,
            "found_at": datetime.now(timezone.utc).isoformat(),
            "source_label": "career_page_scan",
        }
        duplicate.also_seen_at = existing_map
        self.repo.save_discovered_job(duplicate)

        reloaded = self.repo.discovered_jobs[duplicate.id]
        self.assertIn("acme.example", reloaded.also_seen_at)
        self.assertIn(
            "newsletter",
            reloaded.also_seen_at["acme.example"]["url"],
            "the merged source URL must be the candidate's, not the original",
        )

    def test_aggregator_job_can_have_null_company_id(self) -> None:
        job = DiscoveredJob(
            user_id="u1",
            source_url="https://aggregator.example/jobs/1",
            title="Some Job",
        )
        # Field defaults to None.
        self.assertIsNone(job.company_id)
        self.repo.save_discovered_job(job)
        loaded = self.repo.discovered_jobs[job.id]
        self.assertIsNone(loaded.company_id)


class EffectiveFreshnessTests(unittest.TestCase):
    """A re-sighting on a new source promotes the job's effective freshness."""

    def test_falls_back_to_discovered_at_when_no_resightings(self) -> None:
        from datetime import datetime, timezone

        old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        job = DiscoveredJob(
            user_id="u1",
            source_url="https://acme.example/jobs/42",
            title="Backend Engineer",
            discovered_at=old,
        )
        self.assertEqual(effective_freshness_at(job), old)

    def test_picks_latest_resighting_over_discovered_at(self) -> None:
        from datetime import datetime, timezone

        original = datetime(2026, 1, 1, tzinfo=timezone.utc)
        recent = datetime(2026, 5, 9, tzinfo=timezone.utc)
        job = DiscoveredJob(
            user_id="u1",
            source_url="https://acme.example/jobs/42",
            title="Backend Engineer",
            discovered_at=original,
            also_seen_at={
                "indeed.com": {"url": "https://indeed/", "found_at": recent.isoformat()}
            },
        )
        self.assertEqual(effective_freshness_at(job), recent)

    def test_picks_max_across_many_resightings(self) -> None:
        from datetime import datetime, timezone

        a = datetime(2026, 3, 1, tzinfo=timezone.utc)
        b = datetime(2026, 4, 1, tzinfo=timezone.utc)
        c = datetime(2026, 5, 9, tzinfo=timezone.utc)
        job = DiscoveredJob(
            user_id="u1",
            source_url="https://acme.example/jobs/42",
            title="X",
            discovered_at=a,
            also_seen_at={
                "indeed.com": {"found_at": b.isoformat()},
                "linkedin.com": {"found_at": c.isoformat()},
            },
        )
        self.assertEqual(effective_freshness_at(job), c)

    def test_repository_sort_uses_effective_freshness(self) -> None:
        from datetime import datetime, timezone

        repo = InMemoryCompanyDiscoveryRepository()
        # "stale" was discovered first but re-found yesterday via Indeed.
        # "fresh_only_old" was discovered recently with no re-sighting.
        # Effective freshness order should put "stale" first.
        old_discovered = datetime(2026, 1, 1, tzinfo=timezone.utc)
        recent_resighting = datetime(2026, 5, 9, tzinfo=timezone.utc)
        recent_only = datetime(2026, 5, 8, tzinfo=timezone.utc)

        stale = DiscoveredJob(
            user_id="u1",
            source_url="https://a/1",
            title="A",
            discovered_at=old_discovered,
            also_seen_at={"indeed.com": {"found_at": recent_resighting.isoformat()}},
        )
        recent = DiscoveredJob(
            user_id="u1",
            source_url="https://a/2",
            title="B",
            discovered_at=recent_only,
        )
        repo.save_discovered_job(stale)
        repo.save_discovered_job(recent)
        ordered = repo.list_discovered_jobs("u1")
        self.assertEqual(ordered[0].id, stale.id, "Re-sighted job should sort first")


class CrossLocaleDedupTests(unittest.TestCase):
    def test_de_en_software_engineer_collapses(self) -> None:
        from company_discovery.dedup import find_duplicate, normalize_title_cross_locale
        from company_discovery.models import DiscoveredJob

        en = normalize_title_cross_locale("Senior Software Engineer")
        de = normalize_title_cross_locale("Senior Softwareentwickler")
        self.assertEqual(en, de)

        repo = InMemoryCompanyDiscoveryRepository()
        first = DiscoveredJob(
            user_id="u1",
            source_url="https://acme.example/jobs/42",
            title="Senior Software Engineer",
            location="Berlin",
        )
        repo.save_discovered_job(first)
        second = DiscoveredJob(
            user_id="u1",
            source_url="https://acme.example/jobs/42-de",
            title="Senior Softwareentwickler",
            location="Berlin",
        )
        match = find_duplicate(second, repo.discovered_jobs.values())
        self.assertIsNotNone(match)
        self.assertEqual(match.reason, "title_cross_locale")

    def test_does_not_merge_unrelated_roles(self) -> None:
        from company_discovery.dedup import find_duplicate
        from company_discovery.models import DiscoveredJob

        repo = InMemoryCompanyDiscoveryRepository()
        first = DiscoveredJob(
            user_id="u1", source_url="https://x/1", title="Senior Software Engineer", location="Berlin",
        )
        repo.save_discovered_job(first)
        second = DiscoveredJob(
            user_id="u1", source_url="https://x/2", title="Senior Datenanalyst", location="Berlin",
        )
        self.assertIsNone(find_duplicate(second, repo.discovered_jobs.values()))


if __name__ == "__main__":
    unittest.main()
