# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #46 — BYO-AI per-user cost cap contract."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.cost_caps import (
    DEFAULT_MONTHLY_CAP_EUR,
    PROVIDER_RATES_EUR_PER_MTOK,
    CostCapExceeded,
    CostEstimate,
    enforce_cap,
    estimate_eur,
    month_to_date_eur,
    record_invocation,
)
from company_discovery.models import AnalyticsEvent
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository


def _make_repo() -> tuple[SqliteCompanyDiscoveryRepository, TemporaryDirectory]:
    tmp = TemporaryDirectory()
    repo = SqliteCompanyDiscoveryRepository(Path(tmp.name) / "r.sqlite3")
    return repo, tmp


class CostEstimation(unittest.TestCase):
    def test_estimate_zero_for_empty_prompt(self) -> None:
        e = estimate_eur("openai", "")
        self.assertEqual(e.prompt_tokens, 0)
        self.assertEqual(e.total_eur, 0.0)

    def test_estimate_charges_prompt_and_completion_separately(self) -> None:
        # ~1000-char prompt + ~500-char response, OpenAI rates
        e = estimate_eur("openai", "x" * 1000, "y" * 500)
        # 1000 chars → 250 tokens; rates are €2.30 / Mtok
        # expected prompt_eur ≈ 250 / 1_000_000 * 2.30 ≈ 0.000575
        self.assertGreater(e.prompt_eur, 0)
        self.assertGreater(e.completion_eur, 0)
        self.assertGreater(e.completion_eur, e.prompt_eur * 0.4)

    def test_estimate_zero_for_free_provider(self) -> None:
        for free in ("ollama", "manual", "claude_code"):
            e = estimate_eur(free, "x" * 10_000, "y" * 5_000)
            self.assertEqual(e.total_eur, 0.0, f"{free} should not charge")

    def test_estimate_zero_for_unknown_provider(self) -> None:
        # Unknown provider → no rate table → 0 (don't block legitimate calls)
        e = estimate_eur("invented_provider", "x" * 1000)
        self.assertEqual(e.total_eur, 0.0)

    def test_all_listed_providers_have_both_rates(self) -> None:
        for pid, rates in PROVIDER_RATES_EUR_PER_MTOK.items():
            self.assertIn("prompt_per_mtok", rates, f"{pid} missing prompt rate")
            self.assertIn("completion_per_mtok", rates, f"{pid} missing completion rate")
            self.assertGreaterEqual(rates["prompt_per_mtok"], 0)
            self.assertGreaterEqual(rates["completion_per_mtok"], 0)

    def test_every_PROVIDER_OPTIONS_id_has_a_rate_entry(self) -> None:
        """Drift guard: every provider_id in PROVIDER_OPTIONS MUST
        have a rate-table entry. A missing entry = cap bypass (the
        estimate falls to 0 → user can spend unlimited)."""

        from company_discovery.ai_providers import PROVIDER_OPTIONS

        configured_ids = {opt.id for opt in PROVIDER_OPTIONS}
        rate_table_ids = set(PROVIDER_RATES_EUR_PER_MTOK.keys())
        missing = configured_ids - rate_table_ids
        self.assertFalse(
            missing,
            f"Rate table missing entries for provider_id(s) {sorted(missing)} — cap bypass risk",
        )

    def test_paid_cloud_providers_have_nonzero_rates(self) -> None:
        """Specific provider_ids known to be paid APIs MUST have
        non-zero rates. This catches the specific bug where
        'google_gemini' was missing → users could spend unlimited."""

        paid = {"openai", "anthropic", "google_gemini", "deepseek", "openrouter", "custom"}
        for pid in paid:
            rates = PROVIDER_RATES_EUR_PER_MTOK[pid]
            self.assertGreater(
                rates["prompt_per_mtok"],
                0,
                f"{pid} is a paid API but has zero prompt rate — cap bypass",
            )
            self.assertGreater(
                rates["completion_per_mtok"],
                0,
                f"{pid} is a paid API but has zero completion rate — cap bypass",
            )


class MonthToDate(unittest.TestCase):
    def setUp(self) -> None:
        self.repo, self.tmp = _make_repo()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.repo.close)

    def test_zero_for_user_with_no_events(self) -> None:
        self.assertEqual(month_to_date_eur("u_empty", self.repo), 0.0)

    def test_sums_only_cost_events(self) -> None:
        u = "u_test"
        self.repo.save_analytics_event(
            AnalyticsEvent(
                user_id=u,
                kind="ai_invocation_cost",
                payload={"estimated_eur": 1.25},
            )
        )
        self.repo.save_analytics_event(
            AnalyticsEvent(
                user_id=u,
                kind="ai_invocation_cost",
                payload={"estimated_eur": 0.75},
            )
        )
        # Non-cost events must NOT count
        self.repo.save_analytics_event(
            AnalyticsEvent(
                user_id=u,
                kind="chat_cmd",
                payload={"estimated_eur": 99.0},
            )
        )
        self.assertEqual(month_to_date_eur(u, self.repo), 2.0)

    def test_ignores_other_users(self) -> None:
        self.repo.save_analytics_event(
            AnalyticsEvent(user_id="u_a", kind="ai_invocation_cost", payload={"estimated_eur": 5.0})
        )
        self.repo.save_analytics_event(
            AnalyticsEvent(user_id="u_b", kind="ai_invocation_cost", payload={"estimated_eur": 3.0})
        )
        self.assertEqual(month_to_date_eur("u_a", self.repo), 5.0)
        self.assertEqual(month_to_date_eur("u_b", self.repo), 3.0)


