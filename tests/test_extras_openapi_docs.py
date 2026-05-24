# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""2026-05-23: public API documentation surface.

* GET /api/openapi.json → OpenAPI 3.1 spec for the public REST
  surface. Hand-curated covering health / version / uptime-history /
  site-config / transparency / auth-bootstrap / forgot-password /
  CSP / MCP introspection. Admin-only and per-user data endpoints
  are excluded.

* GET /api/docs → human-readable HTML page (static/api-docs.html)
  that fetches /api/openapi.json and renders it inline via
  /api-docs.js. Same-origin only, no third-party CDN, no
  Swagger UI / Redoc bundle.

* robots.txt now Allows both surfaces so NLnet evaluators and
  federated integrators can discover them via search.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class OpenApiSpecUnit(unittest.TestCase):
    """Unit tests for the in-process spec builder."""

    def test_spec_has_required_top_level_fields(self) -> None:
        from app import _build_openapi_spec

        spec = _build_openapi_spec()
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("info", spec)
        self.assertIn("title", spec["info"])
        self.assertIn("version", spec["info"])
        self.assertIn("license", spec["info"])
        self.assertEqual(spec["info"]["license"]["name"], "Apache-2.0")
        self.assertIn("paths", spec)

    def test_spec_covers_critical_public_paths(self) -> None:
        from app import _build_openapi_spec

        spec = _build_openapi_spec()
        for required_path in (
            "/api/health",
            "/api/version",
            "/api/health/history",
            "/api/auth/status",
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/forgot-password",
            "/csp-report",
            "/mcp/schemas.json",
        ):
            with self.subTest(path=required_path):
                self.assertIn(required_path, spec["paths"])

    def test_spec_is_valid_json(self) -> None:
        from app import _get_openapi_spec_json

        raw = _get_openapi_spec_json()
        # Must round-trip without errors
        parsed = json.loads(raw)
        self.assertEqual(parsed["openapi"], "3.1.0")


class OpenApiLiveSurface(unittest.TestCase):
    """End-to-end: spec served, docs page served, robots.txt allows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls.port = _free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_DATA_DIR": cls._tmp.name,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "A" * 43 + "=",
        }
        cls._process = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(cls.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls._wait_for_health()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._process.poll() is None:
            cls._process.terminate()
            try:
                cls._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls._process.kill()
                cls._process.wait()
        for stream in (cls._process.stdout, cls._process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:  # noqa: BLE001
                    pass
        cls._tmp.cleanup()

    @classmethod
    def _wait_for_health(cls) -> None:
        for _ in range(60):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=0.5)
                conn.request("GET", "/api/health")
                resp = conn.getresponse()
                ok = resp.status == 200
                resp.read()
                conn.close()
                if ok:
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"server did not become healthy on port {cls.port}")

    def _get(self, path: str) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def test_openapi_json_served_at_canonical_path(self) -> None:
        status, headers, body = self._get("/api/openapi.json")
        self.assertEqual(status, 200)
        ct = headers.get("Content-Type", "")
        self.assertIn("application/json", ct)
        spec = json.loads(body.decode("utf-8"))
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("Helpmefindthejob", spec["info"]["title"])

    def test_api_docs_serves_html_page(self) -> None:
        status, headers, body = self._get("/api/docs")
        self.assertEqual(status, 200)
        ct = headers.get("Content-Type", "")
        self.assertIn("text/html", ct)
        # Page references the spec URL + the renderer script
        self.assertIn(b"/api/openapi.json", body)
        self.assertIn(b'src="/api-docs.js"', body)
        # Has the standard chrome
        self.assertIn(b'class="site-footer"', body)

    def test_api_docs_js_is_served(self) -> None:
        status, _h, body = self._get("/api-docs.js")
        self.assertEqual(status, 200)
        # The renderer function is named render()
        self.assertIn(b"function render", body)
        # CSP-safe DOM building only — the renderer must not
        # assign-to-innerHTML anywhere. Match the property-write
        # pattern via regex so a code-comment mention doesn't
        # false-positive.
        import re as _re

        assignment_rx = _re.compile(rb"\.innerHTML\s*=")
        self.assertIsNone(
            assignment_rx.search(body),
            "api-docs.js must not assign to .innerHTML (CSP / XSS safety)",
        )

    def test_robots_allows_openapi_and_docs(self) -> None:
        status, _h, body = self._get("/robots.txt")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn("Allow: /api/docs", text)
        self.assertIn("Allow: /api/openapi.json", text)


if __name__ == "__main__":
    unittest.main()
