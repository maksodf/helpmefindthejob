"""Skill-gap atlas (Phase 4 tracker items #39 + #40 data + #41).

The auto-fit LLM prompt now emits a third line ``GAPS: skill1, skill2, skill3``;
the parser extracts those into ``DiscoveredJob.gaps``. On import the
``ImportedJob.gaps`` is populated from the discovered job. The
dashboard aggregator counts gap occurrences across imported jobs and
returns the top-K plus example titles, gated on a minimum-job
threshold so the card stays hidden until the signal is real.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import (
    Company,
    DiscoveredJob,
    ImportedJob,
)


class GapsImportPropagationTests(unittest.TestCase):
    def test_import_carries_gaps_through(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
        company = state.repository.save_company(
            Company(user_id=user.id, name="Acme", website_url="https://acme.example.com"),
        )
        discovered = state.repository.save_discovered_job(
            DiscoveredJob(
                user_id=user.id,
                company_id=company.id,
                source_url="https://acme.example.com/job/42",
                title="Senior Backend Engineer",
                gaps=["Kubernetes", "Terraform", "dbt"],
            ),
        )
        imported = state.service.import_discovered_job(user.id, discovered.id)
        self.assertEqual(imported.gaps, ["Kubernetes", "Terraform", "dbt"])


class AggregateSkillGapsTests(unittest.TestCase):
    def _state(self, gap_lists: list[list[str]]) -> tuple[AppState, str]:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
        company = state.repository.save_company(
            Company(user_id=user.id, name="Acme", website_url="https://acme.example.com"),
        )
        for index, gaps in enumerate(gap_lists):
            discovered = state.repository.save_discovered_job(
                DiscoveredJob(
                    user_id=user.id,
                    company_id=company.id,
                    source_url=f"https://acme.example.com/job/{index}",
                    title=f"Role {index}",
                ),
            )
            state.repository.save_imported_job(
                ImportedJob(
                    user_id=user.id,
                    company_id=company.id,
                    discovered_job_id=discovered.id,
                    source_url=discovered.source_url,
                    title=discovered.title,
                    company_name=company.name,
                    gaps=list(gaps),
                ),
            )
        return state, user.id

    def test_empty_aggregator_is_not_ready(self) -> None:
        state, user_id = self._state([])
        result = state.aggregate_skill_gaps(user_id)
        self.assertFalse(result["ready"])
        self.assertEqual(result["jobsWithGaps"], 0)
        self.assertEqual(result["top"], [])

    def test_below_threshold_is_not_ready(self) -> None:
        state, user_id = self._state(
            [["Kubernetes"], ["Terraform"]],  # 2 jobs, threshold is 3
        )
        result = state.aggregate_skill_gaps(user_id)
        self.assertFalse(result["ready"])
        self.assertEqual(result["jobsWithGaps"], 2)

    def test_top_three_are_returned(self) -> None:
        state, user_id = self._state(
            [
                ["Kubernetes", "Terraform"],
                ["Kubernetes", "dbt"],
                ["Kubernetes", "Terraform", "Snowflake"],
                ["Terraform"],
            ],
        )
        result = state.aggregate_skill_gaps(user_id)
        self.assertTrue(result["ready"])
        self.assertEqual(len(result["top"]), 3)
        # Kubernetes appears 3x, Terraform 3x, dbt 1x, Snowflake 1x.
        skills = [item["skill"] for item in result["top"]]
        self.assertIn("Kubernetes", skills)
        self.assertIn("Terraform", skills)

    def test_case_insensitive_grouping(self) -> None:
        state, user_id = self._state(
            [["kubernetes"], ["Kubernetes"], ["KUBERNETES"], ["something else"]],
        )
        result = state.aggregate_skill_gaps(user_id)
        # All three Kubernetes spellings should collapse into one bucket.
        kube = next((g for g in result["top"] if g["skill"].lower() == "kubernetes"), None)
        self.assertIsNotNone(kube)
        self.assertEqual(kube["jobs"], 3)

    def test_examples_are_capped_at_two(self) -> None:
        state, user_id = self._state(
            [["Kubernetes"], ["Kubernetes"], ["Kubernetes"], ["Kubernetes"]],
        )
        result = state.aggregate_skill_gaps(user_id)
        kube = result["top"][0]
        self.assertEqual(kube["jobs"], 4)
        self.assertEqual(len(kube["examples"]), 2)


if __name__ == "__main__":
    unittest.main()
