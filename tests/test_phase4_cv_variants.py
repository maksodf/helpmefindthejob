# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""CV-variant attribution (Phase 4 tracker item #44).

Each successful tailor-cv run appends a record to
``ImportedJob.cv_variants``. When the user later flags ``replied=True``
on the application, the most recent variant on that job is marked
``attributedReply=True``. A separate aggregator (`cv_variant_outcomes`)
counts the per-variant-index reply rate across the queue and surfaces
a winner once total variants ≥ 3.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import (
    Company,
    DiscoveredJob,
    ImportedJob,
)


def _state_with_imported_job(test):
    tmp = TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name)
    state = AppState(
        root / "company.sqlite3",
        root / "auth.sqlite3",
        root / "ai.json",
        root / "schedule.json",
        start_scheduler=False,
    )
    test.addCleanup(state.auth_store.close)
    test.addCleanup(state.repository.close)
    user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
    company = state.repository.save_company(
        Company(user_id=user.id, name="Acme", website_url="https://acme.example.com"),
    )
    discovered = state.repository.save_discovered_job(
        DiscoveredJob(
            user_id=user.id,
            company_id=company.id,
            source_url="https://acme.example.com/job/42",
            title="Senior Engineer",
        ),
    )
    imported = state.repository.save_imported_job(
        ImportedJob(
            user_id=user.id,
            company_id=company.id,
            discovered_job_id=discovered.id,
            source_url=discovered.source_url,
            title=discovered.title,
            company_name=company.name,
            application_status="applied",
        ),
    )
    return state, user.id, imported


class ReplyAttributesLatestVariantTests(unittest.TestCase):
    def test_replied_true_marks_latest_variant(self) -> None:
        state, user_id, imported = _state_with_imported_job(self)
        # Simulate two tailoring runs persisted on the imported job.
        imported.cv_variants = [
            {
                "index": 1,
                "createdAt": "2026-04-01T10:00:00+00:00",
                "excerpt": "v1",
                "attributedReply": False,
            },
            {
                "index": 2,
                "createdAt": "2026-04-02T10:00:00+00:00",
                "excerpt": "v2",
                "attributedReply": False,
            },
        ]
        state.repository.save_imported_job(imported)

        result = state.update_application_state(user_id, imported.id, {"replied": True})
        self.assertIsNotNone(result.replied_at)
        self.assertFalse(result.cv_variants[0]["attributedReply"])
        self.assertTrue(result.cv_variants[1]["attributedReply"])

    def test_replied_false_clears_attribution(self) -> None:
        state, user_id, imported = _state_with_imported_job(self)
        imported.cv_variants = [
            {
                "index": 1,
                "createdAt": "2026-04-01T10:00:00+00:00",
                "excerpt": "v1",
                "attributedReply": True,
            },
        ]
        imported.replied_at = datetime.now(timezone.utc)
        state.repository.save_imported_job(imported)

        result = state.update_application_state(user_id, imported.id, {"replied": False})
        self.assertIsNone(result.replied_at)
        self.assertFalse(result.cv_variants[0]["attributedReply"])

    def test_replied_true_with_no_variants_is_no_op_on_attribution(self) -> None:
        state, user_id, imported = _state_with_imported_job(self)
        result = state.update_application_state(user_id, imported.id, {"replied": True})
        self.assertEqual(result.cv_variants, [])
        self.assertIsNotNone(result.replied_at)


class CvVariantOutcomesTests(unittest.TestCase):
    def _state_with_jobs(self, jobs_spec: list[list[dict]]) -> tuple[AppState, str]:
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
        for index, variants in enumerate(jobs_spec):
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
                    cv_variants=list(variants),
                ),
            )
        return state, user.id

    def test_empty_outcomes_not_ready(self) -> None:
        state, user_id = self._state_with_jobs([])
        result = state.cv_variant_outcomes(user_id)
        self.assertFalse(result["ready"])
        self.assertEqual(result["totalVariants"], 0)
        self.assertEqual(result["breakdown"], [])
        self.assertIsNone(result["winner"])

    def test_below_threshold_not_ready(self) -> None:
        state, user_id = self._state_with_jobs(
            [[{"index": 1, "attributedReply": False}], [{"index": 1, "attributedReply": True}]],
        )
        result = state.cv_variant_outcomes(user_id)
        self.assertFalse(result["ready"])
        self.assertEqual(result["totalVariants"], 2)

    def test_winner_picks_highest_rate(self) -> None:
        state, user_id = self._state_with_jobs(
            [
                # Job 1: 2 variants, the second got the reply
                [
                    {"index": 1, "attributedReply": False},
                    {"index": 2, "attributedReply": True},
                ],
                # Job 2: 2 variants, again the second got the reply
                [
                    {"index": 1, "attributedReply": False},
                    {"index": 2, "attributedReply": True},
                ],
                # Job 3: only one variant, no reply
                [
                    {"index": 1, "attributedReply": False},
                ],
            ],
        )
        result = state.cv_variant_outcomes(user_id)
        self.assertTrue(result["ready"])
        self.assertEqual(result["totalVariants"], 5)
        winner = result["winner"]
        self.assertIsNotNone(winner)
        self.assertEqual(winner["index"], 2)
        self.assertEqual(winner["replied"], 2)
        self.assertEqual(winner["tailored"], 2)
        self.assertEqual(winner["rate"], 1.0)

    def test_winner_is_none_when_no_attributed_replies(self) -> None:
        state, user_id = self._state_with_jobs(
            [
                [{"index": 1, "attributedReply": False}],
                [{"index": 1, "attributedReply": False}],
                [{"index": 1, "attributedReply": False}],
            ],
        )
        result = state.cv_variant_outcomes(user_id)
        self.assertTrue(result["ready"])
        self.assertIsNone(result["winner"])


if __name__ == "__main__":
    unittest.main()
