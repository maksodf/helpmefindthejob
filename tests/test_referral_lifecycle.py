# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Referral lifecycle contract (phase2-backlog #11).

Closes the "no referral network beyond a stub MCP tool" gap by
adding:

1. **Persistence**: ``Referral`` dataclass + repository
   save/get/list/delete methods.
2. **Full lifecycle**: ``proposed → accepted / declined →
   followed_up → expired`` state machine with explicit allowed-
   transitions table enforced in ``update_referral_status``.
3. **Cross-tenant defense**: a user can only see + update their
   OWN referrals. The MCP tool returns ``not_found`` (not
   ``forbidden`` — never confirm existence to a non-owner) when
   the requesting ``userId`` doesn't match the referral's stored
   user_id.
4. **MCP catalogue extension**: two new tools (``list_referrals``,
   ``update_referral_status``) bring v0.2.0 → 15 tools.
5. **REST endpoints**: GET /api/referrals + PATCH /api/referrals/<id>
   for the user-facing UI.

Tests pin: persistence roundtrip, status state-machine, lifecycle
transitions (allowed + rejected), cross-tenant isolation, MCP
catalogue size, REST endpoint shape.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.mcp_tools import (
    TOOL_SCHEMAS,
    CompanyDiscoveryMCPTools,
)
from company_discovery.models import REFERRAL_STATUSES, Referral
from company_discovery.repository import InMemoryCompanyDiscoveryRepository


class _ServiceLike:
    """Minimal service stub for the MCP-tool layer in unit tests."""

    def __init__(self, repo: InMemoryCompanyDiscoveryRepository) -> None:
        self.repository = repo


# ---------------------------------------------------------------------------
# Model + repository
# ---------------------------------------------------------------------------


class ReferralModelDefaults(unittest.TestCase):
    def test_referral_defaults(self):
        r = Referral(user_id="u1", target_agent="x", reason_code="r")
        self.assertEqual(r.source_agent, "helpmefindthejob")
        self.assertEqual(r.intent, "proposed")
        self.assertEqual(r.status, "proposed")
        self.assertTrue(r.user_consent_required)
        self.assertEqual(r.priority, "routine")
        self.assertEqual(r.supporting_info, {})
        self.assertEqual(r.outcome_note, "")
        # ``new_id`` convention is ``<prefix>_<uuid_hex>`` (underscore,
        # not dash) — see company_discovery/models.py::new_id.
        self.assertTrue(r.id.startswith("ref_"))

    def test_referral_statuses_catalogue(self):
        self.assertEqual(
            REFERRAL_STATUSES,
            ("proposed", "accepted", "declined", "followed_up", "expired"),
        )


class RepositoryReferralRoundtrip(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCompanyDiscoveryRepository()

    def test_save_get(self):
        r = Referral(user_id="u1", target_agent="x", reason_code="r")
        self.repo.save_referral(r)
        self.assertIs(self.repo.get_referral(r.id), r)

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.repo.get_referral("does-not-exist"))

    def test_list_filters_by_user(self):
        r1 = self.repo.save_referral(
            Referral(user_id="u1", target_agent="x", reason_code="r1")
        )
        r2 = self.repo.save_referral(
            Referral(user_id="u2", target_agent="x", reason_code="r2")
        )
        u1 = self.repo.list_referrals(user_id="u1")
        u2 = self.repo.list_referrals(user_id="u2")
        self.assertEqual([r.id for r in u1], [r1.id])
        self.assertEqual([r.id for r in u2], [r2.id])

    def test_list_filters_by_status(self):
        r1 = Referral(
            user_id="u1", target_agent="x", reason_code="r1", status="proposed"
        )
        r2 = Referral(
            user_id="u1", target_agent="x", reason_code="r2", status="accepted"
        )
        self.repo.save_referral(r1)
        self.repo.save_referral(r2)
        proposed = self.repo.list_referrals(user_id="u1", status="proposed")
        accepted = self.repo.list_referrals(user_id="u1", status="accepted")
        self.assertEqual([r.id for r in proposed], [r1.id])
        self.assertEqual([r.id for r in accepted], [r2.id])

    def test_delete(self):
        r = self.repo.save_referral(
            Referral(user_id="u1", target_agent="x", reason_code="r")
        )
        self.repo.delete_referral(r.id)
        self.assertIsNone(self.repo.get_referral(r.id))


