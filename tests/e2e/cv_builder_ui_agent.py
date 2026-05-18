# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UI-driven CV-builder smoke test.

The HTTP integration in ``cv_builder_agent.py`` proves the API; this
script drives the actual UI in headless Chrome to confirm the wizard
renders, sections advance, photo upload works through the file
picker, and the final CV markdown lands on the profile.

Run via ``scripts/run-cv-builder-ui-agent.sh``."""

from __future__ import annotations

import base64
import os
import secrets
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:
    print("ERROR: Playwright not installed", file=sys.stderr)
    sys.exit(2)

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")


def _make_png() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def _ch(ty, data):
        crc = zlib.crc32(ty + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ty + data + struct.pack(">I", crc)

    ihdr = _ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = _ch(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    iend = _ch(b"IEND", b"")
    return sig + ihdr + idat + iend


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2

    results: list[tuple[str, bool, str]] = []

    def report(name: str, ok: bool, detail: str = "") -> None:
        flag = "✅" if ok else "❌"
        print(f"  {flag} {name}{' — ' + detail if detail else ''}")
        results.append((name, ok, detail))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(15000)

        try:
            # Register
            email = f"cvbuilder-ui+{secrets.token_hex(3)}@example.com"
            page.goto(BASE_URL + "/")
            page.locator("#authGate, #mainContent").first.wait_for(state="visible")
            try:
                if page.locator("#registerTos").is_visible(timeout=400):
                    page.locator("#registerTos").check()
                    page.locator("#registerPrivacy").check()
            except Exception:
                pass
            page.locator("#registerForm").wait_for(state="visible", timeout=10000)
            page.locator("#registerEmail").fill(email)
            page.locator("#registerPassword").fill("cvbuilder-ui-pass-99-X")
            page.locator("#registerForm button[type='submit']").click()
            page.locator("#sidebarUserEmail").wait_for(state="visible", timeout=25000)

            # Dismiss the first-run wizard if it pops up.
            try:
                if page.locator("#firstRunWizard").is_visible(timeout=600):
                    if page.locator("#wizardDismiss").is_visible(timeout=200):
                        page.locator("#wizardDismiss").click()
                    else:
                        page.keyboard.press("Escape")
                    page.wait_for_timeout(150)
            except Exception:
                pass

            # 1. Open CV Builder via nav
            page.locator(".nav-item[data-view='cvBuilder']").click()
            page.locator("#view-cvBuilder:not([hidden])").wait_for(timeout=5000)
            report("nav_to_cv_builder", True)

            # The state auto-loads but starts empty — click "Start over"
            # to ensure we're at section 1.
            page.locator("#cvBuilderStartBtn").click()
            page.locator("#cvBuilderSectionHost h3").wait_for(state="visible", timeout=5000)
            heading = page.locator("#cvBuilderSectionHost h3").inner_text()
            report(
                "section_one_renders_header",
                heading.lower().startswith("personal header"),
                f"got '{heading}'",
            )

            # 2. Fill header
            page.locator("#cvb_full_name").fill("Anna Müller")
            page.locator("#cvb_email").fill("anna@example.com")
            page.locator("#cvb_location").fill("Berlin")
            page.locator("#cvBuilderSaveBtn").click()
            page.wait_for_timeout(500)
            page.locator("#cvBuilderSectionHost h3").wait_for(state="visible")
            heading = page.locator("#cvBuilderSectionHost h3").inner_text()
            report(
                "advances_to_summary",
                heading.lower().startswith("professional summary"),
                f"got '{heading}'",
            )

            # 3. Upload photo via the file input (Playwright trick).
            png = _make_png()
            page.locator("#cvBuilderPhotoInput").set_input_files(
                {
                    "name": "photo.png",
                    "mimeType": "image/png",
                    "buffer": png,
                }
            )
            page.wait_for_timeout(800)
            photo_visible = page.locator("#cvBuilderPhotoPreview").is_visible()
            report("photo_preview_renders", photo_visible)
            photo_status = page.locator("#cvBuilderPhotoStatus").inner_text()
            report(
                "photo_status_reports_size",
                "Photo saved" in photo_status,
                f"status='{photo_status}'",
            )

            # 4. Fill summary
            page.locator("#cvb_summary_raw").fill("Senior backend engineer. 8 years Python.")
            page.locator("#cvBuilderSaveBtn").click()
            page.wait_for_timeout(500)
            # 5. Experience
            page.locator("#cvBuilderSectionHost h3").wait_for(state="visible")
            page.locator("#cvb_company_name").fill("Acme")
            page.locator("#cvb_job_title").fill("Senior Backend Engineer")
            page.locator("#cvb_start_date").fill("2022-01")
            page.locator("#cvb_end_date").fill("present")
            page.locator("#cvb_location").fill("Berlin")
            page.locator("#cvb_achievements_raw").fill(
                "Led migration to k8s. Built payments microservice."
            )
            page.locator("#cvBuilderSaveBtn").click()
            page.wait_for_timeout(500)
            # 6. Education
            page.locator("#cvBuilderSectionHost h3").wait_for(state="visible")
            page.locator("#cvb_school").fill("TU Berlin")
            page.locator("#cvb_degree").fill("MSc")
            page.locator("#cvb_field").fill("Computer Science")
            page.locator("#cvb_start_date").fill("2016")
            page.locator("#cvb_end_date").fill("2019")
            page.locator("#cvBuilderSaveBtn").click()
            page.wait_for_timeout(500)
            # 7. Skills
            page.locator("#cvBuilderSectionHost h3").wait_for(state="visible")
            page.locator("#cvb_skills_raw").fill("Python, Postgres, Kubernetes, AWS")
            page.locator("#cvBuilderSaveBtn").click()
            page.wait_for_timeout(500)

            # 8. Certifications + Projects — use Skip button.
            for _ in range(3):
                finish = page.locator("#cvBuilderFinishBtn")
                if finish.is_visible(timeout=300):
                    break
                skip = page.locator("#cvBuilderSkipBtn")
                if skip.is_visible(timeout=300):
                    skip.click()
                    page.wait_for_timeout(500)
                else:
                    # Section is mandatory (required questions) — save with whatever.
                    save = page.locator("#cvBuilderSaveBtn")
                    if save.is_visible(timeout=300):
                        save.click()
                        page.wait_for_timeout(500)
                    else:
                        break

            # 9. Finish
            finish_btn = page.locator("#cvBuilderFinishBtn")
            finish_btn.wait_for(state="visible", timeout=5000)
            finish_btn.click()
            page.wait_for_timeout(800)
            msg = page.locator("#cvBuilderMessage").inner_text()
            report("finish_message_persisted", "CV saved" in msg and "chars" in msg, f"msg='{msg}'")

            # Take a screenshot for the record.
            out_dir = Path(os.environ.get("E2E_SCREENSHOTS", "tests/e2e/screenshots"))
            out_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_dir / "cv_builder_ui.png"), full_page=True)
        finally:
            context.close()
            browser.close()

    failed = [r for r in results if not r[1]]
    print("\n" + "=" * 70)
    print(f"CV BUILDER UI — {len(results) - len(failed)}/{len(results)} PASS")
    print("=" * 70)
    if failed:
        for n, _, d in failed:
            print(f"  ❌ {n}: {d}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
