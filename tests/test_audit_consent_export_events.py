# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for the M4 compliance record-keeping emissions.

Two AI-Act/GDPR audit record types were honestly documented as "specified but
not yet emitted" (audit-log-schema.md §4.4 / §4.5). They are now emitted:

- ``consent_event`` (§4.4, GDPR Art. 7) on AI-provider consent grant/revoke,
  naming the provider as the consent recipient in ``consent_scope``. The
  pre-existing ``log_analytics`` call is product telemetry; this is the
  tamper-evident, hash-chained legal record.
- ``export_event`` (§4.5, GDPR Art. 12/15/20) on every personal-data export —
  the user self-export AND an admin exporting a user's data. The admin export
  is recorded in the SUBJECT's own audit slice (``user_opaque_id`` = the
  target) so the data subject (and a regulator) can see the privileged access.

The helper-contract tests pin the exact §4.4/§4.5 payload shapes + chaining;
the app-wiring tests prove the real update_profile / export_data_audited code
paths emit them (not just the helpers in isolation).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import company_discovery.audit_log as audit_log
from company_discovery.audit_log import (
    AuditLogEmitter,
    emit_consent_event,
    emit_export_event,
    verify_chain,
)

_SALT = b"m4-consent-export-regression-test-salt"


def _emitter(tmp: str) -> tuple[AuditLogEmitter, Path]:
    log_path = Path(tmp) / "audit.log"
    return AuditLogEmitter(log_path, _SALT), log_path


def _records(log_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class HelperContractTests(unittest.TestCase):
    """emit_* helpers write exactly the §4.4/§4.5 payload shapes, hash-chained."""

    def test_consent_event_payload_and_chain(self) -> None:
        with TemporaryDirectory() as tmp:
            em, log_path = _emitter(tmp)
            emit_consent_event(
                consent_topic="ai_provider", consent_state="granted",
                consent_scope="openai", user_opaque_id="u1", emitter=em,
            )
            emit_consent_event(
                consent_topic="ai_provider", consent_state="revoked",
                user_opaque_id="u1", emitter=em,
            )
            recs = _records(log_path)
            self.assertEqual([r["event_type"] for r in recs], ["consent_event", "consent_event"])
            self.assertEqual(
                recs[0]["event_payload"],
                {"consent_topic": "ai_provider", "consent_state": "granted", "consent_scope": "openai"},
            )
            self.assertIsNone(recs[1]["event_payload"]["consent_scope"])
            # subject is hashed (not plaintext); same subject → same hash
            self.assertNotEqual(recs[0]["user_opaque_id"], "u1")
            self.assertEqual(recs[0]["user_opaque_id"], recs[1]["user_opaque_id"])
            self.assertTrue(verify_chain([log_path], em.salt).ok)

    def test_export_event_payload_and_subject_attribution(self) -> None:
        with TemporaryDirectory() as tmp:
            em, log_path = _emitter(tmp)
            emit_export_event(
                export_kind="profile_full", export_size_bytes=10,
                export_format="application/json", user_opaque_id="subject", emitter=em,
            )
            emit_export_event(
                export_kind="profile_full", export_size_bytes=20,
                export_format="application/json", user_opaque_id="other",
                caller="admin", emitter=em,
            )
            recs = _records(log_path)
            self.assertEqual(
                recs[0]["event_payload"],
                {"export_kind": "profile_full", "export_size_bytes": 10, "format": "application/json"},
            )
            self.assertEqual(recs[0]["caller"], "user")
            self.assertEqual(recs[1]["caller"], "admin")
            # distinct subjects land under distinct hashed ids
            self.assertNotEqual(recs[0]["user_opaque_id"], recs[1]["user_opaque_id"])
            self.assertTrue(verify_chain([log_path], em.salt).ok)


class AppWiringTests(unittest.TestCase):
    """The real app.py paths emit the events — not just the helpers."""

    def setUp(self) -> None:
        # Point the process-wide default emitter at a temp log (no setter
        # exists), saving the prior value so we never leak into other tests.
        self._saved_emitter = audit_log._default_emitter  # noqa: SLF001
        self._tmp = TemporaryDirectory()
        root = Path(self._tmp.name)
        self._log = root / "ai_act_audit.log"
        audit_log._default_emitter = AuditLogEmitter(self._log, _SALT)  # noqa: SLF001

        from app import AppState

        self.state = AppState(
            root / "c.sqlite3", root / "a.sqlite3", root / "ai.json", root / "s.json",
            start_scheduler=False,
        )
        self.uid = self.state.auth_store.create_user("m4@x.test", "M4TestPass123456").id

    def tearDown(self) -> None:
        self.state.auth_store.close()
        audit_log._default_emitter = self._saved_emitter  # noqa: SLF001
        self._tmp.cleanup()

    def test_update_profile_emits_consent_event(self) -> None:
        self.state.update_profile(self.uid, {"aiConsent": {"granted": True, "providerId": "gemini"}})
        self.state.update_profile(self.uid, {"aiConsent": {"granted": False}})
        recs = [r for r in _records(self._log) if r["event_type"] == "consent_event"]
        self.assertEqual(len(recs), 2, "consent grant + revoke must each emit a consent_event")
        self.assertEqual(recs[0]["event_payload"]["consent_state"], "granted")
        self.assertEqual(recs[0]["event_payload"]["consent_scope"], "gemini")
        self.assertEqual(recs[1]["event_payload"]["consent_state"], "revoked")
        self.assertTrue(verify_chain([self._log], _SALT).ok)

    def test_export_data_audited_emits_export_event_for_user_and_admin(self) -> None:
        self.state.export_data_audited(self.uid)
        self.state.export_data_audited(self.uid, caller="admin")
        recs = [r for r in _records(self._log) if r["event_type"] == "export_event"]
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["caller"], "user")
        self.assertEqual(recs[1]["caller"], "admin")
        self.assertGreater(recs[0]["event_payload"]["export_size_bytes"], 0)
        self.assertEqual(recs[0]["event_payload"]["format"], "application/json")
        self.assertEqual(recs[0]["event_payload"]["export_kind"], "profile_full")

    def test_overlong_provider_id_is_capped_in_consent_record(self) -> None:
        # A provider id is a short slug; an over-long value is capped at the
        # source so it cannot bloat the profile field, analytics, or the
        # consent_event audit record that all read from it.
        self.state.update_profile(
            self.uid, {"aiConsent": {"granted": True, "providerId": "x" * 200}}
        )
        recs = [r for r in _records(self._log) if r["event_type"] == "consent_event"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(
            len(recs[0]["event_payload"]["consent_scope"]), 64,
            "over-long provider_id must be capped at the source",
        )


if __name__ == "__main__":
    unittest.main()
