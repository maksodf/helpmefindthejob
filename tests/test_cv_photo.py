"""CV photo upload validation tests.

Most security-sensitive surface in the CV builder. Must reject:
  - SVG (text-based, can carry script)
  - Files claimed as image but with wrong magic number
  - Empty / over-size uploads
  - Other exotic formats (ICO, TIFF, etc.)

Must strip EXIF / location metadata from accepted JPEGs.
Must strip text chunks from accepted PNGs."""

from __future__ import annotations

import base64
import struct
import unittest
import zlib

from company_discovery.cv_photo import (
    MAX_RAW_BYTES,
    PhotoValidationError,
    detect_image_mime,
    extract_data_uri_size,
    normalise_photo_upload,
)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk: length(4) + type(4) + data + crc(4)."""
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return (struct.pack(">I", len(data)) + chunk_type + data
            + struct.pack(">I", crc))


def _make_png(width: int = 1, height: int = 1) -> bytes:
    """Build a valid 1x1 RGB PNG. Hand-rolled so we control every byte."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _png_chunk(b"IHDR", ihdr_data)
    # 1 filter byte + 3 RGB bytes per pixel
    row = b"\x00\xff\xff\xff" * width
    raw = row * height
    idat = _png_chunk(b"IDAT", zlib.compress(raw))
    iend = _png_chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# Minimal valid JPEG byte sequences for testing.
_MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00" + b"\x08" * 64  # quantisation
    + b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    + b"\xff\xc4\x00\x14\x00\x01" + b"\x00" * 12 + b"\x01"
    + b"\xff\xc4\x00\x14\x10\x01" + b"\x00" * 12 + b"\x01"
    + b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfc\xff\xd9"
)
_MINIMAL_PNG = _make_png()

_FAKE_SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'


class MagicNumberTests(unittest.TestCase):
    def test_jpeg_detected(self):
        self.assertEqual(detect_image_mime(_MINIMAL_JPEG), "image/jpeg")

    def test_png_detected(self):
        self.assertEqual(detect_image_mime(_MINIMAL_PNG), "image/png")

    def test_svg_rejected(self):
        # SVG must NOT be accepted — its bytes don't match any of our
        # binary magic numbers, so detect returns None.
        self.assertIsNone(detect_image_mime(_FAKE_SVG))

    def test_text_rejected(self):
        self.assertIsNone(detect_image_mime(b"plain text file"))

    def test_empty_rejected(self):
        self.assertIsNone(detect_image_mime(b""))

    def test_webp_requires_signature(self):
        # RIFF prefix without WEBP at offset 8 → reject.
        bogus = b"RIFF" + b"\x00" * 8 + b"\x00" * 100
        self.assertIsNone(detect_image_mime(bogus))
        # With WEBP at offset 8 → accept.
        ok = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 100
        self.assertEqual(detect_image_mime(ok), "image/webp")

    def test_ico_rejected(self):
        # ICO starts with 00 00 01 00 — should fail magic check.
        self.assertIsNone(detect_image_mime(b"\x00\x00\x01\x00rest"))


class UploadValidationTests(unittest.TestCase):
    def test_jpeg_accepted(self):
        uri = normalise_photo_upload(_MINIMAL_JPEG)
        self.assertTrue(uri.startswith("data:image/jpeg;base64,"))

    def test_png_accepted(self):
        uri = normalise_photo_upload(_MINIMAL_PNG)
        self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_empty_rejected(self):
        with self.assertRaises(PhotoValidationError) as ctx:
            normalise_photo_upload(b"")
        self.assertEqual(str(ctx.exception), "empty")

    def test_oversize_rejected(self):
        # 600KB > 512KB limit. Even valid JPEG header doesn't matter.
        oversize = b"\xff\xd8\xff" + b"\x00" * (600 * 1024)
        with self.assertRaises(PhotoValidationError) as ctx:
            normalise_photo_upload(oversize)
        self.assertEqual(str(ctx.exception), "too_large")

    def test_svg_rejected(self):
        with self.assertRaises(PhotoValidationError) as ctx:
            normalise_photo_upload(_FAKE_SVG)
        self.assertEqual(str(ctx.exception), "unsupported_mime")

    def test_random_bytes_rejected(self):
        with self.assertRaises(PhotoValidationError) as ctx:
            normalise_photo_upload(b"random non-image bytes here" * 10)
        self.assertEqual(str(ctx.exception), "unsupported_mime")


class ExifStrippingTests(unittest.TestCase):
    """The cleaned JPEG must not contain any APP1 (EXIF) segment."""

    def test_jpeg_with_exif_stripped(self):
        # Build a JPEG with an APP1 EXIF segment carrying fake GPS text.
        exif_payload = b"Exif\x00\x00" + b"FAKE_GPS_COORDS_BLOCK" * 5
        seg_len = len(exif_payload) + 2  # length includes the 2 length bytes
        app1_seg = (
            b"\xff\xe1"
            + struct.pack(">H", seg_len)
            + exif_payload
        )
        jpeg_with_exif = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            + app1_seg
            + _MINIMAL_JPEG[20:]  # rest of the minimal JPEG
        )
        uri = normalise_photo_upload(jpeg_with_exif)
        # The data URI bytes must not contain the GPS marker — EXIF stripped.
        decoded = base64.b64decode(uri.split(",", 1)[1])
        self.assertNotIn(b"FAKE_GPS_COORDS_BLOCK", decoded)
        # And SOI marker must still be present (we didn't corrupt the file).
        self.assertTrue(decoded.startswith(b"\xff\xd8"))

    def test_png_with_text_chunk_stripped(self):
        """Inject a tEXt chunk and verify it's removed."""
        # Splice a proper-CRC tEXt chunk between IHDR (33 bytes incl sig)
        # and IDAT in the freshly-built PNG.
        text_chunk = _png_chunk(b"tEXt",
                                  b"Comment\x00sensitive_metadata_here")
        # Signature(8) + IHDR(4+4+13+4 = 25) = 33 bytes.
        png_with_text = _MINIMAL_PNG[:33] + text_chunk + _MINIMAL_PNG[33:]
        # Sanity: the injected raw definitely contains the marker.
        self.assertIn(b"sensitive_metadata_here", png_with_text)
        uri = normalise_photo_upload(png_with_text)
        decoded = base64.b64decode(uri.split(",", 1)[1])
        self.assertNotIn(b"sensitive_metadata_here", decoded)
        self.assertNotIn(b"tEXt", decoded)


class DataUriRoundTripTests(unittest.TestCase):
    def test_size_extraction(self):
        uri = normalise_photo_upload(_MINIMAL_JPEG)
        self.assertGreater(extract_data_uri_size(uri), 0)

    def test_size_returns_zero_on_malformed(self):
        self.assertEqual(extract_data_uri_size(None), 0)
        self.assertEqual(extract_data_uri_size(""), 0)
        self.assertEqual(extract_data_uri_size("not-a-data-uri"), 0)
        self.assertEqual(extract_data_uri_size("data:image/jpeg;base64,"), 0)


if __name__ == "__main__":
    unittest.main()
