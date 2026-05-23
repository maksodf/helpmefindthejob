# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-26 — /forgot-password is a minimal dedicated page, not the SPA.

The historical behaviour: GET /forgot-password served the full 103 KB
index.html SPA shell, then the SPA's client-side router showed the
forgotPasswordView. Cold-loading 100 KB of JS+HTML to render a single
email field is a UX regression, particularly on mobile or a poor
connection where the password-reset path is most-needed.

After AUDIT-26: /forgot-password serves a dedicated bilingual page
(EN canonical + DE courtesy translation) of roughly 3 KB that posts
to the same /api/auth/forgot-password endpoint via a small dedicated
JS file. This test file pins the new behaviour:

* The response body is under 20 KB (vs the 103 KB SPA shell).
* The response is the dedicated page, not the SPA shell — checked via
  positive markers (``forgotPasswordForm``) AND negative markers
  (``appShell``, ``authGate``, ``primaryNav`` from the SPA chrome
  must not appear).
* Language resolution honours ?lang=de, ?lang=en, and Accept-Language.
* Both ``forgot-password.html`` and ``forgot-password.de.html`` exist
  on disk and the supporting JS is reachable.
* CSP-compliant: the page contains zero inline <script> blocks.
* The token-bound SPA routes (/accept-invite, /reset-password) still
  fall through to the SPA shell — AUDIT-27 covers those separately.
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
STATIC = ROOT / "static"

_MAX_PAGE_BYTES = 20_000  # SPA shell is ~103 KB; dedicated page is ~3 KB
_FORBIDDEN_SPA_MARKERS = ("appShell", "authGate", "primaryNav", "id=\"app\"")
_REQUIRED_FORM_MARKERS = ("forgotPasswordForm", "forgotEmail", "forgot-password.js")


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class ForgotPasswordStaticFilesPresent(unittest.TestCase):
    """Both bilingual files + the shared JS must exist on disk."""

    def test_en_file_exists(self) -> None:
        path = STATIC / "forgot-password.html"
        self.assertTrue(path.is_file(), f"missing {path}")
        size = path.stat().st_size
        self.assertLess(
            size, 10_000,
            f"AUDIT-26: EN forgot-password.html grew to {size} bytes; "
            "should stay tiny (target < 5 KB).",
        )

    def test_de_file_exists(self) -> None:
        path = STATIC / "forgot-password.de.html"
        self.assertTrue(path.is_file(), f"missing {path}")
        size = path.stat().st_size
        self.assertLess(
            size, 10_000,
            f"AUDIT-26: DE forgot-password.de.html grew to {size} bytes; "
            "should stay tiny (target < 5 KB).",
        )

    def test_shared_js_exists(self) -> None:
        path = STATIC / "forgot-password.js"
        self.assertTrue(path.is_file(), f"missing {path}")
        size = path.stat().st_size
        self.assertLess(
            size, 5_000,
            f"AUDIT-26: forgot-password.js grew to {size} bytes; "
            "should stay tiny (target < 3 KB).",
        )

    def test_en_page_has_required_markers_and_no_inline_script(self) -> None:
        src = (STATIC / "forgot-password.html").read_text(encoding="utf-8")
        for marker in _REQUIRED_FORM_MARKERS:
            self.assertIn(marker, src, f"AUDIT-26 EN page missing {marker!r}")
        for marker in _FORBIDDEN_SPA_MARKERS:
            self.assertNotIn(
                marker, src,
                f"AUDIT-26: EN page should not carry SPA-shell marker {marker!r}",
            )
        # CSP says script-src 'self' — no inline executable <script>
        # blocks allowed. External <script src="..."> is fine. Data
        # blocks like <script type="application/ld+json"> are JSON
        # (not JavaScript) and CSP does not block them per the spec
        # (browsers don't execute non-JS script types).
        for line in src.splitlines():
            stripped = line.strip()
            if not stripped.startswith("<script"):
                continue
            if "src=" in stripped:
                continue
            if 'type="application/ld+json"' in stripped or 'type="application/json"' in stripped:
                continue
            self.fail(
                f"AUDIT-26: inline executable <script> block found in EN page: "
                f"{stripped!r}. CSP forbids inline scripts; use external "
                "src= instead. (JSON-LD data blocks are exempt.)"
            )

    def test_de_page_has_required_markers_and_german_strings(self) -> None:
        src = (STATIC / "forgot-password.de.html").read_text(encoding="utf-8")
        for marker in _REQUIRED_FORM_MARKERS:
            self.assertIn(marker, src, f"AUDIT-26 DE page missing {marker!r}")
        # German UI strings — these are the strongest signal we're
        # serving the right localisation, not just a duplicate of EN.
        for de_phrase in ("Passwort vergessen", "Reset-Link senden", "Zur"):
            self.assertIn(
                de_phrase, src,
                f"AUDIT-26: DE page missing expected German phrase {de_phrase!r}",
            )
        # lang attribute must be 'de'
        self.assertIn('<html lang="de">', src, "DE page must declare lang='de'")


