"""Phase 1 — JobAggregatorProvider implementations + engine."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.aggregators import (
    AggregatedJob,
    AggregatorResultCache,
    JobAggregationEngine,
    canonical_query,
)
from company_discovery.aggregator_providers import (
    ArbeitnowProvider,
    BundesagenturProvider,
    EuresProvider,
    HackerNewsHiringProvider,
    MuseProvider,
    RemotiveProvider,
    WeWorkRemotelyProvider,
    default_no_auth_providers,
)


@dataclass
class _FakeFetcher:
    """Maps url → (status, body). Records last-call params for assertion."""

    routes: dict[str, tuple[int, str]] = field(default_factory=dict)
    last_params: dict | None = None

    def get(self, url, headers=None, params=None):
        self.last_params = dict(params or {})
        return self.routes.get(url, (404, ""))


class CanonicalQueryTests(unittest.TestCase):
    def test_same_query_same_hash(self) -> None:
        self.assertEqual(
            canonical_query("Backend Engineer", "Berlin"),
            canonical_query("backend engineer", "berlin"),
        )

    def test_different_location_different_hash(self) -> None:
        self.assertNotEqual(
            canonical_query("backend", "berlin"),
            canonical_query("backend", "munich"),
        )


class ResultCacheTests(unittest.TestCase):
    def test_round_trip_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = AggregatorResultCache(Path(tmp) / "agg.sqlite3", ttl_seconds=2)
            try:
                jobs = [AggregatedJob(title="A", company_name="Co", source="x", source_url="https://e/1")]
                cache.put("x", "abc", jobs)
                hit = cache.get("x", "abc")
                self.assertIsNotNone(hit)
                assert hit is not None
                self.assertEqual(hit[0].title, "A")
                # Expired (manipulate ttl by negative value via a second cache).
                cache.ttl_seconds = -1
                cache.put("x", "stale", jobs)
                self.assertIsNone(cache.get("x", "stale"))
            finally:
                cache.close()


_ARBEITNOW_BODY = json.dumps({
    "data": [
        {"slug": "abc", "title": "Backend Engineer", "company_name": "Acme",
         "location": "Berlin", "description": "<p>build it</p>", "tags": ["python"],
         "url": "https://www.arbeitnow.com/view/abc", "created_at": 1715000000},
        {"slug": "def", "title": "Frontend Engineer", "company_name": "Beta",
         "location": "Munich", "description": "<p>react</p>", "tags": ["react"],
         "url": "https://www.arbeitnow.com/view/def", "created_at": 1715000001},
    ]
})


class ArbeitnowProviderTests(unittest.TestCase):
    def test_filters_by_tokens(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://www.arbeitnow.com/api/job-board-api": (200, _ARBEITNOW_BODY),
        })
        provider = ArbeitnowProvider(fetcher=fetcher)
        out = provider.search(query="backend", location=None, limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].title, "Backend Engineer")
        self.assertEqual(out[0].source, "arbeitnow")
        self.assertIn("build it", out[0].description or "")

    def test_filters_by_location(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://www.arbeitnow.com/api/job-board-api": (200, _ARBEITNOW_BODY),
        })
        provider = ArbeitnowProvider(fetcher=fetcher)
        out = provider.search(query="engineer", location="Berlin", limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].location, "Berlin")

    def test_handles_bad_json_gracefully(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://www.arbeitnow.com/api/job-board-api": (200, "not json"),
        })
        provider = ArbeitnowProvider(fetcher=fetcher)
        self.assertEqual(provider.search(query="x", location=None, limit=5), [])


_MUSE_BODY = json.dumps({
    "results": [
        {"id": 1, "name": "Senior Healthcare Policy Consultant",
         "company": {"name": "PPH Consulting"},
         "contents": "<p>policy work in DE</p>",
         "publication_date": "2026-05-01T12:00:00Z",
         "locations": [{"name": "Berlin, Germany"}],
         "refs": {"landing_page": "https://www.themuse.com/jobs/pph"},
         "categories": ["Healthcare"]},
        {"id": 2, "name": "Marketing Manager",
         "company": {"name": "Brand Co"},
         "contents": "<p>brand work</p>",
         "publication_date": "2026-05-02T12:00:00Z",
         "locations": [{"name": "Remote"}],
         "refs": {"landing_page": "https://www.themuse.com/jobs/brand"}},
    ]
})


class MuseProviderTests(unittest.TestCase):
    def test_query_filters_correctly(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://www.themuse.com/api/public/jobs": (200, _MUSE_BODY),
        })
        provider = MuseProvider(fetcher=fetcher)
        out = provider.search(query="healthcare policy", location=None, limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].company_name, "PPH Consulting")
        self.assertIsNotNone(out[0].posted_at)


_REMOTIVE_BODY = json.dumps({
    "jobs": [
        {"id": 1, "title": "Backend Engineer", "company_name": "Remote Co",
         "url": "https://remotive.com/r/1", "candidate_required_location": "Worldwide",
         "description": "<p>desc</p>", "publication_date": "2026-05-01T00:00:00Z",
         "salary": "100000-120000", "category": "engineering"},
    ]
})


class RemotiveProviderTests(unittest.TestCase):
    def test_extracts_jobs(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://remotive.com/api/remote-jobs": (200, _REMOTIVE_BODY),
        })
        provider = RemotiveProvider(fetcher=fetcher)
        out = provider.search(query="backend", location=None, limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].salary_hint, "100000-120000")
        self.assertEqual(out[0].source, "remotive")


_WWR_RSS = """<?xml version="1.0"?>
<rss><channel>
<item><title>Acme: Senior Backend Engineer</title>
<link>https://weworkremotely.com/r/abc</link>
<pubDate>Sat, 09 May 2026 17:30:00 +0000</pubDate>
<description>&lt;p&gt;great team&lt;/p&gt;</description></item>
<item><title>Beta Inc: Marketing Lead</title>
<link>https://weworkremotely.com/r/xyz</link>
<pubDate>Sat, 09 May 2026 17:31:00 +0000</pubDate>
<description>&lt;p&gt;lead&lt;/p&gt;</description></item>
</channel></rss>"""


class WeWorkRemotelyProviderTests(unittest.TestCase):
    def test_rss_parsed_with_company_split(self) -> None:
        feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        fetcher = _FakeFetcher(routes={feed_url: (200, _WWR_RSS)})
        provider = WeWorkRemotelyProvider(feeds=(feed_url,), fetcher=fetcher)
        out = provider.search(query="backend", location=None, limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].company_name, "Acme")
        self.assertEqual(out[0].title, "Senior Backend Engineer")
        self.assertEqual(out[0].location, "Remote")


_HN_SEARCH_BODY = json.dumps({"hits": [{"objectID": "12345"}]})
_HN_THREAD_BODY = json.dumps({
    "id": 12345,
    "children": [
        {"id": 1, "text": "PPH Consulting | Healthcare Policy Consultant | Berlin, DE\n\nWe are hiring policy consultants for healthcare reform projects in DACH.",
         "created_at": "2026-05-01T00:00:00Z"},
        {"id": 2, "text": "Acme | Senior Backend Engineer | Remote\n\nPython, Postgres, etc.",
         "created_at": "2026-05-02T00:00:00Z"},
    ],
})


class HackerNewsHiringTests(unittest.TestCase):
    def test_finds_thread_and_extracts(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://hn.algolia.com/api/v1/search": (200, _HN_SEARCH_BODY),
            "https://hn.algolia.com/api/v1/items/12345": (200, _HN_THREAD_BODY),
        })
        provider = HackerNewsHiringProvider(fetcher=fetcher)
        out = provider.search(query="healthcare policy", location="Berlin", limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].company_name, "PPH Consulting")
        self.assertEqual(out[0].title, "Healthcare Policy Consultant")


class JobAggregationEngineTests(unittest.TestCase):
    def test_dedups_cross_provider_by_canonical_url(self) -> None:
        # Two providers return the same job.
        @dataclass
        class _Stub:
            name: str
            attribution: object | None
            output: list

            def search(self, *, query, location, limit=25, persona_id=None):
                return list(self.output)

        shared_url = "https://employer.example/jobs/42"
        a = _Stub(name="a", attribution=None, output=[
            AggregatedJob(title="Backend", company_name="Co", source="a",
                          source_url=shared_url, description="short")
        ])
        b = _Stub(name="b", attribution=None, output=[
            AggregatedJob(title="Backend", company_name="Co", source="b",
                          source_url=shared_url, description="this is a much longer description")
        ])
        engine = JobAggregationEngine(providers=[a, b])
        merged, outcomes = engine.search(query="anything", location=None)
        self.assertEqual(len(merged), 1, "cross-provider dup must collapse")
        # Longest description wins.
        assert merged[0].description is not None
        self.assertGreater(len(merged[0].description), 20)
        self.assertEqual(len(outcomes), 2)


class EuresProviderTests(unittest.TestCase):
    def test_parses_jsonld_jobpostings(self) -> None:
        body = """
        <html><head>
        <script type="application/ld+json">
        {"@type":"JobPosting","title":"Healthcare Policy Consultant",
         "hiringOrganization":{"name":"PPH Consulting"},
         "jobLocation":{"address":{"addressLocality":"Berlin","addressCountry":"Germany"}},
         "url":"https://employer.example/jobs/42",
         "description":"<p>health policy reform projects</p>",
         "datePosted":"2026-05-01T10:00:00Z"}
        </script>
        </head></html>
        """
        fetcher = _FakeFetcher(routes={
            "https://ec.europa.eu/eures/eures-apps/searchengine/page/jv-search/search": (200, body),
        })
        provider = EuresProvider(fetcher=fetcher)
        out = provider.search(query="healthcare policy", location="Berlin", limit=5)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].company_name, "PPH Consulting")
        self.assertIn("Berlin", out[0].location or "")
        self.assertEqual(out[0].source, "eures")

    def test_handles_missing_payload(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://ec.europa.eu/eures/eures-apps/searchengine/page/jv-search/search": (404, ""),
        })
        provider = EuresProvider(fetcher=fetcher)
        self.assertEqual(provider.search(query="x", location=None, limit=5), [])


class BundesagenturProviderTests(unittest.TestCase):
    def test_parses_stellenangebote(self) -> None:
        body = json.dumps({"stellenangebote": [
            {"hashId": "abc123", "titel": "Pflegekraft (m/w/d)",
             "arbeitgeber": "Charité Berlin",
             "arbeitsort": {"ort": "Berlin", "plz": "10115", "land": "Deutschland"},
             "aktuelleVeroeffentlichungsdatum": "2026-05-01"},
            {"hashId": "def456", "titel": "Healthcare Policy Analyst",
             "arbeitgeber": "Some GmbH",
             "arbeitsort": {"ort": "Hamburg"},
             "aktuelleVeroeffentlichungsdatum": "2026-05-02"},
        ]})
        fetcher = _FakeFetcher(routes={
            "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs": (200, body),
        })
        provider = BundesagenturProvider(fetcher=fetcher)
        out = provider.search(query="pflege", location="Berlin", limit=10)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].company_name, "Charité Berlin")
        self.assertIn("Berlin", out[0].location or "")
        self.assertTrue(out[0].source_url.startswith("https://www.arbeitsagentur.de/jobsuche/jobdetail/"))

    def test_returns_empty_on_non_200(self) -> None:
        fetcher = _FakeFetcher(routes={
            "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs": (500, ""),
        })
        provider = BundesagenturProvider(fetcher=fetcher)
        self.assertEqual(provider.search(query="x", location=None, limit=5), [])


class DefaultProvidersTests(unittest.TestCase):
    def test_six_providers_present(self) -> None:
        # Adzuna requires keys; without env vars set, it stays out and
        # the default set is the six no-auth aggregators.
        import os
        prior = (os.environ.pop("DIRECTJOB_ADZUNA_APP_ID", None),
                 os.environ.pop("DIRECTJOB_ADZUNA_APP_KEY", None))
        try:
            providers = default_no_auth_providers()
            names = sorted(p.name for p in providers)
            self.assertEqual(
                names,
                ["arbeitnow", "bundesagentur", "hn_hiring", "muse",
                 "remotive", "weworkremotely"],
            )
        finally:
            if prior[0] is not None:
                os.environ["DIRECTJOB_ADZUNA_APP_ID"] = prior[0]
            if prior[1] is not None:
                os.environ["DIRECTJOB_ADZUNA_APP_KEY"] = prior[1]

    def test_adzuna_registered_when_env_set(self) -> None:
        import os
        os.environ["DIRECTJOB_ADZUNA_APP_ID"] = "test_app_id"
        os.environ["DIRECTJOB_ADZUNA_APP_KEY"] = "test_app_key"
        try:
            providers = default_no_auth_providers()
            names = sorted(p.name for p in providers)
            self.assertIn("adzuna", names)
            self.assertEqual(len(providers), 7)
        finally:
            os.environ.pop("DIRECTJOB_ADZUNA_APP_ID", None)
            os.environ.pop("DIRECTJOB_ADZUNA_APP_KEY", None)


class AdzunaProviderTests(unittest.TestCase):
    def test_returns_empty_when_keys_missing(self) -> None:
        from company_discovery.aggregator_providers import AdzunaProvider

        prov = AdzunaProvider(app_id="", app_key="")

        class NeverCalled:
            def get(self, *a, **k):
                raise AssertionError("must not call API without keys")

        prov.fetcher = NeverCalled()
        self.assertEqual(prov.search(query="data", location=None), [])

    def test_parses_results(self) -> None:
        from company_discovery.aggregator_providers import AdzunaProvider

        sample = {
            "results": [
                {
                    "id": "12345",
                    "title": "Senior Data Engineer",
                    "company": {"display_name": "Acme GmbH"},
                    "location": {"display_name": "Berlin, Germany"},
                    "description": "Build pipelines.",
                    "redirect_url": "https://adzuna.example/jobs/12345",
                    "created": "2026-05-09T08:00:00Z",
                    "category": {"label": "IT Jobs"},
                }
            ]
        }

        class FakeFetcher:
            def get(self, url, headers=None, params=None):
                assert "search/1" in url
                assert params["app_id"] == "ID"
                assert params["app_key"] == "KEY"
                assert params["what"] == "data engineer"
                import json as _json
                return 200, _json.dumps(sample)

        prov = AdzunaProvider(app_id="ID", app_key="KEY", fetcher=FakeFetcher())
        jobs = prov.search(query="data engineer", location="Berlin")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Senior Data Engineer")
        self.assertEqual(jobs[0].company_name, "Acme GmbH")
        self.assertEqual(jobs[0].source, "adzuna")
        self.assertIn("Berlin", jobs[0].location)

    def test_handles_non_200(self) -> None:
        from company_discovery.aggregator_providers import AdzunaProvider

        class FakeFetcher:
            def get(self, url, headers=None, params=None):
                return 401, ""

        prov = AdzunaProvider(app_id="ID", app_key="KEY", fetcher=FakeFetcher())
        self.assertEqual(prov.search(query="x", location=None), [])


if __name__ == "__main__":
    unittest.main()
