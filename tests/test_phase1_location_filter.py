# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

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

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        self.search_called = True
        return list(self.canned_jobs)


@dataclass
class _RegularFakeProvider:
    name: str = "fake_regular"
    attribution: ProviderAttribution | None = None
    remote_only: bool = False
    canned_jobs: list[AggregatedJob] = field(default_factory=list)
    search_called: bool = False

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
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
        remote = _RemoteOnlyFakeProvider(
            canned_jobs=[
                _job(
                    "Senior Backend Engineer",
                    "https://remotive.com/x",
                    "fake_remote_only",
                    "Remote (Anywhere)",
                ),
            ]
        )
        regular = _RegularFakeProvider(
            canned_jobs=[
                _job(
                    "Senior Backend Engineer",
                    "https://acme.example/job/1",
                    "fake_regular",
                    "Berlin, DE",
                ),
            ]
        )
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
        remote = _RemoteOnlyFakeProvider(
            canned_jobs=[
                _job(
                    "Senior Backend Engineer",
                    "https://remotive.com/x",
                    "fake_remote_only",
                    "Remote",
                ),
            ]
        )
        engine = JobAggregationEngine(providers=[remote])

        jobs, _ = engine.search(query="senior backend engineer", location=None)
        self.assertTrue(remote.search_called)
        self.assertEqual(len(jobs), 1)

    def test_remote_in_location_includes_remote_only_provider(self) -> None:
        remote = _RemoteOnlyFakeProvider(
            canned_jobs=[
                _job(
                    "Senior Backend Engineer",
                    "https://remotive.com/x",
                    "fake_remote_only",
                    "Remote",
                ),
            ]
        )
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

                payload = {
                    "data": [
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
                    ]
                }
                return 200, _json.dumps(payload)

        provider = ArbeitnowProvider(fetcher=FakeFetcher())
        results = provider.search(query="senior backend engineer", location="Berlin")
        urls = [j.source_url for j in results]
        self.assertIn("https://example.com/berlin-job", urls)
        self.assertNotIn("https://example.com/remote-job", urls)


