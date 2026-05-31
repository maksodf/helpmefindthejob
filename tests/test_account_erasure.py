# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for GDPR Article 17 erasure + retention-purge durability.

Pins the fix for three deletion bugs that shared one root cause (the
SQLite/Postgres repos persist via per-mutation overrides, but bulk erasure +
retention purge were RAM-only or had an incomplete hardcoded table list):

- `delete_all_user_data` must remove EVERY user-scoped table — including the
  previously-orphaned `user_profiles` (CV/notes/PII), `push_subscriptions`,
  `workspace_memberships` — and the deletion must survive a restart.
- `purge_discovered_jobs_older_than` must delete from the persistent store, not
  just RAM, so purged jobs don't resurrect on restart.
- Erasing one user must not touch another user's data (cross-user scoping).

(The Postgres backend shares the same `delete_all_user_data`/purge override and
the dialect-correct `%s` placeholders; it can't be exercised here without a live
DB, but the architecture — one schema-driven table list per repo — is the fix.)
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from company_discovery import models
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository


def _seed(repo: SqliteCompanyDiscoveryRepository, uid: str) -> None:
    repo.save_company(models.Company(user_id=uid, name="ACME", website_url="https://acme.test"))
    repo.save_saved_search(models.SavedSearch(user_id=uid, name="nurse berlin"))
    repo.save_discovered_job(
        models.DiscoveredJob(user_id=uid, source_url=f"https://j/{uid}", title="T")
    )
    repo.save_user_profile(
        models.UserProfile(user_id=uid, cv_text="secret CV", notes="health", location="Berlin")
    )
    repo.save_push_subscription(
        models.PushSubscription(user_id=uid, endpoint="https://e", p256dh="k", auth="a")
    )
    repo.save_workspace_membership(
        models.WorkspaceMembership(user_id=uid, workspace_id="ws", workspace_owner_id=uid)
    )


def _counts(repo: SqliteCompanyDiscoveryRepository, uid: str) -> dict[str, int]:
    return {
        "companies": len(repo.list_companies(uid)),
        "saved_searches": len(repo.list_saved_searches(uid)),
        "discovered_jobs": len(repo.list_discovered_jobs(uid)),
        "profile": 1 if repo.get_user_profile(uid) is not None else 0,
        "push": len(repo.list_push_subscriptions(uid)),
        "workspace": len(repo.list_workspace_memberships(uid)),
    }


class AccountErasureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dbp = os.path.join(tempfile.mkdtemp(), "erase.db")

    def test_full_erasure_covers_every_table_and_survives_restart(self) -> None:
        r = SqliteCompanyDiscoveryRepository(self.dbp)
        _seed(r, "alice")
        _seed(r, "bob")
        self.assertTrue(all(v >= 1 for v in _counts(r, "alice").values()), "seed failed")

        r.delete_all_user_data("alice")
        r2 = SqliteCompanyDiscoveryRepository(self.dbp)  # reopen == restart

        self.assertEqual(
            _counts(r2, "alice"),
            {k: 0 for k in _counts(r2, "alice")},
            "alice's data must be fully erased across every user-scoped table and not resurrect on restart",
        )
        self.assertTrue(
            all(v >= 1 for v in _counts(r2, "bob").values()),
            "erasing alice must not touch bob (cross-user scoping)",
        )

    def test_purge_survives_restart(self) -> None:
        r = SqliteCompanyDiscoveryRepository(self.dbp)
        r.save_discovered_job(
            models.DiscoveredJob(
                user_id="alice",
                source_url="https://j",
                title="T",
                discovered_at=datetime.now(timezone.utc) - timedelta(days=200),
            )
        )
        removed = r.purge_discovered_jobs_older_than(
            "alice", cutoff=datetime.now(timezone.utc) - timedelta(days=90)
        )
        self.assertEqual(removed, 1)
        r2 = SqliteCompanyDiscoveryRepository(self.dbp)
        self.assertEqual(
            len(r2.list_discovered_jobs("alice")),
            0,
            "purged discovered jobs must not resurrect on restart",
        )


if __name__ == "__main__":
    unittest.main()
