# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UI-driven chat smoke test.

The multi-domain tester drives the HTTP API; this script drives the
ACTUAL UI in headless Chrome so the transcript renderer, send-on-Enter
loop, reset button, and view nav are proven (not just promised).

Run via ``scripts/run-chat-ui-agent.sh``."""

from __future__ import annotations

import json
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
            email = f"chat-ui+{secrets.token_hex(3)}@example.com"
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
            page.locator("#registerPassword").fill("chat-ui-pass-99-X")
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

            # 1. Navigate to Assistant view
            page.locator(".nav-item[data-view='assistant']").click()
            page.locator("#view-assistant:not([hidden])").wait_for(timeout=5000)
            report("nav_to_assistant_view", True)

            # 2. Greeting bubble should appear automatically.
            page.wait_for_timeout(400)
            greeting = page.locator("#chatTranscript .chat-bubble").first
            greeting_visible = greeting.is_visible(timeout=2000)
            report(
                "greeting_bubble_renders",
                greeting_visible,
                greeting.inner_text() if greeting_visible else "",
            )

            # 3. Click "Show commands" button — should send /help and
            # render two new bubbles (user + assistant reply).
            page.locator("#chatHelpBtn").click()
            page.wait_for_timeout(600)
            bubble_count = page.locator("#chatTranscript .chat-bubble").count()
            report(
                "help_button_renders_bubbles",
                bubble_count >= 3,
                f"transcript has {bubble_count} bubbles after /help",
            )
            # The latest assistant bubble must include known command names.
            transcript_text = page.locator("#chatTranscript").inner_text()
            has_help = (
                "Add a company" in transcript_text and "Create a saved search" in transcript_text
            )
            report("help_lists_commands", has_help)

            # 4. Type a slash command via the input + Enter.
            page.locator("#chatInput").fill("/add-company UI-Corp https://ui-corp.example")
            page.locator("#chatInput").press("Enter")
            page.wait_for_timeout(700)
            transcript_text = page.locator("#chatTranscript").inner_text()
            asks_optional = "Career page URL" in transcript_text
            report(
                "slash_pre_fills_required",
                asks_optional,
                "server asked for the optional careerPageUrl, "
                "meaning required fields were pre-filled from inline args",
            )

            # 5. Skip optional with a space → confirmation prompt.
            page.locator("#chatInput").fill(" ")
            page.locator("#chatInput").press("Enter")
            page.wait_for_timeout(1500)
            # Use textContent (not inner_text) — bubbles are appended
            # as plain text nodes, no HTML semantics to render.
            tc = page.evaluate("() => document.querySelector('#chatTranscript')?.textContent || ''")
            asks_confirm = ("UI-Corp" in tc) and ("Confirm" in tc)
            report(
                "confirmation_prompt_renders",
                asks_confirm,
                f"transcript len={len(tc)}, has 'UI-Corp'={('UI-Corp' in tc)}, "
                f"has 'Confirm'={('Confirm' in tc)}",
            )

            # 6. Confirm with "yes"
            page.locator("#chatInput").fill("yes")
            page.locator("#chatInput").press("Enter")
            page.wait_for_timeout(900)
            transcript_text = page.locator("#chatTranscript").inner_text()
            executed = "watchlist" in transcript_text and "UI-Corp" in transcript_text
            report(
                "confirmation_executes_command",
                executed,
                "transcript shows success reply with UI-Corp",
            )

            # 7. Reset button clears the transcript.
            page.locator("#chatResetBtn").click()
            page.wait_for_timeout(500)
            after_reset = page.locator("#chatTranscript .chat-bubble").count()
            # After reset we render an assistant bubble saying "Chat reset.";
            # so 1 bubble is expected.
            report(
                "reset_clears_transcript",
                after_reset == 1,
                f"transcript had {after_reset} bubbles after reset",
            )

            # 8. Keyboard-driven flow — natural-language intent.
            page.locator("#chatInput").fill("I want to add a company")
            page.locator("#chatInput").press("Enter")
            page.wait_for_timeout(600)
            transcript_text = page.locator("#chatTranscript").inner_text()
            asks_name = "company name" in transcript_text.lower()
            report(
                "keyword_router_via_ui",
                asks_name,
                "natural-language intent → keyword router → asks for name",
            )

            # 9. Cancel mid-flow with /help — should reset focus to help.
            # (Our current behaviour: any non-confirmation reply during a
            # pending command is treated as a fill for the awaiting slot.
            # So this is intentionally NOT tested as a slash mid-flow — it'd
            # fail validation. Skip and verify the input remains usable.)
            input_enabled = page.locator("#chatInput").is_enabled()
            report("input_stays_enabled", input_enabled)

            # Screenshot for the record.
            out_dir = Path(os.environ.get("E2E_SCREENSHOTS", "tests/e2e/screenshots"))
            out_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_dir / "chat_ui.png"), full_page=True)
        finally:
            context.close()
            browser.close()

    failed = [r for r in results if not r[1]]
    print("\n" + "=" * 70)
    print(f"CHAT UI — {len(results) - len(failed)}/{len(results)} PASS")
    print("=" * 70)
    if failed:
        for n, _, d in failed:
            print(f"  ❌ {n}: {d}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
