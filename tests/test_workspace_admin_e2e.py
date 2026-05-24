# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Multi-tenant workspace admin E2E tests (13-plan item 4/13;
gap #22).

The workspace data model + invite endpoint shipped in Phase 2,
but the admin surface (list members, change role, remove member)
was missing. This file pins the new endpoints + the authorization
matrix:

| Action | Owner | Admin | Member | Self |
|---|---|---|---|---|
| List members | ✓ all | ✓ all | self only | n/a |
| Invite member | ✓ | ✓ | ✗ | n/a |
| Change role (member↔admin) | ✓ | ✗ | ✗ | ✗ |
| Change role (owner → anything) | ✗ NEVER | ✗ | ✗ | n/a |
| Remove member | ✓ anyone | ✓ members | ✗ others | ✓ self (non-owner) |
| Remove owner | ✗ NEVER | ✗ | ✗ | ✗ |

All checks happen in AppState methods so the HTTP layer is a
thin wrapper. Direct AppState tests + a route-presence
guard pin the full E2E shape.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.models import WorkspaceMembership


def _build_state(tmpdir: Path) -> AppState:
    state = AppState(
        tmpdir / "company.sqlite3",
        tmpdir / "auth.sqlite3",
        tmpdir / "ai.json",
        tmpdir / "schedule.json",
        start_scheduler=False,
    )
    return state


class ListMembersAuthorization(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.owner = self.state.auth_store.create_user(
            "owner@example.com", "pwd-1234567890"
        )
        self.member = self.state.auth_store.create_user(
            "member@example.com", "pwd-1234567890"
        )
        self.outsider = self.state.auth_store.create_user(
            "outsider@example.com", "pwd-1234567890"
        )
        self.workspace_id = self.state.workspace_id_for_owner(self.owner.id)
        # Ensure the owner has the implicit owner membership row
        self.state.ensure_owner_membership(self.owner.id)
        # Add the member to the owner's workspace
        self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=self.member.id,
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="member",
            )
        )

    def test_owner_sees_all_members(self):
        members = self.state.list_workspace_members_enriched(
            self.owner.id, self.workspace_id
        )
        emails = {m["email"] for m in members}
        self.assertEqual(emails, {"owner@example.com", "member@example.com"})
        # Owner is sorted first
        self.assertEqual(members[0]["role"], "owner")

    def test_outsider_gets_forbidden(self):
        with self.assertRaises(ValueError) as cm:
            self.state.list_workspace_members_enriched(
                self.outsider.id, self.workspace_id
            )
        self.assertIn("workspace_forbidden", str(cm.exception))

    def test_member_sees_only_themselves(self):
        members = self.state.list_workspace_members_enriched(
            self.member.id, self.workspace_id
        )
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["email"], "member@example.com")
        self.assertTrue(members[0]["isSelf"])

    def test_stale_membership_for_deleted_user_shows_placeholder(self):
        # Create a membership for a non-existent user_id
        self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id="ghost_user_id",
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="member",
            )
        )
        members = self.state.list_workspace_members_enriched(
            self.owner.id, self.workspace_id
        )
        ghost = next(m for m in members if m["userId"] == "ghost_user_id")
        self.assertEqual(ghost["email"], "(removed user)")


