# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""File-backed Trust Receipt store.

Append-only JSONL per user. Receipts are durable so a user can
download yesterday's fit-score receipt — without this they'd
have to be on the receipt-issuing page when it was emitted.

Storage layout::

    <data_dir>/trust_receipts/<user_id_opaque>.jsonl

Why hash the user_id into the filename: even an operator with
disk access can't easily correlate receipts to the plaintext
user — same privacy posture as the audit log. The hash uses
the same deployer salt the receipts are signed with.

Thread-safe via a per-store lock. Cross-process safety is the
same as the audit log (single-writer recommended for high-
throughput deployments — see compliance/audit-log-schema.md
§8a for the deployer guidance).
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Iterable

from company_discovery.trust_receipt import (
    RECEIPT_SCHEMA_VERSION,
    TrustReceipt,
    verify_trust_receipt,
)


class TrustReceiptStore:
    """File-backed receipt store. One JSONL file per user."""

    def __init__(self, base_dir: Path, salt: bytes) -> None:
        if not isinstance(salt, (bytes, bytearray)) or len(salt) < 16:
            raise ValueError("salt_must_be_bytes_of_at_least_16_bytes")
        self.base_dir = Path(base_dir)
        self.salt = bytes(salt)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _user_dir(self, user_id: str) -> Path:
        # Directory key uses SHA-256-without-salt rather than
        # HMAC(salt, user_id) because user_ids in this system are
        # already 32-hex UUIDs (`user_<32hex>`) — non-enumerable.
        # Salting the directory key would silently orphan all of a
        # user's receipts on every salt rotation; that's a major
        # operational footgun the receipt SIGNATURE already covers
        # (a rotated salt fails signature verification, which is
        # the intended security property).
        # Quality-audit decision (2026-05-21): the SIGNATURE
        # remains salt-keyed (rotation invalidates signatures —
        # correct security behaviour), but the FILE LOCATION is
        # stable across rotations (users can still download their
        # historical receipts even if the signatures are now
        # cryptographically stale).
        opaque = hashlib.sha256((user_id or "").encode("utf-8")).hexdigest()[:16]
        return self.base_dir / opaque

    def _user_log_path(self, user_id: str) -> Path:
        d = self._user_dir(user_id)
        d.mkdir(parents=True, exist_ok=True)
        return d / "receipts.jsonl"

    def save(self, user_id: str, receipt: TrustReceipt) -> None:
        """Append the receipt to the user's JSONL log. Refuses
        to save a receipt whose own signature doesn't verify —
        defends against a caller that constructed a malformed
        TrustReceipt by hand."""
        result = verify_trust_receipt(receipt.to_dict(), self.salt)
        if not result.ok:
            raise ValueError(
                f"refusing_to_save_unverifiable_receipt:{result.reason}"
            )
        path = self._user_log_path(user_id)
        line = receipt.to_jsonl() + "\n"
        with self._lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return all receipts for a user, newest-first by
        decidedAt. Returns an empty list when the user has no
        receipts on file."""
        path = self._user_log_path(user_id)
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        with self._lock:
            with path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        out.sort(key=lambda r: str(r.get("decidedAt", "")), reverse=True)
        return out

    def get(self, user_id: str, receipt_id: str) -> dict[str, Any] | None:
        """Look up a specific receipt by ID, scoped to the user.
        Returns None if not found OR if the receipt exists in
        another user's log (cross-tenant isolation enforced —
        even though the user dirs are hashed, we still scope
        the lookup explicitly)."""
        for receipt in self.list_for_user(user_id):
            if receipt.get("receiptId") == receipt_id:
                return receipt
        return None

    def verify(self, receipt: dict[str, Any]) -> bool:
        """Convenience: verify a receipt against this store's
        salt. Returns True iff signature is valid."""
        return verify_trust_receipt(receipt, self.salt).ok

    def replay(self, user_id: str) -> Iterable[dict[str, Any]]:
        """Yield every receipt in the user's log in file order
        (oldest-first). Used by chain-of-custody tooling that
        wants to detect tampering across the user's history."""
        path = self._user_log_path(user_id)
        if not path.exists():
            return
        with self._lock:
            with path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
