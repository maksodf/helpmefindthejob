"""R23.8 — LLM response cache.

The cache short-circuits the API call for identical (model, system,
messages, tools) tuples that previously produced a text-only reply.
Tool-using replies are never cached (would skip the side effects).
"""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company_discovery.llm_response_cache import (
    CachedResponse, LLMResponseCache, cache_key,
)


class CacheKeyDeterminismTests(unittest.TestCase):
    def test_same_inputs_same_key(self):
        a = cache_key(provider="anthropic", model="claude-haiku-4-5",
                       system="sys",
                       messages=[{"role": "user", "content": "hi"}],
                       tools=[])
        b = cache_key(provider="anthropic", model="claude-haiku-4-5",
                       system="sys",
                       messages=[{"role": "user", "content": "hi"}],
                       tools=[])
        self.assertEqual(a, b)

    def test_different_model_different_key(self):
        a = cache_key(provider="anthropic", model="claude-haiku-4-5",
                       system="sys", messages=[], tools=[])
        b = cache_key(provider="anthropic", model="claude-sonnet-4-6",
                       system="sys", messages=[], tools=[])
        self.assertNotEqual(a, b)

    def test_different_system_different_key(self):
        a = cache_key(provider="anthropic", model="m",
                       system="A", messages=[], tools=[])
        b = cache_key(provider="anthropic", model="m",
                       system="B", messages=[], tools=[])
        self.assertNotEqual(a, b)

    def test_message_order_changes_key(self):
        """Conversation order matters — '...hi/hello' and 'hello/hi'
        are different conversations."""
        a = cache_key(provider="anthropic", model="m", system="s",
                       messages=[{"role": "user", "content": "hi"},
                                  {"role": "assistant", "content": "hello"}],
                       tools=[])
        b = cache_key(provider="anthropic", model="m", system="s",
                       messages=[{"role": "assistant", "content": "hello"},
                                  {"role": "user", "content": "hi"}],
                       tools=[])
        self.assertNotEqual(a, b)


class CacheGetPutTests(unittest.TestCase):
    def setUp(self):
        self.cache = LLMResponseCache(max_entries=4, ttl_s=60)

    def _value(self, text="hello"):
        return CachedResponse(text=text, model_used="m",
                                input_tokens=100, output_tokens=50,
                                stop_reason="end_turn",
                                raw_provider="anthropic")

    def test_put_get_round_trip(self):
        self.cache.put("k1", self._value("alpha"))
        got = self.cache.get("k1")
        self.assertIsNotNone(got)
        self.assertEqual(got.text, "alpha")

    def test_miss_increments_misses(self):
        self.cache.get("nope")
        stats = self.cache.stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 0)

    def test_hit_increments_hits(self):
        self.cache.put("k1", self._value())
        self.cache.get("k1")
        stats = self.cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 0)

    def test_lru_eviction_at_max_entries(self):
        for i in range(6):
            self.cache.put(f"k{i}", self._value(f"v{i}"))
        # Cache size capped at 4; first 2 entries evicted.
        self.assertIsNone(self.cache.get("k0"))
        self.assertIsNone(self.cache.get("k1"))
        self.assertIsNotNone(self.cache.get("k5"))

    def test_ttl_expires_entry(self):
        short = LLMResponseCache(max_entries=4, ttl_s=1)
        short.put("k1", self._value())
        self.assertIsNotNone(short.get("k1"))
        # Force-stale by manipulating the entry timestamp.
        with short._lock:
            _, val = short._entries["k1"]
            short._entries["k1"] = (time.time() - 10, val)
        self.assertIsNone(short.get("k1"))

    def test_empty_text_not_cached(self):
        """Provider error → empty response → don't cache (would lock
        the user out of the right answer on retry)."""
        self.cache.put("k1", CachedResponse(text="", model_used="m",
                                                input_tokens=0,
                                                output_tokens=0,
                                                stop_reason="error",
                                                raw_provider="anthropic"))
        self.assertIsNone(self.cache.get("k1"))

    def test_concurrent_put_get_stable(self):
        """No torn reads / corruption under thread contention."""
        errors: list[str] = []

        def worker(idx: int):
            try:
                for i in range(50):
                    self.cache.put(f"u{idx}-{i}",
                                     self._value(f"u{idx}-{i}"))
                    val = self.cache.get(f"u{idx}-{i}")
                    if val is not None and val.text != f"u{idx}-{i}":
                        errors.append(f"u{idx}-{i}: torn read")
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,))
                    for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


class CacheIntegrationWithRouterTests(unittest.TestCase):
    """End-to-end: a second identical _call_anthropic returns from
    cache without hitting _http_post_json."""

    def test_second_identical_call_does_not_hit_provider(self):
        from company_discovery import tool_use_router as TUR
        cache = LLMResponseCache(max_entries=10, ttl_s=60)

        http_calls = {"n": 0}

        def fake_http(url, headers, body, timeout=None):
            http_calls["n"] += 1
            return 200, {
                "content": [{"type": "text", "text": "cached reply"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }

        with patch.object(TUR, "_http_post_json", new=fake_http):
            turn1 = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5",
                "sys-prompt",
                [{"role": "user", "content": "hi"}],
                [],
                response_cache=cache,
            )
            turn2 = TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5",
                "sys-prompt",
                [{"role": "user", "content": "hi"}],
                [],
                response_cache=cache,
            )

        # Both turns produced the same reply...
        self.assertEqual(turn1.text, "cached reply")
        self.assertEqual(turn2.text, "cached reply")
        # ...but the second call was served from cache: HTTP hit only once.
        self.assertEqual(http_calls["n"], 1,
                          "second call should have been cache-served")
        # Cached call has zero tokens recorded — no cost.
        self.assertEqual(turn2.input_tokens, 0)
        self.assertEqual(turn2.output_tokens, 0)

    def test_tool_use_response_not_cached(self):
        """A response with tool_calls must NOT be cached — caching
        it would skip the side-effectful tool dispatch on replay."""
        from company_discovery import tool_use_router as TUR
        cache = LLMResponseCache(max_entries=10, ttl_s=60)

        http_calls = {"n": 0}

        def fake_http_tool_use(url, headers, body, timeout=None):
            http_calls["n"] += 1
            return 200, {
                "content": [
                    {"type": "tool_use", "id": "t1",
                      "name": "find_jobs",
                      "input": {"persona_id": "bartender"}},
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 50, "output_tokens": 20},
            }

        with patch.object(TUR, "_http_post_json", new=fake_http_tool_use):
            TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5",
                "sys-prompt",
                [{"role": "user", "content": "find jobs"}],
                [{"name": "find_jobs", "description": "search",
                   "input_schema": {"type": "object", "properties": {},
                                       "required": []}}],
                response_cache=cache,
            )
            TUR._call_anthropic(
                "sk-test", "claude-haiku-4-5",
                "sys-prompt",
                [{"role": "user", "content": "find jobs"}],
                [{"name": "find_jobs", "description": "search",
                   "input_schema": {"type": "object", "properties": {},
                                       "required": []}}],
                response_cache=cache,
            )

        # Both calls hit the provider — tool-use responses bypass cache.
        self.assertEqual(http_calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
