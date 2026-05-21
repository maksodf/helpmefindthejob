# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #77 sub-piece (c+d) — chat_handler_draft_motivation_letter_streaming contract.

Asserts the streaming variant of the motivation-letter handler:
- Yields per-token events when a streaming AI is configured
- Yields a final done_payload event with the same shape as the
  single-shot handler's return dict
- Falls back to the templated DACH skeleton when no AI is configured,
  emitting the full template as a single ai_token before done_payload
- Handles missing job / missing CV preconditions identically to the
  single-shot handler (single done_payload with status=false)
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import AppState
from company_discovery.analysis import AnalysisExecutionResult


def _make_state() -> tuple[AppState, str]:
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
    user = state.auth_store.create_user("letter-stream@example.com", "secret-pass-12345678")
    return state, user.id


def _seed_picked_job(state: AppState, user_id: str) -> None:
    """Put a picked job + CV on the user's profile/journey so the
    streaming handler has something to operate on."""
    from company_discovery.journey import UserJourney, PHASE_TAILOR

    profile = state.profile_for(user_id)
    profile.cv_text = (
        "Aïcha Ben Salah\n"
        "Berlin\n"
        "Krankenpflegerin, 7 Jahre Erfahrung\n"
        "Geriatrische Station 2 Jahre\n"
    )
    profile.location = "Berlin"
    job = {
        "title": "Krankenpfleger:in (Anerkennung-friendly)",
        "company": "Beispielarbeitgeber",
        "location": "Berlin",
        "url": "https://example.invalid/job/123",
        "source": "test",
        "description": "Anerkennung-friendly clinical placement in Berlin.",
    }
    journey = UserJourney(phase=PHASE_TAILOR)
    journey.picked_job_id = job["url"]
    journey.search_jobs_by_id = {job["url"]: job}
    merged = dict(profile.chat_state or {})
    merged["journey"] = journey.to_dict()
    profile.chat_state = merged
    state.repository.save_user_profile(profile)


class LetterStreamingContract(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_missing_picked_job_yields_done_payload_with_message(self) -> None:
        events = list(
            self.state.chat_handler_draft_motivation_letter_streaming(self.user_id, {})
        )
        self.assertEqual(len(events), 1)
        kind, payload = events[0]
        self.assertEqual(kind, "done_payload")
        self.assertFalse(payload["ok"])
        self.assertIn("Pick one", payload["message"])

    def test_missing_cv_yields_done_payload_with_cv_hint(self) -> None:
        from company_discovery.journey import UserJourney, PHASE_TAILOR

        profile = self.state.profile_for(self.user_id)
        journey = UserJourney(phase=PHASE_TAILOR)
        journey.picked_job_id = "https://example.invalid/job/1"
        journey.search_jobs_by_id = {
            "https://example.invalid/job/1": {
                "title": "X",
                "company": "Y",
                "location": "Berlin",
                "url": "https://example.invalid/job/1",
                "source": "test",
                "description": "X",
            }
        }
        profile.chat_state = {"journey": journey.to_dict()}
        self.state.repository.save_user_profile(profile)

        events = list(
            self.state.chat_handler_draft_motivation_letter_streaming(self.user_id, {})
        )
        self.assertEqual(len(events), 1)
        kind, payload = events[0]
        self.assertEqual(kind, "done_payload")
        self.assertFalse(payload["ok"])
        self.assertIn("CV", payload["message"])

    def test_no_ai_provider_uses_templated_fallback_single_token(self) -> None:
        _seed_picked_job(self.state, self.user_id)
        # _journey_ai_streaming_caller returns None when no provider.
        events = list(
            self.state.chat_handler_draft_motivation_letter_streaming(self.user_id, {})
        )
        ai_tokens = [e for e in events if e[0] == "ai_token"]
        finals = [e for e in events if e[0] == "done_payload"]
        # Template path: one ai_token carrying the full skeleton, then
        # done_payload.
        self.assertEqual(len(ai_tokens), 1)
        self.assertEqual(len(finals), 1)
        self.assertTrue(finals[0][1]["ok"])
        # The templated DACH skeleton always carries the "Sehr geehrte"
        # salutation or the "Mit freundlichen Grüßen" close (or both).
        self.assertIn(ai_tokens[0][1]["text"], finals[0][1]["letter"])

    def test_streaming_ai_emits_tokens_then_done_payload(self) -> None:
        _seed_picked_job(self.state, self.user_id)

        # Build a streaming-letter-shaped DACH response so
        # looks_like_dach_letter accepts it.
        dach_chunks = [
            "Aïcha Ben Salah, Berlin\n\n",
            "Beispielarbeitgeber\nBerlin\n\n",
            "Bewerbung als Krankenpfleger:in\n\n",
            "Sehr geehrte Damen und Herren,\n\n",
            "ich bringe sieben Jahre klinische Erfahrung mit.\n\n",
            "Mit freundlichen Grüßen,\nAïcha Ben Salah\n",
        ]

        def fake_streaming_caller():
            def _stream(system, user_msg, *, purpose):
                for chunk in dach_chunks:
                    yield ("token", chunk)
                yield (
                    "final",
                    AnalysisExecutionResult(
                        status="completed",
                        provider_id="ollama",
                        invocation_mode="local_http",
                        output="".join(dach_chunks),
                        prompt=system + "\n\n" + user_msg,
                    ),
                )
            return _stream

        with patch.object(
            self.state, "_journey_ai_streaming_caller", return_value=fake_streaming_caller()
        ):
            events = list(
                self.state.chat_handler_draft_motivation_letter_streaming(self.user_id, {})
            )

        ai_tokens = [e for e in events if e[0] == "ai_token"]
        finals = [e for e in events if e[0] == "done_payload"]
        self.assertEqual(len(ai_tokens), len(dach_chunks))
        # Tokens emitted in input order
        self.assertEqual(
            [e[1]["text"] for e in ai_tokens],
            dach_chunks,
        )
        # Final payload carries the accumulated letter
        self.assertEqual(len(finals), 1)
        self.assertTrue(finals[0][1]["ok"])
        self.assertEqual(finals[0][1]["letter"], "".join(dach_chunks))


if __name__ == "__main__":
    unittest.main()
