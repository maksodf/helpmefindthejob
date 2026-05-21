# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #77 sub-piece (c): _dispatch_provider_streaming contract tests.

Asserts the streaming dispatch yields tokens in arrival order and a
final ``("final", AnalysisExecutionResult)`` event for each provider
class:

- Ollama (local_http NDJSON)
- OpenAI-compatible (api SSE: openai / deepseek / openrouter / custom)
- Google Gemini (api SSE-shaped)
- CLI providers (single-shot wrapped as one-event "final")
- Manual / unsupported (single "final" event with handoff or error)

All tests run offline via a urlopen mock so CI works without network.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import _dispatch_provider_streaming


def _provider(
    provider_id: str,
    invocation_mode: str = "api",
    model: str = "test-model",
    base_url: str = "",
    credential_reference: str = "",
) -> AIProviderConfig:
    return AIProviderConfig(
        provider_id=provider_id,
        invocation_mode=invocation_mode,
        model=model,
        credential_reference=credential_reference,
        base_url=base_url,
        command="",
        notes="streaming-test",
    )


class _FakeResponse:
    """Minimal urlopen-context-manager + iterable-over-lines stub."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def __iter__(self):
        return iter(self._lines)

    def read(self) -> bytes:
        return b"".join(self._lines)


@contextmanager
def _patch_urlopen_with(lines: list[bytes]):
    with patch("company_discovery.analysis.urlopen") as mock:
        mock.return_value = _FakeResponse(lines)
        yield mock


class OllamaStreamingTests(unittest.TestCase):
    def test_ndjson_chunks_yield_tokens_in_order(self) -> None:
        lines = [
            b'{"response": "Hello", "done": false}\n',
            b'{"response": " world", "done": false}\n',
            b'{"response": "!", "done": true}\n',
        ]
        provider = _provider("ollama", invocation_mode="local_http", base_url="http://127.0.0.1:11434")
        with _patch_urlopen_with(lines):
            events = list(
                _dispatch_provider_streaming(
                    "Say hi", provider, runtime_credential="", purpose="test"
                )
            )
        token_chunks = [e[1] for e in events if e[0] == "token"]
        finals = [e[1] for e in events if e[0] == "final"]
        self.assertEqual(token_chunks, ["Hello", " world", "!"])
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0].status, "completed")
        self.assertEqual(finals[0].output, "Hello world!")

    def test_remote_base_url_is_rejected(self) -> None:
        provider = _provider(
            "ollama", invocation_mode="local_http", base_url="https://remote.example.invalid"
        )
        events = list(
            _dispatch_provider_streaming("x", provider, runtime_credential="", purpose="t")
        )
        finals = [e for e in events if e[0] == "final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0][1].status, "configuration_error")
        self.assertIn("local", finals[0][1].error)

    def test_empty_stream_returns_provider_error(self) -> None:
        provider = _provider("ollama", invocation_mode="local_http", base_url="http://127.0.0.1:11434")
        with _patch_urlopen_with([b'{"done": true}\n']):
            events = list(
                _dispatch_provider_streaming("x", provider, runtime_credential="", purpose="t")
            )
        finals = [e for e in events if e[0] == "final"]
        self.assertEqual(finals[0][1].status, "provider_error")


class OpenAICompatibleStreamingTests(unittest.TestCase):
    def test_sse_chunks_yield_tokens_in_order(self) -> None:
        lines = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"!"}}]}\n',
            b"data: [DONE]\n",
        ]
        provider = _provider("openai", invocation_mode="api", credential_reference="OPENAI_API_KEY")
        with patch("company_discovery.analysis.urlopen") as mock_url, patch(
            "company_discovery.analysis._resolve_api_key",
            return_value=("sk-test", "env"),
        ):
            mock_url.return_value = _FakeResponse(lines)
            events = list(
                _dispatch_provider_streaming(
                    "Say hi", provider, runtime_credential="", purpose="test"
                )
            )
        token_chunks = [e[1] for e in events if e[0] == "token"]
        finals = [e[1] for e in events if e[0] == "final"]
        self.assertEqual(token_chunks, ["Hello", " world", "!"])
        self.assertEqual(finals[0].status, "completed")
        self.assertEqual(finals[0].output, "Hello world!")

    def test_missing_api_key_returns_configuration_error(self) -> None:
        provider = _provider("openai", invocation_mode="api", credential_reference="UNSET_KEY")
        with patch(
            "company_discovery.analysis._resolve_api_key",
            return_value=("", "env"),
        ):
            events = list(
                _dispatch_provider_streaming(
                    "x", provider, runtime_credential="", purpose="t"
                )
            )
        finals = [e for e in events if e[0] == "final"]
        self.assertEqual(finals[0][1].status, "configuration_error")
        self.assertIn("API key", finals[0][1].error)

    def test_malformed_sse_lines_skipped_silently(self) -> None:
        lines = [
            b"event: progress\n",  # not a "data:" line — skipped
            b"data: not-valid-json\n",  # JSON parse error — skipped
            b'data: {"choices":[{"delta":{"content":"OK"}}]}\n',
            b"data: [DONE]\n",
        ]
        provider = _provider("openai", invocation_mode="api", credential_reference="OPENAI_API_KEY")
        with patch("company_discovery.analysis.urlopen") as mock_url, patch(
            "company_discovery.analysis._resolve_api_key",
            return_value=("sk-test", "env"),
        ):
            mock_url.return_value = _FakeResponse(lines)
            events = list(
                _dispatch_provider_streaming("x", provider, runtime_credential="", purpose="t")
            )
        token_chunks = [e[1] for e in events if e[0] == "token"]
        self.assertEqual(token_chunks, ["OK"])


class GoogleGeminiStreamingTests(unittest.TestCase):
    def test_sse_chunks_yield_tokens_in_order(self) -> None:
        # Non-ASCII tokens like "Aïcha" must survive the streaming
        # pipeline; encode the lines via .encode("utf-8") rather than
        # b"..." bytes literals (Python disallows non-ASCII bytes literals).
        lines = [
            'data: {"candidates":[{"content":{"parts":[{"text":"Bonjour"}]}}]}\n'.encode("utf-8"),
            'data: {"candidates":[{"content":{"parts":[{"text":" Aïcha"}]}}]}\n'.encode("utf-8"),
        ]
        provider = _provider(
            "google_gemini", invocation_mode="api", credential_reference="GEMINI_API_KEY"
        )
        with patch("company_discovery.analysis.urlopen") as mock_url, patch(
            "company_discovery.analysis._resolve_api_key",
            return_value=("AIza-test", "env"),
        ):
            mock_url.return_value = _FakeResponse(lines)
            events = list(
                _dispatch_provider_streaming(
                    "Say hi in French", provider, runtime_credential="", purpose="test"
                )
            )
        token_chunks = [e[1] for e in events if e[0] == "token"]
        finals = [e[1] for e in events if e[0] == "final"]
        self.assertEqual(token_chunks, ["Bonjour", " Aïcha"])
        self.assertEqual(finals[0].status, "completed")


class CliProviderStreamingTests(unittest.TestCase):
    def test_cli_provider_wraps_single_shot_as_final_event(self) -> None:
        """CLI providers don't natively stream; we wrap the single-shot
        result as one ("final", ...) event."""
        from company_discovery.analysis import AnalysisExecutionResult

        provider = _provider("claude_code", invocation_mode="cli", model="")
        canned = AnalysisExecutionResult(
            status="completed",
            provider_id="claude_code",
            invocation_mode="cli",
            output="Hello from Claude Code",
            prompt="x",
        )
        with patch(
            "company_discovery.analysis._execute_cli", return_value=canned
        ):
            events = list(
                _dispatch_provider_streaming(
                    "x", provider, runtime_credential="", purpose="t"
                )
            )
        # No token events; one final event carrying the canned result.
        token_chunks = [e for e in events if e[0] == "token"]
        finals = [e for e in events if e[0] == "final"]
        self.assertEqual(token_chunks, [])
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0][1].output, "Hello from Claude Code")


class ManualAndUnsupportedTests(unittest.TestCase):
    def test_manual_yields_handoff_required_final(self) -> None:
        provider = _provider("manual", invocation_mode="manual")
        events = list(
            _dispatch_provider_streaming(
                "x", provider, runtime_credential="", purpose="t"
            )
        )
        finals = [e for e in events if e[0] == "final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0][1].status, "handoff_required")

    def test_unsupported_provider_yields_unsupported_final(self) -> None:
        provider = _provider("totally-bogus", invocation_mode="api")
        events = list(
            _dispatch_provider_streaming(
                "x", provider, runtime_credential="", purpose="t"
            )
        )
        finals = [e for e in events if e[0] == "final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0][1].status, "unsupported")


class AuditEmissionTests(unittest.TestCase):
    """The streaming dispatch must still emit one ``ai_invocation``
    audit-log event per call (parity with the single-shot dispatch).
    Verified by patching :func:`_emit_dispatch_audit` and counting
    calls."""

    def test_audit_fires_exactly_once_on_success(self) -> None:
        lines = [b'{"response": "x", "done": true}\n']
        provider = _provider(
            "ollama", invocation_mode="local_http", base_url="http://127.0.0.1:11434"
        )
        with _patch_urlopen_with(lines), patch(
            "company_discovery.analysis._emit_dispatch_audit"
        ) as audit:
            list(
                _dispatch_provider_streaming(
                    "x", provider, runtime_credential="", purpose="t"
                )
            )
        self.assertEqual(audit.call_count, 1)
        call_kwargs = audit.call_args.kwargs
        self.assertEqual(call_kwargs["purpose"], "t")
        # Final result is passed through so the audit log captures
        # response_hash + outcome.
        self.assertIsNotNone(call_kwargs["result"])
        self.assertEqual(call_kwargs["result"].status, "completed")


if __name__ == "__main__":
    unittest.main()
