"""State-machine tests for the job-search journey.

Drives ``journey.advance()`` directly so tests are deterministic +
fast. The HTTP integration is exercised in tests/e2e/journey_ux_expert.py.
"""

from __future__ import annotations

import unittest

from company_discovery.journey import (
    DISCOVER_ASK_LANGS,
    DISCOVER_ASK_LOCATION,
    DISCOVER_ASK_ROLE,
    DISCOVER_ASK_YEARS,
    DISCOVER_DONE,
    PHASE_CV_CHECK,
    PHASE_DISCOVER,
    PHASE_DONE,
    PHASE_DRILL,
    PHASE_GREET,
    PHASE_INSPIRE,
    PHASE_PREFS,
    PHASE_REVIEW,
    PHASE_SEARCH,
    PHASE_TAILOR,
    UserJourney,
    advance,
    looks_like_journey_trigger,
    should_auto_start,
)


class JourneyTriggerTests(unittest.TestCase):
    def test_english_explicit_triggers(self):
        for msg in (
            "I want to find a job",
            "help me find work",
            "i need a job",
            "find me a position",
            "search for a role",
            "Can you help me find a job?",
        ):
            self.assertTrue(looks_like_journey_trigger(msg), msg=msg)

    def test_german_explicit_triggers(self):
        for msg in (
            "Ich suche einen Job",
            "Ich will eine Stelle finden",
            "Suche Arbeit in Berlin",
            "Hilf mir einen Job zu finden",
            "Ich brauche eine Stelle",
        ):
            self.assertTrue(looks_like_journey_trigger(msg), msg=msg)

    def test_bare_greetings_do_not_trigger(self):
        # Per scope decision: greetings do NOT auto-start the journey.
        for msg in ("hi", "hello", "hey", "yo", "hallo", "servus",
                     "good morning", "guten tag"):
            self.assertFalse(looks_like_journey_trigger(msg), msg=msg)

    def test_irrelevant_messages_do_not_trigger(self):
        for msg in (
            "what's the weather",
            "show me commands",
            "/add-company X https://x",
            "thanks",
            "",
        ):
            self.assertFalse(looks_like_journey_trigger(msg), msg=msg)


class ShouldAutoStartTests(unittest.TestCase):
    def test_fresh_journey_triggers_on_explicit_phrase(self):
        j = UserJourney()
        self.assertTrue(should_auto_start(j, "I want to find a job"))

    def test_in_progress_journey_does_not_re_trigger(self):
        j = UserJourney(phase=PHASE_DISCOVER)
        self.assertFalse(should_auto_start(j, "I want to find a job"))

    def test_completed_journey_can_re_trigger(self):
        j = UserJourney(phase=PHASE_DONE)
        self.assertTrue(should_auto_start(j, "I need a new job"))

    def test_fresh_journey_no_trigger_on_greeting(self):
        j = UserJourney()
        self.assertFalse(should_auto_start(j, "hi"))
        self.assertFalse(should_auto_start(j, "hallo"))


class GreetPhaseTests(unittest.TestCase):
    def test_greet_advances_to_discover_ask_role(self):
        j = UserJourney()
        r = advance(j, "go")
        self.assertEqual(r.journey.phase, PHASE_DISCOVER)
        self.assertEqual(r.journey.discover_step, DISCOVER_ASK_ROLE)
        self.assertIn("What kind of role", r.reply)


