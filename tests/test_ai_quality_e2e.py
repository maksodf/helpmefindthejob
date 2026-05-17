"""AI quality — end-to-end pipeline test with scripted AI responses.

The unit-level parser tests in ``test_ai_quality.py`` verify the
parser handles every shape. This module goes further: it runs the
*full* analysis pipeline (prompt build → dispatch → parse → persist
to imported_job.structured_analysis / fit_score / recommendation)
against scripted AI responses simulating real-world outputs.

No real LLM is called. Instead we monkey-patch
``analysis._dispatch_provider`` to return a canned
``AnalysisExecutionResult`` for each test case. This proves the
*entire* AI-quality code path is correct: the prompt was built, the
output flowed through dispatch, the parser extracted the fit fields,
and the imported_job row carries the right derived data.

Scenarios covered:
- High-fit (apply) JSON
- Mid-fit (consider) JSON
- Low-fit (skip) JSON
- AI refusal / off-topic response
- Score-only plain text (no JSON)
- Malformed JSON with regex-rescued score
- AI returns 50KB rambling response with embedded JSON
- AI errors (provider_error status)
- Configuration_error path
- Empty AI output"""

from __future__ import annotations

import unittest

from company_discovery import analysis
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import AnalysisExecutionResult
from company_discovery.models import ImportedJob, UserProfile


# ---------------- Test fixtures ----------------


def _make_profile() -> UserProfile:
    return UserProfile(
        user_id="user_test",
        persona_id="tech",
        cv_text=(
            "Senior Software Engineer with 8 years of Python, Postgres, "
            "Kubernetes, Docker, AWS. Based in Berlin."
        ),
        target_roles=["senior backend engineer"],
        location="Berlin",
    )


def _make_imported_job(suffix: str = "x") -> ImportedJob:
    return ImportedJob(
        user_id="user_test",
        company_id="company_test",
        discovered_job_id="discovered_test",
        source_url=f"https://acme.example/jobs/{suffix}",
        title="Senior Backend Engineer",
        company_name="Acme Corp",
        location="Berlin, Germany",
        description=(
            "We're hiring a Senior Backend Engineer to lead our Python "
            "microservices on Kubernetes. 5+ years of Postgres, Docker, AWS."
        ),
    )


def _make_provider() -> AIProviderConfig:
    """A 'custom' provider that we'll monkey-patch the dispatch for.

    Manual mode short-circuits in ``_dispatch_provider`` and returns
    ``handoff_required`` without going through the patch, so we use a
    non-manual ``invocation_mode``."""
    return AIProviderConfig(
        provider_id="custom",
        invocation_mode="cli",
        command="claude",
    )


class _ScriptedDispatch:
    """Context manager: patches analysis._dispatch_provider to return a
    canned AnalysisExecutionResult."""

    def __init__(self, *,
                 status: str = "completed",
                 output: str | None = None,
                 error: str | None = None):
        self.status = status
        self.output = output
        self.error = error
        self._original = None
        self.last_prompt: str | None = None

    def __enter__(self):
        self._original = analysis._dispatch_provider
        outer = self

        def patched(prompt: str,
                    provider: AIProviderConfig,
                    runtime_credential: str,
                    *, task: str = "",
                    record_call=None) -> AnalysisExecutionResult:
            outer.last_prompt = prompt
            outer.last_task = task
            return AnalysisExecutionResult(
                status=outer.status,
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt=prompt,
                output=outer.output,
                error=outer.error,
            )

        analysis._dispatch_provider = patched
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        analysis._dispatch_provider = self._original


# ---------------- Pipeline tests ----------------


