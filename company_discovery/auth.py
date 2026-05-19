# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Type-only import: the EncryptionAtRest class is annotated in
    # _totp_crypto's return type and imported at runtime inside the
    # method body (so cryptography can be lazy-loaded). Keep this
    # import under TYPE_CHECKING so it's visible to type checkers
    # (mypy) and to ruff's name-resolution but does not execute at
    # import time.
    from .crypto_kit import EncryptionAtRest

PBKDF2_ITERATIONS = 240_000
MIN_PASSWORD_LENGTH = 12

# TOTP (RFC 6238): 6-digit codes, 30-second window, SHA1 — interoperable
# with Google Authenticator, Authy, 1Password, Aegis. We accept the
# previous and next 30s windows to forgive clock drift / round-the-edge
# cases (one window each direction).
TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6
TOTP_DRIFT_WINDOWS = 1


def _b32_secret(byte_length: int = 20) -> str:
    """Generate a base32 secret of the given byte length (default 20 = 160 bits)."""

    import base64

    raw = secrets.token_bytes(byte_length)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _totp_at(
    secret_b32: str, *, when: datetime, period: int = TOTP_PERIOD_SECONDS, digits: int = TOTP_DIGITS
) -> str:
    """RFC 6238 TOTP code computation using the stdlib (no pyotp dep)."""

    import base64
    import struct

    counter = int(when.timestamp() // period)
    # base32 may have been stored without padding; restore it.
    pad = "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode((secret_b32 + pad).upper())
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10**digits)).zfill(digits)


def verify_totp(secret_b32: str, code: str, *, when: datetime | None = None) -> bool:
    """Verify a TOTP code with ±1 window drift tolerance."""

    if not secret_b32 or not code or not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    when = when or now_utc()
    for offset in range(-TOTP_DRIFT_WINDOWS, TOTP_DRIFT_WINDOWS + 1):
        from datetime import timedelta

        candidate = _totp_at(
            secret_b32, when=when + timedelta(seconds=offset * TOTP_PERIOD_SECONDS)
        )
        if hmac.compare_digest(candidate, code):
            return True
    return False


def _format_otpauth_url(*, secret_b32: str, account: str, issuer: str = "Helpmefindthejob") -> str:
    """Build the otpauth:// URL that authenticator apps consume via QR code."""

    from urllib.parse import quote

    label = f"{issuer}:{account}"
    return (
        f"otpauth://totp/{quote(label)}"
        f"?secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&algorithm=SHA1"
        f"&digits={TOTP_DIGITS}"
        f"&period={TOTP_PERIOD_SECONDS}"
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


# Basic RFC-5321-ish email shape check. Intentionally lenient — we don't
# do full RFC parsing (real-world addresses are weird) but we DO reject
# the obvious-invalid shapes that the chaos agent surfaced:
#   - missing local part: "@example.com"
#   - missing domain: "user@"
#   - dot-leading domain: "user@.com"
#   - whitespace anywhere: "user space@x.com"
#   - no TLD: "user@example"
_EMAIL_SHAPE_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9](?:[A-Za-z0-9.\-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}$"
)


def is_valid_email_shape(email: str) -> bool:
    """True iff the email passes the basic shape check above. Operates
    on the *normalized* (stripped + casefolded) form."""
    normalized = _normalize_email(email)
    if not normalized or len(normalized) > 254:
        return False
    return bool(_EMAIL_SHAPE_RE.match(normalized))


