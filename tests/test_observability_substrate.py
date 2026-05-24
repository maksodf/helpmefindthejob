# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Observability substrate contract (phase2-backlog #17).

Three opt-in surfaces gated by env vars + a Prometheus-style
metrics endpoint always-on for scraping:

1. ``report_error(exc, context)`` — Sentry dispatch when DSN set
2. ``emit_event(name, properties)`` — PostHog dispatch when key set
3. ``inc / set_gauge / observe`` — in-memory metrics; rendered at
   /api/metrics for Prometheus / Grafana scrape

Tests pin: env-gate honoured (no-op without env), PII sanitiser,
Prometheus exposition format, /api/metrics route, HTTP-request
auto-instrumentation via the Handler.log_request override.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery import observability

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Env-gate honour
# ---------------------------------------------------------------------------


class EnvGateHonoured(unittest.TestCase):
    """Without env vars the substrate is a no-op; with env vars it
    attempts dispatch. Critical: zero overhead in the default
    build."""

    def setUp(self):
        self._original = dict(os.environ)
        for key in (
            "HELPMEFINDTHEJOB_SENTRY_DSN",
            "HELPMEFINDTHEJOB_SENTRY_DSN",
            "HELPMEFINDTHEJOB_POSTHOG_KEY",
            "HELPMEFINDTHEJOB_POSTHOG_KEY",
            "HELPMEFINDTHEJOB_POSTHOG_HOST",
            "HELPMEFINDTHEJOB_POSTHOG_HOST",
        ):
            os.environ.pop(key, None)

    def tearDown(self):
        for key in (
            "HELPMEFINDTHEJOB_SENTRY_DSN",
            "HELPMEFINDTHEJOB_SENTRY_DSN",
            "HELPMEFINDTHEJOB_POSTHOG_KEY",
            "HELPMEFINDTHEJOB_POSTHOG_KEY",
            "HELPMEFINDTHEJOB_POSTHOG_HOST",
            "HELPMEFINDTHEJOB_POSTHOG_HOST",
        ):
            if key in self._original:
                os.environ[key] = self._original[key]
            else:
                os.environ.pop(key, None)

    def test_report_error_returns_false_without_dsn(self):
        result = observability.report_error(ValueError("test"))
        self.assertFalse(result)

    def test_emit_event_returns_false_without_key(self):
        result = observability.emit_event("test_event", properties={"x": 1})
        self.assertFalse(result)

    def test_sentry_dsn_returns_empty_without_env(self):
        self.assertEqual(observability.sentry_dsn(), "")

    def test_posthog_key_returns_empty_without_env(self):
        self.assertEqual(observability.posthog_key(), "")

    def test_posthog_host_has_eu_default(self):
        """Privacy-by-default: EU PostHog host when none specified."""

        os.environ["HELPMEFINDTHEJOB_POSTHOG_KEY"] = "test"
        self.assertEqual(observability.posthog_host(), "https://eu.posthog.com")

    def test_report_error_never_raises(self):
        """Even with malformed input, the function returns cleanly."""

        observability.report_error(ValueError("x"), context={"a": 1})
        observability.report_error(ValueError("x"), context=None)
        observability.report_error(KeyError("y"))

    def test_legacy_env_var_also_works(self):
        os.environ["HELPMEFINDTHEJOB_SENTRY_DSN"] = "fake://test"
        self.assertEqual(observability.sentry_dsn(), "fake://test")


# ---------------------------------------------------------------------------
# PII sanitiser
# ---------------------------------------------------------------------------


