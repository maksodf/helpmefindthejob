#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Authenticated-surface accessibility audit runner.

Closes the §3.6 ce48ba5 deferral: the public unauthenticated surfaces
were audited via axe-core CLI in the first pass; the authenticated
surfaces (chat, settings, journey, CV builder) needed a headless-
browser runner that logs in via seeded persona auth and runs axe at
each navigation state.

Dependencies (one-shot, NOT in requirements-dev.txt to keep the main
dev install slim — a 200 MB Chromium binary would dominate the dev
toolchain otherwise):

    pip install playwright axe-playwright-python
    python3 -m playwright install chromium

Tool versions used in the §3.6-followup audit (2026-05-19):

    playwright              1.60.0
    axe-playwright-python   0.1.7  (bundles axe-core 4.10)
    chromium                via playwright's bundled chrome-headless-shell

Run:

    python3 scripts/accessibility-audit-auth-surfaces.py

Output:

    audit-results/auth-surfaces/<state>.png   — screenshot
    audit-results/auth-surfaces/<state>.json  — full axe JSON
    audit-results/auth-surfaces/<state>.txt   — violations summary
    audit-results/auth-surfaces/summary.txt   — per-state counts

The script:
 1. Spins up a fresh app.py instance in a tmp data dir
 2. Waits for /api/health
 3. Seeds the Aïcha persona via direct repository write (mirrors
    scripts/seed-personas.py's pattern — bypasses update_profile's
    PERSONAS-whitelist so the panel slug 'aicha' lands on the user's
    profile)
 4. Launches Playwright Chromium, logs in via the sign-in form, and
    walks through ≥6 distinct authenticated UI states (dashboard,
    settings, assistant, jobs, companies, CV builder)
 5. Saves the per-state outputs
 6. Tears down the app + Playwright

