# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-4 tests: B1 auto-fit + B3 CV tailoring closeout."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import (
    build_auto_fit_prompt,
    build_cv_tailoring_prompt,
    parse_auto_fit_output,
)
from company_discovery.models import DiscoveredJob, ImportedJob, UserProfile


class AutoFitPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.job = DiscoveredJob(
            user_id="u1",
            company_id="c1",
            source_url="https://acme.example.com/jobs/42",
            title="Senior Backend Engineer",
            location="Berlin",
            raw_description="We need backend engineers fluent in Python.",
        )
        self.provider = AIProviderConfig(provider_id="openai", invocation_mode="api")

    def test_prompt_contains_score_format(self) -> None:
        result = build_auto_fit_prompt(self.job, "Acme", self.provider, profile=None)
        self.assertIn("SCORE:", result["prompt"])
        self.assertIn("REASON:", result["prompt"])
        self.assertIn("Senior Backend Engineer", result["prompt"])

    def test_prompt_includes_persona_from_profile(self) -> None:
        profile = UserProfile(user_id="u1", persona_id="tech", target_roles=["backend"])
        result = build_auto_fit_prompt(self.job, "Acme", self.provider, profile)
        self.assertIn("Technology", result["prompt"])

    def test_prompt_truncates_long_description(self) -> None:
        self.job.raw_description = "X" * 5000
        result = build_auto_fit_prompt(self.job, "Acme", self.provider, profile=None)
        self.assertLess(result["prompt"].count("X"), 1600)


class ParseAutoFitOutputTests(unittest.TestCase):
    def test_well_formed_output(self) -> None:
        score, reason, gaps = parse_auto_fit_output(
            "SCORE: 78\nREASON: strong overlap with backend Python at marketplace scale"
        )
        self.assertEqual(score, 0.78)
        self.assertIn("backend", reason)
        self.assertEqual(gaps, [])

    def test_clamps_above_100(self) -> None:
        score, _, _ = parse_auto_fit_output("SCORE: 150\nREASON: ignored")
        self.assertEqual(score, 1.0)

    def test_no_score_returns_none(self) -> None:
        score, reason, gaps = parse_auto_fit_output("the model rambled instead")
        self.assertIsNone(score)
        self.assertIsNone(reason)
        self.assertEqual(gaps, [])

    def test_handles_dash_separator(self) -> None:
        score, reason, _ = parse_auto_fit_output("score - 42\nreason - some reason")
        self.assertEqual(score, 0.42)
        self.assertEqual(reason, "some reason")

    def test_truncates_very_long_reason(self) -> None:
        long = "x" * 500
        _, reason, _ = parse_auto_fit_output(f"SCORE: 50\nREASON: {long}")
        self.assertLessEqual(len(reason or ""), 280)

    def test_extracts_gaps(self) -> None:
        _, _, gaps = parse_auto_fit_output(
            "SCORE: 65\nREASON: solid Python\nGAPS: Kubernetes, Terraform, dbt"
        )
        self.assertEqual(gaps, ["Kubernetes", "Terraform", "dbt"])

    def test_caps_gaps_at_three(self) -> None:
        _, _, gaps = parse_auto_fit_output("SCORE: 65\nREASON: ok\nGAPS: a, b, c, d, e, f")
        self.assertEqual(gaps, ["a", "b", "c"])

    def test_empty_gaps_line_is_empty_list(self) -> None:
        _, _, gaps = parse_auto_fit_output("SCORE: 92\nREASON: very strong fit\nGAPS:")
        self.assertEqual(gaps, [])


class CvTailoringPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://acme.example.com/job/1",
            title="Staff Backend Engineer",
            company_name="Acme",
            description="Build a high-throughput payments ledger.",
        )
        self.provider = AIProviderConfig(provider_id="openai", invocation_mode="api")

    def test_prompt_demands_no_fabrication(self) -> None:
        result = build_cv_tailoring_prompt(self.job, self.provider, profile=None)
        self.assertIn("without inventing facts", result["prompt"])

    def test_prompt_inlines_cv_text(self) -> None:
        profile = UserProfile(
            user_id="u1",
            persona_id="tech",
            cv_text="Backend at Stripe for 6 years. Distinct marker QQQ123.",
        )
        result = build_cv_tailoring_prompt(self.job, self.provider, profile)
        self.assertIn("QQQ123", result["prompt"])

    def test_prompt_lists_required_sections(self) -> None:
        result = build_cv_tailoring_prompt(self.job, self.provider, profile=None)
        for section in (
            "Tailored CV",
            "Diff vs. original",
            "Missing evidence",
            "Suggested follow-up edits",
        ):
            self.assertIn(section, result["prompt"])

    def test_prompt_always_contains_friction_acknowledgment_instruction(self) -> None:
        """R12-polish remediation (2026-05-19): the friction-context
        acknowledgment instruction must appear in every CV-tailoring
        prompt regardless of whether ``friction_keywords`` is supplied.
        The bias-testing polish report's criterion-(d) finding drove
        this contract. See ``docs/grant/bias-testing-2026-05-18-polish.md``.
        """
        result = build_cv_tailoring_prompt(self.job, self.provider, profile=None)
        self.assertIn("Friction-context acknowledgment", result["prompt"])
        self.assertIn("§16d", result["prompt"])
        self.assertIn("Anerkennung", result["prompt"])
        self.assertIn("Wiedereinstieg", result["prompt"])
        self.assertIn("TVöD", result["prompt"])

    def test_prompt_inlines_persona_friction_keywords_when_supplied(self) -> None:
        """When ``friction_keywords`` is supplied the prompt surfaces
        them verbatim and instructs the model to use the candidate's
        own vocabulary."""
        keywords = ["§16d", "Anerkennung", "BIBB", "Anabin"]
        result = build_cv_tailoring_prompt(
            self.job,
            self.provider,
            profile=None,
            friction_keywords=keywords,
        )
        self.assertIn("documented friction-context vocabulary", result["prompt"])
        for kw in keywords:
            self.assertIn(kw, result["prompt"])
        self.assertIn("verbatim", result["prompt"])

    def test_prompt_backward_compat_when_friction_keywords_absent(self) -> None:
        """Backward-compat: callers that omit ``friction_keywords``, or
        pass ``None`` / empty list, still get a well-formed prompt with
        the generic friction-context instruction but NO
        candidate-specific vocabulary line."""
        for kw_arg in (None, [], ["", "   ", None]):  # type: ignore[list-item]
            result = build_cv_tailoring_prompt(
                self.job,
                self.provider,
                profile=None,
                friction_keywords=kw_arg,
            )
            self.assertIn("Friction-context acknowledgment", result["prompt"])
            self.assertNotIn("documented friction-context vocabulary", result["prompt"])

    def test_prompt_deduplicates_friction_keywords(self) -> None:
        """Whitespace-only entries are dropped; duplicates collapse."""
        keywords = ["§16d", "  ", "§16d", "Anerkennung", "", "Anerkennung"]
        result = build_cv_tailoring_prompt(
            self.job,
            self.provider,
            profile=None,
            friction_keywords=keywords,
        )
        # §16d and Anerkennung should each appear once in the vocab line.
        # The instruction-example list also mentions §16d and Anerkennung
        # as illustrative friction vocabulary, so count occurrences in
        # the vocab-line slice only.
        vocab_line_start = result["prompt"].find("documented friction-context vocabulary")
        vocab_line_end = result["prompt"].find("\n", vocab_line_start + 100)
        vocab_segment = result["prompt"][vocab_line_start:vocab_line_end]
        self.assertEqual(vocab_segment.count("§16d"), 1)
        self.assertEqual(vocab_segment.count("Anerkennung"), 1)


class FrictionKeywordsLookupTests(unittest.TestCase):
    """Contract for ``persona_fixtures.friction_keywords_for`` — the
    chat-router → CV-tailoring production wiring helper added 2026-05-19.

    The bias-test path verified at 92.9% criterion-(d) pass-rate
    (`docs/grant/bias-testing-2026-05-19.md`) uses
    `persona.friction_keywords` from the seven-panel fixtures.
    `friction_keywords_for(persona_id)` is the production wrapper the
    chat-router uses so real users get the same persona-specific
    vocab line.
    """

    def test_returns_keywords_for_each_panel_persona(self) -> None:
        from company_discovery.persona_fixtures import (
            PERSONAS,
            friction_keywords_for,
        )

        for persona in PERSONAS:
            kw = friction_keywords_for(persona.slug)
            self.assertEqual(
                kw,
                list(persona.friction_keywords),
                f"{persona.slug}: helper returned {kw!r}, expected {list(persona.friction_keywords)!r}",
            )
            self.assertGreater(len(kw), 0, f"{persona.slug}: expected ≥1 friction keyword")

    def test_returns_empty_for_non_panel_persona_id(self) -> None:
        from company_discovery.persona_fixtures import friction_keywords_for

        # Production job-category persona_ids defined in
        # company_discovery/personas.py — should return [] so the
        # generic friction-context instruction (always present in the
        # prompt) handles them without a persona-specific vocab line.
        for pid in ("healthcare-management", "tech", "marketing", "finance", "data"):
            self.assertEqual(
                friction_keywords_for(pid),
                [],
                f"non-panel persona_id {pid!r} should return empty list",
            )

    def test_returns_empty_for_none_and_empty_string(self) -> None:
        from company_discovery.persona_fixtures import friction_keywords_for

        self.assertEqual(friction_keywords_for(None), [])
        self.assertEqual(friction_keywords_for(""), [])

    def test_returns_fresh_list_not_shared_reference(self) -> None:
        """Caller mutation of the returned list must not corrupt the
        fixture data."""
        from company_discovery.persona_fixtures import (
            PERSONAS,
            friction_keywords_for,
        )

        kw = friction_keywords_for("aicha")
        kw.append("MUTATED")
        # Re-fetch — the second call must not see the mutation.
        kw2 = friction_keywords_for("aicha")
        self.assertNotIn("MUTATED", kw2)
        # And the fixture itself stays clean.
        aicha = next(p for p in PERSONAS if p.slug == "aicha")
        self.assertNotIn("MUTATED", aicha.friction_keywords)