class PIISanitiser(unittest.TestCase):
    """The PII filter prevents accidental leakage of sensitive
    fields into Sentry / PostHog payloads."""

    def test_email_redacted(self):
        result = observability._sanitise_for_telemetry({"email": "x@y.com"})
        self.assertEqual(result["email"], "<redacted>")

    def test_cv_text_redacted(self):
        result = observability._sanitise_for_telemetry({"cv_text": "Full CV..."})
        self.assertEqual(result["cv_text"], "<redacted>")

    def test_token_redacted(self):
        result = observability._sanitise_for_telemetry({"token": "abc"})
        self.assertEqual(result["token"], "<redacted>")

    def test_safe_keys_pass_through(self):
        result = observability._sanitise_for_telemetry({"persona_id": "aicha"})
        self.assertEqual(result["persona_id"], "aicha")

    def test_nested_dicts_sanitised(self):
        result = observability._sanitise_for_telemetry(
            {"user": {"email": "x@y", "persona_id": "olga"}}
        )
        self.assertEqual(result["user"]["email"], "<redacted>")
        self.assertEqual(result["user"]["persona_id"], "olga")

    def test_lists_sanitised(self):
        result = observability._sanitise_for_telemetry([{"email": "a@b"}, {"persona_id": "yusuf"}])
        self.assertEqual(result[0]["email"], "<redacted>")
        self.assertEqual(result[1]["persona_id"], "yusuf")

    def test_long_strings_truncated(self):
        result = observability._sanitise_for_telemetry("x" * 2000)
        self.assertTrue(result.endswith("<...truncated>"))
        self.assertLess(len(result), 1100)

    def test_case_insensitive_match(self):
        """PII keys match case-insensitively so accidental Email vs
        email casing doesn't slip through."""

        result = observability._sanitise_for_telemetry({"Email": "x@y"})
        self.assertEqual(result["Email"], "<redacted>")


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------


class CounterMetrics(unittest.TestCase):
    def setUp(self):
        observability._reset_registry_for_test()

    def test_inc_creates_counter(self):
        observability.inc("test_counter", help_text="A test counter")
        text = observability.prometheus_text()
        self.assertIn("# HELP test_counter A test counter", text)
        self.assertIn("# TYPE test_counter counter", text)
        self.assertIn("test_counter 1.0", text)

    def test_inc_with_labels(self):
        observability.inc(
            "test_counter",
            labels={"method": "GET", "status": "200"},
        )
        text = observability.prometheus_text()
        self.assertIn('test_counter{method="GET",status="200"}', text)

    def test_inc_accumulates(self):
        observability.inc("acc")
        observability.inc("acc")
        observability.inc("acc", value=3.0)
        text = observability.prometheus_text()
        self.assertIn("acc 5.0", text)


class GaugeMetrics(unittest.TestCase):
    def setUp(self):
        observability._reset_registry_for_test()

    def test_set_gauge(self):
        observability.set_gauge("gauge_test", 42.5)
        text = observability.prometheus_text()
        self.assertIn("# TYPE gauge_test gauge", text)
        self.assertIn("gauge_test 42.5", text)

    def test_set_gauge_overwrites(self):
        observability.set_gauge("g", 1.0)
        observability.set_gauge("g", 99.0)
        text = observability.prometheus_text()
        self.assertIn("g 99.0", text)
        self.assertNotIn("g 1.0\n", text)


class HistogramMetrics(unittest.TestCase):
    def setUp(self):
        observability._reset_registry_for_test()

    def test_observe_creates_histogram(self):
        observability.observe("histo_test", 0.05)
        text = observability.prometheus_text()
        self.assertIn("# TYPE histo_test histogram", text)
        self.assertIn("histo_test_count", text)
        self.assertIn("histo_test_sum", text)
        self.assertIn("histo_test_bucket", text)

    def test_observe_buckets(self):
        observability.observe("h", 0.005)  # in 0.005 bucket
        observability.observe("h", 0.5)  # in 0.5 bucket
        observability.observe("h", 5.0)  # in 5.0 bucket
        text = observability.prometheus_text()
        # The cumulative bucket counts:
        # le=0.005 → 1 (only the 0.005)
        # le=0.5 → 2 (0.005 + 0.5)
        # le=5.0 → 3 (all three)
        self.assertIn('h_bucket{le="0.005"} 1', text)
        self.assertIn('h_bucket{le="0.5"} 2', text)
        self.assertIn('h_bucket{le="5.0"} 3', text)
        self.assertIn('h_bucket{le="+Inf"} 3', text)
        self.assertIn("h_sum 5.505", text)
        self.assertIn("h_count 3", text)