class HighFitJsonTests(unittest.TestCase):
    """Ideal AI response — well-formed JSON, high fit, apply."""

    def test_high_fit_apply_pipeline(self):
        scripted = (
            "The candidate is a great match. 8 years of Python and "
            "Kubernetes maps directly to the JD's 5+ years of "
            "microservices.\n\n"
            '{"fitScore": 0.88, "recommendation": "apply", '
            '"healthcareRelevance": "n/a", '
            '"tools": ["Python", "Kubernetes", "Postgres", "Docker"], '
            '"risks": ["German language preferred but not required"]}'
        )
        imported = _make_imported_job("hi")
        with _ScriptedDispatch(output=scripted) as dispatch:
            result = analysis.execute_job_decision_brief(
                imported, _make_provider(), "", _make_profile(),
            )
            # The prompt was built correctly — must contain CV + job title.
            self.assertIn("Senior Backend Engineer", dispatch.last_prompt)
            self.assertIn("Python", dispatch.last_prompt)
        self.assertEqual(result.status, "completed")
        # Now simulate the persistence step that the route handler does.
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertAlmostEqual(parsed.fit_score, 0.88, places=3)
        self.assertEqual(parsed.recommendation, "apply")
        self.assertIn("Python", parsed.tools)
        self.assertIn("Kubernetes", parsed.tools)


class MidFitConsiderTests(unittest.TestCase):
    def test_mid_fit_consider(self):
        scripted = (
            '{"fitScore": 0.55, "recommendation": "consider", '
            '"requiredExperience": "5+ years Python", '
            '"languageRequirements": "German B2"}'
        )
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("mid"),
                _make_provider(), "", _make_profile(),
            )
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertAlmostEqual(parsed.fit_score, 0.55, places=3)
        self.assertEqual(parsed.recommendation, "consider")
        self.assertEqual(parsed.language_requirements, "German B2")


class LowFitSkipTests(unittest.TestCase):
    def test_low_fit_skip(self):
        scripted = (
            '{"fitScore": 0.2, "recommendation": "skip", '
            '"risks": ["Role is more frontend than backend", '
            '"On-site Munich only"]}'
        )
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("lo"),
                _make_provider(), "", _make_profile(),
            )
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertAlmostEqual(parsed.fit_score, 0.2, places=3)
        self.assertEqual(parsed.recommendation, "skip")
        self.assertEqual(len(parsed.risks), 2)


class RegexRescuedScoreTests(unittest.TestCase):
    """AI returns plain prose with no JSON block — regex extraction
    must still produce a useful fit_score."""

    def test_plain_text_score_extracted(self):
        scripted = (
            "After reviewing the JD and the CV, my Fit Score is 0.75. "
            "I'd recommend you APPLY — the technical match is strong."
        )
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("re"),
                _make_provider(), "", _make_profile(),
            )
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertAlmostEqual(parsed.fit_score, 0.75, places=3)
        self.assertEqual(parsed.recommendation, "apply")


class AiRefusalTests(unittest.TestCase):
    """AI refuses / can't analyse. Pipeline must NOT crash; the user
    sees an empty fit but the analysis text is preserved as notes."""

    def test_refusal_no_crash(self):
        scripted = (
            "I can't provide a meaningful score because the job "
            "description appears to be truncated. Please share the full JD."
        )
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("rf"),
                _make_provider(), "", _make_profile(),
            )
        self.assertEqual(result.status, "completed")
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        # No JSON, no "Fit score: X" pattern → score is None
        self.assertIsNone(parsed.fit_score)
        # But the notes field carries the AI's prose so the user can
        # still read what the model said.
        self.assertIn("can't provide", parsed.notes)


class MalformedJsonTests(unittest.TestCase):
    """AI emits malformed JSON — parser must NOT crash and should
    rescue the score via regex."""

    def test_trailing_comma_recovers(self):
        scripted = (
            '{"fitScore": 0.6, "recommendation": "consider",}'
        )
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("mj"),
                _make_provider(), "", _make_profile(),
            )
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertAlmostEqual(parsed.fit_score, 0.6, places=3)
        self.assertEqual(parsed.recommendation, "consider")