class DiscoverPhaseTests(unittest.TestCase):
    def test_role_extraction_pflegehelfer(self):
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_ROLE)
        r = advance(j, "Pflegehelfer")
        self.assertEqual(r.journey.role_text, "Pflegehelfer")
        self.assertEqual(r.journey.bucket_key, "pflegehelfer")
        self.assertEqual(r.journey.discover_step, DISCOVER_ASK_LOCATION)
        # Persists the job-type filter on profile.
        self.assertEqual(r.profile_updates.get("job_type_filter"),
                          "pflegehelfer")
        self.assertIn("Where", r.reply)

    def test_role_with_no_taxonomy_hit(self):
        # Use a role outside every taxonomy bucket. "Astronaut" has
        # no matching synonym in any bucket.
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_ROLE)
        r = advance(j, "astronaut")
        self.assertEqual(r.journey.role_text, "astronaut")
        self.assertEqual(r.journey.bucket_key, "")
        # No bucket → no job_type_filter persisted.
        self.assertNotIn("job_type_filter", r.profile_updates)

    def test_software_engineer_recognised_as_bucket(self):
        # R21.1: tech-role queries now route to a dedicated bucket
        # instead of falling through to fuzzy aggregator ranking.
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_ROLE)
        r = advance(j, "senior backend engineer")
        self.assertEqual(r.journey.bucket_key, "software_engineer")
        self.assertEqual(r.profile_updates.get("job_type_filter"),
                          "software_engineer")

    def test_location_advance(self):
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_LOCATION)
        r = advance(j, "Berlin")
        self.assertEqual(r.journey.location, "Berlin")
        self.assertEqual(r.journey.location_canonical, "berlin")
        self.assertEqual(r.profile_updates.get("location"), "Berlin")
        self.assertEqual(r.journey.discover_step, DISCOVER_ASK_YEARS)

    def test_years_parsing_integer(self):
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_YEARS)
        r = advance(j, "5")
        self.assertEqual(r.journey.years_experience, 5)
        self.assertEqual(r.profile_updates.get("years_experience"), 5)
        self.assertEqual(r.profile_updates.get("seniority"), "mid")
        self.assertEqual(r.journey.discover_step, DISCOVER_ASK_LANGS)

    def test_years_parsing_words(self):
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_YEARS)
        r = advance(j, "about ten years")
        self.assertEqual(r.journey.years_experience, 10)
        self.assertEqual(r.profile_updates.get("seniority"), "senior")

    def test_years_unparseable_sets_none_but_advances(self):
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_YEARS)
        r = advance(j, "a while")
        self.assertIsNone(r.journey.years_experience)
        self.assertEqual(r.journey.discover_step, DISCOVER_ASK_LANGS)

    def test_languages_split(self):
        j = UserJourney(phase=PHASE_DISCOVER, discover_step=DISCOVER_ASK_LANGS,
                          role_text="Bartender", location="Berlin")
        r = advance(j, "Deutsch, English, Türkçe")
        self.assertEqual(r.journey.languages, ["Deutsch", "English", "Türkçe"])
        self.assertEqual(r.journey.phase, PHASE_CV_CHECK)
        self.assertIn("Bartender", r.reply)
        self.assertIn("Berlin", r.reply)


class CvCheckTests(unittest.TestCase):
    def test_reuse_with_existing_cv_advances_to_inspire(self):
        j = UserJourney(phase=PHASE_CV_CHECK)
        r = advance(j, "reuse", has_existing_cv=True)
        self.assertEqual(r.journey.phase, PHASE_INSPIRE)
        self.assertEqual(r.journey.cv_status, "uploaded")

    def test_build_marks_status_and_kicks_off_sectional_walk(self):
        j = UserJourney(phase=PHASE_CV_CHECK)
        r = advance(j, "build", has_existing_cv=False)
        self.assertEqual(r.journey.cv_status, "building")
        # Stays in cv_check while the sectional build runs.
        self.assertEqual(r.journey.phase, PHASE_CV_CHECK)
        # First sectional question is shown immediately.
        self.assertIn("full name", r.reply.lower())

    def test_pasted_cv_text_stored(self):
        j = UserJourney(phase=PHASE_CV_CHECK)
        paste = (
            "Alex Smith\n"
            "Senior Healthcare PM with 8 years experience in clinical "
            "operations across two hospital groups in Berlin. "
            "Specialised in process improvement and digital health "
            "rollouts. Languages: Deutsch, English. "
            "Hospital Group A 2020-2024 — led 12-person team."
        )
        self.assertGreaterEqual(len(paste), 80)
        r = advance(j, paste, has_existing_cv=False)
        self.assertEqual(r.journey.cv_status, "uploaded")
        self.assertEqual(r.journey.phase, PHASE_INSPIRE)
        self.assertEqual(r.profile_updates.get("cv_text"), paste)

    def test_short_unclear_reply_re_asks(self):
        j = UserJourney(phase=PHASE_CV_CHECK)
        r = advance(j, "uhhh")
        # Still in cv_check, asks user to clarify.
        self.assertEqual(r.journey.phase, PHASE_CV_CHECK)
        self.assertFalse(r.persist)


