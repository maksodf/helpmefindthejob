# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AEAD encryption fuzzing.

The CV / TOTP-secret encryption-at-rest is `ChaCha20-Poly1305`. The
encrypted-at-rest promise (P7) verified that plaintext does NOT leak
to disk; this module verifies the *cipher* under adversarial
conditions:

  - Tampered ciphertext (bit-flip, truncation, append, splice).
  - Wrong key (rotated key after encrypt).
  - Wrong AAD (swap-the-blob attack).
  - Garbage input that looks like the format prefix.
  - Base64 corruption / padding edge cases.
  - Empty / huge inputs.
  - Nonce uniqueness (the same plaintext must produce different
    ciphertexts each call).
  - Cross-version compatibility (v1 ciphertext fed to a future
    decoder must reject, not silently decrypt as garbage).

Every failure mode must surface as ``ValueError`` (or specifically
``"decrypt_failed"`` / format-prefix errors). None should return the
plaintext, none should crash with a non-ValueError exception, none
should silently return garbage."""

from __future__ import annotations

import base64
import os
import unittest

from company_discovery.crypto_kit import (
    _FORMAT_PREFIX,
    _NONCE_BYTES,
    EncryptionAtRest,
    is_aead_blob,
    resolve_data_key,
)


def _fresh_aead() -> EncryptionAtRest:
    """Construct a fresh AEAD with a random 32-byte key per test."""
    return EncryptionAtRest(os.urandom(32))


class HappyPathTests(unittest.TestCase):
    """Confirm round-trip correctness before stressing adversarial inputs."""

    def test_roundtrip(self):
        aead = _fresh_aead()
        plaintext = "Senior Engineer with 8y Python. Berlin."
        blob = aead.encrypt(plaintext)
        self.assertTrue(is_aead_blob(blob))
        self.assertTrue(blob.startswith(_FORMAT_PREFIX))
        self.assertEqual(aead.decrypt(blob), plaintext)

    def test_roundtrip_with_aad(self):
        aead = _fresh_aead()
        plaintext = "totp-secret-stuff"
        aad = b"user_abc123"
        blob = aead.encrypt(plaintext, aad=aad)
        self.assertEqual(aead.decrypt(blob, aad=aad), plaintext)

    def test_roundtrip_empty(self):
        aead = _fresh_aead()
        blob = aead.encrypt("")
        self.assertEqual(aead.decrypt(blob), "")

    def test_roundtrip_unicode(self):
        aead = _fresh_aead()
        plaintext = "🚀 Senior Engineer · München · Müller GmbH · 中文"
        blob = aead.encrypt(plaintext)
        self.assertEqual(aead.decrypt(blob), plaintext)

    def test_roundtrip_huge(self):
        """200 KB plaintext."""
        aead = _fresh_aead()
        plaintext = "Senior Engineer. " * 12_000  # ~200KB
        blob = aead.encrypt(plaintext)
        self.assertEqual(aead.decrypt(blob), plaintext)


class NonceUniquenessTests(unittest.TestCase):
    """Each encrypt() must use a fresh random nonce. Encrypting the
    SAME plaintext twice must produce DIFFERENT ciphertexts.

    Nonce reuse with ChaCha20-Poly1305 is catastrophic — it allows
    plaintext XOR recovery."""

    def test_same_plaintext_different_ciphertexts(self):
        aead = _fresh_aead()
        plaintext = "constant-string"
        blob_a = aead.encrypt(plaintext)
        blob_b = aead.encrypt(plaintext)
        self.assertNotEqual(blob_a, blob_b, "Nonce reuse: same plaintext → same ciphertext")

    def test_nonces_distinct_across_1000_encrypts(self):
        aead = _fresh_aead()
        seen_nonces: set[bytes] = set()
        for _ in range(1000):
            blob = aead.encrypt("x")
            raw = base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX) :])
            nonce = raw[:_NONCE_BYTES]
            self.assertNotIn(nonce, seen_nonces, "duplicate nonce detected")
            seen_nonces.add(nonce)


class BitFlipTamperingTests(unittest.TestCase):
    """Flip a single bit in the ciphertext. Decryption must reject."""

    def _flip_nth_byte(self, blob: str, byte_index: int, xor_mask: int = 0x01) -> str:
        raw = bytearray(base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX) :]))
        raw[byte_index] ^= xor_mask
        return _FORMAT_PREFIX + base64.urlsafe_b64encode(bytes(raw)).decode("ascii")

    def test_flip_first_byte_of_ciphertext(self):
        aead = _fresh_aead()
        blob = aead.encrypt("secret message")
        # Byte 12 is the start of ciphertext (after the 12-byte nonce).
        tampered = self._flip_nth_byte(blob, 12)
        with self.assertRaises(ValueError):
            aead.decrypt(tampered)

    def test_flip_middle_byte(self):
        aead = _fresh_aead()
        blob = aead.encrypt("a" * 200)
        # Halfway through the ciphertext.
        tampered = self._flip_nth_byte(blob, 100)
        with self.assertRaises(ValueError):
            aead.decrypt(tampered)

    def test_flip_tag_byte(self):
        """The last 16 bytes are the Poly1305 tag."""
        aead = _fresh_aead()
        blob = aead.encrypt("short")
        raw = base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX) :])
        # -1 is the last byte of the tag.
        tampered = self._flip_nth_byte(blob, len(raw) - 1)
        with self.assertRaises(ValueError):
            aead.decrypt(tampered)

    def test_flip_nonce_byte(self):
        aead = _fresh_aead()
        blob = aead.encrypt("nonce-attack")
        # Flipping a nonce byte means the AEAD decrypts with a wrong
        # nonce → tag mismatch.
        tampered = self._flip_nth_byte(blob, 0)
        with self.assertRaises(ValueError):
            aead.decrypt(tampered)


class TruncationTests(unittest.TestCase):
    """Lop bytes off the end. Decryption must reject."""

    def test_truncate_last_byte(self):
        aead = _fresh_aead()
        blob = aead.encrypt("important")
        raw = base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX) :])
        truncated_raw = raw[:-1]
        truncated_blob = _FORMAT_PREFIX + base64.urlsafe_b64encode(truncated_raw).decode("ascii")
        with self.assertRaises(ValueError):
            aead.decrypt(truncated_blob)

    def test_truncate_to_nonce_only(self):
        aead = _fresh_aead()
        blob = aead.encrypt("important")
        raw = base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX) :])
        truncated_blob = _FORMAT_PREFIX + base64.urlsafe_b64encode(raw[:_NONCE_BYTES]).decode(
            "ascii"
        )
        with self.assertRaises(ValueError):
            aead.decrypt(truncated_blob)

    def test_truncate_below_minimum_length(self):
        aead = _fresh_aead()
        # Anything shorter than nonce + tag (12 + 16) must reject early.
        short_blob = _FORMAT_PREFIX + base64.urlsafe_b64encode(b"\x00" * 16).decode("ascii")
        with self.assertRaises(ValueError):
            aead.decrypt(short_blob)


class AppendedJunkTests(unittest.TestCase):
    """Append garbage bytes after a valid ciphertext."""

    def test_append_byte_changes_tag_position(self):
        aead = _fresh_aead()
        blob = aead.encrypt("ok")
        raw = base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX) :])
        # Append 16 bytes of garbage so the new "tag" reads from wrong place.
        polluted = _FORMAT_PREFIX + base64.urlsafe_b64encode(raw + b"\x00" * 16).decode("ascii")
        with self.assertRaises(ValueError):
            aead.decrypt(polluted)


class WrongKeyTests(unittest.TestCase):
    """Decrypting with a different key must reject."""

    def test_wrong_key_rejects(self):
        aead_a = _fresh_aead()
        aead_b = _fresh_aead()  # different random key
        blob = aead_a.encrypt("for-a")
        with self.assertRaises(ValueError):
            aead_b.decrypt(blob)


class WrongAadTests(unittest.TestCase):
    """AAD binds ciphertext to a context (e.g., user_id). Different AAD on
    decrypt must reject."""

    def test_wrong_aad_rejects(self):
        aead = _fresh_aead()
        blob = aead.encrypt("user-cv", aad=b"user_alice")
        with self.assertRaises(ValueError):
            aead.decrypt(blob, aad=b"user_bob")

    def test_aad_strict_match(self):
        """Decrypting without AAD when AAD was supplied at encrypt → reject."""
        aead = _fresh_aead()
        blob = aead.encrypt("user-cv", aad=b"user_alice")
        with self.assertRaises(ValueError):
            aead.decrypt(blob)  # default aad=b""


class FormatPrefixTests(unittest.TestCase):
    """The version prefix routes decryption. Without it, the decrypter
    must reject — even if the body decodes."""

    def test_missing_prefix(self):
        aead = _fresh_aead()
        blob = aead.encrypt("secret")
        # Strip the prefix entirely.
        bare = blob[len(_FORMAT_PREFIX) :]
        with self.assertRaises(ValueError):
            aead.decrypt(bare)

    def test_wrong_prefix(self):
        aead = _fresh_aead()
        blob = aead.encrypt("secret")
        swapped = "aead:v9:" + blob[len(_FORMAT_PREFIX) :]
        with self.assertRaises(ValueError):
            aead.decrypt(swapped)

    def test_legacy_xor_marker_rejects(self):
        # Anything not starting with "aead:v1:" is treated as not-aead.
        bogus = "legacy:" + base64.urlsafe_b64encode(b"junk" * 8).decode("ascii")
        self.assertFalse(is_aead_blob(bogus))
        aead = _fresh_aead()
        with self.assertRaises(ValueError):
            aead.decrypt(bogus)

    def test_empty_string(self):
        aead = _fresh_aead()
        with self.assertRaises(ValueError):
            aead.decrypt("")

    def test_none_blob_rejects(self):
        aead = _fresh_aead()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            aead.decrypt(None)  # type: ignore[arg-type]


class Base64CorruptionTests(unittest.TestCase):
    """Body that doesn't decode cleanly must reject without crashing."""

    def test_invalid_base64_chars(self):
        aead = _fresh_aead()
        bogus = _FORMAT_PREFIX + "this is not base64 !!!!"
        with self.assertRaises((ValueError, Exception)):
            aead.decrypt(bogus)

    def test_truncated_base64(self):
        aead = _fresh_aead()
        bogus = _FORMAT_PREFIX + "Q"
        with self.assertRaises((ValueError, Exception)):
            aead.decrypt(bogus)


