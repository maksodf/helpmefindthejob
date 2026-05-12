"""Strict job-type + location filter — unit tests.

Covers: synonym matching (EN + DE), word-boundary safety, location
normalization (anywhere / Germany / specific city), the dict-shape
variant used by HTTP payloads, and edge cases (empty inputs,
unknown roles).
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from company_discovery.job_type_filter import (
    TAXONOMY,
    filter_dict_jobs,
    filter_jobs,
    identify_bucket,
    job_matches_bucket,
    job_matches_location,
    list_supported_roles,
    normalize_location,
)


@dataclass
class _FakeJob:
    title: str
    raw_description: str = ""
    location: str | None = None


class IdentifyBucketTests(unittest.TestCase):
    def test_english_bartender(self):
        self.assertEqual(identify_bucket("find me bartender jobs"), "bartender")

    def test_german_barkeeper(self):
        self.assertEqual(identify_bucket("Suche Barkeeper-Job"), "bartender")

    def test_german_pflegehelfer(self):
        self.assertEqual(identify_bucket("Ich suche Pflegehelfer"), "pflegehelfer")

    def test_english_nursing_assistant(self):
        self.assertEqual(identify_bucket("nursing assistant in Berlin"),
                          "pflegehelfer")

    def test_barista(self):
        self.assertEqual(identify_bucket("Barista jobs near me"), "barista")

    def test_cafe_worker(self):
        self.assertEqual(identify_bucket("café-mitarbeiter"), "cafe_worker")

    def test_waiter(self):
        self.assertEqual(identify_bucket("looking for waiter work"), "waiter")
        self.assertEqual(identify_bucket("Kellner gesucht"), "waiter")

    def test_unknown_returns_none(self):
        self.assertIsNone(identify_bucket("senior backend engineer"))
        self.assertIsNone(identify_bucket("software developer"))
        self.assertIsNone(identify_bucket(""))
        self.assertIsNone(identify_bucket(None))

    def test_longest_synonym_wins(self):
        # "altenpflegehelfer" only lives in the pflegehelfer bucket
        # so it has to route there even though "pfleger" might trigger
        # other rules in future expansions.
        self.assertEqual(identify_bucket("Altenpflegehelfer"), "pflegehelfer")


class JobMatchesBucketTests(unittest.TestCase):
    def test_bartender_in_title_matches(self):
        self.assertTrue(job_matches_bucket("Bartender", "", "bartender"))

    def test_barkeeper_in_title_matches(self):
        self.assertTrue(job_matches_bucket("Barkeeper (m/w/d)", "", "bartender"))

    def test_unrelated_title_rejected(self):
        self.assertFalse(job_matches_bucket("Senior Backend Engineer", "", "bartender"))
        self.assertFalse(job_matches_bucket("Software Developer", "Java team", "bartender"))

    def test_description_matches(self):
        self.assertTrue(job_matches_bucket(
            "Service Mitarbeiter", "Wir suchen einen Pflegehelfer für Berlin",
            "pflegehelfer",
        ))

    def test_word_boundary_safety(self):
        # "backseat" must NOT match "bar back" via substring.
        self.assertFalse(job_matches_bucket("backseat driver", "", "bartender"))
        # "developer" must NOT match "barkeeper".
        self.assertFalse(job_matches_bucket("developer", "", "bartender"))

    def test_unknown_bucket_returns_false(self):
        self.assertFalse(job_matches_bucket("Anything", "anything", "ceo"))

    def test_empty_title_and_description_rejected(self):
        self.assertFalse(job_matches_bucket("", "", "bartender"))
        self.assertFalse(job_matches_bucket("", None, "bartender"))


class NormalizeLocationTests(unittest.TestCase):
    def test_germany_canonical(self):
        self.assertEqual(normalize_location("Germany"), "germany")
        self.assertEqual(normalize_location("Deutschland"), "germany")
        self.assertEqual(normalize_location("DE"), "germany")
        self.assertEqual(normalize_location("ger"), "germany")

    def test_anywhere_returns_none(self):
        for token in ("anywhere", "any city", "remote", "Überall", "egal", "Egal wo"):
            self.assertIsNone(normalize_location(token), msg=token)

    def test_empty_returns_none(self):
        self.assertIsNone(normalize_location(""))
        self.assertIsNone(normalize_location("   "))
        self.assertIsNone(normalize_location(None))

    def test_specific_city_passthrough(self):
        self.assertEqual(normalize_location("Berlin"), "berlin")
        self.assertEqual(normalize_location(" MÜNCHEN "), "münchen")


class JobMatchesLocationTests(unittest.TestCase):
    def test_germany_expands_to_cities(self):
        self.assertTrue(job_matches_location("Berlin", "germany"))
        self.assertTrue(job_matches_location("Munich, DE", "germany"))
        self.assertTrue(job_matches_location("Hamburg, Germany", "germany"))
        self.assertTrue(job_matches_location("Frankfurt am Main", "germany"))
        self.assertFalse(job_matches_location("London", "germany"))
        self.assertFalse(job_matches_location("Vienna", "germany"))

    def test_specific_city_substring(self):
        self.assertTrue(job_matches_location("Berlin", "berlin"))
        self.assertTrue(job_matches_location("Berlin, Germany", "berlin"))
        self.assertFalse(job_matches_location("Munich", "berlin"))

    def test_none_means_any(self):
        self.assertTrue(job_matches_location("Anywhere on the moon", None))
        self.assertTrue(job_matches_location(None, None))

    def test_empty_location_with_filter_rejects(self):
        self.assertFalse(job_matches_location(None, "berlin"))
        self.assertFalse(job_matches_location("", "germany"))


class FilterJobsTests(unittest.TestCase):
    def test_strict_role_filter(self):
        jobs = [
            _FakeJob("Bartender", "Cocktail service", "Berlin"),
            _FakeJob("Senior Backend Engineer", "Python team", "Berlin"),
            _FakeJob("Barkeeper", "Nachtschicht", "München"),
        ]
        kept = filter_jobs(jobs, job_type="bartender", location=None)
        self.assertEqual(len(kept), 2)
        self.assertEqual({j.title for j in kept}, {"Bartender", "Barkeeper"})

    def test_strict_role_plus_location_germany(self):
        jobs = [
            _FakeJob("Bartender", "", "Berlin"),
            _FakeJob("Bartender", "", "London"),
            _FakeJob("Pflegehelfer", "", "München"),
        ]
        kept = filter_jobs(jobs, job_type="bartender", location="Germany")
        self.assertEqual([j.location for j in kept], ["Berlin"])

    def test_pflegehelfer_in_germany(self):
        jobs = [
            _FakeJob("Pflegehelfer", "Altenpflege in Berlin", "Berlin"),
            _FakeJob("Software Engineer", "Healthcare SaaS", "Berlin"),
            _FakeJob("Nursing Assistant", "", "Vienna"),
        ]
        kept = filter_jobs(jobs, job_type="pflegehelfer", location="Germany")
        self.assertEqual([j.title for j in kept], ["Pflegehelfer"])

    def test_no_filter_returns_all(self):
        jobs = [
            _FakeJob("Anything"),
            _FakeJob("Whatever", location="Anywhere"),
        ]
        kept = filter_jobs(jobs, job_type=None, location=None)
        self.assertEqual(len(kept), 2)

    def test_anywhere_location_disables_location_filter(self):
        jobs = [
            _FakeJob("Bartender", location="Tokyo"),
            _FakeJob("Bartender", location="Reykjavik"),
        ]
        kept = filter_jobs(jobs, job_type="bartender", location="anywhere")
        self.assertEqual(len(kept), 2)


class FilterDictJobsTests(unittest.TestCase):
    def test_dict_payload_filtered(self):
        jobs = [
            {"title": "Bartender", "description": "Nachtschicht",
              "location": "Berlin"},
            {"title": "Backend Engineer", "description": "Python", "location": "Berlin"},
        ]
        kept = filter_dict_jobs(jobs, job_type="bartender", location=None)
        self.assertEqual([j["title"] for j in kept], ["Bartender"])

    def test_dict_camel_case_key_supported(self):
        jobs = [
            {"title": "Service", "rawDescription": "Wir suchen Pflegehelfer für Berlin",
              "location": "Berlin"},
            {"title": "Service", "rawDescription": "Restaurant team", "location": "Berlin"},
        ]
        kept = filter_dict_jobs(jobs, job_type="pflegehelfer", location=None)
        self.assertEqual(len(kept), 1)


class ListSupportedRolesTests(unittest.TestCase):
    def test_returns_all_taxonomy_entries(self):
        roles = list_supported_roles()
        self.assertEqual({r["key"] for r in roles}, set(TAXONOMY.keys()))
        for role in roles:
            self.assertTrue(role["label_en"])
            self.assertTrue(role["label_de"])


class ExtractKeywordArgsTests(unittest.TestCase):
    """Inline-arg extraction from the keyword-routed natural-language path.
    Verifies the chat router pre-fills find_jobs without re-prompting the
    user when their message already contains role + location."""

    def test_find_bartender_in_berlin(self):
        from company_discovery.chat_router import extract_keyword_args
        args = extract_keyword_args("find_jobs", "find me bartender jobs in Berlin")
        self.assertEqual(args.get("query"), "Bartender")
        self.assertEqual(args.get("location", "").lower(), "berlin")

    def test_pflegehelfer_in_germany(self):
        from company_discovery.chat_router import extract_keyword_args
        args = extract_keyword_args("find_jobs", "Pflegehelfer in Deutschland gesucht")
        self.assertEqual(args.get("query"), "Nursing assistant")
        # "in Deutschland" maps to canonical "Germany"
        self.assertEqual(args.get("location"), "Germany")

    def test_barista_anywhere(self):
        from company_discovery.chat_router import extract_keyword_args
        args = extract_keyword_args("find_jobs", "find barista jobs anywhere")
        self.assertEqual(args.get("query"), "Barista")
        self.assertEqual(args.get("location"), "anywhere")

    def test_no_match_returns_empty(self):
        from company_discovery.chat_router import extract_keyword_args
        # Different command — not handled here.
        args = extract_keyword_args("add_company", "add Charité https://x")
        self.assertEqual(args, {})

    def test_unknown_role_no_query(self):
        from company_discovery.chat_router import extract_keyword_args
        args = extract_keyword_args("find_jobs", "find me a senior backend role")
        # No taxonomy hit → no query extracted (would be re-asked)
        self.assertNotIn("query", args)


if __name__ == "__main__":
    unittest.main()
