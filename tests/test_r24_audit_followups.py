"""R24.0 — coverage gaps + contract tests caught by the audit.

The deep audit pointed out several behaviour contracts that had
NO explicit test. Pin them down so future refactors can't silently
break them.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.billing import find_plan, plans_payload
from company_discovery.models import UserProfile


class PlansPayloadShapeTests(unittest.TestCase):
    """R23.7 added ``llm_daily_cap`` but no test asserted it's in
    the wire payload. Without this guard, a future refactor could
    drop the field and the frontend cap indicator would silently
    show ``undefined``."""

    def test_every_plan_includes_llm_daily_cap_in_payload(self):
        for plan in plans_payload():
            self.assertIn("llmDailyCap", plan,
                            f"plan {plan['id']!r} missing llmDailyCap")

    def test_free_plan_cap_value(self):
        free = next(p for p in plans_payload() if p["id"] == "free")
        self.assertEqual(free["llmDailyCap"], 5)

    def test_pro_plan_cap_value(self):
        pro = next(p for p in plans_payload() if p["id"] == "pro_monthly")
        self.assertEqual(pro["llmDailyCap"], 50)

    def test_power_plan_cap_value(self):
        power = next(p for p in plans_payload()
                      if p["id"] == "power_monthly")
        self.assertEqual(power["llmDailyCap"], 200)


class AiConsentManagedBypassTests(unittest.TestCase):
    """R23.3: managed AI is covered by ToS+Privacy at signup —
    no per-provider consent banner. Tests pin this behaviour
    so the banner can't sneak back via a refactor."""

    def test_managed_provider_satisfied_without_stored_consent(self):
        profile = UserProfile(user_id="u1")
        # No ai_consent_at on profile.
        provider = AIProviderConfig(
            provider_id="managed", invocation_mode="api")
        self.assertTrue(
            app._ai_consent_satisfied(profile, provider))

    def test_byok_openai_still_requires_consent(self):
        profile = UserProfile(user_id="u1")
        provider = AIProviderConfig(
            provider_id="openai", invocation_mode="api",
            credential_reference="OPENAI_API_KEY")
        # BYOK needs explicit consent.
        self.assertFalse(
            app._ai_consent_satisfied(profile, provider))

    def test_manual_provider_bypasses_consent(self):
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual")
        self.assertTrue(
            app._ai_consent_satisfied(UserProfile(user_id="u1"), provider))


class RecordCallProviderFieldTests(unittest.TestCase):
    """R23.9 / R24.0: ``make_llm_record_call`` returns a closure
    that takes (provider, model, task, in, out). The provider
    must actually land in the cost-tracker row — silently
    recording ``provider=""`` was the original bug."""

    def setUp(self):
        # Clear current-day rows for the test user.
        with app.STATE.llm_cost_tracker._lock:
            app.STATE.llm_cost_tracker.connection.execute(
                "DELETE FROM llm_calls WHERE user_id = ?",
                ("u-test-r24",))
            app.STATE.llm_cost_tracker.connection.commit()

    def test_provider_lands_in_tracker_row(self):
        rec = app.STATE.make_llm_record_call("u-test-r24")
        rec("anthropic", "claude-haiku-4-5", "tool_use_chat",
            500, 200)
        rows = app.STATE.llm_cost_tracker.by_provider_today()
        found = next(
            (r for r in rows if r["provider"] == "anthropic"), None)
        self.assertIsNotNone(found,
                              "anthropic provider missing from by_provider_today()")

    def test_provider_empty_when_caller_passes_empty(self):
        """Defensive — if the dispatcher's provider is missing
        (BYOK with manual config), we should record it as the
        empty string, not crash."""
        rec = app.STATE.make_llm_record_call("u-test-r24")
        rec("", "some-model", "task", 100, 50)
        # Just verifying no crash + the row is recorded with
        # empty provider (not silently dropped).
        rows = app.STATE.llm_cost_tracker.by_provider_today()
        self.assertTrue(any(r["provider"] == "" for r in rows))


