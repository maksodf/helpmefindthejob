# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 15 — Gate 6.4 colloquial intent recognition (DE+EN).

Pins the rule-based intent classification (chat_router.py keyword
regex + slash-alias exact-match) for colloquial DE+EN inputs across
the major intent categories. Three-layer hybrid architecture:

  Layer 1: parse_slash_command  -- exact slash-alias match
  Layer 2: keyword_route        -- regex over Command.keywords
  Layer 3: chat_ai_route        -- LLM-based fallback (safety net)

This file covers Layers 1 + 2 only. Layer 3 is by-design fallback
for inputs that don't match the deterministic regex layer; the
``IntentionalFallthroughToAiRouterTests`` class pins specific
colloquial inputs that SHOULD fall through (returns None from
keyword_route), so future regex changes don't accidentally absorb
them.

Gate 6.4 closure criterion (operator-approved): >= 5 colloquial
variants per language per major intent category pass intent
recognition via keyword_route OR parse_slash_command.
"""

from __future__ import annotations

import unittest

from company_discovery.chat_router import (
    keyword_route,
    parse_slash_command,
)
from company_discovery.journey import (
    _REVIEW_EMPTY_START_FRESH_TOKENS,
    is_cancel_token,
)


def _route(message: str) -> str | None:
    """Layer 1 + 2 combined: try slash first, then keyword regex."""
    slash = parse_slash_command(message)
    if slash:
        return slash[0]
    return keyword_route(message)


# ─── find_jobs intent ────────────────────────────────────────────


class FindJobsColloquialEnTests(unittest.TestCase):
    def test_find_me_a_job(self):
        self.assertEqual(_route("find me a job"), "find_jobs")

    def test_search_for_bartender_jobs(self):
        self.assertEqual(_route("search for bartender jobs"), "find_jobs")

    def test_show_me_jobs(self):
        self.assertEqual(_route("show me jobs"), "find_jobs")

    def test_search_for_a_role(self):
        self.assertEqual(_route("search for a role"), "find_jobs")

    def test_role_token_pflegehelfer(self):
        self.assertEqual(_route("Pflegehelfer please"), "find_jobs")


class FindJobsColloquialDeTests(unittest.TestCase):
    def test_suche_einen_job(self):
        self.assertEqual(_route("suche einen job"), "find_jobs")

    def test_finde_stellen(self):
        self.assertEqual(_route("finde Stellen in Berlin"), "find_jobs")

    def test_stellenangebote_fuer_bartender(self):
        self.assertEqual(_route("Stellenangebote für Bartender"), "find_jobs")

    def test_pflegehelfer_gesucht(self):
        self.assertEqual(_route("Pflegehelfer gesucht"), "find_jobs")

    def test_ich_suche_arbeit(self):
        self.assertEqual(_route("Ich suche Arbeit als Krankenpfleger"), "find_jobs")


# ─── draft_motivation_letter intent ──────────────────────────────


class LetterColloquialEnTests(unittest.TestCase):
    def test_slash_letter(self):
        self.assertEqual(_route("/letter"), "draft_motivation_letter")

    def test_draft_a_motivation_letter(self):
        self.assertEqual(_route("draft a motivation letter"), "draft_motivation_letter")

    def test_write_me_a_cover_letter(self):
        self.assertEqual(_route("write me a cover letter"), "draft_motivation_letter")

    def test_compose_a_motivation_letter(self):
        self.assertEqual(_route("compose a motivation letter"), "draft_motivation_letter")

    def test_prepare_an_application_letter(self):
        self.assertEqual(_route("prepare an application letter"), "draft_motivation_letter")


class LetterColloquialDeTests(unittest.TestCase):
    def test_anschreiben(self):
        self.assertEqual(_route("Anschreiben"), "draft_motivation_letter")

    def test_anschreiben_verfassen(self):
        self.assertEqual(_route("Anschreiben verfassen"), "draft_motivation_letter")

    def test_motivationsschreiben(self):
        self.assertEqual(_route("Motivationsschreiben"), "draft_motivation_letter")

    def test_motivationsschreiben_bitte(self):
        self.assertEqual(_route("Motivationsschreiben bitte"), "draft_motivation_letter")

    def test_bewerbungsschreiben(self):
        self.assertEqual(_route("Bewerbungsschreiben für diese Stelle"), "draft_motivation_letter")


# ─── tailor_cv intent ────────────────────────────────────────────


class TailorCvColloquialEnTests(unittest.TestCase):
    def test_slash_tailor(self):
        self.assertEqual(_route("/tailor"), "tailor_cv")

    def test_tailor_my_cv(self):
        self.assertEqual(_route("tailor my cv"), "tailor_cv")

    def test_tailor_my_resume(self):
        self.assertEqual(_route("tailor my resume"), "tailor_cv")

    def test_rewrite_my_cv(self):
        self.assertEqual(_route("rewrite my cv"), "tailor_cv")

    def test_customize_my_resume(self):
        self.assertEqual(_route("customize my resume"), "tailor_cv")


class TailorCvColloquialDeTests(unittest.TestCase):
    def test_cv_anpassen(self):
        self.assertEqual(_route("CV anpassen"), "tailor_cv")

    def test_lebenslauf_anpassen(self):
        self.assertEqual(_route("Lebenslauf anpassen"), "tailor_cv")

    def test_lebenslauf_aufpolieren(self):
        self.assertEqual(_route("Lebenslauf aufpolieren"), "tailor_cv")

    def test_anpassen_meinen_lebenslauf(self):
        self.assertEqual(_route("anpassen meinen Lebenslauf"), "tailor_cv")

    def test_lebenslauf_umarbeiten(self):
        self.assertEqual(_route("Lebenslauf umarbeiten"), "tailor_cv")


# ─── suggest_cv_enhancements intent ──────────────────────────────


class ConsultColloquialEnTests(unittest.TestCase):
    def test_slash_consult(self):
        self.assertEqual(_route("/consult"), "suggest_cv_enhancements")

    def test_enhance_my_cv(self):
        self.assertEqual(_route("enhance my cv"), "suggest_cv_enhancements")

    def test_improve_my_cv(self):
        self.assertEqual(_route("improve my cv"), "suggest_cv_enhancements")

    def test_consult_about_cv(self):
        self.assertEqual(_route("consult on my cv"), "suggest_cv_enhancements")

    def test_cv_gaps(self):
        self.assertEqual(_route("cv gaps please"), "suggest_cv_enhancements")


class ConsultColloquialDeTests(unittest.TestCase):
    def test_cv_verbessern(self):
        self.assertEqual(_route("CV verbessern"), "suggest_cv_enhancements")

    def test_lebenslauf_verbessern(self):
        self.assertEqual(_route("Lebenslauf verbessern"), "suggest_cv_enhancements")

    def test_lebenslauf_optimieren(self):
        self.assertEqual(_route("Lebenslauf optimieren"), "suggest_cv_enhancements")

    def test_verbessere_meinen_cv(self):
        self.assertEqual(_route("verbessere meinen CV"), "suggest_cv_enhancements")

    def test_optimiere_meinen_lebenslauf(self):
        self.assertEqual(_route("optimiere meinen Lebenslauf"), "suggest_cv_enhancements")


# ─── help intent ─────────────────────────────────────────────────


class HelpColloquialEnTests(unittest.TestCase):
    def test_slash_help(self):
        self.assertEqual(_route("/help"), "help")

    def test_slash_question_mark(self):
        self.assertEqual(_route("/?"), "help")

    def test_help(self):
        self.assertEqual(_route("help"), "help")

    def test_what_can_you_do(self):
        self.assertEqual(_route("what can you do"), "help")

    def test_show_me_commands(self):
        self.assertEqual(_route("show me commands"), "help")


class HelpColloquialDeTests(unittest.TestCase):
    def test_hilfe_lowercase(self):
        self.assertEqual(_route("hilfe"), "help")

    def test_hilfe_capitalised(self):
        self.assertEqual(_route("Hilfe"), "help")

    def test_was_kannst_du(self):
        self.assertEqual(_route("was kannst du"), "help")

    def test_was_kannst_du_question(self):
        self.assertEqual(_route("Was kannst du?"), "help")

    def test_was_kann_ich_tun(self):
        self.assertEqual(_route("was kann ich tun"), "help")


# ─── cancel intent (journey-level via is_cancel_token) ───────────


class CancelColloquialEnTests(unittest.TestCase):
    def test_cancel(self):
        self.assertTrue(is_cancel_token("cancel"))

    def test_nevermind(self):
        self.assertTrue(is_cancel_token("nevermind"))

    def test_never_mind(self):
        self.assertTrue(is_cancel_token("never mind"))

    def test_forget_it(self):
        self.assertTrue(is_cancel_token("forget it"))

    def test_stop_please(self):
        self.assertTrue(is_cancel_token("stop please"))


class CancelColloquialDeTests(unittest.TestCase):
    def test_abbrechen(self):
        self.assertTrue(is_cancel_token("abbrechen"))

    def test_stoppen(self):
        self.assertTrue(is_cancel_token("stoppen"))

    def test_vergiss_es(self):
        self.assertTrue(is_cancel_token("vergiss es"))

    def test_vergiss_das(self):
        self.assertTrue(is_cancel_token("vergiss das"))

    def test_stop_bitte(self):
        self.assertTrue(is_cancel_token("stop bitte"))


# ─── start-fresh intent (sub-state-scoped, journey-level) ────────


class StartFreshColloquialTests(unittest.TestCase):
    def test_lass_uns_nochmal_anfangen(self):
        self.assertIn("lass uns nochmal anfangen", _REVIEW_EMPTY_START_FRESH_TOKENS)

    def test_nochmal_anders(self):
        self.assertIn("nochmal anders", _REVIEW_EMPTY_START_FRESH_TOKENS)

    def test_neu_starten(self):
        self.assertIn("neu starten", _REVIEW_EMPTY_START_FRESH_TOKENS)

    def test_start_fresh(self):
        self.assertIn("start fresh", _REVIEW_EMPTY_START_FRESH_TOKENS)

    def test_restart(self):
        self.assertIn("restart", _REVIEW_EMPTY_START_FRESH_TOKENS)


# ─── Intentional fallthrough — AI router is the safety net ──────


class IntentionalFallthroughToAiRouterTests(unittest.TestCase):
    """Inputs that should NOT match the regex layer -- they fall
    through to chat_ai_route (Layer 3) by design."""

    def test_indirect_employment_phrasing_falls_through(self):
        # No "find/search/show ... job" verb-noun pair; no role token.
        # Should fall through to AI router for classification.
        self.assertIsNone(_route("I'd like to explore career opportunities matching my profile"))

    def test_long_natural_language_query_falls_through(self):
        self.assertIsNone(
            _route("I was wondering if there are any opportunities for someone like me")
        )

    def test_de_polite_form_falls_through(self):
        self.assertIsNone(_route("Könnten Sie mir bei einem Job helfen?"))

    def test_generic_greeting_en_falls_through(self):
        self.assertIsNone(_route("hello"))

    def test_generic_greeting_de_falls_through(self):
        self.assertIsNone(_route("hallo"))


if __name__ == "__main__":
    unittest.main()
