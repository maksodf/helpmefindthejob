"""R25.1 — single chat surface (dock) end-to-end smoke.

Verifies the Assistant view + duplicate transcript are gone:
  1. ``.nav-item[data-view='assistant']`` element is absent.
  2. ``#view-assistant`` element is absent.
  3. ``#chatInput`` + ``#chatTranscript`` (the duplicate-surface IDs)
     are absent.
  4. The dock (``#chatDock``) is visible after login at desktop AND
     mobile viewports.
  5. Typing in ``#dockChatInput`` triggers a normal chat round-trip
     (one user bubble + at least one assistant bubble appear).
"""

from __future__ import annotations

import os
import secrets
import sys
import tempfile
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


def _start_local_server() -> tuple[str, object]:
    PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_r25_1_smoke_"))
    os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
    os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
    os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
    import http.server
    import app  # noqa: F401
    from app import Handler
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return f"http://127.0.0.1:{port}", httpd


def _register(page) -> None:
    try:
        if page.locator("#registerTos").is_visible(timeout=400):
            page.locator("#registerTos").check()
            page.locator("#registerPrivacy").check()
    except Exception:
        pass
    page.locator("#registerForm").wait_for(state="visible", timeout=10000)
    page.locator("#registerEmail").fill(
        f"r251+{secrets.token_hex(3)}@example.com")
    page.locator("#registerPassword").fill("r251-pass-9X-test")
    page.locator("#registerForm button[type='submit']").click()
    page.wait_for_function(
        "() => { const g = document.querySelector('#authGate');"
        "        return !g || g.hidden || g.style.display === 'none'; }",
        timeout=25000,
    )


def main() -> int:
    base = os.environ.get("E2E_BASE_URL", "").rstrip("/")
    httpd = None
    if not base:
        base, httpd = _start_local_server()
    findings: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # ── Desktop pass ────────────────────────────────────
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        ctx.add_init_script(
            "(function(){"
            "  const orig = HTMLDialogElement.prototype.showModal;"
            "  HTMLDialogElement.prototype.showModal = function(){"
            "    if (this.id === 'firstRunWizard') return;"
            "    return orig.call(this);"
            "  };"
            "})();"
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)
        page.goto(base + "/")
        page.locator("#authGate, #mainContent").first.wait_for(state="visible")
        _register(page)

        # 1. Assistant nav-item must be GONE.
        if page.locator(".nav-item[data-view='assistant']").count() != 0:
            findings.append("desktop: legacy assistant nav-item still present")
        # 2. #view-assistant must be GONE.
        if page.locator("#view-assistant").count() != 0:
            findings.append("desktop: #view-assistant still in DOM")
        # 3. Duplicate transcript IDs must be GONE.
        for dead_id in ("chatInput", "chatTranscript", "chatForm",
                         "chatHelpBtn", "chatResetBtn"):
            if page.locator(f"#{dead_id}").count() != 0:
                findings.append(f"desktop: legacy #{dead_id} still in DOM")
        # 4. Dock visible after login.
        dock = page.locator("#chatDock")
        if dock.count() != 1:
            findings.append("desktop: #chatDock missing")
        elif not dock.is_visible():
            findings.append("desktop: #chatDock present but hidden after login")
        # 5. Dock chat round-trip.
        page.locator("#dockChatInput").fill("hi")
        page.locator("#dockChatInput").press("Enter")
        page.wait_for_timeout(700)
        user_bubbles = page.locator(
            "#dockChatTranscript .chat-bubble-user").count()
        assistant_bubbles = page.locator(
            "#dockChatTranscript .chat-bubble-assistant").count()
        if user_bubbles < 1:
            findings.append(
                f"desktop: user bubble missing (count={user_bubbles})")
        if assistant_bubbles < 1:
            findings.append(
                f"desktop: assistant reply missing "
                f"(count={assistant_bubbles})")
        ctx.close()

        # ── Mobile pass ─────────────────────────────────────
        mctx = browser.new_context(viewport={"width": 390, "height": 844})
        mctx.add_init_script(
            "(function(){"
            "  const orig = HTMLDialogElement.prototype.showModal;"
            "  HTMLDialogElement.prototype.showModal = function(){"
            "    if (this.id === 'firstRunWizard') return;"
            "    return orig.call(this);"
            "  };"
            "})();"
        )
        mpage = mctx.new_page()
        mpage.set_default_timeout(15000)
        mpage.goto(base + "/")
        mpage.locator("#authGate, #mainContent").first.wait_for(
            state="visible")
        _register(mpage)
        # Mobile: dock MUST be visible (was previously hidden < 1100px).
        mdock = mpage.locator("#chatDock")
        if mdock.count() != 1 or not mdock.is_visible():
            findings.append(
                "mobile: #chatDock not visible at 390x844 — R25.1 regression")
        # Mobile: dock input must fit viewport.
        bb = mpage.locator("#dockChatInput").bounding_box()
        if bb and bb["width"] > 390:
            findings.append(
                f"mobile: dock input width={bb['width']:.0f}px exceeds 390")
        mctx.close()
        browser.close()

    if httpd is not None:
        httpd.shutdown()

    print()
    print("=" * 60)
    if findings:
        print(f"R25.1 DOCK-ONLY CHAT SMOKE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("R25.1 DOCK-ONLY CHAT SMOKE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
