# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Persona-smoke e2e — Tobias (Berlin, long-term unemployed pivot)."""

from __future__ import annotations

import unittest

from tests.e2e.persona_smoke_helpers import assert_persona_journey_walks_cleanly


class TobiasJourneySmoke(unittest.TestCase):
    def test_full_discover_phase_walks_cleanly(self) -> None:
        assert_persona_journey_walks_cleanly(self, "tobias")


if __name__ == "__main__":
    unittest.main()
