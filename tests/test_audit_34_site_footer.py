# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-34 — site-wide footer + build SHA.

Until AUDIT-34, no public-facing page carried a real footer. Visitors
landing on /privacy or /impressum couldn't find a contact email, a
security disclosure channel, the Apache 2.0 licence, or the Commons
Conservancy parent-org marker without leaving the page first. The
landing page itself had no footer at all.

After AUDIT-34, ``Handler.serve_static`` injects a single source-of-
truth footer (``app.SITE_FOOTER_HTML``) into any HTML response. The
footer carries: contact email, security email + RFC-9116 pointer,
legal-page nav, Apache 2.0 licence link, Commons Conservancy link,
source-code link, app version, and the build SHA. The build SHA is
resolved at process startup from (1) ``HELPMEFINDTHEJOB_BUILD_SHA``
env var, (2) ``.git/HEAD`` → ref → packed-refs, or (3) ``"dev"``
fallback. ``/api/version`` also exposes ``buildSha`` so API
integrators can surface the same value.

This test file pins both layers:

* Constant integrity — ``SITE_FOOTER_HTML`` carries every required
  marker and ``_inject_html_footer`` is idempotent.
* End-to-end — boot the real handler, request several pages, verify
  each one carries the footer; verify non-HTML responses do NOT.
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

_REQUIRED_FOOTER_MARKERS = (
    b'class="site-footer"',
    b"support@helpmefindthejob.org",
    b"security@helpmefindthejob.org",
    b"/.well-known/security.txt",
    b"Apache 2.0",
    b"Commons Conservancy",
    b"commonsconservancy.org",
    b"/impressum",
    b"/privacy",
    b"/terms",
    b"/data-retention",
)


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class SiteFooterConstantIntegrity(unittest.TestCase):
    """The Python constant + helpers carry the right invariants."""

    def test_site_footer_constant_includes_required_markers(self) -> None:
        from app import SITE_FOOTER_HTML

        for marker in _REQUIRED_FOOTER_MARKERS:
            self.assertIn(
                marker,
                SITE_FOOTER_HTML,
                f"AUDIT-34: SITE_FOOTER_HTML missing {marker!r}",
            )

    def test_site_footer_includes_version_and_build_sha(self) -> None:
        from app import APP_VERSION, BUILD_SHA, SITE_FOOTER_HTML

        self.assertIn(
            f"v{APP_VERSION}".encode(),
            SITE_FOOTER_HTML,
            "AUDIT-34: footer must include the app version",
        )
        self.assertIn(
            f"<code>{BUILD_SHA}</code>".encode(),
            SITE_FOOTER_HTML,
            "AUDIT-34: footer must include the build SHA inside a <code> block",
        )

    def test_inject_html_footer_inserts_before_body_close(self) -> None:
        from app import _inject_html_footer

        page = b"<html><body><h1>Test</h1></body></html>"
        result = _inject_html_footer(page)
        self.assertIn(b'class="site-footer"', result)
        # Footer must come before </body>
        footer_idx = result.find(b'class="site-footer"')
        body_close_idx = result.find(b"</body>")
        self.assertLess(footer_idx, body_close_idx, "Footer should be before </body>")

    def test_inject_html_footer_is_idempotent(self) -> None:
        from app import SITE_FOOTER_HTML, _inject_html_footer

        page = b"<html><body>" + SITE_FOOTER_HTML + b"</body></html>"
        result = _inject_html_footer(page)
        self.assertEqual(
            result.count(b'class="site-footer"'),
            1,
            "AUDIT-34: footer injection must be idempotent — re-running on a "
            "page that already has the footer should not duplicate it.",
        )

    def test_inject_html_footer_no_op_without_body_close(self) -> None:
        from app import _inject_html_footer

        page = b"<!doctype html>not-real-html"
        result = _inject_html_footer(page)
        self.assertEqual(result, page, "no </body> → no injection")

    def test_resolve_build_sha_returns_non_empty(self) -> None:
        from app import BUILD_SHA

        self.assertTrue(BUILD_SHA, "BUILD_SHA must resolve to a non-empty value")
        self.assertLessEqual(len(BUILD_SHA), 12, "BUILD_SHA must be ≤ 12 chars")

    def test_resolve_build_sha_respects_env_var(self) -> None:
        from app import _resolve_build_sha

        os.environ["HELPMEFINDTHEJOB_BUILD_SHA"] = "abc123def4567890"
        try:
            self.assertEqual(_resolve_build_sha(), "abc123def456")  # truncated to 12
        finally:
            del os.environ["HELPMEFINDTHEJOB_BUILD_SHA"]


