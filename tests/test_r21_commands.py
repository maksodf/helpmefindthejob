# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Tests for the R21 commands + their structural invariants.

R21 added 5 fixes; this file is the gap I admitted to — no per-fix
tests existed. These run against the in-memory registries and the
helper functions directly so they're cheap + deterministic.
"""

from __future__ import annotations

import unittest
from typing import ClassVar

from company_discovery.chat_router import REGISTRY
from company_discovery.job_type_filter import (
    BUCKET_TO_PERSONA,
    TAXONOMY,
    filter_malformed_jobs,
    looks_malformed,
    persona_for_bucket,
)


class TaxonomyExpansionTests(unittest.TestCase):
    """The 10 new buckets all exist + carry the right shape."""

    EXPECTED_BUCKETS: ClassVar[set[str]] = {
        "software_engineer",
        "data_engineer",
        "product_manager",
        "designer",
        "marketing",
        "sales",
        "finance",
        "consulting",
        "customer_success",
        "healthcare_management",
        # Legacy hospitality / care buckets.
        "bartender",
        "barista",
        "cafe_worker",
        "pflegehelfer",
        # Phase 2 #68 (2026-05-22): panel-persona coverage buckets.
        # Added for Aïcha + Käthe (krankenpfleger),
        # Maria (altenpfleger), Yusuf (mechanical_engineer),
        # Mahmoud (anlagenmechaniker_shk). See
        # tests/test_taxonomy_persona_coverage.py for the contract.
        "krankenpfleger",
        "altenpfleger",
        "mechanical_engineer",
        "anlagenmechaniker_shk",
        "waiter",
    }

    def test_all_buckets_present(self):
        self.assertEqual(set(TAXONOMY), self.EXPECTED_BUCKETS)

    def test_every_bucket_has_synonyms(self):
        for key, bucket in TAXONOMY.items():
            self.assertGreaterEqual(len(bucket.synonyms), 3, msg=key)
            self.assertTrue(bucket.label_en.strip(), msg=key)
            self.assertTrue(bucket.label_de.strip(), msg=key)


class PersonaForBucketTests(unittest.TestCase):
    """Auto-persona switching maps every tech-adjacent bucket to a
    real persona in the PERSONAS registry."""

    def test_every_mapped_persona_exists(self):
        from company_discovery.personas import PERSONAS

        for bucket_key, persona_id in BUCKET_TO_PERSONA.items():
            self.assertIn(
                persona_id,
                PERSONAS,
                msg=f"bucket {bucket_key} maps to missing persona {persona_id}",
            )

    def test_hospitality_buckets_intentionally_unmapped(self):
        # bartender / barista / cafe_worker / waiter have no
        # dedicated persona — the bucket filter does the narrowing.
        # Leaving the user's existing persona alone is intentional.
        for key in ("bartender", "barista", "cafe_worker", "waiter"):
            self.assertIsNone(persona_for_bucket(key), msg=f"{key} should not auto-flip persona")

    def test_software_engineer_maps_to_tech(self):
        self.assertEqual(persona_for_bucket("software_engineer"), "tech")

    def test_pflegehelfer_maps_to_healthcare_clinical(self):
        self.assertEqual(persona_for_bucket("pflegehelfer"), "healthcare-clinical")

    def test_unknown_bucket_returns_none(self):
        self.assertIsNone(persona_for_bucket(""))
        self.assertIsNone(persona_for_bucket(None))
        self.assertIsNone(persona_for_bucket("astronaut"))


class AggregatorSanityTests(unittest.TestCase):
    """filter_malformed_jobs drops the obviously-broken aggregator
    rows the user actually saw on prod."""

    def test_title_that_is_actually_a_location_dropped(self):
        # The exact pattern we saw on prod 0.78.0.
        bad = {
            "title": "Bangalore, India",
            "company": "HackerRank",
            "location": "Senior/Lead Devops Engineer, Lead SDET",
            "url": "https://news.ycombinator.com/item?id=22665806",
        }
        self.assertTrue(looks_malformed(bad))
        self.assertEqual(filter_malformed_jobs([bad]), [])

    def test_location_that_is_actually_a_title_dropped(self):
        bad = {
            "title": "Acme",
            "company": "Acme",
            "location": "Senior Backend Engineer (Remote)",
            "url": "https://acme.example/jobs/1",
        }
        self.assertTrue(looks_malformed(bad))

    def test_bare_city_in_title_dropped(self):
        bad = {
            "title": "Berlin",
            "company": "X",
            "location": "X",
            "url": "https://x.com",
        }
        self.assertTrue(looks_malformed(bad))

    def test_non_http_url_dropped(self):
        bad = {
            "title": "Bartender",
            "company": "Bar",
            "location": "Berlin",
            "url": "javascript:alert(1)",
        }
        self.assertTrue(looks_malformed(bad))

    def test_missing_title_dropped(self):
        bad = {"title": "", "company": "X", "location": "Berlin", "url": "https://x.com"}
        self.assertTrue(looks_malformed(bad))

    def test_clean_job_passes(self):
        good = {
            "title": "Bartender (m/w/d)",
            "company": "Berliner Bar",
            "location": "Berlin",
            "url": "https://berliner-bar.de/jobs/1",
        }
        self.assertFalse(looks_malformed(good))
        self.assertEqual(filter_malformed_jobs([good]), [good])

    def test_mixed_list_filters_correctly(self):
        jobs = [
            {"title": "Berlin", "company": "X", "location": "Y", "url": "https://x"},
            {
                "title": "Bartender",
                "company": "Bar",
                "location": "Berlin",
                "url": "https://bar.example/1",
            },
            {
                "title": "Pflegehelfer",
                "company": "Charité",
                "location": "Senior Lead Manager",
                "url": "https://x",
            },
        ]
        kept = filter_malformed_jobs(jobs)
        self.assertEqual([j["title"] for j in kept], ["Bartender"])


class DeleteAccountCommandTests(unittest.TestCase):
    """The R21 delete_account chat command exists with the right
    safety shape — requires email confirmation + the global
    confirmation gate."""

    def test_command_registered(self):
        self.assertIn("delete_account", REGISTRY)

    def test_requires_email_param(self):
        cmd = REGISTRY["delete_account"]
        param_names = {p.name for p in cmd.params}
        self.assertIn("email", param_names)

    def test_destructive_action_keeps_confirmation_gate(self):
        # Unlike find_jobs / help / show_view, delete_account MUST
        # require the yes/no confirmation prompt — it's destructive
        # and irreversible after the 14-day window.
        cmd = REGISTRY["delete_account"]
        self.assertTrue(cmd.requires_confirmation)

    def test_dsgvo_keyword_routes(self):
        from company_discovery.chat_router import keyword_route

        # German DSGVO triggers should route to delete_account.
        self.assertEqual(
            keyword_route("DSGVO Löschung meines Kontos bitte"),
            "delete_account",
        )

    def test_english_routes(self):
        from company_discovery.chat_router import keyword_route

        self.assertEqual(
            keyword_route("delete my account"),
            "delete_account",
        )


class CommandRegistryShapeTests(unittest.TestCase):
    def test_21_commands(self):
        # If you add or remove a command, update this number and
        # the explicit list in test_chat_router.py too. Phase 2 #76
        # sub-piece (a) added friction_class_change +
        # friction_class_skip (19 → 21).
        self.assertEqual(len(REGISTRY), 21)


if __name__ == "__main__":
    unittest.main()
