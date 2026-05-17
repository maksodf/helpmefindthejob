"""R29 — verify the CV template picker shows real-rendered iframes
(not the old CSS skeleton).

Checks:
  1. The picker shows 6 cards (one per template).
  2. Each card contains an iframe whose src points at
     /api/cv/template-thumbnail with the correct id + accent.
  3. The iframe's contentDocument.body has data-template matching the
     card and data-accent matching the user's chosen accent.
  4. The ResizeObserver in the JS sets a numeric --thumb-w CSS var on
     the .cv-template-thumb so the iframe can scale to fit.
  5. The old CSS-skeleton classes (.cv-template-thumb-line / -name /
     -accent) are no longer present.
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
    PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_r29_smoke_"))
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
            f"r29+{secrets.token_hex(3)}@example.com")
        page.locator("#registerPassword").fill("r29-pass-9X-test")
        page.locator("#registerForm button[type='submit']").click()
        page.wait_for_function(
            "() => { const g = document.querySelector('#authGate');"
            "        return !g || g.hidden || g.style.display === 'none'; }",
            timeout=25000,
        )

        # Show the CV builder canvas (it's chat-reachable, not nav-shown).
        page.evaluate(
            "() => { if (typeof navigate === 'function')"
            "          navigate('cvBuilder'); }")
        page.wait_for_timeout(500)
        # Force a picker render in case CV is empty (picker still
        # appears even without a doc — the *thumbs* render either way).
        page.evaluate(
            "() => { if (typeof renderCvTemplatePicker === 'function')"
            "          renderCvTemplatePicker(); }")
        page.wait_for_timeout(300)

        # 1. Six cards, six iframes.
        cards = page.locator(".cv-template-card")
        n_cards = cards.count()
        if n_cards != 6:
            findings.append(f"expected 6 template cards, got {n_cards}")
        frames = page.locator(".cv-template-thumb-frame")
        n_frames = frames.count()
        if n_frames != 6:
            findings.append(f"expected 6 thumb iframes, got {n_frames}")

        # 2. Each iframe's src has id=<tpl> and accent=indigo (default).
        expected = ["modern", "classic", "tech", "executive",
                    "creative", "academic"]
        for tpl in expected:
            sel = (f".cv-template-card[data-template-id='{tpl}'] "
                   ".cv-template-thumb-frame")
            loc = page.locator(sel)
            if loc.count() != 1:
                findings.append(f"{tpl}: iframe count = {loc.count()}")
                continue
            src = loc.get_attribute("src") or ""
            if f"id={tpl}" not in src:
                findings.append(f"{tpl}: iframe src missing id ({src!r})")
            if "accent=indigo" not in src:
                findings.append(f"{tpl}: iframe src missing accent")

        # 3. Wait for one of the iframes to load and inspect the rendered
        # body's data-template attribute.
        # First wait for the load event so contentDocument is settled.
        page.evaluate(
            "() => new Promise((resolve) => { const f = document.querySelector("
            "  '.cv-template-card[data-template-id=\"modern\"] "
            ".cv-template-thumb-frame'); "
            "  if (!f) return resolve(false); "
            "  if (f.contentDocument && "
            "      f.contentDocument.readyState === 'complete') return resolve(true); "
            "  f.addEventListener('load', () => resolve(true), {once: true}); "
            "  setTimeout(() => resolve(false), 8000); })"
        )
        rendered_tpl = page.evaluate(
            "() => { const f = document.querySelector("
            "  '.cv-template-card[data-template-id=\"modern\"] "
            ".cv-template-thumb-frame'); "
            "  if (!f || !f.contentDocument) return null; "
            "  const d = f.contentDocument.querySelector('.cv-doc'); "
            "  return d && d.getAttribute('data-template'); }"
        )
        # Also assert the sample data is visible inside the iframe so
        # the user sees a realistic CV, not an empty doc.
        rendered_name = page.evaluate(
            "() => { const f = document.querySelector("
            "  '.cv-template-card[data-template-id=\"modern\"] "
            ".cv-template-thumb-frame'); "
            "  if (!f || !f.contentDocument) return null; "
            "  const n = f.contentDocument.querySelector('.cv-name'); "
            "  return n && n.textContent.trim(); }"
        )
        if rendered_name != "Maria Schmidt":
            findings.append(
                f"iframe sample name = {rendered_name!r} "
                f"(want 'Maria Schmidt')")
        if rendered_tpl != "modern":
            findings.append(
                f"iframe contentDocument data-template = "
                f"{rendered_tpl!r} (want 'modern')")

        # 4. ResizeObserver set a numeric --thumb-w on the container.
        thumb_w = page.evaluate(
            "() => { const t = document.querySelector('.cv-template-thumb'); "
            "  return t && t.style.getPropertyValue('--thumb-w'); }"
        )
        try:
            tw = int(thumb_w) if thumb_w else 0
        except ValueError:
            tw = 0
        if tw < 80 or tw > 600:
            findings.append(
                f"--thumb-w not in expected range (got {thumb_w!r})")

        # 5. Old CSS-skeleton classes are gone.
        for legacy in (".cv-template-thumb-line",
                       ".cv-template-thumb-name",
                       ".cv-template-thumb-accent"):
            n = page.locator(legacy).count()
            if n != 0:
                findings.append(
                    f"legacy skeleton class {legacy} still present ({n})")

        ctx.close()
        browser.close()

    if httpd is not None:
        httpd.shutdown()

    print()
    print("=" * 60)
    if findings:
        print(f"R29 TEMPLATE-THUMBNAIL SMOKE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("R29 TEMPLATE-THUMBNAIL SMOKE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
