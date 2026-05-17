# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Privacy-friendly analytics config (Phase 7 tracker item #60).

The public ``GET /api/site-config`` endpoint returns the operator-set
analytics URL + domain. When unset, both fields are ``None`` and the
frontend ships zero third-party requests (the documented default).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding blocked") from error
        return int(sock.getsockname()[1])


class SiteConfigEndpointTests(unittest.TestCase):
    def _spawn(self, env_extra: dict[str, str]) -> tuple[subprocess.Popen, str]:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        port = _free_port()
        env = {
            **os.environ,
            "COMPANY_DISCOVERY_DATA_DIR": tmp.name,
            "COMPANY_DISCOVERY_ENV": "development",
            **env_extra,
        }
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(port)],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.addCleanup(self._terminate, proc)
        base = f"http://127.0.0.1:{port}"
        for _ in range(40):
            try:
                with urlopen(f"{base}/api/health", timeout=0.5) as response:
                    if response.getcode() == 200:
                        return proc, base
            except OSError:
                time.sleep(0.1)
        self.fail("server did not start")

    def _terminate(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    def _get_site_config(self, base: str) -> dict:
        try:
            with urlopen(f"{base}/api/site-config", timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return json.loads(error.read().decode("utf-8") or "{}")

    def test_unset_returns_nulls(self) -> None:
        # Make sure no env vars from the test runner leak in.
        env_extra = {
            "DIRECTJOB_ANALYTICS_SCRIPT_URL": "",
            "DIRECTJOB_ANALYTICS_DOMAIN": "",
        }
        _, base = self._spawn(env_extra)
        cfg = self._get_site_config(base)
        self.assertIsNone(cfg["analytics"]["scriptUrl"])
        self.assertIsNone(cfg["analytics"]["domain"])

    def test_set_returns_values(self) -> None:
        env_extra = {
            "DIRECTJOB_ANALYTICS_SCRIPT_URL": "https://analytics.khalo.org/js/script.js",
            "DIRECTJOB_ANALYTICS_DOMAIN": "khalo.org",
        }
        _, base = self._spawn(env_extra)
        cfg = self._get_site_config(base)
        self.assertEqual(cfg["analytics"]["scriptUrl"], "https://analytics.khalo.org/js/script.js")
        self.assertEqual(cfg["analytics"]["domain"], "khalo.org")


if __name__ == "__main__":
    unittest.main()
