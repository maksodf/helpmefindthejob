# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for ``company_discovery.language_requirement``.

Closes phase2-backlog item #72.

Tests cover:
1. **Per-level detection** — each CEFR rung (B1+ / B2+ / C1+ /
   native) matches the canonical phrasings.
2. **Evidence surfacing** — the matched substring is returned
   verbatim so the user can verify the inference.
3. **Bilingual detection** — JDs requiring both DE + EN surface
   both signals.
4. **Edge cases** — empty / None / very short descriptions return
   silent results (no false positives).
5. **Annotator behaviour** — annotate_jobs_with_language_requirement
   stamps the result on job.raw, leaves malformed jobs unchanged.
6. **level_at_or_above** ladder logic — powers the
   loosen_language widening affordance.
"""

from __future__ import annotations

import unittest

from company_discovery.language_requirement import (
    LEVEL_ORDER,
    LanguageRequirement,
    annotate_jobs_with_language_requirement,
    detect_language_requirement,
    level_at_or_above,
)


# Mock AggregatedJob shape for annotator tests
class _MockJob:
    def __init__(self, description: str, raw: dict | None = None):
        self.description = description
        self.raw = raw if raw is not None else {}


# ---------------------------------------------------------------------------
# Per-level DE detection
# ---------------------------------------------------------------------------


class DeNativeLevelDetection(unittest.TestCase):
    def test_muttersprachler_detected(self):
        req = detect_language_requirement(
            "Wir suchen einen erfahrenen Pflegekräfte (m/w/d), Muttersprachler."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "native")
        self.assertTrue(any("muttersprachler" in ev.lower() for ev in req.evidence))

    def test_native_german_speaker_detected(self):
        req = detect_language_requirement(
            "Native German speaker required for client-facing role."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "native")


class DeC1LevelDetection(unittest.TestCase):
    def test_verhandlungssicher_detected(self):
        req = detect_language_requirement(
            "Sie bringen verhandlungssicheres Deutsch mit."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "C1+")
        self.assertTrue(any("verhandlungssicher" in ev.lower() for ev in req.evidence))

    def test_fliessend_deutsch_detected(self):
        req = detect_language_requirement(
            "Anforderungen: Fließend Deutsch in Wort und Schrift."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "C1+")

    def test_c1_explicit_detected(self):
        req = detect_language_requirement(
            "Sehr gute Deutschkenntnisse (C1) erforderlich."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "C1+")


class DeB2LevelDetection(unittest.TestCase):
    def test_b2_explicit_detected(self):
        req = detect_language_requirement(
            "Wir erwarten Deutsch B2."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "B2+")

    def test_b2_dash_form_detected(self):
        req = detect_language_requirement("B2-Deutsch erforderlich.")
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "B2+")


class DeB1LevelDetection(unittest.TestCase):
    def test_b1_explicit_detected(self):
        req = detect_language_requirement(
            "Deutsch B1 ist ausreichend für den Start."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "B1+")

    def test_grundkenntnisse_deutsch_detected(self):
        req = detect_language_requirement(
            "Vorteilhaft: Grundkenntnisse Deutsch."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "B1+")


class DeUnscopedRequiredDetection(unittest.TestCase):
    def test_deutsch_erforderlich_defaults_to_b2(self):
        """DACH labour-market convention: unscoped "Deutsch
        erforderlich" defaults to B2+ per Bundesagentur für Arbeit
        guidance."""

        req = detect_language_requirement(
            "Folgende Voraussetzungen: Deutsch erforderlich."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "B2+")


# ---------------------------------------------------------------------------
# Per-level EN detection
# ---------------------------------------------------------------------------


class EnLevelDetection(unittest.TestCase):
    def test_native_english_speaker_detected(self):
        req = detect_language_requirement(
            "Looking for a native English speaker — client work in London."
        )
        self.assertEqual(req.language, "en")
        self.assertEqual(req.level, "native")

    def test_fluent_english_detected(self):
        req = detect_language_requirement(
            "Fluent in English is essential for this role."
        )
        self.assertEqual(req.language, "en")
        self.assertEqual(req.level, "C1+")

    def test_good_english_detected(self):
        req = detect_language_requirement(
            "Good English required for daily standups."
        )
        self.assertEqual(req.language, "en")
        self.assertEqual(req.level, "B2+")

    def test_basic_english_detected(self):
        req = detect_language_requirement(
            "Basic English helpful but not required for daily standups."
        )
        self.assertEqual(req.language, "en")
        self.assertEqual(req.level, "B1+")


# ---------------------------------------------------------------------------
# Bilingual + edge cases
# ---------------------------------------------------------------------------


class BilingualDetection(unittest.TestCase):
    def test_de_and_en_both_required(self):
        req = detect_language_requirement(
            "Erforderlich: verhandlungssicheres Deutsch UND fluent English."
        )
        # Both C1+ — primary tie-broken to DE (DACH-focus heuristic)
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "C1+")
        # English evidence appears too, prefixed with "+ EN:"
        en_evidence = [ev for ev in req.evidence if ev.startswith("+ EN:")]
        self.assertGreater(len(en_evidence), 0)

    def test_de_higher_than_en_picks_de(self):
        req = detect_language_requirement(
            "Native German required. Basic English helpful."
        )
        self.assertEqual(req.language, "de")
        self.assertEqual(req.level, "native")

    def test_en_higher_than_de_picks_en(self):
        req = detect_language_requirement(
            "Native English speaker. Grundkenntnisse Deutsch helpful."
        )
        self.assertEqual(req.language, "en")
        self.assertEqual(req.level, "native")


class EdgeCases(unittest.TestCase):
    def test_empty_description_returns_silent(self):
        req = detect_language_requirement("")
        self.assertTrue(req.is_silent())

    def test_none_description_returns_silent(self):
        req = detect_language_requirement(None)
        self.assertTrue(req.is_silent())

    def test_no_language_signal_returns_silent(self):
        """A JD with no language-requirement phrasing must not
        false-positive. Doctrine: silent > guessing."""

        req = detect_language_requirement(
            "Wir suchen einen Softwareentwickler. Standort Berlin. "
            "Vollzeit, 38h/Woche, ab sofort."
        )
        self.assertTrue(req.is_silent())

    def test_very_short_description_returns_silent(self):
        req = detect_language_requirement("dev role")
        self.assertTrue(req.is_silent())

    def test_unrelated_b1_b2_text_does_not_false_positive(self):
        """The B1 / B2 tokens appear in non-language contexts too
        (e.g., highway B1, vitamin B2). Without the language
        anchor they must not trigger language detection."""

        req = detect_language_requirement(
            "Onsite location near the B1 highway. Vitamin B2 included."
        )
        self.assertTrue(req.is_silent())


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class ConfidenceScoring(unittest.TestCase):
    def test_high_confidence_with_multiple_evidence(self):
        req = detect_language_requirement(
            "Verhandlungssicheres Deutsch und fließend Deutsch erforderlich."
        )
        self.assertEqual(req.confidence, "high")

    def test_medium_confidence_with_single_c1_evidence(self):
        req = detect_language_requirement(
            "Verhandlungssichere Deutschkenntnisse."
        )
        self.assertEqual(req.confidence, "medium")

    def test_low_confidence_with_single_b1_evidence(self):
        req = detect_language_requirement(
            "Grundkenntnisse Deutsch sind nützlich."
        )
        # Single B1 match → low (no C1+ specificity)
        self.assertEqual(req.confidence, "low")


# ---------------------------------------------------------------------------
# Evidence surfacing — doctrinal constraint
# ---------------------------------------------------------------------------


class EvidenceSurfacing(unittest.TestCase):
    """The doctrine: detection must be evidence-backed. The user
    sees the matched phrase verbatim so they can verify."""

    def test_evidence_is_verbatim_from_description(self):
        description = "Wir erwarten verhandlungssicheres Deutsch."
        req = detect_language_requirement(description)
        self.assertTrue(
            any(ev.lower() in description.lower() for ev in req.evidence),
            f"evidence {req.evidence!r} must be verbatim from description",
        )

    def test_evidence_is_non_empty_when_level_is_detected(self):
        req = detect_language_requirement("Fluent English required.")
        self.assertFalse(req.is_silent())
        self.assertGreater(len(req.evidence), 0)


# ---------------------------------------------------------------------------
# Annotator
# ---------------------------------------------------------------------------


class AnnotatorBehaviour(unittest.TestCase):
    def test_annotator_stamps_requirement_on_raw(self):
        jobs = [_MockJob("Verhandlungssicheres Deutsch erforderlich.")]
        annotate_jobs_with_language_requirement(jobs)
        self.assertIn("languageRequirement", jobs[0].raw)
        self.assertEqual(jobs[0].raw["languageRequirement"]["language"], "de")
        self.assertEqual(jobs[0].raw["languageRequirement"]["level"], "C1+")

    def test_annotator_skips_silent_jobs(self):
        jobs = [_MockJob("Just a job description with no language signal.")]
        annotate_jobs_with_language_requirement(jobs)
        self.assertNotIn("languageRequirement", jobs[0].raw)

    def test_annotator_skips_jobs_with_none_raw(self):
        """If raw is None (some aggregators), don't crash; just
        skip annotation."""

        class _BadJob:
            description = "Fluent English required."
            raw = None
        jobs = [_BadJob()]
        # Must not raise
        annotate_jobs_with_language_requirement(jobs)

    def test_annotator_mutates_in_place_and_returns_list(self):
        jobs = [_MockJob("Native German required.")]
        result = annotate_jobs_with_language_requirement(jobs)
        self.assertIs(result, jobs)  # same list, fluent chaining

    def test_annotator_handles_missing_description(self):
        class _NoDesc:
            description = None
            raw = {}
        jobs = [_NoDesc()]
        annotate_jobs_with_language_requirement(jobs)
        self.assertNotIn("languageRequirement", jobs[0].raw)


# ---------------------------------------------------------------------------
# level_at_or_above ladder logic
# ---------------------------------------------------------------------------


class LevelAtOrAbove(unittest.TestCase):
    def test_user_higher_than_required_returns_true(self):
        self.assertTrue(level_at_or_above(detected_level="B1+", user_level="C1+"))

    def test_user_equal_to_required_returns_true(self):
        self.assertTrue(level_at_or_above(detected_level="B2+", user_level="B2+"))

    def test_user_lower_than_required_returns_false(self):
        self.assertFalse(level_at_or_above(detected_level="C1+", user_level="B1+"))

    def test_unscoped_requirement_returns_true_for_any_user_level(self):
        self.assertTrue(level_at_or_above(detected_level="", user_level="A2+"))
        self.assertTrue(level_at_or_above(detected_level="", user_level="native"))

    def test_unscoped_user_returns_false(self):
        """A user with no declared level can't prove capability."""

        self.assertFalse(level_at_or_above(detected_level="B1+", user_level=""))

    def test_unknown_level_returns_false(self):
        self.assertFalse(level_at_or_above(detected_level="garbage", user_level="C1+"))


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


class DriftGuards(unittest.TestCase):
    def test_level_order_has_expected_rungs(self):
        """If LEVEL_ORDER changes, downstream callers (UI labels,
        loosen_language affordance) may need updates. Pin the
        invariant."""

        self.assertEqual(
            LEVEL_ORDER,
            ("", "A1+", "A2+", "B1+", "B2+", "C1+", "C2+", "native"),
        )

    def test_silent_requirement_is_silent(self):
        self.assertTrue(LanguageRequirement().is_silent())

    def test_filled_requirement_is_not_silent(self):
        req = LanguageRequirement(language="de", level="C1+", evidence=["x"], confidence="high")
        self.assertFalse(req.is_silent())


if __name__ == "__main__":
    unittest.main()
