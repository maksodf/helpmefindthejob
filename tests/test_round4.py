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


if __name__ == "__main__":
    unittest.main()
