# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for product-robustness bugs found in the bug hunt:

- Aggregation: one provider returning a non-AggregatedJob (or a None/empty
  source_url) used to crash the whole fan-out in the dedup loop, and distinct
  URL-less jobs collapsed into one under the "" key. The isolation boundary now
  extends past provider.search() into the merge, and URL-less jobs keep unique
  keys.
- CV rendering: the <img> passthrough (inline + full-line) let user-supplied
  event handlers (onerror=, ...) survive into rendered CV HTML (self-XSS). Inline
  <img> is now escaped; a full-line <img> is rebuilt from an allow-list.
"""

from __future__ import annotations

import unittest

from company_discovery.aggregators import AggregatedJob, JobAggregationEngine
from company_discovery.cv_builder import _md_inline, cv_markdown_to_html


class _Provider:
    remote_only = False

    def __init__(self, name: str, jobs: list) -> None:
        self.name = name
        self._jobs = jobs

    def search(self, *, query, location, limit=25, persona_id=None):  # noqa: ANN001
        return self._jobs


class AggregatorIsolationTests(unittest.TestCase):
    def test_junk_provider_output_does_not_crash_fanout(self) -> None:
        eng = JobAggregationEngine(providers=[_Provider("junk", [{"not": "a job"}])])
        jobs, _outcomes = eng.search(query="nurse", location="Berlin")
        self.assertIsInstance(jobs, list)  # the merge survived the bad element

    def test_none_source_url_does_not_crash(self) -> None:
        bad = AggregatedJob(title="X", company_name="Y", source="s", source_url=None)  # type: ignore[arg-type]
        eng = JobAggregationEngine(providers=[_Provider("p", [bad])])
        jobs, _ = eng.search(query="nurse", location="Berlin")
        self.assertIsInstance(jobs, list)

    def test_distinct_empty_url_jobs_not_collapsed(self) -> None:
        j1 = AggregatedJob(title="Nurse role A", company_name="Clinic A", source="s", source_url="")
        j2 = AggregatedJob(title="Nurse role B", company_name="Clinic B", source="s", source_url="")
        eng = JobAggregationEngine(providers=[_Provider("p", [j1, j2])])
        jobs, _ = eng.search(query="nurse", location="Berlin")
        self.assertGreaterEqual(len(jobs), 2, "distinct URL-less jobs must not collapse into one")


class CvImgXssTests(unittest.TestCase):
    def test_inline_img_is_escaped(self) -> None:
        out = _md_inline("<img src=x onerror=alert(1)>")
        # The tag is escaped to harmless text (&lt;img ...&gt;) — no LIVE <img>
        # element, so the onerror handler can never execute. (The string "onerror"
        # legitimately remains, but only as escaped text.)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)

    def test_full_line_malicious_img_dropped(self) -> None:
        out = cv_markdown_to_html("<img src=x onerror=alert(document.cookie)>")
        self.assertNotIn("onerror", out)
        self.assertNotIn("<img src=x", out)

    def test_legit_photo_preserved_with_handlers_stripped(self) -> None:
        out = cv_markdown_to_html(
            '<img src="data:image/png;base64,iVBOR" alt="Profile photo" onerror="bad()" />'
        )
        self.assertIn('src="data:image/png', out)
        self.assertNotIn("onerror", out)


if __name__ == "__main__":
    unittest.main()
