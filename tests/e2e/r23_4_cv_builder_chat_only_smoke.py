"""R23.4 — verify CV Builder is no longer a top-level nav item but
remains reachable via the chat's open_cv_builder / show_view flow.
"""

from __future__ import annotations

import os
import secrets
import sys
import threading
import time
import tempfile
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
    PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_r23_4_smoke_"))
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


def main() -> int:
    base = os.environ.get("E2E_BASE_URL", "").rstrip("/")
    httpd = None
    if not base:
        base, httpd = _start_local_server()
    findings: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
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
        try:
            if page.locator("#registerTos").is_visible(timeout=400):
                page.locator("#registerTos").check()
                page.locator("#registerPrivacy").check()
        except Exception:
            pass
        page.locator("#registerForm").wait_for(state="visible", timeout=10000)
        page.locator("#registerEmail").fill(
            f"r234+{secrets.token_hex(3)}@example.com")
        page.locator("#registerPassword").fill("r234-pass-9X-test")
        page.locator("#registerForm button[type='submit']").click()
        page.wait_for_function(
            "() => { const g = document.querySelector('#authGate');"
            "        return !g || g.hidden || g.style.display === 'none'; }",
            timeout=25000,
        )

        # 1. The CV Builder nav button is GONE.
        nav_count = page.locator(".nav-item[data-view='cvBuilder']").count()
        if nav_count != 0:
            findings.append(
                f"CV Builder nav-item still present ({nav_count} found)")

        # 2. The #view-cvBuilder section STILL EXISTS in the DOM (so
        # the chat can show_view it).
        view_count = page.locator("#view-cvBuilder").count()
        if view_count != 1:
            findings.append(
                f"view-cvBuilder count = {view_count}, expected 1")

        # 3. JS navigate('cvBuilder') reveals the canvas. This is the
        # path the chat takes via show_view.
        page.evaluate(
            "() => { if (typeof navigate === 'function')"
            "          navigate('cvBuilder'); }")
        page.wait_for_timeout(300)
        if page.locator("#view-cvBuilder").is_hidden():
            findings.append(
                "view-cvBuilder hidden after navigate('cvBuilder')")

        ctx.close()
        browser.close()

    if httpd is not None:
        httpd.shutdown()

    print()
    print("=" * 60)
    if findings:
        print(f"R23.4 CV-BUILDER-CHAT-ONLY SMOKE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("R23.4 CV-BUILDER-CHAT-ONLY SMOKE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
