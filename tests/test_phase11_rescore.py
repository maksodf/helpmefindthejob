# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 11b — Re-score on persona change.

Tests the AppState.update_profile clear-auto-fit behavior using a freshly
constructed AppState pointed at a temporary data dir, so we never touch
the module-global STATE.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DIRECTJOB_SECRET_KEY", "x" * 64)

from company_discovery.models import DiscoveredJob


def _fresh_state(tmp_dir: str):
    """Build a fresh AppState in ``tmp_dir`` without disturbing module-globals."""

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


class PersonaChangeRescoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.STATE = _fresh_state(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_persona_change_clears_auto_fit_on_open_jobs(self) -> None:
        user = self.STATE.auth_store.create_user("re@score.test", "supersecret-123")
        open_job = DiscoveredJob(
            user_id=user.id,
            source_url="https://x/1",
            title="Open role",
            auto_fit_score=0.85,
            auto_fit_reason="Old persona reasoning",
            auto_fit_at=datetime.now(timezone.utc),
            auto_fit_provider_id="manual",
        )
        imported_job = DiscoveredJob(
            user_id=user.id,
            source_url="https://x/2",
            title="Imported role",
            auto_fit_score=0.90,
            imported_job_id="job_already_imported",
        )
        self.STATE.repository.save_discovered_job(open_job)
        self.STATE.repository.save_discovered_job(imported_job)
        # Initial persona — first call may clear (no previous), so re-seed.
        self.STATE.update_profile(user.id, {"personaId": "tech"})
        open_job.auto_fit_score = 0.85
        imported_job.auto_fit_score = 0.90
        self.STATE.repository.save_discovered_job(open_job)
        self.STATE.repository.save_discovered_job(imported_job)
        # Switch persona.
        self.STATE.update_profile(user.id, {"personaId": "data"})
        reloaded_open = self.STATE.repository.discovered_jobs[open_job.id]
        reloaded_imported = self.STATE.repository.discovered_jobs[imported_job.id]
        self.assertIsNone(reloaded_open.auto_fit_score)
        self.assertIsNone(reloaded_open.auto_fit_reason)
        self.assertEqual(reloaded_imported.auto_fit_score, 0.90)

    def test_same_persona_does_not_clear(self) -> None:
        user = self.STATE.auth_store.create_user("nochange@score.test", "supersecret-123")
        job = DiscoveredJob(
            user_id=user.id, source_url="https://x/3", title="r",
            auto_fit_score=0.50,
        )
        self.STATE.repository.save_discovered_job(job)
        self.STATE.update_profile(user.id, {"personaId": "tech"})
        job.auto_fit_score = 0.50
        self.STATE.repository.save_discovered_job(job)
        self.STATE.update_profile(user.id, {"personaId": "tech"})
        self.assertEqual(self.STATE.repository.discovered_jobs[job.id].auto_fit_score, 0.50)


if __name__ == "__main__":
    unittest.main()
