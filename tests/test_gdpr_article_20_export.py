# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #54 — GDPR Article 20 data-portability contract.

Asserts that ``AppState.export_data(user_id)``:
1. Carries every category of personal data the controller holds for
   the user (identity, profile + CV, watchlist + applications,
   conversational state, analytics, support tickets, push subs,
   workspace memberships).
2. Never leaks secrets the user did not provide (password hashes,
   session secrets, TOTP shared secrets, other users' data).
3. Returns a JSON-serialisable structure that round-trips through
   ``json.dumps`` without losing structure (Article 20 requires
   "structured, commonly used and machine-readable format").
4. Returns the user's own data only, scoped by ``user_id`` — a second
   user's data must not leak into the first user's export.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState


def _make_state() -> tuple[AppState, str, str]:
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    state = AppState(
        root / "company.sqlite3",
        root / "auth.sqlite3",
        root / "ai.json",
        root / "schedule.json",
        start_scheduler=False,
    )
    state._test_tmp = tmp  # noqa: SLF001
    user_a = state.auth_store.create_user("alice@example.com", "secret-pass-12345678")
    user_b = state.auth_store.create_user("bob@example.com", "secret-pass-12345678")
    return state, user_a.id, user_b.id


class Article20ExportContract(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.alice_id, self.bob_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001
        # Seed Alice with profile + CV + chat history
        profile = self.state.profile_for(self.alice_id)
        profile.cv_text = "Alice Jones, Berlin, 5 yrs Backend"
        profile.location = "Berlin"
        profile.persona_id = "yusuf"
        profile.locale = "en"
        profile.theme = "dark"
        profile.industry = "tech"
        self.state.repository.save_user_profile(profile)
        session = self.state.chat_session_for(self.alice_id)
        from company_discovery.chat_router import ChatTurn

        session.history.append(ChatTurn(role="user", content="hello"))
        session.history.append(ChatTurn(role="assistant", content="hi alice"))

    def test_export_contains_top_level_categories(self) -> None:
        out = self.state.export_data(self.alice_id)
        required = {
            "schemaVersion",
            "exportedAt",
            "appVersion",
            "user",
            "profile",
            "companies",
            "discoveredJobs",
            "importedJobs",
            "scans",
            "discoveryRuns",
            "savedSearches",
            "watchlistSchedule",
            "aiProvider",
            "chatHistory",
            "journeyState",
            "analyticsEvents",
            "supportTickets",
            "pushSubscriptions",
            "workspaceMemberships",
        }
        missing = required - set(out.keys())
        self.assertFalse(missing, f"Article 20 export missing required categories: {missing}")

    def test_export_carries_user_identity_without_secrets(self) -> None:
        out = self.state.export_data(self.alice_id)
        user_block = out["user"]
        self.assertEqual(user_block["id"], self.alice_id)
        self.assertEqual(user_block["email"], "alice@example.com")
        self.assertIn("role", user_block)
        self.assertIn("twoFactorEnrolled", user_block)
        # Verify no password / TOTP / session secrets leaked
        flat = json.dumps(out, default=str).lower()
        self.assertNotIn("password_hash", flat)
        self.assertNotIn("passwordhash", flat)
        self.assertNotIn("totp_secret", flat)
        self.assertNotIn("totpsecret", flat)
        self.assertNotIn("session_secret", flat)

    def test_export_carries_full_profile_including_cv_text(self) -> None:
        out = self.state.export_data(self.alice_id)
        profile = out["profile"]
        self.assertEqual(profile["cvText"], "Alice Jones, Berlin, 5 yrs Backend")
        self.assertEqual(profile["personaId"], "yusuf")
        self.assertEqual(profile["locale"], "en")
        self.assertEqual(profile["theme"], "dark")
        self.assertEqual(profile["industry"], "tech")
        self.assertEqual(profile["location"], "Berlin")

    def test_export_carries_chat_history(self) -> None:
        out = self.state.export_data(self.alice_id)
        chat = out["chatHistory"]
        self.assertGreaterEqual(len(chat), 2)
        self.assertEqual(chat[0]["role"], "user")
        self.assertEqual(chat[0]["content"], "hello")
        self.assertEqual(chat[1]["role"], "assistant")
        self.assertEqual(chat[1]["content"], "hi alice")

    def test_export_is_json_serialisable(self) -> None:
        out = self.state.export_data(self.alice_id)
        # Must round-trip through json.dumps without TypeError.
        # default=str is allowed because the controller hands the
        # blob to the user as JSON — datetimes get stringified.
        blob = json.dumps(out, default=str)
        self.assertGreater(len(blob), 200)
        # And reparseable
        roundtrip = json.loads(blob)
        self.assertEqual(roundtrip["user"]["email"], "alice@example.com")

    def test_export_is_scoped_to_user_no_cross_tenant_leak(self) -> None:
        # Seed Bob with distinct profile
        bob_profile = self.state.profile_for(self.bob_id)
        bob_profile.cv_text = "Bob Smith, Hamburg, 10 yrs Frontend"
        bob_profile.location = "Hamburg"
        self.state.repository.save_user_profile(bob_profile)
        bob_session = self.state.chat_session_for(self.bob_id)
        from company_discovery.chat_router import ChatTurn

        bob_session.history.append(ChatTurn(role="user", content="bob-secret-message"))

        alice_export = self.state.export_data(self.alice_id)
        alice_flat = json.dumps(alice_export, default=str).lower()
        self.assertNotIn("bob smith", alice_flat)
        self.assertNotIn("bob-secret-message", alice_flat)
        self.assertNotIn("bob@example.com", alice_flat)

    def test_export_carries_warnings_field_empty_on_clean_load(self) -> None:
        """Quality-audit transparency surface: every export carries
        _exportWarnings, empty when nothing failed to load."""
        out = self.state.export_data(self.alice_id)
        self.assertIn("_exportWarnings", out)
        self.assertEqual(out["_exportWarnings"], [])

    def test_export_warnings_populated_on_partial_load_failure(self) -> None:
        """If a category fails to load, the export must record
        WHY in _exportWarnings — never silently drop. A regulator
        reading the export needs to tell apart 'no data' from
        'data not loaded'."""
        # Force the journey loader to raise
        original_journey_load = self.state._journey_load

        def _broken_journey(uid):
            raise RuntimeError("simulated journey corruption")

        self.state._journey_load = _broken_journey
        try:
            out = self.state.export_data(self.alice_id)
        finally:
            self.state._journey_load = original_journey_load
        warnings = out["_exportWarnings"]
        # Exactly one warning for journeyState
        journey_warnings = [w for w in warnings if w["category"] == "journeyState"]
        self.assertEqual(len(journey_warnings), 1)
        self.assertEqual(journey_warnings[0]["code"], "load_failed")
        self.assertIn("simulated journey corruption", journey_warnings[0]["detail"])
        # journeyState itself is None — but the rest of the export
        # is intact (no cascading failure)
        self.assertIsNone(out["journeyState"])
        self.assertIsNotNone(out["user"])
        self.assertIsNotNone(out["profile"])

    def test_export_works_for_minimal_user_with_no_data(self) -> None:
        # A fresh user with no seeded data should still get a
        # well-formed export — the user has the right to KNOW that
        # we hold nothing on them.
        from app import AppState as _AS  # avoid shadow

        tmp = TemporaryDirectory()
        root = Path(tmp.name)
        state = _AS(
            root / "c.sqlite3",
            root / "a.sqlite3",
            root / "i.json",
            root / "s.json",
            start_scheduler=False,
        )
        try:
            fresh = state.auth_store.create_user("fresh@example.com", "secret-pass-12345678")
            out = state.export_data(fresh.id)
            self.assertEqual(out["user"]["email"], "fresh@example.com")
            self.assertEqual(out["companies"], [])
            self.assertEqual(out["importedJobs"], [])
            self.assertEqual(out["chatHistory"], [])
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
