# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Authenticated symmetric encryption for at-rest secrets.

Replaces the legacy XOR-with-derived-key path that was used for the
TOTP secret column and the plain-text CV column. Uses
``ChaCha20-Poly1305`` (AEAD) so a DB compromise no longer reveals
plaintext, and so a tampering attempt is detected on decrypt rather
than silently propagated.

Key material
------------

The encryption key (32 bytes) is resolved in this order:

1. ``DIRECTJOB_DATA_KEY`` — explicit, base64-encoded 32-byte key.
   Operator can rotate this independently of the secret key.
2. HKDF(``DIRECTJOB_SECRET_KEY``, info=b"directjob/data-key") — zero-
   config fallback. Tied to the lifetime of ``SECRET_KEY``: rotating
   the secret key invalidates encrypted data, exactly as the legacy
   XOR path did. Use this in development; configure a dedicated
   ``DIRECTJOB_DATA_KEY`` before public launch.

Encrypted blob format
---------------------

Strings produced by :meth:`EncryptionAtRest.encrypt` carry an explicit
version prefix so future format upgrades can co-exist with old data::

    aead:v1:<base64(nonce ‖ ciphertext ‖ tag)>

The decrypter routes by prefix. Anything without the prefix is treated
as legacy and the caller is responsible for re-encrypting on next
write (lazy migration).

The ``aad`` argument lets callers bind ciphertext to a record id (for
example, the user id), defeating swap-the-blob attacks. AAD is not
secret — it just has to match on encrypt and decrypt.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Final


_FORMAT_PREFIX: Final[str] = "aead:v1:"
_NONCE_BYTES: Final[int] = 12  # ChaCha20-Poly1305 nonce length
_KEY_BYTES: Final[int] = 32


def _hkdf_sha256(secret: bytes, *, salt: bytes, info: bytes, length: int) -> bytes:
    """Minimal HKDF-Extract-and-Expand (RFC 5869). Used only for the
    fallback derivation of the data key from SECRET_KEY."""

    if len(salt) == 0:
        salt = b"\x00" * hashlib.sha256().digest_size
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    okm = b""
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm += block
        counter += 1
    return okm[:length]


def resolve_data_key(secret_key: str) -> bytes:
    """Return the 32-byte master key, fetching from env or deriving."""

    explicit = os.environ.get("DIRECTJOB_DATA_KEY", "").strip()
    if explicit:
        try:
            decoded = base64.b64decode(explicit)
        except Exception as error:
            raise ValueError("invalid_data_key_base64") from error
        if len(decoded) != _KEY_BYTES:
            raise ValueError("invalid_data_key_length")
        return decoded
    if len(secret_key) < 32:
        raise ValueError("secret_key_too_short_for_derivation")
    return _hkdf_sha256(
        secret_key.encode("utf-8"),
        salt=b"directjob-scout/aead-v1",
        info=b"directjob/data-key",
        length=_KEY_BYTES,
    )


def is_aead_blob(value: str | None) -> bool:
    """Returns True when ``value`` was written by :class:`EncryptionAtRest`.
    Anything else — empty, None, legacy XOR-base64 — returns False."""

    return bool(value) and value.startswith(_FORMAT_PREFIX)


class EncryptionAtRest:
    """Thin wrapper around ChaCha20-Poly1305 with the project's blob
    format. Construct one per-process and share — the AEAD itself is
    threadsafe."""

    def __init__(self, key: bytes) -> None:
        if len(key) != _KEY_BYTES:
            raise ValueError("key_length")
        # Lazy import keeps the module importable even on systems
        # where cryptography fails to load (we'd never write through
        # this path on such a system anyway).
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        self._aead = ChaCha20Poly1305(key)

    @classmethod
    def from_secret_key(cls, secret_key: str) -> "EncryptionAtRest":
        return cls(resolve_data_key(secret_key))

    def encrypt(self, plaintext: str, *, aad: bytes = b"") -> str:
        nonce = secrets.token_bytes(_NONCE_BYTES)
        ciphertext = self._aead.encrypt(nonce, plaintext.encode("utf-8"), aad)
        return _FORMAT_PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, blob: str, *, aad: bytes = b"") -> str:
        if not is_aead_blob(blob):
            raise ValueError("not_aead_format")
        raw = base64.urlsafe_b64decode(blob[len(_FORMAT_PREFIX):])
        if len(raw) < _NONCE_BYTES + 16:  # 16-byte tag minimum
            raise ValueError("blob_too_short")
        nonce, ciphertext = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
        try:
            plaintext = self._aead.decrypt(nonce, ciphertext, aad)
        except Exception as error:
            raise ValueError("decrypt_failed") from error
        return plaintext.decode("utf-8")
