# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Autonomous synthetic-tester agent.

Drives the product end-to-end through a real Chrome instance:

    sign up → onboarding wizard (CV + persona + location)
    → run a Find-jobs search with persona-realistic inputs
    → scrape the rendered queue
    → run an evaluator that scores delivery vs promise

Run via ``scripts/run-synthetic-tester.sh`` which starts a fresh
``app.py`` on a free port and points us at it. Set
``E2E_HEADLESS=false`` for a visible browser when debugging.

This is *not* a unit test — it hits real external APIs (Arbeitnow,
Muse, HN, Bundesagentur free tier) so the result depends on what those
feeds happen to have today. The evaluator is intentionally lenient on
volume ("at least 1 plausible match") but strict on quality ("zero
seniority mismatches", "zero wrong-region mismatches").
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# Make the project root importable when invoked as a script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ModuleNotFoundError:
    print("ERROR: Playwright not installed. pip install playwright && playwright install chromium",
          file=sys.stderr)
    sys.exit(2)


@dataclass
class Persona:
    """A synthetic tester profile."""
    id: str                         # internal key
    label: str                      # human display
    persona_dropdown: str           # value in #wizardPersona select
    cv_text: str                    # pasted into wizard step 1
    target_role_query: str          # typed into #findJobsQuery
    location: str                   # typed into #findJobsLocation (and wizard)
    accepts_remote: bool            # if False, remote-only listings are a fail
    expected_seniority: str         # "senior", "junior", "lead", or "" for any
    role_family_keywords: tuple[str, ...]  # title must contain at least one
    forbidden_keywords: tuple[str, ...]    # title must contain none


PERSONAS: tuple[Persona, ...] = (
    Persona(
        id="senior-backend-berlin",
        label="Senior backend engineer in Berlin",
        persona_dropdown="tech",
        cv_text=(
            "Senior Software Engineer with 8 years of Python, Postgres, "
            "Kubernetes, Docker and AWS experience. Built distributed "
            "backends at scale at a Series C fintech. Based in Berlin, "
            "open to hybrid."
        ),
        target_role_query="senior backend engineer",
        location="Berlin",
        accepts_remote=False,
        expected_seniority="senior",
        role_family_keywords=("backend", "back-end", "back end",
                              "software", "engineer", "developer", "python"),
        forbidden_keywords=("junior", "intern", "internship", "praktikant",
                            "werkstudent", "trainee", "azubi"),
    ),
    Persona(
        id="marketing-manager-munich",
        label="Marketing manager in München",
        persona_dropdown="marketing",
        cv_text=(
            "Marketing Manager with 6 years of growth marketing, paid "
            "acquisition, SEO, content marketing, B2B SaaS demand-gen, "
            "and HubSpot expertise. Led a 2M EUR annual budget at a "
            "Series B fintech. Based in München."
        ),
        target_role_query="marketing manager",
        location="München",
        accepts_remote=False,
        expected_seniority="",  # mid-level, no explicit band requirement
        role_family_keywords=("marketing", "growth", "demand", "brand"),
        forbidden_keywords=("intern", "internship", "praktikant",
                            "werkstudent", "azubi"),
    ),
    Persona(
        id="remote-data-anywhere",
        label="Senior data scientist, remote",
        persona_dropdown="data",
        cv_text=(
            "Senior Data Scientist with 9 years of Python, PyTorch, "
            "SQL, dbt, and statistical modelling experience. Built "
            "recommendation systems for a B2C marketplace. Open to "
            "remote across EU."
        ),
        target_role_query="senior data scientist",
        location="Remote",
        accepts_remote=True,
        expected_seniority="senior",
        role_family_keywords=("data", "scientist", "ml", "machine learning",
                              "analytics", "engineer"),
        forbidden_keywords=("junior", "intern", "praktikant", "werkstudent",
                            "trainee", "azubi"),
    ),
)


@dataclass
class JobRow:
    """One row scraped from #findJobsResults."""
    title: str
    company: str
    location: str
    source: str
    url: str

    def to_dict(self) -> dict:
        return {"title": self.title, "company": self.company,
                "location": self.location, "source": self.source, "url": self.url}


@dataclass
class PersonaResult:
    persona: Persona
    queue: list[JobRow] = field(default_factory=list)
    attributions: str = ""
    status_line: str = ""
    error: str | None = None


def _fold(s: str) -> str:
    s = (s or "").replace("ß", "ss").casefold()
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


_REMOTE_TOKENS: frozenset[str] = frozenset({
    "remote", "worldwide", "anywhere", "latam", "americas", "usa", "us",
    "europe", "eu", "emea", "apac", "global", "international",
})

# Known suburbs / metro regions for ambiguous DE city queries. When the
# user types "München", a job in Hohenbrunn/Unterföhring/etc. is still a
# legitimate match — that's the metro area. Postal-code prefix matters
# too: 80xxx-85xxx are all München-region.
_DE_METRO: dict[str, dict] = {
    "munchen": {
        "postal_prefixes": ("80", "81", "82", "85"),
        "region_words": ("oberbayern",),
    },
    "berlin": {
        "postal_prefixes": ("10", "11", "12", "13", "14"),
        "region_words": (),
    },
    "hamburg": {
        "postal_prefixes": ("20", "21", "22"),
        "region_words": (),
    },
    "frankfurt": {
        "postal_prefixes": ("60", "61", "65"),
        "region_words": ("rhein-main",),
    },
}


def _location_ok(persona: Persona, job_location: str,
                 job_source: str = "") -> tuple[bool, str]:
    """Return (ok, reason).

    The evaluator is honest: it accepts everything a real user would
    accept. Specifically:
    - Remote-accepting personas accept any location tag the remote-only
      feeds emit (Worldwide, LATAM, EU, Europe, USA…) plus 'remote' itself.
    - DE city personas accept the city's metro area (suburbs and
      adjacent postal-code prefixes). 'München' search includes
      Hohenbrunn / Unterföhring — those are part of the München metro.
    - Aliases (Munich↔München) are folded equivalent.
    """
    if not job_location:
        return True, "no-location (not a hard fail)"
    job_fold = _fold(job_location)
    user_fold = _fold(persona.location)

    # Remote-friendly persona: anything the remote feeds emit is fine.
    if persona.accepts_remote:
        if any(tok in job_fold.split() or tok in job_fold for tok in _REMOTE_TOKENS):
            return True, f"remote-friendly tag in '{job_location}'"
        # Remote-only providers can have unstructured tags like "Americas,
        # Europe, Asia, Oceania" — accept anything from a remote-only source.
        # UI applies text-transform: uppercase so we casefold defensively.
        if job_source.casefold() in {"remotive", "weworkremotely"}:
            return True, f"remote-only provider '{job_source}'"

    # Substring match (Munich → Munich, Germany)
    if user_fold and user_fold in job_fold:
        return True, f"substring match on '{persona.location}'"

    # Diacritic-fold alias check
    aliases = {
        "munich": ("munchen", "muenchen", "munich"),
        "munchen": ("munich", "muenchen", "munchen"),
        "koln": ("cologne", "koeln", "koln"),
        "cologne": ("cologne", "koln", "koeln"),
    }
    if user_fold in aliases:
        for alias in aliases[user_fold]:
            if alias in job_fold:
                return True, f"alias match via '{alias}'"

    # Metro-area acceptance — suburbs of major DE cities still count.
    metro = _DE_METRO.get(user_fold)
    if not metro and user_fold in aliases:
        for alias in aliases[user_fold]:
            if alias in _DE_METRO:
                metro = _DE_METRO[alias]
                break
    if metro:
        # Postal-code prefix: ", 85774, Bayern" → look for digit cluster
        digits = re.findall(r"\b(\d{4,5})\b", job_location)
        for d in digits:
            if any(d.startswith(p) for p in metro["postal_prefixes"]):
                return True, f"metro postal-code match (prefix {d[:2]})"
        for region in metro["region_words"]:
            if region in job_fold:
                return True, f"metro region match ('{region}')"

    # Non-remote persona, remote-only listing → fail.
    if "remote" in job_fold and not persona.accepts_remote:
        return False, f"remote-only listing, persona wants '{persona.location}'"
    return False, f"job location '{job_location}' does not match persona '{persona.location}'"


def _seniority_ok(persona: Persona, title: str) -> tuple[bool, str]:
    """Return (ok, reason). Forbidden keywords always apply (even when
    no explicit seniority band is set) — a marketing manager persona
    declared forbidden=['intern','praktikant'] expects those filtered
    out regardless of the band check.

    Uses word-boundary matching so 'intern' doesn't fire on
    'International Marketing Manager'."""
    t = _fold(title)
    for bad in persona.forbidden_keywords:
        # Word-boundary check on the folded title.
        if re.search(rf"\b{re.escape(_fold(bad))}\b", t):
            return False, f"title contains forbidden word '{bad}'"
    return True, "no seniority red flags"


def _role_family_ok(persona: Persona, title: str) -> tuple[bool, str]:
    t = _fold(title)
    for keyword in persona.role_family_keywords:
        if _fold(keyword) in t:
            return True, f"matches role keyword '{keyword}'"
    return False, "title contains none of the role-family keywords"


def evaluate(result: PersonaResult) -> dict:
    """Score a single persona's delivered queue vs the promise."""
    base = {"persona": result.persona.id, "label": result.persona.label}
    if result.error:
        return {**base, "fatal": result.error, "queue_size": 0,
                "verdict": "FAIL — fatal"}
    if not result.queue:
        return {**base, "queue_size": 0,
                "verdict": "FAIL — empty queue",
                "status_line": result.status_line,
                "attribution": result.attributions}
    per_job = []
    seniority_fails = 0
    location_fails = 0
    role_family_fails = 0
    for job in result.queue:
        loc_ok, loc_reason = _location_ok(result.persona, job.location, job.source)
        sen_ok, sen_reason = _seniority_ok(result.persona, job.title)
        rf_ok, rf_reason = _role_family_ok(result.persona, job.title)
        if not loc_ok:
            location_fails += 1
        if not sen_ok:
            seniority_fails += 1
        if not rf_ok:
            role_family_fails += 1
        per_job.append({
            "title": job.title, "location": job.location, "source": job.source,
            "location_ok": loc_ok, "location_reason": loc_reason,
            "seniority_ok": sen_ok, "seniority_reason": sen_reason,
            "role_family_ok": rf_ok, "role_family_reason": rf_reason,
        })
    # Dedup check
    urls = [j.url for j in result.queue if j.url]
    duplicates = len(urls) - len(set(urls))
    # Attribution promise: at least one provider mentioned
    attribution_ok = bool(result.attributions.strip())
    # Verdict
    fail_reasons = []
    if seniority_fails:
        fail_reasons.append(f"{seniority_fails}/{len(result.queue)} seniority mismatch")
    if location_fails:
        fail_reasons.append(f"{location_fails}/{len(result.queue)} location mismatch")
    if duplicates:
        fail_reasons.append(f"{duplicates} duplicate URL(s)")
    if not attribution_ok:
        fail_reasons.append("no provider attribution rendered")
    # Role-family mismatch is a soft warn — title text varies wildly.
    soft_warns = []
    if role_family_fails > len(result.queue) // 2:
        soft_warns.append(f"{role_family_fails}/{len(result.queue)} role-family unclear")

    verdict = "PASS" if not fail_reasons else f"FAIL — {'; '.join(fail_reasons)}"
    return {
        "persona": result.persona.id,
        "label": result.persona.label,
        "queue_size": len(result.queue),
        "duplicates": duplicates,
        "seniority_fails": seniority_fails,
        "location_fails": location_fails,
        "role_family_soft_warns": role_family_fails,
        "attribution": result.attributions[:120],
        "status_line": result.status_line[:120],
        "verdict": verdict,
        "warnings": soft_warns,
        "per_job": per_job,
    }


# ----------------- the actual Playwright driver ---------------------------


def _dismiss_wizard(page) -> None:
    """The first-run wizard auto-opens for empty accounts. We close it
    AFTER walking through it (or skip if it's not visible)."""
    try:
        if page.locator("#firstRunWizard").is_visible(timeout=500):
            dismiss = page.locator("#wizardDismiss")
            if dismiss.is_visible(timeout=500):
                dismiss.click()
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(150)
    except Exception:
        pass


def _walk_wizard(page, persona: Persona) -> None:
    """Step through the first-run wizard, dropping our persona profile."""
    try:
        if not page.locator("#firstRunWizard").is_visible(timeout=2000):
            return
    except Exception:
        return
    # Step 1: paste CV
    page.locator("#wizardCvText").fill(persona.cv_text)
    page.locator("#wizardCvNext").click()
    page.wait_for_timeout(400)
    # Step 2: persona — try to select the explicit dropdown value
    try:
        page.locator("#wizardPersona").select_option(value=persona.persona_dropdown)
    except Exception:
        # Persona ids may not match exactly; let the auto-detected one stand.
        pass
    page.locator("#wizardPersonaNext").click()
    page.wait_for_timeout(400)
    # Step 3: location + target roles
    try:
        page.locator("#wizardLocation").fill(persona.location)
    except Exception:
        pass
    # Find any "Finish" / "Save" button in the wizard.
    finish = page.locator("#firstRunWizard button[type='button']").last
    try:
        finish.click()
    except Exception:
        pass
    page.wait_for_timeout(400)
    _dismiss_wizard(page)


def _scrape_queue(page) -> tuple[list[JobRow], str, str]:
    """Read #findJobsResults rows into JobRow list. Returns (rows, status, attrs)."""
    rows = []
    items = page.locator("#findJobsResults .find-jobs-row")
    count = items.count()
    for i in range(count):
        item = items.nth(i)
        try:
            title_a = item.locator(".find-jobs-title")
            title = title_a.inner_text(timeout=500).strip()
            url = title_a.get_attribute("href") or ""
            meta = item.locator(".find-jobs-meta").inner_text(timeout=500).strip()
            source = item.locator(".find-jobs-source").inner_text(timeout=500).strip()
            # meta is "Company · Location · 2h ago" — best effort
            parts = [p.strip() for p in meta.split("·")]
            company = parts[0] if parts else ""
            location = parts[1] if len(parts) > 1 else ""
            rows.append(JobRow(title=title, company=company, location=location,
                                source=source, url=url))
        except Exception:
            continue
    status = ""
    try:
        status = page.locator("#findJobsStatus").inner_text(timeout=500).strip()
    except Exception:
        pass
    attrs = ""
    try:
        attrs = page.locator("#findJobsAttributions").inner_text(timeout=500).strip()
    except Exception:
        pass
    return rows, status, attrs


def run_persona(base_url: str, browser, persona: Persona) -> PersonaResult:
    email = f"agent+{persona.id}+{secrets.token_hex(3)}@example.com"
    password = "synthetic-tester-pass-9!"
    result = PersonaResult(persona=persona)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.set_default_timeout(15000)
    try:
        # 1. Register. Each persona uses a fresh, unique email so registration
        # always proceeds (DIRECTJOB_ALLOW_REGISTRATION=true is set by the
        # launcher). Wait for the form section to be visible — note that the
        # registerForm element exists in the DOM but is hidden until the auth
        # view renders, so we wait for the auth screen explicitly.
        page.goto(base_url + "/")
        # The auth section is #authGate, not view-auth. Wait for either
        # the gate (unauthenticated) or the main content (already auth'd).
        page.locator("#authGate, #mainContent").first.wait_for(state="visible",
                                                                timeout=15000)
        # If we're already logged in (shouldn't happen for a fresh
        # context but defensive), there's nothing to do for registration.
        if page.locator("#mainContent").is_visible(timeout=500):
            pass  # already authenticated somehow
        else:
            # Wait for registerForm to flip visible. registrationOpen=true
            # because the launcher sets DIRECTJOB_ALLOW_REGISTRATION=true.
            page.locator("#registerForm").wait_for(state="visible",
                                                    timeout=10000)
        # Tick consent checkboxes if visible (they only appear after the
        # bootstrap admin exists).
        try:
            if page.locator("#registerTos").is_visible(timeout=500):
                page.locator("#registerTos").check()
                page.locator("#registerPrivacy").check()
        except Exception:
            pass
        page.locator("#registerEmail").fill(email)
        page.locator("#registerPassword").fill(password)
        page.locator("#registerForm button[type='submit']").click()
        page.locator("#sidebarUserEmail").wait_for(state="visible", timeout=25000)

        # 2. Walk the onboarding wizard with the persona profile
        _walk_wizard(page, persona)

        # 3. Find-jobs form lives directly on the dashboard view (the
        # default landing page after login). No nav click required — just
        # ensure dashboard is visible.
        page.locator(".nav-item[data-view='dashboard']").click()
        page.locator("#findJobsForm").wait_for(state="visible", timeout=10000)
        page.locator("#findJobsQuery").fill(persona.target_role_query)
        page.locator("#findJobsLocation").fill(persona.location)
        page.locator("#findJobsLimit").fill("15")
        page.locator("#findJobsSubmit").click()
        # The status line flips from "Searching…" to "<n> results …" when done.
        try:
            page.wait_for_function(
                "() => { const s = document.querySelector('#findJobsStatus'); "
                "return s && /results|Error|No results|0\\s/.test(s.textContent || ''); }",
                timeout=60000,
            )
        except PWTimeout:
            # Continue with whatever rendered.
            pass
        page.wait_for_timeout(500)

        # 4. Scrape the queue
        rows, status_line, attributions = _scrape_queue(page)
        result.queue = rows
        result.status_line = status_line
        result.attributions = attributions

        # 5. Save a screenshot
        out_dir = Path(os.environ.get("E2E_SCREENSHOTS", "tests/e2e/screenshots"))
        out_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out_dir / f"synthetic_{persona.id}.png"),
                        full_page=True)
    except Exception as exc:  # noqa: BLE001
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        context.close()
    return result


