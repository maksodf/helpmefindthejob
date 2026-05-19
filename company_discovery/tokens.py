# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Single-use, time-limited tokens for invitations and password resets.

Tokens are stored as ``HMAC-SHA256(secret_key, raw_token)`` so leaking the
DB does not leak usable tokens. Raw tokens are returned only at creation
time and then destroyed.

Two token kinds share one table:

- ``invitation``: created by an admin to onboard a new tester. Carries
  the proposed email and role. Consumed when the invitee picks a
  password.
- ``password_reset``: created when a user requests a reset. Consumed
  when the user POSTs a new password.

Tokens are single-use. Calling ``consume_token`` twice returns ``None``
the second time. Expiry is enforced on read.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(secret_key: str, token: str) -> str:
    return hmac.new(secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class Token:
    id: str
    kind: str
    email: str
    role: str
    created_by: str | None
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None


@dataclass(frozen=True)
class IssuedToken:
    raw_token: str
    record: Token


class TokenStore:
    """Stores invitations and password reset tokens in a sqlite DB."""

    def __init__(self, path: str | Path, secret_key: str) -> None:
        if len(secret_key) < 32:
            raise ValueError("secret_key_too_short")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_key = secret_key
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                created_by TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT
            )
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_tokens_kind ON tokens(kind)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_tokens_email ON tokens(email)")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def issue(
        self,
        *,
        kind: str,
        email: str,
        role: str = "member",
        created_by: str | None = None,
        ttl: timedelta = timedelta(hours=48),
    ) -> IssuedToken:
        if kind not in {"invitation", "password_reset"}:
            raise ValueError("invalid_token_kind")
        if not email or "@" not in email:
            raise ValueError("invalid_email")
        if role not in {"admin", "member"}:
            raise ValueError("invalid_role")
        token_id = f"tok_{secrets.token_hex(12)}"
        raw = secrets.token_urlsafe(32)
        token_hash = _hash_token(self.secret_key, raw)
        created_at = _now()
        expires_at = created_at + ttl
        self.connection.execute(
            """
            INSERT INTO tokens(id, kind, token_hash, email, role, created_by, created_at, expires_at, consumed_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                token_id,
                kind,
                token_hash,
                email.strip().casefold(),
                role,
                created_by,
                created_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        self.connection.commit()
        record = Token(
            id=token_id,
            kind=kind,
            email=email.strip().casefold(),
            role=role,
            created_by=created_by,
            created_at=created_at,
            expires_at=expires_at,
            consumed_at=None,
        )
        return IssuedToken(raw_token=raw, record=record)

    def lookup(self, kind: str, raw_token: str) -> Token | None:
        if not raw_token:
            return None
        token_hash = _hash_token(self.secret_key, raw_token)
        row = self.connection.execute(
            """
            SELECT id, kind, email, role, created_by, created_at, expires_at, consumed_at
            FROM tokens WHERE kind = ? AND token_hash = ?
            """,
            (kind, token_hash),
        ).fetchone()
        if row is None:
            return None
        record = Token(
            id=row[0],
            kind=row[1],
            email=row[2],
            role=row[3],
            created_by=row[4],
            created_at=datetime.fromisoformat(row[5]),
            expires_at=datetime.fromisoformat(row[6]),
            consumed_at=datetime.fromisoformat(row[7]) if row[7] else None,
        )
        if record.consumed_at is not None:
            return None
        if record.expires_at <= _now():
            return None
        return record

    def consume(self, kind: str, raw_token: str) -> Token | None:
        record = self.lookup(kind, raw_token)
        if record is None:
            return None
        consumed_at = _now().isoformat()
        cursor = self.connection.execute(
            """
            UPDATE tokens SET consumed_at = ?
            WHERE id = ? AND consumed_at IS NULL
            """,
            (consumed_at, record.id),
        )
        self.connection.commit()
        if cursor.rowcount != 1:
            return None
        return record

    def revoke_all_for(self, email: str, kind: str | None = None) -> int:
        consumed_at = _now().isoformat()
        params: tuple[object, ...]
        if kind is None:
            cursor = self.connection.execute(
                "UPDATE tokens SET consumed_at = ? WHERE email = ? AND consumed_at IS NULL",
                (consumed_at, email.strip().casefold()),
            )
        else:
            cursor = self.connection.execute(
                "UPDATE tokens SET consumed_at = ? WHERE email = ? AND kind = ? AND consumed_at IS NULL",
                (consumed_at, email.strip().casefold(), kind),
            )
        self.connection.commit()
        return cursor.rowcount

    def list_active(self, kind: str) -> list[Token]:
        rows = self.connection.execute(
            """
            SELECT id, kind, email, role, created_by, created_at, expires_at, consumed_at
            FROM tokens
            WHERE kind = ? AND consumed_at IS NULL AND expires_at > ?
            ORDER BY created_at DESC
            """,
            (kind, _now().isoformat()),
        ).fetchall()
        return [
            Token(
                id=row[0],
                kind=row[1],
                email=row[2],
                role=row[3],
                created_by=row[4],
                created_at=datetime.fromisoformat(row[5]),
                expires_at=datetime.fromisoformat(row[6]),
                consumed_at=None,
            )
            for row in rows
        ]
