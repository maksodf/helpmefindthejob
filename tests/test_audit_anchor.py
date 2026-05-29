# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 5 (trustworthiness) — audit-chain anchoring + tamper detection.

The committed fixture (``tests/fixtures/audit_anchor/``) is a real v2 audit log
plus its anchor. A third party can verify it offline with no secret:

* the anchor still matches the log (``verify_anchor`` ok), and
* any edit / deletion of a record is detected — both by the salt-free anchor
  digest AND by the HMAC chain (defense in depth).

This is the offline half of the trust story. Submitting the anchor digest to
Sigstore Rekor / an RFC-3161 TSA is an operator/network step (see
``rekor_hashedrekord_digest``); this suite never fakes an inclusion proof.
"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.audit_anchor import (
    AuditAnchor,
    compute_anchor,
    load_anchor,
    rekor_hashedrekord_digest,
    verify_anchor,
    verify_chain_and_anchor,
)
from company_discovery.audit_log import AuditLogEmitter, verify_chain

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "audit_anchor"
_FIXTURE_LOG = _FIXTURE_DIR / "sample-audit-log.jsonl"
_FIXTURE_ANCHOR = _FIXTURE_DIR / "sample-anchor.json"
# Salt the committed fixture was generated with (pinned; the fixture is frozen).
_FIXTURE_SALT = b"audit-anchor-fixture-salt-v1____"


class CommittedFixtureVerifies(unittest.TestCase):
    def test_fixture_anchor_matches_its_log(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        result = verify_anchor([_FIXTURE_LOG], anchor)
        self.assertTrue(result.ok, result.to_dict())

    def test_fixture_chain_and_anchor_both_ok(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        combined = verify_chain_and_anchor([_FIXTURE_LOG], _FIXTURE_SALT, anchor)
        self.assertTrue(combined.ok, combined.to_dict())
        self.assertTrue(combined.chain.ok)
        self.assertTrue(combined.anchor.ok)

    def test_anchor_commits_to_three_records(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        self.assertEqual(anchor.record_count, 3)
        self.assertEqual(anchor.last_sequence_no, 3)
        self.assertEqual(len(anchor.content_digest), 64)  # sha256 hex


class TamperingIsDetected(unittest.TestCase):
    def _copy_fixture_log(self, tmp: str) -> Path:
        dst = Path(tmp) / "log.jsonl"
        shutil.copy(_FIXTURE_LOG, dst)
        return dst

    def test_editing_a_record_breaks_both_anchor_and_chain(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        with TemporaryDirectory() as tmp:
            log = self._copy_fixture_log(tmp)
            lines = log.read_text(encoding="utf-8").splitlines()
            rec = json.loads(lines[1])
            rec["outcome"] = "tampered"  # edit a field WITHOUT fixing the chain_hmac
            lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            anchor_res = verify_anchor([log], anchor)
            self.assertFalse(anchor_res.ok)
            self.assertEqual(anchor_res.reason, "content_digest_mismatch")
            self.assertNotEqual(anchor_res.actual_digest, anchor.content_digest)

            # Defense in depth: the HMAC chain also rejects the edit.
            self.assertFalse(verify_chain([log], _FIXTURE_SALT).ok)

    def test_deleting_a_record_is_detected(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        with TemporaryDirectory() as tmp:
            log = self._copy_fixture_log(tmp)
            lines = log.read_text(encoding="utf-8").splitlines()
            del lines[1]  # drop the middle record (sequence gap 1,3)
            log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            anchor_res = verify_anchor([log], anchor)
            self.assertFalse(anchor_res.ok)
            # fewer records AND a different digest — either is a valid first failure
            self.assertIn(
                anchor_res.reason,
                ("content_digest_mismatch", "record_count_mismatch:expected=3,actual=2"),
            )
            self.assertFalse(verify_chain([log], _FIXTURE_SALT).ok)


class FreshRoundTrip(unittest.TestCase):
    def test_compute_then_verify_then_tamper(self):
        with TemporaryDirectory() as tmp:
            log = Path(tmp) / "fresh.jsonl"
            salt = b"fresh-roundtrip-salt-0123456789x"
            emitter = AuditLogEmitter(log, salt)
            for _ in range(5):
                emitter.emit("system_event", outcome="ok")

            anchor = compute_anchor([log], created_at="2026-05-29T12:00:00+00:00")
            self.assertEqual(anchor.record_count, 5)
            self.assertTrue(verify_anchor([log], anchor).ok)

            # append a forged record (no valid chain_hmac) → both layers reject
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"schema_version": "v2", "sequence_no": 6, "forged": True}) + "\n")
            self.assertFalse(verify_anchor([log], anchor).ok)
            self.assertFalse(verify_chain([log], salt).ok)


class ExternalAnchorPayload(unittest.TestCase):
    def test_rekor_digest_shape(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        self.assertEqual(
            rekor_hashedrekord_digest(anchor), f"sha256:{anchor.content_digest}"
        )

    def test_anchor_dict_roundtrips(self):
        anchor = load_anchor(_FIXTURE_ANCHOR)
        restored = AuditAnchor.from_dict(anchor.to_dict())
        self.assertEqual(restored, anchor)


if __name__ == "__main__":
    unittest.main()
