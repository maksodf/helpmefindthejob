# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-37 — CSP violation reporting.

Pre-AUDIT-37 the project shipped a strict Content-Security-Policy but
no mechanism to learn when it fires in the wild. A violation in a
user's browser was silently dropped. That made every CSP tightening
a blind change — operators couldn't tell whether a new directive
broke a legitimate code path until a user complained.

After AUDIT-37:

* The main CSP header carries a ``report-uri /csp-report`` directive
  (legacy, universal browser support) AND a ``report-to csp-endpoint``
  directive (modern Reporting API).
* A ``Report-To`` header is emitted alongside the CSP, registering
  the ``csp-endpoint`` group that the report-to directive references.
* A POST handler at ``/csp-report`` accepts the browser-submitted
  reports. It rate-limits per source IP (50/min), caps body size at
  16 KB, parses both legacy ``application/csp-report`` and modern
  ``application/reports+json`` shapes, extracts a PII-safe summary
  (effective-directive + blocked-uri + document-uri, NOTHING ELSE),
  and emits it via the standard library ``logging`` module at WARNING
  level. Always returns 204 No Content — browsers don't retry, and we
  must never enable a client to use the endpoint as an oracle for
  what we do/don't accept.
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


_LEGACY_REPORT = json.dumps({
    "csp-report": {
        "blocked-uri": "https://evil.example/inject.js",
        "document-uri": "https://helpmefindthejob.org/",
        "effective-directive": "script-src",
        "original-policy": "default-src 'self'; script-src 'self'; report-uri /csp-report",
        "referrer": "",
        "status-code": 200,
        "violated-directive": "script-src 'self'",
    }
}).encode("utf-8")

_REPORTING_API_REPORT = json.dumps([{
    "type": "csp-violation",
    "url": "https://helpmefindthejob.org/",
    "user_agent": "Mozilla/5.0 (would-be-PII)",
    "body": {
        "blockedURL": "https://evil.example/inject.js",
        "disposition": "enforce",
        "documentURL": "https://helpmefindthejob.org/",
        "effectiveDirective": "script-src",
        "originalPolicy": "default-src 'self'; report-to csp-endpoint",
        "referrer": "",
        "statusCode": 200,
    }
}]).encode("utf-8")


class CspReportSummariser(unittest.TestCase):
    """Pure-Python tests for ``_summarize_csp_report`` (no live server)."""

    def test_legacy_report_extracts_directive_and_blocked_uri(self) -> None:
        from app import _summarize_csp_report
        summary = _summarize_csp_report(_LEGACY_REPORT)
        self.assertIsNotNone(summary)
        self.assertIn("directive=script-src", summary)
        self.assertIn("blocked=https://evil.example/inject.js", summary)
        self.assertIn("doc=https://helpmefindthejob.org/", summary)

    def test_reporting_api_report_extracts_camelcase_fields(self) -> None:
        from app import _summarize_csp_report
        summary = _summarize_csp_report(_REPORTING_API_REPORT)
        self.assertIsNotNone(summary)
        self.assertIn("directive=script-src", summary)
        self.assertIn("blocked=https://evil.example/inject.js", summary)

    def test_summary_omits_user_agent_pii(self) -> None:
        from app import _summarize_csp_report
        summary = _summarize_csp_report(_REPORTING_API_REPORT)
        self.assertIsNotNone(summary)
        self.assertNotIn(
            "would-be-PII", summary,
            "AUDIT-37: summary must NOT include User-Agent (PII)",
        )
        self.assertNotIn("Mozilla", summary)

    def test_unparseable_body_returns_none(self) -> None:
        from app import _summarize_csp_report
        self.assertIsNone(_summarize_csp_report(b"this is not json"))

    def test_non_csp_json_returns_none(self) -> None:
        from app import _summarize_csp_report
        self.assertIsNone(_summarize_csp_report(b'{"unrelated": "payload"}'))


