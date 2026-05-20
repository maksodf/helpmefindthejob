# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 2 — diagnostic explanation engine tests.

Doctrine-correctness invariants pinned here:
  - DETERMINISTIC: no LLM is ever called (verified by import-graph
    assertion + structural review of the module).
  - NO HALLUCINATION: cold-cache 7-persona matrix all return None
    (the caller substitutes the strict-fact fallback). Warm-cache
    scenarios return only counts the cache actually contained.
  - STRICT-FACT FALLBACK: when no diagnostic_text, the empty-state
    reply contains zero forbidden hedging phrases.
  - PIECE-5 SEAM: the _warm_cache_for_candidate hook exists and is
    invoked on every candidate (piece 5 will decorate it).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from company_discovery.aggregators import (
    AggregatedJob,
    AggregatorResultCache,
    canonical_query,
)
from company_discovery.diagnostic_engine import DiagnosticEngine
from company_discovery.journey import (
    PHASE_REVIEW,
    UserJourney,
    _format_review_empty_reply,
)


# Mirror the 7-persona panel used by PART 5 + PART 6 walks.
# Each entry is (role_text, location).
PERSONAS = (
    ("aicha",   "Registered nurse",                                       "Berlin"),
    ("yusuf",   "Mechanical engineer",                                    "Munich"),
    ("olga",    "Senior frontend developer",                              "Leipzig"),
    ("mahmoud", "Auszubildender Anlagenmechaniker SHK",                   "Hamburg"),
    ("maria",   "Altenpflegerin",                                         "Stuttgart"),
    ("kaethe",  "Krankenschwester (Wiedereinstieg)",                      "Berlin"),
    ("tobias",  "Senior Backend Developer (Public Sector / Civic Tech)",  "Hamburg"),
)


# Forbidden hedging phrases per operator spec 2026-05-20 — the
# strict-fact fallback MUST NOT contain any of these.
_FORBIDDEN_HEDGING = (
    "this might be due to",
    "the role may be uncommon",
    "restrictive criteria",
    "low recent posting volume",
    "the market for",
    "tends to require",
    "typically requires",
    "uncommon combination",
    "may indicate",
    "the labor market",
    "competitive right now",
    "soft for this role",
)


class _StubProvider:
    """Provider stub for cache-key matching; never .search()'d."""

    def __init__(self, name: str) -> None:
        self.name = name


def _make_engine() -> tuple[DiagnosticEngine, AggregatorResultCache, Path]:
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    cache = AggregatorResultCache(tmp.name, ttl_seconds=3600)
    providers = [
        _StubProvider("arbeitnow"),
        _StubProvider("eures"),
        _StubProvider("bundesagentur"),
    ]
    engine = DiagnosticEngine(cache=cache, providers=providers)
    return engine, cache, Path(tmp.name)


def _make_aggregated_jobs(n: int, title_prefix: str = "Test job") -> list[AggregatedJob]:
    return [
        AggregatedJob(
            title=f"{title_prefix} {i}",
            company_name=f"Company {i}",
            source="arbeitnow",
            source_url=f"https://example.test/job/{i}",
            location="Berlin",
        )
        for i in range(n)
    ]