class ChatRouterCvTailoringWiringTests(unittest.TestCase):
    """End-to-end wiring: ``chat_handler_tailor_cv`` resolves the user's
    persona_id, looks up ``friction_keywords``, and passes them through
    to ``execute_cv_tailoring``. Verified by patching
    ``execute_cv_tailoring`` at the call site and capturing the keyword
    argument.

    Two scenarios:
    - Panel persona (Aïcha) → expects Aïcha's friction_keywords.
    - Non-panel persona ("healthcare-management") → expects [].
    """

    def _build_state_and_user(self, persona_id: str):
        """Stand up a minimal AppState with a seeded user whose
        profile carries the given ``persona_id`` (which may be a
        seven-panel slug like ``aicha`` — set via the same
        repository-direct write that ``scripts/seed-personas.py`` uses,
        bypassing ``update_profile``'s production-PERSONAS
        whitelist)."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from app import AppState
        from company_discovery.models import ImportedJob, UserProfile

        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        state = AppState(
            data_path=base / "data.sqlite3",
            auth_path=base / "auth.sqlite3",
            ai_config_path=base / "ai.json",
            schedule_path=base / "schedule.json",
            admin_audit_path=base / "admin_audit.log",
            token_path=base / "tokens.sqlite3",
            quota_path=base / "quotas.sqlite3",
            scheduler_path=base / "scheduler.sqlite3",
            start_scheduler=False,
        )
        user = state.auth_store.create_user(f"{persona_id}@wiring.test", "supersecret-1234")
        # Mirror the seed-personas.py pattern: write the profile
        # directly to the repository so non-production persona_ids
        # (panel slugs like "aicha") can be tested without tripping
        # update_profile's unknown_persona validation.
        profile = UserProfile(
            user_id=user.id,
            persona_id=persona_id,
            cv_text="Synthetic CV body for wiring test (not used by the mock).",
        )
        state.repository.save_user_profile(profile)
        # Seed an imported job for the handler to find.
        imported = ImportedJob(
            user_id=user.id,
            company_id="c-wiring",
            discovered_job_id="dj-wiring",
            source_url="https://demo.directjob-scout.example/job/wiring",
            title="Pflegefachkraft",
            company_name="Test Clinic",
            location="Berlin",
            description="Anerkennungsfreundliche Pflegestelle.",
        )
        state.repository.save_imported_job(imported)
        return state, user, imported

    def _invoke_and_capture(self, state, user, imported):
        """Patch ``execute_cv_tailoring`` and invoke the chat handler;
        return the captured kwargs."""
        from unittest.mock import MagicMock, patch

        from company_discovery.analysis import AnalysisExecutionResult

        captured: dict = {}

        def _fake(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return AnalysisExecutionResult(
                status="completed",
                provider_id="ollama",
                invocation_mode="local_http",
                output="Tailored CV output (fake).",
            )

        with patch("company_discovery.analysis.execute_cv_tailoring", _fake):
            with patch("app._ai_consent_satisfied", return_value=True):
                result = state.chat_handler_tailor_cv(user.id, {"importedJobId": imported.id})
        self.assertTrue(result.get("ok"), f"handler returned {result!r}")
        return captured

    def test_panel_persona_receives_persona_specific_friction_keywords(self) -> None:
        """When the user's persona_id matches a panel persona (Aïcha),
        the chat handler passes that persona's friction_keywords to
        execute_cv_tailoring."""
        from company_discovery.persona_fixtures import friction_keywords_for

        state, user, imported = self._build_state_and_user(persona_id="aicha")
        captured = self._invoke_and_capture(state, user, imported)
        kwargs = captured["kwargs"]
        self.assertIn("friction_keywords", kwargs)
        self.assertEqual(kwargs["friction_keywords"], friction_keywords_for("aicha"))
        self.assertIn("Anerkennung", kwargs["friction_keywords"])
        self.assertIn("§16d", kwargs["friction_keywords"])

    def test_non_panel_persona_receives_empty_friction_keywords(self) -> None:
        """When the user's persona_id is a production job-category
        persona (no panel entry), the chat handler passes []. The
        always-present generic friction-context instruction in the
        prompt still applies — verified via build_cv_tailoring_prompt
        tests."""
        state, user, imported = self._build_state_and_user(persona_id="healthcare-management")
        captured = self._invoke_and_capture(state, user, imported)
        kwargs = captured["kwargs"]
        self.assertIn("friction_keywords", kwargs)
        self.assertEqual(kwargs["friction_keywords"], [])


if __name__ == "__main__":
    unittest.main()
