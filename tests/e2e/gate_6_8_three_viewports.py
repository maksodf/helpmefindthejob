# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 18 — Gate 6.8 mobile viewport tests (3 viewports).

Operator-spec viewports: 320 / 375 / 768. For each, verifies:

  - Touch targets >= 44px (CSS spec for mobile tap targets;
    avoids fat-finger misses)
  - No horizontal scroll on the chat surface (document.body.scrollWidth
    must equal the viewport width)
  - Chat input + send button reachable (visible, within viewport)
  - Sidebar nav reachable OR collapsed appropriately (mobile-pattern)

Note: on-screen-keyboard occlusion is NOT testable in headless
Playwright because virtual keyboards don't render in desktop
Chromium. Documented as a manual-spot-check gap in the closure
section; the CSS @media queries that handle keyboard behavior
are in `static/styles.css` (3 mobile breakpoints: 1099/768/480).

Closure criterion: 3 viewports × 4-5 asserts each = 12-15
invariants. All pass = Gate 6.8 closed.

Run via scripts/run-gate-6-8-smoke.sh.
"""
from __future__ import annotations

import os
import secrets
import sys
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

# Operator-spec viewports
VIEWPORTS = [
    {"name": "320 (smallest mobile)", "width": 320, "height": 568},
    {"name": "375 (iPhone SE/8/X)", "width": 375, "height": 667},
    {"name": "768 (iPad portrait)", "width": 768, "height": 1024},
]

# Touch-target spec (Apple HIG + Material Design): >= 44px
TOUCH_TARGET_MIN_PX = 44

RESULTS: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name}{(' — ' + detail) if detail else ''}")
    RESULTS.append((name, ok, detail))


def _register_via_ui(page, email: str) -> None:
    page.goto(BASE_URL + "/")
    page.locator("#authGate, #mainContent").first.wait_for(state="visible")
    try:
        if page.locator("#registerTos").is_visible(timeout=400):
            page.locator("#registerTos").check()
            page.locator("#registerPrivacy").check()
    except Exception:  # noqa: BLE001
        pass
    page.locator("#registerForm").wait_for(state="visible", timeout=10000)
    page.locator("#registerEmail").fill(email)
    page.locator("#registerPassword").fill("gate-6-8-99-X")
    page.locator("#registerForm button[type='submit']").click()
    # Viewport-agnostic "logged in" signal: wait for the auth gate
    # to disappear AND the main content to render. #sidebarUserEmail
    # works on desktop but is hidden by mobile CSS (sidebar collapses
    # below 1099px), so we can't use it at the 3 Gate 6.8 viewports.
    page.locator("#mainContent").wait_for(state="visible", timeout=25000)
    page.wait_for_timeout(300)  # brief settle for bootstrap fetch
    # Dismiss first-run wizard
    try:
        if page.locator("#firstRunWizard").is_visible(timeout=600):
            if page.locator("#wizardDismiss").is_visible(timeout=200):
                page.locator("#wizardDismiss").click()
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(150)
    except Exception:  # noqa: BLE001
        pass
    # Open chat
    page.locator(".nav-item[data-view='assistant']").click()
    page.locator("#view-assistant:not([hidden])").wait_for(timeout=5000)


def _test_viewport(browser, viewport: dict) -> None:
    """Spin up a fresh context at this viewport + run the 4-5
    invariant checks."""
    name = viewport["name"]
    w = viewport["width"]
    h = viewport["height"]
    email = f"gate68-{secrets.token_hex(3)}@example.test"

    context = browser.new_context(viewport={"width": w, "height": h})
    page = context.new_page()
    try:
        _register_via_ui(page, email)

        # Invariant 1: no horizontal scroll
        scroll_width = page.evaluate("document.body.scrollWidth")
        ok = scroll_width <= w + 2  # ±2px tolerance for sub-pixel rounding
        report(
            f"{name}: no horizontal scroll",
            ok,
            f"body.scrollWidth={scroll_width}, viewport={w}",
        )

        # Invariant 2: chat input visible + within viewport
        try:
            input_box = page.locator("#chatInput").bounding_box(timeout=3000)
        except Exception:  # noqa: BLE001
            input_box = None
        ok = input_box is not None and input_box["width"] <= w + 2
        report(
            f"{name}: chat input within viewport",
            ok,
            f"input width={input_box['width']:.0f}px" if input_box else "missing",
        )

        # Invariant 3: send button reachable (touch-target ≥ 44px)
        # The chat send button may be the submit button OR an Enter-
        # press; check the visible send-related control.
        send_candidates = [
            "#chatForm button[type='submit']",
            "#chatSendButton",
            "#chatForm button",
        ]
        send_box = None
        for selector in send_candidates:
            try:
                loc = page.locator(selector).first
                if loc.count() > 0:
                    send_box = loc.bounding_box(timeout=1000)
                    if send_box:
                        break
            except Exception:  # noqa: BLE001
                continue
        if send_box:
            ok = send_box["height"] >= TOUCH_TARGET_MIN_PX and send_box["width"] >= TOUCH_TARGET_MIN_PX
            report(
                f"{name}: send button touch-target >= {TOUCH_TARGET_MIN_PX}px",
                ok,
                f"send={send_box['width']:.0f}x{send_box['height']:.0f}px",
            )
        else:
            # Chat input may use Enter-only (no separate send button)
            # which is acceptable on mobile if the input itself is
            # large enough.
            ok = input_box is not None and input_box["height"] >= TOUCH_TARGET_MIN_PX
            report(
                f"{name}: chat input touch-target >= {TOUCH_TARGET_MIN_PX}px (no separate send button)",
                ok,
                f"input height={input_box['height']:.0f}px" if input_box else "missing",
            )

        # Invariant 4: nav reachable (either visible or accessible via
        # menu toggle on smaller viewports)
        # On 320/375, sidebar may collapse; on 768, sidebar may be
        # visible. Test for at least ONE nav-item being reachable.
        try:
            nav_visible = page.locator(".nav-item[data-view='assistant']").is_visible(timeout=500)
        except Exception:  # noqa: BLE001
            nav_visible = False
        # Look for menu-toggle if nav isn't directly visible
        menu_toggle_visible = False
        try:
            menu_toggle_visible = page.locator("#menuToggle, .menu-toggle, [aria-label*='menu' i]").first.is_visible(timeout=500)
        except Exception:  # noqa: BLE001
            pass
        ok = nav_visible or menu_toggle_visible
        report(
            f"{name}: nav reachable (direct or via toggle)",
            ok,
            f"direct={nav_visible} toggle={menu_toggle_visible}",
        )

        # Invariant 5: chat transcript scrollable (overflow-y in CSS)
        # Verify the transcript host has overflow-y visible AND a
        # height bounded by the viewport (so it scrolls instead of
        # pushing the input off-screen).
        transcript_overflow = page.evaluate(
            "() => { "
            "  const el = document.querySelector('#chatTranscript');"
            "  if (!el) return null;"
            "  const style = window.getComputedStyle(el);"
            "  return {overflowY: style.overflowY, height: el.clientHeight};"
            "}"
        )
        if transcript_overflow:
            scrollable = transcript_overflow["overflowY"] in (
                "auto", "scroll", "overlay"
            )
            bounded = transcript_overflow["height"] < h
            ok = scrollable and bounded
            report(
                f"{name}: chat transcript scrollable + bounded",
                ok,
                f"overflow={transcript_overflow['overflowY']} h={transcript_overflow['height']}",
            )
        else:
            report(
                f"{name}: chat transcript scrollable + bounded",
                False,
                "transcript element not found",
            )

    finally:
        context.close()


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for viewport in VIEWPORTS:
                print(f"\n--- Viewport: {viewport['name']} ({viewport['width']}x{viewport['height']}) ---")
                _test_viewport(browser, viewport)
        finally:
            browser.close()

    failed = [(name, detail) for (name, ok, detail) in RESULTS if not ok]
    if failed:
        print(f"\n{len(failed)} of {len(RESULTS)} test(s) FAILED:")
        for name, detail in failed:
            print(f"  - {name}{(' — ' + detail) if detail else ''}")
        return 1
    print(f"\nAll {len(RESULTS)} viewport invariants passed across {len(VIEWPORTS)} viewports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