class ForgotPasswordBilingualRouting(unittest.TestCase):
    """Handler routing maps /forgot-password to the right bilingual file."""

    def test_forgot_password_is_in_bilingual_pages(self) -> None:
        from app import Handler
        self.assertIn(
            "/forgot-password",
            Handler._BILINGUAL_PAGES,
            "AUDIT-26: /forgot-password must be registered in _BILINGUAL_PAGES "
            "so serve_static routes by language.",
        )

    def test_forgot_password_not_in_spa_routes(self) -> None:
        # spa_routes is a local variable inside serve_static(), so we test
        # the observable behaviour indirectly via _bilingual_page_path.
        from app import Handler
        self.assertEqual(
            Handler._bilingual_page_path(None, "/forgot-password", "en"),
            "/forgot-password",
            "EN /forgot-password should map to /forgot-password (then .html fallback)",
        )
        self.assertEqual(
            Handler._bilingual_page_path(None, "/forgot-password", "de"),
            "/forgot-password.de",
            "DE /forgot-password should map to /forgot-password.de (then .html fallback)",
        )


class ForgotPasswordLiveResponse(unittest.TestCase):
    """End-to-end: boot the real handler, request /forgot-password under
    several language signals, verify each returns the right small page."""

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
                except Exception:  # noqa: BLE001 — best-effort cleanup
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

    def _get(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        try:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.getheaders()), body
        finally:
            conn.close()

    def test_default_serves_en_minimal_page(self) -> None:
        status, _headers, body = self._get("/forgot-password")
        self.assertEqual(status, 200)
        self.assertLess(
            len(body), _MAX_PAGE_BYTES,
            f"AUDIT-26: /forgot-password body grew to {len(body)} bytes; "
            f"should stay under {_MAX_PAGE_BYTES} (vs ~103 KB SPA shell).",
        )
        self.assertIn("Forgot your password?", body)
        for marker in _FORBIDDEN_SPA_MARKERS:
            self.assertNotIn(
                marker, body,
                f"AUDIT-26: default /forgot-password served the SPA shell "
                f"(saw {marker!r}). Should serve forgot-password.html.",
            )

    def test_lang_de_query_serves_de_page(self) -> None:
        status, _headers, body = self._get("/forgot-password?lang=de")
        self.assertEqual(status, 200)
        self.assertIn("Passwort vergessen", body)
        self.assertIn('<html lang="de">', body)
        self.assertNotIn("Forgot your password?", body)

    def test_lang_en_query_serves_en_page(self) -> None:
        status, _headers, body = self._get("/forgot-password?lang=en")
        self.assertEqual(status, 200)
        self.assertIn("Forgot your password?", body)
        self.assertNotIn("Passwort vergessen", body)

    def test_accept_language_de_serves_de_page(self) -> None:
        status, _headers, body = self._get(
            "/forgot-password", headers={"Accept-Language": "de-DE,de;q=0.9,en;q=0.5"}
        )
        self.assertEqual(status, 200)
        self.assertIn("Passwort vergessen", body)

    def test_shared_js_is_reachable(self) -> None:
        status, _headers, body = self._get("/forgot-password.js")
        self.assertEqual(status, 200, "AUDIT-26: forgot-password.js must be served as a static asset")
        self.assertIn("forgotPasswordForm", body)
        self.assertIn("/api/auth/forgot-password", body)

    def test_spa_aux_routes_still_fall_through_to_shell(self) -> None:
        # AUDIT-26 only extracted /forgot-password; /reset-password and
        # /accept-invite (query-token form) must keep serving the SPA
        # shell so the existing token flows keep working. The path-token
        # form (/reset-password/<token>) is broken pre-AUDIT-27 and gets
        # fixed there, so we deliberately do NOT exercise it here.
        for route in ("/reset-password", "/accept-invite"):
            status, _headers, body = self._get(route)
            self.assertEqual(status, 200, f"{route} should serve SPA shell, got {status}")
            self.assertGreater(
                len(body), 50_000,
                f"AUDIT-26 invariant: {route} should still be the ~103 KB SPA "
                "shell until AUDIT-27 extracts dedicated pages.",
            )


if __name__ == "__main__":
    unittest.main()
