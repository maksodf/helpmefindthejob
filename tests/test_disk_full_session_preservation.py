# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #78 top-tier upgrade item 4 — Case B (disk-full) sessionStorage
preservation contract.

The Case B friendly message in :mod:`company_discovery.db_errors`
says "Your work is preserved in this session — try again in a few
minutes". This file pins both halves of that contract:

1. The backend Case B error envelope shape (code=db_disk_full +
   the friendly message) — verified via the public
   ``format_user_message`` + ``http_status_for`` helpers.
2. The frontend ``preservePendingWrite`` /
   ``getPendingDiskFullWrites`` / ``clearPendingDiskFullWrites``
   contract — verified by extracting the three helpers from
   ``static/app.js`` and running them under a stubbed
   ``sessionStorage`` shim.

The frontend half uses a Node-style sandboxed eval — no real
browser, no Playwright dependency on this test path. It's a unit-
level contract guard; the end-to-end smoke is exercised by the
existing journey browser-smoke when a real disk-full surfaces.
"""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from company_discovery.db_errors import (
    ERR_DISK_FULL,
    classify_db_error,
    format_user_message,
    http_status_for,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
APP_JS = REPO_ROOT / "static" / "app.js"


def _extract_preserve_helpers() -> str:
    """Return the three Case B helper functions as a self-contained
    JS snippet. Hand-extracted by regex against ``static/app.js``
    so the test breaks loudly if any of the three is renamed."""
    source = APP_JS.read_text(encoding="utf-8")
    snippets: list[str] = []
    # The three functions are declared at module scope as
    # ``function name(...) { ... }``. Match each one's full body.
    for name in ("preservePendingWrite", "getPendingDiskFullWrites", "clearPendingDiskFullWrites"):
        match = re.search(
            r"^function " + re.escape(name) + r"\([^)]*\)\s*\{",
            source,
            re.MULTILINE,
        )
        if not match:
            raise RuntimeError(f"Could not locate function {name} in static/app.js")
        # Walk braces from match.end() - 1 to find the matching close.
        i = match.end() - 1  # at the opening brace
        depth = 0
        end = i
        while end < len(source):
            ch = source[end]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end += 1
                    break
            end += 1
        snippets.append(source[match.start():end])
    # Also pull out the storage-key constant
    key_match = re.search(
        r'const\s+_PENDING_WRITES_KEY\s*=\s*"[^"]+";', source
    )
    if not key_match:
        raise RuntimeError("Could not locate _PENDING_WRITES_KEY constant in static/app.js")
    return key_match.group(0) + "\n" + "\n".join(snippets)


class CaseBBackendContract(unittest.TestCase):
    def test_disk_full_classification_returns_known_code(self) -> None:
        import sqlite3

        # The sqlite OperationalError surface that maps to disk-full
        err = sqlite3.OperationalError("database or disk is full")
        self.assertEqual(classify_db_error(err), ERR_DISK_FULL)

    def test_disk_full_http_status_is_507(self) -> None:
        # 507 Insufficient Storage is the correct semantic for Case B
        # (vs 503 Service Unavailable for transient lock-busy).
        self.assertEqual(http_status_for(ERR_DISK_FULL), 507)

    def test_disk_full_message_en_promises_session_preservation(self) -> None:
        msg = format_user_message(ERR_DISK_FULL, locale="en")
        self.assertIn("preserved", msg.lower())
        self.assertIn("session", msg.lower())

    def test_disk_full_message_de_promises_session_preservation(self) -> None:
        msg = format_user_message(ERR_DISK_FULL, locale="de")
        # "in dieser Sitzung erhalten" is the DE half of the promise
        self.assertIn("Sitzung", msg)


class CaseBFrontendContract(unittest.TestCase):
    """Verifies the three sessionStorage helpers in static/app.js
    actually deliver the promise the backend message makes.

    Strategy: extract the three function bodies, plus the key
    constant, and exec them inside a Node interpreter against a
    stubbed sessionStorage shim. No browser needed.
    """

    @classmethod
    def setUpClass(cls) -> None:
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise unittest.SkipTest("node not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise unittest.SkipTest("node not available")
        cls.helpers_js = _extract_preserve_helpers()

    def _run_node(self, body: str) -> dict:
        prelude = (
            "const __store = {};\n"
            "global.sessionStorage = {\n"
            "  getItem: (k) => (k in __store ? __store[k] : null),\n"
            "  setItem: (k, v) => { __store[k] = String(v); },\n"
            "  removeItem: (k) => { delete __store[k]; },\n"
            "};\n"
            "global.window = {};\n"
        )
        prog = prelude + self.helpers_js + "\n" + body
        result = subprocess.run(
            ["node", "-e", prog],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"Node exited {result.returncode}; stderr:\n{result.stderr}"
            )
        return json.loads(result.stdout or "{}")

    def test_preserve_writes_appears_in_get(self) -> None:
        out = self._run_node(
            'preservePendingWrite("/api/profile", "PATCH", JSON.stringify({a: 1}));\n'
            "const q = getPendingDiskFullWrites();\n"
            "process.stdout.write(JSON.stringify({len: q.length, path: q[0].path, method: q[0].method, body: q[0].body}));\n"
        )
        self.assertEqual(out["len"], 1)
        self.assertEqual(out["path"], "/api/profile")
        self.assertEqual(out["method"], "PATCH")
        self.assertEqual(json.loads(out["body"]), {"a": 1})

    def test_preserve_skips_get_requests(self) -> None:
        out = self._run_node(
            'preservePendingWrite("/api/health", "GET", null);\n'
            "process.stdout.write(JSON.stringify({len: getPendingDiskFullWrites().length}));\n"
        )
        self.assertEqual(out["len"], 0)

    def test_preserve_caps_queue_at_20(self) -> None:
        out = self._run_node(
            "for (let i = 0; i < 25; i++) {\n"
            '  preservePendingWrite("/api/x", "POST", JSON.stringify({i}));\n'
            "}\n"
            "const q = getPendingDiskFullWrites();\n"
            "process.stdout.write(JSON.stringify({len: q.length, firstBody: q[0].body, lastBody: q[q.length-1].body}));\n"
        )
        self.assertEqual(out["len"], 20)
        # The first 5 should have been dropped (most recent 20 kept)
        self.assertEqual(json.loads(out["firstBody"]), {"i": 5})
        self.assertEqual(json.loads(out["lastBody"]), {"i": 24})

    def test_clear_empties_the_queue(self) -> None:
        out = self._run_node(
            'preservePendingWrite("/api/x", "POST", "{}");\n'
            'preservePendingWrite("/api/y", "POST", "{}");\n'
            "clearPendingDiskFullWrites();\n"
            "process.stdout.write(JSON.stringify({len: getPendingDiskFullWrites().length}));\n"
        )
        self.assertEqual(out["len"], 0)

    def test_preserve_handles_non_json_string_body(self) -> None:
        out = self._run_node(
            'preservePendingWrite("/api/raw", "POST", "raw-text-body");\n'
            "const q = getPendingDiskFullWrites();\n"
            "process.stdout.write(JSON.stringify({len: q.length, body: q[0].body}));\n"
        )
        self.assertEqual(out["len"], 1)
        self.assertEqual(out["body"], "raw-text-body")

    def test_preserve_skips_null_and_undefined_body(self) -> None:
        out = self._run_node(
            'preservePendingWrite("/api/x", "POST", null);\n'
            'preservePendingWrite("/api/x", "POST", undefined);\n'
            "process.stdout.write(JSON.stringify({len: getPendingDiskFullWrites().length}));\n"
        )
        self.assertEqual(out["len"], 0)


if __name__ == "__main__":
    unittest.main()