class CrossInstanceTamperingTests(unittest.TestCase):
    """Splice ciphertext from one plaintext into the nonce of another."""

    def test_splice_attack_rejects(self):
        aead = _fresh_aead()
        blob_a = aead.encrypt("plaintext A")
        blob_b = aead.encrypt("plaintext B")
        raw_a = base64.urlsafe_b64decode(blob_a[len(_FORMAT_PREFIX) :])
        raw_b = base64.urlsafe_b64decode(blob_b[len(_FORMAT_PREFIX) :])
        # Take nonce from A, ciphertext+tag from B.
        spliced = raw_a[:_NONCE_BYTES] + raw_b[_NONCE_BYTES:]
        spliced_blob = _FORMAT_PREFIX + base64.urlsafe_b64encode(spliced).decode("ascii")
        with self.assertRaises(ValueError):
            aead.decrypt(spliced_blob)


class HugeBlobTests(unittest.TestCase):
    """Adversarial huge inputs shouldn't DoS the decoder. Note: legitimate
    decryption only happens when the row was written by the same code,
    so 'huge' here means a maliciously crafted blob that's larger than
    any real CV. Decoder should either reject or accept gracefully."""

    def test_decode_1mb_random_bytes(self):
        aead = _fresh_aead()
        # 1MB of random bytes pretending to be a valid encrypted blob.
        bogus_raw = os.urandom(1_000_000)
        bogus_blob = _FORMAT_PREFIX + base64.urlsafe_b64encode(bogus_raw).decode("ascii")
        with self.assertRaises(ValueError):
            aead.decrypt(bogus_blob)


