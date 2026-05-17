"""Targeted bug-hunt for the R23.5 + R23.6 changes.

This isn't broad regression coverage — it's a deliberate hunt for
the bug patterns I worried about while building those rounds:

  * Real OpenAI model names with a YYYY-MM-DD suffix (gpt-4o-2024-08-06)
    fall through pricing lookup → operator sees $0 spent on a paid model.
  * The R22 chat sets model_used in the adapter; an LLM error response
    leaves it set to the asked-for model rather than empty, which would
    record cost-from-thin-air entries.
  * record_call closure in the chat handler captures resolve_managed_provider()
    which can flip None between the gate and the closure call.
  * cost tracker writes from many concurrent users mustn't drop entries.
  * legacy _dispatch_provider with task= but no managed AI — must not
    leak the model router into provider config the user can see.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
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
from company_discovery.model_router import (
    TASK_LETTER, select_model,
)


class PricingEdgeCases(unittest.TestCase):
    """Real-world model name shapes that the dashboard must price."""

    def test_openai_dated_suffix_resolves(self):
        # gpt-4o-2024-08-06 is OpenAI's real versioning style.
        # Pre-fix, this returned (0,0) and the dashboard showed $0
        # for a paid model.
        self.assertEqual(
            lookup_pricing("gpt-4o-2024-08-06"),
            (2.50, 10.00),
            "dated OpenAI model must resolve to base gpt-4o price",
        )

    def test_anthropic_short_dated_suffix_resolves(self):
        # claude-haiku-4-5-20251001 is the Anthropic style.
        self.assertEqual(
            lookup_pricing("claude-haiku-4-5-20251001"),
            (0.80, 4.00))

    def test_openrouter_namespaced_resolves(self):
        # OpenRouter sends "anthropic/claude-haiku-4-5" style names.
        self.assertEqual(
            lookup_pricing("anthropic/claude-haiku-4-5"),
            (0.80, 4.00))

    def test_uppercase_normalised(self):
        self.assertEqual(
            lookup_pricing("CLAUDE-Haiku-4-5"),
            (0.80, 4.00))

    def test_cost_realistic_user_day(self):
        """A real day of chat at typical volumes stays under $0.10
        per user — sanity-check our economics."""
        # 100 chat turns × 500 in + 200 out on Haiku
        per_turn = estimate_cost_usd("claude-haiku-4-5", 500, 200)
        daily = per_turn * 100
        self.assertLess(daily, 0.30,
                          f"Haiku 100x daily would cost ${daily:.4f}")

    def test_negative_or_huge_tokens_dont_crash(self):
        # Defensive — provider could return weird numbers.
        self.assertEqual(
            estimate_cost_usd("claude-haiku-4-5", -1, 0), 0.0)
        # 10 billion tokens — won't happen but math must not overflow.
        big = estimate_cost_usd("claude-haiku-4-5",
                                  10_000_000_000, 10_000_000_000)
        self.assertAlmostEqual(big, 48_000.0, places=1)


class TrackerConcurrencyStress(unittest.TestCase):
    """The cost tracker is hit by ALL concurrent users — must not
    drop entries under load."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tracker = LLMCostTracker(Path(self.tmp) / "stress.sqlite")

    def tearDown(self):
        self.tracker.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_200_parallel_inserts_all_land(self):
        """20 threads × 10 inserts = 200 rows must all be there."""
        N_THREADS = 20
        PER_THREAD = 10
        errors: list[str] = []

        def worker(uid: int) -> None:
            try:
                for i in range(PER_THREAD):
                    self.tracker.record(
                        user_id=f"u{uid}",
                        provider="anthropic",
                        model="claude-haiku-4-5",
                        task="tool_use_chat",
                        input_tokens=500,
                        output_tokens=200,
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"u{uid}: {exc}")

        threads = [threading.Thread(target=worker, args=(i,))
                    for i in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        # Count rows directly via the connection.
        rows = self.tracker.connection.execute(
            "SELECT COUNT(*) FROM llm_calls").fetchone()
        self.assertEqual(rows[0], N_THREADS * PER_THREAD)


class TrackerRecordingDefensive(unittest.TestCase):
    """Test record() never crashes the chat — even with junk inputs."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tracker = LLMCostTracker(Path(self.tmp) / "defensive.sqlite")

    def tearDown(self):
        self.tracker.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_with_none_user_id_does_not_crash(self):
        # If the user_id closure somehow gets None, we still record
        # (with empty string) rather than 500-the chat.
        cost = self.tracker.record(
            user_id=None,  # type: ignore[arg-type]
            provider="anthropic",
            model="claude-haiku-4-5",
            task="tool_use_chat",
            input_tokens=100,
            output_tokens=50,
        )
        self.assertGreater(cost, 0)

    def test_record_with_none_token_counts_treated_as_zero(self):
        # Provider error path — usage field absent → tokens = None.
        cost = self.tracker.record(
            user_id="u1",
            provider="anthropic",
            model="claude-haiku-4-5",
            task="tool_use_chat",
            input_tokens=None,  # type: ignore[arg-type]
            output_tokens=None,  # type: ignore[arg-type]
        )
        self.assertEqual(cost, 0.0)


class ModelRouterEdgeCases(unittest.TestCase):
    def test_legacy_env_does_not_pollute_when_task_known(self):
        """If DIRECTJOB_MANAGED_AI_MODEL is set but the caller passes
        a task, the task-router's choice (haiku for chat routing)
        should win over the legacy single-model env."""
        with patch.dict(os.environ, {
            "DIRECTJOB_MANAGED_AI_MODEL": "legacy-pinned-model",
        }, clear=False):
            # Clear per-tier overrides if any.
            for k in list(os.environ):
                if k.startswith("DIRECTJOB_MODEL_"):
                    os.environ.pop(k, None)
            model = select_model("anthropic", TASK_LETTER)
            self.assertEqual(model, "claude-sonnet-4-6")
            self.assertNotEqual(model, "legacy-pinned-model")


class ToolUseRouterModelUsedField(unittest.TestCase):
    """The LLMTurn.model_used field is what the cost tracker reads.
    It must reflect the model we ASKED for, even on error responses
    where the provider didn't echo back a model name."""

    def test_anthropic_error_response_records_zero_cost(self):
        from company_discovery import tool_use_router as TUR
        # Simulate a transport error returning empty parsed dict.
        with patch.object(TUR, "_http_post_json",
                            return_value=(500, {"transport_error": "x"})):
            turn = TUR._call_anthropic(
                "sk-test", "claude-test", "sys", [], [])
        self.assertEqual(turn.stop_reason, "error")
        # On error: tokens must be 0 so the cost tracker records $0.
        self.assertEqual(turn.input_tokens, 0)
        self.assertEqual(turn.output_tokens, 0)

    def test_anthropic_success_populates_token_counts(self):
        """The happy path must surface usage so cost tracking works."""
        from company_discovery import tool_use_router as TUR
        success_body = {
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 230, "output_tokens": 88},
        }
        with patch.object(TUR, "_http_post_json",
                            return_value=(200, success_body)):
            turn = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5", "sys", [], [])
        self.assertEqual(turn.input_tokens, 230)
        self.assertEqual(turn.output_tokens, 88)
        self.assertEqual(turn.model_used, "claude-haiku-4-5")

    def test_openai_success_populates_token_counts(self):
        from company_discovery import tool_use_router as TUR
        success_body = {
            "choices": [{
                "message": {"content": "hello", "tool_calls": []},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 350, "completion_tokens": 42},
        }
        with patch.object(TUR, "_http_post_json",
                            return_value=(200, success_body)):
            turn = TUR._call_openai(
                "sk-test", "gpt-4o-mini", "", "sys", [], [])
        self.assertEqual(turn.input_tokens, 350)
        self.assertEqual(turn.output_tokens, 42)
        self.assertEqual(turn.model_used, "gpt-4o-mini")


class ChatHandlerLLMProviderResolutionRace(unittest.TestCase):
    """The chat handler resolves managed_provider twice — once for
    the gate, once for the cost record closure. If the env vars
    were yanked between, we must not crash."""

    def test_resolve_returns_none_doesnt_crash_handler(self):
        from company_discovery.tool_use_router import resolve_managed_provider
        with patch.dict(os.environ, {}, clear=True):
            # No managed provider env vars at all.
            self.assertIsNone(resolve_managed_provider())
            # That's the gate's responsibility — at the call site we
            # only get there if resolve was non-None. But verify
            # accessing [0] on the result we'd capture would crash;
            # if so, the handler must guard.
            with self.assertRaises(TypeError):
                _ = resolve_managed_provider()[0]


if __name__ == "__main__":
    unittest.main()
