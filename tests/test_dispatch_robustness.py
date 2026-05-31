# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for AI-dispatch robustness bugs found in the bug hunt:

1. Streaming dispatch recorded cost + audit + receipt in a `finally` that read
   `final_result`, but `final_result` was assigned AFTER the yield that
   production consumers break on — so every streamed call audited result=None
   (outcome "error") and under-counted cost. Now the result is captured before
   the yield, and GeneratorExit (normal break cleanup) is not mis-recorded.

2. The non-streaming OpenAI/Gemini adapters parsed the response shape OUTSIDE
   the try and assumed list elements were dicts, and their `except` omitted
   UnicodeDecodeError — so a 200 with an off-spec body (gateways/proxies) or a
   non-UTF-8 body raised, 500ing the request / aborting an auto-fit batch.
   Adapters must classify and return `provider_error`, never raise.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from company_discovery import analysis
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import (
    AnalysisExecutionResult,
    _dispatch_provider_streaming,
    _execute_google_gemini,
    _execute_openai_compatible,
)


def _provider(
    provider_id: str, *, base_url: str = "", invocation_mode: str = "api"
) -> AIProviderConfig:
    return AIProviderConfig(
        provider_id=provider_id,
        invocation_mode=invocation_mode,
        model="m",
        credential_reference="",
        base_url=base_url,
        command="",
        notes="t",
    )


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._b = body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *exc) -> None:
        return None

    def read(self) -> bytes:
        return self._b


class StreamingFinallyTests(unittest.TestCase):
    def test_finally_audits_completed_result_when_consumer_breaks_on_final(self) -> None:
        prov = _provider("openai")
        final = AnalysisExecutionResult("completed", "openai", "api", prompt="p", output="hello")

        def fake_impl(prompt, provider, cred):  # noqa: ANN001
            yield ("token", "hello")
            yield ("final", final)

        captured: dict = {}

        def fake_audit(**kw):  # noqa: ANN003
            captured["result"] = kw.get("result")
            captured["error_class"] = kw.get("error_class")

        with (
            patch.object(analysis, "_dispatch_provider_streaming_impl", fake_impl),
            patch.object(analysis, "_emit_dispatch_audit", fake_audit),
        ):
            gen = _dispatch_provider_streaming("p", prov, runtime_credential="", purpose="t")
            for event in gen:
                if event[0] == "final":
                    break  # production consumers break the instant they get "final"
            gen.close()  # what CPython does at GC; runs the finally

        self.assertIsNotNone(captured.get("result"), "audit ran with result=None (the bug)")
        self.assertEqual(captured["result"].status, "completed")
        self.assertIsNone(
            captured.get("error_class"), "GeneratorExit must not be recorded as an error"
        )


class AdapterRobustnessTests(unittest.TestCase):
    def _openai(self, body: bytes) -> AnalysisExecutionResult:
        with patch("company_discovery.analysis.urlopen", return_value=_FakeResp(body)):
            return _execute_openai_compatible(
                "p", _provider("openai", base_url="https://api.test"), runtime_credential="sk-test"
            )

    def test_openai_unexpected_shape_is_provider_error(self) -> None:
        r = self._openai(json.dumps({"choices": ["a string, not a dict"]}).encode("utf-8"))
        self.assertEqual(r.status, "provider_error")

    def test_openai_non_utf8_body_is_provider_error(self) -> None:
        r = self._openai(b"\xff\xfe\x00 not utf-8")
        self.assertEqual(r.status, "provider_error")

    def test_gemini_unexpected_shape_is_provider_error(self) -> None:
        with patch(
            "company_discovery.analysis.urlopen",
            return_value=_FakeResp(json.dumps({"candidates": ["str"]}).encode("utf-8")),
        ):
            r = _execute_google_gemini(
                "p",
                _provider("google_gemini", base_url="https://g.test"),
                runtime_credential="sk-test",
            )
        self.assertEqual(r.status, "provider_error")


if __name__ == "__main__":
    unittest.main()
