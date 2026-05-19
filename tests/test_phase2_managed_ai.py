# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Managed AI dispatcher contract + minimal HTTP marshalling round-trip.

When a Pro+ user picks ``provider_id="managed"``, ``_dispatch_provider``
rebinds the config to the operator's upstream provider via four env
vars (HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER / KEY / MODEL / BASE_URL —
legacy DIRECTJOB_* still accepted via the env_compat shim) and then
calls the standard adapter for that upstream. Plan gating is upstream
of dispatch — handled by ``AppState.assert_ai_mode_allowed``.

**Test scope** (PART A.4 of the 2026-05-19 deep-audit sweep — explicit
decision): this module is a **contract-shape + minimal-HTTP-marshalling**
test surface, not a live-provider end-to-end suite.

What we cover:

1. ``ManagedAiDispatchTests`` — dispatcher rebind + configuration-error
   paths. The adapters themselves are stubbed via attribute monkey-
   patching so the dispatcher's branching can be exercised without
   sending real HTTP. This proves the dispatch contract.
2. ``OpenAICompatibleAdapterTests`` — patches ``urllib.request.urlopen``
   to return canned bytes for the OpenAI-compatible adapter (the most-
   used path; covers OpenAI / DeepSeek / OpenRouter / managed-mode).
   Exercises the request payload shape, the Authorization header, the
   non-HTTPS base-URL guard, and the HTTPError → provider_error
   coercion.

What we **do not** cover here:

- Live HTTPS round-trip against a real provider (OpenAI / Anthropic /
  Gemini / DeepSeek / OpenRouter / Claude Code). Per the
  pre-submission honesty doctrine + Phase 2 backlog item #15, live-key
  verification of cloud providers is **Phase 2 work** pending real API
  budgets. Maintainers running an end-to-end smoke against their own
  API key can use ``tests/e2e/journey_ai_probe.py``.
- Gemini-specific payload shape — same justification.
- Ollama adapter — exercised live by the bias-testing methodology
  (``test_bias_methodology.py``); not re-tested here.

