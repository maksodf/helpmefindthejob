# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Cross-workspace data isolation: prove A5 + Item 15 actually work.

Two real auth users (Alice owner, Bob member of Alice's workspace).
Proves:
- Alice owns ws_<alice>; Bob owns ws_<bob>; Bob also member of ws_<alice>.
- When Bob's active_workspace is unset, bootstrap shows BOB's data only.
- When Bob's active_workspace = ws_<alice>, bootstrap shows ALICE's data.
- Alice's bootstrap NEVER shows Bob's own-workspace data.
- A non-member trying to set active_workspace gets ValueError("workspace_forbidden").
- Member writes (apply_watchlist_template) under active workspace go to the
  workspace owner's user_id, not the session user's.
"""

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

from company_discovery.models import Company, WorkspaceMembership


class CrossWorkspaceIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round8-iso-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app  # noqa: E402

        cls.state = app.STATE

        # Alice owner + companies; Bob owner of own + member of Alice's.
        cls.alice = cls.state.auth_store.create_user(
            email="iso-alice@example.com",
            password="strongpassword!",
            role="member",
        )
        cls.bob = cls.state.auth_store.create_user(
            email="iso-bob@example.com",
            password="strongpassword!",
            role="member",
        )
        cls.state.ensure_owner_membership(cls.alice.id)
        cls.state.ensure_owner_membership(cls.bob.id)
        cls.alice_ws = cls.state.workspace_id_for_owner(cls.alice.id)
        cls.bob_ws = cls.state.workspace_id_for_owner(cls.bob.id)
        # Bob joins Alice's workspace.
        cls.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=cls.bob.id,
                workspace_id=cls.alice_ws,
                workspace_owner_id=cls.alice.id,
                role="member",
                label="Alice's workspace",
            )
        )
        # Each owner adds a distinct company.
        cls.state.repository.save_company(
            Company(
                user_id=cls.alice.id,
                name="Alice Co",
                website_url="https://alice.example",
            )
        )
        cls.state.repository.save_company(
            Company(
                user_id=cls.bob.id,
                name="Bob Co",
                website_url="https://bob.example",
            )
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self) -> None:
        # Reset Bob's active workspace before each test so they don't leak.
        bob_profile = self.state.profile_for(self.bob.id)
        bob_profile.active_workspace_id = None
        self.state.repository.save_user_profile(bob_profile)

    def test_bob_default_sees_only_own_data(self) -> None:
        boot = self.state.bootstrap(self.bob.id)
        names = {c.name for c in boot["companies"]}
        self.assertIn("Bob Co", names)
        self.assertNotIn("Alice Co", names)

    def test_bob_switching_to_alice_workspace_sees_alice_data(self) -> None:
        bob_profile = self.state.profile_for(self.bob.id)
        bob_profile.active_workspace_id = self.alice_ws
        self.state.repository.save_user_profile(bob_profile)
        boot = self.state.bootstrap(self.bob.id)
        names = {c.name for c in boot["companies"]}
        self.assertIn("Alice Co", names)
        self.assertNotIn("Bob Co", names)
        self.assertEqual(boot["activeWorkspaceId"], self.alice_ws)

    def test_alice_never_sees_bob_data(self) -> None:
        # Even if Alice somehow had Bob's workspace id set, she's not a member.
        boot = self.state.bootstrap(self.alice.id)
        names = {c.name for c in boot["companies"]}
        self.assertIn("Alice Co", names)
        self.assertNotIn("Bob Co", names)

    def test_non_member_cannot_resolve_workspace(self) -> None:
        # Alice tries to act inside Bob's workspace — forbidden.
        with self.assertRaises(ValueError):
            self.state.resolve_workspace_owner(self.alice.id, self.bob_ws)

    def test_member_write_routes_to_workspace_owner(self) -> None:
        # Bob switches to Alice's workspace, applies a watchlist template.
        bob_profile = self.state.profile_for(self.bob.id)
        bob_profile.active_workspace_id = self.alice_ws
        self.state.repository.save_user_profile(bob_profile)
        # Use the helper effective_user_id directly to simulate the handler.
        target = self.state.effective_user_id(self.bob.id)
        self.assertEqual(target, self.alice.id)
        result = self.state.apply_watchlist_template(target, "hospital_groups_de")
        added = result.get("added", [])
        # New companies should belong to Alice (the owner), not Bob.
        for company in added:
            self.assertEqual(company.user_id, self.alice.id)
        # Alice's bootstrap should now include those companies.
        alice_boot = self.state.bootstrap(self.alice.id)
        alice_names = {c.name for c in alice_boot["companies"]}
        self.assertTrue(any("Charité" in name or "Vivantes" in name for name in alice_names))
        # Bob's OWN-workspace bootstrap should NOT include them.
        bob_profile.active_workspace_id = None
        self.state.repository.save_user_profile(bob_profile)
        bob_own_boot = self.state.bootstrap(self.bob.id)
        bob_own_names = {c.name for c in bob_own_boot["companies"]}
        self.assertNotIn("Vivantes", bob_own_names)


if __name__ == "__main__":
    unittest.main()
