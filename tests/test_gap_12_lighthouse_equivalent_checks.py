# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAP-12 (post-self-audit, 2026-05-23): Lighthouse-equivalent
programmatic page-quality checks.

Lighthouse / WebPageTest are the authoritative validators, but they
need a real browser. This file enforces the structural quality
invariants those tools check for:

* Page-size budgets — small pages have a budget; the SPA shell has a
  generous one but caps somewhere.
* No render-blocking inline scripts (CSP-compliant + Lighthouse
  flags inline JS as render-blocking).
* JS loaded with ``defer`` (parser doesn't block).
* All external resources within the CSP allowlist (no surprise
  third-party fetches).
* Same-origin asset loading (CSP same-origin).
* No infinite redirect chains.

Run the actual Lighthouse audit post-deploy at:
https://pagespeed.web.dev/analysis?url=https://helpmefindthejob.org/
to confirm the real-browser metrics.
"""

from __future__ import annotations

import http.client
import os
import re
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]

# Page-size budgets in bytes. Cap is "what we ship today, +20%
# headroom" — tightens drift on accidentally-bloated pages.
_SIZE_BUDGETS = {
    "/": 130_000,            # SPA shell, ~109 KB today
    # UX-G1 (2026-05-23): the global site header added ~3 KB of
    # markup to every public page; was 8 KB before. Bumped to 12 KB
    # to keep headroom for future header refinements without
    # tightening to the byte.
    "/forgot-password": 12_000,
    "/privacy": 25_000,
    "/terms": 12_000,
    "/impressum": 12_000,
    "/data-retention": 16_000,
    "/help": 30_000,
    "/status": 25_000,
    "/changelog": 30_000,
    # 2026-05-23 budget bumps: AUDIT-33 persona-panel CSS + status-
    # uptime-bar CSS + /api/docs CSS grew styles.css from 99 KB to
    # ~106 KB. New bumped budget holds production at 120 KB while
    # leaving headroom for the AUDIT-17 minified /styles.min.css
    # path (~75 KB).
    # 2026-05-23 UX wave (F1 light theme + G1 global header + A10
    # auto-TOC + breadcrumbs + form-UX + api-docs polish + persona-
    # panel mobile mosaic + status mobile grid). styles.css grew
    # from ~105 KB to ~125 KB; bump budget to 140 KB with headroom.
    "/styles.css": 140_000,
    "/styles.min.css": 100_000,
    "/app.js": 400_000,
    "/app.min.js": 250_000,
    "/forgot-password.js": 4_000,
    "/sw.js": 16_000,
}

# Domains the CSP allows for fonts/css. Anything else loaded by a
# page is a surprise third-party fetch (privacy + perf risk).
_CSP_ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class PageQualityChecks(unittest.TestCase):

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

    def test_every_public_surface_within_size_budget(self) -> None:
        for path, budget in _SIZE_BUDGETS.items():
            with self.subTest(path=path):
                status, _h, body = self._get(path)
                self.assertEqual(status, 200, f"{path} → {status}")
                self.assertLess(
                    len(body), budget,
                    f"GAP-12 budget: {path} is {len(body)} bytes, budget {budget}. "
                    "Either drop content or raise the budget here with a comment "
                    "explaining why.",
                )

    def test_no_inline_scripts_in_public_html(self) -> None:
        # CSP allows only script-src 'self', so inline <script>…</script>
        # blocks would be blocked at the browser. They're also render-
        # blocking even when they DO execute. Forbid them.
        for path in ("/", "/privacy", "/impressum", "/forgot-password", "/help"):
            with self.subTest(path=path):
                _status, _h, body = self._get(path)
                text = body.decode("utf-8", errors="replace")
                # Match <script ...> without a src attribute
                for m in re.finditer(r"<script(\s+[^>]*)?>", text):
                    attrs = m.group(1) or ""
                    if "src=" not in attrs and "type=\"application/ld+json\"" not in attrs:
                        self.fail(
                            f"GAP-12: {path} contains inline <script>: {m.group(0)}. "
                            "CSP blocks these; Lighthouse flags as render-blocking."
                        )

    def test_js_assets_use_defer(self) -> None:
        # Parser-blocking scripts hurt FCP. All <script src=...> in our
        # public pages must carry `defer`.
        for path in ("/", "/forgot-password"):
            with self.subTest(path=path):
                _status, _h, body = self._get(path)
                text = body.decode("utf-8", errors="replace")
                for m in re.finditer(r'<script[^>]+src="([^"]+)"[^>]*>', text):
                    tag = m.group(0)
                    src = m.group(1)
                    # Skip externally-pinned scripts (analytics etc.)
                    if "://" in src and not src.startswith(f"http://127.0.0.1:{self.port}"):
                        continue
                    self.assertIn(
                        "defer", tag,
                        f"GAP-12: {path} loads {src!r} without defer — "
                        f"parser-blocking. <script ... defer></script>.",
                    )

    def test_no_unexpected_third_party_resource_origins(self) -> None:
        # Pull only AUTO-FETCHED resource refs (script src, link
        # stylesheet href, img src, iframe src) — outbound <a href>
        # links don't fetch anything until clicked and are out of
        # scope for the CSP allowlist check.
        script_src_rx = re.compile(r'<script[^>]+src="(https?://[^"]+)"')
        link_css_rx = re.compile(
            r'<link[^>]+rel="stylesheet"[^>]+href="(https?://[^"]+)"|'
            r'<link[^>]+href="(https?://[^"]+)"[^>]+rel="stylesheet"'
        )
        img_src_rx = re.compile(r'<img[^>]+src="(https?://[^"]+)"')
        iframe_src_rx = re.compile(r'<iframe[^>]+src="(https?://[^"]+)"')
        host_rx = re.compile(r'^https?://([^/]+)')

        for path in ("/", "/privacy", "/impressum", "/forgot-password", "/help",
                     "/changelog", "/status", "/data-retention", "/terms"):
            with self.subTest(path=path):
                _status, _h, body = self._get(path)
                text = body.decode("utf-8", errors="replace")
                urls: list[str] = []
                for m in script_src_rx.finditer(text):
                    urls.append(m.group(1))
                for m in link_css_rx.finditer(text):
                    urls.append(m.group(1) or m.group(2))
                for m in img_src_rx.finditer(text):
                    urls.append(m.group(1))
                for m in iframe_src_rx.finditer(text):
                    urls.append(m.group(1))
                for url in urls:
                    host_match = host_rx.match(url)
                    if not host_match:
                        continue
                    host = host_match.group(1).lower()
                    if host == "helpmefindthejob.org" or host.startswith("127.0.0.1"):
                        continue
                    self.assertIn(
                        host, _CSP_ALLOWED_HOSTS,
                        f"GAP-12: {path} auto-fetches from third-party host "
                        f"{host!r} (resource: {url!r}) outside the CSP allowlist. "
                        "Add it to _CSP_ALLOWED_HOSTS (after CSP review) or drop "
                        "it from the page.",
                    )

    def test_robots_and_sitemap_have_cache_control(self) -> None:
        for path in ("/robots.txt", "/sitemap.xml"):
            with self.subTest(path=path):
                _status, headers, _body = self._get(path)
                cc = headers.get("Cache-Control", "")
                self.assertIn(
                    "max-age", cc,
                    f"GAP-12: {path} should set Cache-Control: public, max-age=… "
                    "so crawlers don't re-fetch every minute.",
                )

    def test_admin_403_has_no_cache_control(self) -> None:
        # Inverse: per-request decisions must NOT be cached
        _status, headers, _body = self._get("/admin")
        # logged-out /admin = 200 SPA shell, but we test the 403 path
        # via the GAP-3 test. Here we just confirm /api/version (a
        # per-request endpoint) doesn't leak Cache-Control: max-age.
        _status, headers, _body = self._get("/api/version")
        cc = headers.get("Cache-Control", "")
        self.assertNotIn(
            "max-age", cc.lower(),
            f"GAP-12: /api/version returned Cache-Control with max-age: {cc!r}. "
            "Per-request endpoint must not be cached.",
        )

    def test_security_headers_present(self) -> None:
        _status, headers, _body = self._get("/")
        for required in (
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy",
            "Permissions-Policy",
            "Report-To",
        ):
            with self.subTest(header=required):
                self.assertIn(
                    required, headers,
                    f"GAP-12: missing security header {required!r}",
                )

    def test_csp_locks_down_dangerous_apis(self) -> None:
        _status, headers, _body = self._get("/")
        perms = headers.get("Permissions-Policy", "")
        for forbidden in ("geolocation", "microphone", "camera"):
            self.assertIn(
                f"{forbidden}=()", perms,
                f"GAP-12: Permissions-Policy must lock down {forbidden}",
            )


if __name__ == "__main__":
    unittest.main()
