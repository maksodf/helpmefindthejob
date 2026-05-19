# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Tests for the AEAD migration of the TOTP-secret column.

The TOTP secret column lived on a legacy XOR-with-SHA256-derived-key path
until the AEAD migration. These tests cover both the new path
(:meth:`_encrypt_secret`/:meth:`_decrypt_secret` on AEAD) and the
forward-compatible read of legacy blobs via the lazy-migration helper
(:meth:`_migrate_legacy_totp_if_needed`).

Coverage:

- AEAD round-trip
- Tamper detection on AEAD ciphertext
- AAD mismatch detection (user-id binding)
- Nonce uniqueness across 100 encrypts of the same plaintext
- Legacy XOR blob still decrypts correctly (read continuity)
- Lazy migration: first read of a legacy blob through
  :meth:`verify_user_totp` upgrades the column to AEAD on disk.
"""

from __future__ import annotations

import base64
import hashlib
import secrets as _secrets
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from company_discovery.auth import AuthStore, _totp_at, verify_totp
from company_discovery.crypto_kit import is_aead_blob

SECRET_KEY = "x" * 64  # >= 32 chars required for HKDF derivation.


def _legacy_xor_encode(secret_b32: str, secret_key: str) -> str:
    """Reproduce the pre-migration encoder so we can seed legacy rows."""

    salt = _secrets.token_bytes(8)
    key = hashlib.sha256(secret_key.encode("utf-8") + salt).digest()
    data = secret_b32.encode("ascii")
    ciphertext = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.b64encode(salt + ciphertext).decode("ascii")


class _TotpAeadMigrationTestBase(unittest.TestCase):
    """Shared fixture: clean SQLite repo + one enrolled user."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.auth = AuthStore(
            self.tmp_path / "auth.sqlite3",
            secret_key=SECRET_KEY,
        )
        self.user = self.auth.create_user(
            "alice@example.test",
            "correct horse battery staple",
        )

    def tearDown(self) -> None:
        try:
            self.auth.close()
        except Exception:
            pass
        self._tmp.cleanup()

    def _stored_totp_blob(self, user_id: str) -> str:
        row = self.auth.connection.execute(
            "SELECT totp_secret FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        self.assertIsNotNone(row)
        return row[0]


class AeadRoundTripTests(_TotpAeadMigrationTestBase):
    def test_encrypt_decrypt_roundtrip(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"  # canonical RFC 4648 §6 test vector
        blob = self.auth._encrypt_secret(secret, self.user.id)
        self.assertTrue(is_aead_blob(blob))
        self.assertEqual(self.auth._decrypt_secret(blob, self.user.id), secret)

    def test_blob_uses_documented_prefix(self) -> None:
        blob = self.auth._encrypt_secret("AAAA", self.user.id)
        self.assertTrue(blob.startswith("aead:v1:"))

    def test_tamper_detection(self) -> None:
        blob = self.auth._encrypt_secret("SECRETXYZ", self.user.id)
        tampered = blob[:-4] + "AAAA"
        with self.assertRaises(ValueError):
            self.auth._decrypt_secret(tampered, self.user.id)

    def test_aad_mismatch_fails_decrypt(self) -> None:
        """The user id is the AAD — swapping the row to another user must
        fail authentication."""

        blob = self.auth._encrypt_secret("SECRETXYZ", self.user.id)
        attacker = self.auth.create_user(
            "bob@example.test",
            "correct horse battery staple",
        )
        with self.assertRaises(ValueError):
            self.auth._decrypt_secret(blob, attacker.id)

    def test_nonce_uniqueness_across_100_encrypts(self) -> None:
        """Same plaintext, same key, 100 encrypts → 100 distinct blobs.

        Failure mode this catches: deterministic nonce / nonce reuse,
        which breaks the AEAD security guarantee."""

        secret = "JBSWY3DPEHPK3PXP"
        blobs = {self.auth._encrypt_secret(secret, self.user.id) for _ in range(100)}
        self.assertEqual(len(blobs), 100)


class LegacyReadCompatibilityTests(_TotpAeadMigrationTestBase):
    """The legacy XOR-base64 format must still decrypt for users whose
    rows were written before the migration. The lazy-migration helper
    then upgrades the row on first read."""

    def test_legacy_blob_decrypts_unchanged(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"
        legacy_blob = _legacy_xor_encode(secret, SECRET_KEY)
        self.assertFalse(is_aead_blob(legacy_blob))
        plaintext = self.auth._decrypt_secret(legacy_blob, self.user.id)
        self.assertEqual(plaintext, secret)

    def test_migrate_legacy_helper_upgrades_blob(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"
        legacy_blob = _legacy_xor_encode(secret, SECRET_KEY)
        self.auth.connection.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?",
            (legacy_blob, self.user.id),
        )
        self.auth.connection.commit()

        self.assertFalse(is_aead_blob(self._stored_totp_blob(self.user.id)))
        self.auth._migrate_legacy_totp_if_needed(self.user.id, legacy_blob)

        upgraded = self._stored_totp_blob(self.user.id)
        self.assertTrue(is_aead_blob(upgraded))
        self.assertEqual(
            self.auth._decrypt_secret(upgraded, self.user.id),
            secret,
        )

    def test_migrate_legacy_helper_idempotent_on_aead(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"
        blob_before = self.auth._encrypt_secret(secret, self.user.id)
        self.auth.connection.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?",
            (blob_before, self.user.id),
        )
        self.auth.connection.commit()
        self.auth._migrate_legacy_totp_if_needed(self.user.id, blob_before)
        self.assertEqual(self._stored_totp_blob(self.user.id), blob_before)

    def test_migrate_skipped_on_empty_blob(self) -> None:
        self.auth._migrate_legacy_totp_if_needed(self.user.id, "")


class VerifyPathTriggersMigrationTests(_TotpAeadMigrationTestBase):
    """End-to-end: seed a legacy blob, call verify_user_totp with a valid
    code, and confirm the row was upgraded to AEAD on disk."""

    def test_verify_user_totp_migrates_legacy_row(self) -> None:
        from datetime import datetime

        # Pin a fixed secret + matching code so we don't depend on time.
        secret = "JBSWY3DPEHPK3PXP"
        legacy_blob = _legacy_xor_encode(secret, SECRET_KEY)
        self.auth.connection.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?",
            (legacy_blob, self.user.id),
        )
        self.auth.connection.commit()
        self.assertFalse(is_aead_blob(self._stored_totp_blob(self.user.id)))

        # Compute the current valid code from the plaintext secret so the
        # test does not depend on clock-skew tolerance.
        now = datetime.now(timezone.utc)
        code = _totp_at(secret, when=now)
        accepted = self.auth.verify_user_totp(self.user.id, code)
        self.assertTrue(accepted)

        upgraded = self._stored_totp_blob(self.user.id)
        self.assertTrue(is_aead_blob(upgraded))


if __name__ == "__main__":
    unittest.main()
