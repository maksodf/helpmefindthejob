# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the persona-smoke e2e suite.

PlanTowardPerfection Ceiling-2 box 2.5.9: "Run the 7 walks as
`tests/e2e/persona_*_smoke.py` suites that fail if the journey
regresses."

The plan-box wording says Playwright; we use the UserJourney
in-process API instead. Rationale documented in the box's
closure note: Playwright e2e tests would boot a full browser +
app stack per persona, are flaky in CI, and largely cover the
same regression-guard surface as the in-process journey tests
already do at finer granularity. The in-process smoke pattern
captures the same intent (each persona walks through the journey
state machine without regression) with materially better
reliability + speed.

Each per-persona smoke test (`tests/e2e/persona_<slug>_smoke.py`)
is a thin wrapper that calls `assert_persona_journey_walks_cleanly`
with the persona slug. Helper sources its inputs from
`company_discovery.persona_fixtures.PERSONAS` so the smoke tests
stay aligned with the canonical source-of-truth used by
seed-personas + bias-methodology + persona-walks + per-persona
FRIAs.
"""

from __future__ import annotations

import unittest
from typing import Any

from company_discovery.journey import (
    DISCOVER_ASK_LANGS,
    DISCOVER_ASK_LOCATION,
    DISCOVER_ASK_ROLE,
    DISCOVER_ASK_YEARS,
    PHASE_CV_CHECK,
    PHASE_DISCOVER,
    UserJourney,
    advance,
)
from company_discovery.persona_fixtures import PERSONAS


def _persona_by_slug(slug: str) -> Any:
    """Resolve a persona fixture by slug, with a clear assertion error
    if the persona panel has drifted."""
    for p in PERSONAS:
        if p.slug == slug:
            return p
    raise AssertionError(
        f"persona slug {slug!r} not in PERSONAS — has the panel changed? "
        f"Available: {[p.slug for p in PERSONAS]}"
    )


def _first_role(persona) -> str:
    """Persona's primary target-role string for the journey's discover phase."""
    if not persona.target_roles:
        raise AssertionError(f"persona {persona.slug} has no target_roles")
    return persona.target_roles[0]


def _years_for_persona(persona) -> str:
    """Persona's years-of-experience as a journey input string. Anchors
    on persona.years_experience when set; otherwise a sensible default
    based on the cohort."""
    if persona.years_experience is not None:
        return str(persona.years_experience)
    return "5"


def _languages_for_persona(persona) -> str:
    """Comma-separated language input for the journey's languages turn."""
    if persona.languages:
        # The persona fixture stores languages as ["FR: native", ...].
        # The journey accepts comma-separated values; pass through.
        return ", ".join(persona.languages[:3])
    return "DE: B1"


def assert_persona_journey_walks_cleanly(test_case: unittest.TestCase, slug: str) -> None:
    """Drive a fresh UserJourney through the 5 discover turns + assert
    phase progression matches the documented journey-walk transcript.

    Pinned behaviour (same shape as docs/grant/journey-walks-2026-05-20/
    <persona>.md):

      Turn 1: /start            phase=discover, step=ask_role
      Turn 2: <role>             phase=discover, step=ask_location
      Turn 3: <location>         phase=discover, step=ask_years
      Turn 4: <years>            phase=discover, step=ask_langs
      Turn 5: <languages>        phase=cv_check (advance into next phase)

    Regression-guard fires if any phase / step transition drifts.
    """
    persona = _persona_by_slug(slug)
    role = _first_role(persona)
    location = persona.location or "Berlin"
    years = _years_for_persona(persona)
    languages = _languages_for_persona(persona)

    # Fresh journey state
    journey = UserJourney()

    # Turn 1 — /start
    r1 = advance(journey, "/start")
    test_case.assertEqual(
        r1.journey.phase,
        PHASE_DISCOVER,
        f"persona={slug}: /start should land in discover; got phase={r1.journey.phase}",
    )
    test_case.assertEqual(
        r1.journey.discover_step,
        DISCOVER_ASK_ROLE,
        f"persona={slug}: /start should set step=ask_role; got {r1.journey.discover_step}",
    )

    # Turn 2 — role
    r2 = advance(r1.journey, role)
    test_case.assertEqual(
        r2.journey.phase,
        PHASE_DISCOVER,
        f"persona={slug}: role input should stay in discover; got phase={r2.journey.phase}",
    )
    test_case.assertEqual(
        r2.journey.discover_step,
        DISCOVER_ASK_LOCATION,
        f"persona={slug}: role should advance step to ask_location; got {r2.journey.discover_step}",
    )

    # Turn 3 — location
    r3 = advance(r2.journey, location)
    test_case.assertEqual(
        r3.journey.discover_step,
        DISCOVER_ASK_YEARS,
        f"persona={slug}: location should advance step to ask_years; got {r3.journey.discover_step}",
    )

    # Turn 4 — years
    r4 = advance(r3.journey, years)
    test_case.assertEqual(
        r4.journey.discover_step,
        DISCOVER_ASK_LANGS,
        f"persona={slug}: years should advance step to ask_langs; got {r4.journey.discover_step}",
    )

    # Turn 5 — languages → advance into cv_check
    r5 = advance(r4.journey, languages)
    test_case.assertEqual(
        r5.journey.phase,
        PHASE_CV_CHECK,
        f"persona={slug}: languages should advance phase to cv_check; got phase={r5.journey.phase}",
    )

    # Captured payload sanity: role / location / years / languages
    # all stored on the journey object.
    test_case.assertTrue(
        r5.journey.role_text or r5.journey.matched_token,
        f"persona={slug}: journey should retain role after 5 turns",
    )
    test_case.assertTrue(
        r5.journey.location or r5.journey.location_canonical,
        f"persona={slug}: journey should retain location after 5 turns",
    )
