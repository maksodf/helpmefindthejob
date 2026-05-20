# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 2 — diagnostic explanation engine.

Generates a 2-3 sentence prose explanation of WHY the aggregator
returned 0 results for a given query. Strict doctrine:

  - **DETERMINISTIC, NOT AI-DRIVEN.** No LLM is called. Verbalization
    is template-based string assembly from counts the cache supports.
  - **NO HALLUCINATION.** Only facts present in
    ``AggregatorResultCache`` are surfaced. When no cached relaxation
    candidate has data, ``generate()`` returns ``None`` so the caller
    can substitute the strict-fact fallback message.
  - **CACHE-ONLY.** No live ``provider.search()`` calls. The free-tier
    aggregator coverage skews toward English-speaking and tech roles
    (Pflege / Krankenschwester Wiedereinstieg / Anlagenmechaniker
    SHK Ausbildung / German-language civic-tech are under-represented),
    so live-probing only free providers would inject systematic bias
    at the diagnostic layer — under-reporting opportunities for
    exactly the personas this product is built to serve. Operator
    decision 2026-05-20: cache-only is the doctrine-correct architecture.

Forward-compat seam for piece 5 (adjacent-criterion counts): a no-op
hook ``_warm_cache_for_candidate(query, location)`` is invoked on
every relaxation candidate during ``generate()``. Piece 5 will
decorate this hook with live probes against the free-tier providers
plus cache write-back. Piece 2 leaves the call site; piece 5 wires
the substance.

When a persistent facet-indexed job database lands (Phase 2 backlog
#71), it plugs into ``DiagnosticEngine.generate`` without
restructuring — the engine's interface is the seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from company_discovery.aggregators import (
    AggregatedJob,
    AggregatorResultCache,
    canonical_query,
)


# Seniority qualifiers we can strip from role_text as a relaxation
# candidate. Mirrors the prefixes detected in
# aggregators._SENIORITY_CONFLICTS, but only the unambiguously-
# prefix-position ones (we don't want to mistake a job title like
# "Lead Quality Engineer" for a stripped "Lead").
_STRIPPABLE_SENIORITY_PREFIXES: tuple[str, ...] = (
    "senior",
    "junior",
    "lead",
    "principal",
    "staff",
    "head of",
    "chief",
)


class _ProviderName(Protocol):
    name: str


@dataclass(frozen=True)
class _Candidate:
    """One relaxation candidate the engine probes."""

    label: str  # "drop_seniority" | "anywhere" — used by _verbalize
    query: str
    location: str | None
    original_query: str  # for verbalization context
    original_location: str | None


@dataclass(frozen=True)
class _Fact:
    """A cache-probed fact ready for verbalization."""

    candidate: _Candidate
    count: int


