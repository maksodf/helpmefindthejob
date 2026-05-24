# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 14.1 — Playwright verification of phase-aware
typing labels (Gate 6.6 closure).

Drives Chromium through the registered-user chat flow + intercepts
/api/chat/message to delay 2 s. During the delay the typing
bubble's narration text MUST contain the expected label for the
sent input. Closes "every >=2s op narrates SOMETHING" by automated
proof.

Run via ``scripts/run-typing-label-smoke.sh`` (boots dev server).
"""

from __future__ import annotations

import os
import secrets
import sys
import time
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
RESULTS: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name}{(' — ' + detail) if detail else ''}")
    RESULTS.append((name, ok, detail))


def _register_via_ui(page, email: str) -> None:
    """Mirror of journey_browser_smoke._register_via_ui pattern."""
    page.goto(BASE_URL + "/")
    page.locator("#authGate, #mainContent").first.wait_for(state="visible")
    try:
        if page.locator("#registerTos").is_visible(timeout=400):
            page.locator("#registerTos").check()
            page.locator("#registerPrivacy").check()
    except Exception:  # noqa: BLE001 - tos/privacy may already be checked
        pass
    page.locator("#registerForm").wait_for(state="visible", timeout=10000)
    page.locator("#registerEmail").fill(email)
    page.locator("#registerPassword").fill("typing-label-99-X")
    page.locator("#registerForm button[type='submit']").click()
    page.locator("#sidebarUserEmail").wait_for(state="visible", timeout=25000)
    # Dismiss first-run wizard if it pops up
    try:
        if page.locator("#firstRunWizard").is_visible(timeout=600):
            if page.locator("#wizardDismiss").is_visible(timeout=200):
                page.locator("#wizardDismiss").click()
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(150)
    except Exception:  # noqa: BLE001
        pass
    # Open the assistant view + wait for chat input
    page.locator(".nav-item[data-view='assistant']").click()
    page.locator("#chatDock:not([hidden])").wait_for(timeout=5000)
    page.locator("#dockChatInput").wait_for(state="visible", timeout=5000)


def _send_chat_with_delay(page, message: str, delay_ms: int = 2500) -> str:
    """Send `message` via the chat input. Intercept /api/chat/message
    to delay `delay_ms` ms so the typing bubble is observable. Read
    the narration bubble's text mid-flight and return it.

    Robust against back-to-back tests: waits for chat input to be
    enabled, snapshots existing narration count BEFORE the send so
    the new bubble can be identified, uses short timeouts on the
    text-content read since the bubble is removed when the response
    arrives.
    """

    def _slow_handler(route):
        time.sleep(delay_ms / 1000.0)
        route.continue_()

    # Wait for chat input to be ready for new input
    page.locator("#dockChatInput").wait_for(state="visible", timeout=2000)
    # Snapshot how many narration bubbles exist BEFORE we send, so
    # we know the new one when it appears.
    existing_count = page.locator(".chat-bubble-narration").count()

    page.route("**/api/chat/message", _slow_handler)
    try:
        page.locator("#dockChatInput").fill(message)
        page.locator("#dockChatInput").press("Enter")
        # Poll for a NEW narration bubble (count() > existing) with a
        # short timeout. If it appears, read its text immediately.
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if page.locator(".chat-bubble-narration").count() > existing_count:
                # New narration bubble exists. Read its text BEFORE
                # the response arrives and removes it.
                bubbles = page.locator(".chat-bubble-narration").all()
                # Return the text of the LAST one (most recently added)
                if bubbles:
                    try:
                        text = bubbles[-1].text_content(timeout=500) or ""
                        return text.strip()
                    except Exception:  # noqa: BLE001 - bubble removed mid-read; race condition
                        return ""
            time.sleep(0.05)
        # Fallback: default-typing class for "Thinking…" without a label
        try:
            typing = page.locator(".chat-bubble-typing").last
            return (typing.text_content(timeout=500) or "").strip()
        except Exception:  # noqa: BLE001
            return ""
    finally:
        page.unroute("**/api/chat/message")


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL not set", file=sys.stderr)
        return 2

    email = f"typing-label-{secrets.token_hex(3)}@example.test"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            _register_via_ui(page, email)

            # Each test runs independently with continue-on-failure
            # so we get coverage on all 5 cases even if back-to-back
            # tests hit Playwright route-interception timing
            # fragility.
            test_cases = [
                (
                    "/start",
                    "default fallback label",
                    lambda L: "Thinking" in L or "Searching" in L or len(L) > 0,
                ),
                ("/tailor", "tailor label", lambda L: "Tailoring" in L),
                (
                    "/letter",
                    "letter label",
                    lambda L: "motivation letter" in L.lower() or "drafting" in L.lower(),
                ),
                (
                    "/consult",
                    "consult label",
                    lambda L: "Analyzing" in L or "improvement" in L.lower(),
                ),
                ("/find", "search label", lambda L: "Searching" in L),
            ]
            for msg, name, assertion in test_cases:
                try:
                    label = _send_chat_with_delay(page, msg)
                    ok = assertion(label)
                    report(f"{msg} shows {name}", ok, f"got={label[:80]!r}")
                except Exception as e:  # noqa: BLE001 - test-harness fragility under route interception
                    report(f"{msg} shows {name}", False, f"harness error: {e}")
        finally:
            context.close()
            browser.close()

    failed = [(name, detail) for (name, ok, detail) in RESULTS if not ok]
    if failed:
        print(f"\n{len(failed)} test(s) FAILED:")
        for name, detail in failed:
            print(f"  - {name}{(' — ' + detail) if detail else ''}")
        return 1
    print(f"\nAll {len(RESULTS)} typing-label tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
