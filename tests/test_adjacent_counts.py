# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 5 — adjacent-criterion counts tests.

Operator-required invariants (2026-05-20):

  1. ColdCachePanelMatrixTests — 7-persona panel cold-cache → zero
     counts surfaced anywhere (menu lines + auto-relax suggestion).
  2. WarmCacheMixedScenarioTests — seed 1-2 affordances; verify
     seeded surface, cold omit cleanly.
  3. PerLateralMixedStateTests — mixed warm/cold laterals → each
     lateral rendered per its own state in auto-relax; menu
     aggregate omitted (Q2).
  4. SeedAssertsValueInvariant — seed N, assert N in surface text
     (no fabrication, no inflation, no rounding).
  5. NoLLMInvocationTests — static-import grep on widening.py.
  6. BothModesShowCountsTests — warm cache + same scenario →
     menu AND auto-relax both show count on the same affordance.
  7. CountZeroShownExactly — cache seeded with 0 → "(0 postings)"
     in both modes, WITHOUT the tilde (operator Q3 push-back).
  8. MenuAggregateOmittedOnPartialLaterals — 2 of 3 warm + 1 cold
     → menu has NO aggregate; auto-relax per-lateral mixed.
  9. MenuAggregateShownOnAllLateralsWarm — all 3 warm → menu
     shows "(~N postings)" aggregate (sum).
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
    _compute_new_laterals,
    _enter_auto_relax,
    _format_review_empty_reply,
)
from company_discovery.persona_fixtures import PERSONAS
from company_discovery.widening import (
    DROP_SENIORITY,
    TRY_LATERALS,
    WIDEN_LOCATION,
    classify_visa_constraint,
    format_count_text,
    probe_count_for_affordance,
    probe_lateral_counts,
)


class _StubProvider:
    def __init__(self, name: str) -> None:
        self.name = name


def _make_engine() -> tuple[DiagnosticEngine, AggregatorResultCache, Path]:
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    cache = AggregatorResultCache(tmp.name, ttl_seconds=3600)
    engine = DiagnosticEngine(cache=cache, providers=[_StubProvider("arbeitnow")])
    return engine, cache, Path(tmp.name)


def _make_jobs(n: int) -> list[AggregatedJob]:
    return [
        AggregatedJob(
            title=f"Job {i}", company_name=f"Co{i}",
            source="arbeitnow", source_url=f"https://x.test/{i}",
        )
        for i in range(n)
    ]


def _journey_for_persona(slug: str, *, location: str = "Berlin") -> UserJourney:
    persona = next(p for p in PERSONAS if p.slug == slug)
    j = UserJourney(phase=PHASE_REVIEW)
    j.review_substate = "empty"
    j.role_text = persona.target_roles[0]
    j.target_roles = [persona.target_roles[0]]
    j.location = location
    j.years_experience = persona.years_experience
    j.visa_constrained = classify_visa_constraint(persona.residency_status)
    return j


# ----------------------------------------------------------------------
# 7. CountZeroShownExactly (operator Q3 push-back)
# ----------------------------------------------------------------------

class CountZeroShownExactlyTests(unittest.TestCase):
    """Operator Q3 push-back: a cache hit returning 0 results IS
    information. Show "(0 postings)" exactly, NO tilde. Both modes."""

    def test_format_count_text_zero_no_tilde(self) -> None:
        self.assertEqual(format_count_text(0), "(0 postings)")

    def test_format_count_text_positive_has_tilde(self) -> None:
        self.assertEqual(format_count_text(7), "(~7 postings)")
        self.assertEqual(format_count_text(47), "(~47 postings)")

    def test_format_count_text_none_omits(self) -> None:
        self.assertEqual(format_count_text(None), "")

    def test_menu_shows_zero_exactly(self) -> None:
        engine, cache, path = _make_engine()
        try:
            # Seed widen-location cache with EMPTY list (cache hit, 0 results)
            qh = canonical_query("Registered nurse", "")
            cache.put("arbeitnow", qh, [])
            j = _journey_for_persona("aicha")
            reply = _format_review_empty_reply(j, engine=engine)
            self.assertIn(
                "(0 postings)",
                reply,
                "menu must show '(0 postings)' exactly for cache hit with 0 results",
            )
            self.assertNotIn(
                "(~0 postings)",
                reply,
                "0 must NOT have a tilde — tilde reserved for approximate counts",
            )
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_auto_relax_shows_zero_exactly(self) -> None:
        engine, cache, path = _make_engine()
        try:
            # Yusuf is unconstrained → widen_location first in auto-mode
            qh = canonical_query("Mechanical engineer", "")
            cache.put("arbeitnow", qh, [])
            j = _journey_for_persona("yusuf")
            j.role_text = "Mechanical engineer"
            j.target_roles = ["Mechanical engineer"]
            j.auto_relax_declined = [TRY_LATERALS]  # force widen first
            result = _enter_auto_relax(j, new_laterals=[], engine=engine)
            self.assertIn(
                "(0 postings)",
                result.reply,
                "auto-relax must show '(0 postings)' exactly",
            )
            self.assertNotIn("(~0", result.reply)
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# 1. ColdCachePanelMatrixTests
# ----------------------------------------------------------------------