class EnforceCap(unittest.TestCase):
    def setUp(self) -> None:
        self.repo, self.tmp = _make_repo()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.repo.close)

    def test_local_mode_never_triggers_cap(self) -> None:
        # Even with cap=0, local mode should always pass
        for mode in ("local_http", "local_cli", "manual"):
            e = enforce_cap(
                user_id="u",
                repository=self.repo,
                cap_eur=0.0,
                provider_id="ollama",
                invocation_mode=mode,
                prompt_text="x" * 10_000,
            )
            self.assertEqual(e.total_eur, 0.0)

    def test_passes_when_under_cap(self) -> None:
        e = enforce_cap(
            user_id="u",
            repository=self.repo,
            cap_eur=5.0,
            provider_id="openai",
            invocation_mode="api",
            prompt_text="x" * 1000,
        )
        self.assertGreater(e.total_eur, 0)
        self.assertLess(e.total_eur, 5.0)

    def test_raises_when_call_pushes_over_cap(self) -> None:
        # Seed €4.99 of spend; a €0.01 next call would push over €5.00
        self.repo.save_analytics_event(
            AnalyticsEvent(user_id="u", kind="ai_invocation_cost", payload={"estimated_eur": 4.99})
        )
        with self.assertRaises(CostCapExceeded) as cm:
            enforce_cap(
                user_id="u",
                repository=self.repo,
                cap_eur=5.0,
                provider_id="openai",
                invocation_mode="api",
                prompt_text="x" * 50_000,  # forces a real cost > 0.01
            )
        err = cm.exception
        self.assertEqual(err.cap_eur, 5.0)
        self.assertEqual(err.spent_eur, 4.99)
        self.assertGreater(err.next_call_eur, 0)
        self.assertIn("€", str(err))

    def test_german_locale_emits_german_message(self) -> None:
        self.repo.save_analytics_event(
            AnalyticsEvent(user_id="u", kind="ai_invocation_cost", payload={"estimated_eur": 4.99})
        )
        with self.assertRaises(CostCapExceeded) as cm:
            enforce_cap(
                user_id="u",
                repository=self.repo,
                cap_eur=5.0,
                provider_id="openai",
                invocation_mode="api",
                prompt_text="x" * 50_000,
                locale="de",
            )
        self.assertIn("Monatliches", str(cm.exception))

    def test_repository_read_failure_triggers_fail_closed(self) -> None:
        """Quality audit (2026-05-21): if the analytics-events read
        fails, enforce_cap MUST refuse the AI call. Previous
        behaviour silently assumed 0 spend on read failure, which
        would effectively disable the cap whenever the DB
        hiccupped — a cap-bypass vector."""

        class BrokenRepository:
            def list_analytics_events(self, **_kwargs):
                raise RuntimeError("simulated_db_failure")

        broken = BrokenRepository()
        with self.assertRaises(CostCapExceeded) as cm:
            enforce_cap(
                user_id="u",
                repository=broken,
                cap_eur=100.0,
                provider_id="openai",
                invocation_mode="api",
                prompt_text="x" * 1000,
            )
        # The synthetic exception carries cap_eur as spent_eur to
        # signal "we don't know, assume worst" to operators.
        self.assertEqual(cm.exception.spent_eur, 100.0)

    def test_month_to_date_raises_typed_exception_on_repo_failure(self) -> None:
        """The fail-closed contract: month_to_date_eur raises
        CostHistoryUnavailable on repo failure, not a generic
        Exception. Callers depend on the typed signal."""

        from company_discovery.cost_caps import CostHistoryUnavailable

        class BrokenRepository:
            def list_analytics_events(self, **_kwargs):
                raise RuntimeError("simulated_db_failure")

        with self.assertRaises(CostHistoryUnavailable):
            month_to_date_eur("u", BrokenRepository())

    def test_default_cap_constant_is_modest_but_nonzero(self) -> None:
        # Sanity: the default must be > 0 (else no one can call API
        # without configuring) and < 50 EUR (else not really a cap).
        self.assertGreater(DEFAULT_MONTHLY_CAP_EUR, 0)
        self.assertLess(DEFAULT_MONTHLY_CAP_EUR, 50)


class RecordInvocation(unittest.TestCase):
    def setUp(self) -> None:
        self.repo, self.tmp = _make_repo()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.repo.close)

    def test_record_writes_event_that_month_to_date_picks_up(self) -> None:
        before = month_to_date_eur("u", self.repo)
        record_invocation(
            user_id="u",
            repository=self.repo,
            provider_id="openai",
            invocation_mode="api",
            prompt_text="x" * 1000,
            response_text="y" * 500,
        )
        after = month_to_date_eur("u", self.repo)
        self.assertGreater(after, before)

    def test_record_works_for_free_provider_with_zero_cost(self) -> None:
        e = record_invocation(
            user_id="u",
            repository=self.repo,
            provider_id="ollama",
            invocation_mode="local_http",
            prompt_text="x" * 1000,
        )
        self.assertEqual(e.total_eur, 0.0)
        # But the event still got written (call-count audit)
        self.assertEqual(month_to_date_eur("u", self.repo), 0.0)
        events = self.repo.list_analytics_events(user_id="u")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "ai_invocation_cost")


if __name__ == "__main__":
    unittest.main()