Honest tag for this surface: **contract-shape + happy-path / error-path
HTTP marshalling for the openai-compatible adapter**.
"""

from __future__ import annotations

import json
import os
import unittest

# Set the audit-log salt BEFORE the analysis import below triggers
# the emitter's lazy init in `_emit_dispatch_audit`. PART N iteration
# of the 2026-05-19 deep-audit sweep.
os.environ.setdefault(
    "HELPMEFINDTHEJOB_AUDIT_SALT",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
)

from company_discovery.ai_providers import PROVIDER_OPTIONS, AIProviderConfig
from company_discovery.analysis import _dispatch_provider


class _EnvSandbox:
    """Restore env vars to their original values when the with-block
    exits. Simpler than monkey-patching for our use case."""

    def __init__(self, **overrides: str | None) -> None:
        self.overrides = overrides
        self.restore: dict[str, str | None] = {}

    def __enter__(self) -> _EnvSandbox:
        for key, value in self.overrides.items():
            self.restore[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return self

    def __exit__(self, *_args: object) -> None:
        for key, value in self.restore.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class ManagedAiPickerOptionTests(unittest.TestCase):
    def test_managed_option_is_listed(self) -> None:
        managed = next((o for o in PROVIDER_OPTIONS if o.id == "managed"), None)
        self.assertIsNotNone(managed)
        self.assertEqual(managed.invocation_modes, ["api"])
        self.assertIn("Plan-gated", managed.notes)


class ManagedAiDispatchTests(unittest.TestCase):
    def _config(self) -> AIProviderConfig:
        return AIProviderConfig(provider_id="managed", invocation_mode="api")

    def test_missing_key_returns_configuration_error(self) -> None:
        with _EnvSandbox(
            HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER="openai",
            HELPMEFINDTHEJOB_MANAGED_AI_KEY=None,
        ):
            result = _dispatch_provider("hi", self._config(), runtime_credential="")
        self.assertEqual(result.status, "configuration_error")
        self.assertIn("HELPMEFINDTHEJOB_MANAGED_AI_KEY", result.error)

    def test_invalid_upstream_returns_configuration_error(self) -> None:
        with _EnvSandbox(
            HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER="bogus_vendor",
            HELPMEFINDTHEJOB_MANAGED_AI_KEY="sk-test",
        ):
            result = _dispatch_provider("hi", self._config(), runtime_credential="")
        self.assertEqual(result.status, "configuration_error")
        self.assertIn("HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER", result.error)

    def test_rebind_picks_correct_upstream(self) -> None:
        # With a valid upstream + key the dispatcher will try the
        # OpenAI-compatible adapter, which performs an HTTP call. We
        # don't want to fire a real request, so we patch the adapter
        # to capture the rebound provider object.
        captured: dict[str, AIProviderConfig] = {}

        def fake_openai(prompt: str, provider: AIProviderConfig, runtime_credential: str):
            captured["provider"] = provider
            captured["credential"] = runtime_credential
            from company_discovery.analysis import AnalysisExecutionResult

            return AnalysisExecutionResult(
                "completed",
                provider.provider_id,
                provider.invocation_mode,
                output="ok",
                prompt=prompt,
            )

        from company_discovery import analysis as analysis_module

        original = analysis_module._execute_openai_compatible
        analysis_module._execute_openai_compatible = fake_openai
        try:
            with _EnvSandbox(
                HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER="openai",
                HELPMEFINDTHEJOB_MANAGED_AI_KEY="sk-operator-test-key",
                HELPMEFINDTHEJOB_MANAGED_AI_MODEL="gpt-4o-mini",
            ):
                result = _dispatch_provider("hi", self._config(), runtime_credential="")
            self.assertEqual(result.status, "completed")
            rebound = captured["provider"]
            self.assertEqual(rebound.provider_id, "openai")
            self.assertEqual(rebound.invocation_mode, "api")
            self.assertEqual(rebound.credential_reference, "HELPMEFINDTHEJOB_MANAGED_AI_KEY")
            self.assertEqual(rebound.model, "gpt-4o-mini")
            # No runtime credential — the adapter resolves the env var.
            self.assertEqual(captured["credential"], "")
        finally:
            analysis_module._execute_openai_compatible = original


class OpenAICompatibleAdapterTests(unittest.TestCase):
    """Round-trip HTTP marshalling for ``_execute_openai_compatible``.

    Exercises the request payload shape + Authorization header + 200
    happy path + non-HTTPS guard + HTTPError → provider_error coercion.
    Uses a ``unittest.mock.patch`` of ``urllib.request.urlopen`` so no
    real network IO happens. Covers PART A.4 of the 2026-05-19 deep
    audit's BYO-AI-test-depth decision.
    """

    def setUp(self) -> None:
        from company_discovery.ai_providers import AIProviderConfig

        self.provider = AIProviderConfig(
            provider_id="openai",
            invocation_mode="direct",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            credential_reference="HELPMEFINDTHEJOB_MANAGED_AI_KEY",
        )

    def _patched_urlopen(self, status: int, body_bytes: bytes):
        """Build a context manager that fakes ``urlopen`` to return a
        response with the given status + body. ``urlopen`` is used as a
        context manager (``with urlopen(...) as response:``), so the
        returned object must implement ``__enter__`` / ``__exit__`` and
        a ``read()`` method."""
        from unittest.mock import MagicMock, patch

        class _FakeResponse:
            def __init__(self) -> None:
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return body_bytes

        captured: dict[str, object] = {}

        def _fake(request, timeout=None):  # mirrors urlopen(request, timeout=...)
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data
            captured["method"] = request.get_method()
            captured["timeout"] = timeout
            return _FakeResponse()

        return patch("company_discovery.analysis.urlopen", side_effect=_fake), captured

    def test_happy_path_returns_completed_with_choice_content(self) -> None:
        from company_discovery.analysis import _execute_openai_compatible

        body = json.dumps(
            {"choices": [{"message": {"content": "fit=80 strong analyst match"}}]}
        ).encode("utf-8")
        ctx, captured = self._patched_urlopen(200, body)
        with ctx:
            result = _execute_openai_compatible(
                "prompt-text", self.provider, runtime_credential="key-from-runtime"
            )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "fit=80 strong analyst match")
        # Request shape: chat/completions endpoint, JSON body, Bearer auth.
        self.assertEqual(captured["url"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(captured["method"], "POST")
        payload = json.loads(captured["body"].decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["messages"], [{"role": "user", "content": "prompt-text"}])
        headers_lower = {k.lower(): v for k, v in captured["headers"].items()}
        self.assertEqual(headers_lower["authorization"], "Bearer key-from-runtime")
        self.assertEqual(headers_lower["content-type"], "application/json")
        self.assertEqual(captured["timeout"], 45)

    def test_non_https_base_url_returns_configuration_error(self) -> None:
        from company_discovery.ai_providers import AIProviderConfig
        from company_discovery.analysis import _execute_openai_compatible

        insecure = AIProviderConfig(
            provider_id="openai",
            invocation_mode="direct",
            base_url="http://insecure.example.com/v1",
            model="gpt-4o-mini",
            credential_reference="HELPMEFINDTHEJOB_MANAGED_AI_KEY",
        )
        # Should not perform any HTTP — patch urlopen as a guard.
        ctx, _ = self._patched_urlopen(200, b"never")
        with ctx:
            result = _execute_openai_compatible("prompt", insecure, runtime_credential="anything")
        self.assertEqual(result.status, "configuration_error")
        self.assertIn("HTTPS", result.error or "")

    def test_http_error_returns_provider_error(self) -> None:
        from unittest.mock import patch
        from urllib.error import HTTPError

        from company_discovery.analysis import _execute_openai_compatible

        def _raise(*_a, **_kw):
            raise HTTPError(
                url="https://api.openai.com/v1/chat/completions",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=None,
            )

        with patch("company_discovery.analysis.urlopen", side_effect=_raise):
            result = _execute_openai_compatible("prompt", self.provider, runtime_credential="key")
        self.assertEqual(result.status, "provider_error")
        self.assertIn("HTTP 429", result.error or "")

    def test_no_credential_returns_configuration_error(self) -> None:
        # No runtime credential AND no env-var fallback for the
        # credential_reference → adapter must return configuration_error
        # before any HTTP. Patch urlopen as a guard.
        from unittest.mock import patch

        from company_discovery.analysis import _execute_openai_compatible

        with patch("company_discovery.analysis.urlopen") as urlopen_mock:
            result = _execute_openai_compatible("prompt", self.provider, runtime_credential="")
        urlopen_mock.assert_not_called()
        self.assertEqual(result.status, "configuration_error")


if __name__ == "__main__":
    unittest.main()
