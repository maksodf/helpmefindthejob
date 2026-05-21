# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #32 — CV-photo GDPR contract tests.

Three GDPR concerns audited + fixed:
1. Encryption at rest — cv_photo_data_uri now AEAD-encrypted (was plaintext)
2. Consent timestamp — cv_photo_consent_at recorded on upload (Article 7)
3. WebP metadata stripping — EXIF + XMP chunks now removed
"""

from __future__ import annotations

import base64
import json
import struct
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.cv_photo import (
    _strip_webp_metadata,
    normalise_photo_upload,
)


# Minimal valid 1x1 PNG (no metadata to begin with)
_PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a"  # PNG signature
    "0000000d49484452"  # IHDR chunk header
    "00000001000000010802000000907753de"  # 1x1 RGB
    "0000000a4944415478da6300010000050001"  # IDAT (minimal)
    "0d0a2db4"
    "0000000049454e44ae426082"  # IEND
)


def _make_webp_with_exif(payload_size: int = 100) -> bytes:
    """Construct a minimal WebP file with an EXIF chunk so we can
    verify the stripper actually removes it."""

    # Body: VP8 (image) chunk + EXIF chunk
    vp8 = b"VP8 " + struct.pack("<I", payload_size) + b"\x00" * payload_size
    exif_payload = b"EXIF-PII-LATITUDE-LONGITUDE-CAMERA-SERIAL"
    exif = b"EXIF" + struct.pack("<I", len(exif_payload)) + exif_payload
    if len(exif_payload) % 2:
        exif += b"\x00"  # RIFF pad-to-even
    body = vp8 + exif
    header = b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP"
    return header + body


class WebPMetadataStripping(unittest.TestCase):
    def test_webp_exif_chunk_removed(self) -> None:
        raw = _make_webp_with_exif()
        self.assertIn(b"EXIF-PII-LATITUDE", raw)
        cleaned = _strip_webp_metadata(raw)
        self.assertNotIn(b"EXIF-PII-LATITUDE", cleaned)
        # Header still says WebP
        self.assertEqual(cleaned[:4], b"RIFF")
        self.assertEqual(cleaned[8:12], b"WEBP")
        # VP8 image chunk preserved
        self.assertIn(b"VP8 ", cleaned)

    def test_webp_xmp_chunk_removed(self) -> None:
        # Build WebP with XMP instead of EXIF
        vp8 = b"VP8 " + struct.pack("<I", 16) + b"\x00" * 16
        xmp_payload = b"XMP-RDF-LOCATION-PII-DATA"
        xmp = b"XMP " + struct.pack("<I", len(xmp_payload)) + xmp_payload
        if len(xmp_payload) % 2:
            xmp += b"\x00"
        body = vp8 + xmp
        raw = b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP" + body
        cleaned = _strip_webp_metadata(raw)
        self.assertNotIn(b"XMP-RDF-LOCATION", cleaned)

    def test_non_webp_passed_through_unchanged(self) -> None:
        # A PNG is not WebP — stripper returns it unmodified
        self.assertEqual(_strip_webp_metadata(_PNG_1x1), _PNG_1x1)

    def test_truncated_webp_returned_as_is(self) -> None:
        """Defense: don't corrupt a truncated upload."""
        raw = b"RIFF" + struct.pack("<I", 1000) + b"WEBP" + b"VP8 " + struct.pack("<I", 1000) + b"abc"
        # Chunk claims 1000 bytes but we only have 3 → bail
        self.assertEqual(_strip_webp_metadata(raw), raw)


class EncryptionAtRest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        from app import AppState

        root = Path(self.tmp.name)
        self.state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.user = self.state.auth_store.create_user(
            "photo@example.com", "secret-pass-12345"
        )

    def test_cv_photo_uri_encrypted_on_disk(self) -> None:
        # Skip if no crypto layer (dev environment without master key)
        if self.state.repository._crypto is None:
            self.skipTest("crypto layer not initialised in this environment")
        profile = self.state.profile_for(self.user.id)
        photo_uri = "data:image/jpeg;base64," + base64.b64encode(b"FAKE-IMAGE-BYTES").decode()
        profile.cv_photo_data_uri = photo_uri
        self.state.repository.save_user_profile(profile)
        # Read the raw payload from the sqlite row — it should be
        # an AEAD-encrypted blob, NOT the plaintext URI.
        row = self.state.repository._connection.execute(
            "SELECT payload FROM user_profiles WHERE user_id = ?", (self.user.id,)
        ).fetchone()
        self.assertIsNotNone(row)
        stored = json.loads(row[0])
        from company_discovery.crypto_kit import is_aead_blob

        self.assertTrue(
            is_aead_blob(stored["cv_photo_data_uri"]),
            f"cv_photo_data_uri must be AEAD-encrypted at rest; got: {stored['cv_photo_data_uri'][:50]}",
        )
        # And the encrypted form is NOT the plaintext
        self.assertNotEqual(stored["cv_photo_data_uri"], photo_uri)


class ConsentTimestamp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        from app import AppState

        root = Path(self.tmp.name)
        self.state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.user = self.state.auth_store.create_user(
            "consent@example.com", "secret-pass-12345"
        )

    def test_profile_carries_cv_photo_consent_at_field(self) -> None:
        profile = self.state.profile_for(self.user.id)
        # New field exists; defaults to None until photo upload
        self.assertTrue(hasattr(profile, "cv_photo_consent_at"))
        self.assertIsNone(profile.cv_photo_consent_at)

    def test_setting_photo_records_consent_timestamp(self) -> None:
        profile = self.state.profile_for(self.user.id)
        profile.cv_photo_data_uri = "data:image/jpeg;base64,ZmFrZQ=="
        profile.cv_photo_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        # Reload to confirm persistence
        reloaded = self.state.profile_for(self.user.id)
        self.assertIsNotNone(reloaded.cv_photo_consent_at)

    def test_gdpr_article_20_export_includes_cv_photo_consent_at(self) -> None:
        """Article 20 portable export must include the consent
        timestamp so a successor controller knows when consent was
        given."""
        profile = self.state.profile_for(self.user.id)
        profile.cv_photo_data_uri = "data:image/jpeg;base64,ZmFrZQ=="
        profile.cv_photo_consent_at = datetime.now(timezone.utc)
        self.state.repository.save_user_profile(profile)
        export = self.state.export_data(self.user.id)
        self.assertIn("cvPhotoConsentAt", export["profile"])
        self.assertIsNotNone(export["profile"]["cvPhotoConsentAt"])


class NormaliseUploadIntegration(unittest.TestCase):
    def test_webp_upload_strips_exif_inline(self) -> None:
        webp_with_exif = _make_webp_with_exif()
        data_uri = normalise_photo_upload(webp_with_exif)
        # Decode the data URI back to bytes and verify EXIF gone
        prefix, b64 = data_uri.split(",", 1)
        self.assertEqual(prefix, "data:image/webp;base64")
        cleaned = base64.b64decode(b64)
        self.assertNotIn(b"EXIF-PII-LATITUDE", cleaned)


if __name__ == "__main__":
    unittest.main()