class AnthropicCacheTokenAccountingTests(unittest.TestCase):
    """R24.0 — Anthropic's prompt-caching usage block returns three
    input-token buckets. Verify our adapter folds them in with the
    correct cost multipliers."""

    def test_cache_read_tokens_weighted_at_10_percent(self):
        from company_discovery import tool_use_router as TUR
        # Construct a usage payload with cache_read_input_tokens.
        success_body = {
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "cache_read_input_tokens": 1000,
                "output_tokens": 50,
            },
        }
        with patch.object(TUR, "_http_post_json",
                            return_value=(200, success_body)):
            turn = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5", "sys", [], [])
        # 100 + round(1000 * 0.1) + 0 = 200.
        self.assertEqual(turn.input_tokens, 200)
        self.assertEqual(turn.output_tokens, 50)

    def test_cache_creation_tokens_weighted_at_125_percent(self):
        from company_discovery import tool_use_router as TUR
        success_body = {
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 50,
                "cache_creation_input_tokens": 1000,
                "output_tokens": 20,
            },
        }
        with patch.object(TUR, "_http_post_json",
                            return_value=(200, success_body)):
            turn = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5", "sys", [], [])
        # 50 + 0 + round(1000 * 1.25) = 1300.
        self.assertEqual(turn.input_tokens, 1300)

    def test_no_cache_blocks_match_raw_input(self):
        from company_discovery import tool_use_router as TUR
        success_body = {
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 250, "output_tokens": 60},
        }
        with patch.object(TUR, "_http_post_json",
                            return_value=(200, success_body)):
            turn = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5", "sys", [], [])
        # No cache fields → input_tokens == raw input.
        self.assertEqual(turn.input_tokens, 250)


class DispatchProviderRecordsErrorsTests(unittest.TestCase):
    """R24.0 audit: failed AI calls (provider_error / handoff) MUST
    still be recorded — providers charge for input tokens on errors
    too. configuration_error stays excluded (the call never reached
    the provider)."""

    def test_provider_error_status_is_recorded(self):
        from company_discovery import analysis as A
        from company_discovery.ai_providers import AIProviderConfig
        captured: list[tuple] = []

        def fake_executor(prompt, provider, runtime_credential=""):
            return A.AnalysisExecutionResult(
                status="provider_error",
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt=prompt, error="HTTP 500",
                input_tokens=120, output_tokens=0,
                model_used="gpt-4o-mini",
            )

        def rec(provider, model, task, in_tok, out_tok):
            captured.append((provider, model, task, in_tok, out_tok))

        with patch.object(A, "_execute_openai_compatible",
                            new=fake_executor):
            result = A._dispatch_provider(
                "test prompt",
                AIProviderConfig(
                    provider_id="openai", invocation_mode="api",
                    credential_reference="OPENAI_API_KEY"),
                "",
                task="job_brief",
                record_call=rec,
            )
        self.assertEqual(result.status, "provider_error")
        # Even on error, the call WAS recorded.
        self.assertEqual(len(captured), 1,
                          "provider_error result was not recorded — operator dashboard misses it")
        self.assertEqual(captured[0][0], "openai")
        self.assertEqual(captured[0][3], 120)

    def test_configuration_error_is_NOT_recorded(self):
        """A configuration_error means the call never reached the
        provider, so we record nothing."""
        from company_discovery import analysis as A
        from company_discovery.ai_providers import AIProviderConfig

        captured: list[tuple] = []

        def rec(*args):
            captured.append(args)

        # provider with manual mode never dispatches → handoff_required
        # which is also pre-dispatch. Use a real configuration_error
        # path: managed provider without DIRECTJOB_MANAGED_AI_KEY.
        import os
        prev_key = os.environ.pop("DIRECTJOB_MANAGED_AI_KEY", None)
        try:
            result = A._dispatch_provider(
                "test prompt",
                AIProviderConfig(
                    provider_id="managed", invocation_mode="api"),
                "",
                task="job_brief",
                record_call=rec,
            )
        finally:
            if prev_key is not None:
                os.environ["DIRECTJOB_MANAGED_AI_KEY"] = prev_key
        self.assertEqual(result.status, "configuration_error")
        self.assertEqual(captured, [],
                          "configuration_error should NOT record (call never reached provider)")


if __name__ == "__main__":
    unittest.main()
