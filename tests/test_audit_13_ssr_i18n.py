# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-13 (2026-05-23): SSR i18n for the SPA shell.

Pre-fix: the SPA's first paint was always English regardless of
Accept-Language. The data-i18n fallbacks ARE the EN strings
(``test_html_inline_fallback_matches_en_json`` locks this), and
the JS-side translator only swaps them after page load. Search
engines indexing the first paint always saw English, which
blocked German SEO entirely. Same story for ?lang=de URLs visited
in a non-JS context.

Post-fix: ``Handler.serve_static`` runs ``_ssr_translate_html``
on every HTML response. For ``lang='de'`` (or any non-EN locale
with a static/i18n/<lang>.json bundle), every simple
``<tag ... data-i18n="key" ...>fallback</tag>`` element gets its
text content swapped to the bundle value before the response
leaves the server. The document-level ``<html lang="en">`` is
rewritten to ``<html lang="de">`` so the locale matches.

The JS-side translator is unchanged — it re-applies the same
substitution after SPA boot, which is a no-op for already-
translated text. Round-trip is idempotent.
"""

from __future__ import annotations

import http.client
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


class SsrTranslatorUnit(unittest.TestCase):
    """Pure unit tests for the translator helper — no server needed."""

    def test_en_locale_is_a_passthrough(self) -> None:
        from app import _ssr_translate_html
        html = b'<html lang="en"><body><p data-i18n="x">Fallback</p></body></html>'
        self.assertEqual(_ssr_translate_html(html, "en"), html)

    def test_de_locale_translates_landing_headline(self) -> None:
        from app import _ssr_translate_html
        html = (
            '<html lang="en"><body>'
            '<h1 data-i18n="landing.headline">The job search the labor market wasn&rsquo;t built for.</h1>'
            "</body></html>"
        ).encode("utf-8")
        result = _ssr_translate_html(html, "de")
        text = result.decode("utf-8")
        # DE landing.headline from static/i18n/de.json should appear
        self.assertIn("Stellensuche", text)
        # English fallback removed
        self.assertNotIn("The job search the labor market", text)
        # Document lang rewritten
        self.assertIn('<html lang="de">', text)

    def test_unknown_locale_is_a_passthrough(self) -> None:
        from app import _ssr_translate_html
        html = b'<html lang="en"><body><p data-i18n="x">Fallback</p></body></html>'
        self.assertEqual(_ssr_translate_html(html, "fr"), html)

    def test_unknown_key_keeps_fallback(self) -> None:
        from app import _ssr_translate_html
        html = (
            b'<html lang="en"><body>'
            b'<p data-i18n="this.key.does.not.exist">Specific fallback text</p>'
            b'</body></html>'
        )
        result = _ssr_translate_html(html, "de")
        self.assertIn(b"Specific fallback text", result)

    def test_translation_is_html_escaped(self) -> None:
        # Add a temporary key with HTML metacharacters and verify
        # they're escaped in the rendered output. Use the cache
        # directly so we don't touch the real bundle on disk.
        import app
        app._LOCALE_BUNDLE_CACHE["xx-test"] = {"safety.test": "evil <script>alert(1)</script>"}
        try:
            html = (
                b'<html lang="en"><body>'
                b'<p data-i18n="safety.test">orig</p>'
                b'</body></html>'
            )
            result = app._ssr_translate_html(html, "xx-test")
            text = result.decode("utf-8")
            # Angle brackets escaped
            self.assertNotIn("<script>alert(1)</script>", text)
            self.assertIn("&lt;script&gt;", text)
        finally:
            app._LOCALE_BUNDLE_CACHE.pop("xx-test", None)


class SsrLiveResponse(unittest.TestCase):
    """End-to-end: real handler, real /index.html, real Accept-
    Language headers."""

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

    def test_de_accept_language_renders_german_landing(self) -> None:
        status, body = self._get("/", accept_language="de-DE,de;q=0.9")
        self.assertEqual(status, 200)
        # The hero headline DE: "Die Stellensuche, für die der
        # Arbeitsmarkt nicht gebaut wurde."
        self.assertIn("Stellensuche".encode("utf-8"), body)
        # English fallback must be GONE from the first-paint HTML
        self.assertNotIn(b"The job search the labor market wasn", body)
        # Document-level lang attribute switched
        self.assertIn(b'<html lang="de">', body)

    def test_en_accept_language_keeps_english_landing(self) -> None:
        status, body = self._get("/", accept_language="en-US,en;q=0.9")
        self.assertEqual(status, 200)
        self.assertIn(b"The job search the labor market", body)
        self.assertIn(b'<html lang="en">', body)
        self.assertNotIn("Stellensuche".encode("utf-8"), body)

    def test_lang_query_de_overrides_accept_language(self) -> None:
        status, body = self._get("/?lang=de", accept_language="en-US,en;q=0.9")
        self.assertEqual(status, 200)
        self.assertIn("Stellensuche".encode("utf-8"), body)
        self.assertIn(b'<html lang="de">', body)

    def test_persona_cards_translated_to_german(self) -> None:
        # AUDIT-33 added persona cards; AUDIT-13 ensures they SSR
        # to German for DE visitors.
        _status, body = self._get("/", accept_language="de")
        text = body.decode("utf-8")
        # DE for Aïcha card: contains "Krankenschwester"
        self.assertIn("Krankenschwester", text)
        # 2026-05-23 (UX-B3): the internal-jargon cohort labels
        # ("Akute Migranten-Kohorte" / "Erweiterte Friktions-Klasse")
        # were replaced with user-facing labels. The migrant five now
        # carry "Neueinwander:in · <sector>"; verify the DE bundle
        # value reaches the live SSR render.
        self.assertIn("Neueinwander:in", text)


if __name__ == "__main__":
    unittest.main()
