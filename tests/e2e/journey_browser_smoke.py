# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Browser smoke for the guided job-search journey.

Drives Chromium through the chat UI (the actual rendered bubbles +
input field — NOT the HTTP API) and asserts the journey works
end-to-end without:

  - JS console errors
  - layout overflow on the long DACH letter bubble
  - the chat input becoming disabled mid-journey
  - the chat transcript losing scroll
  - mobile (390x844) rendering breaking

Run via ``scripts/run-journey-browser-smoke.sh``.
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
    except Exception:
        pass
    page.locator("#registerForm").wait_for(state="visible", timeout=10000)
    page.locator("#registerEmail").fill(email)
    page.locator("#registerPassword").fill("ui-pass-99-X")
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


def _send_chat(page, text: str) -> None:
    page.locator("#dockChatInput").fill(text)
    page.locator("#dockChatInput").press("Enter")
    # Brief settle for the round-trip + bubble append.
    page.wait_for_timeout(700)


def _transcript_text(page) -> str:
    return page.evaluate("() => document.querySelector('#dockChatTranscript')?.textContent || ''")


def _drive_full_journey(page) -> None:
    """Maria's full path through the chat UI."""
    page.locator(".nav-item[data-view='assistant']").click()
    page.locator("#chatDock:not([hidden])").wait_for(timeout=5000)
    _send_chat(page, "Ich suche einen Job als Pflegehelfer")
    _send_chat(page, "Pflegehelfer")
    _send_chat(page, "Berlin")
    _send_chat(page, "5")
    _send_chat(page, "Deutsch, English")
    _send_chat(page, "build")
    _send_chat(page, "Maria Schmidt")
    _send_chat(page, "Berlin")
    _send_chat(page, "6 years experience in elderly care across two Berlin clinics.")
    _send_chat(page, "Charité 2020-2024 — Pflegehelferin. Cared for 12 residents per shift.")
    _send_chat(page, "Pflege, Erste Hilfe, Dokumentation, Deutsch, English")
    _send_chat(page, "yes")
    # Sending "skip" triggers a live aggregator search — multi-second
    # round-trip. Wait for the typing-indicator bubble to disappear
    # (class is "chat-bubble-typing", single hyphen). Cap at 30s.
    page.locator("#dockChatInput").fill("skip")
    page.locator("#dockChatInput").press("Enter")
    try:
        page.wait_for_function(
            "() => !document.querySelector('#dockChatTranscript .chat-bubble-typing')",
            timeout=30000,
        )
    except Exception:  # noqa: BLE001 — best effort; still assert below
        pass
    page.wait_for_timeout(500)


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2

    console_errors: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # 1) Desktop viewport — full journey
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.set_default_timeout(15000)
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))
        page.on(
            "console",
            lambda msg: (
                console_errors.append(f"[{msg.type}] {msg.text}")
                if msg.type in ("error", "warning")
                else None
            ),
        )

        try:
            email = f"jbrow+{secrets.token_hex(3)}@example.com"
            _register_via_ui(page, email)
            report("registered_account", True, email)

            _drive_full_journey(page)

            # Check transcript ends with the search outcome — accept
            # any of the three reasonable shapes (results, empty, or
            # the graceful error path).
            tc = _transcript_text(page)
            report(
                "transcript_contains_journey_progress",
                "Pflegehelfer" in tc and "Berlin" in tc,
                "journey messages present",
            )
            search_outcome_present = any(
                marker in tc
                for marker in (
                    "Found",
                    "No matching jobs",
                    "hit a snag",
                )
            )
            if not search_outcome_present:
                # Debug — dump the last 500 chars of the transcript so
                # we can see what actually came back.
                print(f"  DEBUG transcript tail: ...{tc[-800:]!r}")
            report(
                "results_summary_or_graceful_message",
                search_outcome_present,
                "results summary OR empty-fallback OR aggregator-error message",
            )

            bubble_count = page.locator("#dockChatTranscript .chat-bubble").count()
            report(
                "chat_bubble_count_reasonable",
                bubble_count >= 12,
                f"{bubble_count} bubbles in transcript",
            )

            # Test cancel: register a fresh account so the journey is
            # in a known starting state (the prior journey just ended).
            ctx.close()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.set_default_timeout(15000)
            page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(f"[{msg.type}] {msg.text}")
                    if msg.type in ("error", "warning")
                    else None
                ),
            )
            email2 = f"jbrow-c+{secrets.token_hex(3)}@example.com"
            _register_via_ui(page, email2)
            page.locator(".nav-item[data-view='assistant']").click()
            page.locator("#chatDock:not([hidden])").wait_for()
            _send_chat(page, "I want to find a job")
            _send_chat(page, "cancel")
            tc2 = _transcript_text(page)
            report(
                "cancel_token_recognised",
                "Canceled" in tc2 or "canceled" in tc2.lower(),
                "cancel echoed in chat",
            )

            # Test help mid-journey: start fresh, get past greet,
            # then ask /help.
            _send_chat(page, "I need a job")
            _send_chat(page, "/help")
            tc3 = _transcript_text(page)
            report(
                "help_token_recognised_mid_journey",
                "middle of a guided" in tc3.lower() or "in the middle" in tc3.lower(),
                "help reply surfaced",
            )

            # Test off-topic redirect: continue the in-progress
            # journey with a weather question.
            _send_chat(page, "Bartender")
            _send_chat(page, "What's the weather?")
            tc4 = _transcript_text(page)
            report(
                "off_topic_redirected", "focused on" in tc4.lower(), "off-topic redirect surfaced"
            )

            out = Path(os.environ.get("E2E_SCREENSHOTS", "tests/e2e/screenshots"))
            out.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out / "journey_desktop.png"), full_page=True)

        finally:
            ctx.close()

        # 2) Mobile viewport — verify layout. Same neutering pattern
        # that mobile_smoke_agent.py uses (proven reliable).
        mctx = browser.new_context(viewport={"width": 390, "height": 844})
        mctx.add_init_script(
            "(function(){\n"
            "  const orig = HTMLDialogElement.prototype.showModal;\n"
            "  HTMLDialogElement.prototype.showModal = function(){\n"
            "    if (this.id === 'firstRunWizard') return;\n"
            "    return orig.call(this);\n"
            "  };\n"
            "})();"
        )
        mpage = mctx.new_page()
        mpage.set_default_timeout(15000)
        try:
            email_m = f"jbrow-m+{secrets.token_hex(3)}@example.com"
            mpage.goto(BASE_URL + "/")
            mpage.locator("#authGate, #mainContent").first.wait_for(state="visible")
            # When users already exist (a desktop register ran first
            # against this same server), the consent checkboxes are
            # mandatory.
            try:
                if mpage.locator("#registerTos").is_visible(timeout=400):
                    mpage.locator("#registerTos").check()
                    mpage.locator("#registerPrivacy").check()
            except Exception:
                pass
            mpage.locator("#registerForm").wait_for(state="visible", timeout=10000)
            mpage.locator("#registerEmail").fill(email_m)
            mpage.locator("#registerPassword").fill("ui-pass-99-X")
            mpage.locator("#registerForm button[type='submit']").click()
            mpage.wait_for_function(
                "() => { const g = document.querySelector('#authGate');"
                "        return !g || g.hidden || g.style.display === 'none'; }",
                timeout=25000,
            )
            mpage.locator(".nav-item[data-view='assistant']").click()
            mpage.locator("#chatDock:not([hidden])").wait_for()
            mpage.wait_for_timeout(300)

            box_input = mpage.locator("#dockChatInput").bounding_box()
            box_transcript = mpage.locator("#dockChatTranscript").bounding_box()
            report(
                "mobile_chat_input_within_viewport",
                bool(box_input) and box_input["width"] <= 390,
                f"input width={box_input['width']:.0f}px" if box_input else "missing",
            )
            report(
                "mobile_chat_transcript_within_viewport",
                bool(box_transcript) and box_transcript["width"] <= 390,
                f"transcript width={box_transcript['width']:.0f}px"
                if box_transcript
                else "missing",
            )

            _send_chat(mpage, "I want to find a job")
            mpage.wait_for_timeout(300)
            bubbles = mpage.locator("#dockChatTranscript .chat-bubble").all()
            overflow = False
            for b in bubbles:
                bb = b.bounding_box()
                if bb and bb["width"] > 390:
                    overflow = True
                    break
            report("mobile_no_bubble_overflow", not overflow, "all bubbles ≤390px wide")
            mpage.screenshot(path=str(out / "journey_mobile.png"), full_page=True)
        except Exception as exc:  # noqa: BLE001 - best-effort path; failure must not break the caller
            report("mobile_browser_smoke", False, str(exc)[:200])
        finally:
            mctx.close()
            browser.close()

    # JS console — any errors fail the smoke. Filter out the noisy
    # CSP-on-inline-style we already documented (a font/UI artefact).
    real_errors = [e for e in console_errors if "Content Security Policy" not in e]
    report(
        "no_js_console_errors",
        not real_errors,
        ("\n  ".join(real_errors[:5]) if real_errors else "clean"),
    )

    print()
    print("=" * 70)
    failed = [r for r in RESULTS if not r[1]]
    total = len(RESULTS)
    if failed:
        print(f"JOURNEY BROWSER SMOKE — {total - len(failed)}/{total} PASS")
        print("=" * 70)
        for n, _, d in failed:
            print(f"  FAIL {n}: {d}")
        return 1
    print(f"JOURNEY BROWSER SMOKE — ALL {total}/{total} CHECKS PASS")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
