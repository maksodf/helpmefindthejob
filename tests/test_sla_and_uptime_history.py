# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""SLA template + uptime-history surface contract (phase2-backlog #30).

Closes the procurement-readiness portion of #30:

1. ``docs/SLA-template.md`` — procurement-ready template for
   institutional deployers (Beratungsstellen / IQ-Netzwerk /
   government adopters) carrying uptime tiers, performance
   targets, incident-response matrix, GDPR processor-controller
   roles, RPO/RTO, maintenance windows, reporting cadence,
   SLA-credits appendix, force-majeure carve-outs.
2. ``/api/health/history`` — uptime-aware status surface backed
   by the existing analytics-events stream. Records a
   ``health_check`` event on every public health call (best-
   effort, never raises). The /status page reads this for
   24h + 7d rolling uptime tallies.

Tests pin: SLA template completeness, the recording path,
the history-endpoint shape + clamping, and the status-page
wiring.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parent.parent
SLA_DOC = REPO_ROOT / "docs" / "SLA-template.md"


# ---------------------------------------------------------------------------
# SLA template structure
# ---------------------------------------------------------------------------


class SLATemplateContent(unittest.TestCase):
    """Procurement-ready SLA template must carry the canonical
    sections institutional deployers will look for."""

    def setUp(self):
        self.src = SLA_DOC.read_text(encoding="utf-8")

    def test_sla_exists(self):
        self.assertTrue(SLA_DOC.exists())

    def test_explicitly_marked_template(self):
        self.assertIn("TEMPLATE", self.src)

    def test_carries_uptime_tier_table(self):
        for tier in ("Community", "Standard", "Institutional"):
            with self.subTest(tier=tier):
                self.assertIn(tier, self.src)
        for percent in ("99.0%", "99.5%", "99.9%"):
            with self.subTest(percent=percent):
                self.assertIn(percent, self.src)

    def test_carries_performance_targets(self):
        self.assertIn("p50", self.src)
        self.assertIn("p95", self.src)
        self.assertIn("p99", self.src)

    def test_carries_incident_severity_matrix(self):
        for sev in ("P0", "P1", "P2", "P3"):
            with self.subTest(severity=sev):
                self.assertIn(sev, self.src)

    def test_carries_gdpr_processor_controller_roles(self):
        """Institutional deployers need the Art. 28 framing."""

        self.assertIn("Auftragsverarbeiter", self.src)
        self.assertIn("Verantwortlicher", self.src)
        self.assertIn("Art. 28", self.src)

    def test_carries_rpo_rto(self):
        self.assertIn("RPO", self.src)
        self.assertIn("RTO", self.src)

    def test_carries_maintenance_window_policy(self):
        self.assertIn("Maintenance windows", self.src)
        self.assertIn("Planned", self.src)
        self.assertIn("Emergency", self.src)

    def test_carries_force_majeure_carveouts(self):
        self.assertIn("Force majeure", self.src)

    def test_carries_sla_credits_appendix(self):
        self.assertIn("SLA credits", self.src)

    def test_carries_incident_contact_registry(self):
        self.assertIn("Incident-contact registry", self.src)

    def test_carries_dpa_cross_link(self):
        # Updated 2026-05-22 (phase2-backlog #37 docs polish):
        # DPA template lives at compliance/dpa-template.md, not
        # docs/DPA-template.md. The mkdocs strict build caught the
        # broken link.
        self.assertIn("dpa-template.md", self.src)


# ---------------------------------------------------------------------------
# Uptime-history surface — module-level functions
# ---------------------------------------------------------------------------


class HealthHistoryEndpointInModuleSource(unittest.TestCase):
    """Source-level check: the AppState methods + route handler
    are wired correctly (the live route is exercised below via
    subprocess; this layer catches refactor regressions cheaply)."""

    def setUp(self):
        self.src = (REPO_ROOT / "app.py").read_text(encoding="utf-8")

    def test_record_health_snapshot_method_exists(self):
        self.assertIn("def record_health_snapshot(", self.src)

    def test_health_history_method_exists(self):
        self.assertIn("def health_history(", self.src)

    def test_api_health_records_snapshot(self):
        """The /api/health handler must call record_health_snapshot
        on every public hit so the history surface accrues data."""

        self.assertIn(
            'parsed.path == "/api/health"',
            self.src,
        )
        self.assertIn("STATE.record_health_snapshot(payload)", self.src)

    def test_api_health_history_route_registered(self):
        self.assertIn('parsed.path == "/api/health/history"', self.src)
        self.assertIn("STATE.health_history(window_hours=", self.src)

    def test_window_clamped(self):
        """The window parameter must be clamped to a sane range to
        prevent a malicious caller from requesting 10 years of
        history and exhausting memory."""

        # Look for the clamp pattern
        self.assertIn("max(1, min(window, 720))", self.src)


# ---------------------------------------------------------------------------
# Live end-to-end test of the history surface
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