class DiagnosticEngine:
    """Cache-only, deterministic diagnostic engine.

    Doctrine reminder (operator 2026-05-20): never calls an LLM. Never
    fires a live provider search. Surfaces only counts derivable from
    ``AggregatorResultCache``. Returns ``None`` when no substantive
    facts are available; callers substitute the strict-fact fallback
    message.
    """

    def __init__(
        self,
        cache: AggregatorResultCache | None,
        providers: list[_ProviderName] | None = None,
    ) -> None:
        self.cache = cache
        self.providers = list(providers or [])

    def generate(
        self,
        *,
        role_text: str,
        location: str | None,
        filters: dict | None = None,
    ) -> str | None:
        """Probe the cache for relaxation candidates; return a 2-3
        sentence diagnostic if substantive facts found, else None.

        Inputs are the user's failed-search criteria (role_text from
        the user's verbatim journey input, location, filters). The
        engine computes relaxation candidates (drop seniority, widen
        to anywhere), probes the cache for each, and verbalizes any
        substantive counts.
        """
        if self.cache is None:
            return None
        candidates = self._build_relaxation_candidates(role_text, location)
        facts: list[_Fact] = []
        seen_combos: set[tuple[str, str | None]] = set()
        for c in candidates:
            combo = (c.query.casefold().strip(), (c.location or "").casefold().strip() or None)
            if combo in seen_combos:
                # De-dup: don't surface the same fact through two
                # different candidate paths (e.g., a query with no
                # seniority to strip AND wider-location may produce
                # the same probe).
                continue
            seen_combos.add(combo)
            # Forward-compat seam: piece 5 will decorate this hook to
            # fire a live probe + write-back when the cache is cold.
            # In piece 2 it's a no-op; the probe is pure cache read.
            self._warm_cache_for_candidate(c.query, c.location)
            count = self._cache_count_across_providers(c.query, c.location)
            if count is not None and count > 0:
                facts.append(_Fact(candidate=c, count=count))
        if not facts:
            return None
        return self._verbalize(role_text, location, facts)

    # ------------------------------------------------------------------
    # Relaxation candidates — pure functions, no I/O
    # ------------------------------------------------------------------

    def _build_relaxation_candidates(
        self, role_text: str, location: str | None
    ) -> list[_Candidate]:
        out: list[_Candidate] = []
        rt = (role_text or "").strip()
        if not rt:
            return out
        # 1. Drop seniority qualifier (if present)
        stripped = self._strip_seniority_prefix(rt)
        if stripped and stripped.casefold() != rt.casefold():
            out.append(
                _Candidate(
                    label="drop_seniority",
                    query=stripped,
                    location=location,
                    original_query=rt,
                    original_location=location,
                )
            )
        # 2. Widen location to None (anywhere)
        if location:
            out.append(
                _Candidate(
                    label="anywhere",
                    query=rt,
                    location=None,
                    original_query=rt,
                    original_location=location,
                )
            )
        # 3. Combined: drop seniority AND widen location
        if stripped and stripped.casefold() != rt.casefold() and location:
            out.append(
                _Candidate(
                    label="drop_seniority_and_anywhere",
                    query=stripped,
                    location=None,
                    original_query=rt,
                    original_location=location,
                )
            )
        return out

    @staticmethod
    def _strip_seniority_prefix(role_text: str) -> str:
        lc = role_text.casefold()
        for prefix in _STRIPPABLE_SENIORITY_PREFIXES:
            if lc.startswith(prefix + " "):
                # Preserve the rest of the role_text verbatim
                # (case + punctuation) so the candidate query is
                # natural.
                return role_text[len(prefix) :].strip()
        return role_text

    # ------------------------------------------------------------------
    # Cache probes — no live calls
    # ------------------------------------------------------------------

    def probe_cached_count(
        self, query: str, location: str | None
    ) -> int | None:
        """Public count primitive for per-candidate cache lookup.

        Used by ``DiagnosticEngine.generate`` (piece 2 — assembles
        relaxation-candidate counts into the diagnostic prose) AND by
        ``widening`` piece 4 (auto-relax engine — surfaces per-
        affordance counts in the suggestion text when available).

        Returns the count of unique jobs (de-duped by source_url
        across providers) for the cached (provider, query, location)
        triple. Returns ``None`` when no provider had a cache hit —
        callers must substitute the cold-cache fallback (omit count
        from the diagnostic / auto-relax suggestion text).

        Forward-compat (piece 5): when persistent job-index lands
        (Phase 2 #71), this method is the integration point — its
        signature stays identical; the underlying cache becomes the
        index.
        """
        return self._cache_count_across_providers(query, location)

    def _cache_count_across_providers(
        self, query: str, location: str | None
    ) -> int | None:
        """Probe the cache across all configured providers for the
        given (query, location). Returns the count of unique jobs
        across cache hits, or None if no provider had a cache hit.

        Private implementation; piece-2 internals call this name.
        Public callers use the alias ``probe_cached_count`` above.
        """
        if self.cache is None:
            return None
        qh = canonical_query(query, location)
        seen_keys: set[str] = set()
        any_hit = False
        for provider in self.providers:
            provider_name = getattr(provider, "name", None)
            if not provider_name:
                continue
            hit = self.cache.get(provider_name, qh)
            if hit is None:
                continue
            any_hit = True
            for job in hit:
                # De-dup by source_url; fall back to title-key.
                key = (
                    getattr(job, "source_url", None)
                    or getattr(job, "title", None)
                    or ""
                ).casefold()
                if key:
                    seen_keys.add(key)
        if not any_hit:
            return None
        return len(seen_keys)

    def _warm_cache_for_candidate(
        self, query: str, location: str | None
    ) -> None:  # noqa: ARG002 - piece-5 seam; arguments will be used when decorated
        """Forward-compat seam for piece 5 (adjacent-criterion counts).

        In piece 2 this is a no-op — option (a) is strictly cache-only.
        Piece 5 will decorate this method to fire a live probe against
        the free-tier providers (with appropriate cross-class-skew
        guards per operator's decision tree) and write the response
        back to the cache so subsequent diagnostics hit warm.

        Leaving the call site here means piece 5 only modifies the
        engine; the caller / fallback semantics stay identical.
        """

    # ------------------------------------------------------------------
    # Verbalization — template-based, no LLM
    # ------------------------------------------------------------------

    def _verbalize(
        self,
        role_text: str,
        location: str | None,
        facts: list[_Fact],
    ) -> str:
        """Compose a 2-3 sentence diagnostic from cached facts.

        Strict no-narrative: each sentence reports a concrete count
        + criterion change. No 'most', 'the market', 'tends to', or
        other inference language.
        """
        role_display = (role_text or "").strip() or "(no role specified)"
        loc_display = (location or "anywhere").strip() or "anywhere"
        # Lead sentence: state the fact + criterion
        lead = (
            f"No matches found for **{role_display}** in **{loc_display}** "
            f"with these preferences."
        )
        # Per-fact sentences (cap at 2 to stay within the 2-3 sentence budget)
        fact_sentences: list[str] = []
        for fact in facts[:2]:
            c = fact.candidate
            if c.label == "drop_seniority":
                # The seniority was stripped — surface this fact
                fact_sentences.append(
                    f"Recent searches without the seniority qualifier "
                    f"returned **{fact.count} posting(s)** for "
                    f"**{c.query}** in **{c.location or 'anywhere'}**."
                )
            elif c.label == "anywhere":
                fact_sentences.append(
                    f"Recent searches for **{c.query}** with no "
                    f"location filter returned **{fact.count} "
                    f"posting(s)**."
                )
            elif c.label == "drop_seniority_and_anywhere":
                fact_sentences.append(
                    f"Without the seniority qualifier and with no "
                    f"location filter, recent searches returned "
                    f"**{fact.count} posting(s)** for **{c.query}**."
                )
        return lead + " " + " ".join(fact_sentences)