def _hash_token(secret_key: str, token: str) -> str:
    return hmac.new(secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt_bytes = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(expected.hex(), digest_hex)


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    role: str
    active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin" and self.active


@dataclass(frozen=True)
class AuthSession:
    token: str
    user: AuthUser
    csrf_token: str
    expires_at: datetime


class AuthStore:
    """Auth state on SQLite. Threading model: each thread gets its own
    sqlite3.Connection via the ``connection`` property + thread-local
    storage. Sharing one connection across threads (the previous
    design) caused cursor-state races under burst — sqlite3 raised
    ``ProgrammingError("bad parameter or other API misuse")`` when
    two threads ran ``.execute(...).fetchone()`` interleaved on the
    same connection. WAL mode + a 5s busy_timeout per-connection
    handle the actual on-disk concurrency; per-thread Python
    connections handle the in-process Cursor-state isolation.

    Schema setup runs once in __init__ on the main thread's connection;
    subsequent threads see the migrated schema via WAL — sqlite
    auto-syncs readers with the latest committed write."""

    def __init__(
        self,
        path: str | Path,
        secret_key: str,
        *,
        session_ttl_days: int = 14,
    ) -> None:
        if len(secret_key) < 32:
            raise ValueError("secret_key_too_short")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_key = secret_key
        self.session_ttl = timedelta(days=session_ttl_days)
        self._local = threading.local()
        # Eagerly run schema setup on this (the constructing) thread's
        # connection. The property lazily creates per-thread handles
        # for any other threads that touch the store later.
        self._create_schema()

    @property
    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            # Wait up to 5s for a write lock instead of failing
            # immediately when another thread holds it. With <100
            # active users the contention window is sub-millisecond
            # in practice; 5s is a generous ceiling.
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _create_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        self._add_column_if_missing("users", "role", "TEXT NOT NULL DEFAULT 'member'")
        self._add_column_if_missing("users", "active", "INTEGER NOT NULL DEFAULT 1")
        self._add_column_if_missing("users", "last_login_at", "TEXT")
        self._add_column_if_missing("users", "last_active_at", "TEXT")
        # 2FA columns. ``totp_secret`` stores the base32 secret encrypted
        # with the AuthStore secret_key (HMAC-SHA256-derived XOR key).
        # ``recovery_codes`` is a JSON array of hashed (HMAC) codes that
        # can each be consumed once.
        self._add_column_if_missing("users", "totp_secret", "TEXT")
        self._add_column_if_missing("users", "totp_enabled", "INTEGER NOT NULL DEFAULT 0")
        self._add_column_if_missing("users", "recovery_codes", "TEXT")
        # Account deletion grace flow: when a user requests deletion we store
        # the HMAC-SHA256 hash of a one-time confirmation token they receive
        # by email. On confirmation we set ``deletion_scheduled_at`` to
        # ``now() + 7 days``. The retention purge sweep deletes the account
        # once that timestamp is in the past. The user can cancel during
        # the grace window which clears both columns.
        self._add_column_if_missing("users", "deletion_token_hash", "TEXT")
        self._add_column_if_missing("users", "deletion_scheduled_at", "TEXT")
        # DSGVO consent capture (#30). When a user signs up via the
        # public form they must tick "I have read the Terms" and "…
        # the Privacy policy". We persist the timestamp of agreement
        # so the operator can later prove informed consent in case of
        # a complaint. NULL on accounts created before consent was
        # required (e.g. the first-account bootstrap admin).
        self._add_column_if_missing("users", "tos_accepted_at", "TEXT")
        self._add_column_if_missing("users", "privacy_accepted_at", "TEXT")
        # Email verification (#31). On public sign-up we mint a single-
        # use token, stash its HMAC, and email a confirm link. When the
        # user clicks it, ``email_verified_at`` is stamped. The bootstrap
        # admin path is auto-verified because the operator owns the
        # mailbox already. Operator-side gate
        # ``DIRECTJOB_REQUIRE_EMAIL_VERIFICATION`` decides whether
        # unverified accounts can sign in.
        self._add_column_if_missing("users", "email_verified_at", "TEXT")
        self._add_column_if_missing("users", "email_verification_token_hash", "TEXT")
        # Onboarding email drip (#37). NULL until the corresponding day-N
        # email is sent. The hourly drip sweep skips users whose column
        # is already populated, making it safe to re-run.
        self._add_column_if_missing("users", "drip_day3_sent_at", "TEXT")
        self._add_column_if_missing("users", "drip_day7_sent_at", "TEXT")
        # Referral program (#46). Each user gets a short, URL-safe
        # ``referral_code`` on first save; ``referred_by`` records the
        # code that brought them in. Reward grant (1 month Pro for
        # both sides) is deferred to when the Pro plan exists
        # (gated by tracker #21).
        self._add_column_if_missing("users", "referral_code", "TEXT")
        self._add_column_if_missing("users", "referred_by", "TEXT")
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                csrf_token TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        self._ensure_admin_exists()
        self.connection.commit()

    def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        columns = {
            row[1] for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_admin_exists(self) -> None:
        admin_count = self.connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1"
        ).fetchone()[0]
        if admin_count:
            return
        first = self.connection.execute(
            "SELECT id FROM users ORDER BY created_at LIMIT 1"
        ).fetchone()
        if first:
            self.connection.execute(
                "UPDATE users SET role = 'admin', active = 1 WHERE id = ?", (first[0],)
            )

    def close(self) -> None:
        # Closes the calling thread's connection only. Other threads'
        # connections are GC'd at thread death. For the typical
        # request-pool topology this is fine — threads outlive the
        # store; in tests there's only one thread.
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def has_users(self) -> bool:
        row = self.connection.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return row is not None

    def list_users(self) -> list[AuthUser]:
        rows = self.connection.execute(
            "SELECT id, email, role, active, created_at, last_login_at, last_active_at FROM users ORDER BY created_at"
        ).fetchall()
        return [self._user_from_row(row) for row in rows]

    def create_user(self, email: str, password: str, role: str = "member") -> AuthUser:
        normalized = _normalize_email(email)
        if not is_valid_email_shape(normalized):
            raise ValueError("invalid_email")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError("password_too_short")
        if role not in {"admin", "member"}:
            raise ValueError("invalid_role")
        user = AuthUser(
            id=f"user_{secrets.token_hex(16)}",
            email=normalized,
            role=role,
            active=True,
            created_at=now_utc(),
        )
        try:
            self.connection.execute(
                "INSERT INTO users(id, email, password_hash, role, active, created_at) VALUES(?, ?, ?, ?, ?, ?)",
                (
                    user.id,
                    user.email,
                    hash_password(password),
                    user.role,
                    1,
                    user.created_at.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("email_already_exists") from error
        self.connection.commit()
        return user

    def bootstrap_admin_from_env(self, email: str | None, password: str | None) -> AuthUser | None:
        if self.has_users() or not email or not password:
            return None
        user = self.create_user(email, password, role="admin")
        # The bootstrap admin owns the mailbox by definition (the env-
        # var values were typed by the operator), so flag the account
        # email-verified directly. Without this the admin can't sign in
        # when DIRECTJOB_REQUIRE_EMAIL_VERIFICATION=true (the env var
        # would otherwise lock out the very account it bootstraps).
        self.mark_email_verified(user.id)
        return user

    def authenticate(self, email: str, password: str) -> AuthUser | None:
        normalized = _normalize_email(email)
        row = self.connection.execute(
            "SELECT id, email, password_hash, role, active, created_at FROM users WHERE email = ?",
            (normalized,),
        ).fetchone()
        if row is None or not row[4] or not verify_password(password, row[2]):
            return None
        login_at = now_utc()
        self.connection.execute(
            "UPDATE users SET last_login_at = ?, last_active_at = ? WHERE id = ?",
            (login_at.isoformat(), login_at.isoformat(), row[0]),
        )
        self.connection.commit()
        return AuthUser(
            id=row[0],
            email=row[1],
            role=row[3],
            active=bool(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            last_login_at=login_at,
            last_active_at=login_at,
        )

    def create_session(self, user: AuthUser) -> AuthSession:
        token = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        created_at = now_utc()
        expires_at = created_at + self.session_ttl
        self.connection.execute(
            """
            INSERT INTO sessions(token_hash, user_id, csrf_token, expires_at, created_at, last_seen_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                _hash_token(self.secret_key, token),
                user.id,
                csrf_token,
                expires_at.isoformat(),
                created_at.isoformat(),
                created_at.isoformat(),
            ),
        )
        self.connection.commit()
        return AuthSession(token=token, user=user, csrf_token=csrf_token, expires_at=expires_at)

    def get_session(self, token: str | None) -> AuthSession | None:
        if not token:
            return None
        token_hash = _hash_token(self.secret_key, token)
        row = self.connection.execute(
            """
            SELECT s.csrf_token, s.expires_at, u.id, u.email, u.role, u.active, u.created_at,
                   u.last_login_at, u.last_active_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND u.active = 1
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row[1])
        if expires_at <= now_utc():
            self.delete_session(token)
            return None
        seen_at = now_utc()
        self.connection.execute(
            "UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?",
            (seen_at.isoformat(), token_hash),
        )
        self.connection.execute(
            "UPDATE users SET last_active_at = ? WHERE id = ?",
            (seen_at.isoformat(), row[2]),
        )
        self.connection.commit()
        return AuthSession(
            token=token,
            user=AuthUser(
                id=row[2],
                email=row[3],
                role=row[4],
                active=bool(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                last_login_at=datetime.fromisoformat(row[7]) if row[7] else None,
                last_active_at=seen_at,
            ),
            csrf_token=row[0],
            expires_at=expires_at,
        )

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        self.connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?", (_hash_token(self.secret_key, token),)
        )
        self.connection.commit()

    def delete_user_sessions(self, user_id: str) -> None:
        self.connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        self.connection.commit()

    def get_user(self, user_id: str) -> AuthUser:
        row = self.connection.execute(
            "SELECT id, email, role, active, created_at, last_login_at, last_active_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return self._user_from_row(row)

    def count_active_admins(self) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1"
            ).fetchone()[0]
        )

    # --- TOTP 2FA --------------------------------------------------------

    def _totp_crypto(self) -> EncryptionAtRest:
        """Lazy-init and cache the AEAD helper used for the TOTP-secret
        column. Same key-derivation chain as the CV-text column (HKDF from
        ``self.secret_key`` unless ``DIRECTJOB_DATA_KEY`` is set), so a
        single rotation of either env var rotates both columns together.
        """

        from .crypto_kit import EncryptionAtRest

        cached = getattr(self, "_totp_crypto_cached", None)
        if cached is None:
            cached = EncryptionAtRest.from_secret_key(self.secret_key)
            self._totp_crypto_cached = cached
        return cached

    def _encrypt_secret(self, secret_b32: str, user_id: str) -> str:
        """AEAD-encrypt the TOTP base32 secret with the user id as AAD.

        AAD binding defeats swap-the-blob attacks: a row written for one
        user cannot be transplanted into another user's row and decrypted.
        """

        aad = user_id.encode("utf-8")
        return self._totp_crypto().encrypt(secret_b32, aad=aad)

    def _decrypt_secret(self, blob: str, user_id: str) -> str:
        """Decrypt the TOTP base32 secret. Transparent across the two
        on-disk formats produced over the project's history:

        * AEAD (current) — ``aead:v1:...`` blobs written by
          :meth:`_encrypt_secret`. Decrypted with AAD bound to user id.
        * Legacy XOR — unauthenticated XOR-with-SHA256-derived-key blobs
          written before the migration. Decrypted via
          :meth:`_decrypt_legacy_totp` for read continuity; callers that
          mutate state should invoke :meth:`_migrate_legacy_totp_if_needed`
          to opportunistically upgrade the column on next write.
        """

        from .crypto_kit import is_aead_blob

        if is_aead_blob(blob):
            aad = user_id.encode("utf-8")
            return self._totp_crypto().decrypt(blob, aad=aad)
        return self._decrypt_legacy_totp(blob)

    def _decrypt_legacy_totp(self, blob: str) -> str:
        """Decrypt a pre-migration XOR-base64 TOTP blob. Kept solely to
        support transparent lazy-migration of existing rows; never used
        for new writes."""

        import base64

        raw = base64.b64decode(blob)
        salt, ciphertext = raw[:8], raw[8:]
        key = hashlib.sha256(self.secret_key.encode("utf-8") + salt).digest()
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(ciphertext))
        return plain.decode("ascii")

    def _migrate_legacy_totp_if_needed(self, user_id: str, blob: str) -> None:
        """If the stored TOTP blob is in the pre-migration XOR-base64
        format, re-encrypt it under AEAD and update the row. Idempotent:
        a no-op when the blob is already in ``aead:v1:`` format.

        Called from the read paths (verify / confirm) so the column
        upgrades on first read after the migration deploys, without
        requiring a separate offline migration step.
        """

        from .crypto_kit import is_aead_blob

        if not blob or is_aead_blob(blob):
            return
        plaintext = self._decrypt_legacy_totp(blob)
        new_blob = self._encrypt_secret(plaintext, user_id)
        self.connection.execute(
            "UPDATE users SET totp_secret = ? WHERE id = ?",
            (new_blob, user_id),
        )
        self.connection.commit()

    def has_totp_enabled(self, user_id: str) -> bool:
        row = self.connection.execute(
            "SELECT totp_enabled FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return bool(row and row[0])

    def start_totp_enrollment(self, user_id: str) -> dict[str, str]:
        """Generate a fresh secret and stash it as pending (totp_enabled=0)
        until the user proves they can read codes from it."""

        user = self.get_user(user_id)
        secret = _b32_secret()
        encrypted = self._encrypt_secret(secret, user_id)
        # Pre-generate 8 single-use recovery codes; only persist after
        # confirmation so a half-finished enrollment doesn't litter rows.
        self.connection.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 0, recovery_codes = NULL WHERE id = ?",
            (encrypted, user_id),
        )
        self.connection.commit()
        return {
            "secret": secret,
            "otpauthUrl": _format_otpauth_url(secret_b32=secret, account=user.email),
        }

    def confirm_totp_enrollment(self, user_id: str, code: str) -> list[str]:
        """Verify the supplied code and, on success, persist 8 recovery codes
        (returning the *plaintext* codes so they can be shown once)."""

        import json

        row = self.connection.execute(
            "SELECT totp_secret FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not row[0]:
            raise ValueError("totp_not_started")
        secret = self._decrypt_secret(row[0], user_id)
        self._migrate_legacy_totp_if_needed(user_id, row[0])
        if not verify_totp(secret, code):
            raise ValueError("invalid_totp_code")
        plaintext_codes = [secrets.token_hex(5) for _ in range(8)]
        hashed = [_hash_token(self.secret_key, c) for c in plaintext_codes]
        self.connection.execute(
            "UPDATE users SET totp_enabled = 1, recovery_codes = ? WHERE id = ?",
            (json.dumps(hashed), user_id),
        )
        self.connection.commit()
        return plaintext_codes

    def verify_user_totp(self, user_id: str, code: str) -> bool:
        row = self.connection.execute(
            "SELECT totp_secret, totp_enabled FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not row[0] or not row[1]:
            return False
        secret = self._decrypt_secret(row[0], user_id)
        self._migrate_legacy_totp_if_needed(user_id, row[0])
        return verify_totp(secret, code)

    def consume_recovery_code(self, user_id: str, code: str) -> bool:
        import json

        row = self.connection.execute(
            "SELECT recovery_codes FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not row[0]:
            return False
        try:
            codes = json.loads(row[0]) or []
        except json.JSONDecodeError:
            return False
        target = _hash_token(self.secret_key, (code or "").strip())
        if target not in codes:
            return False
        remaining = [c for c in codes if c != target]
        self.connection.execute(
            "UPDATE users SET recovery_codes = ? WHERE id = ?",
            (json.dumps(remaining), user_id),
        )
        self.connection.commit()
        return True

    # --- Account deletion grace flow -----------------------------------

    def start_account_deletion(self, user_id: str) -> str:
        """Mint a one-time confirmation token, store its hash, return the
        raw token for emailing. Calling twice replaces the previous token."""

        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(self.secret_key, token)
        self.connection.execute(
            "UPDATE users SET deletion_token_hash = ?, deletion_scheduled_at = NULL WHERE id = ?",
            (token_hash, user_id),
        )
        self.connection.commit()
        return token

    def confirm_account_deletion(self, token: str, *, grace_days: int = 7) -> tuple[str, datetime]:
        """Verify the confirmation token and schedule the hard delete.
        Returns ``(user_id, scheduled_at)``. Raises ``ValueError`` with
        ``"invalid_or_expired_token"`` when the token doesn't match."""

        token_hash = _hash_token(self.secret_key, (token or "").strip())
        row = self.connection.execute(
            "SELECT id FROM users WHERE deletion_token_hash = ? AND active = 1",
            (token_hash,),
        ).fetchone()
        if not row:
            raise ValueError("invalid_or_expired_token")
        user_id = str(row[0])
        scheduled_at = now_utc() + timedelta(days=grace_days)
        # Burn the token on confirmation; only one redemption is allowed.
        self.connection.execute(
            "UPDATE users SET deletion_token_hash = NULL, deletion_scheduled_at = ? WHERE id = ?",
            (scheduled_at.isoformat(), user_id),
        )
        self.connection.commit()
        return user_id, scheduled_at

    # --- Email verification --------------------------------------------

    def start_email_verification(self, user_id: str) -> str:
        """Mint a single-use email-verification token. Calling twice
        replaces the previous token (resend support)."""

        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(self.secret_key, token)
        self.connection.execute(
            "UPDATE users SET email_verification_token_hash = ? WHERE id = ?",
            (token_hash, user_id),
        )
        self.connection.commit()
        return token

    def confirm_email_verification(self, token: str) -> str:
        """Verify the token, stamp ``email_verified_at = now()``, burn
        the token. Returns the verified user_id. Raises ``ValueError``
        with ``invalid_or_expired_token`` if the token doesn't match."""

        token_hash = _hash_token(self.secret_key, (token or "").strip())
        row = self.connection.execute(
            "SELECT id FROM users WHERE email_verification_token_hash = ? AND active = 1",
            (token_hash,),
        ).fetchone()
        if not row:
            raise ValueError("invalid_or_expired_token")
        user_id = str(row[0])
        self.connection.execute(
            "UPDATE users SET email_verified_at = ?, email_verification_token_hash = NULL WHERE id = ?",
            (now_utc().isoformat(), user_id),
        )
        self.connection.commit()
        return user_id

    # --- Referral program ----------------------------------------------

    def ensure_referral_code(self, user_id: str) -> str:
        """Return the user's referral code, minting one on first call.
        Codes are 10 URL-safe characters, collision-checked against the
        existing index. Idempotent: subsequent calls return the same
        code unless the row has been wiped."""

        row = self.connection.execute(
            "SELECT referral_code FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row and row[0]:
            return str(row[0])
        # Mint up to 5 candidates before giving up — at 64**10 slot
        # density a collision is astronomically unlikely.
        for _ in range(5):
            candidate = secrets.token_urlsafe(8)[:10]
            existing = self.connection.execute(
                "SELECT 1 FROM users WHERE referral_code = ?",
                (candidate,),
            ).fetchone()
            if not existing:
                self.connection.execute(
                    "UPDATE users SET referral_code = ? WHERE id = ?",
                    (candidate, user_id),
                )
                self.connection.commit()
                return candidate
        raise RuntimeError("referral_code_collision")

    def find_user_by_referral_code(self, code: str) -> AuthUser | None:
        cleaned = (code or "").strip()
        if not cleaned:
            return None
        row = self.connection.execute(
            "SELECT id, email, role, active, created_at, last_login_at, last_active_at "
            "FROM users WHERE referral_code = ?",
            (cleaned,),
        ).fetchone()
        return self._user_from_row(row) if row else None

    def record_referral(self, user_id: str, referrer_code: str) -> None:
        """Stamp ``users.referred_by`` for a new sign-up. Validates the
        referrer code refers to an active user and isn't the user's
        own code (self-referral attempt). No-op when validation fails
        — sign-up should not be blocked by a bad referral code."""

        if not referrer_code:
            return
        referrer = self.find_user_by_referral_code(referrer_code)
        if referrer is None or not referrer.active or referrer.id == user_id:
            return
        self.connection.execute(
            "UPDATE users SET referred_by = ? WHERE id = ?",
            (referrer_code, user_id),
        )
        self.connection.commit()

    def count_referrals(self, user_id: str) -> int:
        row = self.connection.execute(
            "SELECT referral_code FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row or not row[0]:
            return 0
        count_row = self.connection.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ? AND active = 1",
            (row[0],),
        ).fetchone()
        return int(count_row[0]) if count_row else 0

    def users_due_for_drip(
        self,
        *,
        column: str,
        min_age_days: int,
        max_age_days: int | None = None,
        now: datetime | None = None,
    ) -> list[AuthUser]:
        """Return users whose ``created_at`` falls in the window
        ``[now - max_age_days, now - min_age_days]`` AND whose ``column``
        is still NULL. Used by the onboarding-drip cron to find which
        accounts are due for the day-3 / day-7 email."""

        if column not in {"drip_day3_sent_at", "drip_day7_sent_at"}:
            raise ValueError("invalid_drip_column")
        threshold_min = (now or now_utc()) - timedelta(days=min_age_days)
        threshold_max = (
            (now or now_utc()) - timedelta(days=max_age_days) if max_age_days is not None else None
        )
        params: list[Any] = [threshold_min.isoformat()]
        sql = (
            f"SELECT id, email, role, active, created_at, last_login_at, last_active_at "
            f"FROM users WHERE {column} IS NULL AND active = 1 AND created_at <= ?"
        )
        if threshold_max is not None:
            sql += " AND created_at >= ?"
            params.append(threshold_max.isoformat())
        rows = self.connection.execute(sql, params).fetchall()
        return [self._user_from_row(row) for row in rows]

    def mark_drip_sent(self, user_id: str, column: str) -> None:
        if column not in {"drip_day3_sent_at", "drip_day7_sent_at"}:
            raise ValueError("invalid_drip_column")
        self.connection.execute(
            f"UPDATE users SET {column} = ? WHERE id = ?",
            (now_utc().isoformat(), user_id),
        )
        self.connection.commit()

    def is_email_verified(self, user_id: str) -> bool:
        row = self.connection.execute(
            "SELECT email_verified_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return bool(row and row[0])

    def mark_email_verified(self, user_id: str) -> None:
        """Bootstrap-only short-circuit: stamp the verified-at timestamp
        without minting a token. Used for the first-account admin who
        owns the mailbox already."""

        self.connection.execute(
            "UPDATE users SET email_verified_at = ?, email_verification_token_hash = NULL WHERE id = ?",
            (now_utc().isoformat(), user_id),
        )
        self.connection.commit()

    def record_consent(self, user_id: str, *, tos: bool, privacy: bool) -> None:
        """Stamp the consent columns. Either flag may already be set
        from a previous sign-up — we overwrite anyway because the user
        re-confirmed by submitting the form again."""

        now = now_utc().isoformat()
        if tos:
            self.connection.execute(
                "UPDATE users SET tos_accepted_at = ? WHERE id = ?",
                (now, user_id),
            )
        if privacy:
            self.connection.execute(
                "UPDATE users SET privacy_accepted_at = ? WHERE id = ?",
                (now, user_id),
            )
        self.connection.commit()

    def get_consent(self, user_id: str) -> dict[str, str | None]:
        row = self.connection.execute(
            "SELECT tos_accepted_at, privacy_accepted_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"tosAcceptedAt": None, "privacyAcceptedAt": None}
        return {"tosAcceptedAt": row[0], "privacyAcceptedAt": row[1]}

    def cancel_account_deletion(self, user_id: str) -> bool:
        """Clear deletion state for ``user_id``. Returns True when an
        active request was cleared, False when nothing was pending."""

        row = self.connection.execute(
            "SELECT deletion_token_hash, deletion_scheduled_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row or (not row[0] and not row[1]):
            return False
        self.connection.execute(
            "UPDATE users SET deletion_token_hash = NULL, deletion_scheduled_at = NULL WHERE id = ?",
            (user_id,),
        )
        self.connection.commit()
        return True

    def get_deletion_state(self, user_id: str) -> dict[str, Any]:
        """Return the deletion state for the account. Shape:
        ``{"pending": bool, "scheduledAt": iso|None}``. ``pending`` is
        True when either an unconfirmed request or a scheduled delete is
        in flight."""

        row = self.connection.execute(
            "SELECT deletion_token_hash, deletion_scheduled_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"pending": False, "scheduledAt": None}
        token_hash, scheduled_at = row[0], row[1]
        return {
            "pending": bool(token_hash) or bool(scheduled_at),
            "scheduledAt": scheduled_at,
        }

    def due_account_deletions(self, *, now: datetime | None = None) -> list[str]:
        """Return user_ids whose ``deletion_scheduled_at`` is in the past.
        Caller is responsible for performing the cascade delete."""

        threshold = (now or now_utc()).isoformat()
        rows = self.connection.execute(
            "SELECT id FROM users WHERE deletion_scheduled_at IS NOT NULL AND deletion_scheduled_at <= ?",
            (threshold,),
        ).fetchall()
        return [str(r[0]) for r in rows]

    def issue_2fa_challenge(self, user_id: str, *, ttl_seconds: int = 300) -> str:
        """Mint a short-lived bearer token the client must send back with
        the 6-digit code. The token is stored hashed; the raw value is
        only ever in the response body."""

        token = secrets.token_urlsafe(32)
        expires_at = now_utc() + timedelta(seconds=ttl_seconds)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_2fa(
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        # Garbage-collect expired rows on every write (cheap, single row scan).
        self.connection.execute(
            "DELETE FROM pending_2fa WHERE expires_at < ?", (now_utc().isoformat(),)
        )
        self.connection.execute(
            "INSERT INTO pending_2fa(token_hash, user_id, expires_at) VALUES(?, ?, ?)",
            (_hash_token(self.secret_key, token), user_id, expires_at.isoformat()),
        )
        self.connection.commit()
        return token

    def consume_2fa_challenge(self, token: str) -> str | None:
        """Return the user_id bound to ``token`` and delete the row.
        Returns None if the challenge expired or doesn't exist."""

        token_hash = _hash_token(self.secret_key, token)
        row = self.connection.execute(
            "SELECT user_id, expires_at FROM pending_2fa WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        user_id, expires_at = row
        self.connection.execute("DELETE FROM pending_2fa WHERE token_hash = ?", (token_hash,))
        self.connection.commit()
        if datetime.fromisoformat(expires_at) <= now_utc():
            return None
        return user_id

    def disable_totp(self, user_id: str, password: str) -> None:
        """Turn off 2FA. Requires password verification to prevent a
        stolen session from silently disabling 2FA."""

        row = self.connection.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not verify_password(password, row[0]):
            raise ValueError("invalid_password")
        self.connection.execute(
            "UPDATE users SET totp_enabled = 0, totp_secret = NULL, recovery_codes = NULL WHERE id = ?",
            (user_id,),
        )
        self.connection.commit()

    def update_user(
        self,
        user_id: str,
        *,
        role: str | None = None,
        active: bool | None = None,
        password: str | None = None,
    ) -> AuthUser:
        user = self.get_user(user_id)
        new_role = user.role if role is None else role
        new_active = user.active if active is None else active
        if new_role not in {"admin", "member"}:
            raise ValueError("invalid_role")
        if password is not None and len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError("password_too_short")
        if user.role == "admin" and user.active and (new_role != "admin" or not new_active):
            if self.count_active_admins() <= 1:
                raise ValueError("last_admin_required")
        if password is None:
            self.connection.execute(
                "UPDATE users SET role = ?, active = ? WHERE id = ?",
                (new_role, 1 if new_active else 0, user_id),
            )
        else:
            self.connection.execute(
                "UPDATE users SET role = ?, active = ?, password_hash = ? WHERE id = ?",
                (new_role, 1 if new_active else 0, hash_password(password), user_id),
            )
        self.connection.commit()
        if password is not None or not new_active:
            self.delete_user_sessions(user_id)
        return self.get_user(user_id)

    def _user_from_row(self, row: sqlite3.Row | tuple[object, ...]) -> AuthUser:
        last_login = datetime.fromisoformat(str(row[5])) if len(row) > 5 and row[5] else None
        last_active = datetime.fromisoformat(str(row[6])) if len(row) > 6 and row[6] else None
        return AuthUser(
            id=str(row[0]),
            email=str(row[1]),
            role=str(row[2]),
            active=bool(row[3]),
            created_at=datetime.fromisoformat(str(row[4])),
            last_login_at=last_login,
            last_active_at=last_active,
        )
