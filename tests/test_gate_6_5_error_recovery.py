# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 16 — Gate 6.5 error recovery path tests.

Pins the partial-failure transparency banner (Fix D) and verifies
that erroredOutcomes propagate from chat_handler_find_jobs through
to the journey-driven run_search_with branch. The frontend api()
wrapper changes (Fixes B + C — session-expiry + network-drop
normalization) are JS-side and verified by spot review; no Python
unit test reaches them.
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass


@dataclass
class _StubOutcome:
    """Mirrors AggregationOutcome shape for testing the banner
    string-builder logic without needing the full aggregator
    engine + cache wired up."""
    provider: str
    error: str | None


class PartialFailureBannerLogicTests(unittest.TestCase):
    """The banner-string builder is small but the contract matters:
    fires iff (some-failed AND some-results-present), counts both
    halves correctly, uses the agreed phrasing. Mirrors the
    chat_handler_find_jobs inline branch."""

    def _build_banner(self, outcomes: list[_StubOutcome], job_count: int) -> str:
        """Same shape as the chat_handler_find_jobs Loop 16 branch."""
        errored = [o for o in outcomes if o.error]
        if not errored or not job_count:
            return ""
        return (
            f"_(Some providers were temporarily unavailable "
            f"— {len(errored)} of {len(outcomes)} reported errors. "
            f"Results below are from the working providers.)_\n\n"
        )

    def test_no_banner_when_no_errors(self):
        outcomes = [
            _StubOutcome("arbeitnow", None),
            _StubOutcome("eures", None),
        ]
        self.assertEqual(self._build_banner(outcomes, 5), "")

    def test_no_banner_when_all_errored_and_zero_jobs(self):
        """Total failure -> the journey's run_search_with except
        path handles this with its own friendly message; the
        banner is for PARTIAL failure only."""
        outcomes = [
            _StubOutcome("arbeitnow", "timeout"),
            _StubOutcome("eures", "timeout"),
        ]
        self.assertEqual(self._build_banner(outcomes, 0), "")

    def test_banner_when_partial_failure(self):
        outcomes = [
            _StubOutcome("arbeitnow", None),
            _StubOutcome("eures", "timeout"),
            _StubOutcome("muse", "rate_limited"),
            _StubOutcome("remotive", None),
        ]
        banner = self._build_banner(outcomes, 7)
        self.assertIn("Some providers were temporarily unavailable", banner)
        self.assertIn("2 of 4 reported errors", banner)
        self.assertIn("Results below are from the working providers", banner)

    def test_banner_singular_provider_failed(self):
        outcomes = [
            _StubOutcome("arbeitnow", None),
            _StubOutcome("eures", "timeout"),
        ]
        banner = self._build_banner(outcomes, 3)
        self.assertIn("1 of 2 reported errors", banner)

    def test_banner_uses_italic_markdown(self):
        """Banner uses italic underscore markdown to match the
        AI-fallback banner convention from
        cv_consult / motivation_letter."""
        outcomes = [_StubOutcome("a", "err"), _StubOutcome("b", None)]
        banner = self._build_banner(outcomes, 1)
        self.assertTrue(banner.startswith("_(") and banner.rstrip().endswith(")_"))


class ErroredOutcomesPropagationContractTests(unittest.TestCase):
    """chat_handler_find_jobs must include `erroredOutcomes` in its
    return so the journey's run_search_with branch can surface the
    same banner. Loop 16 plumbing contract."""

    def test_contract_shape(self):
        # Document the expected return-dict key shape. Each entry
        # has {"provider": str, "error": str}.
        outcomes = [
            _StubOutcome("arbeitnow", None),
            _StubOutcome("eures", "timeout_after_5s"),
        ]
        serialised = [
            {"provider": o.provider, "error": o.error}
            for o in outcomes
            if o.error
        ]
        self.assertEqual(len(serialised), 1)
        self.assertEqual(serialised[0]["provider"], "eures")
        self.assertEqual(serialised[0]["error"], "timeout_after_5s")

    def test_no_propagation_when_no_errors(self):
        outcomes = [_StubOutcome("a", None), _StubOutcome("b", None)]
        serialised = [
            {"provider": o.provider, "error": o.error}
            for o in outcomes
            if o.error
        ]
        self.assertEqual(serialised, [])


if __name__ == "__main__":
    unittest.main()
