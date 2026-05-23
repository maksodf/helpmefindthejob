# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAP-11 (post-self-audit, 2026-05-23): accessibility audit on the
pages this session introduced or rebuilt.

axe-core / Lighthouse a11y are the authoritative validators, but we
can't run a real browser from this environment. This file enforces
the structural a11y invariants that those tools check for, on every
page surface we touched:

* ``forgot-password.html`` / ``forgot-password.de.html`` (AUDIT-26)
* The 403 ``Admin access required`` page (GAP-3)
* The injected site-wide footer (AUDIT-34 / GAP-1+2)

For each surface:
* Single ``<h1>`` (WCAG 2.4.6 — headings convey structure).
* ``<html lang="…">`` declared.
* ``<title>`` non-empty.
* ``<meta name="viewport">`` declared.
* Every ``<input>`` has an associated ``<label for="…">``.
* Every ``<input required>`` carries ``aria-required="true"``
  (belt-and-braces — some screen readers ignore the HTML5 attribute).
* Skip-link present.
* No inline event handlers (``onclick=`` / ``onload=`` etc.) — CSP
  would block them anyway, but a clean source is the contract.
* Every ``<a>`` has an ``href``.
* The injected footer has ``role="contentinfo"`` and ``aria-label``.
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
STATIC = ROOT / "static"


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


# Inline event handlers banned by CSP; this list covers the common ones
_INLINE_HANDLER_RX = re.compile(
    r'\son(click|load|submit|change|focus|blur|mouseover|mouseout|keydown|keyup|keypress|input|error)=',
    re.IGNORECASE,
)


def _audit_html(html: str, source_name: str, testcase: unittest.TestCase) -> None:
    """Run the shared structural-a11y checks against a piece of HTML."""

    # 1. lang attribute
    testcase.assertIsNotNone(
        re.search(r'<html\s+lang="[a-z]{2}"', html),
        f"{source_name}: <html> must declare lang attribute",
    )

    # 2. Single h1
    h1_count = html.count("<h1")
    testcase.assertEqual(
        h1_count, 1,
        f"{source_name}: must have exactly one <h1>, found {h1_count}",
    )

    # 3. Non-empty title
    title_match = re.search(r"<title>([^<]+)</title>", html)
    testcase.assertIsNotNone(title_match, f"{source_name}: <title> missing")
    testcase.assertTrue(
        len(title_match.group(1).strip()) >= 3,
        f"{source_name}: <title> too short",
    )

    # 4. viewport meta
    testcase.assertIsNotNone(
        re.search(r'<meta name="viewport"', html),
        f"{source_name}: missing viewport meta",
    )

    # 5. Every <input> has an associated label OR aria-label
    for input_match in re.finditer(r'<input\s+([^>]*?)/?>', html):
        attrs = input_match.group(1)
        input_id_match = re.search(r'\bid="([^"]+)"', attrs)
        input_type_match = re.search(r'\btype="([^"]+)"', attrs)
        if input_type_match and input_type_match.group(1) in {"hidden", "submit", "button"}:
            continue
        if input_id_match:
            input_id = input_id_match.group(1)
            has_label = re.search(
                rf'<label[^>]*\sfor="{re.escape(input_id)}"', html
            )
            has_aria_label = 'aria-label="' in attrs or 'aria-labelledby="' in attrs
            testcase.assertTrue(
                has_label or has_aria_label,
                f"{source_name}: <input id={input_id!r}> has no <label for=…> "
                "and no aria-label",
            )
            # Required inputs must also have aria-required (defense)
            if "required" in attrs:
                testcase.assertIn(
                    'aria-required="true"', attrs,
                    f"{source_name}: required <input id={input_id!r}> missing "
                    "aria-required=true (HTML5 required attribute alone isn't "
                    "consistently announced by screen readers)",
                )

    # 6. No inline event handlers (CSP-required)
    match = _INLINE_HANDLER_RX.search(html)
    if match:
        # Show context for the failure
        context = html[max(0, match.start() - 30):match.end() + 30]
        testcase.fail(
            f"{source_name}: inline event handler found: ...{context}... "
            "CSP would block these even if they worked."
        )

    # 7. Every <a> has an href
    for anchor_match in re.finditer(r"<a(\s+[^>]*?)>", html):
        attrs = anchor_match.group(1)
        if 'href="' not in attrs:
            testcase.fail(
                f"{source_name}: <a> without href: <a{attrs}>"
            )

    # 8. Skip-link present (WCAG 2.4.1 bypass blocks)
    testcase.assertIn(
        'class="skip-link"', html,
        f"{source_name}: missing skip-link (WCAG 2.4.1)",
    )