class HealthHistoryEndpointLive(unittest.TestCase):
    """Boot app.py as a subprocess; verify the route produces the
    expected payload shape AND that /api/health hits accrue into
    the history."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = TemporaryDirectory()
        cls.port = _free_port()
        env = dict(os.environ)
        env["HELPMEFINDTHEJOB_DATA_FILE"] = str(
            Path(cls.tmpdir.name) / "data.json"
        )
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

    def _get_json(self, path: str) -> dict:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_history_initially_empty_or_self_recorded(self):
        """First call to /history might already contain the entries
        created by the smoke calls during setUpClass + earlier tests.
        Just verify the shape."""

        payload = self._get_json("/api/health/history?window=24")
        self.assertIn("windowHours", payload)
        self.assertIn("snapshotCount", payload)
        self.assertIn("okCount", payload)
        self.assertIn("uptimePercent", payload)
        self.assertIn("snapshots", payload)
        self.assertEqual(payload["windowHours"], 24)

    def test_health_hit_accrues_snapshot(self):
        """Hitting /api/health must add a snapshot to the history."""

        # Get current count
        before = self._get_json("/api/health/history?window=24")["snapshotCount"]
        # Hit health a few times
        for _ in range(3):
            self._get_json("/api/health")
        after = self._get_json("/api/health/history?window=24")["snapshotCount"]
        self.assertGreaterEqual(after, before + 3)

    def test_uptime_percent_computed_correctly(self):
        # Hit health multiple times so we have data
        for _ in range(5):
            self._get_json("/api/health")
        payload = self._get_json("/api/health/history?window=24")
        if payload["snapshotCount"] > 0:
            # All hits should have status=ok in this happy-path test
            self.assertEqual(payload["okCount"], payload["snapshotCount"])
            self.assertEqual(payload["uptimePercent"], 100.0)

    def test_window_param_clamped_low(self):
        payload = self._get_json("/api/health/history?window=0")
        # Window=0 clamps to 1
        self.assertEqual(payload["windowHours"], 1)

    def test_window_param_clamped_high(self):
        payload = self._get_json("/api/health/history?window=10000")
        # Window=10000 clamps to 720 (30d)
        self.assertEqual(payload["windowHours"], 720)

    def test_window_param_invalid_falls_back_to_default(self):
        payload = self._get_json("/api/health/history?window=notanumber")
        # Invalid input falls back to 24
        self.assertEqual(payload["windowHours"], 24)

    def test_snapshot_shape(self):
        for _ in range(2):
            self._get_json("/api/health")
        payload = self._get_json("/api/health/history?window=24")
        if payload["snapshots"]:
            snap = payload["snapshots"][-1]
            self.assertIn("at", snap)
            self.assertIn("status", snap)
            self.assertIn("storage", snap)


# ---------------------------------------------------------------------------
# Status page wiring
# ---------------------------------------------------------------------------


class RingBufferBoundedness(unittest.TestCase):
    """phase2-backlog #30 panic-round catch: the original design
    wrote to analytics_events on every /api/health hit — unbounded
    growth with status-page polling. Refactored to a bounded
    in-memory ring buffer. This test verifies the bound holds."""

    def test_ring_buffer_drops_oldest_on_overflow(self):
        from tempfile import TemporaryDirectory
        from app import AppState, MAX_HEALTH_SNAPSHOTS

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = AppState(
                root / "company.sqlite3",
                root / "auth.sqlite3",
                root / "ai.json",
                root / "schedule.json",
                start_scheduler=False,
            )
            try:
                # Push 2x the cap; verify it stays capped
                for i in range(MAX_HEALTH_SNAPSHOTS * 2):
                    state.record_health_snapshot({"status": "ok"})
                # Ring buffer should never exceed the cap
                self.assertLessEqual(
                    len(state._health_snapshots),
                    MAX_HEALTH_SNAPSHOTS,
                    "ring buffer exceeded MAX_HEALTH_SNAPSHOTS cap",
                )
            finally:
                state.auth_store.close()
                state.repository.close()

    def test_max_snapshots_constant_present(self):
        from app import MAX_HEALTH_SNAPSHOTS
        self.assertGreaterEqual(MAX_HEALTH_SNAPSHOTS, 1000)
        self.assertLessEqual(MAX_HEALTH_SNAPSHOTS, 50000)

    def test_history_uses_in_memory_buffer_not_analytics_events(self):
        """Source-level check: the refactored health_history MUST
        read from self._health_snapshots, NOT from the analytics
        events table. Catches a future regression where someone
        accidentally re-introduces the unbounded write."""

        src = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        # Find the health_history method body
        start = src.find("def health_history(")
        end = src.find("\n    def ", start + 10)
        method_src = src[start:end]
        # Must reference the ring buffer
        self.assertIn("_health_snapshots", method_src)
        # And must NOT loop over repository.analytics_events
        self.assertNotIn(
            "self.repository.analytics_events.values()",
            method_src,
            "health_history accidentally reads from the unbounded "
            "analytics_events table — should use the ring buffer",
        )


class StatusPageReadsHistory(unittest.TestCase):
    """HTML structure in status.html; JS behavior in status.js
    (extracted 2026-05-22 per AUDIT-2 to comply with CSP
    script-src self)."""

    def setUp(self):
        self.html = (REPO_ROOT / "static" / "status.html").read_text(
            encoding="utf-8"
        )
        self.js = (REPO_ROOT / "static" / "status.js").read_text(
            encoding="utf-8"
        )

    def test_uptime_cards_present(self):
        self.assertIn('id="uptime24h"', self.html)
        self.assertIn('id="uptime7d"', self.html)

    def test_status_js_loaded_externally(self):
        self.assertIn('<script src="/status.js"', self.html)

    def test_history_endpoint_referenced(self):
        self.assertIn("/api/health/history?window=24", self.js)
        self.assertIn("/api/health/history?window=168", self.js)

    def test_uptime_formatter_handles_no_data(self):
        """The 'no data yet' fallback prevents the page from
        showing a misleading 0% on a fresh deploy."""

        self.assertIn("no data yet", self.js)


if __name__ == "__main__":
    unittest.main()