class CvSectionalBuildTests(unittest.TestCase):
    """Phase R17.2 — chat-driven sectional CV build, 5 quick questions."""

    def test_build_kickoff_asks_first_question(self):
        from company_discovery.journey import (
            UserJourney, PHASE_CV_CHECK, _CV_BUILD_ORDER,
        )
        j = UserJourney(phase=PHASE_CV_CHECK, cv_status="building",
                          cv_build_step=_CV_BUILD_ORDER[0])
        r = advance(j, "")
        # Empty msg at the very first step — just re-asks.
        self.assertIn("full name", r.reply.lower())

    def test_each_step_advances(self):
        from company_discovery.journey import (
            UserJourney, PHASE_CV_CHECK, PHASE_INSPIRE, _CV_BUILD_ORDER,
        )
        j = UserJourney(phase=PHASE_CV_CHECK, cv_status="building",
                          cv_build_step=_CV_BUILD_ORDER[0])
        # Answer each step in sequence.
        r = advance(j, "Maria Schmidt")
        self.assertEqual(j.cv_build_answers["name"], "Maria Schmidt")
        self.assertIn("city", r.reply.lower())
        r = advance(j, "Berlin")
        self.assertEqual(j.cv_build_answers["location"], "Berlin")
        r = advance(j, "Senior Pflegehelferin with 6 years experience in "
                       "elderly care across two clinics in Berlin.")
        self.assertIn("recent role", r.reply.lower())
        r = advance(j, "Charité 2020-2024 — Pflegehelferin. Cared for "
                       "12 residents per shift, led handover meetings.")
        self.assertIn("skills", r.reply.lower())
        r = advance(j, "Pflege, Erste Hilfe, Deutsch, English, "
                       "Dokumentation, Empathie")
        # Sequence complete → phase advances + cv_text persisted.
        self.assertEqual(j.phase, PHASE_INSPIRE)
        self.assertIn("cv_text", r.profile_updates)
        cv_text = r.profile_updates["cv_text"]
        self.assertIn("Maria Schmidt", cv_text)
        self.assertIn("Berlin", cv_text)
        self.assertIn("Charité", cv_text)
        self.assertIn("Pflege", cv_text)

    def test_assemble_omits_empty_sections(self):
        from company_discovery.journey import assemble_cv_from_build
        text = assemble_cv_from_build({
            "name": "Lars",
            "location": "",  # skipped
            "summary": "Backend engineer.",
            "recent_role": "",
            "skills": "Python, Go",
        })
        self.assertIn("# Lars", text)
        self.assertIn("Summary", text)
        self.assertIn("Skills", text)
        self.assertNotIn("Recent experience", text)


