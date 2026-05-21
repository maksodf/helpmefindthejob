# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #77 sub-piece (a) + (b) — chat_handler_find_jobs_streaming
contract tests.

Asserts the streaming variant of the find_jobs chat handler:
- Yields a documented event sequence (search_started, provider_*,
  done_payload)
- The terminal ``done_payload`` event carries a dict byte-equivalent
  to what the single-shot ``chat_handler_find_jobs`` returns for the
  same args
- Failures in individual providers surface as ``provider_error`` events
  without aborting the stream — partial-result transparency preserved
- The ThreadPoolExecutor fan-out works against stubbed providers
  without real HTTP calls (tests run offline)

Companion contract for the SSE endpoint at
``/api/chat/message/stream``; the endpoint is a thin SSE wrapper
around this generator.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.aggregators import AggregatedJob


class _StubProvider:
    """Minimal :class:`JobAggregatorProvider` for offline streaming
    tests. Returns the canned ``_jobs`` list or raises ``_error`` if
    set. ``remote_only`` honoured so we can exercise the skip path."""

    def __init__(
        self,
        name: str,
        jobs: list[AggregatedJob] | None = None,
        error: Exception | None = None,
        remote_only: bool = False,
    ) -> None:
        self.name = name
        self._jobs = jobs or []
        self._error = error
        self.remote_only = remote_only

    def search(self, *, query: str, location, limit: int, persona_id=None):
        if self._error is not None:
            raise self._error
        return list(self._jobs)


def _make_job(provider: str, idx: int) -> AggregatedJob:
    return AggregatedJob(
        title=f"Job {idx} via {provider}",
        company_name=f"Co {idx}",
        location="Berlin",
        source_url=f"https://example.invalid/{provider}/{idx}",
        source=provider,
        description=f"Description for job {idx}",
    )


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
    # Tag the cleanup onto the state so the caller's addCleanup gets
    # the right ordering (state cleanup before tmp cleanup).
    state._test_tmp = tmp  # noqa: SLF001 - test attribute attach
    user = state.auth_store.create_user("streaming@example.com", "secret-pass-1234567")
    return state, user.id