class ColdCachePanelMatrixTests(unittest.TestCase):
    def test_no_counts_in_menu_for_any_persona(self) -> None:
        engine, cache, path = _make_engine()
        try:
            for persona in PERSONAS:
                with self.subTest(persona=persona.slug):
                    j = _journey_for_persona(persona.slug)
                    reply = _format_review_empty_reply(j, engine=engine)
                    self.assertNotIn(
                        "postings)",
                        reply,
                        f"cold-cache menu for {persona.slug} must show no counts",
                    )
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_no_counts_in_auto_relax_for_any_persona(self) -> None:
        engine, cache, path = _make_engine()
        try:
            for persona in PERSONAS:
                with self.subTest(persona=persona.slug):
                    j = _journey_for_persona(persona.slug)
                    new_laterals = _compute_new_laterals(j)
                    result = _enter_auto_relax(
                        j, new_laterals=new_laterals, engine=engine
                    )
                    self.assertNotIn(
                        "postings)",
                        result.reply,
                        f"cold-cache auto-relax for {persona.slug} must show no counts",
                    )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# 2. WarmCacheMixedScenarioTests
# ----------------------------------------------------------------------

class WarmCacheMixedScenarioTests(unittest.TestCase):
    def test_widen_warm_drop_cold_in_menu(self) -> None:
        engine, cache, path = _make_engine()
        try:
            # Seed widen_location cache hit (same role, no location)
            qh = canonical_query("Senior Krankenpfleger", "")
            cache.put("arbeitnow", qh, _make_jobs(13))
            # NO drop-seniority probe seeded → that line should omit
            j = _journey_for_persona("aicha")
            j.role_text = "Senior Krankenpfleger"
            j.target_roles = ["Senior Krankenpfleger"]
            reply = _format_review_empty_reply(j, engine=engine)
            # Widen line should have the count
            self.assertIn("(~13 postings)", reply)
            # The reply should NOT contain a fabricated count for drop_seniority
            # (only one count should appear)
            self.assertEqual(reply.count("postings)"), 1)
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# 3 + 8 + 9. PerLateralMixedStateTests + MenuAggregate variants
# ----------------------------------------------------------------------

class PerLateralMixedStateTests(unittest.TestCase):
    def test_per_lateral_rendering_mixed_state_auto_relax(self) -> None:
        engine, cache, path = _make_engine()
        try:
            j = _journey_for_persona("aicha")
            # Aïcha's deterministic laterals = [
            #   "Senior Registered nurse", "Lead Registered nurse",
            #   "Assistant Registered nurse"
            # ]
            new_laterals = _compute_new_laterals(j)
            self.assertEqual(len(new_laterals), 3, "fixture sanity")
            # Seed 2 of 3 warm, 1 cold
            cache.put(
                "arbeitnow",
                canonical_query(new_laterals[0], "Berlin"),
                _make_jobs(12),
            )
            cache.put(
                "arbeitnow",
                canonical_query(new_laterals[1], "Berlin"),
                _make_jobs(8),
            )
            # new_laterals[2] left cold
            # Force try_laterals to be first in auto-mode (Aïcha
            # constrained order = laterals first, so it's already
            # first; no need to manipulate state)
            result = _enter_auto_relax(
                j, new_laterals=new_laterals, engine=engine
            )
            # Warm laterals show their counts inline
            self.assertIn("(~12 postings)", result.reply)
            self.assertIn("(~8 postings)", result.reply)
            # Cold lateral renders WITHOUT a count parenthetical
            # (look for the lateral name followed by `,` or `.` — not
            # by ` (`)
            cold_lateral = new_laterals[2]
            # The cold lateral appears bolded in the suggestion
            self.assertIn(f"**{cold_lateral}**", result.reply)
            # And it does NOT have a count next to it
            self.assertNotIn(
                f"**{cold_lateral}** (",
                result.reply,
                f"cold lateral {cold_lateral!r} must render without "
                f"a fabricated count parenthetical",
            )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


