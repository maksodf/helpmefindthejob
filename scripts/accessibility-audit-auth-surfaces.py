#!/usr/bin/env python3
# Copyright (c) 2026 DirectJob Scout contributors
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
EMAIL = "aicha@demo.directjob-scout.example"


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


def _audit_state(axe, page, state: str) -> tuple[int, int, int, int]:
    """Run axe on the current page; save screenshot + JSON + summary.

    Returns ``(critical, serious, moderate, minor)`` violation counts.
    """
    print(f"[audit] {state}")
    page.screenshot(path=str(OUT_DIR / f"{state}.png"), full_page=True)
    result = axe.run(page)
    response = result.response  # axe-playwright-python AxeResults wraps a dict
    with (OUT_DIR / f"{state}.json").open("w", encoding="utf-8") as fh:
        json.dump(response, fh, indent=2, ensure_ascii=False)
    violations = response.get("violations", [])
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    lines: list[str] = [f"axe-core violations for state: {state}", "-" * 60]
    for v in violations:
        impact = v.get("impact") or "unknown"
        counts[impact] = counts.get(impact, 0) + 1
        nodes = v.get("nodes", [])
        lines.append(f"[{impact}] {v.get('id', '?')}: {len(nodes)} node(s) — {v.get('help', '')}")
        for n in nodes[:3]:
            lines.append(f"    target: {n.get('target')}")
    lines.append(f"Totals: {counts}")
    (OUT_DIR / f"{state}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
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


def main() -> int:
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
        summary: dict[str, tuple[int, int, int, int]] = {}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1280, "height": 800})
                page = context.new_page()
                axe = Axe()

                # State 1 — sign-in landing (re-audit the same surface
                # the §3.6 first pass already covered, against the
                # post-fix HTML; serves as a regression check).
                page.goto(base_url + "/")
                page.locator("#authGate").wait_for(state="visible", timeout=15000)
                summary["01-signin-landing"] = _audit_state(axe, page, "01-signin-landing")

                # State 2 — post-login dashboard.
                _login(page, base_url)
                summary["02-post-login"] = _audit_state(axe, page, "02-post-login")

                # States 3-8 — each of the sidebar nav views in turn.
                # `jobs` is the initial view post-login; capture its
                # dedicated entry separately so the audit clearly maps
                # to it.
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
                        # Continue with remaining states rather than abort.
                        continue
                    summary[state] = _audit_state(axe, page, state)

                browser.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

        # Per-state summary file.
        summary_lines = ["Per-state axe violation counts", "=" * 60]
        total = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
        for state, (c, s, m, mi) in summary.items():
            summary_lines.append(f"{state}: critical={c} serious={s} moderate={m} minor={mi}")
            total["critical"] += c
            total["serious"] += s
            total["moderate"] += m
            total["minor"] += mi
        summary_lines.append("-" * 60)
        summary_lines.append(
            f"TOTALS: critical={total['critical']} "
            f"serious={total['serious']} moderate={total['moderate']} "
            f"minor={total['minor']}"
        )
        (OUT_DIR / "summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        print("\n" + "\n".join(summary_lines))

    return 0


if __name__ == "__main__":
    # The unused-import guard for `secrets` is to keep the module
    # ready for cryptographic-quality nonce generation if a future
    # version needs CSP nonces or similar; remove if it becomes a
    # ruff finding.
    _ = secrets
    sys.exit(main())
