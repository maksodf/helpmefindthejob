# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 11a — Slack outbound notification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.slack_notify import post_high_fit_notification


class SlackNotifyTests(unittest.TestCase):
    def test_skipped_when_url_invalid(self) -> None:
        for url in ["", "http://example.test/wrong", "javascript:alert(1)"]:
            res = post_high_fit_notification(
                webhook_url=url,
                job_title="X",
                company_name="Y",
                location=None,
                fit_score=0.9,
                fit_reason=None,
                job_url=None,
            )
            self.assertEqual(res["status"], "skipped")

    def test_posts_compact_message(self) -> None:
        captured = {}

        class FakeResp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b""

        def fake_urlopen(req, timeout=5.0):
            captured["url"] = req.full_url
            captured["body"] = req.data
            captured["headers"] = dict(req.headers)
            return FakeResp()

        with patch("company_discovery.slack_notify.urllib.request.urlopen", fake_urlopen):
            res = post_high_fit_notification(
                webhook_url="https://hooks.slack.com/services/T/B/X",
                job_title="Senior Data Engineer",
                company_name="Acme",
                location="Berlin",
                fit_score=0.82,
                fit_reason="Strong overlap on Python + Postgres.",
                job_url="https://acme/jobs/1",
                public_url="https://app.helpmefindthejob.com",
            )
        self.assertEqual(res["status"], "ok")
        self.assertIn("Senior Data Engineer", captured["body"].decode())
        self.assertIn("82%", captured["body"].decode())
        self.assertIn("Berlin", captured["body"].decode())
        self.assertEqual(captured["headers"].get("Content-type"), "application/json")

    def test_returns_error_on_http_failure(self) -> None:
        import urllib.error

        def boom(req, timeout=5.0):
            raise urllib.error.HTTPError("u", 500, "Server error", {}, None)

        with patch("company_discovery.slack_notify.urllib.request.urlopen", boom):
            res = post_high_fit_notification(
                webhook_url="https://hooks.slack.com/services/X",
                job_title="X",
                company_name="Y",
                location=None,
                fit_score=0.9,
                fit_reason=None,
                job_url=None,
            )
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], 500)


if __name__ == "__main__":
    unittest.main()