class MetricKindMismatch(unittest.TestCase):
    def setUp(self):
        observability._reset_registry_for_test()

    def test_reregister_as_different_kind_raises(self):
        observability.inc("mixed")
        with self.assertRaises(ValueError):
            observability.set_gauge("mixed", 1.0)


# ---------------------------------------------------------------------------
# Label escaping
# ---------------------------------------------------------------------------


class LabelEscaping(unittest.TestCase):
    def setUp(self):
        observability._reset_registry_for_test()

    def test_quotes_escaped(self):
        observability.inc("c", labels={"k": 'a"b'})
        text = observability.prometheus_text()
        self.assertIn(r'k="a\"b"', text)

    def test_backslashes_escaped(self):
        observability.inc("c", labels={"k": "a\\b"})
        text = observability.prometheus_text()
        self.assertIn(r'k="a\\b"', text)

    def test_newlines_escaped(self):
        observability.inc("c", labels={"k": "a\nb"})
        text = observability.prometheus_text()
        self.assertIn(r'k="a\nb"', text)


# ---------------------------------------------------------------------------
# Live /api/metrics endpoint
# ---------------------------------------------------------------------------


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


class MetricsEndpointLive(unittest.TestCase):
    """Boot app.py + verify /api/metrics returns Prometheus
    text format with the auto-instrumented HTTP metrics
    accruing after a few requests."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = TemporaryDirectory()
        cls.port = _free_port()
        env = dict(os.environ)
        env["HELPMEFINDTHEJOB_DATA_FILE"] = str(Path(cls.tmpdir.name) / "data.json")
        env["HELPMEFINDTHEJOB_DISABLE_SCHEDULER"] = "1"
        env.pop("HELPMEFINDTHEJOB_DATABASE_URL", None)
        cls.proc = subprocess.Popen(
            [sys.executable, "app.py", "--port", str(cls.port)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _wait_for_port(cls.port, timeout=15.0):
            cls.proc.terminate()
            raise RuntimeError("app.py failed to bind")

    @classmethod
    def tearDownClass(cls):
        if cls.proc is not None:
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.tmpdir.cleanup()

    def _get(self, path: str) -> tuple[int, dict, str]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return (
                resp.status,
                {k.lower(): v for k, v in resp.headers.items()},
                resp.read().decode("utf-8"),
            )

    def test_metrics_endpoint_returns_prometheus_text(self):
        # Generate some HTTP traffic
        for _ in range(3):
            self._get("/api/health")
        status, headers, body = self._get("/api/metrics")
        self.assertEqual(status, 200)
        self.assertIn(
            "text/plain",
            headers.get("content-type", ""),
            "Prometheus exposition format requires text/plain",
        )
        self.assertIn("version=0.0.4", headers.get("content-type", ""))

    def test_http_requests_total_metric_present(self):
        for _ in range(3):
            self._get("/api/health")
        _, _, body = self._get("/api/metrics")
        self.assertIn("helpmefindthejob_http_requests_total", body)
        # Should have a method label
        self.assertIn('method="GET"', body)

    def test_request_duration_histogram_present(self):
        for _ in range(2):
            self._get("/api/health")
        _, _, body = self._get("/api/metrics")
        self.assertIn("helpmefindthejob_http_request_duration_seconds", body)
        self.assertIn("helpmefindthejob_http_request_duration_seconds_count", body)

    def test_scheduler_active_jobs_gauge_present(self):
        _, _, body = self._get("/api/metrics")
        self.assertIn("helpmefindthejob_scheduler_active_jobs", body)
        self.assertIn("# TYPE helpmefindthejob_scheduler_active_jobs gauge", body)

    def test_metrics_endpoint_cache_no_store(self):
        """Scrape endpoint must not be cached — Prometheus needs
        fresh values every poll."""

        _, headers, _ = self._get("/api/metrics")
        self.assertIn("no-store", headers.get("cache-control", "").lower())


if __name__ == "__main__":
    unittest.main()
