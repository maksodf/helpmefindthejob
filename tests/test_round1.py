"""Round-1 globalisation + depth tests.

Covers:

- ``personas`` registry exposes 5 personas with disjoint sector weights.
- ``rank_candidates`` ranks a tech employer above a hospital when the
  persona is tech, and the inverse when the persona is healthcare.
- ``CAREER_LINK_TERMS`` covers French / Dutch / Spanish / Italian /
  Polish / Portuguese.
- ``suggest_curated_companies(persona_id=...)`` only returns entries
  whose persona membership matches.
- ``list_templates(persona_id=...)`` filters watchlist templates.
- ``UserProfile`` is created, updated, and persisted by the in-memory
  and sqlite repositories.
- ``build_job_decision_brief_prompt`` and ``build_cover_letter_brief_prompt``
  both inline persona + profile context and respect a custom CV.
- The HTTP layer surfaces ``/api/personas``, ``/api/profile``
  (GET + POST), and ``/api/imported-jobs/<id>/prepare-cover-letter``.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import (
    build_cover_letter_brief_prompt,
    build_job_decision_brief_prompt,
)
from company_discovery.curated_companies import suggest_curated_companies
from company_discovery.models import ImportedJob, UserProfile
from company_discovery.persona_ranking import rank_candidates
from company_discovery.personas import (
    DEFAULT_PERSONA_ID,
    PERSONAS,
    get_persona,
    list_personas_summary,
)
from company_discovery.repository import InMemoryCompanyDiscoveryRepository
from company_discovery.service import CAREER_LINK_TERMS
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository
from company_discovery.watchlist_templates import list_templates


class PersonaRegistryTests(unittest.TestCase):
    def test_default_persona_present(self) -> None:
        self.assertIn(DEFAULT_PERSONA_ID, PERSONAS)
        self.assertEqual(get_persona(None).id, DEFAULT_PERSONA_ID)
        self.assertEqual(get_persona("does-not-exist").id, DEFAULT_PERSONA_ID)

    def test_personas_includes_originals(self) -> None:
        # The original five must remain available; later phases add more
        # (education, legal, sales, design, operations, healthcare-clinical).
        self.assertTrue(
            {"healthcare-management", "tech", "marketing", "finance", "product-management"}
            .issubset(set(PERSONAS))
        )

    def test_personas_summary_contains_required_fields(self) -> None:
        summary = list_personas_summary()
        self.assertGreaterEqual(len(summary), 5)
        for persona in summary:
            self.assertIn("id", persona)
            self.assertIn("label", persona)
            self.assertIn("description", persona)
            self.assertIsInstance(persona["defaultTargetRoles"], list)

    def test_sector_weights_differ_by_persona(self) -> None:
        # Healthcare and tech don't share their highest-weighted sector.
        healthcare_top = max(get_persona("healthcare-management").sector_weights.items(), key=lambda kv: kv[1])
        tech_top = max(get_persona("tech").sector_weights.items(), key=lambda kv: kv[1])
        self.assertNotEqual(healthcare_top[0], tech_top[0])


class SuggestPersonaFromTextTests(unittest.TestCase):
    """Phase 6d — auto-suggest persona by scanning CV keywords."""

    def test_data_cv_picks_data_persona(self) -> None:
        from company_discovery.personas import suggest_persona_from_text

        cv = (
            "Senior data scientist with 6 years of experience building machine "
            "learning pipelines, deploying MLOps stacks, and leading analytics "
            "engineer teams in fintech."
        )
        ranked = suggest_persona_from_text(cv, top_k=3)
        self.assertEqual(ranked[0][0], "data")
        self.assertGreater(ranked[0][1], 0.0)

    def test_legal_cv_picks_legal_persona(self) -> None:
        from company_discovery.personas import suggest_persona_from_text

        cv = (
            "Rechtsanwältin / corporate counsel with deep experience in M&A, "
            "compliance, and litigation across DACH law firms."
        )
        ranked = suggest_persona_from_text(cv, top_k=3)
        self.assertEqual(ranked[0][0], "legal")

    def test_empty_text_returns_empty_list(self) -> None:
        from company_discovery.personas import suggest_persona_from_text

        self.assertEqual(suggest_persona_from_text(""), [])
        self.assertEqual(suggest_persona_from_text("   "), [])

    def test_top_k_capped(self) -> None:
        from company_discovery.personas import suggest_persona_from_text

        cv = "data engineer ml hr recruiter design ux journalist editor"
        ranked = suggest_persona_from_text(cv, top_k=3)
        self.assertLessEqual(len(ranked), 3)


class RankingPersonaSwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = [
            {
                "type": "company",
                "name": "Datadog",
                "sector": "SaaS / observability",
                "relevanceReason": "Cloud observability platform with platform engineering roles.",
                "locationHint": "Paris / Dublin",
            },
            {
                "type": "company",
                "name": "Charite",
                "sector": "University hospital",
                "relevanceReason": "Hospital with project management and research roles.",
                "locationHint": "Berlin",
            },
        ]

    def test_tech_persona_prefers_saas(self) -> None:
        ranked = rank_candidates(
            self.candidates,
            target_roles=["platform engineer"],
            persona_id="tech",
        )
        self.assertEqual(ranked[0]["name"], "Datadog")

    def test_healthcare_persona_prefers_hospital(self) -> None:
        ranked = rank_candidates(
            self.candidates,
            target_roles=["project management", "quality"],
            persona_id="healthcare-management",
        )
        self.assertEqual(ranked[0]["name"], "Charite")


class CareerLinkTermsTests(unittest.TestCase):
    def test_includes_international_terms(self) -> None:
        for term in (
            "carrières", "emplois",
            "vacatures", "werken bij",
            "empleos", "carreras",
            "lavoro", "candidati",
            "kariera", "praca",
            "carreiras", "vagas",
        ):
            self.assertIn(term, CAREER_LINK_TERMS, msg=f"missing: {term}")

    def test_keeps_legacy_terms(self) -> None:
        for term in ("karriere", "career", "jobs", "stellen"):
            self.assertIn(term, CAREER_LINK_TERMS)


class SuggestCuratedCompaniesByPersonaTests(unittest.TestCase):
    def test_tech_persona_excludes_hospitals(self) -> None:
        results = suggest_curated_companies(
            target_roles=["backend engineer"],
            industry="Technology",
            location=None,
            limit=20,
            persona_id="tech",
        )
        names = {item["name"] for item in results}
        self.assertNotIn("Charite - Universitaetsmedizin Berlin", names)
        self.assertTrue({"Datadog", "Hugging Face"} & names)

    def test_finance_persona_excludes_consumer_brands(self) -> None:
        results = suggest_curated_companies(
            target_roles=["audit"],
            industry="Finance",
            location=None,
            limit=20,
            persona_id="finance",
        )
        names = {item["name"] for item in results}
        self.assertIn("Deutsche Bank", names)
        self.assertNotIn("HelloFresh", names)


class WatchlistTemplatesPersonaTests(unittest.TestCase):
    def test_filtered_to_persona(self) -> None:
        finance_ids = {item["id"] for item in list_templates("finance")}
        self.assertIn("dax_finance_de", finance_ids)
        self.assertIn("big4_de", finance_ids)
        self.assertNotIn("hospital_groups_de", finance_ids)

    def test_unfiltered_returns_all(self) -> None:
        all_ids = {item["id"] for item in list_templates()}
        self.assertGreaterEqual(len(all_ids), 9)


class UserProfileRepositoryTests(unittest.TestCase):
    def test_save_get_delete_in_memory(self) -> None:
        repo = InMemoryCompanyDiscoveryRepository()
        self.assertIsNone(repo.get_user_profile("u1"))
        profile = UserProfile(
            user_id="u1",
            persona_id="tech",
            target_roles=["backend"],
            cv_text="Some CV text",
        )
        repo.save_user_profile(profile)
        loaded = repo.get_user_profile("u1")
        assert loaded is not None
        self.assertEqual(loaded.persona_id, "tech")
        self.assertEqual(loaded.cv_text, "Some CV text")
        repo.delete_user_profile("u1")
        self.assertIsNone(repo.get_user_profile("u1"))

    def test_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "round1.sqlite3"
            repo = SqliteCompanyDiscoveryRepository(path)
            try:
                profile = UserProfile(
                    user_id="u1",
                    persona_id="finance",
                    target_roles=["fp&a"],
                    languages=["English", "German"],
                    cv_text="Years of finance.",
                )
                repo.save_user_profile(profile)
            finally:
                repo.close()

            reopened = SqliteCompanyDiscoveryRepository(path)
            try:
                loaded = reopened.get_user_profile("u1")
                assert loaded is not None
                self.assertEqual(loaded.persona_id, "finance")
                self.assertEqual(loaded.target_roles, ["fp&a"])
                self.assertEqual(loaded.languages, ["English", "German"])
                self.assertEqual(loaded.cv_text, "Years of finance.")
            finally:
                reopened.close()


class AnalysisPromptPersonaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://example.com/job/1",
            title="Senior Backend Engineer",
            company_name="Datadog",
            location="Paris",
            description="We are hiring backend engineers for our platform team.",
        )
        self.provider = AIProviderConfig(provider_id="openai", invocation_mode="api")

    def test_brief_includes_persona_and_cv(self) -> None:
        profile = UserProfile(
            user_id="u1",
            persona_id="tech",
            target_roles=["platform engineer"],
            cv_text="Distinctive marker XYZ123 in the CV body.",
        )
        result = build_job_decision_brief_prompt(self.job, self.provider, profile)
        self.assertIn("Technology", result["prompt"])
        self.assertIn("XYZ123", result["prompt"])
        self.assertIn("platform engineer", result["prompt"].lower())

    def test_brief_falls_back_to_default_persona(self) -> None:
        result = build_job_decision_brief_prompt(self.job, self.provider, profile=None)
        self.assertIn("Healthcare management", result["prompt"])
        self.assertIn("No CV uploaded yet", result["prompt"])

    def test_cover_letter_prompt_uses_profile(self) -> None:
        profile = UserProfile(
            user_id="u1",
            persona_id="tech",
            target_roles=["platform engineer"],
            cv_text="Backend at Acme for 5 years.",
            languages=["English (C2)"],
        )
        result = build_cover_letter_brief_prompt(self.job, self.provider, profile)
        prompt = result["prompt"]
        self.assertIn("cover letter", prompt.lower())
        self.assertIn("Datadog", prompt)
        self.assertIn("English (C2)", prompt)
        self.assertIn("Backend at Acme", prompt)


class HttpProfileEndpointTests(unittest.TestCase):
    """Smoke tests that exercise app.STATE directly without HTTP wiring."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round1-state-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        # Ensure a fresh import.
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app  # noqa: E402

        cls.state = app.STATE
        cls.app = app

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_profile_round_trip_through_state(self) -> None:
        user_id = "round1-user"
        profile = self.state.update_profile(
            user_id,
            {
                "personaId": "tech",
                "targetRoles": "backend, platform",
                "industry": "Technology",
                "location": "Berlin",
                "yearsExperience": 4,
                "languages": "English, German",
                "cvText": "Engineering experience.",
                "notes": "Visa: Blue Card.",
            },
        )
        self.assertEqual(profile.persona_id, "tech")
        self.assertEqual(profile.target_roles, ["backend", "platform"])
        self.assertEqual(profile.years_experience, 4)
        self.assertEqual(profile.languages, ["English", "German"])

        again = self.state.profile_for(user_id)
        self.assertEqual(again.cv_text, "Engineering experience.")
        self.assertEqual(again.notes, "Visa: Blue Card.")

    def test_unknown_persona_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.state.update_profile("u2", {"personaId": "not-a-real-persona"})

    def test_bootstrap_includes_personas_and_profile(self) -> None:
        boot = self.state.bootstrap("round1-user")
        self.assertIn("personas", boot)
        self.assertGreaterEqual(len(boot["personas"]), 5)
        self.assertIn("profile", boot)
        self.assertIn("personaId", boot["profile"])

    def test_watchlist_templates_filtered_by_persona(self) -> None:
        # Configure user with finance persona, then verify bootstrap filters templates.
        self.state.update_profile("finance-user", {"personaId": "finance"})
        boot = self.state.bootstrap("finance-user")
        template_ids = {item["id"] for item in boot["watchlistTemplates"]}
        self.assertIn("dax_finance_de", template_ids)
        self.assertNotIn("hospital_groups_de", template_ids)

    def test_cv_too_long_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.state.update_profile(
                "round1-user",
                {"cvText": "x" * 70_000},
            )


if __name__ == "__main__":
    unittest.main()
