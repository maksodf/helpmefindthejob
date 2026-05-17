"""LLM response cache (R23.8).

Two cost-saving mechanisms work together:

1. **Provider-side prompt caching** (Anthropic ``cache_control``,
   OpenAI automatic) — the provider keeps our system prompt warm
   for a few minutes and charges ~10% of input cost on cache hit.
   That happens at the API layer; we just need to mark the system
   block.
2. **Process-side response cache** (this module) — when the exact
   same (model, system, messages, tools) tuple already produced a
   text reply with NO tool calls, return that cached reply instead
   of re-calling the LLM. Skips the network entirely.

Why "no tool calls" is the cache key gate
=========================================

A response with tool_calls is the FIRST half of a side-effectful
operation. Even if the user asks the same question twice, the
second one needs the side effect to happen again (recording the
chat call, hitting the database, etc.). Caching a text-only reply
is safe because there's no side effect — it's just words.

Cache shape
===========

An in-memory ``OrderedDict`` keyed by a SHA-256 of the request
tuple. LRU eviction at ``MAX_ENTRIES`` (default 512). TTL per
entry (default 600s) trades freshness against hit rate; LLM
behaviour drifts slowly so 10 minutes is a sensible default.

Telemetry
=========

``hits`` and ``misses`` counters expose effectiveness to the
admin dashboard; ``hit_rate()`` is the headline number. Reset
on server restart — the cache itself is per-process and ephemeral.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass


MAX_ENTRIES = int(os.environ.get("DIRECTJOB_LLM_CACHE_MAX_ENTRIES") or "512")
DEFAULT_TTL_S = int(os.environ.get("DIRECTJOB_LLM_CACHE_TTL_S") or "600")


@dataclass
class CachedResponse:
    """The payload we replay on a cache hit. Matches the subset of
    ``LLMTurn`` fields that depend on the LLM provider."""
    text: str
    model_used: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    raw_provider: str


def _stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False)


def cache_key(*, provider: str, model: str, system: str,
                messages: list, tools: list) -> str:
    """Hash the inputs that materially change the LLM response."""
    payload = _stable_json({
        "provider": provider,
        "model": model,
        "system": system,
        "messages": messages,
        "tools": tools,
    })
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LLMResponseCache:
    """Thread-safe LRU + TTL cache. Single instance lives on
    ``AppState`` and is invoked by the provider adapters."""

    def __init__(self, *, max_entries: int = MAX_ENTRIES,
                  ttl_s: int = DEFAULT_TTL_S) -> None:
        self.max_entries = max(1, int(max_entries))
        self.ttl_s = max(1, int(ttl_s))
        self._entries: "OrderedDict[str, tuple[float, CachedResponse]]" = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        # R24.2 — periodic TTL sweep so stale entries don't squat
        # memory until LRU eviction pressure hits. Throttled to once
        # per ``ttl_s`` seconds so the sweep cost is amortised.
        self._last_sweep_at = 0.0

    def get(self, key: str) -> CachedResponse | None:
        now = time.time()
        with self._lock:
            # R24.2 — opportunistic sweep before lookup. Throttled
            # so the sweep cost only lands when meaningful.
            if now - self._last_sweep_at > self.ttl_s:
                self._sweep_expired_locked(now)
                self._last_sweep_at = now
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires_at, value = entry
            if expires_at <= now:
                # Stale — evict and miss.
                self._entries.pop(key, None)
                self.misses += 1
                return None
            # LRU bump.
            self._entries.move_to_end(key)
            self.hits += 1
            return value

    def _sweep_expired_locked(self, now: float) -> int:
        """Drop every expired entry. Must hold ``self._lock``.
        Returns the number of entries dropped."""
        stale = [k for k, (exp, _v) in self._entries.items() if exp <= now]
        for k in stale:
            self._entries.pop(k, None)
        return len(stale)

    def sweep_expired(self) -> int:
        """Public TTL-sweep entry point — runs unconditionally
        (ignores the throttle). Returns rows dropped. Useful for
        tests and operator hard-clean."""
        now = time.time()
        with self._lock:
            return self._sweep_expired_locked(now)

    def put(self, key: str, value: CachedResponse) -> None:
        # Don't cache empty replies (provider error / refusal) — those
        # waste a slot and a retry would likely succeed.
        if not (value and (value.text or "").strip()):
            return
        with self._lock:
            self._entries[key] = (time.time() + self.ttl_s, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def invalidate_all(self) -> int:
        """Test helper / operator hard-reset."""
        with self._lock:
            n = len(self._entries)
            self._entries.clear()
            return n

    def stats(self) -> dict[str, int | float]:
        with self._lock:
            total = self.hits + self.misses
            rate = (self.hits / total) if total else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(rate, 4),
                "entries": len(self._entries),
                "max_entries": self.max_entries,
                "ttl_s": self.ttl_s,
            }
