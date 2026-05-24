# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-B9 (2026-05-23, task #71): the DE landing must NOT leak
English. Pre-fix:

* The topbar <h2 id="viewTitle">Today</h2> + <p id="viewSubtitle">
  were hardcoded English with no data-i18n attribute — visible as a
  flash before JS hydration and to crawlers indexing the first paint.
* The dock chat input's placeholder + aria-label and the send
  button's aria-label were English-only attribute values. The
  SSR pipeline only translated TEXT content, not ATTRIBUTE values,
  so these stayed English even with data-i18n-placeholder hints.

Fix (architectural — not patch):

1. SSR translator extended to handle attribute values too. New
   pattern: an element carrying ``attr="english"`` AND
   ``data-i18n-attr="bundle.key"`` gets the attr value swapped
   to the bundle entry. Supported attrs: placeholder, aria-label,
   title.
2. viewTitle / viewSubtitle annotated with data-i18n keys.
3. Dock chat input + form + send button annotated with
   data-i18n-placeholder / data-i18n-aria-label / data-i18n-title.
4. New bundle keys: dock.chat.placeholder / dock.chat.form /
   dock.chat.input / dock.chat.send (en + de).

This file is the regression guard.
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


class DELandingNoEnglishLeaks(unittest.TestCase):
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

    def _get_de(self) -> str:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=4)
        conn.request("GET", "/?lang=de")
        resp = conn.getresponse()
        try:
            return resp.read().decode("utf-8")
        finally:
            conn.close()

    def test_view_title_translated_in_de(self) -> None:
        body = self._get_de()
        # The DE bundle has view.dashboard.title = "Heute" (matches
        # the sidebar nav.dashboard wording — both surfaces use the
        # same word). The English fallback "Today" must NOT appear
        # as the rendered text inside the viewTitle element.
        self.assertNotIn(
            '<h2 id="viewTitle" data-i18n="view.dashboard.title">Today</h2>',
            body,
            "UX-B9 regression: viewTitle still shows English 'Today' "
            "on /?lang=de. SSR translator broken.",
        )
        # And the DE value should be present.
        self.assertIn(
            ">Heute<",
            body,
            "DE viewTitle 'Heute' missing from SSR render.",
        )

    def test_view_subtitle_translated_in_de(self) -> None:
        body = self._get_de()
        # Should NOT contain the EN fallback as the actual rendered value
        self.assertNotIn(
            "Your watched companies, recent runs, and what to do next.",
            body,
            "UX-B9 regression: viewSubtitle still shows English on DE.",
        )

    def test_dock_chat_placeholder_translated_in_de(self) -> None:
        body = self._get_de()
        self.assertNotIn(
            'placeholder="Type what you want to do…"',
            body,
            "UX-B9 regression: dock chat placeholder still English on DE. "
            "The SSR attribute-translation pass must run.",
        )
        # DE value present.
        self.assertIn(
            "Sag mir, was du tun willst",
            body,
            "DE dock placeholder missing from SSR render.",
        )

    def test_dock_chat_aria_labels_translated_in_de(self) -> None:
        body = self._get_de()
        # Specifically reject these three EN aria-labels.
        for english in (
            'aria-label="Quick chat (docked)"',
            'aria-label="Chat message"',
            'aria-label="Send"',
        ):
            with self.subTest(english=english):
                self.assertNotIn(
                    english,
                    body,
                    f"UX-B9 regression: {english} still English on DE.",
                )

    def test_en_landing_still_renders_english(self) -> None:
        """Sanity: don't accidentally translate EN to anything else."""

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=4)
        conn.request("GET", "/?lang=en")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()

        self.assertIn(
            "Your watched companies, recent runs, and what to do next.",
            body,
            "EN landing lost its viewSubtitle text — SSR broke EN render.",
        )

    def test_i18n_dock_chat_keys_in_both_bundles(self) -> None:
        en = json.loads((ROOT / "static" / "i18n" / "en.json").read_text(encoding="utf-8"))
        de = json.loads((ROOT / "static" / "i18n" / "de.json").read_text(encoding="utf-8"))
        for key in ("dock.chat.placeholder", "dock.chat.form", "dock.chat.input", "dock.chat.send"):
            with self.subTest(key=key):
                self.assertIn(key, en, f"{key} missing from en.json")
                self.assertIn(key, de, f"{key} missing from de.json")


if __name__ == "__main__":
    unittest.main()
