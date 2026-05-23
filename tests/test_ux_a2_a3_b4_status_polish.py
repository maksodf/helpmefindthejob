# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-A2 + A3 + B4 (2026-05-23, tasks #54/#55/#66): /status polish.

* A2: the Storage card was deleted. AUDIT-42 (2026-05-22) intentionally
  stripped `storage` from public /api/health, so the card always
  showed an em-dash placeholder — looked like the feature was broken.

* A3: the response-time-trend "—" empty state was replaced with real
  copy ("Not enough data yet — check back in a minute.") rendered
  in the SSR HTML, and the JS no longer overwrites it on each tick
  while the buffer is empty.

* B4: the public-facing copy was de-internalized. Removed the
  operator-launch-runbook.md reference and the "Polled directly
  from the running app every 30 seconds. No third-party uptime
  vendor." wording — the latter was an internal operator note,
  not user-facing copy.
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


class StatusPagePolish(unittest.TestCase):

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

    def _get(self, path: str) -> str:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        try:
            return resp.read().decode("utf-8")
        finally:
            conn.close()

    def test_a2_storage_card_removed(self) -> None:
        body = self._get("/status")
        # No #appStorage element, no "Storage" card label.
        self.assertNotIn(
            'id="appStorage"', body,
            "UX-A2 regression: #appStorage card reappeared on /status. "
            "/api/health no longer exposes storage publicly (AUDIT-42), "
            "so this card always shows em-dash. Keep it deleted.",
        )

    def test_a3_latency_empty_state_copy_in_ssr(self) -> None:
        body = self._get("/status")
        self.assertIn(
            "Not enough data yet", body,
            "UX-A3 regression: latency-trend empty-state copy missing. "
            "An em-dash placeholder makes the feature look broken; "
            "render real copy when the buffer is empty.",
        )

    def test_a3_latency_stats_helpful_default(self) -> None:
        body = self._get("/status")
        self.assertIn(
            "min / p50 / p95 / max",
            body,
            "UX-A3 regression: latency-stats default copy missing. "
            "Tell the user what they'll see once data accumulates.",
        )

    def test_b4_no_internal_operator_runbook_reference(self) -> None:
        body = self._get("/status")
        self.assertNotIn(
            "operator-launch-runbook.md", body,
            "UX-B4 regression: internal operator-runbook reference is "
            "back on the public /status page. Public pages must not "
            "leak internal-only file paths.",
        )

    def test_b4_no_third_party_vendor_internal_phrasing(self) -> None:
        body = self._get("/status")
        # The pre-fix line was: "Polled directly from the running app
        # every 30 seconds. No third-party uptime vendor." — written
        # for ops/operators, not end-users.
        self.assertNotIn(
            "third-party uptime vendor", body,
            "UX-B4 regression: operator-internal phrasing about uptime "
            "vendors is back on the public /status page.",
        )


if __name__ == "__main__":
    unittest.main()