class InspirePhaseTests(unittest.TestCase):
    def test_fallback_suggestions_when_no_ai(self):
        j = UserJourney(phase=PHASE_INSPIRE, role_text="Pflegehelfer",
                          bucket_key="pflegehelfer")
        r = advance(j, "", ai_available=False)
        self.assertGreaterEqual(len(r.journey.lateral_roles), 3)
        # Templated honesty.
        self.assertIn("templated", r.reply.lower())
        self.assertIn("Pflegeassistent", r.reply)

    def test_user_accepts_all_suggestions(self):
        j = UserJourney(phase=PHASE_INSPIRE,
                          role_text="Pflegehelfer",
                          bucket_key="pflegehelfer",
                          lateral_roles=["Pflegeassistent", "Altenpflegehelfer"])
        r = advance(j, "yes", ai_available=False)
        self.assertEqual(
            r.journey.target_roles,
            ["Pflegehelfer", "Pflegeassistent", "Altenpflegehelfer"],
        )
        self.assertEqual(r.journey.phase, PHASE_PREFS)

    def test_user_declines_suggestions(self):
        j = UserJourney(phase=PHASE_INSPIRE,
                          role_text="Bartender",
                          bucket_key="bartender",
                          lateral_roles=["Barista", "Server"])
        r = advance(j, "no")
        self.assertEqual(r.journey.target_roles, ["Bartender"])
        self.assertEqual(r.journey.phase, PHASE_PREFS)

    def test_user_cherry_picks_via_csv(self):
        j = UserJourney(phase=PHASE_INSPIRE,
                          role_text="Bartender",
                          bucket_key="bartender",
                          lateral_roles=["Barista", "Server", "Bar Manager"])
        r = advance(j, "Barista, Bar Manager")
        self.assertEqual(
            r.journey.target_roles,
            ["Bartender", "Barista", "Bar Manager"],
        )

    def test_ai_caller_used_when_available(self):
        # Inject a fake AI caller.
        called: dict[str, str] = {}

        def fake_ai(system, user_msg):
            called["system"] = system
            called["user"] = user_msg
            return '["Senior Pflegehelfer", "OTA", "Krankenpflegehelfer"]'

        j = UserJourney(phase=PHASE_INSPIRE, role_text="Pflegehelfer",
                          bucket_key="pflegehelfer", years_experience=6)
        r = advance(j, "", ai_available=True, ai_caller=fake_ai)
        self.assertEqual(r.journey.lateral_roles,
                          ["Senior Pflegehelfer", "OTA", "Krankenpflegehelfer"])
        # No templated honesty banner when AI succeeded.
        self.assertNotIn("templated", r.reply.lower())
        self.assertIn("Pflegehelfer", called["user"])

    def test_ai_caller_error_falls_back(self):
        def crashing_ai(system, user_msg):
            raise RuntimeError("api down")

        j = UserJourney(phase=PHASE_INSPIRE, role_text="Bartender",
                          bucket_key="bartender")
        r = advance(j, "", ai_available=True, ai_caller=crashing_ai)
        # Falls through to template.
        self.assertIn("Barista", r.reply)


class PrefsPhaseTests(unittest.TestCase):
    def test_skip(self):
        j = UserJourney(
            phase=PHASE_PREFS, role_text="Bartender",
            location="Berlin",
            target_roles=["Bartender"],
        )
        r = advance(j, "skip")
        self.assertEqual(r.journey.phase, PHASE_SEARCH)
        self.assertIsNotNone(r.run_search_with)
        self.assertEqual(r.run_search_with["target_roles"], ["Bartender"])

    def test_remote_required(self):
        j = UserJourney(
            phase=PHASE_PREFS, role_text="Backend",
            location="anywhere",
            target_roles=["Backend"],
        )
        r = advance(j, "remote only please, min 70k, startup")
        self.assertTrue(r.journey.remote_required)
        self.assertEqual(r.journey.salary_floor, 70000)
        self.assertEqual(r.journey.company_size, "startup")


