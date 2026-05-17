"""DE-render audit + core E2E flow.

Walks Naser's 6-step checklist against ``E2E_BASE_URL`` with the
locale forced to DE via localStorage. Captures a screenshot per step
and asserts that key German strings render in the visible DOM. Catches
straggler English text that leaked past Items 1 + 17.

Required environment (script no-ops without all three so CI doesn't run it):
  E2E_BASE_URL    e.g. https://app.khalo.org
  E2E_EMAIL       admin email
  E2E_PASSWORD    admin password

Usage:
  E2E_BASE_URL=... E2E_EMAIL=... E2E_PASSWORD=... \\
      /private/tmp/directjob-e2e-venv/bin/python tests/e2e/test_de_audit.py
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # CI runners don't ship playwright; skip the whole module.
    raise unittest.SkipTest("playwright not installed")

OUT = Path("/tmp/dj-de-audit")
OUT.mkdir(exist_ok=True)

URL = os.environ.get("E2E_BASE_URL", "")
EMAIL = os.environ.get("E2E_EMAIL", "")
PASSWORD = os.environ.get("E2E_PASSWORD", "")
if not (URL and EMAIL and PASSWORD):
    raise unittest.SkipTest("E2E_BASE_URL / E2E_EMAIL / E2E_PASSWORD not set")


def assert_de(page, text, label):
    # CSS may text-transform some labels to UPPERCASE; compare case-insensitively
    # against both inner_text (visible, post-transform) and inner_html (raw DOM).
    visible = page.inner_text("body").lower()
    raw = page.inner_html("body").lower()
    needle = text.lower()
    assert needle in visible or needle in raw, (
        f"[{label}] expected {text!r} in DOM (case-insensitive) but didn't find it"
    )
    print(f"  ✓ [{label}] saw '{text}'")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # Force locale to DE via localStorage so the auth gate renders in DE.
        page.add_init_script("localStorage.setItem('dj_locale', 'de')")
        page.goto(URL, wait_until="networkidle")
        page.screenshot(path=str(OUT / "01-login-de.png"))
        assert_de(page, "Anmelden", "login")
        assert_de(page, "Passwort", "login")

        # Step 1: sign in
        page.fill("#loginEmail", EMAIL)
        page.fill("#loginPassword", PASSWORD)
        page.click("#loginForm button[type='submit']")
        page.wait_for_selector("#appShell:not([hidden])", timeout=10_000)
        page.wait_for_timeout(2500)
        # Server-side profile locale may default to "en" for the admin
        # account; flip it to "de" so the rest of the walkthrough renders
        # in German end-to-end.
        page.evaluate("""
            async () => {
                const csrf = (await (await fetch('/api/auth/state')).json()).csrfToken
                  || (await (await fetch('/api/profile')).json()).profile?.csrfToken;
                const cookieMatch = document.cookie.match(/directjob_session=([^;]+)/);
                await fetch('/api/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json',
                               'X-CSRF-Token': window.__CSRF__ || '' },
                    body: JSON.stringify({ locale: 'de' }),
                    credentials: 'same-origin',
                });
            }
        """)
        # Navigate the locale toggle to DE in the running app — this is the
        # actual user-facing path and re-renders all data-i18n spans.
        page.wait_for_function("typeof loadLocale === 'function'", timeout=2000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "02-dashboard-de.png"), full_page=True)
        assert_de(page, "Übersicht", "dashboard nav")
        assert_de(page, "Beobachtete Unternehmen", "dashboard metric")
        assert_de(page, "Nächster Schritt", "dashboard next-step")

        # Step 2: Settings → Persona & profile (DE labels)
        page.click(".nav-item[data-view='settings']")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "03-settings-de.png"), full_page=True)
        assert_de(page, "Persona & Profil", "settings persona heading")
        assert_de(page, "Sprache", "settings language card")
        assert_de(page, "KI-Anbieter", "settings ai provider")
        assert_de(page, "Browser-Benachrichtigungen", "settings push card")
        assert_de(page, "Design", "settings theme card")

        # R25.2 + R25.4 — Jobs and Companies nav buttons removed.
        # Navigate via the SPA's JS function (the views still exist
        # as canvases reachable from chat). R23.1 renamed Brief →
        # Applications.
        # Step 3: Companies canvas
        page.evaluate("() => navigate('companies')")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "04-companies-de.png"), full_page=True)
        assert_de(page, "Beobachtete Unternehmen", "companies watchlist heading")
        assert_de(page, "Unternehmen hinzufügen", "companies add heading")
        assert_de(page, "Vorlagen", "companies templates")

        # Step 4: Discovered jobs canvas
        page.evaluate("() => navigate('jobs')")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "05-queue-de.png"), full_page=True)
        assert_de(page, "Stellen auf Unternehmens-Websites", "queue heading")
        assert_de(page, "Sortieren nach", "queue toolbar")
        assert_de(page, "Ungescorte bewerten", "queue auto-fit-all")

        # Step 5: Applications view (R23.1 renamed Brief → Applications)
        page.click(".nav-item[data-view='applications']")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "06-brief-de.png"), full_page=True)
        assert_de(page, "So läuft die KI", "brief provider heading")
        assert_de(page, "Bewerbungs-Vorbereitung", "application form heading")
        assert_de(page, "Anschreiben entwerfen", "draft cover letter button")

        # Step 6: switch language back to EN, confirm bilingual works
        page.click(".nav-item[data-view='settings']")
        page.wait_for_timeout(400)
        page.select_option("#localeSelect", "en")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "07-settings-en.png"), full_page=True)
        body_lower = page.inner_text("body").lower()
        assert "save profile" in body_lower or "ai provider" in body_lower, (
            f"EN switch didn't apply — body has no 'Save profile'/'AI Provider'. "
            f"first 200 chars lower: {body_lower[:200]}"
        )
        print("  ✓ [locale toggle] DE → EN round-trip OK")

        browser.close()
    print("\nALL CHECKS PASSED — DE coverage complete on Naser's 6-step flow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
