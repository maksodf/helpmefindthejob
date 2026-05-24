# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for ``company_discovery.visa_status_flags``.

Closes phase2-backlog item #73. Tests cover:

1. Per-flag detection — every flag in ALL_FLAGS has at least one
   pattern that triggers it from a realistic JD snippet.
2. Evidence surfacing — every detected flag carries the matched
   substring verbatim.
3. Multi-flag detection — a JD with 2+ accommodations surfaces
   both.
4. Polarity — positive flags (accommodation) vs negative flags
   (barrier) classified correctly.
5. Friction-class compatibility — has_barrier_for_class +
   matches_preferred_for_class against the 7-persona panel.
6. Annotator — stamps job.raw["visaStatusFlags"]; skips silent
   jobs; resilient to None/missing raw.
7. Drift guards on ALL_FLAGS catalogue size + label coverage.
"""

from __future__ import annotations

import unittest

from company_discovery.visa_status_flags import (
    ALL_FLAGS,
    FLAG_ANERKENNUNG_FRIENDLY,
    FLAG_AUSBILDUNG_CLASS,
    FLAG_BLUE_CARD_OK,
    FLAG_EU_CITIZENS_ONLY,
    FLAG_HUMANITARIAN_PATHWAY,
    FLAG_LABELS,
    FLAG_PARAGRAPH_16D,
    FLAG_PERMANENT_RESIDENCE_REQUIRED,
    FLAG_WIEDEREINSTIEG_FRIENDLY,
    FRICTION_CLASS_BARRIER_FLAGS,
    FRICTION_CLASS_PREFERRED_FLAGS,
    NEGATIVE_FLAGS,
    POSITIVE_FLAGS,
    VisaStatusFlag,
    annotate_jobs_with_visa_status_flags,
    detect_visa_status_flags,
    has_barrier_for_class,
    matches_preferred_for_class,
)


class _MockJob:
    def __init__(self, description: str, raw: dict | None = None):
        self.description = description
        self.raw = raw if raw is not None else {}


# ---------------------------------------------------------------------------
# Per-flag detection
# ---------------------------------------------------------------------------


class AnerkennungFlagDetection(unittest.TestCase):
    def test_anerkennungs_freundlich_detected(self):
        flags = detect_visa_status_flags(
            "Wir sind Anerkennungs-freundlich und unterstützen den Prozess."
        )
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_ANERKENNUNG_FRIENDLY, slugs)

    def test_anerkennungspartner_detected(self):
        flags = detect_visa_status_flags("Klinik ist offizieller Anerkennungspartner.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_ANERKENNUNG_FRIENDLY, slugs)

    def test_supports_anerkennung_detected(self):
        flags = detect_visa_status_flags("We support Anerkennung for international nurses.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_ANERKENNUNG_FRIENDLY, slugs)


class BlueCardFlagDetection(unittest.TestCase):
    def test_eu_blue_card_detected(self):
        flags = detect_visa_status_flags("EU Blue Card sponsorship available.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_BLUE_CARD_OK, slugs)

    def test_blaue_karte_detected(self):
        flags = detect_visa_status_flags(
            "Unterstützung bei der Blauen Karte EU für hochqualifizierte Bewerber."
        )
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_BLUE_CARD_OK, slugs)

    def test_paragraph_18b_detected(self):
        flags = detect_visa_status_flags("Aufenthaltstitel nach §18b AufenthG möglich.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_BLUE_CARD_OK, slugs)


class WiedereinstiegFlagDetection(unittest.TestCase):
    def test_wiedereinstieg_detected(self):
        flags = detect_visa_status_flags(
            "Wiedereinstieg nach Familienzeit ausdrücklich willkommen."
        )
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_WIEDEREINSTIEG_FRIENDLY, slugs)

    def test_wiedereinsteigerinnen_detected(self):
        flags = detect_visa_status_flags("Wiedereinsteigerinnen sind herzlich willkommen.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_WIEDEREINSTIEG_FRIENDLY, slugs)

    def test_career_returner_detected(self):
        flags = detect_visa_status_flags("Career returners welcome — after career break.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_WIEDEREINSTIEG_FRIENDLY, slugs)


class AusbildungFlagDetection(unittest.TestCase):
    def test_ausbildung_zur_detected(self):
        flags = detect_visa_status_flags("Ausbildung zur Pflegefachkraft, Start September 2026.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_AUSBILDUNG_CLASS, slugs)

    def test_apprenticeship_detected(self):
        flags = detect_visa_status_flags("Apprenticeship program for school leavers.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_AUSBILDUNG_CLASS, slugs)

    def test_duale_ausbildung_detected(self):
        flags = detect_visa_status_flags("Wir bieten eine duale Ausbildung mit Hochschulabschluss.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_AUSBILDUNG_CLASS, slugs)


class Paragraph16DDetection(unittest.TestCase):
    def test_paragraph_16d_detected(self):
        flags = detect_visa_status_flags(
            "Stellenangebot für Pflegekräfte im §16d AufenthG-Verfahren."
        )
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_PARAGRAPH_16D, slugs)

    def test_section_16d_alone_detected(self):
        flags = detect_visa_status_flags("§ 16d residence permit holders welcome.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_PARAGRAPH_16D, slugs)


class HumanitarianPathwayDetection(unittest.TestCase):
    def test_paragraph_24_detected(self):
        flags = detect_visa_status_flags("Stelle für Personen mit Aufenthalt nach §24 AufenthG.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_HUMANITARIAN_PATHWAY, slugs)

    def test_paragraph_4_asyl_detected(self):
        flags = detect_visa_status_flags("Beschäftigung möglich nach §4 AsylG.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_HUMANITARIAN_PATHWAY, slugs)

    def test_temporary_protection_detected(self):
        flags = detect_visa_status_flags("Open to Ukrainian refugees under temporary protection.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_HUMANITARIAN_PATHWAY, slugs)


class EuCitizensOnlyDetection(unittest.TestCase):
    def test_eu_citizens_only_detected(self):
        flags = detect_visa_status_flags("Position open to EU citizens only — no sponsorship.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_EU_CITIZENS_ONLY, slugs)

    def test_nur_fuer_eu_buerger_detected(self):
        flags = detect_visa_status_flags("Stelle nur für EU-Bürger ausgeschrieben.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_EU_CITIZENS_ONLY, slugs)


class PermanentResidenceDetection(unittest.TestCase):
    def test_permanent_residence_required_detected(self):
        flags = detect_visa_status_flags("Permanent residency required — no work-visa sponsorship.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_PERMANENT_RESIDENCE_REQUIRED, slugs)

    def test_niederlassungserlaubnis_detected(self):
        flags = detect_visa_status_flags("Niederlassungserlaubnis erforderlich für diese Position.")
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_PERMANENT_RESIDENCE_REQUIRED, slugs)


# ---------------------------------------------------------------------------
# Evidence surfacing
# ---------------------------------------------------------------------------


class EvidenceSurfacing(unittest.TestCase):
    def test_evidence_is_verbatim_from_description(self):
        description = "Wir sind Anerkennungs-freundlich für internationale Bewerber."
        flags = detect_visa_status_flags(description)
        for f in flags:
            for ev in f.evidence:
                self.assertIn(
                    ev.lower(),
                    description.lower(),
                    f"evidence {ev!r} not verbatim from description",
                )

    def test_all_detected_flags_carry_evidence(self):
        flags = detect_visa_status_flags("EU Blue Card sponsorship + Anerkennungs-friendly clinic.")
        for f in flags:
            self.assertGreater(
                len(f.evidence),
                0,
                f"flag {f.slug} has no evidence",
            )


# ---------------------------------------------------------------------------
# Multi-flag + polarity
# ---------------------------------------------------------------------------


class MultiFlagDetection(unittest.TestCase):
    def test_multiple_flags_can_coexist(self):
        flags = detect_visa_status_flags(
            "Wir sind Anerkennungs-freundlich und unterstützen §16d AufenthG."
        )
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_ANERKENNUNG_FRIENDLY, slugs)
        self.assertIn(FLAG_PARAGRAPH_16D, slugs)

    def test_positive_and_negative_can_coexist(self):
        """Edge case: a JD that says "Anerkennung-friendly for EU
        nationals only" carries both a positive AND a negative
        flag. Both should surface."""

        flags = detect_visa_status_flags(
            "Anerkennungs-freundlich, position open to EU citizens only."
        )
        slugs = {f.slug for f in flags}
        self.assertIn(FLAG_ANERKENNUNG_FRIENDLY, slugs)
        self.assertIn(FLAG_EU_CITIZENS_ONLY, slugs)

    def test_returned_list_is_ordered_by_ALL_FLAGS(self):
        """Determinism: the returned list follows ALL_FLAGS ordering
        so downstream tooling can rely on stable iteration."""

        flags = detect_visa_status_flags("Ausbildung in Pflege; Anerkennung-friendly clinic.")
        slugs_in_order = [f.slug for f in flags]
        # Anerkennung comes before Ausbildung in ALL_FLAGS
        idx_a = ALL_FLAGS.index(FLAG_ANERKENNUNG_FRIENDLY)
        idx_b = ALL_FLAGS.index(FLAG_AUSBILDUNG_CLASS)
        self.assertLess(idx_a, idx_b)
        # Therefore Anerkennung must appear first in detected list
        if FLAG_ANERKENNUNG_FRIENDLY in slugs_in_order and FLAG_AUSBILDUNG_CLASS in slugs_in_order:
            self.assertLess(
                slugs_in_order.index(FLAG_ANERKENNUNG_FRIENDLY),
                slugs_in_order.index(FLAG_AUSBILDUNG_CLASS),
            )


class PolarityClassification(unittest.TestCase):
    def test_positive_flags_classified_correctly(self):
        for slug in POSITIVE_FLAGS:
            with self.subTest(slug=slug):
                f = VisaStatusFlag(slug=slug, evidence=["x"])
                self.assertTrue(f.is_positive())
                self.assertFalse(f.is_negative())

    def test_negative_flags_classified_correctly(self):
        for slug in NEGATIVE_FLAGS:
            with self.subTest(slug=slug):
                f = VisaStatusFlag(slug=slug, evidence=["x"])
                self.assertTrue(f.is_negative())
                self.assertFalse(f.is_positive())

    def test_positive_and_negative_are_disjoint(self):
        self.assertEqual(POSITIVE_FLAGS & NEGATIVE_FLAGS, frozenset())

    def test_every_flag_has_a_polarity_or_is_neutral(self):
        for slug in ALL_FLAGS:
            with self.subTest(slug=slug):
                self.assertTrue(
                    slug in POSITIVE_FLAGS or slug in NEGATIVE_FLAGS,
                    f"flag {slug} has no polarity assignment",
                )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class EdgeCases(unittest.TestCase):
    def test_empty_returns_silent(self):
        self.assertEqual(detect_visa_status_flags(""), [])

    def test_none_returns_silent(self):
        self.assertEqual(detect_visa_status_flags(None), [])

    def test_no_signal_returns_silent(self):
        flags = detect_visa_status_flags("Software-Entwickler gesucht, Berlin, 38h/Woche.")
        self.assertEqual(flags, [])


# ---------------------------------------------------------------------------
# Friction-class compatibility
# ---------------------------------------------------------------------------


class FrictionClassBarriers(unittest.TestCase):
    def test_aicha_blocked_by_eu_citizens_only(self):
        flags = [VisaStatusFlag(slug=FLAG_EU_CITIZENS_ONLY, evidence=["EU citizens only"])]
        self.assertTrue(has_barrier_for_class(flags, "aicha"))

    def test_yusuf_blocked_by_eu_citizens_only(self):
        flags = [VisaStatusFlag(slug=FLAG_EU_CITIZENS_ONLY, evidence=["EU citizens only"])]
        self.assertTrue(has_barrier_for_class(flags, "yusuf"))

    def test_maria_not_blocked_by_anything(self):
        """Maria is an EU citizen — no visa barriers apply."""

        flags = [
            VisaStatusFlag(slug=FLAG_EU_CITIZENS_ONLY, evidence=["x"]),
            VisaStatusFlag(slug=FLAG_PERMANENT_RESIDENCE_REQUIRED, evidence=["x"]),
        ]
        self.assertFalse(has_barrier_for_class(flags, "maria"))

    def test_kaethe_not_blocked_by_anything(self):
        """Käthe is a German citizen returning from career break."""

        flags = [VisaStatusFlag(slug=FLAG_EU_CITIZENS_ONLY, evidence=["x"])]
        self.assertFalse(has_barrier_for_class(flags, "kaethe"))

    def test_unknown_class_not_blocked(self):
        flags = [VisaStatusFlag(slug=FLAG_EU_CITIZENS_ONLY, evidence=["x"])]
        self.assertFalse(has_barrier_for_class(flags, "unknown_persona"))

    def test_no_barriers_when_no_negative_flags(self):
        flags = [VisaStatusFlag(slug=FLAG_ANERKENNUNG_FRIENDLY, evidence=["x"])]
        self.assertFalse(has_barrier_for_class(flags, "aicha"))


class FrictionClassPreferences(unittest.TestCase):
    def test_aicha_matches_anerkennung(self):
        flags = [VisaStatusFlag(slug=FLAG_ANERKENNUNG_FRIENDLY, evidence=["x"])]
        self.assertTrue(matches_preferred_for_class(flags, "aicha"))

    def test_yusuf_matches_blue_card(self):
        flags = [VisaStatusFlag(slug=FLAG_BLUE_CARD_OK, evidence=["x"])]
        self.assertTrue(matches_preferred_for_class(flags, "yusuf"))

    def test_kaethe_matches_wiedereinstieg(self):
        flags = [VisaStatusFlag(slug=FLAG_WIEDEREINSTIEG_FRIENDLY, evidence=["x"])]
        self.assertTrue(matches_preferred_for_class(flags, "kaethe"))

    def test_maria_matches_no_flag(self):
        """Maria has no visa friction — no preferred flags."""

        flags = [VisaStatusFlag(slug=FLAG_ANERKENNUNG_FRIENDLY, evidence=["x"])]
        self.assertFalse(matches_preferred_for_class(flags, "maria"))

    def test_unrelated_flag_doesnt_match(self):
        flags = [VisaStatusFlag(slug=FLAG_EU_CITIZENS_ONLY, evidence=["x"])]
        self.assertFalse(matches_preferred_for_class(flags, "yusuf"))


# ---------------------------------------------------------------------------
# Annotator
# ---------------------------------------------------------------------------


class AnnotatorBehaviour(unittest.TestCase):
    def test_annotator_stamps_flags_on_raw(self):
        jobs = [_MockJob("Anerkennungs-freundlich, EU Blue Card supported.")]
        annotate_jobs_with_visa_status_flags(jobs)
        self.assertIn("visaStatusFlags", jobs[0].raw)
        slugs = [f["slug"] for f in jobs[0].raw["visaStatusFlags"]]
        self.assertIn(FLAG_ANERKENNUNG_FRIENDLY, slugs)
        self.assertIn(FLAG_BLUE_CARD_OK, slugs)

    def test_annotator_skips_silent_jobs(self):
        jobs = [_MockJob("Standard developer role, no special accommodation.")]
        annotate_jobs_with_visa_status_flags(jobs)
        self.assertNotIn("visaStatusFlags", jobs[0].raw)

    def test_annotator_resilient_to_missing_raw(self):
        class _BadJob:
            description = "Anerkennungs-freundlich clinic."
            raw = None

        jobs = [_BadJob()]
        # Must not raise
        annotate_jobs_with_visa_status_flags(jobs)

    def test_annotator_mutates_in_place_and_returns_list(self):
        jobs = [_MockJob("Anerkennungs-freundlich.")]
        result = annotate_jobs_with_visa_status_flags(jobs)
        self.assertIs(result, jobs)

    def test_annotator_payload_carries_polarity(self):
        jobs = [_MockJob("EU citizens only.")]
        annotate_jobs_with_visa_status_flags(jobs)
        entry = jobs[0].raw["visaStatusFlags"][0]
        self.assertEqual(entry["polarity"], "negative")
        self.assertEqual(entry["slug"], FLAG_EU_CITIZENS_ONLY)
        self.assertIn("evidence", entry)


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


class DriftGuards(unittest.TestCase):
    def test_all_flags_have_labels(self):
        for slug in ALL_FLAGS:
            with self.subTest(slug=slug):
                self.assertIn(slug, FLAG_LABELS)
                self.assertNotEqual(FLAG_LABELS[slug], "")

    def test_all_friction_classes_have_preferred_set(self):
        for class_slug in ("aicha", "yusuf", "olga", "mahmoud", "maria", "kaethe", "tobias"):
            with self.subTest(class_slug=class_slug):
                self.assertIn(class_slug, FRICTION_CLASS_PREFERRED_FLAGS)
                self.assertIn(class_slug, FRICTION_CLASS_BARRIER_FLAGS)

    def test_all_flags_size_is_eight(self):
        """Pin the catalogue size — if a new flag is added,
        force the maintainer to update the test suite to cover it."""

        self.assertEqual(len(ALL_FLAGS), 8)


if __name__ == "__main__":
    unittest.main()