class ColdCachePanelMatrixTests(unittest.TestCase):
    """Cold-cache scenario: NO relaxation candidate has data → engine
    returns None for every persona. The caller substitutes the strict-
    fact fallback (no hallucination)."""

    def test_each_persona_returns_none_on_cold_cache(self) -> None:
        engine, cache, path = _make_engine()
        try:
            for slug, role_text, location in PERSONAS:
                with self.subTest(persona=slug):
                    diag = engine.generate(
                        role_text=role_text, location=location, filters=None
                    )
                    self.assertIsNone(
                        diag,
                        f"persona {slug}: cold-cache engine MUST return None "
                        f"(returned {diag!r}); no inference allowed",
                    )
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_cold_cache_fallback_contains_no_hedging(self) -> None:
        """The strict-fact fallback emitted when diagnostic is None
        must contain zero forbidden hedging phrases — the operator's
        doctrine."""
        engine, cache, path = _make_engine()
        try:
            for slug, role_text, location in PERSONAS:
                with self.subTest(persona=slug):
                    journey = UserJourney(phase=PHASE_REVIEW)
                    journey.target_roles = [role_text]
                    journey.location = location
                    journey.review_substate = "empty"
                    # Engine returns None (cold cache)
                    diag = engine.generate(
                        role_text=role_text, location=location, filters=None
                    )
                    self.assertIsNone(diag)
                    # Reply uses the strict-fact fallback
                    reply = _format_review_empty_reply(journey, diagnostic_text=None)
                    reply_lc = reply.lower()
                    for forbidden in _FORBIDDEN_HEDGING:
                        self.assertNotIn(
                            forbidden,
                            reply_lc,
                            f"persona {slug}: strict-fact fallback contains "
                            f"forbidden hedging phrase {forbidden!r}",
                        )
                    # Sanity: the fallback states the fact + names the role/location
                    self.assertIn("No matches found", reply)
                    self.assertIn(role_text, reply)
                    self.assertIn(location, reply)
        finally:
            cache.close()
            path.unlink(missing_ok=True)


class WarmCacheDiagnosticTests(unittest.TestCase):
    """Warm-cache scenario: a relaxation candidate has cached data →
    engine generates substantive diagnostic from the count. Verifies
    the verbalization template + that only cached numbers appear."""

    def test_drop_seniority_candidate_warm(self) -> None:
        engine, cache, path = _make_engine()
        try:
            # Seed cache with the relaxation candidate (role without
            # "Senior" prefix, same location) for one provider.
            seeded_jobs = _make_aggregated_jobs(13)
            seeded_hash = canonical_query("frontend developer", "Leipzig")
            cache.put("arbeitnow", seeded_hash, seeded_jobs)
            # Engine called with Olga's failed query
            diag = engine.generate(
                role_text="Senior frontend developer",
                location="Leipzig",
                filters=None,
            )
            self.assertIsNotNone(
                diag, "warm-cache relaxation candidate must produce a diagnostic"
            )
            self.assertIn("13", diag, "diagnostic must surface the actual cached count")
            self.assertIn("frontend developer", diag)
            self.assertIn("Leipzig", diag)
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_anywhere_candidate_warm(self) -> None:
        engine, cache, path = _make_engine()
        try:
            # Seed: same role, no location
            seeded_jobs = _make_aggregated_jobs(47, title_prefix="Krankenschwester")
            seeded_hash = canonical_query("Krankenschwester", "")
            cache.put("eures", seeded_hash, seeded_jobs)
            diag = engine.generate(
                role_text="Krankenschwester", location="Berlin", filters=None
            )
            self.assertIsNotNone(diag)
            self.assertIn("47", diag)
            self.assertIn("no location filter", diag.lower())
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_diagnostic_contains_only_cached_numbers(self) -> None:
        """The model must NEVER invent counts. Seed 7 jobs, expect 7
        in the diagnostic — never 8, 47, or any other number."""
        engine, cache, path = _make_engine()
        try:
            seeded_jobs = _make_aggregated_jobs(7)
            seeded_hash = canonical_query("nurse", "Berlin")
            cache.put("arbeitnow", seeded_hash, seeded_jobs)
            diag = engine.generate(
                role_text="Senior nurse", location="Berlin", filters=None
            )
            self.assertIsNotNone(diag)
            # The diagnostic must surface "7" and no other count
            self.assertIn("7", diag)
            # Should not contain numbers from operator's example
            # diagnostics (3, 14, 47) UNLESS our seed produced them
            for plausible_other_count in ("3 ", "14 ", "47 "):
                self.assertNotIn(
                    plausible_other_count,
                    diag,
                    f"diagnostic contained {plausible_other_count!r} but the "
                    f"seeded count was 7 — count must reflect cache, not invention",
                )
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_dedup_across_providers(self) -> None:
        """Jobs cached at multiple providers (cross-aggregator dedup)
        must be counted once by source_url, not summed."""
        engine, cache, path = _make_engine()
        try:
            # Same 5 jobs at TWO providers — count should be 5, not 10.
            jobs = _make_aggregated_jobs(5)
            qh = canonical_query("frontend developer", "Leipzig")
            cache.put("arbeitnow", qh, jobs)
            cache.put("eures", qh, jobs)
            diag = engine.generate(
                role_text="Senior frontend developer",
                location="Leipzig",
                filters=None,
            )
            self.assertIsNotNone(diag)
            self.assertIn("5 posting", diag)
        finally:
            cache.close()
            path.unlink(missing_ok=True)