class SiteFooterLiveResponse(unittest.TestCase):
    """Boot the real handler and probe several pages for the footer."""

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
            body = resp.read()
            return resp.status, dict(resp.getheaders()), body
        finally:
            conn.close()

    def test_footer_injected_on_privacy(self) -> None:
        status, _headers, body = self._get("/privacy")
        self.assertEqual(status, 200)
        for marker in _REQUIRED_FOOTER_MARKERS:
            self.assertIn(marker, body, f"AUDIT-34: /privacy missing {marker!r}")

    def test_footer_injected_on_impressum(self) -> None:
        status, _headers, body = self._get("/impressum")
        self.assertEqual(status, 200)
        for marker in _REQUIRED_FOOTER_MARKERS:
            self.assertIn(marker, body, f"AUDIT-34: /impressum missing {marker!r}")

    def test_footer_injected_on_forgot_password(self) -> None:
        status, _headers, body = self._get("/forgot-password")
        self.assertEqual(status, 200)
        for marker in _REQUIRED_FOOTER_MARKERS:
            self.assertIn(marker, body, f"AUDIT-34: /forgot-password missing {marker!r}")

    def test_footer_injected_on_landing(self) -> None:
        status, _headers, body = self._get("/")
        self.assertEqual(status, 200)
        for marker in _REQUIRED_FOOTER_MARKERS:
            self.assertIn(marker, body, f"AUDIT-34: / missing {marker!r}")

    def test_footer_injected_only_once_on_landing(self) -> None:
        status, _headers, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertEqual(
            body.count(b'class="site-footer"'),
            1,
            "AUDIT-34: footer must appear exactly once per page (idempotent injection)",
        )

    def test_footer_not_injected_on_json_api(self) -> None:
        status, _headers, body = self._get("/api/version")
        self.assertEqual(status, 200)
        self.assertNotIn(
            b"site-footer",
            body,
            "AUDIT-34: site-footer must not leak into JSON API responses",
        )

    def test_footer_not_injected_on_javascript(self) -> None:
        status, _headers, body = self._get("/forgot-password.js")
        self.assertEqual(status, 200)
        self.assertNotIn(b"site-footer", body)

    def test_api_version_carries_build_sha(self) -> None:
        status, _headers, body = self._get("/api/version")
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertIn("buildSha", payload, "AUDIT-34: /api/version must expose buildSha")
        self.assertTrue(payload["buildSha"], "buildSha must be non-empty")
        self.assertLessEqual(len(payload["buildSha"]), 12)

    def test_footer_contains_resolved_build_sha(self) -> None:
        from app import BUILD_SHA

        status, _headers, body = self._get("/privacy")
        self.assertEqual(status, 200)
        self.assertIn(
            f"<code>{BUILD_SHA}</code>".encode(),
            body,
            "AUDIT-34: rendered footer must include the resolved BUILD_SHA",
        )


