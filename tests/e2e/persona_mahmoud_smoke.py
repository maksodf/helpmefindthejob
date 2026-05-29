# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Persona-smoke e2e — Mahmoud (Syria → Hamburg, §4 Subsidiärer Schutz)."""

from __future__ import annotations

import unittest

from tests.e2e.persona_smoke_helpers import assert_persona_journey_walks_cleanly


class MahmoudJourneySmoke(unittest.TestCase):
    def test_full_discover_phase_walks_cleanly(self) -> None:
        assert_persona_journey_walks_cleanly(self, "mahmoud")


if __name__ == "__main__":
    unittest.main()
