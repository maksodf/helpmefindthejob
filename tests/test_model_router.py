"""R23.5 — per-task model router.

Verifies the resolver picks the right model for each (provider, task)
combination and honours both per-tier env overrides and the legacy
single-model env. The vision: cheap tasks use cheap models without
compromising user-perceived quality on premium ones.
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

from company_discovery.model_router import (
    DEFAULT_MODELS, TASK_CHAT_ROUTING, TASK_CV_CONSULT,
    TASK_KEYWORD_EXTRACTION, TASK_LETTER, TASK_TOOL_USE_CHAT,
    TIER_CHEAP, TIER_MEDIUM, TIER_PREMIUM,
    select_model, tier_for_task,
)


class TierMappingTests(unittest.TestCase):
    def test_cheap_tasks_mapped_to_cheap_tier(self):
        for task in (TASK_CHAT_ROUTING, TASK_KEYWORD_EXTRACTION):
            self.assertEqual(tier_for_task(task), TIER_CHEAP,
                              f"{task} should be cheap")

    def test_premium_tasks_mapped_to_premium_tier(self):
        for task in (TASK_LETTER, TASK_CV_CONSULT):
            self.assertEqual(tier_for_task(task), TIER_PREMIUM,
                              f"{task} should be premium")

    def test_default_medium_when_unknown_task(self):
        self.assertEqual(tier_for_task("unknown_made_up_task"),
                          TIER_MEDIUM)


class DefaultModelSelectionTests(unittest.TestCase):
    """No env overrides — purely the baked-in defaults."""

    def setUp(self):
        # Clear any DIRECTJOB_MODEL_* env vars so we test pure defaults.
        keys_to_clear = [k for k in os.environ
                          if k.startswith("DIRECTJOB_MODEL_")
                          or k == "DIRECTJOB_MANAGED_AI_MODEL"]
        self._patch = patch.dict(os.environ,
                                   {k: "" for k in keys_to_clear},
                                   clear=False)
        self._patch.start()
        for k in keys_to_clear:
            os.environ.pop(k, None)

    def tearDown(self):
        self._patch.stop()

    def test_anthropic_premium_picks_sonnet(self):
        self.assertEqual(
            select_model("anthropic", TASK_LETTER),
            "claude-sonnet-4-6")

    def test_anthropic_cheap_picks_haiku(self):
        self.assertEqual(
            select_model("anthropic", TASK_CHAT_ROUTING),
            "claude-haiku-4-5")

    def test_openai_premium_picks_4o(self):
        self.assertEqual(
            select_model("openai", TASK_LETTER), "gpt-4o")

    def test_openai_cheap_picks_4o_mini(self):
        self.assertEqual(
            select_model("openai", TASK_CHAT_ROUTING),
            "gpt-4o-mini")

    def test_deepseek_premium_picks_reasoner(self):
        self.assertEqual(
            select_model("deepseek", TASK_LETTER),
            "deepseek-reasoner")

    def test_deepseek_cheap_picks_chat(self):
        self.assertEqual(
            select_model("deepseek", TASK_CHAT_ROUTING),
            "deepseek-chat")

    def test_gemini_premium_picks_pro(self):
        self.assertEqual(
            select_model("google_gemini", TASK_LETTER),
            "gemini-1.5-pro")

    def test_medium_task_uses_medium_tier(self):
        """Tool-use chat is MEDIUM — should match the medium model."""
        self.assertEqual(
            select_model("anthropic", TASK_TOOL_USE_CHAT),
            DEFAULT_MODELS["anthropic"][TIER_MEDIUM])


class EnvOverrideTests(unittest.TestCase):
    def test_per_tier_env_override_wins_over_default(self):
        with patch.dict(os.environ, {
            "DIRECTJOB_MODEL_ANTHROPIC_PREMIUM": "claude-opus-4-7",
        }, clear=False):
            self.assertEqual(
                select_model("anthropic", TASK_LETTER),
                "claude-opus-4-7")

    def test_per_tier_env_does_not_leak_to_other_tier(self):
        with patch.dict(os.environ, {
            "DIRECTJOB_MODEL_ANTHROPIC_PREMIUM": "claude-opus-4-7",
        }, clear=False):
            # Cheap tier should still be the default haiku.
            self.assertEqual(
                select_model("anthropic", TASK_CHAT_ROUTING),
                "claude-haiku-4-5")

    def test_explicit_model_beats_env(self):
        with patch.dict(os.environ, {
            "DIRECTJOB_MODEL_ANTHROPIC_PREMIUM": "claude-opus-4-7",
        }, clear=False):
            self.assertEqual(
                select_model("anthropic", TASK_LETTER,
                              explicit_model="claude-haiku-4-5"),
                "claude-haiku-4-5")

    def test_legacy_single_model_env_used_when_no_default_match(self):
        """An unknown provider with the legacy env set falls back to it."""
        with patch.dict(os.environ, {
            "DIRECTJOB_MANAGED_AI_MODEL": "custom-tuned-model-v3",
        }, clear=False):
            self.assertEqual(
                select_model("totally_unknown_provider", TASK_LETTER),
                "custom-tuned-model-v3")

    def test_empty_when_nothing_configured(self):
        with patch.dict(os.environ,
                          {"DIRECTJOB_MANAGED_AI_MODEL": ""},
                          clear=False):
            os.environ.pop("DIRECTJOB_MANAGED_AI_MODEL", None)
            self.assertEqual(
                select_model("unknown_provider", TASK_LETTER), "")


class IntegrationTests(unittest.TestCase):
    """Spot-check that the router actually saves operator cost on
    realistic chat traffic — cheap tasks pick cheap models, premium
    tasks pick premium models. This is the whole point of R23.5."""

    def setUp(self):
        for k in list(os.environ):
            if k.startswith("DIRECTJOB_MODEL_"):
                os.environ.pop(k, None)

    def test_routing_a_typical_chat_uses_cheap_model(self):
        # User typing "find me a bartender" → chat routing.
        chat_model = select_model("anthropic", TASK_CHAT_ROUTING)
        letter_model = select_model("anthropic", TASK_LETTER)
        # Premium model must NOT be the same as cheap one (we'd lose
        # the whole cost-tier benefit).
        self.assertNotEqual(chat_model, letter_model)
        self.assertIn("haiku", chat_model.lower())
        self.assertIn("sonnet", letter_model.lower())


if __name__ == "__main__":
    unittest.main()
