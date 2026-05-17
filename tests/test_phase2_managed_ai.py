# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Managed AI scaffold (Phase 2 tracker item #26).

When a Pro+ user picks ``provider_id="managed"``, ``_dispatch_provider``
rebinds the config to the operator's upstream provider via four env
vars (DIRECTJOB_MANAGED_AI_PROVIDER / KEY / MODEL / BASE_URL) and then
calls the standard adapter for that upstream. Plan gating is upstream
of dispatch — handled by ``AppState.assert_ai_mode_allowed`` (#24/#25).

These tests cover the rebind logic + the configuration-error paths.
The actual upstream HTTP call is exercised by the existing analysis
suite; we don't re-test that here.
"""

from __future__ import annotations

import os
import unittest

from company_discovery.ai_providers import AIProviderConfig, PROVIDER_OPTIONS
from company_discovery.analysis import _dispatch_provider


class _EnvSandbox:
    """Restore env vars to their original values when the with-block
    exits. Simpler than monkey-patching for our use case."""

    def __init__(self, **overrides: str | None) -> None:
        self.overrides = overrides
        self.restore: dict[str, str | None] = {}

    def __enter__(self) -> "_EnvSandbox":
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
            DIRECTJOB_MANAGED_AI_PROVIDER="openai",
            DIRECTJOB_MANAGED_AI_KEY=None,
        ):
            result = _dispatch_provider("hi", self._config(), runtime_credential="")
        self.assertEqual(result.status, "configuration_error")
        self.assertIn("DIRECTJOB_MANAGED_AI_KEY", result.error)

    def test_invalid_upstream_returns_configuration_error(self) -> None:
        with _EnvSandbox(
            DIRECTJOB_MANAGED_AI_PROVIDER="bogus_vendor",
            DIRECTJOB_MANAGED_AI_KEY="sk-test",
        ):
            result = _dispatch_provider("hi", self._config(), runtime_credential="")
        self.assertEqual(result.status, "configuration_error")
        self.assertIn("DIRECTJOB_MANAGED_AI_PROVIDER", result.error)

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
                "completed", provider.provider_id, provider.invocation_mode,
                output="ok", prompt=prompt,
            )

        from company_discovery import analysis as analysis_module
        original = analysis_module._execute_openai_compatible
        analysis_module._execute_openai_compatible = fake_openai
        try:
            with _EnvSandbox(
                DIRECTJOB_MANAGED_AI_PROVIDER="openai",
                DIRECTJOB_MANAGED_AI_KEY="sk-operator-test-key",
                DIRECTJOB_MANAGED_AI_MODEL="gpt-4o-mini",
            ):
                result = _dispatch_provider("hi", self._config(), runtime_credential="")
            self.assertEqual(result.status, "completed")
            rebound = captured["provider"]
            self.assertEqual(rebound.provider_id, "openai")
            self.assertEqual(rebound.invocation_mode, "api")
            self.assertEqual(rebound.credential_reference, "DIRECTJOB_MANAGED_AI_KEY")
            self.assertEqual(rebound.model, "gpt-4o-mini")
            # No runtime credential — the adapter resolves the env var.
            self.assertEqual(captured["credential"], "")
        finally:
            analysis_module._execute_openai_compatible = original


if __name__ == "__main__":
    unittest.main()
