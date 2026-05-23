# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-R1 (2026-05-23, task #109): the persistent #chatDock is the
single canonical chat surface. The previously-redundant
#view-assistant section + sidebar Assistant nav-item are deleted.

Why this exists:
* Before: two parallel chat surfaces — the dock (always visible)
  and a full-page Assistant view in the sidebar. Every chat
  action wired to BOTH DOMs (chatTranscript vs dockChatTranscript,
  chatForm vs dockChatForm, etc.). i18n keys doubled. Maintenance
  trap. The Assistant view's placeholder copy was already stale.
* After: dock-only. ~200 LOC removed across HTML, CSS, JS, i18n.

This file locks the deletion in.
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


class ChatDockCanonicalSurface(unittest.TestCase):
    """Static-content checks — no server boot needed."""

    def setUp(self) -> None:
        self.index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.app_min_js = (ROOT / "static" / "app.min.js").read_text(encoding="utf-8")
        self.styles_css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.en_i18n = json.loads((ROOT / "static" / "i18n" / "en.json").read_text(encoding="utf-8"))
        self.de_i18n = json.loads((ROOT / "static" / "i18n" / "de.json").read_text(encoding="utf-8"))

    def test_view_assistant_section_is_removed(self) -> None:
        self.assertNotIn(
            'id="view-assistant"', self.index_html,
            "UX-R1 regression: <section id='view-assistant'> reappeared. "
            "The dock is canonical; do not add a second chat surface.",
        )

    def test_sidebar_assistant_nav_item_is_removed(self) -> None:
        self.assertNotIn(
            'data-view="assistant"', self.index_html,
            "UX-R1 regression: sidebar nav-item with data-view='assistant' "
            "reappeared. Do not add a separate Assistant page to the nav — "
            "the dock is always-on, not a destination.",
        )

    def test_duplicate_chat_dom_ids_are_removed(self) -> None:
        """The dock uses #dockChat* IDs. The deleted view used #chat*
        (without the 'dock' prefix). If those bare IDs reappear in
        the SPA shell, the dual-surface architecture is back."""

        # Exact-match container IDs that belonged to view-assistant.
        forbidden = [
            'id="chatTranscript"',
            'id="chatForm"',
            'id="chatInput"',
            'id="chatSendBtn"',
            'id="chatHelpBtn"',
            'id="chatResetBtn"',
            'id="chatPendingHint"',
        ]
        for needle in forbidden:
            with self.subTest(needle=needle):
                self.assertNotIn(
                    needle, self.index_html,
                    f"UX-R1 regression: {needle} reappeared in the SPA "
                    "shell. The dock-only architecture forbids this — "
                    "use the matching #dockChat* ID instead.",
                )

    def test_dock_remains_canonical_surface(self) -> None:
        """Sanity: confirm the dock is still wired up. If this fails,
        we accidentally deleted too much."""

        for needle in (
            'id="chatDock"',
            'id="dockChatTranscript"',
            'id="dockChatForm"',
            'id="dockChatInput"',
            'id="dockChatSendBtn"',
            'id="dockChatHelpBtn"',
            'id="dockChatResetBtn"',
            'id="dockChatPendingHint"',
        ):
            with self.subTest(needle=needle):
                self.assertIn(
                    needle, self.index_html,
                    f"Dock DOM disappeared: {needle}. "
                    "Re-check the deletion patch — too aggressive.",
                )

    def test_js_does_not_target_deleted_ids(self) -> None:
        """The JS source must not reference any of the deleted IDs."""

        forbidden_patterns = [
            '"#chatTranscript"',
            '"#chatForm"',
            '"#chatInput"',
            '"#chatSendBtn"',
            '"#chatHelpBtn"',
            '"#chatResetBtn"',
            '"#chatPendingHint"',
        ]
        for needle in forbidden_patterns:
            with self.subTest(needle=needle):
                self.assertNotIn(
                    needle, self.app_js,
                    f"UX-R1 regression: app.js still references {needle}. "
                    "The selector targets a DOM that no longer exists. "
                    "Use the matching #dockChat* selector.",
                )
                # Also check the minified bundle so a stale build can't
                # silently mask a regression.
                self.assertNotIn(
                    needle, self.app_min_js,
                    f"UX-R1 regression: app.min.js still references "
                    f"{needle}. Rebuild via scripts/build-static.sh.",
                )

    def test_view_titles_no_assistant_entry(self) -> None:
        """The VIEW_TITLES map shouldn't list 'assistant' as a
        navigable view anymore."""

        self.assertNotIn(
            "assistant: { title:", self.app_js,
            "UX-R1 regression: VIEW_TITLES still has an 'assistant' "
            "entry. There is no Assistant view; the dock is always-on.",
        )

    def test_i18n_nav_assistant_key_removed_from_both_bundles(self) -> None:
        self.assertNotIn(
            "nav.assistant", self.en_i18n,
            "UX-R1 regression: nav.assistant key reappeared in en.json. "
            "There is no Assistant nav item — drop the key.",
        )
        self.assertNotIn(
            "nav.assistant", self.de_i18n,
            "UX-R1 regression: nav.assistant key reappeared in de.json. "
            "There is no Assistant nav item — drop the key.",
        )

    def test_i18n_en_de_key_parity_preserved(self) -> None:
        en_keys = set(self.en_i18n.keys())
        de_keys = set(self.de_i18n.keys())
        self.assertSetEqual(
            en_keys, de_keys,
            f"i18n key parity broken after UX-R1 deletion. "
            f"EN-DE diff: {en_keys - de_keys!r}, "
            f"DE-EN diff: {de_keys - en_keys!r}.",
        )

    def test_dead_css_rules_removed(self) -> None:
        """The .chat-transcript / .chat-input / .chat-form-row /
        #chatForm / #chatInput CSS rules targeted the deleted DOM.
        They're now dead code; this guards against accidental
        re-introduction.

        We allow the rule NAMES to appear in comments (we left some
        explanatory comments behind), but reject any actual rule
        definitions."""

        import re as _re

        # ".chat-transcript {" with optional whitespace = a rule body.
        for needle, label in (
            (r"\.chat-transcript\s*\{", ".chat-transcript rule"),
            (r"\.chat-form-row\s*\{", ".chat-form-row rule"),
            (r"^\.chat-input\s*\{", ".chat-input rule"),
            (r"^#chatForm\s+", "#chatForm rule"),
            (r"^#chatInput\s*\{", "#chatInput rule"),
        ):
            with self.subTest(rule=label):
                self.assertIsNone(
                    _re.search(needle, self.styles_css, _re.MULTILINE),
                    f"UX-R1 regression: dead CSS rule for {label} "
                    f"is back in styles.css. It targets the deleted "
                    f"view-assistant DOM and serves no purpose.",
                )


class ChatDockRuntime(unittest.TestCase):
    """End-to-end: boot the server and confirm the dock-only SPA
    shell still validates as HTML and serves the chat surface."""

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

    def _get(self, path: str) -> bytes:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        try:
            return resp.read()
        finally:
            conn.close()

    def test_landing_serves_dock_not_view_assistant(self) -> None:
        body = self._get("/").decode("utf-8")
        self.assertIn('id="chatDock"', body,
                      "Live SPA shell missing #chatDock — the dock is "
                      "the canonical chat surface.")
        self.assertNotIn('id="view-assistant"', body,
                         "Live SPA shell still serves the deleted "
                         "view-assistant section.")


if __name__ == "__main__":
    unittest.main()
