# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UI-side XSS render check.

The API-level chaos agent verifies that HTML/JS payloads are accepted
and round-tripped through storage. This script verifies they are
*safely rendered* — i.e., when the UI displays a CV / company name /
application notes / etc. containing a ``<script>...</script>`` payload,
the script does NOT execute.

We inject a sentinel side-effect (``window.__chaos_xss_fired__ = true``)
into each chaos payload. If the UI is escaping correctly, the sentinel
stays undefined after the page renders. If it fires, the verifier
reports a critical-severity XSS finding.

Run via ``./scripts/run-chaos-ui-xss.sh``."""

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


SENTINEL = "__chaos_xss_fired__"

# Different XSS shapes — script tag, event handler, javascript: URL,
# svg vector, encoded variants. Each should NOT execute when rendered.
XSS_PAYLOADS = [
    ("script_tag", f"<script>window.{SENTINEL}_script=true</script>"),
    ("img_onerror", f"<img src=x onerror='window.{SENTINEL}_img=true'>"),
    ("svg_onload", f"<svg onload='window.{SENTINEL}_svg=true'></svg>"),
    ("a_javascript", f"<a href='javascript:window.{SENTINEL}_a=true'>x</a>"),
    ("body_onfocus", f"<body onfocus='window.{SENTINEL}_body=true'>"),
    ("iframe_srcdoc", f'<iframe srcdoc="<script>parent.{SENTINEL}_iframe=true</script>"></iframe>'),
    ("data_uri", f"<embed src='data:text/html,<script>top.{SENTINEL}_embed=true</script>'>"),
]


def _signup(page, email: str, password: str) -> None:
    page.goto(BASE_URL + "/")
    page.locator("#authGate, #mainContent").first.wait_for(state="visible", timeout=15000)
    if page.locator("#mainContent").is_visible(timeout=300):
        return
    page.locator("#registerForm").wait_for(state="visible", timeout=10000)
    # consent (if shown)
    try:
        if page.locator("#registerTos").is_visible(timeout=300):
            page.locator("#registerTos").check()
            page.locator("#registerPrivacy").check()
    except Exception:
        pass
    page.locator("#registerEmail").fill(email)
    page.locator("#registerPassword").fill(password)
    page.locator("#registerForm button[type='submit']").click()
    page.locator("#sidebarUserEmail").wait_for(state="visible", timeout=20000)


def _dismiss_wizard(page) -> None:
    try:
        if page.locator("#firstRunWizard").is_visible(timeout=400):
            dismiss = page.locator("#wizardDismiss")
            if dismiss.is_visible(timeout=300):
                dismiss.click()
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(150)
    except Exception:
        pass


def _check_no_xss(page, surface: str, payload_name: str) -> tuple[bool, str]:
    """Verify no sentinel keys appear on window. Returns (ok, detail)."""
    fired_keys = page.evaluate(f"() => Object.keys(window).filter(k => k.startsWith('{SENTINEL}'))")
    if fired_keys:
        return False, (f"{surface}: XSS sentinel fired via {payload_name}: keys={fired_keys}")
    return True, f"{surface}: no XSS fired ({payload_name} rendered inert)"


def run_xss_sweep() -> list[dict]:
    """One user, all payloads run sequentially. After each payload we
    page.reload() to wipe the JS window and check for sentinel fire."""
    results: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)
        email = f"chaos-xss-{secrets.token_hex(3)}@example.com"
        try:
            _signup(page, email, "chaos-ui-xss-pass-99-X")
            _dismiss_wizard(page)

            for payload_name, payload in XSS_PAYLOADS:
                try:
                    # Surface 1: CV render via Settings.
                    page.locator(".nav-item[data-view='settings']").click()
                    page.locator("#view-settings:not([hidden])").wait_for()
                    cv = page.locator("#profileCvText")
                    cv.wait_for(state="visible", timeout=5000)
                    cv.fill(f"Senior Engineer. {payload}")
                    # Trigger profile save via the explicit button (the
                    # form has type='button' on its submit, so we must
                    # click the named button rather than submit-on-enter).
                    save = page.locator("#saveProfileBtn")
                    save.wait_for(state="visible", timeout=5000)
                    save.click()
                    page.wait_for_timeout(700)
                    # Reload so the CV is re-rendered from a fresh bootstrap.
                    page.reload()
                    page.locator("#sidebarUserEmail").wait_for(state="visible")
                    page.wait_for_timeout(600)
                    page.locator(".nav-item[data-view='settings']").click()
                    page.wait_for_timeout(400)
                    ok, detail = _check_no_xss(page, "cv_render", payload_name)
                    results.append(
                        {"payload": payload_name, "surface": "cv", "ok": ok, "detail": detail}
                    )

                    # Surface 2: Company name in queue / detail render.
                    page.locator(".nav-item[data-view='companies']").click()
                    page.wait_for_timeout(300)
                    # The companyForm is inside a collapsed <details>;
                    # open it via JS so the inputs become visible.
                    page.evaluate(
                        "document.querySelector('#companyForm')"
                        "?.closest('details')?.setAttribute('open', '')"
                    )
                    page.wait_for_timeout(150)
                    name_input = page.locator("#companyForm input[name='name']")
                    name_input.fill(f"Evil-Corp-{payload_name} {payload}")
                    page.locator("#companyForm input[name='websiteUrl']").fill(
                        f"https://evil-{payload_name}.example"
                    )
                    page.locator("#companyForm button[type='submit']").click()
                    page.wait_for_timeout(800)
                    page.reload()
                    page.locator("#sidebarUserEmail").wait_for(state="visible")
                    page.locator(".nav-item[data-view='companies']").click()
                    page.wait_for_timeout(600)
                    ok, detail = _check_no_xss(page, "company_name", payload_name)
                    results.append(
                        {
                            "payload": payload_name,
                            "surface": "company_name",
                            "ok": ok,
                            "detail": detail,
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - best-effort path; failure must not break the caller
                    results.append(
                        {
                            "payload": payload_name,
                            "surface": "error",
                            "ok": False,
                            "detail": f"{type(exc).__name__}: {exc}",
                        }
                    )
        finally:
            context.close()
            browser.close()
    return results


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL is required", file=sys.stderr)
        return 2
    print(f"[chaos-ui-xss] base_url={BASE_URL}")
    results = run_xss_sweep()
    out = Path(os.environ.get("E2E_XSS_REPORT", "tests/e2e/chaos_ui_xss_report.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("UI XSS SWEEP")
    print("=" * 70)
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    for r in results:
        marker = "✅" if r["ok"] else "❌"
        print(f"  {marker} [{r['surface']:14s}] {r['payload']}: {r['detail']}")
    print(f"\n  total: {len(results)}, pass: {passed}, fail: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
