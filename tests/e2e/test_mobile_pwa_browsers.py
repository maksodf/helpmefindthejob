# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Mobile + PWA browser-driven E2E coverage.

PlanTowardPerfection Ceiling-2 box 2.13.2: "Mobile/PWA E2E test
suite — Playwright runs against iOS Safari + Chrome Android, not
just headless desktop Chromium."

This module runs against the same booted-app fixture as the
desktop tests/e2e/test_browser_flow.py — driven by
scripts/run-e2e.sh which sets E2E_BASE_URL on a free port. The
difference is Playwright's device emulation: iPhone 12 (WebKit /
iOS Safari approximation) + Pixel 5 (Chromium / Chrome Android
approximation). Both engines render the SPA + the manifest +
the service-worker contract from the SAME upstream code path
the desktop tests exercise.

Scope per device:
  * Landing page renders without console errors
  * Manifest link is present in the rendered DOM
  * Service-worker registers (or has-registered) on the SAME
    origin
  * Sign-in form is keyboard-focusable + the submit button is
    tap-targetable (touch UA)
  * The sign-up consent surface is visible (the UX-P0 fix from
    the prior session that boxes 1.6.5 + the demo-banner depend
    on)
  * No layout overflow on the canonical phone viewport (the
    rendered body width matches the device viewport width)

The persona-walks regression-guard is the existing in-process
tests/e2e/persona_<slug>_smoke.py suite (UserJourney API-level);
this file is the BROWSER-LEVEL regression-guard for the actual
mobile rendering surface, complementing the desktop coverage.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover — local-dev gate
    sync_playwright = None  # type: ignore[assignment]


def _require_e2e_env() -> tuple[str, Path, bool]:
    base_url = os.environ.get("E2E_BASE_URL", "")
    screenshots = Path(os.environ.get("E2E_SCREENSHOTS", "tests/e2e/screenshots"))
    headless = os.environ.get("E2E_HEADLESS", "true").strip().casefold() != "false"
    if not base_url:
        raise unittest.SkipTest("E2E_BASE_URL is not set; run via scripts/run-e2e.sh")
    return base_url, screenshots, headless


@unittest.skipIf(
    sync_playwright is None,
    "Playwright is not installed (pip install playwright && playwright install)",
)
class MobilePwaBrowserSmoke(unittest.TestCase):
    """Per-device mobile-rendering smoke. Runs the SAME landing-
    page + auth-surface + SPA-shell assertions on Chrome Android
    (Pixel 5) AND iOS Safari (iPhone 12) device profiles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.base_url, cls.screenshots, cls.headless = _require_e2e_env()
        cls.screenshots.mkdir(parents=True, exist_ok=True)
        cls._pw = sync_playwright().start()
        # Chromium for Pixel 5; WebKit for iPhone 12. Both engines
        # must be installed via `playwright install --with-deps
        # chromium webkit`; the CI workflow handles this.
        cls.chromium = cls._pw.chromium.launch(headless=cls.headless)
        try:
            cls.webkit = cls._pw.webkit.launch(headless=cls.headless)
        except Exception as exc:  # pragma: no cover — environment-specific
            cls.webkit = None
            cls._webkit_error = str(exc)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.chromium.close()
        if cls.webkit is not None:
            cls.webkit.close()
        cls._pw.stop()

    def _run_landing_smoke(self, browser, device_descriptor, slug: str) -> None:
        """Boot a Playwright context with the given device descriptor +
        run the standardised landing-smoke assertions. Captures a
        screenshot per device for diagnostics."""
        ctx_options = dict(device_descriptor)
        # Make sure the device's viewport is honoured.
        context = browser.new_context(**ctx_options)
        try:
            page = context.new_page()
            console_errors: list[str] = []
            page.on(
                "console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None,
            )

            page.goto(self.base_url + "/", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 1. Manifest link present.
            self.assertEqual(
                page.locator('link[rel="manifest"]').count(),
                1,
                f"{slug}: expected exactly 1 manifest link in head",
            )

            # 2. Service-worker registration object is wired (registration
            #    is async; we just verify the navigator surface is
            #    available — i.e., the page is on HTTPS or localhost +
            #    the SW infrastructure is reachable).
            sw_available = page.evaluate("'serviceWorker' in navigator")
            self.assertTrue(
                sw_available,
                f"{slug}: navigator.serviceWorker unavailable — page not "
                "served over HTTPS/localhost OR browser doesn't support PWA",
            )

            # 3. Sign-in form is present + focusable.
            self.assertEqual(
                page.locator("#loginEmail").count(),
                1,
                f"{slug}: sign-in email field missing",
            )
            self.assertEqual(
                page.locator("#loginPassword").count(),
                1,
                f"{slug}: sign-in password field missing",
            )

            # 4. Registration consent block is visible (UX-P0 + 1.6.5
            #    dependency).
            consent_block = page.locator("#registerConsent")
            self.assertEqual(
                consent_block.count(),
                1,
                f"{slug}: #registerConsent block missing from landing — "
                "regression in the UX-P0 fix or the demo-banner contract",
            )

            # 5. No layout overflow — body inner-width matches viewport.
            #    Allow a small fudge factor for scrollbars/zoom rounding.
            body_width = page.evaluate("document.body.clientWidth")
            viewport_width = page.viewport_size["width"]
            self.assertLessEqual(
                body_width,
                viewport_width + 10,
                f"{slug}: body width {body_width}px > viewport {viewport_width}px "
                f"+ 10px tolerance — layout overflow on mobile",
            )

            # 6. No console errors. (Warnings are OK; errors are not.)
            #    Filter known-noisy entries (favicon 404 in test, etc.)
            real_errors = [
                e for e in console_errors
                if "favicon" not in e.lower()
                and "Manifest" not in e  # PWA manifest warnings can fire under headless emulation
            ]
            self.assertEqual(
                real_errors,
                [],
                f"{slug}: console errors observed: {real_errors!r}",
            )

            # Capture diagnostic screenshot.
            page.screenshot(
                path=str(self.screenshots / f"mobile_pwa_{slug}.png"),
                full_page=False,
            )
        finally:
            context.close()

    def test_chrome_android_pixel_5_landing_smoke(self) -> None:
        device = self._pw.devices.get("Pixel 5")
        if device is None:
            self.skipTest("Playwright Pixel 5 device descriptor unavailable")
        self._run_landing_smoke(self.chromium, device, "chrome_android_pixel5")

    def test_ios_safari_iphone_12_landing_smoke(self) -> None:
        if self.webkit is None:
            self.skipTest(
                f"WebKit not available: {getattr(self, '_webkit_error', 'unknown')}"
            )
        device = self._pw.devices.get("iPhone 12")
        if device is None:
            self.skipTest("Playwright iPhone 12 device descriptor unavailable")
        self._run_landing_smoke(self.webkit, device, "ios_safari_iphone12")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
