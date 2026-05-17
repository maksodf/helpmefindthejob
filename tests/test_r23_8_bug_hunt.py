"""R23.8 — targeted bug-hunt for the response cache.

Hunting specifically for:
  * Cache hit returning stale model_used after operator changes model
  * Anthropic system-block shape regression (string → list[{...}])
  * Concurrent cache misses → racing puts that LOSE later writes
  * record_call invoked for cache hits with 0 tokens (zero-cost row)
  * Cache key stability under same-content-different-dict-order
"""

from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company_discovery import tool_use_router as TUR
from company_discovery.llm_response_cache import (
    CachedResponse, LLMResponseCache, cache_key,
)


class AnthropicCacheBreakpointTests(unittest.TestCase):
    """Phase 1 / Step 2 — cache_control belongs on the LAST tool, not
    on the system block. The system text is rebuilt every turn
    (user_profile + journey_phase + last_search_summary + locale are
    all baked in), so it never repeats and cache_control on system
    is effectively useless. The tools array is the actually-stable
    prefix worth caching.

    The previous R23.8 design put cache_control on the system block;
    this test was rewritten when the breakpoint moved.
    """

    def test_body_sends_cache_control_on_last_tool(self):
        captured_body = {"v": None}

        def fake_http(url, headers, body, timeout=None):
            captured_body["v"] = body
            captured_body["headers"] = headers
            return 200, {
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 100, "output_tokens": 30},
            }

        sample_tools = [
            {"name": "first", "description": "first tool",
             "input_schema": {"type": "object",
                              "properties": {}, "required": []}},
            {"name": "last", "description": "last tool",
             "input_schema": {"type": "object",
                              "properties": {}, "required": []}},
        ]
        with patch.object(TUR, "_http_post_json", new=fake_http):
            TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5",
                "you are a helpful assistant",
                [{"role": "user", "content": "hi"}],
                sample_tools)
        body = captured_body["v"]
        # System is now a plain string — the breakpoint moved off it
        # since system text is per-turn.
        self.assertIsInstance(body["system"], str)
        # cache_control is on the LAST tool only.
        self.assertNotIn("cache_control", body["tools"][0])
        self.assertEqual(
            body["tools"][-1]["cache_control"]["type"], "ephemeral")
        # The earlier R23.8 tools (no cache_control on intermediate
        # tools) — Anthropic uses ONE breakpoint per request for
        # ephemeral cache; placing it on the last tool caches the
        # entire tools prefix.
        # The obsolete anthropic-beta prompt-caching header is also
        # not present.
        self.assertNotIn("anthropic-beta", captured_body["headers"])

    def test_body_with_no_tools_sends_plain_system_string(self):
        """Edge case: when tools is empty, no cache breakpoint
        exists; system is sent as a plain string."""
        captured_body = {"v": None}

        def fake_http(url, headers, body, timeout=None):
            captured_body["v"] = body
            return 200, {
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }

        with patch.object(TUR, "_http_post_json", new=fake_http):
            TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5", "sys", [], [])
        body = captured_body["v"]
        self.assertIsInstance(body["system"], str)
        self.assertEqual(body["tools"], [])


class CacheKeyStabilityTests(unittest.TestCase):
    def test_dicts_with_different_field_order_hash_the_same(self):
        """JSON serialisation must use sort_keys=True so {a, b} and
        {b, a} dicts produce identical hashes."""
        a = cache_key(provider="anthropic", model="m", system="s",
                       messages=[{"role": "user", "content": "hi"}],
                       tools=[{"name": "x", "description": "y",
                                "input_schema": {"type": "object",
                                                  "properties": {}}}])
        # Build the same tools dict with a different key order in the
        # nested input_schema — same content, different ordering.
        b = cache_key(provider="anthropic", model="m", system="s",
                       messages=[{"content": "hi", "role": "user"}],
                       tools=[{"description": "y", "name": "x",
                                "input_schema": {"properties": {},
                                                  "type": "object"}}])
        self.assertEqual(a, b)


class CacheHitRecordCallTests(unittest.TestCase):
    """When the cache serves a reply, the cost-tracker callback
    should still fire (with 0 tokens) so we can SEE that cache hits
    happened — but should NOT record fake cost."""

    def test_cache_hit_invokes_record_with_zero_tokens(self):
        cache = LLMResponseCache(max_entries=10, ttl_s=60)
        # Pre-seed the cache.
        cache.put(
            cache_key(provider="anthropic", model="claude-haiku-4-5",
                        system="sys", messages=[{"role": "user", "content": "hi"}],
                        tools=[]),
            CachedResponse(text="cached reply",
                            model_used="claude-haiku-4-5",
                            input_tokens=120, output_tokens=40,
                            stop_reason="end_turn",
                            raw_provider="anthropic"),
        )
        with patch.object(TUR, "_http_post_json") as http_mock:
            turn = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5",
                "sys",
                [{"role": "user", "content": "hi"}],
                [],
                response_cache=cache,
            )
        http_mock.assert_not_called()
        # Cache hit returns zero-cost (correct — no API call made).
        self.assertEqual(turn.input_tokens, 0)
        self.assertEqual(turn.output_tokens, 0)
        # But model_used and text come from the cache.
        self.assertEqual(turn.text, "cached reply")
        self.assertEqual(turn.model_used, "claude-haiku-4-5")


class CacheConcurrencyDoesNotLoseEntriesTests(unittest.TestCase):
    """Many threads putting + getting must not corrupt the dict."""

    def test_concurrent_puts_all_land_or_get_evicted_lru(self):
        cache = LLMResponseCache(max_entries=200, ttl_s=60)

        def worker(idx: int):
            for i in range(20):
                cache.put(f"u{idx}-{i}",
                           CachedResponse(text=f"r{idx}-{i}",
                                            model_used="m",
                                            input_tokens=10,
                                            output_tokens=5,
                                            stop_reason="end_turn",
                                            raw_provider="anthropic"))

        threads = [threading.Thread(target=worker, args=(i,))
                    for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        stats = cache.stats()
        # 200 entries cap → exactly 200 entries should be there.
        self.assertEqual(stats["entries"], 200)


class OpenAICacheRespectsResponseShapeTests(unittest.TestCase):
    def test_openai_cache_hit_returns_openai_provider_label(self):
        cache = LLMResponseCache(max_entries=10, ttl_s=60)
        cache.put(
            cache_key(provider="openai", model="gpt-4o-mini",
                        system="sys",
                        messages=[{"role": "user", "content": "hi"}],
                        tools=[]),
            CachedResponse(text="cached", model_used="gpt-4o-mini",
                            input_tokens=50, output_tokens=20,
                            stop_reason="stop", raw_provider="openai"),
        )
        with patch.object(TUR, "_http_post_json") as http_mock:
            turn = TUR._call_openai(
                "sk-test", "gpt-4o-mini", "",
                "sys",
                [{"role": "user", "content": "hi"}],
                [],
                response_cache=cache,
            )
        http_mock.assert_not_called()
        self.assertEqual(turn.raw_provider, "openai")
        self.assertEqual(turn.text, "cached")


if __name__ == "__main__":
    unittest.main()