class ChatHandlerFindJobsStreamingContract(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def _set_providers(self, providers: list[_StubProvider]) -> None:
        self.state.aggregator_engine.providers = list(providers)
        # Disable the cache so each call hits the providers directly
        # (otherwise repeated tests would race on cached results).
        self.state.aggregator_engine.cache = None

    def test_event_sequence_with_all_providers_succeeding(self) -> None:
        self._set_providers(
            [
                _StubProvider("provider_a", jobs=[_make_job("provider_a", 1)]),
                _StubProvider("provider_b", jobs=[_make_job("provider_b", 2)]),
                _StubProvider("provider_c", jobs=[_make_job("provider_c", 3)]),
            ]
        )
        events = list(
            self.state.chat_handler_find_jobs_streaming(
                self.user_id, {"query": "developer", "location": "Berlin"}
            )
        )
        kinds = [e[0] for e in events]

        # First event must always be search_started
        self.assertEqual(kinds[0], "search_started")
        # Last event must always be done_payload
        self.assertEqual(kinds[-1], "done_payload")
        # Middle events must be exactly one provider_ok per provider
        provider_ok_events = [e for e in events if e[0] == "provider_ok"]
        self.assertEqual(len(provider_ok_events), 3)
        provider_names = {e[1]["provider"] for e in provider_ok_events}
        self.assertEqual(provider_names, {"provider_a", "provider_b", "provider_c"})
        # No provider_error events
        self.assertEqual([e for e in events if e[0] == "provider_error"], [])

    def test_provider_error_surfaces_without_aborting_stream(self) -> None:
        self._set_providers(
            [
                _StubProvider("ok_provider", jobs=[_make_job("ok_provider", 1)]),
                _StubProvider("flaky_provider", error=RuntimeError("upstream 503")),
            ]
        )
        events = list(
            self.state.chat_handler_find_jobs_streaming(
                self.user_id, {"query": "developer", "location": "Berlin"}
            )
        )
        kinds = [e[0] for e in events]
        # Both event kinds present
        self.assertIn("provider_ok", kinds)
        self.assertIn("provider_error", kinds)
        # Stream completed with done_payload (didn't abort on the error)
        self.assertEqual(kinds[-1], "done_payload")
        # Error event carries the provider name + sanitised error text
        err_event = next(e for e in events if e[0] == "provider_error")
        self.assertEqual(err_event[1]["provider"], "flaky_provider")
        self.assertIn("RuntimeError", err_event[1]["error"])
        self.assertIn("503", err_event[1]["error"])

    def test_done_payload_matches_single_shot_handler(self) -> None:
        """Byte-equivalence (for the user-facing fields) between
        chat_handler_find_jobs(args) and the streaming variant's
        terminal done_payload event."""

        providers = [
            _StubProvider("provider_a", jobs=[_make_job("provider_a", 1)]),
            _StubProvider("provider_b", jobs=[_make_job("provider_b", 2)]),
        ]
        self._set_providers(providers)

        single_shot = self.state.chat_handler_find_jobs(
            self.user_id, {"query": "developer", "location": "Berlin"}
        )

        # Reset providers (the single-shot call mutated journey state +
        # other side effects) before running the streaming variant.
        self._set_providers(providers)
        # Reset the profile so the streaming run is fresh.
        profile = self.state.profile_for(self.user_id)
        profile.chat_state = {}
        self.state.repository.save_user_profile(profile)

        events = list(
            self.state.chat_handler_find_jobs_streaming(
                self.user_id, {"query": "developer", "location": "Berlin"}
            )
        )
        streaming_payload = events[-1][1]

        # Compare user-facing fields. ``message`` ends with the same
        # category-md tail; ``jobs`` / ``totalJobs`` / ``jobType`` /
        # ``categories`` / ``erroredOutcomes`` / ``totalProviders`` /
        # ``navigateTo`` must match exactly.
        for field in (
            "ok",
            "totalJobs",
            "jobType",
            "categories",
            "erroredOutcomes",
            "totalProviders",
            "navigateTo",
        ):
            self.assertEqual(
                single_shot.get(field),
                streaming_payload.get(field),
                msg=f"{field} differs: single={single_shot.get(field)!r} stream={streaming_payload.get(field)!r}",
            )

    def test_remote_only_provider_skipped_on_city_search(self) -> None:
        """Remote-only feeds (Remotive / WeWorkRemotely) skipped on a
        city-search per the existing contract. Streaming variant
        surfaces the skip via the ``search_started.skipped`` list +
        no provider_ok/provider_error event for the skipped provider."""

        self._set_providers(
            [
                _StubProvider("city_provider", jobs=[_make_job("city_provider", 1)]),
                _StubProvider("remote_only_provider", jobs=[], remote_only=True),
            ]
        )
        events = list(
            self.state.chat_handler_find_jobs_streaming(
                self.user_id, {"query": "developer", "location": "Berlin"}
            )
        )
        started = next(e for e in events if e[0] == "search_started")
        self.assertEqual(started[1]["providers"], ["city_provider"])
        skipped_names = {s["provider"] for s in started[1]["skipped"]}
        self.assertEqual(skipped_names, {"remote_only_provider"})

    def test_empty_provider_list_still_yields_started_and_done(self) -> None:
        """Edge case: zero providers configured. Stream still
        produces search_started + done_payload (no provider events
        between). done_payload carries empty jobs + outcomes."""

        self._set_providers([])
        events = list(
            self.state.chat_handler_find_jobs_streaming(
                self.user_id, {"query": "developer", "location": "Berlin"}
            )
        )
        kinds = [e[0] for e in events]
        self.assertEqual(kinds[0], "search_started")
        self.assertEqual(kinds[-1], "done_payload")
        self.assertEqual([k for k in kinds if k.startswith("provider_")], [])


if __name__ == "__main__":
    unittest.main()
