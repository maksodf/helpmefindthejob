# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W3 D11-12: no-AI / no-network fallback completeness
audit (invariant 9).

The doctrine: this project MUST work without a paid AI provider.
A deployer with no API key, or a user who picked "manual" mode,
MUST still get value from every AI-touching endpoint — either by
running through a heuristic fallback or by receiving the AI prompt
to copy/paste into their tool of choice (ChatGPT, Claude.ai, etc.).

These tests close the audit's "missing E2E coverage" finding by
exercising the dispatch → handoff_required → response loop for
every AI-touching code path. A regression that broke manual mode
would fail here, not in production.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import AppState
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import (
    AnalysisExecutionResult,
    _dispatch_provider,
    _dispatch_provider_streaming,
    execute_auto_fit,
    execute_cover_letter_brief,
    execute_cv_tailoring,
    execute_job_decision_brief,
)
from company_discovery.models import DiscoveredJob, ImportedJob, UserProfile


def _manual_provider() -> AIProviderConfig:
    """Default manual-mode provider — what a user with no AI
    configured gets."""

    return AIProviderConfig(provider_id="manual", invocation_mode="manual")


def _profile() -> UserProfile:
    """Minimal real UserProfile so dispatch sees the expected
    shape (consent fields, target_roles list, etc.)."""

    return UserProfile(
        user_id="test-user",
        persona_id="aicha",
        cv_text="CV content with skills + experience.",
    )


def _imported_job(**overrides) -> ImportedJob:
    """ImportedJob factory matching the dataclass's required
    positional + keyword fields."""

    defaults = dict(
        user_id="test-user",
        company_id="c1",
        discovered_job_id="d1",
        source_url="https://jobs.example.com/p1",
        title="Embedded Engineer",
        company_name="Daimler",
        description="Stuttgart embedded engineering role.",
    )
    defaults.update(overrides)
    return ImportedJob(**defaults)


# ---------------------------------------------------------------------------
# Dispatch-layer contract: manual mode MUST return handoff_required
# ---------------------------------------------------------------------------


class DispatchReturnsHandoffForManual(unittest.TestCase):
    """The core invariant of invariant 9. If a refactor caused
    manual mode to fall through to the network HTTP path, these
    tests would catch it."""

    def test_dispatch_provider_manual_returns_handoff_required(self):
        provider = _manual_provider()
        result = _dispatch_provider(
            "What is the fit score?",
            provider,
            runtime_credential="",
            purpose="fit_score",
        )
        self.assertEqual(result.status, "handoff_required")
        self.assertEqual(result.provider_id, "manual")
        self.assertEqual(result.invocation_mode, "manual")
        self.assertIn("What is the fit score?", result.prompt)
        # The error explains what to do
        self.assertTrue(result.error)

    def test_dispatch_streaming_manual_returns_handoff_required(self):
        provider = _manual_provider()
        tokens = []
        final_result = None
        # Streaming dispatch is a generator yielding ("token", str)
        # events and ending with ("final", AnalysisExecutionResult).
        for event_type, payload in _dispatch_provider_streaming(
            "Draft a German Anschreiben",
            provider,
            runtime_credential="",
            purpose="motivation_letter",
        ):
            if event_type == "token":
                tokens.append(payload)
            elif event_type == "final":
                final_result = payload
        self.assertIsNotNone(final_result)
        self.assertEqual(final_result.status, "handoff_required")
        self.assertIn("Anschreiben", final_result.prompt)
        # Manual mode emits no tokens — there's nothing to stream
        self.assertEqual(tokens, [])

    def test_manual_dispatch_does_not_call_network(self):
        """Defense-in-depth: with manual mode, urllib.request.urlopen
        MUST NOT be called. Anyone who later adds a code path that
        bypasses this check will be caught here."""

        provider = _manual_provider()
        with patch("urllib.request.urlopen") as urlopen_mock:
            _dispatch_provider(
                "any prompt",
                provider,
                runtime_credential="",
                purpose="test",
            )
        urlopen_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Endpoint-layer contract: every execute_* returns handoff for manual
# ---------------------------------------------------------------------------