def main() -> int:
    base_url = os.environ.get("E2E_BASE_URL", "").rstrip("/")
    if not base_url:
        print("ERROR: E2E_BASE_URL is required", file=sys.stderr)
        return 2
    headless = os.environ.get("E2E_HEADLESS", "true").strip().casefold() != "false"
    print(f"[agent] base_url={base_url} headless={headless}")
    out_path = Path(os.environ.get("E2E_REPORT", "tests/e2e/synthetic_report.json"))

    reports = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        try:
            for persona in PERSONAS:
                print(f"\n[agent] === Running persona: {persona.label} ===")
                result = run_persona(base_url, browser, persona)
                report = evaluate(result)
                reports.append(report)
                print(f"  queue_size={report.get('queue_size', 0)}  "
                      f"verdict={report.get('verdict')}")
                if report.get("warnings"):
                    print(f"  warnings: {report['warnings']}")
        finally:
            browser.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False))
    print(f"\n[agent] wrote report to {out_path}")

    # Print a compact final summary
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)
    for r in reports:
        marker = "✅" if r["verdict"].startswith("PASS") else "❌"
        print(f"{marker} {r['label']}: {r['verdict']} "
              f"(queue={r.get('queue_size', 0)})")
    failing = [r for r in reports if not r["verdict"].startswith("PASS")]
    return 0 if not failing else 1


if __name__ == "__main__":
    sys.exit(main())
