# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Tier-limit framework (Phase 2 tracker items #24 + #25).

Each ``Plan`` carries four tier-limit fields beyond label/price:

- ``saved_search_limit`` — None for unlimited, int for a hard cap.
- ``ai_modes_allowed`` — subset of (``manual``, ``byok``, ``managed``).
- ``retention_days_max`` — ceiling on per-user retention preferences.
- ``daily_digest_enabled`` — whether the digest cron applies.

The shipped ``pilot`` plan caps saved searches at 3 and only allows
manual AI; ``team`` and ``org`` are unlimited / all modes. Tests
exercise the enforcement points without depending on any operator-
side env wiring.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.billing import PLANS, find_plan


class PlanShapeTests(unittest.TestCase):
    def test_each_shipped_plan_carries_limits(self) -> None:
        for plan in PLANS:
            self.assertIsInstance(plan.ai_modes_allowed, tuple)
            self.assertIn(plan.daily_digest_enabled, (True, False))
            self.assertIsInstance(plan.retention_days_max, int)

    def test_pilot_is_the_restricted_one(self) -> None:
        pilot = find_plan("pilot")
        self.assertEqual(pilot.saved_search_limit, 3)
        self.assertEqual(pilot.ai_modes_allowed, ("manual",))
        self.assertFalse(pilot.daily_digest_enabled)

    def test_team_unlocks_byok_and_managed(self) -> None:
        team = find_plan("team")
        self.assertIsNone(team.saved_search_limit)
        self.assertIn("byok", team.ai_modes_allowed)
        self.assertIn("managed", team.ai_modes_allowed)
        self.assertTrue(team.daily_digest_enabled)


class PlanLimitsHelperTests(unittest.TestCase):
    def _state_on_plan(self, plan_id: str) -> AppState:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        sub = state.get_subscription()
        sub.plan_id = plan_id
        state.billing_backend.save(sub)
        return state

    def test_pilot_plan_limits_match_definition(self) -> None:
        state = self._state_on_plan("pilot")
        limits = state.plan_limits()
        self.assertEqual(limits["savedSearchLimit"], 3)
        self.assertEqual(limits["aiModesAllowed"], ("manual",))
        self.assertEqual(limits["retentionDaysMax"], 30)
        self.assertFalse(limits["dailyDigestEnabled"])

    def test_unknown_plan_falls_back_to_permissive(self) -> None:
        state = self._state_on_plan("ghost-plan-not-in-PLANS")
        limits = state.plan_limits()
        self.assertIsNone(limits["savedSearchLimit"])
        self.assertEqual(set(limits["aiModesAllowed"]), {"manual", "byok", "managed"})


class SavedSearchLimitTests(unittest.TestCase):
    def _state_with_user(self, plan_id: str) -> tuple[AppState, str]:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        sub = state.get_subscription()
        sub.plan_id = plan_id
        state.billing_backend.save(sub)
        user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
        return state, user.id

    def test_pilot_blocks_creation_past_three(self) -> None:
        state, user_id = self._state_with_user("pilot")
        for n in range(3):
            state.save_saved_search(user_id, {"name": f"search-{n}"})
        with self.assertRaises(ValueError) as ctx:
            state.save_saved_search(user_id, {"name": "search-4"})
        self.assertEqual(str(ctx.exception), "plan_saved_search_limit")

    def test_team_does_not_block(self) -> None:
        state, user_id = self._state_with_user("team")
        # Add ten without raising.
        for n in range(10):
            state.save_saved_search(user_id, {"name": f"search-{n}"})
        self.assertEqual(len(state.repository.list_saved_searches(user_id)), 10)

    def test_editing_existing_search_at_limit_is_allowed(self) -> None:
        state, user_id = self._state_with_user("pilot")
        records = [state.save_saved_search(user_id, {"name": f"search-{n}"}) for n in range(3)]
        # User is at the cap. Editing an existing one is fine.
        renamed = state.save_saved_search(user_id, {"id": records[0].id, "name": "renamed"})
        self.assertEqual(renamed.name, "renamed")


class AiModeLockingTests(unittest.TestCase):
    def _state_on_plan(self, plan_id: str) -> AppState:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        sub = state.get_subscription()
        sub.plan_id = plan_id
        state.billing_backend.save(sub)
        return state

    def test_pilot_allows_manual_only(self) -> None:
        state = self._state_on_plan("pilot")
        state.assert_ai_mode_allowed("manual")  # no raise
        with self.assertRaises(ValueError):
            state.assert_ai_mode_allowed("byok")
        with self.assertRaises(ValueError):
            state.assert_ai_mode_allowed("managed")

    def test_team_unlocks_byok_and_managed(self) -> None:
        state = self._state_on_plan("team")
        state.assert_ai_mode_allowed("manual")
        state.assert_ai_mode_allowed("byok")
        state.assert_ai_mode_allowed("managed")

    def test_update_ai_provider_refuses_byok_on_pilot(self) -> None:
        state = self._state_on_plan("pilot")
        user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
        with self.assertRaises(ValueError) as ctx:
            state.update_ai_provider(
                user.id,
                {
                    "providerId": "openai",
                    "invocationMode": "api",
                    "credentialReference": "OPENAI_API_KEY",
                },
            )
        self.assertEqual(str(ctx.exception), "plan_ai_mode_locked")

    def test_update_ai_provider_accepts_byok_on_team(self) -> None:
        state = self._state_on_plan("team")
        user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
        config = state.update_ai_provider(
            user.id,
            {
                "providerId": "openai",
                "invocationMode": "api",
                "credentialReference": "OPENAI_API_KEY",
            },
        )
        self.assertEqual(config.invocation_mode, "api")


if __name__ == "__main__":
    unittest.main()
