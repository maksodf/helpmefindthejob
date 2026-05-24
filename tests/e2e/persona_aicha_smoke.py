# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Persona-smoke e2e — Aïcha (Tunisia → Berlin, §16d Anerkennung).

PlanTowardPerfection Ceiling-2 box 2.5.9. See
`tests/e2e/persona_smoke_helpers.py` for the helper + rationale
on why the in-process pattern is used rather than Playwright.
"""

from __future__ import annotations

import unittest

from tests.e2e.persona_smoke_helpers import assert_persona_journey_walks_cleanly


class AichaJourneySmoke(unittest.TestCase):
    def test_full_discover_phase_walks_cleanly(self) -> None:
        assert_persona_journey_walks_cleanly(self, "aicha")


if __name__ == "__main__":
    unittest.main()