class ReviewDrillPhaseTests(unittest.TestCase):
    def test_review_with_categories(self):
        j = UserJourney(
            phase=PHASE_REVIEW,
            search_results_by_category={
                "Clinical": ["job_a", "job_b"],
                "Digital health": ["job_c"],
            },
        )
        r = advance(j, "clinical")
        self.assertEqual(r.journey.picked_category, "Clinical")
        self.assertEqual(r.journey.phase, PHASE_DRILL)

    def test_review_empty_results_marks_done(self):
        j = UserJourney(phase=PHASE_REVIEW, search_results_by_category={})
        r = advance(j, "")
        self.assertEqual(r.journey.phase, PHASE_DONE)
        self.assertTrue(r.done)

    def test_drill_picks_job_by_number(self):
        j = UserJourney(
            phase=PHASE_DRILL,
            picked_category="Clinical",
            search_results_by_category={
                "Clinical": ["job_a", "job_b", "job_c"],
            },
        )
        r = advance(j, "2")
        self.assertEqual(r.journey.picked_job_id, "job_b")
        self.assertEqual(r.journey.phase, PHASE_TAILOR)

    def test_drill_out_of_range_stays(self):
        j = UserJourney(
            phase=PHASE_DRILL,
            picked_category="Clinical",
            search_results_by_category={
                "Clinical": ["job_a", "job_b"],
            },
        )
        r = advance(j, "9")
        self.assertEqual(r.journey.picked_job_id, "")
        self.assertEqual(r.journey.phase, PHASE_DRILL)


class CategorizationTests(unittest.TestCase):
    def test_categorize_clinical(self):
        from company_discovery.journey import categorize_job
        self.assertEqual(categorize_job("Pflegehelfer Berlin"),
                          "Clinical / Pflege")
        self.assertEqual(categorize_job("Senior Nurse"),
                          "Clinical / Pflege")

    def test_categorize_hospitality(self):
        from company_discovery.journey import categorize_job
        self.assertEqual(categorize_job("Bartender"),
                          "Hospitality / Bar")
        self.assertEqual(categorize_job("Barista (m/w/d)"),
                          "Hospitality / Bar")

    def test_categorize_tech(self):
        from company_discovery.journey import categorize_job
        self.assertEqual(categorize_job("Senior Backend Engineer"),
                          "Tech / Engineering")

    def test_categorize_other(self):
        from company_discovery.journey import categorize_job
        self.assertEqual(categorize_job("Astronaut"), "Other")

    def test_cluster_jobs_distributes_by_title(self):
        from company_discovery.journey import cluster_jobs
        jobs = [
            {"title": "Bartender", "url": "u1"},
            {"title": "Backend Engineer", "url": "u2"},
            {"title": "Pflegehelfer", "url": "u3"},
            {"title": "Bartender Berlin", "url": "u4"},
        ]
        clusters = cluster_jobs(jobs)
        self.assertIn("Hospitality / Bar", clusters)
        self.assertIn("Tech / Engineering", clusters)
        self.assertIn("Clinical / Pflege", clusters)
        # Two bartender jobs in the same bucket.
        self.assertEqual(len(clusters["Hospitality / Bar"]), 2)


class JourneySerialisationTests(unittest.TestCase):
    def test_roundtrip(self):
        j = UserJourney(
            phase=PHASE_INSPIRE,
            role_text="Pflegehelfer",
            bucket_key="pflegehelfer",
            location="Berlin",
            location_canonical="berlin",
            years_experience=5,
            languages=["Deutsch", "English"],
            cv_status="uploaded",
            lateral_roles=["Pflegeassistent"],
            target_roles=[],
        )
        d = j.to_dict()
        j2 = UserJourney.from_dict(d)
        self.assertEqual(j2.phase, j.phase)
        self.assertEqual(j2.role_text, j.role_text)
        self.assertEqual(j2.languages, j.languages)
        self.assertEqual(j2.lateral_roles, j.lateral_roles)

    def test_from_empty_dict_is_default(self):
        j = UserJourney.from_dict(None)
        self.assertEqual(j.phase, PHASE_GREET)
        self.assertEqual(j.discover_step, DISCOVER_ASK_ROLE)

    def test_from_partial_dict(self):
        j = UserJourney.from_dict({"phase": PHASE_DISCOVER,
                                       "roleText": "Bartender"})
        self.assertEqual(j.phase, PHASE_DISCOVER)
        self.assertEqual(j.role_text, "Bartender")
        # Defaults fill the rest.
        self.assertEqual(j.languages, [])


if __name__ == "__main__":
    unittest.main()
