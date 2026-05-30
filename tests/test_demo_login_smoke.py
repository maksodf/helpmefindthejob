# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for scripts/demo-login-smoke.py.

The demo-login smoke script is the operator's pre-submission check that every
seeded demo persona can actually log in. This test spins up a tiny mock
``/api/auth/login`` server and asserts the script's ``_post_login`` classifier
returns the right (status, detail) for every response branch — so the
operator-facing pass/fail output cannot silently regress.

We exercise the real classification logic (not a stub); the only thing not
covered here is the operator's remote network call, which is the genuine
operator boundary.
"""

from __future__ import annotations

import importlib.util
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO / "scripts" / "demo-login-smoke.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("demo_login_smoke", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SMOKE = _load_script_module()


class _MockLoginHandler(BaseHTTPRequestHandler):
    """Routes by the posted email to produce each real login response shape."""

    def log_message(self, *_args):  # silence test server logging
        pass

    def _send(self, code, body, *, set_cookie=False, raw=False):
        payload = body if raw else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if set_cookie:
            self.send_header("Set-Cookie", "hmftj_session=abc; HttpOnly; Path=/")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        email = data.get("email", "")
        password = data.get("password", "")
        if email == "good@x" and password == "right":
            self._send(200, {"user": {"id": "u1", "email": email}, "bootstrap": {}}, set_cookie=True)
        elif email == "nocookie@x":
            self._send(200, {"user": {"id": "u2"}, "bootstrap": {}})  # 200+user but no Set-Cookie
        elif email == "twofa@x":
            self._send(200, {"requires2fa": True, "challengeToken": "ct"})
        elif email == "unverified@x":
            self._send(403, {"error": "email_unverified", "detail": "Verify your email"})
        elif email == "limited@x":
            self._send(429, {"error": "rate_limited"})
        elif email == "weird@x":
            self._send(200, b"this is not json", raw=True)
        else:
            self._send(401, {"error": "invalid_login"})


class DemoLoginSmokeClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _MockLoginHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _login(self, email, password):
        return SMOKE._post_login(self.base, email, password, timeout=5.0)

    def test_valid_login_passes(self):
        status, detail = self._login("good@x", "right")
        self.assertEqual(status, "pass", detail)
        self.assertIn("session", detail.lower())

    def test_wrong_password_fails_401(self):
        status, detail = self._login("good@x", "wrong")
        self.assertEqual(status, "fail")
        self.assertIn("401", detail)
        self.assertIn("invalid_login", detail)

    def test_unknown_account_fails_401(self):
        status, detail = self._login("nobody@x", "right")
        self.assertEqual(status, "fail")
        self.assertIn("401", detail)

    def test_email_unverified_fails_403(self):
        status, detail = self._login("unverified@x", "right")
        self.assertEqual(status, "fail")
        self.assertIn("403", detail)
        self.assertIn("unverified", detail.lower())

    def test_two_factor_warns(self):
        status, detail = self._login("twofa@x", "right")
        self.assertEqual(status, "warn")
        self.assertIn("2fa", detail.lower())

    def test_rate_limited_fails_429(self):
        status, detail = self._login("limited@x", "right")
        self.assertEqual(status, "fail")
        self.assertIn("429", detail)

    def test_200_without_cookie_fails(self):
        status, detail = self._login("nocookie@x", "right")
        self.assertEqual(status, "fail")
        self.assertIn("Set-Cookie", detail)

    def test_non_json_200_fails(self):
        status, detail = self._login("weird@x", "right")
        self.assertEqual(status, "fail")
        self.assertIn("non-JSON", detail)

    def test_unreachable_host_fails(self):
        # Point at a port nothing is listening on.
        status, detail = SMOKE._post_login("http://127.0.0.1:1", "good@x", "right", timeout=2.0)
        self.assertEqual(status, "fail")
        self.assertIn("cannot reach", detail.lower())

    def test_script_uses_canonical_persona_panel(self):
        # The script must iterate the canonical 7-persona panel, not a hardcoded list.
        self.assertEqual(len(SMOKE.PERSONAS), 7)
        self.assertEqual(SMOKE.demo_email("aicha"), "aicha@demo.helpmefindthejob.org")


if __name__ == "__main__":
    unittest.main()