class SiteFooterBilingualAndLangSwitcher(unittest.TestCase):
    """GAP-1+2 (post-self-audit, 2026-05-23): the footer must
    localise on Accept-Language / ?lang= and must carry a language
    switcher so EN visitors can flip to DE and vice versa."""

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

    def _get(self, path: str, *, accept_language: str = "en") -> tuple[int, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path, headers={"Accept-Language": accept_language})
        resp = conn.getresponse()
        try:
            return resp.status, resp.read()
        finally:
            conn.close()

    def test_en_footer_carries_english_section_headings(self) -> None:
        status, body = self._get("/", accept_language="en")
        self.assertEqual(status, 200)
        for marker in (b">Contact</h2>", b">Legal</h2>", b">Project</h2>"):
            self.assertIn(
                marker,
                body,
                f"GAP-1: English footer must carry English heading {marker!r}",
            )

    def test_de_footer_carries_german_section_headings_when_accept_language_de(self) -> None:
        status, body = self._get("/", accept_language="de-DE,de;q=0.9")
        self.assertEqual(status, 200)
        for marker in (b">Kontakt</h2>", b">Rechtliches</h2>", b">Projekt</h2>"):
            self.assertIn(
                marker,
                body,
                f"GAP-1: DE footer must carry German heading {marker!r}",
            )
        # DE-specific legal-link labels
        self.assertIn(b">Datenschutz</a>", body)
        self.assertIn(b">Nutzungsbedingungen</a>", body)
        self.assertIn(b">Aufbewahrungsfristen</a>", body)
        # English Project labels must NOT bleed into the FOOTER. We
        # scope to the footer block because the SPA's settings view
        # has an unrelated <h2>Legal</h2> heading in the appShell
        # template that's also in body bytes.
        footer_match = re.search(
            rb'<footer[^>]*class="site-footer"[^>]*>(.*?)</footer>',
            body,
            re.DOTALL,
        )
        self.assertIsNotNone(footer_match, "footer must be present")
        footer_html = footer_match.group(1)
        for english_heading in (b">Contact</h2>", b">Legal</h2>", b">Project</h2>"):
            self.assertNotIn(
                english_heading,
                footer_html,
                f"DE footer must not contain {english_heading!r}",
            )

    def test_de_footer_when_lang_query_de_overrides_accept_language(self) -> None:
        # ?lang=de should beat Accept-Language: en
        status, body = self._get("/?lang=de", accept_language="en-US")
        self.assertEqual(status, 200)
        self.assertIn(b">Kontakt</h2>", body)
        self.assertNotIn(b">Contact</h2>", body)

    def test_footer_carries_lang_switcher_with_both_languages(self) -> None:
        status, body = self._get("/", accept_language="en")
        self.assertEqual(status, 200)
        self.assertIn(
            b'class="site-footer-langswitch"',
            body,
            "GAP-2: footer must carry the lang-switcher block",
        )
        # Both languages must be linked
        self.assertIn(b'href="?lang=en"', body)
        self.assertIn(b'href="?lang=de"', body)
        # Both must declare hreflang for accessibility / SEO
        self.assertIn(b'hreflang="en"', body)
        self.assertIn(b'hreflang="de"', body)

    def test_html_responses_carry_vary_accept_language_and_cookie(self) -> None:
        """Post-GAP-1+2: HTML responses depend on Accept-Language (footer
        + legal-page variant) and on Cookie (the lang cookie). Without
        Vary, a CDN/proxy would serve the wrong-language footer to a
        mismatched visitor — the EN visitor whose cached response was
        populated by a DE visitor would see Kontakt instead of Contact."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/")
        resp = conn.getresponse()
        vary = resp.getheader("Vary") or ""
        resp.read()
        conn.close()
        self.assertIn(
            "Accept-Language", vary, "GAP-1+2 followup: HTML responses must Vary: Accept-Language"
        )
        self.assertIn("Cookie", vary, "GAP-1+2 followup: HTML responses must Vary: Cookie")

    def test_non_html_responses_vary_only_by_origin(self) -> None:
        """JS / CSS / manifest don't change by language, but post-
        2026-05-23 they DO Vary: Origin so CDN CORS caching stays
        correct. Assertion: Vary contains 'Origin' but NOT
        'Accept-Language' (which is HTML-only)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/forgot-password.js")
        resp = conn.getresponse()
        vary = resp.getheader("Vary") or ""
        resp.read()
        conn.close()
        self.assertIn(
            "Origin",
            vary,
            f"JS responses must Vary: Origin for CORS caching, got {vary!r}",
        )
        self.assertNotIn(
            "Accept-Language",
            vary,
            f"JS doesn't vary by language; should not be in Vary, got {vary!r}",
        )

    def test_lang_switcher_marks_current_language_with_aria_current(self) -> None:
        # EN page: the English link is aria-current="true"
        _status, body_en = self._get("/", accept_language="en")
        # Strip whitespace to handle multi-line markup
        en_link = re.search(rb'<a[^>]*href="\?lang=en"[^>]*>English</a>', body_en)
        de_link = re.search(rb'<a[^>]*href="\?lang=de"[^>]*>Deutsch</a>', body_en)
        self.assertIsNotNone(en_link)
        self.assertIsNotNone(de_link)
        self.assertIn(b'aria-current="true"', en_link.group(0))
        self.assertNotIn(b'aria-current="true"', de_link.group(0))

        # DE page: the German link is aria-current="true"
        _status, body_de = self._get("/", accept_language="de")
        en_link_de = re.search(rb'<a[^>]*href="\?lang=en"[^>]*>English</a>', body_de)
        de_link_de = re.search(rb'<a[^>]*href="\?lang=de"[^>]*>Deutsch</a>', body_de)
        self.assertIsNotNone(en_link_de)
        self.assertIsNotNone(de_link_de)
        self.assertNotIn(b'aria-current="true"', en_link_de.group(0))
        self.assertIn(b'aria-current="true"', de_link_de.group(0))


# `re` is used in the bilingual-switcher tests above. Imported here
# because the original test file didn't need it.
import re  # noqa: E402

if __name__ == "__main__":
    unittest.main()
