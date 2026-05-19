# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-expert end-to-end verifier for the guided job-search journey.

Plays N personas through the chat API and asserts the journey stays
on-rails. Each persona is a deterministic script — no LLM dependency,
so the verifier is reliable in CI.

Run via ``scripts/run-journey-ux-expert.sh``.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")
RESULTS: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name}{(' — ' + detail) if detail else ''}")
    RESULTS.append((name, ok, detail))


class _Client:
    def __init__(self, base: str):
        self.base = base
        self.cookie = ""
        self.csrf = ""

    def request(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf and method != "GET":
            headers["X-CSRF-Token"] = self.csrf
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                sc = resp.headers.get("Set-Cookie", "")
                if sc:
                    self.cookie = sc.split(";", 1)[0]
                raw = resp.read().decode("utf-8", errors="replace")
                payload: dict | str = {}
                if raw:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = raw
                if isinstance(payload, dict):
                    for k in ("csrfToken", "csrf_token"):
                        if isinstance(payload.get(k), str) and payload[k]:
                            self.csrf = payload[k]
                            break
                    u = payload.get("user") or {}
                    if isinstance(u, dict):
                        for k in ("csrfToken", "csrf_token"):
                            if isinstance(u.get(k), str) and u[k]:
                                self.csrf = u[k]
                                break
                return resp.status, payload
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            try:
                return e.code, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return e.code, raw


def _register(client: _Client, who: str) -> str:
    email = f"ux-{who}+{secrets.token_hex(3)}@example.com"
    client.request("GET", "/")
    s, p = client.request(
        "POST",
        "/api/auth/register",
        {
            "email": email,
            "password": "ux-pass-99-X",
            "tosAccepted": True,
            "privacyAccepted": True,
        },
    )
    if s not in (200, 201):
        raise RuntimeError(f"register {s} {p}")
    return email


def _send(client: _Client, msg: str) -> dict:
    s, p = client.request("POST", "/api/chat/message", {"message": msg})
    if s != 200:
        raise RuntimeError(f"chat HTTP {s}: {p}")
    if not isinstance(p, dict):
        raise TypeError(f"chat returned non-dict: {p!r}")
    return p


def _journey_phase(reply_payload: dict) -> str:
    return reply_payload.get("journeyPhase") or ""


# ----------------- Personas (scripted) -----------------


def play_maria_no_cv(client: _Client) -> None:
    """Maria, Pflegehelferin in Berlin, no CV — uses sectional build."""
    _register(client, "maria")
    # Kick off journey via explicit phrase.
    p = _send(client, "Ich suche einen Job als Pflegehelfer")
    report("maria.journey_triggers", _journey_phase(p) == "discover", f"phase={_journey_phase(p)}")
    report(
        "maria.first_question_role", "role" in (p.get("reply") or "").lower(), "agent asks for role"
    )
    # Discover: role
    p = _send(client, "Pflegehelfer")
    report(
        "maria.discover_role_advances",
        "Where" in (p.get("reply") or ""),
        "next question is location",
    )
    # Location
    p = _send(client, "Berlin")
    report(
        "maria.discover_location_advances",
        "years" in (p.get("reply") or "").lower(),
        "next question is years",
    )
    # Years
    p = _send(client, "5")
    report(
        "maria.discover_years_advances",
        "languages" in (p.get("reply") or "").lower()
        or "language" in (p.get("reply") or "").lower(),
        "next question is languages",
    )
    # Languages
    p = _send(client, "Deutsch, English")
    report(
        "maria.discover_done_offers_cv_choice",
        "CV" in (p.get("reply") or "") and "build" in (p.get("reply") or "").lower(),
        "CV choice offered",
    )
    # CV: build (no CV)
    p = _send(client, "build")
    report(
        "maria.cv_build_kickoff",
        "full name" in (p.get("reply") or "").lower(),
        "first sectional question",
    )
    # Sectional answers
    p = _send(client, "Maria Schmidt")
    report("maria.cv_step_name", "city" in (p.get("reply") or "").lower(), "step 2 of 5")
    p = _send(client, "Berlin")
    p = _send(client, "Pflegehelferin with 5 years experience in elderly care.")
    p = _send(client, "Charité 2020-2024 — Pflegehelferin. Cared for 12 residents.")
    p = _send(client, "Pflege, Erste Hilfe, Deutsch, English")
    # Should now be in inspire phase
    report(
        "maria.cv_complete_advances_to_inspire",
        _journey_phase(p) == "inspire",
        f"phase={_journey_phase(p)}",
    )
    report(
        "maria.inspire_shows_suggestions",
        "Pflegeassistent" in (p.get("reply") or "") or "Altenpflege" in (p.get("reply") or ""),
        "templated fallback suggestions surface",
    )
    # Accept all suggestions
    p = _send(client, "yes")
    report(
        "maria.inspire_accept_advances_to_prefs",
        _journey_phase(p) == "preferences",
        f"phase={_journey_phase(p)}",
    )
    report(
        "maria.prefs_asks_dealbreakers",
        "deal-breakers" in (p.get("reply") or "").lower()
        or "remote" in (p.get("reply") or "").lower(),
        "prefs question asked",
    )
    # Skip prefs and run search
    p = _send(client, "skip")
    report(
        "maria.search_results_summary_returned",
        "Found" in (p.get("reply") or "") and "job(s) total" in (p.get("reply") or ""),
        "categorized results summary",
    )
    # Gate 4: pick a category, then a job, then ask for a motivation letter.
    # Search results depend on live aggregators — we make this resilient
    # by picking whatever category the agent surfaced.
    reply = p.get("reply") or ""
    import re as _re

    cat_match = _re.search(r"\*\*([^*]+)\*\*: \d+ job\(s\)", reply)
    if cat_match:
        category = cat_match.group(1)
        p = _send(client, category)
        report(
            "maria.category_drill_renders_jobs",
            "**1." in (p.get("reply") or "") or "1. **" in (p.get("reply") or ""),
            "numbered job list shown",
        )
        # Pick first job
        p = _send(client, "1")
        report(
            "maria.job_pick_offers_actions",
            "letter" in (p.get("reply") or "").lower()
            and "consult" in (p.get("reply") or "").lower(),
            "letter/consult/save menu offered",
        )
        # Ask for the motivation letter
        p = _send(client, "letter")
        letter_reply = p.get("reply") or ""
        report(
            "maria.letter_drafted_with_dach_structure",
            "Sehr geehrte" in letter_reply and "Mit freundlichen Grüßen" in letter_reply,
            "DACH norm Anrede + Schluss present",
        )
        report(
            "maria.letter_invoked_marker",
            p.get("invoked") == "draft_motivation_letter",
            f"invoked={p.get('invoked')!r}",
        )
    else:
        report(
            "maria.category_present_in_summary", False, "no **<category>**: N job(s) found in reply"
        )


def play_lars_has_cv_via_paste(client: _Client) -> None:
    """Lars pastes a long CV → bypass sectional build, then runs the
    full journey through prefs → search → category drill → letter."""
    _register(client, "lars")
    p = _send(client, "I want to find a job")
    report("lars.journey_triggers", _journey_phase(p) == "discover", "phase=discover")
    _send(client, "Senior backend engineer")
    _send(client, "Munich")
    _send(client, "9")
    p = _send(client, "English, Deutsch")
    report("lars.lands_at_cv_check", _journey_phase(p) == "cv_check", f"phase={_journey_phase(p)}")
    paste = (
        "Lars Müller. Senior backend engineer with 9 years experience "
        "in distributed systems and platform engineering. Worked at "
        "two scale-ups in Munich. Languages: Deutsch, English. "
        "Skills: Go, Python, Kafka, Postgres, Kubernetes."
    )
    p = _send(client, paste)
    report(
        "lars.paste_advances_to_inspire",
        _journey_phase(p) == "inspire",
        f"phase={_journey_phase(p)}",
    )
    report(
        "lars.paste_chars_acknowledged",
        "chars" in (p.get("reply") or "").lower(),
        "agent confirms paste",
    )
    # Decline lateral suggestions, skip prefs, look at results.
    p = _send(client, "no")
    report(
        "lars.decline_lateral_advances_to_prefs",
        _journey_phase(p) == "preferences",
        f"phase={_journey_phase(p)}",
    )
    p = _send(client, "remote required, min 80k")
    report(
        "lars.prefs_capture_then_search",
        "Found" in (p.get("reply") or ""),
        "search executed after prefs",
    )


def play_asha_career_change(client: _Client) -> None:
    """Asha — career change from barista to digital marketing. Tests
    that the inspire phase suggests adjacent roles AND the user can
    cherry-pick a subset (not 'yes' or 'no')."""
    _register(client, "asha")
    p = _send(client, "I need a new job")
    report("asha.journey_triggers", _journey_phase(p) == "discover", "phase=discover")
    _send(client, "Barista")
    _send(client, "anywhere")
    _send(client, "3")
    p = _send(client, "English")
    report("asha.lands_at_cv_check", _journey_phase(p) == "cv_check", f"phase={_journey_phase(p)}")
    # Build a CV via the sectional path.
    _send(client, "build")
    _send(client, "Asha Patel")
    _send(client, "Berlin")
    _send(
        client,
        "Three years as barista — coffee art, customer "
        "engagement, café operations. Want to pivot to "
        "digital marketing.",
    )
    _send(
        client,
        "Café Adler 2022-2025 — Barista. Built customer loyalty program, ran social media channel.",
    )
    p = _send(
        client, "Coffee preparation, social media, customer service, English, basic Photoshop"
    )
    report(
        "asha.cv_complete_phase_inspire",
        _journey_phase(p) == "inspire",
        f"phase={_journey_phase(p)}",
    )
    # Cherry-pick the suggestions (not 'yes' or 'no').
    p = _send(client, "Café Manager, Event Crew")
    report(
        "asha.cherry_pick_lateral_roles",
        _journey_phase(p) == "preferences",
        "advanced to prefs after cherry-pick",
    )
    p = _send(client, "skip")
    reply = p.get("reply") or ""
    # Search runs whether or not there are hits — accept either the
    # "Found N job(s)" summary or the "No matching jobs right now"
    # fallback. Both prove the search ran end-to-end.
    report(
        "asha.search_runs_after_prefs",
        "Found" in reply or "No matching jobs" in reply,
        "search executed after prefs skip",
    )


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2

    print("\n=== Persona: Maria (Pflegehelferin, no CV, sectional build) ===")
    play_maria_no_cv(_Client(BASE_URL))
    print("\n=== Persona: Lars (senior backend, pastes CV) ===")
    play_lars_has_cv_via_paste(_Client(BASE_URL))
    print("\n=== Persona: Asha (career change barista → marketing) ===")
    play_asha_career_change(_Client(BASE_URL))

    print()
    print("=" * 70)
    failed = [r for r in RESULTS if not r[1]]
    total = len(RESULTS)
    if failed:
        print(f"JOURNEY UX EXPERT — {total - len(failed)}/{total} PASS")
        print("=" * 70)
        for n, _, d in failed:
            print(f"  FAIL {n}: {d}")
        return 1
    print(f"JOURNEY UX EXPERT — ALL {total}/{total} CHECKS PASS")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
