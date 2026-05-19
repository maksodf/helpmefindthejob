# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 9c — data-retention auto-purge."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.models import DiscoveredJob
from company_discovery.repository import InMemoryCompanyDiscoveryRepository


class RetentionPurgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryCompanyDiscoveryRepository()
        self.now = datetime(2026, 5, 9, tzinfo=timezone.utc)
        self.repo.save_discovered_job(
            DiscoveredJob(
                user_id="u1",
                source_url="https://x/old",
                title="Old role",
                discovered_at=self.now - timedelta(days=120),
            )
        )
        self.repo.save_discovered_job(
            DiscoveredJob(
                user_id="u1",
                source_url="https://x/recent",
                title="Recent role",
                discovered_at=self.now - timedelta(days=15),
            )
        )
        self.repo.save_discovered_job(
            DiscoveredJob(
                user_id="u1",
                source_url="https://x/imported",
                title="Imported role",
                imported_job_id="job_xyz",
                discovered_at=self.now - timedelta(days=200),
            )
        )

    def test_only_old_unimported_removed(self) -> None:
        cutoff = self.now - timedelta(days=90)
        removed = self.repo.purge_discovered_jobs_older_than(
            "u1", cutoff=cutoff, keep_imported=True
        )
        self.assertEqual(removed, 1)
        remaining_titles = [j.title for j in self.repo.discovered_jobs.values()]
        self.assertIn("Recent role", remaining_titles)
        self.assertIn("Imported role", remaining_titles)
        self.assertNotIn("Old role", remaining_titles)

    def test_resighted_old_job_kept(self) -> None:
        # An "old" job that was re-found yesterday should NOT be purged
        # because effective_freshness_at picks the most recent timestamp.
        self.repo.discovered_jobs.clear()
        recent = self.now - timedelta(days=1)
        self.repo.save_discovered_job(
            DiscoveredJob(
                user_id="u1",
                source_url="https://x/old-but-fresh",
                title="Old but re-sighted",
                discovered_at=self.now - timedelta(days=200),
                also_seen_at={"indeed.com": {"found_at": recent.isoformat()}},
            )
        )
        cutoff = self.now - timedelta(days=90)
        removed = self.repo.purge_discovered_jobs_older_than(
            "u1", cutoff=cutoff, keep_imported=True
        )
        self.assertEqual(removed, 0)


if __name__ == "__main__":
    unittest.main()
