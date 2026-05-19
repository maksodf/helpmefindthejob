# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Reply-rate analytics summary (Phase 4 tracker item #43).

Counts ImportedJob rows that have moved off the default ``saved``
status (i.e. a real application has happened) and divides by the
``replied_at`` count. Surfaced via ``application_outcomes_summary`` and
included in every ``/api/bootstrap`` payload as ``applicationOutcomes``.
The frontend hides the dashboard card until ``ready=True`` (>=5
applications), which avoids showing wildly noisy single-digit rates.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import Company, DiscoveredJob, ImportedJob


class ApplicationOutcomesSummaryTests(unittest.TestCase):
    def _state_with_jobs(
        self,
        jobs_spec: list[tuple[str, datetime | None]],
    ) -> tuple[AppState, str]:
        """Build an AppState seeded with one ImportedJob per spec entry.
        spec is a list of ``(application_status, replied_at)`` tuples."""

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
        for status, replied_at in jobs_spec:
            discovered = state.repository.save_discovered_job(
                DiscoveredJob(
                    user_id=user.id,
                    source_url=f"https://acme.example.com/job/{status}",
                    title=f"Role for {status}",
                    company_id=company.id,
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
                    application_status=status,
                    replied_at=replied_at,
                ),
            )
        return state, user.id

    def test_empty_summary_is_not_ready(self) -> None:
        state, user_id = self._state_with_jobs([])
        result = state.application_outcomes_summary(user_id)
        self.assertEqual(result["totalApplications"], 0)
        self.assertEqual(result["replied"], 0)
        self.assertEqual(result["replyRate"], 0.0)
        self.assertFalse(result["ready"])

    def test_saved_does_not_count_as_application(self) -> None:
        # Three jobs but all in 'saved' (== considered + not yet applied);
        # the analytics treats them as out-of-funnel.
        state, user_id = self._state_with_jobs(
            [("saved", None), ("saved", None), ("saved", None)],
        )
        result = state.application_outcomes_summary(user_id)
        self.assertEqual(result["totalApplications"], 0)
        self.assertFalse(result["ready"])

    def test_below_threshold_is_not_ready(self) -> None:
        # 4 applications, 1 reply — below the 5-application threshold.
        now = datetime.now(timezone.utc)
        state, user_id = self._state_with_jobs(
            [
                ("applied", None),
                ("applied", now),
                ("interview", None),
                ("rejected", None),
            ],
        )
        result = state.application_outcomes_summary(user_id)
        self.assertEqual(result["totalApplications"], 4)
        self.assertEqual(result["replied"], 1)
        self.assertFalse(result["ready"])

    def test_at_threshold_reports_rate(self) -> None:
        now = datetime.now(timezone.utc)
        state, user_id = self._state_with_jobs(
            [
                ("applied", now),
                ("applied", None),
                ("applied", None),
                ("interview", now),
                ("rejected", None),
            ],
        )
        result = state.application_outcomes_summary(user_id)
        self.assertEqual(result["totalApplications"], 5)
        self.assertEqual(result["replied"], 2)
        self.assertEqual(result["replyRate"], 0.4)
        self.assertTrue(result["ready"])

    def test_archived_counts_as_application(self) -> None:
        # Archived = the user closed it out, but it was a real application.
        # Including it gives a more honest reply rate.
        now = datetime.now(timezone.utc)
        state, user_id = self._state_with_jobs(
            [
                ("applied", now),
                ("applied", None),
                ("applied", None),
                ("archived", now),
                ("archived", None),
            ],
        )
        result = state.application_outcomes_summary(user_id)
        self.assertEqual(result["totalApplications"], 5)
        self.assertEqual(result["replied"], 2)

    def test_bootstrap_includes_outcomes(self) -> None:
        state, user_id = self._state_with_jobs(
            [("applied", datetime.now(timezone.utc))],
        )
        bootstrap = state.bootstrap(user_id)
        self.assertIn("applicationOutcomes", bootstrap)
        self.assertEqual(bootstrap["applicationOutcomes"]["totalApplications"], 1)


if __name__ == "__main__":
    unittest.main()
