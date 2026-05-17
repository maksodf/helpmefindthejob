"""R23.1 — end-to-end smoke for the merged Applications view.

Verifies:
  1. The legacy "Brief / Briefcase" nav item has been renamed to
     "Applications".
  2. The AI-brief textarea (#briefPrompt) is GONE.
  3. The manual-handoff buttons (#copyBriefBtn, #openInChatGPTBtn,
     #openInClaudeBtn, #runAnalysisBriefBtn) are GONE.
  4. The "Imported jobs" + "Application preparation" cards remain.
  5. The view-applications section is reachable by clicking the
     renamed nav item.
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


def _maybe_start_local_server() -> tuple[str, object | None]:
    base = os.environ.get("E2E_BASE_URL", "").rstrip("/")
    if base:
        return base, None
    PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_r23_1_smoke_"))
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
    base, httpd = _maybe_start_local_server()
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
            f"r231+{secrets.token_hex(3)}@example.com")
        page.locator("#registerPassword").fill("r231-pass-9X-test")
        page.locator("#registerForm button[type='submit']").click()
        page.wait_for_function(
            "() => { const g = document.querySelector('#authGate');"
            "        return !g || g.hidden || g.style.display === 'none'; }",
            timeout=25000,
        )

        # 1. Nav item — should say "Applications" not "Briefcase".
        nav_text = page.locator(".nav-item[data-view='applications']") \
                       .first.inner_text(timeout=4000)
        if "Applications" not in nav_text:
            findings.append(f"nav label = {nav_text!r}, expected 'Applications'")
        # Old Briefcase nav must be gone.
        old_count = page.locator(".nav-item[data-view='brief']").count()
        if old_count != 0:
            findings.append(f"legacy data-view='brief' still present ({old_count})")

        # 2. The applications view exists.
        if page.locator("#view-applications").count() == 0:
            findings.append("#view-applications section missing")

        # 3. The old brief textarea + buttons must be GONE.
        for dead_id in ("briefPrompt", "briefMeta", "copyBriefBtn",
                         "openInChatGPTBtn", "openInClaudeBtn",
                         "runAnalysisBriefBtn"):
            if page.locator(f"#{dead_id}").count() != 0:
                findings.append(f"legacy element #{dead_id} still in DOM")

        # 4. The imported-jobs + application-form cards remain.
        if page.locator("#importedJobsList").count() == 0:
            findings.append("#importedJobsList missing")
        if page.locator("#applicationForm").count() == 0:
            findings.append("#applicationForm missing")

        # 5. Click the renamed nav item → view-applications becomes visible.
        page.locator(".nav-item[data-view='applications']").click()
        page.wait_for_timeout(300)
        if page.locator("#view-applications").is_hidden():
            findings.append("view-applications still hidden after nav click")

        # 6. No JS console errors.
        console_errors: list[str] = []
        page.on("pageerror",
                  lambda exc: console_errors.append(f"[pageerror] {exc}"))
        page.on("console",
                  lambda msg: console_errors.append(
                      f"[{msg.type}] {msg.text}")
                  if msg.type in ("error",) else None)
        # Trigger a re-nav to catch any deferred errors. R25.1 — the
        # Assistant nav-item was removed; instead toggle between
        # Settings + Applications.
        page.locator(".nav-item[data-view='settings']").click()
        page.wait_for_timeout(400)
        page.locator(".nav-item[data-view='applications']").click()
        page.wait_for_timeout(400)
        real_errors = [e for e in console_errors
                        if "Content Security Policy" not in e]
        if real_errors:
            findings.append(
                "console errors: " + " | ".join(real_errors[:3]))

        out = Path(os.environ.get(
            "E2E_SCREENSHOTS", "tests/e2e/screenshots"))
        out.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out / "r23_1_applications.png"),
                          full_page=True)
        ctx.close()
        browser.close()

    if httpd is not None:
        httpd.shutdown()

    print()
    print("=" * 60)
    if findings:
        print(f"R23.1 APPLICATIONS-VIEW SMOKE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("R23.1 APPLICATIONS-VIEW SMOKE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
