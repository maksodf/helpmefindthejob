# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""2026-05-23: enhanced /status page — 30-day uptime tile, 24-cell
visual uptime bar, latency trend sparkline.

Pre-fix the /status surface showed live polling + 24h + 7d uptime
percentages. Post-fix it ALSO shows:

* 30-day rolling uptime tile alongside 24h / 7d
* 24-cell visual bar (one cell per hour, green/amber/red based on
  per-hour ok% from /api/health/history?window=24, grey when no
  data exists for that hour)
* Last-20 latency Unicode-block sparkline + min/p50/p95/max stats

All hydrated by status.js from the existing /api/health and
/api/health/history endpoints; no server-side changes."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


class StatusPageMarkup(unittest.TestCase):
    """Source-level invariants on status.html and status.js."""

    def setUp(self) -> None:
        self.html = (STATIC / "status.html").read_text(encoding="utf-8")
        self.js = (STATIC / "status.js").read_text(encoding="utf-8")
        self.css = (STATIC / "styles.css").read_text(encoding="utf-8")

    def test_status_html_carries_30_day_tile(self) -> None:
        self.assertIn(
            'id="uptime30d"',
            self.html,
            "30-day uptime tile must exist on /status",
        )

    def test_status_html_carries_uptime_bar_container(self) -> None:
        self.assertIn(
            'id="uptimeBar"',
            self.html,
            "24-cell uptime bar container must exist on /status",
        )
        self.assertIn(
            'role="img"',
            self.html,
            "uptime bar must declare role=img for accessibility",
        )

    def test_status_html_carries_latency_trend(self) -> None:
        self.assertIn('id="latencyTrend"', self.html)
        self.assertIn('id="latencyStats"', self.html)

    def test_status_js_hydrates_30_day_uptime(self) -> None:
        self.assertIn("window=720", self.js, "status.js must request 30-day window (720h)")
        self.assertIn("uptime30d", self.js)

    def test_status_js_renders_24_hourly_buckets(self) -> None:
        # The bucketer creates 24 hourly cells.
        self.assertIn("length: 24", self.js)
        self.assertIn("uptime-cell", self.js)

    def test_status_js_renders_latency_sparkline(self) -> None:
        # Unicode block sparkline characters
        self.assertIn("▁", self.js)
        self.assertIn("█", self.js)
        # Stats line includes p50 and p95
        self.assertIn("p50", self.js)
        self.assertIn("p95", self.js)

    def test_css_has_uptime_bar_styling(self) -> None:
        for needed in (
            ".uptime-bar",
            ".uptime-cell--ok",
            ".uptime-cell--warn",
            ".uptime-cell--bad",
            ".uptime-cell--empty",
        ):
            with self.subTest(rule=needed):
                self.assertIn(needed, self.css)


if __name__ == "__main__":
    unittest.main()
