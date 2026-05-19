# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-5 tests: A5 workspace scaffolding."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.models import WORKSPACE_ROLES, WorkspaceMembership
from company_discovery.repository import InMemoryCompanyDiscoveryRepository
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository


class WorkspaceModelTests(unittest.TestCase):
    def test_workspace_roles_constant(self) -> None:
        self.assertEqual(WORKSPACE_ROLES, ("owner", "admin", "member"))

    def test_default_role(self) -> None:
        m = WorkspaceMembership(
            user_id="user_a",
            workspace_id="ws_a",
            workspace_owner_id="user_a",
        )
        self.assertEqual(m.role, "member")


class WorkspaceRepositoryTests(unittest.TestCase):
    def test_save_list_find_in_memory(self) -> None:
        repo = InMemoryCompanyDiscoveryRepository()
        m = WorkspaceMembership(
            user_id="user_a",
            workspace_id="ws_a",
            workspace_owner_id="user_a",
            role="owner",
        )
        repo.save_workspace_membership(m)
        listed = repo.list_workspace_memberships("user_a")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].role, "owner")
        found = repo.find_workspace_membership("user_a", "ws_a")
        assert found is not None
        self.assertEqual(found.id, m.id)
        members = repo.list_workspace_members("ws_a")
        self.assertEqual(len(members), 1)

    def test_sqlite_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ws.sqlite3"
            repo = SqliteCompanyDiscoveryRepository(path)
            try:
                repo.save_workspace_membership(
                    WorkspaceMembership(
                        user_id="user_a",
                        workspace_id="ws_a",
                        workspace_owner_id="user_a",
                        role="owner",
                        label="Acme",
                    )
                )
                repo.save_workspace_membership(
                    WorkspaceMembership(
                        user_id="user_b",
                        workspace_id="ws_a",
                        workspace_owner_id="user_a",
                        role="member",
                    )
                )
            finally:
                repo.close()

            reopened = SqliteCompanyDiscoveryRepository(path)
            try:
                members = reopened.list_workspace_members("ws_a")
                self.assertEqual({m.user_id for m in members}, {"user_a", "user_b"})
                roles = {m.user_id: m.role for m in members}
                self.assertEqual(roles["user_a"], "owner")
                self.assertEqual(roles["user_b"], "member")
            finally:
                reopened.close()


class WorkspaceStateHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round5-ws-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app  # noqa: E402

        cls.state = app.STATE
        cls.app = app

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_workspace_id_is_stable(self) -> None:
        ws1 = self.state.workspace_id_for_owner("user_abc123")
        ws2 = self.state.workspace_id_for_owner("user_abc123")
        self.assertEqual(ws1, ws2)
        self.assertTrue(ws1.startswith("ws_"))

    def test_resolve_falls_back_to_own_workspace(self) -> None:
        owner = self.state.resolve_workspace_owner("user_synthetic_owner", None)
        self.assertEqual(owner, "user_synthetic_owner")

    def test_resolve_forbidden_for_non_member(self) -> None:
        alice_ws = self.state.workspace_id_for_owner("user_alice_synthetic")
        # Trigger Alice's owner membership creation by listing.
        self.state.list_user_workspaces("user_alice_synthetic")
        with self.assertRaises(ValueError):
            self.state.resolve_workspace_owner("user_bob_synthetic", alice_ws)

    def test_bootstrap_includes_workspaces(self) -> None:
        boot = self.state.bootstrap("user_boot_synthetic")
        self.assertIn("workspaces", boot)
        self.assertIn("activeWorkspaceId", boot)
        self.assertEqual(len(boot["workspaces"]), 1)
        self.assertEqual(boot["workspaces"][0]["role"], "owner")


if __name__ == "__main__":
    unittest.main()