class DataKeyDerivationTests(unittest.TestCase):
    """resolve_data_key must reject malformed inputs and produce
    deterministic output for HKDF fallback."""

    def test_short_secret_key_rejected(self):
        with self.assertRaises(ValueError):
            resolve_data_key("short")  # < 32 chars

    def test_hkdf_deterministic(self):
        key1 = resolve_data_key("x" * 64)
        key2 = resolve_data_key("x" * 64)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)

    def test_hkdf_differs_per_secret(self):
        key1 = resolve_data_key("a" * 64)
        key2 = resolve_data_key("b" * 64)
        self.assertNotEqual(key1, key2)

    def test_explicit_data_key_env(self):
        """When DIRECTJOB_DATA_KEY is set, it must be base64-decodable
        AND exactly 32 bytes — otherwise raise."""
        # 32-byte valid key
        valid_key = os.urandom(32)
        try:
            os.environ["DIRECTJOB_DATA_KEY"] = base64.b64encode(valid_key).decode("ascii")
            self.assertEqual(resolve_data_key("any-secret-key-here"), valid_key)
            # invalid base64
            os.environ["DIRECTJOB_DATA_KEY"] = "%%%not base64%%%"
            with self.assertRaises(ValueError):
                resolve_data_key("any")
            # wrong length
            os.environ["DIRECTJOB_DATA_KEY"] = base64.b64encode(b"short").decode("ascii")
            with self.assertRaises(ValueError):
                resolve_data_key("any")
        finally:
            os.environ.pop("DIRECTJOB_DATA_KEY", None)


class KeyLengthGuardTests(unittest.TestCase):
    """The EncryptionAtRest constructor must reject wrong key sizes."""

    def test_31_byte_key_rejected(self):
        with self.assertRaises(ValueError):
            EncryptionAtRest(b"x" * 31)

    def test_33_byte_key_rejected(self):
        with self.assertRaises(ValueError):
            EncryptionAtRest(b"x" * 33)

    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError):
            EncryptionAtRest(b"")


if __name__ == "__main__":
    unittest.main()
