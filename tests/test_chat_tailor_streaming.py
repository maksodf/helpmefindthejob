# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #77 top-tier upgrade item 3 — chat_handler_tailor_cv_streaming contract.

Asserts the streaming variant of the tailor-cv handler:
- Yields per-token events when a streaming AI is configured
- Yields a final done_payload event with the same shape as the
  single-shot handler's return dict (plus ``tailored`` carrying the
  full text and ``streamed=True`` set on the analytics log)
- Handles missing imported job / missing CV / missing AI consent
  preconditions identically to the single-shot handler (single
  done_payload with status=false and a hint message)
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import AppState
from company_discovery.analysis import AnalysisExecutionResult
from company_discovery.models import ImportedJob


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
    user = state.auth_store.create_user("tailor-stream@example.com", "secret-pass-12345678")
    return state, user.id


def _seed_imported_job(state: AppState, user_id: str) -> ImportedJob:
    """Save a minimal ImportedJob for the user and return it."""
    job = ImportedJob(
        user_id=user_id,
        company_id="c-tailor-stream-1",
        discovered_job_id="d-tailor-stream-1",
        source_url="https://example.invalid/job/tailor-1",
        title="Krankenpfleger:in (Anerkennung-friendly)",
        company_name="Beispielarbeitgeber",
        location="Berlin",
        description="Anerkennung-friendly clinical placement in Berlin.",
    )
    state.repository.save_imported_job(job)
    return job


class TailorStreamingContract(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_missing_imported_job_yields_done_payload_with_message(self) -> None:
        events = list(
            self.state.chat_handler_tailor_cv_streaming(
                self.user_id, {"importedJobId": "no-such-id"}
            )
        )
        self.assertEqual(len(events), 1)
        kind, payload = events[0]
        self.assertEqual(kind, "done_payload")
        self.assertFalse(payload["ok"])
        self.assertIn("not found", payload["message"])

    def test_missing_cv_yields_done_payload_with_cv_hint(self) -> None:
        job = _seed_imported_job(self.state, self.user_id)
        # No cv_text on the profile.
        events = list(
            self.state.chat_handler_tailor_cv_streaming(
                self.user_id, {"importedJobId": job.id}
            )
        )
        self.assertEqual(len(events), 1)
        kind, payload = events[0]
        self.assertEqual(kind, "done_payload")
        self.assertFalse(payload["ok"])
        self.assertIn("CV", payload["message"])

    def test_no_streaming_caller_yields_empty_result_done_payload(self) -> None:
        """Without an AI provider configured, _journey_ai_streaming_caller
        returns None and the handler should emit a single done_payload
        with ok=False indicating no streaming output (no fake fallback)."""
        job = _seed_imported_job(self.state, self.user_id)
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Aïcha Ben Salah\nBerlin\nKrankenpflegerin, 7 Jahre Erfahrung\n"
        # Grant AI consent so we reach the streaming-caller branch
        profile.ai_consent_provider_id = "manual"
        profile.ai_consent_at = "2026-05-21T00:00:00Z"
        self.state.repository.save_user_profile(profile)

        events = list(
            self.state.chat_handler_tailor_cv_streaming(
                self.user_id, {"importedJobId": job.id}
            )
        )
        ai_tokens = [e for e in events if e[0] == "ai_token"]
        finals = [e for e in events if e[0] == "done_payload"]
        self.assertEqual(len(ai_tokens), 0)
        self.assertEqual(len(finals), 1)
        # No streaming caller → ok=False with a hint
        self.assertFalse(finals[0][1]["ok"])
        self.assertIn("provider_error", finals[0][1]["message"])

    def test_streaming_ai_emits_tokens_then_done_payload(self) -> None:
        job = _seed_imported_job(self.state, self.user_id)
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Aïcha Ben Salah\nBerlin\nKrankenpflegerin, 7 Jahre Erfahrung\n"
        profile.ai_consent_provider_id = "ollama"
        profile.ai_consent_at = "2026-05-21T00:00:00Z"
        self.state.repository.save_user_profile(profile)

        tailored_chunks = [
            "AÏCHA BEN SALAH\n",
            "Krankenpflegerin · 7 Jahre Erfahrung\n\n",
            "PROFIL\n",
            "Geriatrie-Schwerpunkt, Anerkennung in Bearbeitung.\n\n",
            "ERFAHRUNG\n",
            "2018–2025 · Klinikum Hamadi, Tunis\n",
        ]

        def fake_streaming_caller():
            def _stream(system, user_msg, *, purpose):
                for chunk in tailored_chunks:
                    yield ("token", chunk)
                yield (
                    "final",
                    AnalysisExecutionResult(
                        status="completed",
                        provider_id="ollama",
                        invocation_mode="local_http",
                        output="".join(tailored_chunks),
                        prompt=system + "\n\n" + user_msg,
                    ),
                )
            return _stream

        with patch.object(
            self.state, "_journey_ai_streaming_caller", return_value=fake_streaming_caller()
        ):
            events = list(
                self.state.chat_handler_tailor_cv_streaming(
                    self.user_id, {"importedJobId": job.id}
                )
            )

        ai_tokens = [e for e in events if e[0] == "ai_token"]
        finals = [e for e in events if e[0] == "done_payload"]
        self.assertEqual(len(ai_tokens), len(tailored_chunks))
        self.assertEqual(
            [e[1]["text"] for e in ai_tokens],
            tailored_chunks,
        )
        self.assertEqual(len(finals), 1)
        self.assertTrue(finals[0][1]["ok"])
        self.assertEqual(finals[0][1]["tailored"], "".join(tailored_chunks))
        # tailoredExcerpt is the first 400 chars (matches the
        # single-shot handler's contract)
        self.assertEqual(
            finals[0][1]["tailoredExcerpt"],
            "".join(tailored_chunks)[:400],
        )


if __name__ == "__main__":
    unittest.main()
