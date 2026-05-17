"""R22.9 + R23.7 — per-user daily LLM-call budget cap.

The router calls a managed LLM for every chat message in supported
phases. Without a cap, one user spamming the chat can burn through
the operator's API budget. R23.7 makes the cap plan-aware — Free
tier gets a small taste, Pro gets the typical user's full day,
Power gets headroom for heavy weeks. The env var stays as an
operator escape hatch.

Resolution order:
1. ``DIRECTJOB_LLM_DAILY_CAP`` env (positive int = cap, negative = unlimited)
2. Subscription plan's ``llm_daily_cap`` (None = unlimited)
3. 0 (managed AI off)
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from company_discovery.billing import Plan, Subscription


def _stub_subscription(plan_id: str):
    """Patch get_subscription to return a fake plan_id without touching disk."""
    sub = Subscription(plan_id=plan_id)
    return patch.object(app.STATE, "get_subscription",
                          return_value=sub)


class CapResolutionTests(unittest.TestCase):
    """Verify the resolution order: env → plan → 0."""

    def setUp(self):
        with app.STATE._llm_tool_use_lock:
            app.STATE._llm_tool_use_calls.clear()
        # Strip any DIRECTJOB_LLM_DAILY_CAP set by prior tests.
        os.environ.pop("DIRECTJOB_LLM_DAILY_CAP", None)

    def test_no_subscription_returns_zero(self):
        """No plan = no managed AI. The chat must still work via the
        deterministic path — that's the fallback UX."""
        # Force the resolver to see plan=None
        with patch("company_discovery.billing.find_plan",
                    return_value=None):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 0)

    def test_free_plan_caps_at_5(self):
        with _stub_subscription("free"):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 5)

    def test_pro_plan_caps_at_50(self):
        with _stub_subscription("pro_monthly"):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 50)

    def test_power_plan_caps_at_200(self):
        with _stub_subscription("power_monthly"):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 200)

    def test_env_positive_overrides_plan(self):
        """Operator can lower or raise the cap regardless of plan
        — useful for development or incident throttling."""
        with _stub_subscription("pro_monthly"), patch.dict(
                os.environ, {"DIRECTJOB_LLM_DAILY_CAP": "3"}):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 3)

    def test_env_negative_means_unlimited(self):
        """Negative env = unlimited (operator's full-firehose mode)."""
        with _stub_subscription("free"), patch.dict(
                os.environ, {"DIRECTJOB_LLM_DAILY_CAP": "-1"}):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"),
                sys.maxsize)

    def test_env_invalid_falls_to_plan(self):
        with _stub_subscription("free"), patch.dict(
                os.environ, {"DIRECTJOB_LLM_DAILY_CAP": "banana"}):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 5)

    def test_env_zero_falls_to_plan(self):
        """Env=0 should be treated as 'no override' so the plan takes
        over — surprising to set 0 expecting unlimited."""
        with _stub_subscription("pro_monthly"), patch.dict(
                os.environ, {"DIRECTJOB_LLM_DAILY_CAP": "0"}):
            self.assertEqual(
                app.STATE.llm_daily_cap_for_user("u1"), 50)


class SlotClaimingTests(unittest.TestCase):
    """The claim_llm_tool_use_slot path is what the chat handler hits."""

    def setUp(self):
        with app.STATE._llm_tool_use_lock:
            app.STATE._llm_tool_use_calls.clear()
        os.environ.pop("DIRECTJOB_LLM_DAILY_CAP", None)

    def test_free_user_blocks_after_5_claims(self):
        with _stub_subscription("free"):
            for _ in range(5):
                self.assertTrue(
                    app.STATE.claim_llm_tool_use_slot("alice"))
            self.assertFalse(
                app.STATE.claim_llm_tool_use_slot("alice"))

    def test_pro_user_gets_50_claims(self):
        with _stub_subscription("pro_monthly"):
            for i in range(50):
                self.assertTrue(
                    app.STATE.claim_llm_tool_use_slot(f"u{i % 3}")
                    if False else app.STATE.claim_llm_tool_use_slot("p1"),
                    f"failed at call {i + 1}")
            self.assertFalse(
                app.STATE.claim_llm_tool_use_slot("p1"))

    def test_per_user_isolation_on_plan_cap(self):
        """One user hitting the cap doesn't lock out another."""
        with _stub_subscription("free"):
            for _ in range(5):
                app.STATE.claim_llm_tool_use_slot("alice")
            self.assertFalse(
                app.STATE.claim_llm_tool_use_slot("alice"))
            # bob is fresh — gets the full 5.
            self.assertTrue(
                app.STATE.claim_llm_tool_use_slot("bob"))

    def test_no_managed_ai_when_plan_returns_zero(self):
        """If plan.llm_daily_cap=0 the user cannot use managed AI
        at all — first claim returns False."""
        zero_plan = Plan(
            id="zero", label="Zero", monthly_price_eur=0,
            seats_included=1, features=(),
            llm_daily_cap=0,
        )
        with patch("company_discovery.billing.find_plan",
                    return_value=zero_plan):
            self.assertFalse(
                app.STATE.claim_llm_tool_use_slot("u1"))

    def test_unlimited_plan_never_blocks(self):
        unlimited_plan = Plan(
            id="vip", label="VIP", monthly_price_eur=999,
            seats_included=1, features=(),
            llm_daily_cap=None,
        )
        with patch("company_discovery.billing.find_plan",
                    return_value=unlimited_plan):
            for _ in range(100):
                self.assertTrue(
                    app.STATE.claim_llm_tool_use_slot("vip"))

    def test_read_only_count_matches(self):
        with _stub_subscription("pro_monthly"):
            for _ in range(7):
                app.STATE.claim_llm_tool_use_slot("user-z")
        self.assertEqual(
            app.STATE.llm_tool_use_count_today("user-z"), 7)


if __name__ == "__main__":
    unittest.main()
