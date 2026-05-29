# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Tamper-evident anchoring of the audit chain to an external transparency log.

The audit log (``audit_log.py``) is an HMAC hash-chain: each record's
``chain_hmac`` commits to every record before it, so the head HMAC is a
cryptographic commitment to the entire history. ``verify_chain`` proves the
chain is internally intact, but a holder of the salt could in principle rewrite
the whole chain consistently. **Anchoring** closes that gap: it publishes a
salt-free digest of the ordered records to an external, append-only
transparency log (Sigstore Rekor) at a point in time. Afterwards, anyone — with
no secret — can recompute the digest from the logs and confirm it matches what
was anchored; any retroactive edit changes the digest and is detected.

This module is deliberately decoupled from ``audit_log.py``: it *composes* with
``verify_chain`` rather than modifying it, so the strict-checked core chain
verifier keeps its exact contract. The offline half (compute + verify a digest,
detect tampering) runs anywhere with no network. The external half (submitting
the digest to Rekor / an RFC-3161 TSA) is an operator/network step; this module
produces the exact bytes to submit but never fakes an inclusion proof.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from company_discovery.audit_log import ChainVerificationResult, verify_chain

#: Bumped if the anchor record shape changes.
ANCHOR_VERSION = "v1"


# ---------------------------------------------------------------------------
# Reading the chain
# ---------------------------------------------------------------------------


def _ordered_v2_records(log_paths: list[Path]) -> list[dict[str, Any]]:
    """Return every valid v2 record across the log files, sorted by
    ``sequence_no``. Mirrors ``verify_chain``'s acceptance rules (v2 only,
    integer sequence_no) so the anchored digest covers exactly the records the
    chain verifier checks. Malformed / non-v2 lines are skipped — a tampered
    line that adds one is caught by ``verify_chain`` in the combined check."""
    records: list[tuple[int, dict[str, Any]]] = []
    for path in log_paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("schema_version") != "v2":
                    continue
                seq = obj.get("sequence_no")
                if not isinstance(seq, int):
                    continue
                records.append((seq, obj))
    records.sort(key=lambda pair: pair[0])
    return [obj for _seq, obj in records]


def compute_content_digest(records: list[dict[str, Any]]) -> str:
    """SHA-256 over the canonical JSON of the ordered records.

    Salt-free and deterministic (sorted keys, compact separators), so any third
    party can recompute it from the log files alone. This is the value anchored
    to the transparency log.
    """
    canonical = "\n".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The anchor record
# ---------------------------------------------------------------------------


@dataclass
class AuditAnchor:
    """A point-in-time commitment to the audit chain. ``content_digest`` is the
    externally-anchored, salt-free value; the other fields are cross-reference
    metadata. ``created_at`` is supplied by the caller (this module performs no
    wall-clock reads, so anchoring is deterministic + testable)."""

    anchor_version: str
    record_count: int
    last_sequence_no: int
    head_chain_hmac: str
    content_digest: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchorVersion": self.anchor_version,
            "recordCount": self.record_count,
            "lastSequenceNo": self.last_sequence_no,
            "headChainHmac": self.head_chain_hmac,
            "contentDigest": self.content_digest,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AuditAnchor:
        return cls(
            anchor_version=str(raw["anchorVersion"]),
            record_count=int(raw["recordCount"]),
            last_sequence_no=int(raw["lastSequenceNo"]),
            head_chain_hmac=str(raw["headChainHmac"]),
            content_digest=str(raw["contentDigest"]),
            created_at=str(raw["createdAt"]),
        )


def compute_anchor(log_paths: list[Path], *, created_at: str) -> AuditAnchor:
    """Build an :class:`AuditAnchor` over the current state of the chain."""
    records = _ordered_v2_records(log_paths)
    last = records[-1] if records else {}
    return AuditAnchor(
        anchor_version=ANCHOR_VERSION,
        record_count=len(records),
        last_sequence_no=int(last.get("sequence_no", 0)),
        head_chain_hmac=str(last.get("chain_hmac", "")),
        content_digest=compute_content_digest(records),
        created_at=created_at,
    )


def load_anchor(path: Path) -> AuditAnchor:
    return AuditAnchor.from_dict(json.loads(path.read_text(encoding="utf-8")))


def write_anchor(path: Path, anchor: AuditAnchor) -> None:
    path.write_text(
        json.dumps(anchor.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@dataclass
class AnchorVerificationResult:
    ok: bool
    reason: str | None = None
    expected_digest: str | None = None
    actual_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "expectedDigest": self.expected_digest,
            "actualDigest": self.actual_digest,
        }


def verify_anchor(log_paths: list[Path], anchor: AuditAnchor) -> AnchorVerificationResult:
    """Recompute the content digest from the current logs and confirm it still
    matches the anchored value. Any record edit / insertion / deletion changes
    the digest (or the record count / head HMAC) and is reported here."""
    records = _ordered_v2_records(log_paths)
    actual = compute_content_digest(records)
    if actual != anchor.content_digest:
        return AnchorVerificationResult(
            ok=False,
            reason="content_digest_mismatch",
            expected_digest=anchor.content_digest,
            actual_digest=actual,
        )
    if len(records) != anchor.record_count:
        return AnchorVerificationResult(
            ok=False,
            reason=f"record_count_mismatch:expected={anchor.record_count},actual={len(records)}",
            expected_digest=anchor.content_digest,
            actual_digest=actual,
        )
    head = str(records[-1].get("chain_hmac", "")) if records else ""
    if head != anchor.head_chain_hmac:
        return AnchorVerificationResult(
            ok=False,
            reason="head_chain_hmac_mismatch",
            expected_digest=anchor.content_digest,
            actual_digest=actual,
        )
    return AnchorVerificationResult(ok=True, expected_digest=anchor.content_digest, actual_digest=actual)


@dataclass
class AnchoredChainResult:
    """Combined result: the chain is internally intact AND still matches its
    external anchor. This is the ``verify_chain(verify_anchors=True)`` capability
    the trust story needs, expressed by composition so the strict-checked
    ``verify_chain`` keeps its exact signature."""

    chain: ChainVerificationResult
    anchor: AnchorVerificationResult

    @property
    def ok(self) -> bool:
        return self.chain.ok and self.anchor.ok

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "chain": self.chain.to_dict(), "anchor": self.anchor.to_dict()}


def verify_chain_and_anchor(
    log_paths: list[Path], salt: bytes, anchor: AuditAnchor
) -> AnchoredChainResult:
    """Verify the HMAC chain (``verify_chain``) and the external anchor together."""
    return AnchoredChainResult(
        chain=verify_chain(log_paths, salt),
        anchor=verify_anchor(log_paths, anchor),
    )


# ---------------------------------------------------------------------------
# External transparency log (operator / network step)
# ---------------------------------------------------------------------------


def rekor_hashedrekord_digest(anchor: AuditAnchor) -> str:
    """The ``sha256:<hex>`` digest an operator submits to Sigstore Rekor (as a
    ``hashedrekord`` entry) or to an RFC-3161 timestamping authority. Building it
    here keeps the submission reproducible; the actual submission is an
    operator/network step (this module never fabricates an inclusion proof).
    """
    return f"sha256:{anchor.content_digest}"
