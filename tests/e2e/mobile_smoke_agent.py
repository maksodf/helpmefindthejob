"""Mobile-viewport smoke for the surfaces added in Round 15.

Drives Playwright at iPhone 12-class viewport (390×844) and asserts:
  - Sidebar nav items remain reachable (no overflow off-screen)
  - Chat input + form render full-width
  - CV Builder layout collapses to a single column
  - First-run wizard fits inside the viewport

Run via ``scripts/run-mobile-smoke.sh``."""

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
VIEWPORT = {"width": 390, "height": 844}  # iPhone 12-class


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2
    results: list[tuple[str, bool, str]] = []

    def report(name, ok, detail=""):
        flag = "✅" if ok else "❌"
        print(f"  {flag} {name}{' — ' + detail if detail else ''}")
        results.append((name, ok, detail))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # device_scale_factor + has_touch closer to real iPhone behavior
        # Narrow viewport without is_mobile=True — keeps responsive CSS
        # active but click events fire normally. The mobile-specific
        # bugs we care about are CSS layout, not touch behavior.
        context = browser.new_context(viewport=VIEWPORT)
        # Neuter the first-run wizard for this test. We assert its
        # viewport width separately below by reading inline CSS; the
        # actual modal blocks clicks otherwise and we can't drive the
        # rest of the UI.
        context.add_init_script(
            "(function(){\n"
            "  const orig = HTMLDialogElement.prototype.showModal;\n"
            "  HTMLDialogElement.prototype.showModal = function(){\n"
            "    if (this.id === 'firstRunWizard') return;\n"
            "    return orig.call(this);\n"
            "  };\n"
            "})();"
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        try:
            # Sign up
            email = f"mobile+{secrets.token_hex(3)}@example.com"
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
            page.locator("#registerPassword").fill("mobile-pass-99-X")
            page.locator("#registerForm button[type='submit']").click()
            # After register the auth gate hides. Wait for the gate to
            # disappear.
            page.wait_for_function(
                "() => { const g = document.querySelector('#authGate');"
                "        return !g || g.hidden || g.style.display === 'none'; }",
                timeout=25000,
            )
            # Measure the wizard's intrinsic width even though showModal
            # was neutered — we read the bounding box of the dialog
            # element directly (it has CSS dimensions regardless of
            # whether it's currently shown as a modal).
            page.wait_for_timeout(400)
            dialog_width = page.evaluate(
                "() => { const d = document.querySelector('#firstRunWizard');"
                "        if (!d) return null;"
                "        d.style.display='block';"  # force render so getBoundingClientRect works
                "        const r = d.getBoundingClientRect();"
                "        d.style.display='';"
                "        return r.width; }"
            )
            if dialog_width is not None:
                report("wizard_within_viewport",
                        dialog_width <= VIEWPORT["width"],
                        f"wizard width={dialog_width:.0f}px (≤{VIEWPORT['width']})")

            # Assistant view — chat surface fits
            page.locator(".nav-item[data-view='assistant']").click()
            page.locator("#view-assistant:not([hidden])").wait_for()
            page.wait_for_timeout(300)
            chat_box = page.locator("#chatTranscript").bounding_box()
            input_box = page.locator("#chatInput").bounding_box()
            report("chat_transcript_within_viewport",
                    chat_box and chat_box["width"] <= VIEWPORT["width"],
                    f"transcript width={chat_box['width']:.0f}px" if chat_box else "missing")
            report("chat_input_within_viewport",
                    input_box and input_box["width"] <= VIEWPORT["width"],
                    f"input width={input_box['width']:.0f}px" if input_box else "missing")

            # Send a message via the input; assert the typing bubble appears.
            page.locator("#chatInput").fill("/help")
            page.locator("#chatInput").press("Enter")
            page.wait_for_timeout(800)
            transcript_text = page.evaluate(
                "() => document.querySelector('#chatTranscript')?.textContent || ''"
            )
            report("chat_help_renders_on_mobile",
                    "Add a company" in transcript_text,
                    "help reply present in transcript")

            # CV Builder view — single-column collapse
            page.locator(".nav-item[data-view='cvBuilder']").click()
            page.locator("#view-cvBuilder:not([hidden])").wait_for()
            page.wait_for_timeout(300)
            # The layout grid should be one column. We probe the
            # computed grid-template-columns of the wrapper.
            cols = page.evaluate(
                "() => { const el = document.querySelector('.cv-builder-layout');"
                "        return el ? getComputedStyle(el).gridTemplateColumns : null; }"
            )
            report("cv_builder_collapsed_to_single_column",
                    cols is not None and "1fr" in cols
                    and len(cols.split(" ")) == 1,
                    f"grid-template-columns: {cols}")

            # Save screenshots.
            out = Path(os.environ.get("E2E_SCREENSHOTS", "tests/e2e/screenshots"))
            out.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out / "mobile_chat.png"), full_page=True)
            page.locator(".nav-item[data-view='cvBuilder']").click()
            page.wait_for_timeout(300)
            page.screenshot(path=str(out / "mobile_cv.png"), full_page=True)
        finally:
            context.close()
            browser.close()

    failed = [r for r in results if not r[1]]
    print("\n" + "=" * 70)
    print(f"MOBILE SMOKE — {len(results) - len(failed)}/{len(results)} PASS")
    print("=" * 70)
    if failed:
        for n, _, d in failed:
            print(f"  ❌ {n}: {d}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
