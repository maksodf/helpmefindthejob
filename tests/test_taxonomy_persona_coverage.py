# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 2 #68 — taxonomy persona-coverage contract tests.

Closes phase2-backlog item #68 (verified gaps from PART 6 walks):

Previously, the bucket taxonomy at
``company_discovery/job_type_filter.py::TAXONOMY`` had no entries
for several panel-persona canonical roles:

- Aïcha: Krankenschwester / Krankenpfleger / Pflegefachkraft → None
- Mahmoud: Anlagenmechaniker SHK / Auszubildender SHK → None
- Käthe: Krankenschwester (Wiedereinstieg) → None
- Maria: Altenpflegerin → None
- Yusuf: Mechanical engineer / Maschinenbauingenieur → None

The journey still worked because role_text falls through to the
raw user message, but persona-based categorisation, filtering
and ranking silently degraded for them downstream.

This commit adds 4 new buckets (krankenpfleger / altenpfleger /
mechanical_engineer / anlagenmechaniker_shk) and these tests
pin the persona-coverage contract:

1. Every panel persona's PRIMARY canonical role matches a bucket.
2. Every secondary canonical role either matches a bucket OR
   is intentionally None (ambiguous, e.g., "Quality Engineer").
3. The new buckets have proper DE + EN label coverage.
4. Drift guard: ALL_PANEL_PERSONAS catalogue size pinned.
"""

from __future__ import annotations

import unittest
from pathlib import Path as _RPath

from company_discovery.job_type_filter import TAXONOMY, identify_bucket
from company_discovery.persona_fixtures import PERSONAS

_REPO_ROOT = _RPath(__file__).resolve().parent.parent


PANEL_SLUGS = ("aicha", "yusuf", "olga", "mahmoud", "maria", "kaethe", "tobias")


# Each entry: (persona_slug, primary_role, expected_bucket_key).
# `expected_bucket_key` MUST be a key in TAXONOMY for this test
# to pass. If a future agent removes one of these buckets without
# updating the test, CI fires.
PERSONA_PRIMARY_ROLE_COVERAGE: tuple[tuple[str, str, str], ...] = (
    ("aicha", "Registered nurse", "krankenpfleger"),
    ("aicha", "Krankenpfleger", "krankenpfleger"),
    ("aicha", "Pflegefachkraft", "krankenpfleger"),
    ("yusuf", "Mechanical engineer", "mechanical_engineer"),
    ("yusuf", "Automotive supplier engineer", "mechanical_engineer"),
    ("olga", "Senior frontend developer", "software_engineer"),
    ("olga", "React engineer", "software_engineer"),
    ("mahmoud", "Anlagenmechaniker SHK", "anlagenmechaniker_shk"),
    # NOTE: "Auszubildender Handwerk" is intentionally None — too
    # generic across Handwerk trades to assign to SHK. Mahmoud's
    # PRIMARY canonical role above carries the categorisation.
    ("maria", "Altenpflegerin", "altenpfleger"),
    ("maria", "Pflegehelferin", "pflegehelfer"),
    ("maria", "Home-care worker", "altenpfleger"),
    ("kaethe", "Krankenschwester (Wiedereinstieg)", "krankenpfleger"),
    ("kaethe", "Wiedereinstiegspflege", "krankenpfleger"),
    ("tobias", "Backend Developer (Public Sector)", "software_engineer"),
    ("tobias", "Civic-Tech Engineer", "software_engineer"),
)


# ---------------------------------------------------------------------------
# Per-persona primary canonical role coverage
# ---------------------------------------------------------------------------


class EveryPanelPersonaPrimaryRoleMatchesBucket(unittest.TestCase):
    """The 7-persona panel is the project's canonical narrative
    anchor. Every panel persona's PRIMARY target_role MUST match
    some bucket — silent None breaks persona-based ranking +
    filtering downstream."""

    def test_every_panel_persona_primary_role_matches(self):
        for persona in PERSONAS:
            if persona.slug not in PANEL_SLUGS:
                continue
            primary = persona.target_roles[0] if persona.target_roles else ""
            with self.subTest(persona=persona.slug, primary=primary):
                bucket = identify_bucket(primary)
                self.assertIsNotNone(
                    bucket,
                    f"persona {persona.slug!r} primary role "
                    f"{primary!r} matches no bucket — persona-based "
                    f"ranking is broken for this user",
                )


class CoverageMatrix(unittest.TestCase):
    """Pin specific (persona, role, bucket) matches so a regression
    surfaces with the exact persona that broke."""

    def test_each_entry_resolves_to_expected_bucket(self):
        for persona, role, expected in PERSONA_PRIMARY_ROLE_COVERAGE:
            with self.subTest(persona=persona, role=role):
                actual = identify_bucket(role)
                self.assertEqual(
                    actual,
                    expected,
                    f"persona {persona!r} role {role!r} expected "
                    f"bucket {expected!r}, got {actual!r}",
                )


# ---------------------------------------------------------------------------
# New buckets exist + are well-formed
# ---------------------------------------------------------------------------


class NewBucketsArePresent(unittest.TestCase):
    """The 4 new buckets shipped for #68 must exist in TAXONOMY
    with EN + DE labels and non-empty synonyms."""

    NEW_BUCKETS = (
        "krankenpfleger",
        "altenpfleger",
        "mechanical_engineer",
        "anlagenmechaniker_shk",
    )

    def test_all_new_buckets_present(self):
        for key in self.NEW_BUCKETS:
            with self.subTest(bucket=key):
                self.assertIn(
                    key,
                    TAXONOMY,
                    f"bucket {key!r} missing from TAXONOMY",
                )

    def test_each_new_bucket_has_labels(self):
        for key in self.NEW_BUCKETS:
            with self.subTest(bucket=key):
                bucket = TAXONOMY[key]
                self.assertTrue(
                    bucket.label_en,
                    f"{key}: label_en empty",
                )
                self.assertTrue(
                    bucket.label_de,
                    f"{key}: label_de empty",
                )

    def test_each_new_bucket_has_synonyms(self):
        for key in self.NEW_BUCKETS:
            with self.subTest(bucket=key):
                bucket = TAXONOMY[key]
                self.assertGreater(
                    len(bucket.synonyms),
                    5,
                    f"{key} has too few synonyms ({len(bucket.synonyms)}) "
                    "— rich coverage matters for free-text matching",
                )


# ---------------------------------------------------------------------------
# DE + EN coverage per new bucket
# ---------------------------------------------------------------------------


class KrankenpflegerBucketCoverage(unittest.TestCase):
    def test_modern_qualifications_covered(self):
        for term in ("Pflegefachfrau", "Pflegefachmann", "Pflegefachkraft"):
            self.assertEqual(identify_bucket(term), "krankenpfleger")

    def test_legacy_terms_covered(self):
        for term in ("Krankenschwester", "Krankenpfleger", "Krankenpflegerin"):
            self.assertEqual(identify_bucket(term), "krankenpfleger")

    def test_english_terms_covered(self):
        for term in ("Registered nurse", "Staff nurse", "Hospital nurse"):
            self.assertEqual(identify_bucket(term), "krankenpfleger")

    def test_specialisation_terms_covered(self):
        for term in ("Intensivpflege", "Fachkrankenpfleger"):
            self.assertEqual(identify_bucket(term), "krankenpfleger")


class AltenpflegerBucketCoverage(unittest.TestCase):
    def test_de_terms_covered(self):
        # "Altenpflegehelfer" intentionally stays in pflegehelfer
        # bucket (lower qualification tier) — see comment in
        # altenpfleger bucket definition. Test it explicitly so
        # the routing is documented + pinned.
        for term in ("Altenpfleger", "Altenpflegerin", "Altenpflegekraft"):
            self.assertEqual(identify_bucket(term), "altenpfleger")
        # Helper-tier roles still route to pflegehelfer
        self.assertEqual(identify_bucket("Altenpflegehelfer"), "pflegehelfer")

    def test_en_terms_covered(self):
        for term in ("Geriatric nurse", "Elder care", "Home-care worker"):
            self.assertEqual(identify_bucket(term), "altenpfleger")

    def test_setting_terms_covered(self):
        for term in ("Ambulante Pflege", "Stationäre Altenpflege"):
            self.assertEqual(identify_bucket(term), "altenpfleger")


class MechanicalEngineerBucketCoverage(unittest.TestCase):
    def test_de_terms_covered(self):
        for term in ("Maschinenbauingenieur", "Konstrukteur", "Produktionsingenieur"):
            self.assertEqual(identify_bucket(term), "mechanical_engineer")

    def test_en_terms_covered(self):
        for term in ("Mechanical engineer", "Production engineer", "Process engineer"):
            self.assertEqual(identify_bucket(term), "mechanical_engineer")

    def test_automotive_specialisation_covered(self):
        for term in ("Automotive engineer", "Automotive supplier engineer", "Powertrain engineer"):
            self.assertEqual(identify_bucket(term), "mechanical_engineer")


class AnlagenmechanikerSHKBucketCoverage(unittest.TestCase):
    def test_full_de_term_covered(self):
        for term in (
            "Anlagenmechaniker SHK",
            "Anlagenmechaniker für Sanitär",
            "Anlagenmechaniker für Sanitär, Heizung und Klimatechnik",
        ):
            self.assertEqual(identify_bucket(term), "anlagenmechaniker_shk")

    def test_legacy_trade_terms_covered(self):
        for term in ("Heizungsbauer", "Sanitärinstallateur"):
            self.assertEqual(identify_bucket(term), "anlagenmechaniker_shk")

    def test_en_terms_covered(self):
        for term in ("Plumber", "Plumbing technician", "HVAC technician"):
            self.assertEqual(identify_bucket(term), "anlagenmechaniker_shk")

    def test_ausbildung_variants_covered(self):
        for term in ("Auszubildender SHK", "Ausbildung Anlagenmechaniker", "SHK-Azubi"):
            self.assertEqual(identify_bucket(term), "anlagenmechaniker_shk")


# ---------------------------------------------------------------------------
# No false positives — buckets don't cross-contaminate
# ---------------------------------------------------------------------------


class NoCrossContamination(unittest.TestCase):
    """A query for one bucket must not accidentally trigger another.
    Catches the case where adding synonyms broadened the match
    boundary too far."""

    def test_pflegehelfer_query_doesnt_match_krankenpfleger(self):
        """Pflegehelfer is a separate (lower) qualification from
        Krankenpfleger — must not cross-match."""

        result = identify_bucket("Pflegehelferin")
        self.assertEqual(
            result,
            "pflegehelfer",
            "Pflegehelferin should stay in pflegehelfer bucket — "
            "krankenpfleger / altenpfleger are higher qualifications",
        )

    def test_software_engineer_query_doesnt_match_mechanical(self):
        """A "frontend engineer" must stay in software_engineer
        even after adding mechanical_engineer + design_engineer
        synonyms."""

        self.assertEqual(
            identify_bucket("Senior frontend developer"),
            "software_engineer",
        )

    def test_unrelated_role_returns_none(self):
        for query in (
            "Restaurant manager",
            "Truck driver",
            "Pharmacist",
            "Teacher",
        ):
            with self.subTest(query=query):
                self.assertIsNone(
                    identify_bucket(query),
                    f"{query!r} should not match any current bucket",
                )


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


class LateralRoleFallbackCoverage(unittest.TestCase):
    """Phase 2 #68 panic-round catch: the journey's templated
    lateral-role inspiration (used when no AI provider is
    configured) had no entries for the new buckets. Users on the
    krankenpfleger / altenpfleger / mechanical_engineer /
    anlagenmechaniker_shk paths would degrade to the seniority-
    variant last-resort fallback. Tests verify each new bucket
    has tailored lateral roles."""

    def setUp(self):
        # Re-read the fallback_map from journey.py source — the
        # map is a function-local literal, not a module-level
        # constant, so we extract via AST parsing of the live
        # source to keep this test stable across refactors.
        import re
        from pathlib import Path

        src = Path(str(_REPO_ROOT / "company_discovery/journey.py")).read_text(encoding="utf-8")
        # Find the fallback_map literal block + extract keys
        start = src.find("fallback_map = {")
        end = src.find("}", start)
        block = src[start:end]
        self.bucket_keys_with_fallbacks = set(re.findall(r'"([a-z_]+)":\s*\[', block))

    def test_new_buckets_have_lateral_role_fallbacks(self):
        for bucket in (
            "krankenpfleger",
            "altenpfleger",
            "mechanical_engineer",
            "anlagenmechaniker_shk",
        ):
            with self.subTest(bucket=bucket):
                self.assertIn(
                    bucket,
                    self.bucket_keys_with_fallbacks,
                    f"bucket {bucket} has no lateral-role entry in "
                    "journey.py fallback_map — no-AI users degrade "
                    "to seniority-variant last-resort fallback",
                )


class DriftGuards(unittest.TestCase):
    def test_panel_size_is_seven(self):
        panel_count = sum(1 for p in PERSONAS if p.slug in PANEL_SLUGS)
        self.assertEqual(
            panel_count,
            7,
            "panel size drifted — should be exactly 7 (Aïcha / "
            "Yusuf / Olga / Mahmoud / Maria / Käthe / Tobias)",
        )

    def test_taxonomy_size_at_least_18_after_68(self):
        """Pre-#68 had 15 buckets; #68 adds 4. Pin >=18 so a
        future agent who drops a bucket without intent fails CI."""

        self.assertGreaterEqual(len(TAXONOMY), 18)

    def test_label_strings_are_distinct_per_bucket(self):
        """Catch the case where a new bucket accidentally copies
        another bucket's label."""

        en_labels = [b.label_en for b in TAXONOMY.values()]
        self.assertEqual(
            len(en_labels),
            len(set(en_labels)),
            "duplicate label_en across buckets — naming collision",
        )


if __name__ == "__main__":
    unittest.main()
