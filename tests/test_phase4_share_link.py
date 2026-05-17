# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Public share link for imported jobs (Phase 4 tracker item #45).

Adds an opt-in ``share_enabled`` flag on ImportedJob and a public
server-rendered HTML page at ``/share/job/<id>`` so the owner can
share an SEO-indexable preview with a sign-up CTA. Owner can flip
sharing off at any time and the URL flips to 404.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import Company, DiscoveredJob, ImportedJob


class ShareLinkTests(unittest.TestCase):
    def _state(self) -> tuple[AppState, str, str]:
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
                description="Senior backend role on the platform team.",
            ),
        )
        return state, user.id, imported.id

    def test_share_disabled_by_default(self) -> None:
        state, _, job_id = self._state()
        job = state.repository.imported_jobs[job_id]
        self.assertFalse(job.share_enabled)

    def test_owner_can_enable_and_disable(self) -> None:
        state, user_id, job_id = self._state()

        enabled = state.set_share_enabled(user_id, job_id, True)
        self.assertTrue(enabled.share_enabled)

        disabled = state.set_share_enabled(user_id, job_id, False)
        self.assertFalse(disabled.share_enabled)

    def test_other_users_cannot_toggle_share(self) -> None:
        state, _, job_id = self._state()
        with self.assertRaises(KeyError):
            state.set_share_enabled("not-the-owner", job_id, True)

    def test_unknown_job_id_raises(self) -> None:
        state, user_id, _ = self._state()
        with self.assertRaises(KeyError):
            state.set_share_enabled(user_id, "imported_job_does_not_exist", True)

    def test_toggle_persists_through_in_memory_round_trip(self) -> None:
        # The change updates the persisted profile via save_imported_job;
        # re-reading from the repo returns the new flag without needing
        # a re-load of the AppState (the in-memory dict and disk both
        # reflect the same dataclass).
        state, user_id, job_id = self._state()
        state.set_share_enabled(user_id, job_id, True)
        self.assertTrue(state.repository.imported_jobs[job_id].share_enabled)


if __name__ == "__main__":
    unittest.main()