class ForgotPasswordPageA11y(unittest.TestCase):
    """Static analysis of the dedicated forgot-password pages."""

    def test_en_page_passes_structural_a11y_checks(self) -> None:
        html = (STATIC / "forgot-password.html").read_text(encoding="utf-8")
        _audit_html(html, "static/forgot-password.html", self)

    def test_de_page_passes_structural_a11y_checks(self) -> None:
        html = (STATIC / "forgot-password.de.html").read_text(encoding="utf-8")
        _audit_html(html, "static/forgot-password.de.html", self)


class LiveSurfacesA11y(unittest.TestCase):
    """Run the same checks against pages that only exist post-injection
    (footer, 403 page) — these aren't static files, so we have to
    fetch them from a live server."""

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

    def _get(self, path: str, headers: dict | None = None) -> tuple[int, str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, resp.read().decode("utf-8")
        finally:
            conn.close()

    def test_forgot_password_live_response_passes_a11y(self) -> None:
        status, html = self._get("/forgot-password")
        self.assertEqual(status, 200)
        _audit_html(html, "/forgot-password (live)", self)

    def test_footer_carries_required_aria(self) -> None:
        status, html = self._get("/privacy")
        self.assertEqual(status, 200)
        # Extract just the footer
        footer_match = re.search(
            r'<footer[^>]*class="site-footer"[^>]*>(.*?)</footer>',
            html, re.DOTALL,
        )
        self.assertIsNotNone(footer_match)
        footer_tag = re.search(r'<footer[^>]*class="site-footer"[^>]*>', html).group(0)
        self.assertIn('role="contentinfo"', footer_tag,
                      "site-footer must declare role=contentinfo")
        self.assertIn('aria-label="', footer_tag,
                      "site-footer must carry an aria-label")
        # Lang switcher must mark current language
        self.assertIn('aria-current="true"', footer_match.group(1))

    def test_admin_403_page_passes_a11y(self) -> None:
        # We can't easily get a logged-in non-admin in this isolated
        # test (would need to register + login), so we read the body
        # via a slightly different path: register first to bootstrap,
        # then re-register a non-admin via the admin invite path.
        # Since GAP-3 already covers the integration, this test just
        # checks the structural-a11y invariants of a manually-rendered
        # version of the page by calling the helper through a stub.
        # Skip if the helper isn't directly invocable.
        import importlib, sys as _sys
        if "app" in _sys.modules:
            app = _sys.modules["app"]
        else:
            app = importlib.import_module("app")
        # Build a Handler with the minimum surface and call the helper
        # to capture its output.
        from io import BytesIO
        class _Capture:
            def __init__(self):
                self.headers_sent = []
                self.body = BytesIO()
                self.status = None
            def send_response(self, status):
                self.status = status
            def send_header(self, k, v):
                self.headers_sent.append((k, v))
            def end_headers(self):
                pass
            @property
            def wfile(self):
                return self.body
            def _resolve_user_language(self):
                return "en"
            # Bind the method-under-test to this object so it can use
            # the stubbed helpers.
            _send_admin_forbidden_page = app.Handler._send_admin_forbidden_page

        cap = _Capture()
        cap.headers = {}  # ensure .headers attribute exists for Cookie lookup
        cap._send_admin_forbidden_page()
        rendered = cap.body.getvalue().decode("utf-8")
        self.assertEqual(cap.status, 403)
        _audit_html(rendered, "admin-403 page (rendered)", self)


if __name__ == "__main__":
    unittest.main()
