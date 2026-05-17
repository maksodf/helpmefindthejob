# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-6 tests: A5 cross-workspace data routing + invite."""

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


class CrossWorkspaceReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round6-ws-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app  # noqa: E402

        cls.state = app.STATE

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    _seq = 0

    def _seed(self):
        # Owner Alice has a company; Bob is a member of Alice's workspace.
        type(self)._seq += 1
        alice = self.state.auth_store.create_user(
            email=f"alice-ws-{type(self)._seq}@example.com",
            password="strongpassword!",
            role="member",
        )
        bob = self.state.auth_store.create_user(
            email=f"bob-ws-{type(self)._seq}@example.com",
            password="strongpassword!",
            role="member",
        )
        self.state.ensure_owner_membership(alice.id, label="Alice's workspace")
        self.state.ensure_owner_membership(bob.id, label="Bob's workspace")
        # Bob joins Alice's workspace as member.
        alice_ws = self.state.workspace_id_for_owner(alice.id)
        self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=bob.id,
                workspace_id=alice_ws,
                workspace_owner_id=alice.id,
                role="member",
                label="Alice's workspace",
            )
        )
        self.state.repository.save_company(Company(
            user_id=alice.id,
            name="Acme",
            website_url="https://acme.example.com",
        ))
        return alice, bob, alice_ws

    def test_default_effective_user_is_session_user(self) -> None:
        alice, bob, _ = self._seed()
        self.assertEqual(self.state.effective_user_id(alice.id), alice.id)
        self.assertEqual(self.state.effective_user_id(bob.id), bob.id)

    def test_active_workspace_switches_effective_user(self) -> None:
        alice, bob, alice_ws = self._seed()
        bob_profile = self.state.profile_for(bob.id)
        bob_profile.active_workspace_id = alice_ws
        self.state.repository.save_user_profile(bob_profile)
        self.assertEqual(self.state.effective_user_id(bob.id), alice.id)

    def test_bootstrap_for_member_returns_owner_data(self) -> None:
        alice, bob, alice_ws = self._seed()
        bob_profile = self.state.profile_for(bob.id)
        bob_profile.active_workspace_id = alice_ws
        self.state.repository.save_user_profile(bob_profile)
        boot = self.state.bootstrap(bob.id)
        names = {c.name for c in boot["companies"]}
        self.assertIn("Acme", names)
        self.assertEqual(boot["activeWorkspaceId"], alice_ws)

    def test_invalid_active_workspace_falls_back_to_own(self) -> None:
        alice, bob, _ = self._seed()
        bob_profile = self.state.profile_for(bob.id)
        bob_profile.active_workspace_id = "ws_does_not_exist"
        self.state.repository.save_user_profile(bob_profile)
        # Bob isn't a member of that workspace → fall back to his own.
        self.assertEqual(self.state.effective_user_id(bob.id), bob.id)


if __name__ == "__main__":
    unittest.main()