class MenuAggregateOmittedOnPartialLateralsTests(unittest.TestCase):
    """Operator Q2: menu aggregate appears ONLY when ALL laterals
    warm. Partial-data sum would be decision-misleading."""

    def test_2_of_3_warm_omits_aggregate(self) -> None:
        engine, cache, path = _make_engine()
        try:
            j = _journey_for_persona("aicha")
            new_laterals = _compute_new_laterals(j)
            cache.put(
                "arbeitnow",
                canonical_query(new_laterals[0], "Berlin"),
                _make_jobs(12),
            )
            cache.put(
                "arbeitnow",
                canonical_query(new_laterals[1], "Berlin"),
                _make_jobs(8),
            )
            # new_laterals[2] left cold → aggregate must be omitted
            reply = _format_review_empty_reply(j, engine=engine)
            # Verify try_laterals affordance is present but has NO count
            # parenthetical (the line ends with the description, not "(...)")
            # Search for the try_laterals line:
            line = next(
                ln for ln in reply.split("\n") if "Try lateral roles" in ln
            )
            self.assertNotIn(
                "postings)",
                line,
                "try_laterals menu line must omit aggregate on partial "
                "lateral cache state",
            )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


class MenuAggregateShownOnAllLateralsWarmTests(unittest.TestCase):
    def test_all_warm_shows_aggregate(self) -> None:
        engine, cache, path = _make_engine()
        try:
            j = _journey_for_persona("aicha")
            new_laterals = _compute_new_laterals(j)
            counts = [12, 8, 4]
            for lat, c in zip(new_laterals, counts):
                cache.put(
                    "arbeitnow",
                    canonical_query(lat, "Berlin"),
                    _make_jobs(c),
                )
            reply = _format_review_empty_reply(j, engine=engine)
            line = next(
                ln for ln in reply.split("\n") if "Try lateral roles" in ln
            )
            # Aggregate = 12 + 8 + 4 = 24
            self.assertIn(
                "(~24 postings)",
                line,
                "all-warm laterals must surface aggregate count on menu line",
            )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# 4. SeedAssertsValueInvariant
# ----------------------------------------------------------------------

class SeedAssertsValueInvariantTests(unittest.TestCase):
    """Seed exactly N, assert exactly N appears in surface text.
    No fabrication, no inflation, no rounding (mirror piece-2 pattern)."""

    def test_widen_location_count_matches_seed(self) -> None:
        engine, cache, path = _make_engine()
        try:
            for n in (1, 7, 47, 99, 156):
                cache.purge_expired()  # not actually needed but harmless
                with self.subTest(n=n):
                    # Fresh cache entry per N
                    j = _journey_for_persona("yusuf")
                    j.role_text = "Mechanical engineer"
                    j.target_roles = ["Mechanical engineer"]
                    qh = canonical_query("Mechanical engineer", "")
                    cache.put("arbeitnow", qh, _make_jobs(n))
                    count = probe_count_for_affordance(
                        j,
                        type("A", (), {"id": WIDEN_LOCATION})(),
                        engine=engine,
                    )
                    self.assertEqual(
                        count,
                        n,
                        f"seeded N={n}, expected count {n}, got {count}",
                    )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# 5. NoLLMInvocationTests
# ----------------------------------------------------------------------

