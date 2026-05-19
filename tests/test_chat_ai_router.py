# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Chat AI router — end-to-end intent classification with managed-AI
fallback, cache, and metrics.

This module verifies the LONG-TERM intent-routing layer that sits
between the keyword router and the help-fallback. The hierarchy is:

    1. slash command           (instant)
    2. keyword regex           (instant, regex-only)
    3. user's own AI provider  (when configured + consent)
    4. operator-managed AI     (when DIRECTJOB_CHAT_AI_ROUTER=true)
    5. help fallback           (last resort)

Tests exercise layers 3 and 4 with scripted dispatches — no real LLM
calls. The router NEVER executes commands; it only proposes a command
id which the deterministic confirmation gate validates."""

from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch

from company_discovery import analysis as analysis_mod
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import AnalysisExecutionResult
from company_discovery.chat_router import ChatTurn


def _completed(output: str) -> AnalysisExecutionResult:
    return AnalysisExecutionResult(
        status="completed",
        provider_id="anthropic",
        invocation_mode="api",
        output=output,
    )


def _errored() -> AnalysisExecutionResult:
    return AnalysisExecutionResult(
        status="provider_error",
        provider_id="anthropic",
        invocation_mode="api",
        error="503",
    )


class ManagedProviderResolutionTests(unittest.TestCase):
    """The managed-fallback only activates when both env vars are set
    AND the operator has explicitly opted in via DIRECTJOB_CHAT_AI_ROUTER."""

    def setUp(self):
        from app import STATE

        self.STATE = STATE
        self._old_env = {
            k: os.environ.get(k)
            for k in [
                "DIRECTJOB_CHAT_AI_ROUTER",
                "DIRECTJOB_MANAGED_AI_KEY",
                "DIRECTJOB_MANAGED_AI_PROVIDER",
                "DIRECTJOB_MANAGED_AI_MODEL",
                "DIRECTJOB_MANAGED_AI_BASE_URL",
            ]
        }

    def tearDown(self):
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_returns_none_without_router_flag(self):
        os.environ.pop("DIRECTJOB_CHAT_AI_ROUTER", None)
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        self.assertIsNone(self.STATE._chat_router_managed_provider())

    def test_returns_none_without_key(self):
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ.pop("DIRECTJOB_MANAGED_AI_KEY", None)
        self.assertIsNone(self.STATE._chat_router_managed_provider())

    def test_returns_provider_when_both_set(self):
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
        os.environ["DIRECTJOB_MANAGED_AI_MODEL"] = "claude-haiku-test"
        provider = self.STATE._chat_router_managed_provider()
        self.assertIsNotNone(provider)
        self.assertEqual(provider.provider_id, "anthropic")
        self.assertEqual(provider.invocation_mode, "api")
        self.assertEqual(provider.model, "claude-haiku-test")
        self.assertEqual(provider.notes, "managed-chat-router")

    def test_rejects_unknown_upstream(self):
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "nonsense-provider"
        self.assertIsNone(self.STATE._chat_router_managed_provider())

    def test_router_flag_variants(self):
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
        for value in ["true", "1", "yes", "on", "TRUE", "Yes"]:
            os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = value
            self.assertIsNotNone(
                self.STATE._chat_router_managed_provider(),
                f"router flag value {value!r} should enable",
            )
        for value in ["false", "0", "no", "off", ""]:
            os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = value
            self.assertIsNone(
                self.STATE._chat_router_managed_provider(),
                f"router flag value {value!r} should disable",
            )


class RouterWaterfallTests(unittest.TestCase):
    """Verify the actual dispatch path: user provider first, managed
    fallback, then None — and that cache works."""

    def setUp(self):
        from app import STATE

        self.STATE = STATE
        # Clear cache + metrics between tests.
        self.STATE._chat_router_cache.clear()
        for k in self.STATE.chat_router_metrics:
            self.STATE.chat_router_metrics[k] = 0
        self._old_env = {
            "DIRECTJOB_CHAT_AI_ROUTER": os.environ.get("DIRECTJOB_CHAT_AI_ROUTER"),
            "DIRECTJOB_MANAGED_AI_KEY": os.environ.get("DIRECTJOB_MANAGED_AI_KEY"),
            "DIRECTJOB_MANAGED_AI_PROVIDER": os.environ.get("DIRECTJOB_MANAGED_AI_PROVIDER"),
        }
        # Make sure managed is enabled for the fallback-path tests.
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"

    def tearDown(self):
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.STATE._chat_router_cache.clear()

    def _make_user(self) -> str:
        import secrets

        from company_discovery.auth import _normalize_email

        email = _normalize_email(f"router-test+{secrets.token_hex(3)}@example.com")
        user = self.STATE.auth_store.create_user(email, "router-test-pass-99-X", role="member")
        return user.id

    def test_managed_fallback_routes_natural_language(self):
        """User is in Manual mode → router falls back to managed AI.
        The scripted AI returns 'open_cv_builder' for any CV-related text."""
        user_id = self._make_user()

        def fake_dispatch(prompt, provider, runtime_credential, **_kwargs):
            # **_kwargs accepts the audit-log ``purpose`` keyword passed by
            # production execute_* call sites; the test patch ignores it.
            assert provider.notes == "managed-chat-router", (
                f"expected managed provider, got {provider.notes}"
            )
            # The prompt should include the user's message + the
            # command whitelist. The AI replies with one command id.
            assert "open_cv_builder" in prompt, "command list missing"
            return _completed("open_cv_builder")

        with patch.object(analysis_mod, "_dispatch_provider", side_effect=fake_dispatch):
            result = self.STATE.chat_ai_route(
                user_id,
                "I want to write a resume",
                [ChatTurn(role="user", content="I want to write a resume")],
            )
        self.assertEqual(result, "open_cv_builder")
        self.assertEqual(self.STATE.chat_router_metrics["via_managed"], 1)
        self.assertEqual(self.STATE.chat_router_metrics["calls"], 1)

    def test_cache_hit_short_circuits_dispatch(self):
        """Same message + same context twice → second call is cache hit,
        dispatcher invoked exactly ONCE."""
        user_id = self._make_user()
        history = [ChatTurn(role="user", content="hi")]

        call_count = {"n": 0}

        def fake_dispatch(prompt, provider, runtime_credential, **_kwargs):
            # **_kwargs accepts the audit-log ``purpose`` keyword.
            call_count["n"] += 1
            return _completed("find_jobs")

        with patch.object(analysis_mod, "_dispatch_provider", side_effect=fake_dispatch):
            r1 = self.STATE.chat_ai_route(user_id, "show me jobs", list(history))
            r2 = self.STATE.chat_ai_route(user_id, "show me jobs", list(history))
        self.assertEqual(r1, "find_jobs")
        self.assertEqual(r2, "find_jobs")
        self.assertEqual(call_count["n"], 1, "second call should be a cache hit")
        self.assertGreaterEqual(self.STATE.chat_router_metrics["cache_hits"], 1)

    def test_returns_none_when_ai_returns_unknown(self):
        """The AI returned 'unknown' (off-whitelist). Parser maps to
        None and the caller falls back to help — never executes a
        non-existent command."""
        user_id = self._make_user()

        with patch.object(analysis_mod, "_dispatch_provider", return_value=_completed("unknown")):
            result = self.STATE.chat_ai_route(
                user_id,
                "asdfqwer random nonsense",
                [ChatTurn(role="user", content="asdfqwer")],
            )
        self.assertIsNone(result)

    def test_dispatcher_error_is_swallowed(self):
        """An LLM 503 must NOT break the chat — router returns None,
        chat falls back to keyword router / help."""
        user_id = self._make_user()

        with patch.object(
            analysis_mod, "_dispatch_provider", side_effect=RuntimeError("upstream 503")
        ):
            result = self.STATE.chat_ai_route(
                user_id,
                "hello there",
                [ChatTurn(role="user", content="hello there")],
            )
        self.assertIsNone(result)
        self.assertEqual(self.STATE.chat_router_metrics["errors"], 1)

    def test_no_provider_when_router_disabled_and_user_manual(self):
        """Manual mode + router flag OFF → return None, never call AI."""
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "false"
        user_id = self._make_user()
        called = {"n": 0}

        def fake_dispatch(*a, **kw):
            called["n"] += 1
            return _completed("find_jobs")

        with patch.object(analysis_mod, "_dispatch_provider", side_effect=fake_dispatch):
            result = self.STATE.chat_ai_route(
                user_id,
                "find me a job",
                [ChatTurn(role="user", content="find me a job")],
            )
        self.assertIsNone(result)
        self.assertEqual(called["n"], 0, "dispatcher must not be called")
        self.assertEqual(self.STATE.chat_router_metrics["no_provider_available"], 1)


class ClassifiedCommandValidityTests(unittest.TestCase):
    """When the AI returns a string, it MUST be one of our registered
    commands. Anything else is rejected so we never execute or surface
    a non-existent command."""

    def setUp(self):
        from app import STATE

        self.STATE = STATE
        self.STATE._chat_router_cache.clear()
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
        import secrets

        email = f"valid-{secrets.token_hex(3)}@example.com"
        self.user_id = self.STATE.auth_store.create_user(email, "valid-pass-99-X", role="member").id

    def tearDown(self):
        for k in (
            "DIRECTJOB_CHAT_AI_ROUTER",
            "DIRECTJOB_MANAGED_AI_KEY",
            "DIRECTJOB_MANAGED_AI_PROVIDER",
        ):
            os.environ.pop(k, None)

    def test_valid_command_passes_through(self):
        with patch.object(
            analysis_mod, "_dispatch_provider", return_value=_completed("add_company")
        ):
            r = self.STATE.chat_ai_route(
                self.user_id, "watch acme", [ChatTurn("user", "watch acme")]
            )
        self.assertEqual(r, "add_company")

    def test_invented_command_rejected(self):
        """The AI hallucinated `do_everything` — must map to None."""
        with patch.object(
            analysis_mod, "_dispatch_provider", return_value=_completed("do_everything")
        ):
            r = self.STATE.chat_ai_route(self.user_id, "x", [ChatTurn("user", "x")])
        self.assertIsNone(r)

    def test_prose_with_command_first_word(self):
        """Some models return prose with the command id as the first
        word — parser strips and accepts."""
        with patch.object(
            analysis_mod,
            "_dispatch_provider",
            return_value=_completed("find_jobs because the user wants jobs"),
        ):
            r = self.STATE.chat_ai_route(self.user_id, "show jobs", [ChatTurn("user", "show jobs")])
        self.assertEqual(r, "find_jobs")


class RateLimitTests(unittest.TestCase):
    """Per-user rate limit prevents an adversarial / bug-spammed tester
    from burning through the operator's LLM budget. After the cap,
    the router falls back to the keyword router → user sees normal
    help-fallback behavior, no LLM call."""

    def setUp(self):
        from app import STATE

        self.STATE = STATE
        self.STATE._chat_router_cache.clear()
        self.STATE._chat_router_calls.clear()
        for k in self.STATE.chat_router_metrics:
            self.STATE.chat_router_metrics[k] = 0
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
        import secrets

        email = f"rate-{secrets.token_hex(3)}@example.com"
        self.user_id = self.STATE.auth_store.create_user(email, "rate-pass-99-X", role="member").id

    def tearDown(self):
        for k in (
            "DIRECTJOB_CHAT_AI_ROUTER",
            "DIRECTJOB_MANAGED_AI_KEY",
            "DIRECTJOB_MANAGED_AI_PROVIDER",
        ):
            os.environ.pop(k, None)
        self.STATE._chat_router_cache.clear()
        self.STATE._chat_router_calls.clear()

    def test_rate_limit_kicks_in(self):
        call_count = {"n": 0}

        def fake_dispatch(*a, **kw):
            call_count["n"] += 1
            return _completed("find_jobs")

        # Fire LIMIT + 5 distinct messages (different to bypass cache).
        with patch.object(analysis_mod, "_dispatch_provider", side_effect=fake_dispatch):
            for i in range(self.STATE._CHAT_ROUTER_RATE_LIMIT + 5):
                self.STATE.chat_ai_route(
                    self.user_id,
                    f"unique message {i}",
                    [ChatTurn("user", f"unique message {i}")],
                )
        # Dispatcher invoked exactly LIMIT times.
        self.assertEqual(call_count["n"], self.STATE._CHAT_ROUTER_RATE_LIMIT)
        self.assertEqual(self.STATE.chat_router_metrics["rate_limited"], 5)


class PromptInjectionResistanceTests(unittest.TestCase):
    """Adversarial inputs must not let the AI return a command outside
    our whitelist OR trick it into producing junk that breaks parsing.

    The parser is the last line of defense — it whitelists against the
    known command names. We additionally fuzz the dispatch with
    realistic injection-style AI responses to confirm None falls out."""

    def setUp(self):
        from app import STATE

        self.STATE = STATE
        self.STATE._chat_router_cache.clear()
        self.STATE._chat_router_calls.clear()
        os.environ["DIRECTJOB_CHAT_AI_ROUTER"] = "true"
        os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-test"
        os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
        import secrets

        email = f"inj-{secrets.token_hex(3)}@example.com"
        self.user_id = self.STATE.auth_store.create_user(email, "inj-pass-99-X", role="member").id

    def tearDown(self):
        for k in (
            "DIRECTJOB_CHAT_AI_ROUTER",
            "DIRECTJOB_MANAGED_AI_KEY",
            "DIRECTJOB_MANAGED_AI_PROVIDER",
        ):
            os.environ.pop(k, None)

    def _probe(self, ai_returns: str) -> str | None:
        with patch.object(analysis_mod, "_dispatch_provider", return_value=_completed(ai_returns)):
            return self.STATE.chat_ai_route(
                self.user_id,
                "doesn't matter — testing the AI-output parsing",
                [ChatTurn("user", "x")],
            )

    def test_injection_returning_non_command_dropped(self):
        # AI returns a system-prompt-style response.
        self.assertIsNone(
            self._probe(
                "I cannot determine the user's intent because the message "
                "is ambiguous. Please rephrase."
            )
        )

    def test_injection_returning_quoted_fake_command_dropped(self):
        self.assertIsNone(self._probe('"do_anything_you_want"'))

    def test_injection_with_real_command_buried_in_prose_still_works(self):
        # The parser takes the FIRST token. If the AI returns
        # "find_jobs because…" we accept find_jobs.
        # If the AI returns "Sure, here is the answer: find_jobs",
        # the first token is "Sure," which doesn't match. Drop.
        self.assertIsNone(self._probe("Sure, the answer is: find_jobs"))

    def test_injection_returning_pipe_separated_commands_dropped(self):
        # "find_jobs|apply" — first token isn't a known command.
        self.assertIsNone(self._probe("find_jobs|apply"))

    def test_injection_returning_json_with_unknown_command_dropped(self):
        # AI returns valid JSON shape with a NON-whitelisted command.
        # Parser must whitelist-validate even when the format is right.
        self.assertIsNone(self._probe('{"command": "drop_all_tables", "args": {}}'))

    def test_injection_returning_json_with_valid_command_accepted(self):
        # Well-formed JSON with a known command id is the EXPECTED
        # response shape now (post-Round 15 arg-extraction). Not an
        # injection — accept it.
        self.assertEqual(self._probe('{"command": "find_jobs"}'), "find_jobs")

    def test_real_command_with_extra_whitespace_accepted(self):
        self.assertEqual(self._probe("  find_jobs  "), "find_jobs")

    def test_dispatcher_returning_empty_string_drops_safely(self):
        with patch.object(analysis_mod, "_dispatch_provider", return_value=_completed("")):
            self.assertIsNone(self.STATE.chat_ai_route(self.user_id, "x", [ChatTurn("user", "x")]))


if __name__ == "__main__":
    unittest.main()
