"""R22.12 — Mobile chat bubble overflow stress.

Boots a local server (or hits E2E_BASE_URL if set), drives a 390x844
mobile viewport, and pushes 4 adversarial assistant bubbles into the
transcript that LLM responses might realistically contain:

  1. A 2000-char narrative paragraph
  2. A 95-char unbroken URL
  3. A 60-char unbroken word (chemical name etc.)
  4. A 1500-char preformatted code block

For each, asserts that the bubble's rendered width does NOT exceed
the viewport width minus the chat-input padding. Without R22.12's
``word-break: break-word`` + ``overflow-wrap: anywhere`` rules,
items 2 and 3 forced a horizontal scrollbar on the chat panel.

Run via ``scripts/run-mobile-overflow-smoke.sh`` (or directly with
E2E_BASE_URL pointing at any running server).
"""

from __future__ import annotations

import os
import secrets
import sys
import threading
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


def _maybe_start_local_server() -> tuple[str, object | None]:
    """If E2E_BASE_URL is set, use it. Otherwise spin up a local
    app.Handler for the duration of the test."""
    base = os.environ.get("E2E_BASE_URL", "").rstrip("/")
    if base:
        return base, None
    os.environ.setdefault("DIRECTJOB_DB_PATH",
                           "/tmp/directjob_overflow_smoke.sqlite")
    os.environ.setdefault("DIRECTJOB_REGISTER_LIMIT", "999")
    os.environ.setdefault("DIRECTJOB_ALLOW_REGISTRATION", "true")
    for _p in ("/tmp/directjob_overflow_smoke.sqlite",
                "/tmp/directjob_overflow_smoke.sqlite-shm",
                "/tmp/directjob_overflow_smoke.sqlite-wal"):
        Path(_p).unlink(missing_ok=True)
    import http.server
    import app  # noqa: F401
    from app import Handler
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return f"http://127.0.0.1:{port}", httpd


LONG_NARRATIVE = (
    "Here are five strong bartender roles in Berlin. "
    "The top hit is at Hotel Adlon, which has been running a "
    "rotating beverage program since 2019; the manager there has "
    "a track record of promoting from within within 18 months. "
) * 8

LONG_URL = (
    "https://example.com/jobs/listing/very-long-unbroken-"
    "identifier-that-could-blow-out-mobile-layout-without-care-"
    "9237298473984"
)

LONG_UNBROKEN_WORD = "antidisestablishmentarianismunbreakablewordtest" + "X" * 20

LONG_PREFORMATTED = (
    "```\n"
    + "\n".join(
        f"  {i:03d}  some-very-long-line-of-output-no-spaces-{i*7}"
        for i in range(40)
    )
    + "\n```"
)


def main() -> int:
    base, httpd = _maybe_start_local_server()
    findings: list[tuple[str, str]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        # Suppress the first-run wizard.
        ctx.add_init_script(
            "(function(){\n"
            "  const orig = HTMLDialogElement.prototype.showModal;\n"
            "  HTMLDialogElement.prototype.showModal = function(){\n"
            "    if (this.id === 'firstRunWizard') return;\n"
            "    return orig.call(this);\n"
            "  };\n"
            "})();"
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)
        page.goto(base + "/")
        page.locator("#authGate, #mainContent").first.wait_for(state="visible")
        try:
            if page.locator("#registerTos").is_visible(timeout=400):
                page.locator("#registerTos").check()
                page.locator("#registerPrivacy").check()
        except Exception:
            pass
        page.locator("#registerForm").wait_for(state="visible", timeout=10000)
        page.locator("#registerEmail").fill(
            f"ov+{secrets.token_hex(3)}@example.com")
        page.locator("#registerPassword").fill("overflow-pass-9X")
        page.locator("#registerForm button[type='submit']").click()
        # The sidebar is hidden at mobile widths so #sidebarUserEmail
        # never becomes visible. Wait for the auth-gate to disappear
        # instead — that's the signal that login succeeded.
        try:
            page.wait_for_function(
                "() => { const g = document.querySelector('#authGate');"
                "        return !g || g.hidden || g.style.display === 'none'; }",
                timeout=25000,
            )
        except Exception:
            page.screenshot(path="/tmp/overflow_register_fail.png",
                              full_page=True)
            errs = page.evaluate(
                "() => Array.from(document.querySelectorAll('.form-error,.error,[data-error]'))"
                "  .map(e => e.textContent).join(' | ')"
            )
            print(f"register stuck — error elements: {errs!r}",
                  file=sys.stderr)
            raise
        # R25.1 — the standalone Assistant view was removed; dock is
        # visible everywhere now (mobile = main column).
        page.locator("#dockChatTranscript").wait_for(
            state="visible", timeout=10000)
        page.wait_for_timeout(300)

        # Inject 4 adversarial bubbles via the page's own chatAppendBubble
        # function so we exercise the same rendering path the LLM uses.
        for label, body in (
            ("narrative", LONG_NARRATIVE),
            ("long_url", LONG_URL),
            ("long_word", LONG_UNBROKEN_WORD),
            ("preformatted", LONG_PREFORMATTED),
        ):
            page.evaluate(
                "(text) => window.chatAppendBubble"
                " && window.chatAppendBubble('assistant', text)",
                body,
            )
        page.wait_for_timeout(200)

        # Verify every assistant bubble fits inside 390px.
        bubbles = page.locator(
            "#dockChatTranscript .chat-bubble-assistant").all()
        if not bubbles:
            findings.append(("setup", "no assistant bubbles rendered"))
        for i, b in enumerate(bubbles):
            bb = b.bounding_box()
            if bb is None:
                findings.append((f"bubble[{i}]", "no bounding box"))
                continue
            if bb["width"] > 390:
                findings.append((
                    f"bubble[{i}]",
                    f"width={bb['width']:.0f}px exceeds 390px viewport",
                ))
            if bb["x"] + bb["width"] > 391:
                findings.append((
                    f"bubble[{i}]",
                    f"right edge at {bb['x']+bb['width']:.0f}px exceeds 390",
                ))

        # Verify the chat transcript itself doesn't have a horizontal
        # scroll. document.scrollingElement covers the WHOLE document
        # since the dock is fixed and uses internal scrolling.
        transcript_overflow = page.evaluate(
            "() => {"
            "  const el = document.querySelector('#dockChatTranscript');"
            "  return el ? (el.scrollWidth - el.clientWidth) : 0;"
            "}"
        )
        if transcript_overflow > 1:  # 1px tolerance for sub-pixel
            findings.append((
                "transcript-h-scroll",
                f"transcript has {transcript_overflow}px horizontal overflow",
            ))

        # Page-level horizontal scrollbar = layout broke at page level.
        doc_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth"
            " - document.documentElement.clientWidth"
        )
        if doc_overflow > 1:
            findings.append((
                "document-h-scroll",
                f"document has {doc_overflow}px horizontal overflow",
            ))

        out = Path(os.environ.get(
            "E2E_SCREENSHOTS", "tests/e2e/screenshots"))
        out.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out / "mobile_overflow.png"),
                          full_page=True)

        ctx.close()
        browser.close()

    if httpd is not None:
        httpd.shutdown()

    print()
    print("=" * 60)
    if findings:
        print(f"MOBILE OVERFLOW SMOKE — {len(findings)} FINDING(S)")
        for sid, msg in findings:
            print(f"  FAIL [{sid}]: {msg}")
        return 1
    print("MOBILE OVERFLOW SMOKE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