class LocationMatcherDiacriticAndAliasTests(unittest.TestCase):
    """The matcher must be locale-tolerant: a tester typing 'Munich' or
    'Köln' should not lose listings just because the source spelled the
    city with umlauts (or without). Previously plain casefold-substring
    matching missed both directions, so München-spelled Bundesagentur
    rows fell out of a 'Munich' search and Munich-spelled Indeed rows
    fell out of a 'München' search. Both should now match."""

    def test_munich_query_matches_munchen_job(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertTrue(location_matches("Munich", "München, Deutschland"))
        self.assertTrue(location_matches("munich", "München"))
        self.assertTrue(location_matches("Muenchen", "München"))

    def test_munchen_query_matches_munich_job(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertTrue(location_matches("München", "Munich, Germany"))
        self.assertTrue(location_matches("muenchen", "Munich"))

    def test_koln_aliases(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertTrue(location_matches("Cologne", "Köln, Deutschland"))
        self.assertTrue(location_matches("Köln", "Cologne, Germany"))
        self.assertTrue(location_matches("Koeln", "Köln"))

    def test_unrelated_cities_still_rejected(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertFalse(location_matches("Munich", "Hamburg, Germany"))
        self.assertFalse(location_matches("Berlin", "München"))
        self.assertFalse(location_matches("Cologne", "Frankfurt am Main"))

    def test_arbeitnow_munich_query_includes_munchen_listing(self) -> None:
        """End-to-end: the diacritic-fold + alias pass through the
        ArbeitnowProvider filter."""

        from company_discovery.aggregator_providers import ArbeitnowProvider

        class FakeFetcher:
            def get(self, url, params=None, headers=None):
                import json as _json

                payload = {
                    "data": [
                        {
                            "slug": "muc-job",
                            "title": "Senior Backend",
                            "company_name": "Acme",
                            "description": "Senior Python role",
                            "location": "München, Deutschland",
                            "tags": ["python"],
                            "url": "https://example.com/muc-job",
                            "created_at": "2026-05-01T10:00:00+00:00",
                        },
                    ]
                }
                return 200, _json.dumps(payload)

        provider = ArbeitnowProvider(fetcher=FakeFetcher())
        results = provider.search(query="senior backend", location="Munich")
        self.assertEqual([j.source_url for j in results], ["https://example.com/muc-job"])


class SameNameUsNamesakeBlockerTests(unittest.TestCase):
    """A user in Germany typing 'Berlin' (no country qualifier) must not
    receive 'Berlin, GA, USA' or 'Hamburg, NY' listings. The matcher
    detects US listings via a state-code regex and filters them out
    when the user typed an ambiguous DE/EU city without disambiguation."""

    def test_berlin_query_rejects_berlin_georgia(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertFalse(location_matches("Berlin", "Berlin, GA, USA"))
        self.assertFalse(location_matches("Berlin", "Berlin, GA"))
        self.assertFalse(location_matches("Berlin", "Berlin, OH"))
        self.assertFalse(location_matches("Berlin", "Berlin, NJ"))

    def test_berlin_query_still_accepts_berlin_germany(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertTrue(location_matches("Berlin", "Berlin, Germany"))
        self.assertTrue(location_matches("Berlin", "Berlin, DE"))
        self.assertTrue(location_matches("Berlin", "Berlin · Hybrid"))
        self.assertTrue(location_matches("Berlin", "Berlin"))

    def test_explicit_us_qualifier_still_matches_us_namesake(self) -> None:
        """If the user EXPLICITLY types a US state qualifier (e.g.
        'Berlin, GA'), the namesake blocker stays out of the way and
        the substring match proceeds normally."""
        from company_discovery.aggregators import location_matches

        self.assertTrue(location_matches("Berlin, GA", "Berlin, GA, USA"))

    def test_hamburg_query_rejects_hamburg_ny(self) -> None:
        from company_discovery.aggregators import location_matches

        self.assertFalse(location_matches("Hamburg", "Hamburg, NY"))
        self.assertTrue(location_matches("Hamburg", "Hamburg, Germany"))

    def test_munich_query_rejects_us_namesake(self) -> None:
        from company_discovery.aggregators import location_matches

        # Munich, ND exists (real US town). The alias-expansion path
        # must respect the US-listing rejection too.
        self.assertFalse(location_matches("Munich", "Munich, ND, USA"))
        self.assertTrue(location_matches("Munich", "München, Deutschland"))


class SeniorityConflictsTests(unittest.TestCase):
    """OR-token matching alone passes 'Junior Backend Engineer' for a
    'senior backend engineer' query. The seniority-conflict filter
    rejects obvious mismatches while staying out of the way of queries
    that don't name a seniority band."""

    def test_senior_query_rejects_junior_title(self) -> None:
        from company_discovery.aggregators import seniority_conflicts

        self.assertTrue(seniority_conflicts("senior backend engineer", "Junior Backend Engineer"))
        self.assertTrue(seniority_conflicts("senior python developer", "Praktikant Python"))
        self.assertTrue(seniority_conflicts("senior data scientist", "Working Student — Data"))
        self.assertTrue(seniority_conflicts("lead backend engineer", "Junior Backend Engineer"))

    def test_senior_query_accepts_senior_title(self) -> None:
        from company_discovery.aggregators import seniority_conflicts

        self.assertFalse(seniority_conflicts("senior backend engineer", "Senior Backend Engineer"))
        self.assertFalse(seniority_conflicts("senior backend engineer", "Lead Backend Engineer"))
        self.assertFalse(seniority_conflicts("senior backend engineer", "Staff Backend Engineer"))

    def test_junior_query_rejects_senior_title(self) -> None:
        from company_discovery.aggregators import seniority_conflicts

        self.assertTrue(seniority_conflicts("junior backend engineer", "Senior Backend Engineer"))
        self.assertTrue(seniority_conflicts("internship marketing", "Head of Marketing"))

    def test_unband_query_passes_everything(self) -> None:
        """A query with no seniority signal should not filter on band."""
        from company_discovery.aggregators import seniority_conflicts

        self.assertFalse(seniority_conflicts("backend engineer", "Senior Backend Engineer"))
        self.assertFalse(seniority_conflicts("backend engineer", "Junior Backend Engineer"))
        self.assertFalse(seniority_conflicts("data scientist", "Working Student — Data"))

    def test_arbeitnow_senior_query_rejects_junior_listing(self) -> None:
        """End-to-end: the seniority filter runs inside the Arbeitnow
        provider, not just on the helper."""
        from company_discovery.aggregator_providers import ArbeitnowProvider

        class FakeFetcher:
            def get(self, url, params=None, headers=None):
                import json as _json

                payload = {
                    "data": [
                        {
                            "slug": "junior",
                            "title": "Junior Backend Engineer",
                            "company_name": "Acme",
                            "description": "Junior role",
                            "location": "Berlin, Germany",
                            "tags": ["python"],
                            "url": "https://example.com/junior",
                            "created_at": "2026-05-01T10:00:00+00:00",
                        },
                        {
                            "slug": "senior",
                            "title": "Senior Backend Engineer",
                            "company_name": "Acme",
                            "description": "5+ years",
                            "location": "Berlin, Germany",
                            "tags": ["python"],
                            "url": "https://example.com/senior",
                            "created_at": "2026-05-01T10:00:00+00:00",
                        },
                    ]
                }
                return 200, _json.dumps(payload)

        provider = ArbeitnowProvider(fetcher=FakeFetcher())
        results = provider.search(query="senior backend engineer", location="Berlin")
        urls = [j.source_url for j in results]
        self.assertIn("https://example.com/senior", urls)
        self.assertNotIn("https://example.com/junior", urls)


class DedupCanonicalisationTests(unittest.TestCase):
    """Real-world job URLs vary on three axes that all mean the same
    listing: ``www.`` prefix, trailing slash, and tracking params
    (``?utm_source=...``). The engine's cross-provider dedup must
    collapse them; otherwise the same role shows up twice in the queue
    once from Indeed and once from StepStone with a different UTM."""

    def _engine(self, *url_pairs):
        from dataclasses import dataclass
        from datetime import datetime

        from company_discovery.aggregators import (
            AggregatedJob,
            JobAggregationEngine,
            ProviderAttribution,
        )

        @dataclass
        class _P:
            name: str
            attribution: ProviderAttribution | None
            remote_only: bool
            _jobs: list

            def search(self, *, query, location, limit=25, persona_id=None):
                return list(self._jobs)

        now = datetime.now(timezone.utc)
        providers = []
        for i, (url, desc) in enumerate(url_pairs):
            providers.append(
                _P(
                    name=f"p{i}",
                    attribution=None,
                    remote_only=False,
                    _jobs=[
                        AggregatedJob(
                            title="Senior Backend",
                            company_name="Acme",
                            source=f"p{i}",
                            source_url=url,
                            location="Berlin",
                            description=desc,
                            posted_at=now,
                        )
                    ],
                )
            )
        return JobAggregationEngine(providers=providers)

    def test_www_prefix_dedupes(self) -> None:
        engine = self._engine(
            ("https://acme.example/jobs/42", "x"),
            ("https://www.acme.example/jobs/42", "x"),
        )
        jobs, _ = engine.search(query="x", location="Berlin")
        self.assertEqual(len(jobs), 1)

    def test_trailing_slash_dedupes(self) -> None:
        engine = self._engine(
            ("https://acme.example/jobs/42", "x"),
            ("https://acme.example/jobs/42/", "x"),
        )
        jobs, _ = engine.search(query="x", location="Berlin")
        self.assertEqual(len(jobs), 1)

    def test_utm_params_dedupe(self) -> None:
        engine = self._engine(
            ("https://acme.example/jobs/42", "x"),
            ("https://acme.example/jobs/42?utm_source=indeed", "x"),
        )
        jobs, _ = engine.search(query="x", location="Berlin")
        self.assertEqual(len(jobs), 1)

    def test_combined_variants_dedupe(self) -> None:
        engine = self._engine(
            ("https://acme.example/jobs/42", "x"),
            ("https://www.acme.example/jobs/42/?utm_source=stepstone", "x"),
        )
        jobs, _ = engine.search(query="x", location="Berlin")
        self.assertEqual(len(jobs), 1)

    def test_distinct_paths_preserved(self) -> None:
        engine = self._engine(
            ("https://acme.example/jobs/42", "x"),
            ("https://acme.example/jobs/43", "x"),
        )
        jobs, _ = engine.search(query="x", location="Berlin")
        self.assertEqual(len(jobs), 2)


class TitleFamilyMatchTests(unittest.TestCase):
    """The OR-token filter was passing jobs that shared only a generic
    word like 'manager' or 'engineer' with the user's query. A
    'marketing manager' search returned 'HR Manager', 'Property
    Manager', etc. The title-family rule requires at least one
    *distinctive* (non-generic, non-seniority, non-stopword) token from
    the query to appear in the job title."""

    def test_marketing_manager_rejects_hr_manager(self) -> None:
        from company_discovery.aggregators import title_matches_query_family

        self.assertFalse(title_matches_query_family("marketing manager", "HR Manager"))
        self.assertFalse(title_matches_query_family("marketing manager", "Property Manager"))
        self.assertFalse(
            title_matches_query_family("marketing manager", "Projektmanager Sanierung")
        )

    def test_marketing_manager_accepts_marketing_titles(self) -> None:
        from company_discovery.aggregators import title_matches_query_family

        self.assertTrue(title_matches_query_family("marketing manager", "Marketing Manager"))
        self.assertTrue(
            title_matches_query_family("marketing manager", "Brand Marketing Specialist")
        )
        self.assertTrue(title_matches_query_family("marketing manager", "Marketing Lead"))

    def test_data_scientist_rejects_freelance_writer(self) -> None:
        from company_discovery.aggregators import title_matches_query_family

        self.assertFalse(title_matches_query_family("data scientist", "Freelance Writer"))
        self.assertFalse(title_matches_query_family("data scientist", "Copywriter"))
        self.assertFalse(title_matches_query_family("data scientist", "Customer Support Manager"))

    def test_data_scientist_accepts_data_titles(self) -> None:
        from company_discovery.aggregators import title_matches_query_family

        self.assertTrue(title_matches_query_family("data scientist", "Senior Data Scientist"))
        self.assertTrue(title_matches_query_family("data scientist", "Data Engineer"))
        self.assertTrue(title_matches_query_family("senior data scientist", "ML Data Analyst"))

    def test_purely_generic_query_passes_everything(self) -> None:
        """If the user typed only generic words, fall back to OR-match
        (don't over-filter). E.g. 'engineer' alone is too generic to
        discriminate — let other layers decide."""
        from company_discovery.aggregators import title_matches_query_family

        self.assertTrue(title_matches_query_family("engineer", "Software Developer"))
        self.assertTrue(title_matches_query_family("manager", "Sales Lead"))

    def test_arbeitnow_marketing_query_rejects_hr_manager(self) -> None:
        """End-to-end: the title-family rule runs inside the Arbeitnow
        provider, not just on the helper."""
        from company_discovery.aggregator_providers import ArbeitnowProvider

        class FakeFetcher:
            def get(self, url, params=None, headers=None):
                import json as _json

                payload = {
                    "data": [
                        {
                            "slug": "hr",
                            "title": "HR Manager - Recruiting",
                            "company_name": "X",
                            "description": "manager role",
                            "location": "Berlin, Germany",
                            "tags": [],
                            "url": "https://example.com/hr",
                            "created_at": "2026-05-01T10:00:00+00:00",
                        },
                        {
                            "slug": "mkt",
                            "title": "Marketing Manager",
                            "company_name": "Y",
                            "description": "marketing role",
                            "location": "Berlin, Germany",
                            "tags": [],
                            "url": "https://example.com/mkt",
                            "created_at": "2026-05-01T10:00:00+00:00",
                        },
                    ]
                }
                return 200, _json.dumps(payload)

        provider = ArbeitnowProvider(fetcher=FakeFetcher())
        results = provider.search(query="marketing manager", location="Berlin")
        urls = [j.source_url for j in results]
        self.assertIn("https://example.com/mkt", urls)
        self.assertNotIn("https://example.com/hr", urls)


class SeniorityDefenseInDepthTests(unittest.TestCase):
    """Server-side providers (Bundesagentur, Adzuna, EURES) trust their
    API's keyword match, but ``was=`` / ``what=`` / ``keywords=`` only
    match tokens — they don't enforce seniority bands. We re-apply the
    client-side seniority filter as defense in depth."""

    def test_bundesagentur_filters_junior_and_werkstudent(self) -> None:
        from company_discovery.aggregator_providers import BundesagenturProvider

        class FakeFetcher:
            def get(self, url, params=None, headers=None):
                import json as _json

                payload = {
                    "stellenangebote": [
                        {
                            "titel": "Junior Backend Engineer",
                            "arbeitgeber": "A",
                            "hashId": "h1",
                            "arbeitsort": {"ort": "Berlin", "land": "DE"},
                            "aktuelleVeroeffentlichungsdatum": "2026-05-01",
                        },
                        {
                            "titel": "Senior Backend Engineer",
                            "arbeitgeber": "B",
                            "hashId": "h2",
                            "arbeitsort": {"ort": "Berlin", "land": "DE"},
                            "aktuelleVeroeffentlichungsdatum": "2026-05-01",
                        },
                        {
                            "titel": "Werkstudent Backend",
                            "arbeitgeber": "C",
                            "hashId": "h3",
                            "arbeitsort": {"ort": "Berlin", "land": "DE"},
                            "aktuelleVeroeffentlichungsdatum": "2026-05-01",
                        },
                    ]
                }
                return 200, _json.dumps(payload)

        provider = BundesagenturProvider(fetcher=FakeFetcher())
        results = provider.search(query="senior backend engineer", location="Berlin")
        titles = [r.title for r in results]
        self.assertIn("Senior Backend Engineer", titles)
        self.assertNotIn("Junior Backend Engineer", titles)
        self.assertNotIn("Werkstudent Backend", titles)

    def test_adzuna_filters_junior(self) -> None:
        from company_discovery.aggregator_providers import AdzunaProvider

        class FakeFetcher:
            def get(self, url, params=None, headers=None):
                import json as _json

                payload = {
                    "results": [
                        {
                            "title": "Junior Python Developer",
                            "company": {"display_name": "A"},
                            "location": {"display_name": "Berlin"},
                            "created": "2026-05-01T00:00:00Z",
                            "redirect_url": "https://adzuna.example/1",
                        },
                        {
                            "title": "Senior Python Developer",
                            "company": {"display_name": "B"},
                            "location": {"display_name": "Berlin"},
                            "created": "2026-05-01T00:00:00Z",
                            "redirect_url": "https://adzuna.example/2",
                        },
                    ]
                }
                return 200, _json.dumps(payload)

        provider = AdzunaProvider(app_id="x", app_key="y", fetcher=FakeFetcher())
        results = provider.search(query="senior python developer", location="Berlin")
        urls = [r.source_url for r in results]
        self.assertIn("https://adzuna.example/2", urls)
        self.assertNotIn("https://adzuna.example/1", urls)


if __name__ == "__main__":
    unittest.main()
