# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for the live chat → journey path (the demo's core flow).

The persona_smoke suite drives the journey via the pure advance() function; this
test drives AppState.chat_journey_step — the in-process entry the HTTP
/api/chat/message handler calls — so the routing + per-turn profile persistence
the live demo relies on stays working. It mirrors the runtime HTTP walk
(login -> /start -> discover answers -> cv_check) that proved the demo journey
end-to-end against a booted instance.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState


def _state() -> tuple[AppState, str]:
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    state = AppState(
        root / "c.sqlite3", root / "a.sqlite3", root / "ai.json", root / "s.json",
        start_scheduler=False,
    )
    state._test_tmp = tmp  # noqa: SLF001 - keep tempdir alive
    user = state.auth_store.create_user("walk@x.test", "WalkPass12345678")
    return state, user.id


class ChatJourneyPathTests(unittest.TestCase):
    def test_journey_advances_discover_to_cv_check_with_replies(self) -> None:
        state, uid = _state()
        self.addCleanup(state.auth_store.close)
        steps = [
            ("/start", "discover"),
            ("Registered nurse", "discover"),
            ("Berlin", "discover"),
            ("7 years", "discover"),
            ("English, German B1", "cv_check"),
        ]
        for msg, expected_phase in steps:
            result = state.chat_journey_step(uid, msg)
            self.assertTrue(
                (result.get("message") or "").strip(), f"{msg!r} produced no chat reply"
            )
            phase = result.get("journeyPhase")
            self.assertEqual(
                phase, expected_phase, f"after {msg!r}: phase={phase!r}, expected {expected_phase!r}"
            )
        # the discover answers were persisted to the profile (role captured)
        journey = state._journey_load(uid)  # noqa: SLF001
        self.assertTrue(getattr(journey, "role_text", "") or getattr(journey, "target_roles", []))


if __name__ == "__main__":
    unittest.main()