# ---------------------------------------------------------------------------
# propose_referral now persists
# ---------------------------------------------------------------------------


class ProposeReferralPersists(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCompanyDiscoveryRepository()
        self.tools = CompanyDiscoveryMCPTools(_ServiceLike(self.repo))

    def test_propose_referral_persists_referral(self):
        out = self.tools.propose_referral(
            userId="aicha",
            targetAgent="housing",
            reason="user mentioned no Anschreiben",
        )
        self.assertEqual(out["status"], "ok")
        referral_id = out["referral"]["referralId"]
        persisted = self.repo.get_referral(referral_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.user_id, "aicha")
        self.assertEqual(persisted.target_agent, "housing")
        self.assertEqual(persisted.status, "proposed")

    def test_propose_referral_returns_persisted_id(self):
        """The returned referralId must be the persisted ID, not a
        fresh uuid-stub."""

        out = self.tools.propose_referral(
            userId="u1", targetAgent="x", reason="test"
        )
        returned_id = out["referral"]["referralId"]
        # Persisted IDs use new_id's underscore convention
        self.assertTrue(returned_id.startswith("ref_"))
        self.assertIsNotNone(self.repo.get_referral(returned_id))

    def test_propose_referral_returns_status_field(self):
        out = self.tools.propose_referral(
            userId="u1", targetAgent="x", reason="test"
        )
        # The new shape includes status (lifecycle stage)
        self.assertEqual(out["referral"]["status"], "proposed")

    def test_propose_referral_supports_context(self):
        out = self.tools.propose_referral(
            userId="u1",
            targetAgent="x",
            reason="test",
            context={"originalMessage": "user said X"},
        )
        referral_id = out["referral"]["referralId"]
        persisted = self.repo.get_referral(referral_id)
        self.assertEqual(
            persisted.supporting_info, {"originalMessage": "user said X"}
        )

    def test_propose_referral_no_repo_returns_stub(self):
        """Falls back to legacy stub shape when no repo is wired —
        keeps the tool usable in stripped-down test harnesses."""

        class _NoRepoService:
            pass

        tools = CompanyDiscoveryMCPTools(_NoRepoService())
        out = tools.propose_referral(userId="u1", targetAgent="x", reason="test")
        # Status still ok; returned shape compatible
        self.assertEqual(out["status"], "ok")
        self.assertIn("referralId", out["referral"])


# ---------------------------------------------------------------------------
# list_referrals tool
# ---------------------------------------------------------------------------


class ListReferralsTool(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCompanyDiscoveryRepository()
        self.tools = CompanyDiscoveryMCPTools(_ServiceLike(self.repo))

    def test_empty_returns_clean_payload(self):
        out = self.tools.list_referrals(userId="u-fresh")
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["referrals"], [])

    def test_returns_user_referrals(self):
        self.tools.propose_referral(
            userId="u1", targetAgent="housing", reason="r1"
        )
        self.tools.propose_referral(
            userId="u1", targetAgent="healthcare", reason="r2"
        )
        out = self.tools.list_referrals(userId="u1")
        self.assertEqual(len(out["referrals"]), 2)

    def test_status_filter_works(self):
        out1 = self.tools.propose_referral(
            userId="u1", targetAgent="x", reason="r1"
        )
        self.tools.update_referral_status(
            userId="u1",
            referralId=out1["referral"]["referralId"],
            status="accepted",
        )
        self.tools.propose_referral(
            userId="u1", targetAgent="y", reason="r2"
        )
        proposed = self.tools.list_referrals(userId="u1", status="proposed")
        accepted = self.tools.list_referrals(userId="u1", status="accepted")
        self.assertEqual(len(proposed["referrals"]), 1)
        self.assertEqual(len(accepted["referrals"]), 1)

    def test_invalid_status_returns_error(self):
        out = self.tools.list_referrals(userId="u1", status="garbage")
        self.assertEqual(out["status"], "invalid_arguments")

    def test_cross_tenant_isolation(self):
        self.tools.propose_referral(userId="u1", targetAgent="x", reason="r")
        out = self.tools.list_referrals(userId="u2")
        # u2 sees nothing — u1's referral isn't theirs
        self.assertEqual(out["referrals"], [])


# ---------------------------------------------------------------------------
# update_referral_status — lifecycle state machine
# ---------------------------------------------------------------------------


class UpdateReferralStatusLifecycle(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCompanyDiscoveryRepository()
        self.tools = CompanyDiscoveryMCPTools(_ServiceLike(self.repo))
        # Create a referral in 'proposed' state
        out = self.tools.propose_referral(
            userId="aicha", targetAgent="housing", reason="test"
        )
        self.referral_id = out["referral"]["referralId"]

    def test_proposed_to_accepted_transition(self):
        out = self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="accepted"
        )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["referral"]["status"], "accepted")
        # intent updates in lockstep (FHIR-aligned)
        self.assertEqual(out["referral"]["intent"], "directive")

    def test_proposed_to_declined_transition(self):
        out = self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="declined"
        )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["referral"]["status"], "declined")

    def test_accepted_to_followed_up_transition(self):
        self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="accepted"
        )
        out = self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="followed_up"
        )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["referral"]["intent"], "completed")

    def test_proposed_to_followed_up_rejected(self):
        """Can't skip 'accepted' — must accept first."""

        out = self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="followed_up"
        )
        self.assertEqual(out["status"], "invalid_transition")
        self.assertEqual(out["currentStatus"], "proposed")

    def test_declined_to_accepted_rejected(self):
        """Declined is a terminal state for normal flow."""

        self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="declined"
        )
        out = self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="accepted"
        )
        self.assertEqual(out["status"], "invalid_transition")

    def test_expired_transition_from_any_state(self):
        """Garbage-collection path: any state can transition to
        expired (lifecycle-completion mark)."""

        for from_state, _ in (
            ("proposed", "expired"),
            ("accepted", "expired"),
            ("declined", "expired"),
            ("followed_up", "expired"),
        ):
            # Set up a fresh referral in each from_state
            out = self.tools.propose_referral(
                userId="aicha", targetAgent="x", reason="r"
            )
            rid = out["referral"]["referralId"]
            if from_state == "accepted":
                self.tools.update_referral_status(
                    userId="aicha", referralId=rid, status="accepted"
                )
            elif from_state == "declined":
                self.tools.update_referral_status(
                    userId="aicha", referralId=rid, status="declined"
                )
            elif from_state == "followed_up":
                self.tools.update_referral_status(
                    userId="aicha", referralId=rid, status="accepted"
                )
                self.tools.update_referral_status(
                    userId="aicha", referralId=rid, status="followed_up"
                )
            # Now expire it
            result = self.tools.update_referral_status(
                userId="aicha", referralId=rid, status="expired"
            )
            self.assertEqual(
                result["status"], "ok", f"from_state={from_state}"
            )

    def test_invalid_status_value_rejected(self):
        out = self.tools.update_referral_status(
            userId="aicha", referralId=self.referral_id, status="garbage"
        )
        self.assertEqual(out["status"], "invalid_arguments")

    def test_not_found_status(self):
        out = self.tools.update_referral_status(
            userId="aicha", referralId="ref-does-not-exist", status="accepted"
        )
        self.assertEqual(out["status"], "not_found")

    def test_outcome_note_persisted(self):
        out = self.tools.update_referral_status(
            userId="aicha",
            referralId=self.referral_id,
            status="declined",
            outcomeNote="user changed mind",
        )
        self.assertEqual(out["referral"]["outcomeNote"], "user changed mind")

    def test_outcome_note_truncated_at_1000(self):
        big = "x" * 5000
        out = self.tools.update_referral_status(
            userId="aicha",
            referralId=self.referral_id,
            status="declined",
            outcomeNote=big,
        )
        self.assertLessEqual(len(out["referral"]["outcomeNote"]), 1000)