class NoLLMInvocationTests(unittest.TestCase):
    """Piece 5 surface is template + cache. Static-import grep on
    widening.py guarantees no LLM dependencies. Mirror piece-2 pattern."""

    def test_widening_module_does_not_import_llm_paths(self) -> None:
        import company_discovery.widening as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        forbidden = (
            "_dispatch_provider",
            "build_auto_fit_prompt",
            "build_cv_tailoring_prompt",
            "build_letter_prompt",
            "AIProviderConfig",
            "openai",
            "anthropic",
            "ollama",
            "google.generativeai",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                source,
                f"widening.py references {f!r} — count surface must "
                f"be deterministic + template-based; LLM is forbidden",
            )


# ----------------------------------------------------------------------
# 6. BothModesShowCountsTests
# ----------------------------------------------------------------------

class BothModesShowCountsTests(unittest.TestCase):
    def test_widen_location_count_appears_in_menu_and_auto_relax(self) -> None:
        engine, cache, path = _make_engine()
        try:
            qh = canonical_query("Mechanical engineer", "")
            cache.put("arbeitnow", qh, _make_jobs(47))
            j = _journey_for_persona("yusuf")
            j.role_text = "Mechanical engineer"
            j.target_roles = ["Mechanical engineer"]
            # Menu mode
            menu_reply = _format_review_empty_reply(j, engine=engine)
            self.assertIn("(~47 postings)", menu_reply)
            # Auto-relax mode (force widen first via declining laterals)
            j2 = _journey_for_persona("yusuf")
            j2.role_text = "Mechanical engineer"
            j2.target_roles = ["Mechanical engineer"]
            j2.auto_relax_declined = [TRY_LATERALS]
            ar_result = _enter_auto_relax(j2, new_laterals=[], engine=engine)
            self.assertIn("(~47 postings)", ar_result.reply)
        finally:
            cache.close()
            path.unlink(missing_ok=True)


# ----------------------------------------------------------------------
# Helpers — probe_lateral_counts shape contract
# ----------------------------------------------------------------------

class ProbeLateralCountsTests(unittest.TestCase):
    def test_returns_aligned_list(self) -> None:
        engine, cache, path = _make_engine()
        try:
            j = _journey_for_persona("aicha")
            new_laterals = _compute_new_laterals(j)
            cache.put(
                "arbeitnow",
                canonical_query(new_laterals[0], "Berlin"),
                _make_jobs(5),
            )
            # Other two cold
            counts = probe_lateral_counts(j, new_laterals, engine=engine)
            self.assertEqual(len(counts), len(new_laterals))
            self.assertEqual(counts[0], 5)
            self.assertIsNone(counts[1])
            self.assertIsNone(counts[2])
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_empty_input_returns_empty(self) -> None:
        engine, cache, path = _make_engine()
        try:
            j = _journey_for_persona("aicha")
            self.assertEqual(probe_lateral_counts(j, [], engine=engine), [])
        finally:
            cache.close()
            path.unlink(missing_ok=True)

    def test_no_engine_returns_all_none(self) -> None:
        j = _journey_for_persona("aicha")
        new_laterals = _compute_new_laterals(j)
        counts = probe_lateral_counts(j, new_laterals, engine=None)
        self.assertEqual(counts, [None, None, None])

    def test_probes_with_journey_location_not_none(self) -> None:
        """Operator Q4: TRY_LATERALS widens role, not location.
        probe_lateral_counts MUST probe with journey.location intact,
        not None."""
        engine, cache, path = _make_engine()
        try:
            j = _journey_for_persona("aicha", location="Berlin")
            # Seed counts ONLY at the Berlin-specific cache key
            cache.put(
                "arbeitnow",
                canonical_query("Senior Registered nurse", "Berlin"),
                _make_jobs(9),
            )
            # And a different value at the no-location key — to prove
            # probe_lateral_counts isn't using location=None
            cache.put(
                "arbeitnow",
                canonical_query("Senior Registered nurse", ""),
                _make_jobs(999),
            )
            counts = probe_lateral_counts(
                j, ["Senior Registered nurse"], engine=engine
            )
            self.assertEqual(
                counts[0],
                9,
                "probe_lateral_counts must use journey.location='Berlin' "
                "(returns 9), not location=None (which would return 999)",
            )
        finally:
            cache.close()
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
