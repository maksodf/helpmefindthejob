# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #46 chat-handler integration — verify the cost-cap gate
actually refuses AI invocations at the handler boundary."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import AnalyticsEvent, ImportedJob


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
    user = state.auth_store.create_user("cap-int@example.com", "secret-pass-12345678")
    return state, user.id


def _seed_imported_job(state: AppState, user_id: str) -> ImportedJob:
    job = ImportedJob(
        user_id=user_id,
        company_id="c-cap-int-1",
        discovered_job_id="d-cap-int-1",
        source_url="https://example.invalid/job/cap-1",
        title="Backend Engineer",
        company_name="Test GmbH",
        location="Berlin",
        description="Backend role.",
    )
    state.repository.save_imported_job(job)
    return job


class CostCapChatHandlerIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def _set_paid_api_provider(self) -> None:
        # Bypass plan-tier gating (tests run as the default plan,
        # which may not allow byok; the integration we care about
        # is the cost-cap gate, not the plan gate). Setting the
        # provider dict directly.
        from company_discovery.ai_providers import AIProviderConfig

        self.state.ai_providers[self.user_id] = AIProviderConfig(
            provider_id="openai",
            invocation_mode="api",
            credential_reference="OPENAI_API_KEY_TEST",
        )

    def _seed_spend(self, eur: float) -> None:
        self.state.repository.save_analytics_event(
            AnalyticsEvent(
                user_id=self.user_id,
                kind="ai_invocation_cost",
                payload={"estimated_eur": eur},
            )
        )

    def test_tailor_cv_returns_cap_exceeded_when_user_is_over_cap(self) -> None:
        self._set_paid_api_provider()
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV text " * 50
        profile.monthly_spend_cap_eur = 1.0
        profile.ai_consent_provider_id = "openai"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)
        # Seed spend that exceeds the cap
        self._seed_spend(2.5)

        result = self.state.chat_handler_tailor_cv(
            self.user_id, {"importedJobId": job.id}
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result.get("code"), "cost_cap_exceeded")
        self.assertIn("€", result["message"])

    def test_tailor_cv_streaming_yields_cap_exceeded_done_payload(self) -> None:
        self._set_paid_api_provider()
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV text " * 50
        profile.monthly_spend_cap_eur = 1.0
        profile.ai_consent_provider_id = "openai"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)
        self._seed_spend(2.5)

        events = list(
            self.state.chat_handler_tailor_cv_streaming(
                self.user_id, {"importedJobId": job.id}
            )
        )
        finals = [e for e in events if e[0] == "done_payload"]
        # The streaming variant should yield exactly one done_payload
        # with cost_cap_exceeded. It must NOT have yielded any tokens
        # (the cap check refuses the call up front).
        self.assertEqual(len(finals), 1)
        payload = finals[0][1]
        self.assertFalse(payload["ok"])
        self.assertEqual(payload.get("code"), "cost_cap_exceeded")
        ai_tokens = [e for e in events if e[0] == "ai_token"]
        self.assertEqual(len(ai_tokens), 0)

    def test_execute_cv_tailoring_enforces_cap_at_chokepoint(self) -> None:
        """Phase 2 #46 root-cause refactor verification: even when a
        caller bypasses the chat handler (e.g. direct REST endpoint
        call to /api/imported-jobs/{id}/tailor-cv), the cap must
        still be enforced because the chokepoint is at
        _dispatch_provider, not at the handler.
        """

        from company_discovery.analysis import execute_cv_tailoring
        from company_discovery.cost_caps import CostCapExceeded

        self._set_paid_api_provider()
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV text " * 50
        profile.monthly_spend_cap_eur = 1.0
        profile.ai_consent_provider_id = "openai"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)
        self._seed_spend(2.5)

        provider = self.state.ai_provider_for(self.user_id)
        ctx = self.state.cost_cap_context_for(self.user_id)
        with self.assertRaises(CostCapExceeded):
            execute_cv_tailoring(
                job, provider, "", profile, cap_context=ctx
            )

    def test_execute_cover_letter_brief_enforces_cap_at_chokepoint(self) -> None:
        """Same as above for the cover-letter path. Closes the
        bypass at the /api/imported-jobs/{id}/draft-cover-letter
        REST endpoint."""

        from company_discovery.analysis import execute_cover_letter_brief
        from company_discovery.cost_caps import CostCapExceeded

        self._set_paid_api_provider()
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV text"
        profile.monthly_spend_cap_eur = 1.0
        profile.ai_consent_provider_id = "openai"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)
        self._seed_spend(2.5)

        provider = self.state.ai_provider_for(self.user_id)
        ctx = self.state.cost_cap_context_for(self.user_id)
        with self.assertRaises(CostCapExceeded):
            execute_cover_letter_brief(
                job, provider, "", profile, cap_context=ctx
            )

    def test_update_profile_persists_monthly_cap(self) -> None:
        """The user must be able to change their cap via the
        profile-update API. Without this, the default 5.0 is
        unchangeable — a UX gap."""

        profile = self.state.update_profile(
            self.user_id, {"monthlySpendCapEur": 25.0}
        )
        self.assertEqual(profile.monthly_spend_cap_eur, 25.0)

    def test_update_profile_clamps_cap_to_safe_range(self) -> None:
        """Cap is clamped 0–500 EUR. Negative values become 0;
        anything over 500 becomes 500."""

        profile = self.state.update_profile(
            self.user_id, {"monthlySpendCapEur": -10.0}
        )
        self.assertEqual(profile.monthly_spend_cap_eur, 0.0)
        profile = self.state.update_profile(
            self.user_id, {"monthlySpendCapEur": 99999.0}
        )
        self.assertEqual(profile.monthly_spend_cap_eur, 500.0)

    def test_update_profile_rejects_non_numeric_cap(self) -> None:
        """Garbage values raise — not silently default to 5.0."""

        with self.assertRaises(ValueError):
            self.state.update_profile(
                self.user_id, {"monthlySpendCapEur": "expensive"}
            )

    def test_bootstrap_payload_surfaces_cap(self) -> None:
        """The Settings UI reads the cap from the bootstrap payload."""

        self.state.update_profile(self.user_id, {"monthlySpendCapEur": 7.5})
        bootstrap = self.state.bootstrap(self.user_id)
        self.assertEqual(bootstrap["profile"]["monthlySpendCapEur"], 7.5)

    def test_cap_context_with_zero_cap_blocks_any_charged_call(self) -> None:
        """Sanity: a cap of 0 must block any non-free call. This
        catches off-by-one bugs in the > vs >= comparison."""

        from company_discovery.analysis import execute_cv_tailoring
        from company_discovery.cost_caps import CostCapContext, CostCapExceeded

        self._set_paid_api_provider()
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV"
        profile.ai_consent_provider_id = "openai"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)

        provider = self.state.ai_provider_for(self.user_id)
        zero_ctx = CostCapContext(
            user_id=self.user_id,
            repository=self.state.repository,
            cap_eur=0.0,
            locale="en",
        )
        with self.assertRaises(CostCapExceeded):
            execute_cv_tailoring(job, provider, "", profile, cap_context=zero_ctx)

    def test_cap_refusal_writes_analytics_event(self) -> None:
        """Refused calls leave no AI-invocation audit (no call
        happened) but MUST leave an ai_invocation_refused_cap
        analytics event so ops + the user can see refusal
        history. Without this, refused calls would be invisible.
        """

        from company_discovery.analysis import execute_cv_tailoring
        from company_discovery.cost_caps import CostCapExceeded

        self._set_paid_api_provider()
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV"
        profile.monthly_spend_cap_eur = 1.0
        profile.ai_consent_provider_id = "openai"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)
        self._seed_spend(2.5)

        provider = self.state.ai_provider_for(self.user_id)
        ctx = self.state.cost_cap_context_for(self.user_id)
        with self.assertRaises(CostCapExceeded):
            execute_cv_tailoring(job, provider, "", profile, cap_context=ctx)

        # Refusal event present
        events = self.state.repository.list_analytics_events(user_id=self.user_id)
        refusals = [e for e in events if e.kind == "ai_invocation_refused_cap"]
        self.assertEqual(len(refusals), 1)
        payload = refusals[0].payload
        self.assertEqual(payload["purpose"], "tailor_cv")
        self.assertEqual(payload["provider_id"], "openai")
        self.assertEqual(payload["cap_eur"], 1.0)
        self.assertEqual(payload["spent_eur"], 2.5)

    def test_local_provider_never_hits_cap_even_with_seeded_spend(self) -> None:
        # Set provider to ollama (local_http, free) — no matter how
        # much spend is seeded, the handler must NOT refuse the call.
        from company_discovery.ai_providers import AIProviderConfig

        self.state.ai_providers[self.user_id] = AIProviderConfig(
            provider_id="ollama",
            invocation_mode="local_http",
            base_url="http://localhost:11434",
            model="llama3.2",
        )
        profile = self.state.profile_for(self.user_id)
        profile.cv_text = "Sample CV text " * 50
        profile.monthly_spend_cap_eur = 0.01  # impossible cap
        profile.ai_consent_provider_id = "ollama"
        from datetime import datetime, timezone

        profile.ai_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        job = _seed_imported_job(self.state, self.user_id)
        self._seed_spend(100.0)

        result = self.state.chat_handler_tailor_cv(
            self.user_id, {"importedJobId": job.id}
        )
        # The call may fail for other reasons (no real ollama
        # running), but it must NOT fail with cost_cap_exceeded.
        self.assertNotEqual(result.get("code"), "cost_cap_exceeded")


if __name__ == "__main__":
    unittest.main()
