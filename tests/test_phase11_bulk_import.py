# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 11d — Bulk-import endpoint."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("HELPMEFINDTHEJOB_SECRET_KEY", "x" * 64)

from company_discovery.models import Company, DiscoveredJob


def _fresh_state(tmp_dir: str):
    from app import AppState

    base = Path(tmp_dir)
    return AppState(
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


class BulkImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.STATE = _fresh_state(self.tmp.name)
        self.user = self.STATE.auth_store.create_user("bi@test.local", "supersecret-12345")
        self.company = self.STATE.repository.save_company(
            Company(
                user_id=self.user.id,
                name="Acme",
                website_url="https://acme.test",
            )
        )
        self.j1 = self.STATE.repository.save_discovered_job(
            DiscoveredJob(
                user_id=self.user.id,
                company_id=self.company.id,
                source_url="https://acme.test/jobs/1",
                title="Backend Engineer",
            )
        )
        self.j2 = self.STATE.repository.save_discovered_job(
            DiscoveredJob(
                user_id=self.user.id,
                company_id=self.company.id,
                source_url="https://acme.test/jobs/2",
                title="Frontend Engineer",
            )
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_bulk_imports_two_jobs(self) -> None:
        outcomes = []
        for did in [self.j1.id, self.j2.id]:
            try:
                imported = self.STATE.service.import_discovered_job(self.user.id, did)
                outcomes.append({"id": did, "status": "imported", "importedJobId": imported.id})
            except Exception as e:
                outcomes.append({"id": did, "status": "error", "code": str(e)})
        statuses = [o["status"] for o in outcomes]
        self.assertEqual(statuses.count("imported"), 2)
        self.assertEqual(len(self.STATE.repository.list_imported_jobs(self.user.id)), 2)

    def test_unknown_id_returns_error(self) -> None:
        try:
            self.STATE.service.import_discovered_job(self.user.id, "discovered_job_does_not_exist")
            self.fail("Expected KeyError")
        except KeyError:
            pass


if __name__ == "__main__":
    unittest.main()
