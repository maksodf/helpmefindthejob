# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Reply-rate signal on ImportedJob (Phase 4 tracker item #42).

Also covers a regression guard: demo-data jobs (#34) must be importable.
The seed previously created DiscoveredJob rows without a company_id,
which broke `import_discovered_job` because that flow requires a
company. The seeder now creates a per-role demo company first and
links the job to it.

Adds a ``replied_at: datetime | None`` field that the user toggles
from the application form. Distinct from ``application_status`` —
status transitions can be triggered by auto-emails, but
``replied_at`` is the user-confirmed signal that someone wrote back.
The toggle is idempotent: setting ``replied=True`` repeatedly does
not overwrite the original stamp; only ``replied=False`` clears it.
"""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import Company, DiscoveredJob, ImportedJob


class RepliedAtTests(unittest.TestCase):
    def _state(self) -> tuple[AppState, str]:
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
                source_url="https://acme.example.com/job/42",
                title="Senior Engineer",
                company_id=company.id,
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
            ),
        )
        return state, imported.id

    def test_replied_true_stamps_replied_at(self) -> None:
        state, job_id = self._state()
        result = state.update_application_state(
            "alice@example.com" and state.repository.imported_jobs[job_id].user_id,
            job_id,
            {"replied": True},
        )
        self.assertIsNotNone(result.replied_at)

    def test_replied_true_is_idempotent(self) -> None:
        state, job_id = self._state()
        user_id = state.repository.imported_jobs[job_id].user_id

        first = state.update_application_state(user_id, job_id, {"replied": True})
        first_stamp = first.replied_at
        self.assertIsNotNone(first_stamp)

        time.sleep(0.01)  # ensure now_utc() would advance
        second = state.update_application_state(user_id, job_id, {"replied": True})
        # Same stamp, not overwritten.
        self.assertEqual(second.replied_at, first_stamp)

    def test_replied_false_clears_stamp(self) -> None:
        state, job_id = self._state()
        user_id = state.repository.imported_jobs[job_id].user_id
        state.update_application_state(user_id, job_id, {"replied": True})
        cleared = state.update_application_state(user_id, job_id, {"replied": False})
        self.assertIsNone(cleared.replied_at)

    def test_replied_at_iso_string_accepted(self) -> None:
        state, job_id = self._state()
        user_id = state.repository.imported_jobs[job_id].user_id
        explicit = "2026-04-01T09:00:00+00:00"
        result = state.update_application_state(user_id, job_id, {"repliedAt": explicit})
        self.assertEqual(result.replied_at, datetime.fromisoformat(explicit))

    def test_invalid_replied_at_rejected(self) -> None:
        state, job_id = self._state()
        user_id = state.repository.imported_jobs[job_id].user_id
        with self.assertRaises(ValueError):
            state.update_application_state(user_id, job_id, {"repliedAt": "not-a-date"})


class DemoDataImportTests(unittest.TestCase):
    """Regression guard for #34. Seed five demo jobs, then import each
    via the standard ``service.import_discovered_job`` path. Previously
    the seed produced jobs without a ``company_id`` which crashed the
    import on a KeyError lookup of ``self.companies[None]``."""

    def _state(self) -> AppState:
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
        return state

    def test_seed_then_import_each_does_not_raise(self) -> None:
        state = self._state()
        user = state.auth_store.create_user("demo@example.com", "very-secret-pass-1234")
        seeded = state.seed_demo_data(user.id)
        self.assertEqual(len(seeded), 5)
        for job_summary in seeded:
            discovered = state.repository.discovered_jobs[job_summary["id"]]
            self.assertIsNotNone(
                discovered.company_id,
                f"demo job {discovered.title!r} must carry a company_id for import to work",
            )
            imported = state.service.import_discovered_job(user.id, discovered.id)
            self.assertEqual(imported.title, discovered.title)
            self.assertEqual(imported.company_name, discovered.structured_data["company_name"])


if __name__ == "__main__":
    unittest.main()
