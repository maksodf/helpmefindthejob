# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 3 cont'd — email-forward ingest parser."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.email_ingest import parse_email_to_jobs

_LINKEDIN_HTML = """
<html><body>
<table><tr><td>
  Hi Yusuf, here are 3 new matches for "Healthcare Policy Consultant":
</td></tr><tr><td>
  <a href="https://www.linkedin.com/jobs/view/9876543210?refId=abc&trk=public_jobs">
    Senior Healthcare Policy Consultant at PPH Consulting
  </a>
</td></tr><tr><td>
  <a href="https://www.linkedin.com/jobs/view/1112223334?ref=ad">
    Health Policy Manager at Bertelsmann
  </a>
</td></tr></table>
</body></html>
"""


_INDEED_TEXT = """
Hi Yusuf,

We have 2 new jobs for you:

1. Junior Backend Engineer at Acme GmbH — Berlin
   https://de.indeed.com/viewjob?jk=abc123&from=share

2. Senior DevOps Engineer at Beta — Munich
   https://de.indeed.com/viewjob?jk=def456&from=share
"""


class EmailIngestTests(unittest.TestCase):
    def test_linkedin_html_extracts_two_jobs(self) -> None:
        out = parse_email_to_jobs(
            sender="alerts@linkedin.com",
            subject="3 new jobs for Healthcare Policy Consultant",
            text_body=None,
            html_body=_LINKEDIN_HTML,
        )
        self.assertEqual(len(out), 2)
        titles = [j.title for j in out]
        self.assertTrue(any("PPH Consulting" in t for t in titles))
        self.assertTrue(any("Bertelsmann" in t for t in titles))
        self.assertTrue(all(j.source == "email-forward:linkedin" for j in out))
        # Company inference: "X at Y"
        companies = [j.company for j in out]
        self.assertIn("PPH Consulting", companies)

    def test_indeed_text_extracts_two_jobs(self) -> None:
        out = parse_email_to_jobs(
            sender="alerts@indeed.com",
            subject="2 new Backend Engineer jobs",
            text_body=_INDEED_TEXT,
            html_body=None,
        )
        urls = sorted(j.url for j in out)
        self.assertEqual(len(urls), 2)
        self.assertTrue(all(j.source == "email-forward:indeed" for j in out))

    def test_filters_out_non_platform_urls(self) -> None:
        body_html = """
        <a href="https://example.com/random">Random link</a>
        <a href="https://www.linkedin.com/jobs/view/42">Real job at Co</a>
        """
        out = parse_email_to_jobs(
            sender="x@y",
            subject="x",
            text_body=None,
            html_body=body_html,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].source, "email-forward:linkedin")

    def test_dedup_collapses_query_variants(self) -> None:
        body_html = """
        <a href="https://www.linkedin.com/jobs/view/42?refId=abc">Role A</a>
        <a href="https://www.linkedin.com/jobs/view/42?refId=def">Role A again</a>
        """
        out = parse_email_to_jobs(
            sender="x@y",
            subject="x",
            text_body=None,
            html_body=body_html,
        )
        self.assertEqual(len(out), 1, "URLs differing only by query should dedup to one row")

    def test_empty_inputs_return_empty(self) -> None:
        self.assertEqual(
            parse_email_to_jobs(sender=None, subject=None, text_body=None, html_body=None), []
        )
        self.assertEqual(
            parse_email_to_jobs(sender="x", subject="x", text_body="", html_body=""), []
        )


if __name__ == "__main__":
    unittest.main()
