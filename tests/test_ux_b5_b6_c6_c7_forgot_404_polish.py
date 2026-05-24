# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-B5 / B6 / C6 / C7 (2026-05-23, tasks #67/#68/#79/#80):

* B5: 404 page copy — dropped the apologetic "(any more)" /
  "(mehr)" parenthetical in both EN and DE leads.

* B6 + C7: audit re-verification. The forgot-password page already
  had a non-duplicated lead + a wired post-submit success state
  ("If a matching account exists, a reset link has been sent.
  Check your inbox (and spam folder)…"). Closed by re-verification —
  no change required, but lock in the contract here.

* C6: surface the rate-limit policy below the forgot-password
  form ("up to 5 reset emails every 10 minutes from one network")
  on both EN and DE pages, so users retrying repeatedly aren't
  confused by silence.
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


class ForgotAnd404Polish(unittest.TestCase):
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

    def _get(self, path: str) -> tuple[int, str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        try:
            return resp.status, resp.read().decode("utf-8")
        finally:
            conn.close()

    def test_b5_404_en_no_any_more_parenthetical(self) -> None:
        status, body = self._get("/this-url-does-not-exist")
        self.assertEqual(status, 404)
        self.assertNotIn(
            "(any more)",
            body,
            "UX-B5 regression: apologetic '(any more)' parenthetical is back on the EN 404 page.",
        )

    def test_b5_404_de_no_mehr_parenthetical(self) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/this-url-does-not-exist", headers={"Accept-Language": "de"})
        resp = conn.getresponse()
        status, body = resp.status, resp.read().decode("utf-8")
        conn.close()
        self.assertEqual(status, 404)
        self.assertNotIn(
            "(mehr)",
            body,
            "UX-B5 regression: apologetic '(mehr)' parenthetical is back on the DE 404 page.",
        )

    def test_c6_en_rate_limit_hint_present(self) -> None:
        _status, body = self._get("/forgot-password")
        self.assertIn(
            "5 reset emails every 10 minutes",
            body,
            "UX-C6 regression: rate-limit hint missing from EN "
            "forgot-password page. Users retrying repeatedly need "
            "to know why they're being silently rate-limited.",
        )

    def test_c6_de_rate_limit_hint_present(self) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/forgot-password", headers={"Accept-Language": "de"})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()
        self.assertIn(
            "5 Reset-E-Mails pro 10 Minuten",
            body,
            "UX-C6 regression: rate-limit hint missing from DE forgot-password page.",
        )

    def test_c7_post_submit_success_copy_wired(self) -> None:
        """The post-submit success message is set by JS from the
        form's data-msg-sent attribute. Re-verify the attribute
        carries the contract-required copy."""

        _status, body = self._get("/forgot-password")
        self.assertIn(
            "If a matching account exists, a reset link has been sent.",
            body,
            "UX-C7 regression: post-submit success state copy missing "
            "from EN forgot-password page. Required: must not leak "
            "whether email exists; must give the user a useful next "
            "step (check inbox + spam).",
        )


if __name__ == "__main__":
    unittest.main()