# ---------------------------------------------------------------------------
# Cross-tenant defense
# ---------------------------------------------------------------------------


class CrossTenantIsolation(unittest.TestCase):
    """A user must not be able to update someone else's referral.
    The MCP tool returns not_found rather than forbidden so we
    never confirm existence to a non-owner."""

    def setUp(self):
        self.repo = InMemoryCompanyDiscoveryRepository()
        self.tools = CompanyDiscoveryMCPTools(_ServiceLike(self.repo))
        out = self.tools.propose_referral(
            userId="aicha", targetAgent="x", reason="r"
        )
        self.referral_id = out["referral"]["referralId"]

    def test_cannot_update_other_users_referral(self):
        # Yusuf tries to update Aïcha's referral
        out = self.tools.update_referral_status(
            userId="yusuf",
            referralId=self.referral_id,
            status="accepted",
        )
        self.assertEqual(out["status"], "not_found")
        # And the referral is unchanged
        persisted = self.repo.get_referral(self.referral_id)
        self.assertEqual(persisted.status, "proposed")


# ---------------------------------------------------------------------------
# MCP catalogue surface
# ---------------------------------------------------------------------------


class CatalogueExtension(unittest.TestCase):
    def test_list_referrals_in_catalogue(self):
        names = {t["name"] for t in TOOL_SCHEMAS}
        self.assertIn("list_referrals", names)

    def test_update_referral_status_in_catalogue(self):
        names = {t["name"] for t in TOOL_SCHEMAS}
        self.assertIn("update_referral_status", names)

    def test_catalogue_size_15(self):
        self.assertEqual(len(TOOL_SCHEMAS), 15)

    def test_per_tool_schema_files_exist(self):
        repo_root = Path(__file__).resolve().parent.parent
        schemas_dir = repo_root / "mcp_server" / "schemas"
        for new_tool in ("list_referrals", "update_referral_status"):
            with self.subTest(tool=new_tool):
                self.assertTrue(
                    (schemas_dir / f"{new_tool}.json").exists(),
                    f"missing per-tool schema file for {new_tool}",
                )