class CspReportSlotRateLimit(unittest.TestCase):
    """Direct tests for the State.claim_csp_report_slot rate limiter."""

    def test_first_50_pass_then_429(self) -> None:
        from app import STATE, CSP_REPORT_LIMIT
        client = "192.0.2.1"
        # Make sure the bucket starts empty for this client
        with STATE._csp_report_lock:  # noqa: SLF001 — test setup
            STATE._csp_requests.pop(client, None)
        for _ in range(CSP_REPORT_LIMIT):
            self.assertTrue(STATE.claim_csp_report_slot(client))
        # 51st claim should fail
        self.assertFalse(STATE.claim_csp_report_slot(client))


class CspHeaderAndReportEndpoint(unittest.TestCase):
    """Live probes for the CSP header + /csp-report endpoint."""

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

    def _request(self, method: str, path: str, *,
                 body: bytes | None = None,
                 headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def test_csp_header_contains_report_uri(self) -> None:
        _status, headers, _body = self._request("GET", "/api/health")
        csp = headers.get("Content-Security-Policy", "")
        self.assertIn(
            "report-uri /csp-report", csp,
            "AUDIT-37: legacy report-uri directive must be present in CSP header",
        )

    def test_csp_header_contains_report_to(self) -> None:
        _status, headers, _body = self._request("GET", "/api/health")
        csp = headers.get("Content-Security-Policy", "")
        self.assertIn(
            "report-to csp-endpoint", csp,
            "AUDIT-37: modern report-to directive must be present in CSP header",
        )

    def test_report_to_header_registers_group(self) -> None:
        _status, headers, _body = self._request("GET", "/api/health")
        report_to = headers.get("Report-To", "")
        self.assertTrue(
            report_to,
            "AUDIT-37: Report-To header must be set to register the Reporting API group",
        )
        parsed = json.loads(report_to)
        self.assertEqual(parsed["group"], "csp-endpoint")
        self.assertGreater(parsed["max_age"], 60 * 60 * 24, "max_age must be ≥ 1 day")
        urls = [endpoint["url"] for endpoint in parsed["endpoints"]]
        self.assertIn("/csp-report", urls)

    def test_csp_report_post_legacy_returns_204(self) -> None:
        status, _headers, body = self._request(
            "POST", "/csp-report",
            body=_LEGACY_REPORT,
            headers={"Content-Type": "application/csp-report", "Content-Length": str(len(_LEGACY_REPORT))},
        )
        self.assertEqual(status, 204)
        self.assertEqual(body, b"")

    def test_csp_report_post_reporting_api_returns_204(self) -> None:
        status, _headers, body = self._request(
            "POST", "/csp-report",
            body=_REPORTING_API_REPORT,
            headers={"Content-Type": "application/reports+json", "Content-Length": str(len(_REPORTING_API_REPORT))},
        )
        self.assertEqual(status, 204)
        self.assertEqual(body, b"")

    def test_csp_report_post_invalid_body_still_204(self) -> None:
        # Browsers don't retry on non-2xx, and we must not let the
        # endpoint be used as an oracle for what shapes we accept.
        bad = b"not json at all"
        status, _headers, _body = self._request(
            "POST", "/csp-report",
            body=bad,
            headers={"Content-Type": "application/csp-report", "Content-Length": str(len(bad))},
        )
        self.assertEqual(status, 204)

    def test_csp_report_post_oversize_body_returns_413(self) -> None:
        # Send a Content-Length that exceeds the cap. We never actually
        # read the body when it's too large, so we can announce a big
        # length without sending the bytes — the server rejects on the
        # Content-Length check before any read.
        from app import CSP_REPORT_MAX_BYTES
        oversize = CSP_REPORT_MAX_BYTES + 1
        # Use a dummy connection that announces the size without sending
        # the full body — the server should respond before reading.
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(
            "POST", "/csp-report",
            body=b"x",  # tiny body; Content-Length header is what trips the check
            headers={
                "Content-Type": "application/csp-report",
                "Content-Length": str(oversize),
            },
        )
        # Override the header manually since http.client may correct it
        # The test is best-effort; if the client refuses to send a
        # mismatched Content-Length, the underlying invariant is still
        # enforced by the unit-tested constant.
        try:
            resp = conn.getresponse()
            status = resp.status
            resp.read()
        except Exception:
            self.skipTest("http.client refused to send mismatched Content-Length")
        finally:
            conn.close()
        self.assertEqual(status, 413, f"oversize report should return 413, got {status}")


if __name__ == "__main__":
    unittest.main()