class NoLLMInvocationTests(unittest.TestCase):
    """The diagnostic engine MUST be deterministic and template-based.
    No LLM is ever called. Verified by import-graph inspection.
    """

    def test_module_does_not_import_llm_paths(self) -> None:
        """Static check: diagnostic_engine module imports nothing
        that would let it reach an AI provider. The allowed imports
        are aggregator cache helpers + standard library."""
        import company_discovery.diagnostic_engine as mod

        # Inspect the module's source for forbidden imports
        source_path = Path(mod.__file__)
        source = source_path.read_text(encoding="utf-8")
        forbidden_imports = (
            "_dispatch_provider",
            "build_auto_fit_prompt",
            "build_cv_tailoring_prompt",
            "build_letter_prompt",
            "ai_providers",
            "AIProviderConfig",
            "openai",
            "anthropic",
            "ollama",
            "google.generativeai",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(
                forbidden,
                source,
                f"diagnostic_engine.py references {forbidden!r} — the engine "
                f"must be deterministic and never call an LLM. If LLM-based "
                f"verbalization is later added it must be a Phase 2 item "
                f"with strict 'verbalize only pre-computed facts' constraints.",
            )


class PieceFiveSeamTests(unittest.TestCase):
    """The _warm_cache_for_candidate hook is the forward-compat seam
    for piece 5. It MUST be invoked on every relaxation candidate so
    piece 5 only needs to decorate the hook, not restructure the
    engine."""

    def test_warm_hook_invoked_on_each_candidate(self) -> None:
        engine, cache, path = _make_engine()
        try:
            calls: list[tuple[str, str | None]] = []
            original_hook = engine._warm_cache_for_candidate

            def _spy(query: str, location: str | None) -> None:
                calls.append((query, location))
                original_hook(query, location)

            engine._warm_cache_for_candidate = _spy  # type: ignore[method-assign]
            # Olga's failed query produces 3 relaxation candidates:
            # drop_seniority, anywhere, drop_seniority_and_anywhere
            engine.generate(
                role_text="Senior frontend developer",
                location="Leipzig",
                filters=None,
            )
            # Each unique candidate combo should have been probed
            self.assertGreaterEqual(
                len(calls),
                2,
                "the piece-5 seam must be invoked on each relaxation "
                "candidate so piece 5 can decorate the hook to fire "
                "live probes + write-back",
            )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


class RelaxationCandidatesTests(unittest.TestCase):
    """The relaxation-candidate builder is the engine's core logic.
    Pin its shape so future taxonomy / persona additions don't drift."""

    def test_strips_senior_prefix(self) -> None:
        engine, cache, path = _make_engine()
        try:
            candidates = engine._build_relaxation_candidates(
                "Senior frontend developer", "Leipzig"
            )
            labels = [c.label for c in candidates]
            self.assertIn("drop_seniority", labels)
            self.assertIn("anywhere", labels)
            self.assertIn("drop_seniority_and_anywhere", labels)
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_no_seniority_strip_when_none_present(self) -> None:
        engine, cache, path = _make_engine()
        try:
            candidates = engine._build_relaxation_candidates(
                "Registered nurse", "Berlin"
            )
            labels = [c.label for c in candidates]
            # "Registered" is not in the strippable seniority set
            self.assertNotIn("drop_seniority", labels)
            self.assertNotIn("drop_seniority_and_anywhere", labels)
            # But anywhere widening always applies when location set
            self.assertIn("anywhere", labels)
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_no_anywhere_when_location_already_empty(self) -> None:
        engine, cache, path = _make_engine()
        try:
            candidates = engine._build_relaxation_candidates(
                "Senior frontend developer", None
            )
            labels = [c.label for c in candidates]
            self.assertIn("drop_seniority", labels)
            # No location to widen
            self.assertNotIn("anywhere", labels)
        finally:
            cache.close()
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
