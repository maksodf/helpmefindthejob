# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Public job-alert SEO pages (Phase 1 tracker item #17).

Operator-edited config at ``data/seo-pages.json`` defines a list of
``/jobs/<slug>`` URLs. Each renders a server-side HTML landing page
with role + city + sign-up CTA. Pages are indexable; their slugs are
manually added to ``static/sitemap.xml``.

These tests cover the data-layer (config parsing) plus the route
behaviour. The route renders are wired through the regular HTTP
handler in `app.py`; we exercise them via subprocess elsewhere — here
we focus on the pure functions to keep the suite fast.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.request import urlopen

if TYPE_CHECKING:
    from app import AppState

ROOT = Path(__file__).resolve().parents[1]


class SeoPageConfigTests(unittest.TestCase):
    def _state_with_config(self, payload: dict) -> AppState:
        from app import AppState

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        # Write the config in the parent dir of the data path because
        # AppState reads from data_path.parent / "seo-pages.json".
        (root / "seo-pages.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        return state

    def test_returns_empty_list_when_config_missing(self) -> None:
        from app import AppState

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        self.assertEqual(state.list_seo_pages(), [])

    def test_malformed_json_returns_empty(self) -> None:
        from app import AppState

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "seo-pages.json").write_text("not json {", encoding="utf-8")
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        self.assertEqual(state.list_seo_pages(), [])

    def test_filters_invalid_slugs(self) -> None:
        state = self._state_with_config(
            {
                "pages": [
                    {"slug": "valid-slug", "title": "T", "role": "R", "city": "C", "intro": "I"},
                    {"slug": "has spaces", "title": "T"},  # filtered (space)
                    {"slug": "has;DROP", "title": "T"},  # filtered (semi)
                    {"slug": "", "title": "T"},  # filtered (empty)
                ],
            }
        )
        slugs = [p["slug"] for p in state.list_seo_pages()]
        self.assertEqual(slugs, ["valid-slug"])

    def test_find_seo_page_returns_match_or_none(self) -> None:
        state = self._state_with_config(
            {
                "pages": [
                    {
                        "slug": "data-engineer-berlin",
                        "title": "T",
                        "role": "R",
                        "city": "C",
                        "intro": "I",
                    },
                ],
            }
        )
        self.assertIsNotNone(state.find_seo_page("data-engineer-berlin"))
        self.assertIsNone(state.find_seo_page("does-not-exist"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding blocked") from error
        return int(sock.getsockname()[1])


class HttpSeoPageRouteTests(unittest.TestCase):
    """Spin up the real server and curl the /jobs/<slug> route. Uses
    the shipped data/seo-pages.json so we exercise the full file-read
    path. The shipped config has a ``data-engineer-berlin`` entry."""

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Copy the shipped example into the test data dir so the
        # AppState reads it from data_path.parent at runtime.
        template = (ROOT / "deploy" / "seo-pages.json.example").read_text(encoding="utf-8")
        Path(self.tmp.name, "seo-pages.json").write_text(template, encoding="utf-8")
        self.port = _free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_DATA_DIR": self.tmp.name,
            "HELPMEFINDTHEJOB_ENV": "development",
        }
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(self.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._terminate)
        self.base = f"http://127.0.0.1:{self.port}"
        for _ in range(40):
            try:
                with urlopen(f"{self.base}/api/health", timeout=0.5) as response:
                    if response.getcode() == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            self.fail("server did not start")

    def _terminate(self) -> None:
        try:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        finally:
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

    def _get(self, path: str) -> tuple[int, str]:
        try:
            with urlopen(f"{self.base}{path}", timeout=2) as response:
                return response.getcode(), response.read().decode("utf-8")
        except HTTPError as error:
            return error.code, error.read().decode("utf-8") if error.fp else ""

    def test_known_slug_renders_with_seo_meta(self) -> None:
        code, html = self._get("/jobs/data-engineer-berlin")
        self.assertEqual(code, 200)
        self.assertIn("<title>Data engineer jobs in Berlin", html)
        self.assertIn("og:title", html)
        self.assertIn("canonical", html)
        self.assertIn("Sign up", html)

    def test_unknown_slug_returns_404_explanation(self) -> None:
        code, html = self._get("/jobs/totally-bogus")
        self.assertEqual(code, 404)
        self.assertIn("Job alert not found", html)

    def test_path_traversal_attempt_rejected(self) -> None:
        # Slug validator should refuse any non-alnum-or-dash characters.
        # urllib will percent-encode these but the validator runs on the
        # decoded path component.
        code, _ = self._get("/jobs/..%2Fetc%2Fpasswd")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
