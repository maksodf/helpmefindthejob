"""Location filter regression — testers reported remote-anywhere jobs
bleeding into specific-location searches (a Berlin search returning
remote-EU jobs from Remotive / WeWorkRemotely / Arbeitnow / HN
"who is hiring?").

Two classes of leak fixed:

1. **Remote-only feeds** (Remotive, WeWorkRemotely) didn't honor the
   ``location`` argument at all. Now flagged ``remote_only = True`` —
   the engine skips them on specific-location searches.
2. **Substring filters with a "remote in text" OR-clause** (Arbeitnow,
   HN-Hiring) let any job mentioning "remote" slip past the
   location check. Tightened to a strict substring match against the
   user's location.

Either condition: when the user names a city/region, the queue must
not contain remote-anywhere jobs. When the user leaves location empty
(or includes "remote"), the remote-only feeds are included again.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone

from company_discovery.aggregators import (
    AggregatedJob,
    JobAggregationEngine,
    ProviderAttribution,
    _user_wants_remote,
)


@dataclass
class _RemoteOnlyFakeProvider:
    name: str = "fake_remote_only"
    attribution: ProviderAttribution | None = None
    remote_only: bool = True
    canned_jobs: list[AggregatedJob] = field(default_factory=list)
    search_called: bool = False

    def search(self, *, query: str, location: str | None, limit: int = 25,
               persona_id: str | None = None) -> list[AggregatedJob]:
        self.search_called = True
        return list(self.canned_jobs)


@dataclass
class _RegularFakeProvider:
    name: str = "fake_regular"
    attribution: ProviderAttribution | None = None
    remote_only: bool = False
    canned_jobs: list[AggregatedJob] = field(default_factory=list)
    search_called: bool = False

    def search(self, *, query: str, location: str | None, limit: int = 25,
               persona_id: str | None = None) -> list[AggregatedJob]:
        self.search_called = True
        return list(self.canned_jobs)


def _job(title: str, source_url: str, source: str, location: str | None) -> AggregatedJob:
    return AggregatedJob(
        title=title,
        company_name="Acme",
        source=source,
        source_url=source_url,
        location=location,
        description="x",
        posted_at=datetime.now(timezone.utc),
    )


class UserWantsRemoteHelperTests(unittest.TestCase):
    def test_empty_location_accepts_remote(self) -> None:
        self.assertTrue(_user_wants_remote(None))
        self.assertTrue(_user_wants_remote(""))

    def test_remote_in_location_accepts_remote(self) -> None:
        self.assertTrue(_user_wants_remote("Remote"))
        self.assertTrue(_user_wants_remote("remote"))
        self.assertTrue(_user_wants_remote("Remote — DACH"))
        self.assertTrue(_user_wants_remote("DACH (remote)"))

    def test_specific_city_does_not_accept_remote(self) -> None:
        self.assertFalse(_user_wants_remote("Berlin"))
        self.assertFalse(_user_wants_remote("Munich"))
        self.assertFalse(_user_wants_remote("Frankfurt"))
        self.assertFalse(_user_wants_remote("Vienna"))


class EngineSkipsRemoteOnlyForLocationSearchTests(unittest.TestCase):
    def test_specific_location_skips_remote_only_provider(self) -> None:
        remote = _RemoteOnlyFakeProvider(canned_jobs=[
            _job("Senior Backend Engineer", "https://remotive.com/x", "fake_remote_only", "Remote (Anywhere)"),
        ])
        regular = _RegularFakeProvider(canned_jobs=[
            _job("Senior Backend Engineer", "https://acme.example/job/1", "fake_regular", "Berlin, DE"),
        ])
        engine = JobAggregationEngine(providers=[remote, regular])

        jobs, outcomes = engine.search(query="senior backend engineer", location="Berlin")

        # Regular provider was called; remote-only was NOT.
        self.assertTrue(regular.search_called)
        self.assertFalse(remote.search_called)
        # Outcome trail records the skip explicitly.
        skip = next(o for o in outcomes if o.provider == "fake_remote_only")
        self.assertEqual(skip.error, "skipped_remote_only_for_location_search")
        self.assertEqual(skip.job_count, 0)
        # Only the Berlin job is in the result set.
        sources = {job.source for job in jobs}
        self.assertNotIn("fake_remote_only", sources)
        self.assertIn("fake_regular", sources)

    def test_empty_location_includes_remote_only_provider(self) -> None:
        remote = _RemoteOnlyFakeProvider(canned_jobs=[
            _job("Senior Backend Engineer", "https://remotive.com/x", "fake_remote_only", "Remote"),
        ])
        engine = JobAggregationEngine(providers=[remote])

        jobs, _ = engine.search(query="senior backend engineer", location=None)
        self.assertTrue(remote.search_called)
        self.assertEqual(len(jobs), 1)

    def test_remote_in_location_includes_remote_only_provider(self) -> None:
        remote = _RemoteOnlyFakeProvider(canned_jobs=[
            _job("Senior Backend Engineer", "https://remotive.com/x", "fake_remote_only", "Remote"),
        ])
        engine = JobAggregationEngine(providers=[remote])

        jobs, _ = engine.search(query="senior backend engineer", location="Remote — DACH")
        self.assertTrue(remote.search_called)
        self.assertEqual(len(jobs), 1)


class ArbeitnowSubstringFilterTightenedTests(unittest.TestCase):
    """When the user searches for Berlin, Arbeitnow's substring filter
    must not leak jobs whose location is just "Remote" — those are
    remote-anywhere listings that the previous OR-clause let through."""

    def test_berlin_search_excludes_remote_only_listing(self) -> None:
        from company_discovery.aggregator_providers import ArbeitnowProvider

        class FakeFetcher:
            def get(self, url, params=None):
                import json as _json
                payload = {"data": [
                    {
                        "slug": "berlin-job",
                        "title": "Senior Backend Engineer",
                        "company_name": "Acme Berlin",
                        "description": "Senior Python role",
                        "location": "Berlin, Germany",
                        "tags": ["python"],
                        "url": "https://example.com/berlin-job",
                        "created_at": "2026-05-01T10:00:00+00:00",
                    },
                    {
                        "slug": "remote-job",
                        "title": "Senior Backend Engineer",
                        "company_name": "Acme Anywhere",
                        "description": "Remote-friendly role across EU",
                        "location": "Remote",
                        "tags": ["python"],
                        "url": "https://example.com/remote-job",
                        "created_at": "2026-05-01T10:00:00+00:00",
                    },
                ]}
                return 200, _json.dumps(payload)

        provider = ArbeitnowProvider(fetcher=FakeFetcher())
        results = provider.search(query="senior backend engineer", location="Berlin")
        urls = [j.source_url for j in results]
        self.assertIn("https://example.com/berlin-job", urls)
        self.assertNotIn("https://example.com/remote-job", urls)


if __name__ == "__main__":
    unittest.main()