class UpdateMemberRoleAuthorization(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.owner = self.state.auth_store.create_user(
            "owner@example.com", "pwd-1234567890"
        )
        self.admin = self.state.auth_store.create_user(
            "admin@example.com", "pwd-1234567890"
        )
        self.member = self.state.auth_store.create_user(
            "member@example.com", "pwd-1234567890"
        )
        self.workspace_id = self.state.workspace_id_for_owner(self.owner.id)
        self.state.ensure_owner_membership(self.owner.id)
        self.admin_membership = self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=self.admin.id,
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="admin",
            )
        )
        self.member_membership = self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=self.member.id,
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="member",
            )
        )
        self.owner_membership = self.state.repository.find_workspace_membership(
            self.owner.id, self.workspace_id
        )

    def test_owner_can_promote_member_to_admin(self):
        result = self.state.update_workspace_member_role(
            actor_user_id=self.owner.id,
            workspace_id=self.workspace_id,
            membership_id=self.member_membership.id,
            new_role="admin",
        )
        self.assertEqual(result["role"], "admin")
        # Persisted
        reloaded = self.state.repository.find_workspace_membership(
            self.member.id, self.workspace_id
        )
        self.assertEqual(reloaded.role, "admin")

    def test_owner_can_demote_admin_to_member(self):
        self.state.update_workspace_member_role(
            actor_user_id=self.owner.id,
            workspace_id=self.workspace_id,
            membership_id=self.admin_membership.id,
            new_role="member",
        )
        reloaded = self.state.repository.find_workspace_membership(
            self.admin.id, self.workspace_id
        )
        self.assertEqual(reloaded.role, "member")

    def test_admin_cannot_promote_others(self):
        with self.assertRaises(ValueError) as cm:
            self.state.update_workspace_member_role(
                actor_user_id=self.admin.id,
                workspace_id=self.workspace_id,
                membership_id=self.member_membership.id,
                new_role="admin",
            )
        self.assertIn("workspace_forbidden", str(cm.exception))

    def test_owner_cannot_demote_themselves(self):
        with self.assertRaises(ValueError) as cm:
            self.state.update_workspace_member_role(
                actor_user_id=self.owner.id,
                workspace_id=self.workspace_id,
                membership_id=self.owner_membership.id,
                new_role="member",
            )
        self.assertIn("cannot_change_owner_role", str(cm.exception))

    def test_invalid_role_rejected(self):
        with self.assertRaises(ValueError) as cm:
            self.state.update_workspace_member_role(
                actor_user_id=self.owner.id,
                workspace_id=self.workspace_id,
                membership_id=self.member_membership.id,
                new_role="superuser",
            )
        self.assertIn("invalid_role", str(cm.exception))

    def test_missing_membership_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.state.update_workspace_member_role(
                actor_user_id=self.owner.id,
                workspace_id=self.workspace_id,
                membership_id="nonexistent",
                new_role="admin",
            )


class RemoveMemberAuthorization(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.owner = self.state.auth_store.create_user(
            "owner@example.com", "pwd-1234567890"
        )
        self.admin = self.state.auth_store.create_user(
            "admin@example.com", "pwd-1234567890"
        )
        self.member = self.state.auth_store.create_user(
            "member@example.com", "pwd-1234567890"
        )
        self.workspace_id = self.state.workspace_id_for_owner(self.owner.id)
        self.state.ensure_owner_membership(self.owner.id)
        self.admin_membership = self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=self.admin.id,
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="admin",
            )
        )
        self.member_membership = self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=self.member.id,
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="member",
            )
        )
        self.owner_membership = self.state.repository.find_workspace_membership(
            self.owner.id, self.workspace_id
        )

    def test_owner_can_remove_admin(self):
        self.state.remove_workspace_member(
            actor_user_id=self.owner.id,
            workspace_id=self.workspace_id,
            membership_id=self.admin_membership.id,
        )
        self.assertIsNone(
            self.state.repository.find_workspace_membership(
                self.admin.id, self.workspace_id
            )
        )

    def test_admin_can_remove_member(self):
        self.state.remove_workspace_member(
            actor_user_id=self.admin.id,
            workspace_id=self.workspace_id,
            membership_id=self.member_membership.id,
        )
        self.assertIsNone(
            self.state.repository.find_workspace_membership(
                self.member.id, self.workspace_id
            )
        )

    def test_admin_cannot_remove_other_admin(self):
        # Add a second admin
        other_admin_user = self.state.auth_store.create_user(
            "admin2@example.com", "pwd-1234567890"
        )
        other_admin_membership = self.state.repository.save_workspace_membership(
            WorkspaceMembership(
                user_id=other_admin_user.id,
                workspace_id=self.workspace_id,
                workspace_owner_id=self.owner.id,
                role="admin",
            )
        )
        with self.assertRaises(ValueError):
            self.state.remove_workspace_member(
                actor_user_id=self.admin.id,
                workspace_id=self.workspace_id,
                membership_id=other_admin_membership.id,
            )

    def test_member_can_self_remove(self):
        self.state.remove_workspace_member(
            actor_user_id=self.member.id,
            workspace_id=self.workspace_id,
            membership_id=self.member_membership.id,
        )
        self.assertIsNone(
            self.state.repository.find_workspace_membership(
                self.member.id, self.workspace_id
            )
        )

    def test_owner_cannot_be_removed(self):
        # Owner trying to self-remove: blocked
        with self.assertRaises(ValueError) as cm:
            self.state.remove_workspace_member(
                actor_user_id=self.owner.id,
                workspace_id=self.workspace_id,
                membership_id=self.owner_membership.id,
            )
        self.assertIn("cannot_remove_owner", str(cm.exception))

    def test_member_cannot_remove_admin(self):
        with self.assertRaises(ValueError):
            self.state.remove_workspace_member(
                actor_user_id=self.member.id,
                workspace_id=self.workspace_id,
                membership_id=self.admin_membership.id,
            )


