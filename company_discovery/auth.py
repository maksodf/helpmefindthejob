from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


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


def _totp_at(secret_b32: str, *, when: datetime, period: int = TOTP_PERIOD_SECONDS, digits: int = TOTP_DIGITS) -> str:
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

        candidate = _totp_at(secret_b32, when=when + timedelta(seconds=offset * TOTP_PERIOD_SECONDS))
        if hmac.compare_digest(candidate, code):
            return True
    return False


def _format_otpauth_url(*, secret_b32: str, account: str, issuer: str = "DirectJob Scout") -> str:
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
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

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
        columns = {row[1] for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_admin_exists(self) -> None:
        admin_count = self.connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1"
        ).fetchone()[0]
        if admin_count:
            return
        first = self.connection.execute("SELECT id FROM users ORDER BY created_at LIMIT 1").fetchone()
        if first:
            self.connection.execute("UPDATE users SET role = 'admin', active = 1 WHERE id = ?", (first[0],))

    def close(self) -> None:
        self.connection.close()

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
        if not normalized or "@" not in normalized:
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
                (user.id, user.email, hash_password(password), user.role, 1, user.created_at.isoformat()),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("email_already_exists") from error
        self.connection.commit()
        return user

    def bootstrap_admin_from_env(self, email: str | None, password: str | None) -> AuthUser | None:
        if self.has_users() or not email or not password:
            return None
        return self.create_user(email, password, role="admin")

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
        self.connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(self.secret_key, token),))
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

    def _encrypt_secret(self, secret_b32: str) -> str:
        """Symmetric envelope: derive a key from secret_key + a per-user
        salt, XOR the base32 secret. Reversible only with secret_key."""

        import base64

        salt = secrets.token_bytes(8)
        key = hashlib.sha256(self.secret_key.encode("utf-8") + salt).digest()
        data = secret_b32.encode("ascii")
        ciphertext = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return base64.b64encode(salt + ciphertext).decode("ascii")

    def _decrypt_secret(self, blob: str) -> str:
        import base64

        raw = base64.b64decode(blob)
        salt, ciphertext = raw[:8], raw[8:]
        key = hashlib.sha256(self.secret_key.encode("utf-8") + salt).digest()
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(ciphertext))
        return plain.decode("ascii")

    def has_totp_enabled(self, user_id: str) -> bool:
        row = self.connection.execute(
            "SELECT totp_enabled FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return bool(row and row[0])

    def start_totp_enrollment(self, user_id: str) -> dict[str, str]:
        """Generate a fresh secret and stash it as pending (totp_enabled=0)
        until the user proves they can read codes from it."""

        import json

        user = self.get_user(user_id)
        secret = _b32_secret()
        encrypted = self._encrypt_secret(secret)
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
        secret = self._decrypt_secret(row[0])
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
        return verify_totp(self._decrypt_secret(row[0]), code)

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
