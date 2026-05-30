# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for two crypto-layer bugs found in the bug hunt:

1. `EncryptionAtRest.encrypt/decrypt` accepted a `str` AAD silently — on the
   Postgres path that crashed every CV save (encrypt) and silently wiped data
   on read (decrypt, caught + nulled). The boundary now rejects non-bytes AAD
   loudly so the mistake fails at the source instead of as data loss.

2. `_resolve_salt` used `base64.b64decode(validate=False)` + a `len >= 16`
   threshold, which silently dropped non-alphabet chars from passphrases and
   flipped interpretation across a 16-byte boundary (breaking chain continuity).
   It now only accepts the base64 form when it strictly validates AND is exactly
   32 bytes; otherwise the configured value is treated as raw bytes.
"""

from __future__ import annotations

import base64
import os
import unittest

from company_discovery.audit_log import _resolve_salt
from company_discovery.crypto_kit import EncryptionAtRest


class AadBytesContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enc = EncryptionAtRest(os.urandom(32))

    def test_str_aad_rejected_on_encrypt(self) -> None:
        with self.assertRaises(TypeError):
            self.enc.encrypt("cv text", aad="user-123")  # type: ignore[arg-type]

    def test_bytes_aad_roundtrips(self) -> None:
        blob = self.enc.encrypt("cv text", aad=b"user-123")
        self.assertEqual(self.enc.decrypt(blob, aad=b"user-123"), "cv text")

    def test_str_aad_rejected_on_decrypt(self) -> None:
        blob = self.enc.encrypt("cv text", aad=b"user-123")
        with self.assertRaises(TypeError):
            self.enc.decrypt(blob, aad="user-123")  # type: ignore[arg-type]

    def test_wrong_bytes_aad_still_fails_closed(self) -> None:
        blob = self.enc.encrypt("cv text", aad=b"user-123")
        with self.assertRaises(ValueError):
            self.enc.decrypt(blob, aad=b"attacker")


class ResolveSaltTests(unittest.TestCase):
    def test_proper_32_byte_base64_decodes(self) -> None:
        key = os.urandom(32)
        self.assertEqual(_resolve_salt(base64.b64encode(key).decode("ascii")), key)

    def test_passphrase_with_spaces_is_raw_not_mangled(self) -> None:
        phrase = "correct horse battery staple extra padding xx"
        # spaces are not in the base64 alphabet -> validate=True rejects -> raw path
        self.assertEqual(_resolve_salt(phrase), phrase.encode("utf-8"))

    def test_non_32_byte_base64_falls_through_to_raw(self) -> None:
        # 24-byte base64 used to be accepted (len>=16); now only exactly 32 bytes
        # is taken as base64, so this resolves to the raw string bytes instead.
        twenty_four = base64.b64encode(b"x" * 24).decode("ascii")
        self.assertEqual(_resolve_salt(twenty_four), twenty_four.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
