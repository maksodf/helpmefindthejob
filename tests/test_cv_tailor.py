"""R24.9 — structured tailoring tests.

Verifies that the tailor patch is ONLY allowed to modify summary +
bullet ordering. Everything else (titles, companies, dates, etc.)
is locked.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company_discovery import analysis as A
from company_discovery import cv_tailor as T
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.cv_schema import (
    CvDocument, CvExperience, MAX_SUMMARY,
)


PROVIDER = AIProviderConfig(
    provider_id="openai", invocation_mode="api",
    credential_reference="OPENAI_API_KEY",
)


def _base_doc() -> CvDocument:
    return CvDocument(
        full_name="Anna",
        summary="Generic summary that should be tailored.",
        experience=[
            CvExperience(
                title="Senior Engineer", company="ACME",
                start="2020", end="present",
                bullets=[
                    "Shipped feature A",
                    "Mentored 3 engineers",
                    "Reduced p99 latency by 30%",
                ],
            ),
            CvExperience(
                title="Engineer", company="OldCo",
                start="2017", end="2020",
                bullets=["Wrote Python", "Wrote tests"],
            ),
        ],
        skills=["Python", "Go"],
    )


class ApplyPatchTests(unittest.TestCase):
    """The patcher must enforce the lock: summary + bullet order only."""

    def test_summary_replaced(self):
        doc = _base_doc()
        out = T.apply_tailor_patch(
            doc, {"summary": "New tailored summary."})
        self.assertEqual(out.summary, "New tailored summary.")

    def test_bullets_reordered_within_role(self):
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [
                {"role_index": 0, "bullet_order": [2, 0, 1]},
            ],
        })
        self.assertEqual(out.experience[0].bullets[0],
                          "Reduced p99 latency by 30%")
        self.assertEqual(out.experience[0].bullets[1], "Shipped feature A")
        self.assertEqual(out.experience[0].bullets[2],
                          "Mentored 3 engineers")
        # Role 1 was untouched.
        self.assertEqual(out.experience[1].bullets[0], "Wrote Python")

    def test_dropped_bullets_appended_not_lost(self):
        """If the model only picks 1 bullet, the others stay in
        the document (just deprioritised)."""
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [{"role_index": 0, "bullet_order": [2]}],
        })
        # First bullet is the tailored choice.
        self.assertEqual(out.experience[0].bullets[0],
                          "Reduced p99 latency by 30%")
        # Other 2 bullets remain — none lost.
        self.assertEqual(len(out.experience[0].bullets), 3)
        self.assertIn("Shipped feature A", out.experience[0].bullets)
        self.assertIn("Mentored 3 engineers", out.experience[0].bullets)

    def test_invalid_bullet_index_silently_ignored(self):
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [{"role_index": 0, "bullet_order": [99, "x"]}],
        })
        # Original bullets preserved.
        self.assertEqual(len(out.experience[0].bullets), 3)

    def test_role_index_out_of_range_ignored(self):
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [{"role_index": 99, "bullet_order": [0]}],
        })
        self.assertEqual(out.experience[0].bullets[0], "Shipped feature A")

    def test_cannot_rewrite_title(self):
        """Defense-in-depth — even if the model returns a 'title'
        key, the patcher ignores it."""
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [
                {"role_index": 0, "title": "EVIL Rewrite",
                  "bullet_order": [0]},
            ],
        })
        self.assertEqual(out.experience[0].title, "Senior Engineer")

    def test_cannot_rewrite_company_or_dates(self):
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [
                {"role_index": 0, "company": "X",
                  "start": "1999", "end": "2000",
                  "bullet_order": [0]},
            ],
        })
        self.assertEqual(out.experience[0].company, "ACME")
        self.assertEqual(out.experience[0].start, "2020")
        self.assertEqual(out.experience[0].end, "present")

    def test_cannot_inject_new_bullets(self):
        doc = _base_doc()
        out = T.apply_tailor_patch(doc, {
            "experience": [
                {"role_index": 0,
                  "bullets": ["INVENTED Achievement"],
                  "bullet_order": [0]},
            ],
        })
        for b in out.experience[0].bullets:
            self.assertNotIn("INVENTED", b)

    def test_non_dict_patch_returns_original(self):
        doc = _base_doc()
        for junk in (None, [], "string", 42):
            out = T.apply_tailor_patch(doc, junk)
            self.assertEqual(out.summary, doc.summary)
            self.assertEqual(len(out.experience), 2)

    def test_summary_length_capped(self):
        doc = _base_doc()
        huge = "A" * 10000
        out = T.apply_tailor_patch(doc, {"summary": huge})
        self.assertLessEqual(len(out.summary), MAX_SUMMARY)

    def test_original_doc_unchanged_when_patch_applied(self):
        """``apply_tailor_patch`` must operate on a deep copy."""
        doc = _base_doc()
        before_bullets = list(doc.experience[0].bullets)
        T.apply_tailor_patch(doc, {
            "experience": [{"role_index": 0, "bullet_order": [2, 0, 1]}],
        })
        self.assertEqual(doc.experience[0].bullets, before_bullets)


class TailorEndToEndTests(unittest.TestCase):
    """Stub the LLM and verify the full pipeline."""

    def test_happy_path_with_stubbed_llm(self):
        canned_json = """{
            "summary": "Backend engineer optimised for low-latency systems.",
            "experience": [
                {"role_index": 0, "bullet_order": [2, 0]}
            ]
        }"""

        def fake_dispatch(prompt, provider, runtime_credential, *,
                            task="", record_call=None):
            return A.AnalysisExecutionResult(
                status="completed",
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt=prompt, output=canned_json,
                input_tokens=500, output_tokens=120,
                model_used="claude-sonnet-4-6",
            )

        with patch.object(A, "_dispatch_provider", side_effect=fake_dispatch):
            out = T.tailor_cv_for_job(
                _base_doc(),
                "Looking for a backend engineer with strong latency focus.",
                PROVIDER)
        self.assertEqual(
            out.summary,
            "Backend engineer optimised for low-latency systems.")
        self.assertEqual(out.experience[0].bullets[0],
                          "Reduced p99 latency by 30%")

    def test_malformed_llm_output_returns_original(self):
        def fake_dispatch(prompt, provider, runtime_credential, *,
                            task="", record_call=None):
            return A.AnalysisExecutionResult(
                status="completed",
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt=prompt, output="not valid json",
            )

        with patch.object(A, "_dispatch_provider", side_effect=fake_dispatch):
            out = T.tailor_cv_for_job(
                _base_doc(), "anything", PROVIDER)
        # Unchanged.
        self.assertEqual(out.summary,
                          "Generic summary that should be tailored.")

    def test_provider_error_returns_original(self):
        def fake_dispatch(prompt, provider, runtime_credential, *,
                            task="", record_call=None):
            return A.AnalysisExecutionResult(
                status="provider_error",
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt=prompt, error="HTTP 500",
            )

        with patch.object(A, "_dispatch_provider", side_effect=fake_dispatch):
            out = T.tailor_cv_for_job(
                _base_doc(), "anything", PROVIDER)
        self.assertEqual(out.summary,
                          "Generic summary that should be tailored.")


if __name__ == "__main__":
    unittest.main()
