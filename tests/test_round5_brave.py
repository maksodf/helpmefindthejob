"""Round-5 tests: B4 Brave Search provider."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.discovery_providers import BraveSearchProvider


@dataclass
class _FakeFetcher:
    """Minimal stub matching ``BraveSearchProvider.fetcher`` signature."""

    body: str
    last_query: str = ""

    def get(self, url, headers, params):
        self.last_query = params.get("q", "")
        return 200, self.body


class BraveSearchProviderTests(unittest.TestCase):
    def _payload(self, *items: dict[str, str]) -> str:
        return json.dumps({"web": {"results": list(items)}})

    def test_no_api_key_returns_empty(self) -> None:
        provider = BraveSearchProvider(api_key="")
        out = provider.discover(target_roles=["backend"], industry="Tech", location="Berlin", limit=5)
        self.assertEqual(out, [])

    def test_filters_restricted_hosts(self) -> None:
        body = self._payload(
            {"url": "https://www.linkedin.com/jobs/123", "title": "On LinkedIn", "description": "noise"},
            {"url": "https://acme.example.com/careers", "title": "Careers - Acme", "description": "Backend role at Acme"},
        )
        provider = BraveSearchProvider(api_key="key", fetcher=_FakeFetcher(body=body))
        out = provider.discover(target_roles=["backend"], industry="Tech", location="Berlin", limit=5)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].name, "Careers")  # split on " - " keeps left side

    def test_extracts_company_name_when_separator_present(self) -> None:
        body = self._payload(
            {"url": "https://acme.com/careers", "title": "Acme - Careers", "description": ""},
        )
        provider = BraveSearchProvider(api_key="key", fetcher=_FakeFetcher(body=body))
        out = provider.discover(target_roles=["pm"], industry="Tech", location="Paris", limit=5)
        self.assertEqual(out[0].name, "Acme")
        self.assertEqual(out[0].source, "brave_search")

    def test_falls_back_to_host_when_no_separator(self) -> None:
        body = self._payload({"url": "https://widgets.example/careers", "title": "Plain title", "description": ""})
        provider = BraveSearchProvider(api_key="key", fetcher=_FakeFetcher(body=body))
        out = provider.discover(target_roles=["pm"], industry="Tech", location="Madrid", limit=5)
        # No separator in title → fall back to the hostname's first segment.
        self.assertEqual(out[0].name, "Widgets")

    def test_query_includes_roles_industry_location(self) -> None:
        body = self._payload({"url": "https://acme.example/careers", "title": "Careers - Acme", "description": ""})
        fetcher = _FakeFetcher(body=body)
        provider = BraveSearchProvider(api_key="key", fetcher=fetcher)
        provider.discover(
            target_roles=["backend engineer", "platform"],
            industry="Tech",
            location="Berlin",
            limit=5,
        )
        for token in ("backend engineer", "platform", "Tech", "Berlin", "careers"):
            self.assertIn(token, fetcher.last_query)

    def test_handles_invalid_body_gracefully(self) -> None:
        provider = BraveSearchProvider(api_key="key", fetcher=_FakeFetcher(body="not json"))
        out = provider.discover(target_roles=["backend"], industry="Tech", location=None, limit=5)
        self.assertEqual(out, [])

    def test_respects_limit(self) -> None:
        body = self._payload(*[
            {"url": f"https://acme{i}.example/careers", "title": f"Careers - Acme{i}", "description": ""}
            for i in range(5)
        ])
        provider = BraveSearchProvider(api_key="key", fetcher=_FakeFetcher(body=body))
        out = provider.discover(target_roles=["backend"], industry="Tech", location=None, limit=2)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