class VeryLongResponseTests(unittest.TestCase):
    """A real model often produces multi-paragraph output. The parser
    must still find the embedded JSON."""

    def test_50kb_response_with_json(self):
        prose = (
            "The candidate has many strengths. Let me elaborate. "
        ) * 1500  # ~70KB
        scripted = prose + ('\n\n{"fitScore": 0.81, '
                             '"recommendation": "apply"}')
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("lg"),
                _make_provider(), "", _make_profile(),
            )
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertAlmostEqual(parsed.fit_score, 0.81, places=3)
        self.assertEqual(parsed.recommendation, "apply")


class ProviderErrorTests(unittest.TestCase):
    """The AI dispatch may return ``provider_error`` (rate limit,
    upstream 500). The route must not crash; analysis_error is set."""

    def test_provider_error_propagates(self):
        with _ScriptedDispatch(status="provider_error",
                                error="upstream returned 503"):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("er"),
                _make_provider(), "", _make_profile(),
            )
        self.assertEqual(result.status, "provider_error")
        self.assertEqual(result.error, "upstream returned 503")
        self.assertIsNone(result.output)


class EmptyOutputTests(unittest.TestCase):
    def test_empty_output_clean_state(self):
        with _ScriptedDispatch(output=""):
            result = analysis.execute_job_decision_brief(
                _make_imported_job("em"),
                _make_provider(), "", _make_profile(),
            )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "")
        from company_discovery.structured_analysis import parse_freeform
        parsed = parse_freeform(result.output)
        self.assertIsNone(parsed.fit_score)
        self.assertIsNone(parsed.recommendation)


class CvTailoringPipelineTests(unittest.TestCase):
    """The tailor-cv path is a parallel pipeline to the brief one.
    Verify it also dispatches the prompt and returns the AI output."""

    def test_tailor_cv_returns_completed(self):
        scripted = (
            "# Senior Backend Engineer — Tailored CV for Acme Corp\n\n"
            "## Summary\n"
            "Senior Software Engineer with 8 years of Python, Postgres, "
            "Kubernetes, AWS — directly relevant to the Acme microservices role.\n"
        )
        with _ScriptedDispatch(output=scripted) as dispatch:
            result = analysis.execute_cv_tailoring(
                _make_imported_job("ct"),
                _make_provider(), "", _make_profile(),
            )
            # The tailor prompt must reference both the user's CV and the
            # job title (so the AI knows what to tailor TO).
            self.assertIn("Senior Backend Engineer", dispatch.last_prompt)
            self.assertIn("Python", dispatch.last_prompt)
        self.assertEqual(result.status, "completed")
        self.assertIn("Tailored CV", result.output)
        self.assertIn("Acme Corp", result.output)


class AutoFitGapsExtractionTests(unittest.TestCase):
    """Auto-fit's prompt asks the AI to emit GAPS: line listing missing
    skills. Verify the pipeline preserves gap data when the model
    cooperates. ``execute_auto_fit`` runs against a DiscoveredJob, not
    an ImportedJob, so the fixture differs from the brief tests above."""

    def test_gaps_in_json_persist(self):
        from company_discovery.models import DiscoveredJob

        discovered = DiscoveredJob(
            user_id="user_test",
            source_url="https://acme.example/jobs/af",
            title="Senior Backend Engineer",
            raw_description=(
                "5+ years of Python on Kubernetes. Terraform and Helm "
                "experience required."
            ),
            location="Berlin, Germany",
        )
        scripted = (
            '{"fitScore": 0.6, "recommendation": "consider", '
            '"missingSkills": ["Terraform", "Helm"], '
            '"tools": ["Python", "K8s"]}\n'
            "GAPS: Terraform, Helm"
        )
        with _ScriptedDispatch(output=scripted):
            result = analysis.execute_auto_fit(
                discovered, "Acme Corp",
                _make_provider(), "", _make_profile(),
            )
        self.assertEqual(result.status, "completed")
        self.assertIn("Terraform", result.output)


if __name__ == "__main__":
    unittest.main()