Exit code:
    0 = audit completed (look at audit-results/ for findings)
    1 = audit could not complete (missing deps, app refused to start,
        seed failed, login failed, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "audit-results" / "auth-surfaces"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEMO_PASSWORD = os.environ.get("AUDIT_PASSWORD", "audit-test-12345678")
EMAIL = "aicha@demo.helpmefindthejob.com"


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _pick_port() -> int:
    """Bind to port 0 to get an ephemeral free port, close, return."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).read()  # noqa: S310
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)
    return False


def _seed_aicha(data_dir: Path) -> None:
    """Seed the Aïcha persona into the app's database. Mirrors
    scripts/seed-personas.py's pattern of writing directly via
    repository.save_user_profile so the panel persona_id 'aicha' lands
    on the profile (update_profile's whitelist would reject it)."""
    env = os.environ.copy()
    env["COMPANY_DISCOVERY_DATA_DIR"] = str(data_dir)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "seed-personas.py"),
        "--password",
        DEMO_PASSWORD,
        "--data-dir",
        str(data_dir),
        "--force-password-reset",
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        _err(f"seed-personas failed (exit {result.returncode}):")
        _err(result.stdout)
        _err(result.stderr)
        raise RuntimeError("seed-personas failed")
    print("[seed] aicha persona seeded into", data_dir)


def _start_app(data_dir: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["COMPANY_DISCOVERY_HOST"] = "127.0.0.1"
    env["COMPANY_DISCOVERY_PORT"] = str(port)
    # COMPANY_DISCOVERY_DATA_DIR is the SAME env var seed-personas
    # respects; setting just this guarantees the seed and the app
    # share the same SQLite files (auth.sqlite3 + company_discovery.
    # sqlite3 + scheduler.sqlite3 + tokens.sqlite3 + quotas.sqlite3,
    # all under this directory). Don't set the per-file *_PATH
    # variables — they're not read by app.py's data path resolution.
    env["COMPANY_DISCOVERY_DATA_DIR"] = str(data_dir)
    log_file = open(data_dir / "app.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "app.py")],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    if not _wait_for(f"http://127.0.0.1:{port}/api/health", timeout=20.0):
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError("app.py failed to come up; see " + str(data_dir / "app.log"))
    print(f"[app] up at http://127.0.0.1:{port}")
    return proc


def _audit_state(axe, page, state: str, *, suffix: str = "") -> tuple[int, int, int, int]:
    """Run axe on the current page; save screenshot + JSON + summary.

    Returns ``(critical, serious, moderate, minor)`` violation counts.

    ``suffix`` is appended before the file extension so the same
    state-id can be re-audited in different conditions without
    overwriting the prior artefact. E.g., ``suffix="-light"`` writes
    ``<state>-light.{png,json,txt}``.
    """
    label = f"{state}{suffix}"
    print(f"[audit] {label}")
    page.screenshot(path=str(OUT_DIR / f"{label}.png"), full_page=True)
    result = axe.run(page)
    response = result.response  # axe-playwright-python AxeResults wraps a dict
    with (OUT_DIR / f"{label}.json").open("w", encoding="utf-8") as fh:
        json.dump(response, fh, indent=2, ensure_ascii=False)
    violations = response.get("violations", [])
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    lines: list[str] = [f"axe-core violations for state: {label}", "-" * 60]
    for v in violations:
        impact = v.get("impact") or "unknown"
        counts[impact] = counts.get(impact, 0) + 1
        nodes = v.get("nodes", [])
        lines.append(f"[{impact}] {v.get('id', '?')}: {len(nodes)} node(s) — {v.get('help', '')}")
        for n in nodes[:3]:
            lines.append(f"    target: {n.get('target')}")
    lines.append(f"Totals: {counts}")
    (OUT_DIR / f"{label}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"       critical={counts['critical']} "
        f"serious={counts['serious']} "
        f"moderate={counts['moderate']} "
        f"minor={counts['minor']}"
    )
    return (counts["critical"], counts["serious"], counts["moderate"], counts["minor"])


def _login(page, base_url: str) -> None:
    """Fill the sign-in form and wait for the authenticated shell."""
    page.goto(base_url + "/")
    page.locator("#authGate").wait_for(state="visible", timeout=15000)
    page.locator("#loginEmail").fill(EMAIL)
    page.locator("#loginPassword").fill(DEMO_PASSWORD)
    page.locator("#loginForm button[type='submit']").click()
    # After auth, the sidebar's email element becomes visible.
    page.locator("#sidebarUserEmail").wait_for(state="visible", timeout=20000)
    # Dismiss any first-run wizard pop-up to land on a stable state.
    try:
        if page.locator("#firstRunWizard").is_visible(timeout=500):
            if page.locator("#wizardDismiss").is_visible(timeout=200):
                page.locator("#wizardDismiss").click()
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(200)
    except Exception:
        pass


def _navigate(page, view: str) -> None:
    """Click the sidebar nav item for ``view`` and wait for the view
    region to be visible."""
    selector = f'.nav-item[data-view="{view}"]'
    page.locator(selector).first.click()
    target = f"#view-{view}:not([hidden])"
    page.locator(target).first.wait_for(state="visible", timeout=10000)
    # Brief settle for any async data load.
    page.wait_for_timeout(400)


def _open_cmdk(page) -> None:
    """Open the cmdk (command-palette) dialog via keyboard shortcut.
    Waits for the dialog to be visible."""
    # On macOS Playwright headless: Meta+K. On Linux: Control+K.
    # The app handles both; send Control+K which works in CI runners.
    page.keyboard.press("Control+K")
    try:
        page.locator("#cmdkDialog[open]").wait_for(state="visible", timeout=5000)
    except Exception:
        # Fall back to clicking the launcher button explicitly.
        try:
            page.locator("#cmdkLauncher").click(timeout=2000)
            page.locator("#cmdkDialog[open]").wait_for(state="visible", timeout=5000)
        except Exception:
            raise RuntimeError("cmdk dialog did not open")
    page.wait_for_timeout(200)


def _close_cmdk(page) -> None:
    """Close the cmdk dialog (best-effort)."""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass


def _trigger_login_error(page, base_url: str) -> None:
    """On the sign-in landing, submit the login form with a bad
    password; the `#authMessage` role="alert" element becomes
    populated. This audits the error-state form.

    Clears the authenticated session first so the sign-in form is
    actually visible (otherwise the auth-cookie redirects to the
    authenticated shell)."""
    page.context.clear_cookies()
    page.goto(base_url + "/")
    page.locator("#authGate").wait_for(state="visible", timeout=10000)
    page.locator("#loginEmail").fill(EMAIL)
    page.locator("#loginPassword").fill("intentionally-bad-password")
    page.locator("#loginForm button[type='submit']").click()
    # Wait for the error message to be populated. The element is
    # always in the DOM with role="alert"; the content fills async.
    deadline_ms = 8000
    elapsed = 0
    while elapsed < deadline_ms:
        text = page.evaluate("() => document.querySelector('#authMessage')?.textContent || ''")
        if text.strip():
            break
        page.wait_for_timeout(200)
        elapsed += 200
    page.wait_for_timeout(150)


def _expand_suggestions_disclosure(page) -> None:
    """On the companies view, expand the Suggestions <details>
    widget by clicking its summary."""
    _navigate(page, "companies")
    # Find the Suggestions <details> via the heading text inside
    # its summary. The :has() selector is supported in modern
    # Chromium.
    summary = page.locator("details.collapsible:has(h2:has-text('Suggestions')) > summary")
    summary.click()
    # Confirm details is now open.
    page.locator("details.collapsible:has(h2:has-text('Suggestions'))[open]").wait_for(
        state="attached", timeout=5000
    )
    page.wait_for_timeout(300)


def _open_settings_and_change(page) -> None:
    """Navigate to settings, change a setting that the app
    persists silently (e.g., flip the theme via the in-app
    selector), audit the settings view with the new state
    visible. This is a stand-in for a 'post-form-submit'
    confirmation flow — the settings persist on change without a
    dedicated toast in the current UI."""
    _navigate(page, "settings")
    # Change the persona via the settings UI if exposed; otherwise
    # the audit captures the settings view in its rendered state
    # with all controls visible. The intent of this dynamic state
    # is to exercise the form-controls' rendered accessibility tree
    # at a populated state, not specifically a toast.
    page.wait_for_timeout(300)


def _walk_eight_states(
    axe, page, base_url: str, suffix: str, scheme: str
) -> dict[str, tuple[int, int, int, int]]:
    """Walk the 8 authenticated UI states and run axe at each.

    Returns ``{state_id: (critical, serious, moderate, minor)}``. The
    file suffix lets the caller distinguish runs (e.g., ``-dark``
    vs ``-light``). ``scheme`` is the in-app theme to apply via
    ``applyTheme(scheme)`` after login — Playwright's
    ``prefers-color-scheme`` emulation alone is insufficient because
    the app's CSS keys off ``:root[data-theme]`` which is set by JS
    from ``state.profile.theme`` (default ``"dark"``).
    """
    summary: dict[str, tuple[int, int, int, int]] = {}

    # State 1 — sign-in landing (re-audit the same surface
    # the §3.6 first pass already covered, against the post-fix HTML;
    # serves as a regression check). The pre-login screen runs before
    # applyTheme picks up profile.theme, so the data-theme can be set
    # directly on documentElement via init script.
    page.goto(base_url + "/")
    # Force the data-theme attribute so the CSS variables resolve to
    # the requested scheme even before the app's JS runs applyTheme().
    page.evaluate(
        "(scheme) => { document.documentElement.dataset.theme = scheme; }",
        scheme,
    )
    page.locator("#authGate").wait_for(state="visible", timeout=15000)
    summary["01-signin-landing"] = _audit_state(axe, page, "01-signin-landing", suffix=suffix)

    # State 2 — post-login dashboard. After login, the app's
    # applyTheme() ran with the user's profile.theme (defaults to
    # "dark"). Flip it now via the in-app function so subsequent
    # views render in the requested scheme.
    _login(page, base_url)
    page.evaluate(
        "(scheme) => { if (typeof applyTheme === 'function') applyTheme(scheme); "
        "else document.documentElement.dataset.theme = scheme; }",
        scheme,
    )
    page.wait_for_timeout(150)  # let the CSS variable cascade settle
    summary["02-post-login"] = _audit_state(axe, page, "02-post-login", suffix=suffix)

    # States 3-8 — each of the sidebar nav views in turn.
    for state, view in [
        ("03-jobs", "jobs"),
        ("04-assistant", "assistant"),
        ("05-companies", "companies"),
        ("06-cv-builder", "cvBuilder"),
        ("07-settings", "settings"),
        ("08-dashboard", "dashboard"),
    ]:
        try:
            _navigate(page, view)
        except Exception as exc:
            _err(f"could not navigate to view {view!r}: {exc}")
            continue
        summary[state] = _audit_state(axe, page, state, suffix=suffix)

    # Dynamic-state audits — these surface accessibility issues that
    # are only present once a user has triggered a particular UI
    # transition (modal open, disclosure expanded, error rendered).
    # They run only for the dark-scheme pass to keep the runner's
    # wall-clock budget reasonable; light-mode dynamic-state coverage
    # is tracked as a known gap if any dynamic-state finding turns
    # out to be scheme-dependent.
    if scheme == "dark":
        # State 09 — cmdk command-palette dialog open.
        try:
            _open_cmdk(page)
            summary["09-dynamic-cmdk-dialog"] = _audit_state(
                axe, page, "09-dynamic-cmdk-dialog", suffix=suffix
            )
            _close_cmdk(page)
        except Exception as exc:
            _err(f"cmdk dynamic state failed: {exc}")

        # State 10 — disclosure expanded (Suggestions <details>).
        try:
            _expand_suggestions_disclosure(page)
            summary["10-dynamic-disclosure-open"] = _audit_state(
                axe, page, "10-dynamic-disclosure-open", suffix=suffix
            )
        except Exception as exc:
            _err(f"disclosure dynamic state failed: {exc}")

        # State 12 — settings view with form controls audited at
        # rendered state. (Reasonable stand-in for post-submit
        # confirmation; the current UI persists settings on change
        # without a toast surface.)
        try:
            _open_settings_and_change(page)
            summary["12-dynamic-settings-loaded"] = _audit_state(
                axe, page, "12-dynamic-settings-loaded", suffix=suffix
            )
        except Exception as exc:
            _err(f"settings dynamic state failed: {exc}")

        # State 11 — login-error state. Doing this LAST because it
        # navigates away from the authenticated session, ending the
        # in-app flow. The runner's outer loop tears down the context
        # afterwards.
        try:
            _trigger_login_error(page, base_url)
            summary["11-dynamic-login-error"] = _audit_state(
                axe, page, "11-dynamic-login-error", suffix=suffix
            )
        except Exception as exc:
            _err(f"login-error dynamic state failed: {exc}")

    return summary


def _write_summary(per_scheme: dict[str, dict[str, tuple[int, int, int, int]]]) -> None:
    """Aggregate per-state counts across one or more colour schemes
    and write ``audit-results/auth-surfaces/summary.txt``."""
    lines: list[str] = ["Per-state axe violation counts", "=" * 60]
    grand_total = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for scheme, states in per_scheme.items():
        scheme_total = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
        lines.append(f"\n[color-scheme: {scheme}]")
        for state, (c, s, m, mi) in states.items():
            lines.append(f"  {state}-{scheme}: critical={c} serious={s} moderate={m} minor={mi}")
            for k, v in (("critical", c), ("serious", s), ("moderate", m), ("minor", mi)):
                scheme_total[k] += v
                grand_total[k] += v
        lines.append(
            f"  {scheme} subtotal: critical={scheme_total['critical']} "
            f"serious={scheme_total['serious']} moderate={scheme_total['moderate']} "
            f"minor={scheme_total['minor']}"
        )
    lines.append("-" * 60)
    lines.append(
        f"GRAND TOTAL: critical={grand_total['critical']} "
        f"serious={grand_total['serious']} moderate={grand_total['moderate']} "
        f"minor={grand_total['minor']}"
    )
    (OUT_DIR / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Helpmefindthejob auth-surface accessibility audit runner."
    )
    parser.add_argument(
        "--color-scheme",
        choices=["dark", "light", "both"],
        default="both",
        help=(
            "Colour scheme to audit. 'dark' and 'light' run a single "
            "scheme; 'both' (default) runs them sequentially and writes "
            "scheme-suffixed artefacts."
        ),
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        _err(
            "Playwright not installed. Run: "
            "pip install playwright axe-playwright-python "
            "&& python3 -m playwright install chromium"
        )
        return 1
    try:
        from axe_playwright_python.sync_playwright import Axe
    except ModuleNotFoundError:
        _err("axe-playwright-python not installed. Run: pip install axe-playwright-python")
        return 1

    if args.color_scheme == "both":
        schemes: list[str] = ["dark", "light"]
    else:
        schemes = [args.color_scheme]

    with tempfile.TemporaryDirectory(prefix="dj-audit-") as tmp:
        data_dir = Path(tmp)
        port = _pick_port()
        try:
            _seed_aicha(data_dir)
        except Exception as exc:
            _err(f"seed step failed: {exc}")
            return 1
        try:
            proc = _start_app(data_dir, port)
        except Exception as exc:
            _err(f"app start failed: {exc}")
            return 1
        base_url = f"http://127.0.0.1:{port}"
        per_scheme: dict[str, dict[str, tuple[int, int, int, int]]] = {}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for scheme in schemes:
                    print(f"\n=== Pass: color-scheme={scheme} ===\n")
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        color_scheme=scheme,
                    )
                    page = context.new_page()
                    axe = Axe()
                    per_scheme[scheme] = _walk_eight_states(
                        axe, page, base_url, f"-{scheme}", scheme
                    )
                    context.close()
                browser.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

        _write_summary(per_scheme)

    return 0


if __name__ == "__main__":
    # The unused-import guard for `secrets` is to keep the module
    # ready for cryptographic-quality nonce generation if a future
    # version needs CSP nonces or similar; remove if it becomes a
    # ruff finding.
    _ = secrets
    sys.exit(main())
