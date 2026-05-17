"""R23.2 — verify the AI provider picker is no longer visible by default.

Vision: only an "Advanced" collapsible exposes BYOK / CLI / custom
config. Default user sees just "Your subscription covers the AI".
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
    PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_r23_2_smoke_"))
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
            f"r232+{secrets.token_hex(3)}@example.com")
        page.locator("#registerPassword").fill("r232-pass-9X-test")
        page.locator("#registerForm button[type='submit']").click()
        page.wait_for_function(
            "() => { const g = document.querySelector('#authGate');"
            "        return !g || g.hidden || g.style.display === 'none'; }",
            timeout=25000,
        )

        # Use JS-driven navigation (sidebar buttons may be off-screen
        # at narrower viewports or behind a wizard overlay; navigate()
        # is the same function the click handlers call).
        page.evaluate(
            "() => { if (typeof navigate === 'function') navigate('settings'); }")
        page.locator("#view-settings:not([hidden])").wait_for(timeout=5000)
        page.wait_for_timeout(300)
        # R26.3 — the AI Provider card moved to data-tab="developer"
        # (out of normal user view). Switch to that tab to find it.
        page.evaluate(
            "() => { if (typeof setSettingsTab === 'function')"
            "          setSettingsTab('developer'); }")
        page.wait_for_timeout(200)

        # 1. The AI assistant card heading should say "AI assistant"
        # (not the old "AI brief & cover letters — pick how it runs").
        ai_card = page.locator("section[aria-label='AI Provider']")
        if ai_card.count() != 1:
            findings.append("AI Provider card not found in settings")
        else:
            heading = ai_card.locator("h2").first.inner_text(timeout=2000)
            if "AI assistant" not in heading:
                findings.append(f"heading={heading!r}, expected 'AI assistant'")

        # 2. The 3-mode picker buttons must NOT be visible by default
        # (they live inside an unopened <details>).
        managed_btn = page.locator(".ai-mode[data-ai-mode='managed']")
        byok_btn = page.locator(".ai-mode[data-ai-mode='byok']")
        # Managed button is removed entirely (no managed mode in advanced —
        # managed IS the default and not user-selectable).
        if managed_btn.count() != 0:
            findings.append(
                "managed-mode button still in DOM — should be removed "
                "(managed is the implicit default now, not a picker option)")
        # BYOK button exists but should be hidden (inside closed details).
        if byok_btn.count() != 1:
            findings.append(f"byok button count = {byok_btn.count()}, expected 1")
        elif byok_btn.is_visible():
            findings.append(
                "byok button visible by default — should be inside "
                "the closed Advanced collapsible")

        # 3. The Advanced summary text must be friendly.
        adv_summary = page.locator(".ai-advanced > summary").first
        if adv_summary.count() != 0:
            txt = adv_summary.inner_text(timeout=2000)
            if "Advanced" not in txt:
                findings.append(f"advanced summary = {txt!r}")

        # 4. Expanding Advanced reveals the BYOK button.
        if adv_summary.count() != 0:
            diag = page.evaluate(
                "() => { const d = document.querySelector('.ai-advanced');"
                "        if (d) d.open = true;"
                "        const b = document.querySelector("
                "          '.ai-mode[data-ai-mode=\"byok\"]');"
                "        if (!b) return {status: 'missing'};"
                "        const s = window.getComputedStyle(b);"
                "        const r = b.getBoundingClientRect();"
                "        return {open: d && d.open, display: s.display,"
                "          visibility: s.visibility, w: r.width, h: r.height,"
                "          parentDisplay: window.getComputedStyle(b.parentElement).display}; }"
            )
            print(f"[diag] byok after open: {diag}")
            if not (diag.get("w", 0) > 0 and diag.get("h", 0) > 0):
                findings.append(
                    f"byok button still not visible: {diag}")

        out = Path(os.environ.get(
            "E2E_SCREENSHOTS", "tests/e2e/screenshots"))
        out.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out / "r23_2_ai_picker_hidden.png"),
                          full_page=True)
        ctx.close()
        browser.close()

    if httpd is not None:
        httpd.shutdown()

    print()
    print("=" * 60)
    if findings:
        print(f"R23.2 AI-PICKER-HIDDEN SMOKE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("R23.2 AI-PICKER-HIDDEN SMOKE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
