# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

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


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
        return int(sock.getsockname()[1])


class AppSmokeTests(unittest.TestCase):
    def test_server_serves_ui_and_core_apis(self) -> None:
        with TemporaryDirectory() as tmp:
            port = free_port()
            env = {
                **os.environ,
                "HELPMEFINDTHEJOB_DATA_DIR": tmp,
                # deterministic test salt; silences audit-log dev warning
                "HELPMEFINDTHEJOB_AUDIT_SALT": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            }
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "app.py"), "--port", str(port)],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                base = f"http://127.0.0.1:{port}"
                # 100 × 0.1s = 10 s wall-clock budget. Cross-platform CI:
                # GitHub Actions macOS runners exhibit a slower TCP-bind
                # cycle than the ubuntu-latest runners (the original
                # range(40) = 4 s was tight enough that the macOS matrix
                # entry intermittently failed in setUpClass per the
                # test.yml head comment). The longer budget is safe — on
                # a healthy boot the first iteration succeeds well under
                # 1 s; the additional headroom only burns wall-clock when
                # something has actually gone wrong.
                for _ in range(100):
                    try:
                        with urlopen(f"{base}/api/health", timeout=0.5) as response:
                            health = json.loads(response.read().decode("utf-8"))
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    self.fail(f"server did not start (waited 10s on port {port})")

                self.assertEqual(health["status"], "ok")
                with urlopen(f"{base}/", timeout=1) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("Helpmefindthejob", html)
                self.assertIn("AI Provider", html)
                self.assertIn("Discovery Run Controls", html)

                with self.assertRaises(HTTPError) as unauthorized:
                    urlopen(f"{base}/api/bootstrap", timeout=1)
                self.assertEqual(unauthorized.exception.code, 401)

                request = Request(
                    f"{base}/api/auth/register",
                    data=json.dumps(
                        {"email": "tester@example.com", "password": "very-secure-password"}
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=1) as response:
                    auth = json.loads(response.read().decode("utf-8"))
                    cookie = response.headers["Set-Cookie"].split(";", 1)[0]
                csrf = auth["user"]["csrfToken"]
                bootstrap = auth["bootstrap"]
                self.assertIn("aiProviderOptions", bootstrap)
                authed_headers = {
                    "Content-Type": "application/json",
                    "Cookie": cookie,
                    "X-CSRF-Token": csrf,
                }

                request = Request(
                    f"{base}/api/suggest-companies",
                    data=json.dumps(
                        {"targetRoles": ["Digital Health"], "industry": "Healthcare"}
                    ).encode("utf-8"),
                    headers=authed_headers,
                    method="POST",
                )
                with urlopen(request, timeout=1) as response:
                    suggestions = json.loads(response.read().decode("utf-8"))
                self.assertEqual(suggestions["suggestions"][0]["type"], "company")
                self.assertIn("career_page_url", suggestions["suggestions"][0])

                request = Request(
                    f"{base}/api/demo/seed",
                    data=json.dumps({}).encode("utf-8"),
                    headers=authed_headers,
                    method="POST",
                )
                with urlopen(request, timeout=1) as response:
                    demo = json.loads(response.read().decode("utf-8"))
                self.assertEqual(demo["demo"]["company"]["name"], "Demo Klinikgruppe")

                request = Request(
                    f"{base}/api/watchlist/scan",
                    data=json.dumps({}).encode("utf-8"),
                    headers=authed_headers,
                    method="POST",
                )
                with urlopen(request, timeout=1) as response:
                    watchlist_scan = json.loads(response.read().decode("utf-8"))
                self.assertEqual(watchlist_scan["result"]["status"], "nothing_to_scan")
                self.assertEqual(
                    watchlist_scan["result"]["skipped"][0]["reason"], "demo_fixture_not_scanned"
                )

                request = Request(
                    f"{base}/api/watchlist/schedule",
                    data=json.dumps({"enabled": False, "intervalMinutes": 30}).encode("utf-8"),
                    headers=authed_headers,
                    method="POST",
                )
                with urlopen(request, timeout=1) as response:
                    schedule = json.loads(response.read().decode("utf-8"))
                self.assertEqual(schedule["watchlistSchedule"]["intervalMinutes"], 30)

                request = Request(f"{base}/api/data/export", headers={"Cookie": cookie})
                with urlopen(request, timeout=1) as response:
                    exported = json.loads(response.read().decode("utf-8"))
                self.assertEqual(exported["schemaVersion"], 1)
            finally:
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                finally:
                    for stream in (process.stdin, process.stdout, process.stderr):
                        if stream is not None:
                            try:
                                stream.close()
                            except Exception:
                                pass