class ExecuteHandlersHandoffForManual(unittest.TestCase):
    """Every AI-touching entry point in the analysis layer MUST
    return handoff_required when the provider is manual. The
    audit found 5 endpoints route through these; testing each
    closes the coverage gap."""

    def setUp(self) -> None:
        self.provider = _manual_provider()
        self.profile = _profile()

    def test_execute_auto_fit_manual(self):
        job = DiscoveredJob(
            user_id="test-user",
            source_url="https://jobs.example.com/p1",
            title="Pflegekraft Berlin",
            confidence_score=0.9,
            structured_data={"description": "Berlin Pflegestelle"},
        )
        result = execute_auto_fit(
            job,
            "Berliner Pflegeheim",
            self.provider,
            "",
            self.profile,
        )
        self.assertEqual(result.status, "handoff_required")
        self.assertTrue(result.prompt)
        # Prompt must carry the company and job title so the manual
        # handoff is useful.
        self.assertIn("Pflegekraft", result.prompt)
        self.assertIn("Berliner Pflegeheim", result.prompt)

    def test_execute_cover_letter_brief_manual(self):
        imported = _imported_job(
            title="Embedded Engineer",
            company_name="Daimler",
            description="Stuttgart embedded engineering role.",
        )
        result = execute_cover_letter_brief(
            imported,
            self.provider,
            "",
            self.profile,
        )
        self.assertEqual(result.status, "handoff_required")
        self.assertTrue(result.prompt)

    def test_execute_cv_tailoring_manual(self):
        imported = _imported_job(
            title="Anerkennung-friendly clinical role",
            company_name="Hannover Klinikum",
            description="Brandenburg clinical pathway.",
        )
        result = execute_cv_tailoring(
            imported,
            self.provider,
            "",
            self.profile,
        )
        self.assertEqual(result.status, "handoff_required")

    def test_execute_job_decision_brief_manual(self):
        imported = _imported_job(
            title="Quereinstieg Bildung",
            company_name="VHS Berlin",
            description="Career switcher path.",
        )
        result = execute_job_decision_brief(
            imported,
            self.provider,
            "",
            self.profile,
        )
        self.assertEqual(result.status, "handoff_required")


# ---------------------------------------------------------------------------
# Batch /auto-fit-all gap fix: outcomes MUST carry the prompt
# ---------------------------------------------------------------------------


class BatchAutoFitManualMode(unittest.TestCase):
    """W3 D11 fix: batch /auto-fit-all used to silently emit
    handoff_required outcomes WITHOUT the prompt, making batch
    manual mode unusable. This test pins the new contract:
    every handoff outcome carries the prompt."""

    def test_batch_outcome_construction_includes_prompt(self):
        # Reproduce the exact outcome-construction shape the
        # /auto-fit-all route now uses. If the route's shape
        # diverges from this, change BOTH together.
        provider = _manual_provider()
        result = _dispatch_provider(
            "Rank job against candidate",
            provider,
            runtime_credential="",
            purpose="fit_score",
        )
        outcome = {
            "discoveredJobId": "j1",
            "status": result.status,
            "score": None,
            "error": result.error or None,
        }
        if result.status == "handoff_required" and getattr(result, "prompt", None):
            outcome["prompt"] = result.prompt

        self.assertEqual(outcome["status"], "handoff_required")
        self.assertIn("prompt", outcome)
        self.assertTrue(outcome["prompt"])
        self.assertIn("Rank job", outcome["prompt"])


# ---------------------------------------------------------------------------
# AppState default — a fresh deploy MUST land in manual mode
# ---------------------------------------------------------------------------


class FreshDeployDefaultsToManual(unittest.TestCase):
    """Without configuration, a fresh AppState's per-user provider
    lookup MUST return manual mode. If this regressed (e.g. a
    default OpenAI fallback), users without keys would silently
    fail on every AI call."""

    def test_default_provider_is_manual(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = AppState(
                root / "company.sqlite3",
                root / "auth.sqlite3",
                root / "ai.json",
                root / "schedule.json",
                start_scheduler=False,
            )
            try:
                user = state.auth_store.create_user(
                    "fresh@example.com", "secret-pass-12345678"
                )
                provider = state.ai_provider_for(user.id)
                self.assertEqual(provider.invocation_mode, "manual")
                self.assertEqual(provider.provider_id, "manual")
            finally:
                state.auth_store.close()
                state.repository.close()


# ---------------------------------------------------------------------------
# Network failure survivability
# ---------------------------------------------------------------------------


class NoNetworkSurvivability(unittest.TestCase):
    """The doctrine: a network failure in an aggregator MUST NOT
    crash the user-facing journey. Aggregators run inside
    JobAggregationEngine which has its own error-swallowing
    discipline — these tests pin that contract."""

    def test_aggregation_engine_handles_provider_exception(self):
        """If a JobAggregatorProvider raises, the engine returns
        an empty result rather than crashing."""

        from company_discovery.aggregators import JobAggregationEngine

        class _CrashingProvider:
            provider_id = "crashing"
            name = "crashing"

            def fetch(self, *args, **kwargs):
                raise ConnectionError("network down (simulated)")

        engine = JobAggregationEngine(providers=[_CrashingProvider()])
        jobs, outcomes = engine.search(
            query="anything",
            location="Berlin",
        )
        # Engine returned cleanly, no exception escaped
        self.assertEqual(jobs, [])
        # The outcomes list MUST surface the failure so an operator
        # can see why the search yielded nothing — silent zero-result
        # responses are debugging poison.
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].provider, "crashing")
        # The error message is captured so an operator can debug
        self.assertIsNotNone(outcomes[0].error)


if __name__ == "__main__":
    unittest.main()