class FrontendUIPresenceContract(unittest.TestCase):
    """The user-facing surface MUST exist + reference the
    endpoints the backend ships. A regression here means we
    have admin endpoints but no way to use them."""

    def test_index_html_has_members_card(self):
        text = Path(
            str(Path(__file__).resolve().parent.parent / "static/index.html")
        ).read_text(encoding="utf-8")
        self.assertIn('id="workspaceMembersCard"', text)
        self.assertIn('id="workspaceMembersTable"', text)
        self.assertIn('id="workspaceMembersBody"', text)

    def test_app_js_has_renderer_and_fetches_endpoint(self):
        text = Path(
            str(Path(__file__).resolve().parent.parent / "static/app.js")
        ).read_text(encoding="utf-8")
        self.assertIn("renderWorkspaceMembersCard", text)
        self.assertIn("/api/workspaces/", text)
        # The renderer is in the dispatch list
        self.assertRegex(text, r"renderers\s*=\s*\[[^\]]*renderWorkspaceMembersCard")
        # PATCH + DELETE helpers exist
        self.assertIn("_changeMemberRole", text)
        self.assertIn("_removeMember", text)

    def test_i18n_workspace_members_keys_present(self):
        import json

        for locale in ("en", "de"):
            bundle = json.loads(
                Path(
                    str(Path(__file__).resolve().parent.parent / f"static/i18n/{locale}.json")
                ).read_text(encoding="utf-8")
            )
            for key in (
                "settings.workspace.members.heading",
                "settings.workspace.members.col.email",
                "settings.workspace.members.col.role",
                "settings.workspace.members.col.actions",
            ):
                self.assertIn(key, bundle, f"missing in {locale}.json: {key}")


class RoutesPresenceContract(unittest.TestCase):
    """The HTTP layer is a thin wrapper. Pin that the routes
    exist in app.py source so a future refactor that quietly
    removes them fails CI."""

    def test_get_members_route_present(self):
        src = Path(
            str(Path(__file__).resolve().parent.parent / "app.py")
        ).read_text(encoding="utf-8")
        self.assertIn("/api/workspaces/", src)
        self.assertIn("ws_members_match", src)
        self.assertIn("list_workspace_members_enriched", src)

    def test_patch_member_role_route_present(self):
        src = Path(
            str(Path(__file__).resolve().parent.parent / "app.py")
        ).read_text(encoding="utf-8")
        self.assertIn("update_workspace_member_role", src)

    def test_delete_member_route_present(self):
        src = Path(
            str(Path(__file__).resolve().parent.parent / "app.py")
        ).read_text(encoding="utf-8")
        self.assertIn("remove_workspace_member", src)


if __name__ == "__main__":
    unittest.main()