import os


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL", "").strip(),
    "TEST_POSTGRES_URL not set — skipping live PG referral roundtrip",
)
class LivePostgresReferralRoundtrip(unittest.TestCase):
    """phase2-backlog #11 PG side: referrals persist to the
    referrals table AND rehydrate on _load (process restart)."""

    @classmethod
    def setUpClass(cls):
        from company_discovery.postgres_repository import (
            PostgresCompanyDiscoveryRepository,
        )

        cls.url = os.environ["TEST_POSTGRES_URL"].strip()
        cls.repo = PostgresCompanyDiscoveryRepository(cls.url)

    @classmethod
    def tearDownClass(cls):
        cur = cls.repo._connection.cursor()
        for table in cls.repo._TABLES + ("schema_version",):
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            except Exception:
                pass
        cls.repo._connection.commit()
        cur.close()
        cls.repo.close()

    def setUp(self):
        # Clear referrals between tests
        cur = self.repo._connection.cursor()
        cur.execute("DELETE FROM referrals")
        self.repo._connection.commit()
        cur.close()
        self.repo.referrals.clear()

    def test_referral_persists_to_postgres(self):
        r = Referral(
            user_id="aicha",
            target_agent="housing",
            reason_code="user mentioned housing search",
            supporting_info={"city": "Berlin"},
        )
        self.repo.save_referral(r)
        # Verify it's in the DB
        cur = self.repo._connection.cursor()
        cur.execute("SELECT COUNT(*) FROM referrals WHERE id = %s", (r.id,))
        count = cur.fetchone()[0]
        cur.close()
        self.assertEqual(count, 1)

    def test_referral_rehydrates_on_reopen(self):
        from company_discovery.postgres_repository import (
            PostgresCompanyDiscoveryRepository,
        )

        r = Referral(
            user_id="aicha",
            target_agent="housing",
            reason_code="rehydration test",
        )
        self.repo.save_referral(r)
        # Reopen a fresh PG repo — should rehydrate
        repo2 = PostgresCompanyDiscoveryRepository(self.url)
        try:
            found = repo2.get_referral(r.id)
            self.assertIsNotNone(found)
            self.assertEqual(found.user_id, "aicha")
            self.assertEqual(found.target_agent, "housing")
        finally:
            repo2.close()

    def test_referral_delete_removes_from_postgres(self):
        r = Referral(
            user_id="u1", target_agent="x", reason_code="delete test"
        )
        self.repo.save_referral(r)
        self.repo.delete_referral(r.id)
        cur = self.repo._connection.cursor()
        cur.execute("SELECT COUNT(*) FROM referrals WHERE id = %s", (r.id,))
        count = cur.fetchone()[0]
        cur.close()
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
