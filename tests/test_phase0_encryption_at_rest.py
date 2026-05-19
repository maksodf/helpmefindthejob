# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Encryption-at-rest covers Phase 0 tracker item #2.

Verifies that ``profile.cv_text`` is stored as an AEAD blob on disk
and round-trips back to plaintext through the repository, that
swapping the blob across users is rejected (AAD binding), and that a
legacy plaintext value migrates to the encrypted format on the next
save (lazy migration).
"""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.crypto_kit import EncryptionAtRest, is_aead_blob
from company_discovery.models import UserProfile
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository


class EncryptionAtRestTests(unittest.TestCase):
    def _open_repo(self, tmp: Path) -> tuple[SqliteCompanyDiscoveryRepository, EncryptionAtRest]:
        crypto = EncryptionAtRest.from_secret_key("x" * 64)
        repo = SqliteCompanyDiscoveryRepository(tmp / "company.sqlite3", crypto=crypto)
        self.addCleanup(repo._connection.close)
        return repo, crypto

    def _disk_cv(self, db_path: Path, user_id: str) -> str | None:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT payload FROM user_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return None
        return json.loads(row[0]).get("cv_text")

    def test_cv_text_is_aead_encrypted_on_disk(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _ = self._open_repo(root)
            user_id = "user_aead_1"
            profile = UserProfile(user_id=user_id, cv_text="my private CV with PII")
            repo.save_user_profile(profile)
            on_disk = self._disk_cv(root / "company.sqlite3", user_id)
            self.assertIsNotNone(on_disk)
            self.assertTrue(is_aead_blob(on_disk))
            self.assertNotIn("my private CV", on_disk)

    def test_cold_load_decrypts_cv_text(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_id = "user_aead_2"
            crypto = EncryptionAtRest.from_secret_key("x" * 64)
            repo = SqliteCompanyDiscoveryRepository(root / "company.sqlite3", crypto=crypto)
            repo.save_user_profile(UserProfile(user_id=user_id, cv_text="restored plaintext"))
            repo._connection.close()

            # Open a brand-new repo against the same file. This is the
            # cold-restart equivalent — the in-memory state is rebuilt
            # from the on-disk encrypted blob.
            fresh = SqliteCompanyDiscoveryRepository(root / "company.sqlite3", crypto=crypto)
            self.addCleanup(fresh._connection.close)
            loaded = fresh.user_profiles[user_id]
            self.assertEqual(loaded.cv_text, "restored plaintext")

    def test_aad_binds_blob_to_user_id(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            crypto = EncryptionAtRest.from_secret_key("x" * 64)
            repo = SqliteCompanyDiscoveryRepository(root / "company.sqlite3", crypto=crypto)
            repo.save_user_profile(UserProfile(user_id="alice", cv_text="alice CV"))
            repo.save_user_profile(UserProfile(user_id="bob", cv_text="bob CV"))
            repo._connection.close()

            # Swap Alice's blob into Bob's row on disk. On next load
            # the AAD check fails and Bob's cv_text drops to None
            # rather than leaking Alice's data.
            with sqlite3.connect(root / "company.sqlite3") as conn:
                alice_payload = json.loads(
                    conn.execute(
                        "SELECT payload FROM user_profiles WHERE user_id = ?", ("alice",)
                    ).fetchone()[0]
                )
                bob_payload = json.loads(
                    conn.execute(
                        "SELECT payload FROM user_profiles WHERE user_id = ?", ("bob",)
                    ).fetchone()[0]
                )
                bob_payload["cv_text"] = alice_payload["cv_text"]
                conn.execute(
                    "UPDATE user_profiles SET payload = ? WHERE user_id = ?",
                    (json.dumps(bob_payload), "bob"),
                )
                conn.commit()

            fresh = SqliteCompanyDiscoveryRepository(root / "company.sqlite3", crypto=crypto)
            self.addCleanup(fresh._connection.close)
            self.assertIsNone(fresh.user_profiles["bob"].cv_text)
            # Alice still decrypts cleanly.
            self.assertEqual(fresh.user_profiles["alice"].cv_text, "alice CV")

    def test_legacy_plaintext_migrates_on_next_save(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_id = "user_legacy"

            # Stage a profile written by an older code path: cv_text
            # stored as plain string in the JSON. The new repo should
            # read it as plaintext (legacy fallback) and then re-write
            # it encrypted on the next save.
            no_crypto = SqliteCompanyDiscoveryRepository(root / "company.sqlite3")
            no_crypto.save_user_profile(UserProfile(user_id=user_id, cv_text="legacy plain CV"))
            no_crypto._connection.close()

            # Verify the staged blob is plain (no aead prefix).
            with sqlite3.connect(root / "company.sqlite3") as conn:
                row = conn.execute(
                    "SELECT payload FROM user_profiles WHERE user_id = ?", (user_id,)
                ).fetchone()
                staged = json.loads(row[0]).get("cv_text")
                self.assertEqual(staged, "legacy plain CV")

            # Open with crypto, read profile (plaintext path), save.
            crypto = EncryptionAtRest.from_secret_key("x" * 64)
            repo = SqliteCompanyDiscoveryRepository(root / "company.sqlite3", crypto=crypto)
            self.addCleanup(repo._connection.close)
            profile = repo.user_profiles[user_id]
            self.assertEqual(profile.cv_text, "legacy plain CV")
            repo.save_user_profile(profile)

            # Now the on-disk value is aead-encrypted.
            with sqlite3.connect(root / "company.sqlite3") as conn:
                row = conn.execute(
                    "SELECT payload FROM user_profiles WHERE user_id = ?", (user_id,)
                ).fetchone()
                migrated = json.loads(row[0]).get("cv_text")
                self.assertTrue(is_aead_blob(migrated))


if __name__ == "__main__":
    unittest.main()
