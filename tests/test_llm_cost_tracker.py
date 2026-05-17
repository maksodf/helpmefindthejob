"""R23.6 — LLM call cost tracker.

Verifies cost recording, aggregation, pricing lookup, env overrides,
and graceful behaviour on unknown models. The cost tracker is the
SPEND-side dashboard pair for the R22.9 daily call cap.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company_discovery.llm_cost_tracker import LLMCostTracker
from company_discovery.llm_pricing import (
    estimate_cost_usd, lookup_pricing,
)


class PricingTests(unittest.TestCase):
    def test_known_model_prices(self):
        self.assertEqual(
            lookup_pricing("claude-haiku-4-5"), (0.80, 4.00))
        self.assertEqual(
            lookup_pricing("gpt-4o-mini"), (0.15, 0.60))
        self.assertEqual(
            lookup_pricing("deepseek-chat"), (0.14, 0.28))

    def test_dated_suffix_stripped(self):
        # A model name like "claude-haiku-4-5-20251001" still matches.
        self.assertEqual(
            lookup_pricing("claude-haiku-4-5-20251001"), (0.80, 4.00))

    def test_openrouter_prefix_stripped(self):
        # OpenRouter prefixes "anthropic/" — strip and match.
        self.assertEqual(
            lookup_pricing("anthropic/claude-haiku-4-5"), (0.80, 4.00))

    def test_unknown_model_returns_zero(self):
        self.assertEqual(lookup_pricing("my-future-model"), (0.0, 0.0))

    def test_env_override_wins(self):
        with patch.dict(os.environ, {
            "DIRECTJOB_PRICE_CLAUDE_HAIKU_4_5_IN_USD_M": "0.50",
            "DIRECTJOB_PRICE_CLAUDE_HAIKU_4_5_OUT_USD_M": "2.00",
        }):
            self.assertEqual(
                lookup_pricing("claude-haiku-4-5"), (0.50, 2.00))

    def test_cost_formula(self):
        # 1M input + 1M output at haiku rates → $0.80 + $4 = $4.80
        cost = estimate_cost_usd(
            "claude-haiku-4-5",
            input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(cost, 4.80, places=4)

    def test_cost_small_call(self):
        # Realistic: 500 in + 200 out on haiku
        cost = estimate_cost_usd("claude-haiku-4-5", 500, 200)
        expected = (500 * 0.80 + 200 * 4.00) / 1_000_000
        self.assertAlmostEqual(cost, expected, places=8)

    def test_cost_unknown_model_is_zero(self):
        self.assertEqual(
            estimate_cost_usd("unknown", 9999, 9999), 0.0)

    def test_cost_negative_tokens_safe(self):
        self.assertEqual(
            estimate_cost_usd("gpt-4o", -10, 100), 0.0)


class TrackerRecordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tracker = LLMCostTracker(
            Path(self.tmp) / "llm_costs.sqlite")

    def tearDown(self):
        self.tracker.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_one_call_increments_total(self):
        self.assertEqual(self.tracker.today_total_usd(), 0.0)
        self.tracker.record(
            user_id="u1", provider="anthropic",
            model="claude-haiku-4-5", task="tool_use_chat",
            input_tokens=500, output_tokens=200)
        self.assertGreater(self.tracker.today_total_usd(), 0)

    def test_record_per_user_isolated(self):
        self.tracker.record(
            user_id="alice", provider="anthropic",
            model="claude-haiku-4-5", task="x",
            input_tokens=1000, output_tokens=500)
        self.tracker.record(
            user_id="bob", provider="anthropic",
            model="claude-haiku-4-5", task="x",
            input_tokens=2000, output_tokens=1000)
        alice = self.tracker.today_total_for_user_usd("alice")
        bob = self.tracker.today_total_for_user_usd("bob")
        # Bob spent ~2x Alice.
        self.assertGreater(bob, alice)
        self.assertAlmostEqual(bob, alice * 2, places=6)

    def test_by_provider_aggregates(self):
        self.tracker.record(
            user_id="u1", provider="anthropic",
            model="claude-haiku-4-5", task="x",
            input_tokens=100, output_tokens=50)
        self.tracker.record(
            user_id="u2", provider="openai",
            model="gpt-4o-mini", task="x",
            input_tokens=100, output_tokens=50)
        rows = self.tracker.by_provider_today()
        providers = {r["provider"] for r in rows}
        self.assertSetEqual(providers, {"anthropic", "openai"})

    def test_by_task_aggregates(self):
        for task in ("chat_routing", "motivation_letter",
                       "chat_routing"):
            self.tracker.record(
                user_id="u1", provider="anthropic",
                model="claude-haiku-4-5", task=task,
                input_tokens=100, output_tokens=50)
        rows = self.tracker.by_task_today()
        task_to_calls = {r["task"]: r["calls"] for r in rows}
        self.assertEqual(task_to_calls["chat_routing"], 2)
        self.assertEqual(task_to_calls["motivation_letter"], 1)

    def test_top_users_today_ordered(self):
        # Big spender + small spender.
        for _ in range(10):
            self.tracker.record(
                user_id="big", provider="anthropic",
                model="claude-sonnet-4-6", task="letter",
                input_tokens=500, output_tokens=500)
        self.tracker.record(
            user_id="small", provider="anthropic",
            model="claude-haiku-4-5", task="routing",
            input_tokens=100, output_tokens=50)
        top = self.tracker.top_users_today(limit=5)
        self.assertEqual(top[0]["user_id"], "big")

    def test_record_never_raises(self):
        """Cost tracking must never break the chat — even with junk."""
        # Should silently no-op.
        cost = self.tracker.record(
            user_id="", provider="", model="",
            task="", input_tokens=0, output_tokens=0)
        self.assertEqual(cost, 0.0)


class CostFormulaSpotTests(unittest.TestCase):
    """Sanity-spot-check the operator's expected per-chat cost."""

    def test_typical_chat_turn_haiku_is_under_a_cent(self):
        # 800 in + 300 out on Haiku = $0.001 + $0.0012 ≈ $0.0022
        cost = estimate_cost_usd("claude-haiku-4-5", 800, 300)
        self.assertLess(cost, 0.003)

    def test_premium_letter_drafting_sonnet_under_15_cents(self):
        # 2500 in + 1500 out on Sonnet 4.6 = $0.0075 + $0.0225 = $0.030
        cost = estimate_cost_usd("claude-sonnet-4-6", 2500, 1500)
        self.assertLess(cost, 0.10)


if __name__ == "__main__":
    unittest.main()
