# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""DuckDuckGoSearchProvider tests (no network)."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.discovery_providers import DuckDuckGoSearchProvider


@dataclass
class _FakeFetcher:
    body: str
    last_query: str = ""

    def get(self, url, headers, params):
        self.last_query = params.get("q", "")
        return 200, self.body


_DDG_HTML = """
<html>
  <body>
    <div class="result">
      <a class="result__a" href="https://acme.example/careers">Careers - Acme</a>
      <a class="result__snippet">Acme is hiring backend engineers in Berlin.</a>
    </div>
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwidgets.example%2Fjobs">Widgets jobs</a>
      <a class="result__snippet">Widgets — open roles.</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://www.linkedin.com/jobs/12345">LinkedIn job</a>
      <a class="result__snippet">should be filtered</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://acme.example/about">Duplicate host of Acme</a>
      <a class="result__snippet">should dedupe</a>
    </div>
  </body>
</html>
"""


class DuckDuckGoSearchProviderTests(unittest.TestCase):
    def test_parses_results_filters_restricted_dedupes(self) -> None:
        provider = DuckDuckGoSearchProvider(fetcher=_FakeFetcher(body=_DDG_HTML))
        out = provider.discover(
            target_roles=["backend"], industry="Tech", location="Berlin", limit=5,
        )
        names = [r.name for r in out]
        sources = {r.source for r in out}
        hosts = {r.raw["host"] for r in out}

        self.assertIn("Careers", names)  # title split on " - " keeps left side
        # "Widgets jobs" has no separator → falls back to host segment "Widgets".
        self.assertIn("Widgets", names)
        self.assertNotIn("LinkedIn job", names)  # restricted host filtered
        self.assertEqual(len(out), 2)  # acme.example deduped, linkedin filtered
        self.assertEqual(sources, {"duckduckgo"})
        self.assertEqual(hosts, {"acme.example", "widgets.example"})

    def test_query_includes_roles_industry_location(self) -> None:
        fetcher = _FakeFetcher(body=_DDG_HTML)
        provider = DuckDuckGoSearchProvider(fetcher=fetcher)
        provider.discover(
            target_roles=["backend engineer", "platform"],
            industry="Tech",
            location="Berlin",
            limit=5,
        )
        for token in ("backend engineer", "platform", "Tech", "Berlin", "careers"):
            self.assertIn(token, fetcher.last_query)

    def test_handles_empty_body_gracefully(self) -> None:
        provider = DuckDuckGoSearchProvider(fetcher=_FakeFetcher(body=""))
        self.assertEqual(provider.discover(target_roles=["x"], industry="y", location=None, limit=5), [])

    def test_respects_limit(self) -> None:
        body = "".join(
            f'<a class="result__a" href="https://site{i}.example/c">Site{i} - Careers</a>'
            f'<a class="result__snippet">snippet {i}</a>'
            for i in range(10)
        )
        provider = DuckDuckGoSearchProvider(fetcher=_FakeFetcher(body=body))
        out = provider.discover(target_roles=["x"], industry="y", location=None, limit=3)
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()
