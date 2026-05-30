# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 10.1 — friction_classifier unit tests.

Operator scope (Loop 10.1): 8 unit tests (7 personas + 1
unclassified) + determinism guard test. This file ships those
9 + extras covering tie-break, scored-fallback, and threshold
behavior so the Phase 1 best-guess substrate has documented
expected behavior for downstream loops.
"""

from __future__ import annotations

import unittest

from company_discovery.friction_classifier import (
    SCORED_MIN_HITS,
    ClassificationResult,
    classify,
    classify_with_telemetry,
)

# ─── 7-persona panel — each CV gets classified to its own slug ───


class SevenPersonaPanelTests(unittest.TestCase):
    """One test per fixture persona. Each CV uses fixture-shaped
    strong markers + a smattering of scored signals — the kind of
    CV text a fluent-in-institutional-vocabulary user would write."""

    def test_aicha_cv_classifies_strong(self):
        cv = (
            "Registered nurse, Tunis, Tunisia. Seven years experience "
            "in geriatric care. Currently in §16d Anerkennung process "
            "with BIBB and Anabin recognition databases. Email: a@x.de"
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "aicha")
        self.assertEqual(result.confidence, "strong")

    def test_yusuf_cv_classifies_strong(self):
        cv = (
            "Mechanical engineer, ITÜ Istanbul. Thirteen years in "
            "automotive Tier-2 supplier work. EU Blue Card application "
            "in progress, employer-sponsored at a Munich firm. "
            "CATIA, SolidWorks, ISO 9001 lead auditor."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "yusuf")
        self.assertEqual(result.confidence, "strong")

    def test_olga_cv_classifies_strong(self):
        cv = (
            "DevOps engineer from Kyiv, Ukraine. Currently in Berlin "
            "under §24 AufenthG (Sonderaufenthalt for Ukrainian "
            "displacement). Looking for remote / English-speaking team."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "olga")
        self.assertEqual(result.confidence, "strong")

    def test_mahmoud_cv_classifies_strong(self):
        cv = (
            "Background in Syria, currently in Frankfurt under §4 AsylG "
            "(subsidiärer Schutz). Looking for Ausbildung opportunities "
            "in Handwerk or Lagerarbeit. Have prepared a Bewerbungsmappe."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "mahmoud")
        self.assertEqual(result.confidence, "strong")

    def test_maria_cv_classifies_strong(self):
        cv = (
            "EU citizen from Romania, currently in Stuttgart. Romanian- and "
            "Hungarian-native Krankenschwester with home-elderly-care "
            "(Altenpflege) background. Moved under Freizügigkeitsrecht "
            "freedom of movement."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "maria")
        self.assertEqual(result.confidence, "strong")

    def test_kaethe_cv_classifies_strong(self):
        cv = (
            "Krankenschwester returning to the workforce after a "
            "10-year Familienpause. Looking for Wiedereinstieg "
            "opportunities. Auffrischung courses completed."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "kaethe")
        self.assertEqual(result.confidence, "strong")

    def test_tobias_cv_classifies_strong(self):
        cv = (
            "Former fintech developer exploring Quereinstieg into Civic Tech / "
            "Sovereign Tech. Interested in TVöD public-sector roles "
            "and GovTech."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "tobias")
        self.assertEqual(result.confidence, "strong")


# ─── 1 unclassified — neutral CV with no fixture signals ────────


class UnclassifiedTests(unittest.TestCase):
    def test_neutral_cv_returns_empty(self):
        cv = (
            "Software engineer with 5 years of experience. "
            "Background in distributed systems and cloud platforms. "
            "Email: candidate@example.com  Phone: +49 30 1234-5678  "
            "Experience: 2019 - 2024 at TechCo (Berlin)."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "")
        self.assertEqual(result.confidence, "none")
        self.assertEqual(result.match_count, 0)

    def test_empty_string_returns_empty(self):
        result = classify_with_telemetry("")
        self.assertEqual(result.slug, "")
        self.assertEqual(result.confidence, "none")
        self.assertEqual(result.match_count, 0)

    def test_whitespace_only_returns_empty(self):
        result = classify_with_telemetry("   \n\t  ")
        self.assertEqual(result.slug, "")
        self.assertEqual(result.confidence, "none")


# ─── Determinism guard (OQ-5 verdict) ───────────────────────────


class DeterminismGuardTests(unittest.TestCase):
    """OQ-5 verdict: classify(cv_text) called 10x returns identical
    output. Trivial test pinning the determinism invariant."""

    def test_classify_is_deterministic_10x(self):
        cv = "Registered nurse, §16d Anerkennung process, Tunisia. Email: a@x.de"
        results = [classify(cv) for _ in range(10)]
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(results[0], "aicha")

    def test_classify_with_telemetry_is_deterministic_10x(self):
        cv = "DevOps engineer, Berlin, §24 AufenthG, English team, remote work."
        results = [classify_with_telemetry(cv) for _ in range(10)]
        slugs = {r.slug for r in results}
        confidences = {r.confidence for r in results}
        counts = {r.match_count for r in results}
        self.assertEqual(slugs, {"olga"})
        self.assertEqual(confidences, {"strong"})
        self.assertEqual(counts, {1})


# ─── Tie-break (Q-D verdict — alphabetical slug) ────────────────


class AlphabeticalTieBreakTests(unittest.TestCase):
    """Q-D verdict: ties broken alphabetically by persona slug.
    For strong-markers, iteration is sorted-by-slug so the
    alphabetically-first slug with any hit wins."""

    def test_strong_markers_tied_resolve_alphabetically(self):
        # CV contains BOTH Aïcha (§16d) AND Yusuf (Blue Card)
        # strong markers — alphabetical tie-break picks aicha.
        cv = (
            "Background includes both §16d Anerkennung process and "
            "EU Blue Card status — unusual but possible."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "aicha")  # a < y
        self.assertEqual(result.confidence, "strong")

    def test_scored_pattern_tie_resolves_alphabetically(self):
        # Construct a CV with exactly 2 scored-only hits for two
        # personas at the SAME count. No strong markers (otherwise
        # strong-path short-circuits). Alphabetical wins.
        # mahmoud: "Ausbildung" + "Handwerk" = 2 scored hits
        # tobias:  "fintech" + "career change" = 2 scored hits
        cv = (
            "Background: looking for Ausbildung in Handwerk, "
            "with fintech experience exploring career change."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "mahmoud")  # m < t


# ─── Scored fallback semantics ──────────────────────────────────


class ScoredFallbackTests(unittest.TestCase):
    """Soft multi-signal matching: persona-specific patterns
    requiring ≥ SCORED_MIN_HITS to fire."""

    def test_two_scored_hits_qualifies(self):
        # aicha scored bank includes "Anerkennung" + "Krankenpflege"
        # + "Tunis" + "geriatric" etc. Two hits, no strong markers.
        cv = "Years of Krankenpflege experience in Tunis. Currently exploring the German market."
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "aicha")
        self.assertEqual(result.confidence, "scored")
        self.assertGreaterEqual(result.match_count, 2)

    def test_one_scored_hit_falls_through_to_unclassified(self):
        # Only "Anerkennung" — single soft hit, below threshold.
        cv = (
            "Recognition / Anerkennung process underway. Six years "
            "of professional experience abroad."
        )
        result = classify_with_telemetry(cv)
        self.assertEqual(result.slug, "")
        self.assertEqual(result.confidence, "none")
        self.assertEqual(result.match_count, 0)


# ─── ClassificationResult shape (OQ-2 telemetry contract) ───────


class TelemetryContractTests(unittest.TestCase):
    """OQ-2 verdict: caller writes one log.info per classification
    call with resolved/confidence/match_count. The dataclass shape
    is the contract."""

    def test_result_is_frozen_dataclass(self):
        cv = "§16d Anerkennung"
        result = classify_with_telemetry(cv)
        self.assertIsInstance(result, ClassificationResult)
        # Frozen — mutation raises FrozenInstanceError (a subclass of AttributeError)
        from dataclasses import FrozenInstanceError

        with self.assertRaises(FrozenInstanceError):
            result.slug = "yusuf"  # type: ignore[misc]

    def test_strong_match_has_match_count_one(self):
        cv = "§16d Anerkennung process"
        result = classify_with_telemetry(cv)
        self.assertEqual(result.confidence, "strong")
        self.assertEqual(result.match_count, 1)

    def test_none_match_has_match_count_zero(self):
        result = classify_with_telemetry("Software engineer in Berlin.")
        self.assertEqual(result.confidence, "none")
        self.assertEqual(result.match_count, 0)

    def test_strong_match_has_empty_tied_slugs(self):
        cv = "§16d Anerkennung process"
        result = classify_with_telemetry(cv)
        self.assertEqual(result.confidence, "strong")
        self.assertEqual(result.tied_slugs, ())

    def test_none_match_has_empty_tied_slugs(self):
        result = classify_with_telemetry("Software engineer in Berlin.")
        self.assertEqual(result.confidence, "none")
        self.assertEqual(result.tied_slugs, ())


class PersonaFrictionReconciliationTests(unittest.TestCase):
    """Phase 2 #76 sub-piece (b): persona-vs-friction-class mismatch
    reconciliation. Returns a hint string when persona industry
    doesn't overlap with friction-class typical industry; "" when
    aligned / no constraint / no signal."""

    def test_aligned_persona_friction_returns_empty(self):
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        # Healthcare persona + Aïcha (healthcare friction) — aligned.
        hint = reconcile_persona_and_friction_class(
            persona_industry_terms=("health", "gesund", "klinik"),
            friction_slug="aicha",
        )
        self.assertEqual(hint, "")

    def test_marketing_persona_aicha_friction_flags_mismatch(self):
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        hint = reconcile_persona_and_friction_class(
            persona_industry_terms=("marketing", "brand", "growth"),
            friction_slug="aicha",
        )
        self.assertTrue(hint)
        self.assertIn("§16d", hint)  # Aïcha label
        self.assertIn("marketing", hint)

    def test_empty_friction_slug_returns_empty(self):
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        hint = reconcile_persona_and_friction_class(
            persona_industry_terms=("marketing",),
            friction_slug="",
        )
        self.assertEqual(hint, "")

    def test_kaethe_wiedereinstieg_never_flags_mismatch(self):
        """Käthe = Wiedereinstieg returner; industry-broad — no
        mismatch ever surfaces regardless of persona."""
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        for terms in (
            ("marketing", "brand"),
            ("finance", "bank"),
            ("tech", "saas"),
            ("trade", "handwerk"),
            (),  # no persona signal at all
        ):
            hint = reconcile_persona_and_friction_class(
                persona_industry_terms=terms, friction_slug="kaethe"
            )
            self.assertEqual(hint, "", msg=f"unexpected hint for terms={terms}")

    def test_empty_persona_terms_returns_empty(self):
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        # No persona industry signal — can't reconcile, so no hint.
        hint = reconcile_persona_and_friction_class(
            persona_industry_terms=(), friction_slug="aicha"
        )
        self.assertEqual(hint, "")

    def test_unknown_friction_slug_returns_empty(self):
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        hint = reconcile_persona_and_friction_class(
            persona_industry_terms=("marketing",), friction_slug="totally-bogus"
        )
        self.assertEqual(hint, "")

    def test_case_insensitive_overlap(self):
        from company_discovery.friction_classifier import (
            reconcile_persona_and_friction_class,
        )

        # Persona terms in uppercase, expected industry tokens in
        # lowercase — should still resolve as aligned.
        hint = reconcile_persona_and_friction_class(
            persona_industry_terms=("HEALTH", "KLINIK"),
            friction_slug="aicha",
        )
        self.assertEqual(hint, "")


class TiedSlugsTests(unittest.TestCase):
    """Phase 2 #76 sub-piece (b): scored fallback now surfaces tied
    alternatives in ClassificationResult.tied_slugs so the chat UX
    can name them ("you might also be in Y") + let the user override
    via the change flow. Alphabetical tie-break still picks the
    winner deterministically."""

    def test_tied_slugs_is_tuple(self):
        result = classify_with_telemetry("§16d Anerkennung process")
        self.assertIsInstance(result.tied_slugs, tuple)

    def test_tied_slugs_excludes_the_winning_slug(self):
        from company_discovery.friction_classifier import (
            SCORED_PATTERNS,
        )

        # Construct a CV that packs SCORED_MIN_HITS markers from two
        # different slugs so both qualify with equal counts at the
        # scored fallback. Alphabetical tie-break picks one; the
        # other is reported in tied_slugs.
        slug_a = sorted(SCORED_PATTERNS.keys())[0]
        slug_b = sorted(SCORED_PATTERNS.keys())[1]
        markers_a = list(SCORED_PATTERNS[slug_a])[:SCORED_MIN_HITS]
        markers_b = list(SCORED_PATTERNS[slug_b])[:SCORED_MIN_HITS]
        cv = " ".join(markers_a + markers_b) + " — generic resume body."
        result = classify_with_telemetry(cv)
        # Contract: tied_slugs is a tuple of strings, winner not in
        # it. Specific tied content depends on which markers happen
        # to overlap with STRONG_MARKERS — the assertions below are
        # the universal invariants.
        self.assertIsInstance(result.tied_slugs, tuple)
        self.assertNotIn(result.slug, result.tied_slugs)
        for tied in result.tied_slugs:
            self.assertIsInstance(tied, str)
            self.assertTrue(tied)


# ─── Case-insensitive matching ──────────────────────────────────


class CaseInsensitiveTests(unittest.TestCase):
    """Patterns match regardless of CV text casing — the casefold()
    invariant."""

    def test_uppercase_marker_still_matches(self):
        result = classify_with_telemetry("§16D ANERKENNUNG")
        self.assertEqual(result.slug, "aicha")

    def test_lowercase_marker_still_matches(self):
        result = classify_with_telemetry("blue card application")
        self.assertEqual(result.slug, "yusuf")


# ─── Defensive: None / non-string handling ──────────────────────


class DefensiveInputTests(unittest.TestCase):
    def test_none_input_treated_as_empty(self):
        # classify() docstring says str; defensive in case caller
        # passes a typed-Optional that ended up None.
        result = classify_with_telemetry(None)  # type: ignore[arg-type]
        self.assertEqual(result.slug, "")


if __name__ == "__main__":
    unittest.main()
