"""CV photo handling — upload validation + EXIF stripping.

DACH CVs traditionally include a portrait photo (different convention
from US/UK where photos are discouraged). The CV builder must support
this, but the upload path is the most security-sensitive surface:

  - Reject non-image MIME types (defence against executable upload).
  - Reject SVG specifically — SVG can carry ``<script>`` and onload
    handlers that fire when the CV is rendered.
  - Reject anything above 512KB raw (~700KB base64) — large photos
    bloat the SQLite blob and the CV-export payload.
  - Strip EXIF metadata (GPS, camera serial, timestamps) for privacy —
    a candidate's photo should not leak their home address.
  - Return a self-contained ``data:image/...;base64,...`` URI so the
    CV markdown renders offline and exports cleanly.

The byte-level validation runs WITHOUT any external dependencies (no
Pillow, no imagemagick) so it works in a stdlib-only environment. We
do a magic-number check rather than trusting the client-declared MIME.
"""

from __future__ import annotations

import base64
import re
from typing import Final


MAX_RAW_BYTES: Final[int] = 512 * 1024  # 512KB raw image (~700KB b64)


# Magic-number prefixes for the image types we accept. Anything else
# is rejected at upload — including SVG (text-based, can carry script).
_MAGIC_NUMBERS: dict[str, bytes] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"RIFF",  # also requires "WEBP" at offset 8
}


class PhotoValidationError(ValueError):
    """Raised when an uploaded photo fails any safety / size check.

    The error code is one of:
      - "too_large"
      - "empty"
      - "unsupported_mime"
      - "magic_mismatch"
      - "webp_signature_mismatch"
    """


def detect_image_mime(raw: bytes) -> str | None:
    """Return the canonical MIME type from the magic-number prefix, or
    None when the bytes don't match any accepted type."""
    if not raw:
        return None
    for mime, prefix in _MAGIC_NUMBERS.items():
        if raw.startswith(prefix):
            if mime == "image/webp":
                # WebP also needs 'WEBP' at offset 8 to be valid.
                if len(raw) < 12 or raw[8:12] != b"WEBP":
                    return None
            return mime
    return None


def _strip_jpeg_exif(raw: bytes) -> bytes:
    """Remove EXIF/APP1 segments from a JPEG without re-encoding.

    JPEG structure: SOI (FFD8) | segments | image data | EOI (FFD9).
    Each segment is `FF Xn LEN_HI LEN_LO ...`. APP1 (FFE1) is where
    EXIF lives. We pass through SOI, skip APP1 segments, keep
    everything else.

    Returns the stripped bytes. If parsing fails for any reason we
    return the original bytes — never crash, but log via the
    PhotoValidationError pathway if the caller wants strictness.
    """
    if not raw.startswith(b"\xff\xd8"):
        return raw
    out = bytearray(raw[:2])  # SOI
    i = 2
    n = len(raw)
    while i < n:
        if raw[i] != 0xFF:
            # Outside a segment header — must be image data. Append rest.
            out.extend(raw[i:])
            return bytes(out)
        marker = raw[i + 1] if i + 1 < n else None
        if marker is None:
            return raw
        # Standalone markers (no length field): SOI/EOI/RSTn.
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            out.extend(raw[i:i + 2])
            i += 2
            continue
        # SOS (FFDA) signals start-of-scan; everything after is image
        # data until EOI. Keep verbatim.
        if marker == 0xDA:
            out.extend(raw[i:])
            return bytes(out)
        # Length-prefixed segment.
        if i + 4 > n:
            return raw  # malformed; bail
        seg_len = (raw[i + 2] << 8) | raw[i + 3]
        seg_end = i + 2 + seg_len
        if seg_end > n or seg_len < 2:
            return raw  # malformed; bail
        # Drop APP1 (EXIF) and APP13 (Photoshop IPTC) — both carry
        # location / camera / authorship metadata we don't want to leak.
        if marker in {0xE1, 0xED}:
            i = seg_end
            continue
        out.extend(raw[i:seg_end])
        i = seg_end
    return bytes(out)


def _strip_png_metadata(raw: bytes) -> bytes:
    """Remove ancillary PNG chunks (text/timestamp/EXIF). PNG structure:
    8-byte signature + chunks. Each chunk: length(4) + type(4) +
    data(length) + crc(4). Chunk types starting with lowercase are
    ancillary (safe to drop). We keep IHDR/PLTE/IDAT/IEND verbatim."""
    sig = b"\x89PNG\r\n\x1a\n"
    if not raw.startswith(sig):
        return raw
    out = bytearray(sig)
    i = len(sig)
    n = len(raw)
    while i < n:
        if i + 8 > n:
            return raw
        length = int.from_bytes(raw[i:i + 4], "big")
        chunk_type = raw[i + 4:i + 8]
        chunk_end = i + 8 + length + 4
        if chunk_end > n:
            return raw
        # Critical chunks (uppercase first byte) — keep.
        is_ancillary = chunk_type[0:1].islower()
        # Always strip eXIf, tEXt, zTXt, iTXt, tIME chunks. They carry
        # metadata; tEXt can contain arbitrary key/value text.
        drop_types = {b"eXIf", b"tEXt", b"zTXt", b"iTXt", b"tIME"}
        if chunk_type in drop_types or is_ancillary:
            i = chunk_end
            continue
        out.extend(raw[i:chunk_end])
        i = chunk_end
        if chunk_type == b"IEND":
            break
    return bytes(out)


def normalise_photo_upload(raw: bytes) -> str:
    """Validate + EXIF-strip + return a data URI ready for storage.

    Raises ``PhotoValidationError`` on any failure. The returned URI is
    safe to embed in HTML / Markdown / PDF — it's pure base64."""

    if not raw:
        raise PhotoValidationError("empty")
    if len(raw) > MAX_RAW_BYTES:
        raise PhotoValidationError("too_large")
    mime = detect_image_mime(raw)
    if mime is None:
        raise PhotoValidationError("unsupported_mime")
    if mime == "image/jpeg":
        cleaned = _strip_jpeg_exif(raw)
    elif mime == "image/png":
        cleaned = _strip_png_metadata(raw)
    else:
        # WebP — no metadata stripping for now (rare on real CVs).
        cleaned = raw
    encoded = base64.b64encode(cleaned).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def extract_data_uri_size(data_uri: str | None) -> int:
    """Decoded-bytes size of a stored photo URI. Returns 0 when absent
    or malformed."""
    if not data_uri or not data_uri.startswith("data:"):
        return 0
    match = re.match(r"^data:image/[a-z]+;base64,(.+)$", data_uri)
    if not match:
        return 0
    try:
        return len(base64.b64decode(match.group(1), validate=False))
    except Exception:  # noqa: BLE001
        return 0
