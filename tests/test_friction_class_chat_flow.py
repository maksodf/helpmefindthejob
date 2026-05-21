# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #76 sub-piece (a): chat-driven friction-class confirmation
flow contract.

After CV paste, the journey reply surfaces the inferred classification
with affordances to:
- type "change classification" → triggers friction_class_change command
- type "skip classification" → triggers friction_class_skip command

Both commands respect the same UserProfile.friction_class field as the
paste-branch classifier + Settings UI (Phase 2 #76 sub-piece d).
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.chat_router import REGISTRY, parse_slash_command, keyword_route
from company_discovery.friction_classifier import FRICTION_CLASS_LABELS


def _make_state() -> tuple[AppState, str]:
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    state = AppState(
        root / "company.sqlite3",
        root / "auth.sqlite3",
        root / "ai.json",
        root / "schedule.json",
        start_scheduler=False,
    )
    state._test_tmp = tmp  # noqa: SLF001
    user = state.auth_store.create_user("friction-flow@example.com", "secret-pass-12345678")
    return state, user.id


class FrictionClassChatRouterContract(unittest.TestCase):
    def test_slash_friction_routes_to_friction_class_change(self):
        name, _ = parse_slash_command("/friction aicha")
        self.assertEqual(name, "friction_class_change")

    def test_slash_skip_friction_routes_to_friction_class_skip(self):
        name, _ = parse_slash_command("/skip-friction")
        self.assertEqual(name, "friction_class_skip")

    def test_change_classification_keyword_routes_to_change(self):
        # keyword_route returns the command name (str) or None.
        self.assertEqual(keyword_route("change classification"), "friction_class_change")

    def test_skip_classification_keyword_routes_to_skip(self):
        self.assertEqual(keyword_route("skip classification"), "friction_class_skip")

    def test_de_klassifikation_aendern_keyword_routes_to_change(self):
        # DE: "klassifikation ändern" — change classification
        self.assertEqual(keyword_route("klassifikation ändern"), "friction_class_change")

    def test_change_command_has_slug_param(self):
        cmd = REGISTRY["friction_class_change"]
        self.assertEqual(len(cmd.params), 1)
        self.assertEqual(cmd.params[0].name, "slug")

    def test_skip_command_has_no_params(self):
        cmd = REGISTRY["friction_class_skip"]
        self.assertEqual(cmd.params, [])


class FrictionClassChatHandlerContract(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_change_with_list_arg_shows_seven_options(self):
        result = self.state.chat_handler_friction_class_change(
            self.user_id, {"slug": "list"}
        )
        self.assertTrue(result["ok"])
        # Every slug should appear in the listing message
        for slug in FRICTION_CLASS_LABELS:
            self.assertIn(slug, result["message"], msg=f"missing {slug}")
        # And the skip affordance
        self.assertIn("/skip-friction", result["message"])

    def test_change_with_empty_slug_shows_seven_options(self):
        result = self.state.chat_handler_friction_class_change(self.user_id, {})
        self.assertTrue(result["ok"])
        self.assertIn("aicha", result["message"])

    def test_change_with_valid_slug_updates_profile(self):
        result = self.state.chat_handler_friction_class_change(
            self.user_id, {"slug": "yusuf"}
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["frictionClass"], "yusuf")
        profile = self.state.profile_for(self.user_id)
        self.assertEqual(profile.friction_class, "yusuf")

    def test_change_with_unknown_slug_returns_error(self):
        result = self.state.chat_handler_friction_class_change(
            self.user_id, {"slug": "bogus-slug"}
        )
        self.assertFalse(result["ok"])
        self.assertIn("bogus-slug", result["message"])
        # No profile mutation on failure
        profile = self.state.profile_for(self.user_id)
        self.assertEqual(profile.friction_class, "")

    def test_change_with_uppercase_slug_normalises(self):
        result = self.state.chat_handler_friction_class_change(
            self.user_id, {"slug": "AICHA"}
        )
        self.assertTrue(result["ok"])
        profile = self.state.profile_for(self.user_id)
        self.assertEqual(profile.friction_class, "aicha")

    def test_skip_clears_existing_classification(self):
        profile = self.state.profile_for(self.user_id)
        profile.friction_class = "aicha"
        self.state.repository.save_user_profile(profile)

        result = self.state.chat_handler_friction_class_skip(self.user_id, {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["frictionClass"], "")
        refreshed = self.state.profile_for(self.user_id)
        self.assertEqual(refreshed.friction_class, "")

    def test_skip_is_idempotent_when_already_cleared(self):
        result = self.state.chat_handler_friction_class_skip(self.user_id, {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["frictionClass"], "")


class JourneyPasteSuffixContract(unittest.TestCase):
    """The paste-branch reply now appends a non-gating confirmation
    note showing the inferred class + affordances to change/skip."""

    def test_paste_reply_includes_classification_label_when_confident(self):
        from company_discovery.journey import (
            UserJourney,
            _advance_cv_check,
            PHASE_CV_CHECK,
        )

        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        # looks_like_pasted_cv requires >=80 chars + at least one CV
        # marker (email / dates / section header / bullets / phone).
        # We include a section header, dates, and email so the paste
        # branch fires.
        cv_text = (
            "Aïcha Ben Salah — Berlin\n"
            "Email: aicha@example.invalid\n\n"
            "EXPERIENCE\n"
            "- Hôpital Habib Bourguiba, Tunis — Krankenpflegerin, 2018-2025\n"
            "  Geriatric ward 2 years; general medical ward 5 years.\n"
            "\n"
            "RESIDENCY STATUS\n"
            "- §16d AufenthG (visa for purpose of recognition of foreign "
            "qualification) since 2025-02. Anerkennungsverfahren at BIBB."
        )
        result = _advance_cv_check(journey, cv_text, has_existing_cv=False)
        # The reply ends with the affordance text inviting the user
        # to change / skip the classification.
        self.assertIn("change classification", result.reply)
        self.assertIn("skip classification", result.reply)
        # The label for the resolved class (Aïcha) appears in the
        # suffix so the user knows what was inferred.
        self.assertIn(
            FRICTION_CLASS_LABELS["aicha"],
            result.reply,
            msg=f"Aicha label missing from reply:\n{result.reply}",
        )

    def test_paste_reply_no_suffix_when_no_confident_match(self):
        from company_discovery.journey import (
            UserJourney,
            _advance_cv_check,
            PHASE_CV_CHECK,
        )

        # Generic resume — meets looks_like_pasted_cv shape (email +
        # length + section header) but has NO regulatory markers and
        # NO scored-pattern hits, so classification returns "".
        journey = UserJourney(phase=PHASE_CV_CHECK, cv_status="unknown")
        cv_text = (
            "Generic Resume\n"
            "Email: someone@example.invalid\n\n"
            "EXPERIENCE\n"
            "- Generic Company, City — Generic Role, 2018-2025\n"
            "  Worked on generic projects, delivered generic results.\n"
            "  Built generic features. Mentored generic colleagues."
        )
        result = _advance_cv_check(journey, cv_text, has_existing_cv=False)
        # When classification produces no slug, the affordance suffix
        # is not emitted (avoids confusing the user with "you're in
        # the ... process" when nothing matched).
        self.assertNotIn("change classification", result.reply)
        self.assertNotIn("skip classification", result.reply)


if __name__ == "__main__":
    unittest.main()
