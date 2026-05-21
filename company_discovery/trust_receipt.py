# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Trust Receipt — user-verifiable proof of an AI-decision (Invariant 2).

A Trust Receipt is a signed JSON object the user can download
after every consequential AI decision (fit score, friction-class
assignment, cover-letter draft, CV tailoring, mesh referral).
It carries enough fields that the user — or a regulator — can
later prove:

- which AI provider produced the decision
- which prompt template was used (by stable hash)
- what the response was (by stable hash)
- when the decision was emitted (ISO timestamp)
- which audit-log entry recorded it (sequence_no + chain HMAC)
- the verifying public key reference (DID:web identifier)

The receipt is signed using the same deployer salt that keys
the audit-log HMAC chain. Verification is done by re-computing
the HMAC over the receipt body and comparing against the
``signature`` field — same trust model as the audit log
(symmetric, salt-keyed). A future v2 of this schema will
upgrade to asymmetric (Ed25519) signing so the user can verify
without trusting the deployer; v1 establishes the data shape so
downstream tooling can already consume it.

Why this matters for the NLnet civic-commons grant: it gives
the user **mathematical proof** of what the system did on
their behalf, separate from any UI screenshot. Combined with
the audit-log chain HMAC + verify_chain, the user holds a
verifiable evidence packet they can present to a Beratungs-
stelle, a court, or a regulator — without trusting our infra.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


RECEIPT_SCHEMA_VERSION = "v1"


# The known decision types Trust Receipts cover. Adding a new
# type means adding a new constant here and a test in the
# corresponding test suite — the receipt builder rejects
# unknown types at construction time.
DECISION_FIT_SCORE = "fit_score"
DECISION_FRICTION_CLASS = "friction_class"
DECISION_COVER_LETTER = "cover_letter"
DECISION_TAILOR_CV = "tailor_cv"
DECISION_CONSULT = "consult"
DECISION_MESH_REFERRAL = "mesh_referral"
DECISION_MOTIVATION_LETTER = "motivation_letter"
DECISION_CV_BUILDER_FORMAT = "cv_builder_format"
DECISION_JOB_DECISION_BRIEF = "job_decision_brief"

KNOWN_DECISIONS: tuple[str, ...] = (
    DECISION_FIT_SCORE,
    DECISION_FRICTION_CLASS,
    DECISION_COVER_LETTER,
    DECISION_TAILOR_CV,
    DECISION_CONSULT,
    DECISION_MESH_REFERRAL,
    DECISION_MOTIVATION_LETTER,
    DECISION_CV_BUILDER_FORMAT,
    DECISION_JOB_DECISION_BRIEF,
)


@dataclass(frozen=True)
class TrustReceipt:
    """Frozen container for a signed Trust Receipt. Use
    :func:`build_trust_receipt` to construct, never the
    dataclass directly — the builder enforces the
    decision-type allowlist + computes the signature."""

    receipt_id: str
    schema_version: str
    decision_type: str
    decided_at: str
    user_id_opaque: str
    ai_provider: str
    prompt_template_id: str
    prompt_hash: str
    response_hash: str
    audit_log_sequence_no: int | None
    audit_log_chain_hmac: str | None
    issuer_did: str
    signature: str
    signature_algorithm: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receiptId": self.receipt_id,
            "schemaVersion": self.schema_version,
            "decisionType": self.decision_type,
            "decidedAt": self.decided_at,
            "userIdOpaque": self.user_id_opaque,
            "aiProvider": self.ai_provider,
            "promptTemplateId": self.prompt_template_id,
            "promptHash": self.prompt_hash,
            "responseHash": self.response_hash,
            "auditLogSequenceNo": self.audit_log_sequence_no,
            "auditLogChainHmac": self.audit_log_chain_hmac,
            "issuerDid": self.issuer_did,
            "signature": self.signature,
            "signatureAlgorithm": self.signature_algorithm,
            "metadata": dict(self.metadata),
        }

    def to_jsonl(self) -> str:
        """Single-line JSON for archival storage (mirrors audit
        log line format)."""
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)


def _hash_user_id(user_id: str, salt: bytes) -> str:
    """HMAC-SHA256 16-hex-char opaque hash of the user id, same
    shape as the audit log's hash_id."""
    digest = hmac.new(salt, (user_id or "").encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:16]


def _short_content_hash(content: str) -> str:
    """First 16 hex chars of SHA-256 — used for prompt + response
    fingerprints. Long enough to be collision-resistant for the
    deployer's traffic; short enough to fit comfortably in a
    receipt the user might print on one A4 page."""
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()[:16]


def _canonical_signable(payload: dict[str, Any]) -> bytes:
    """Canonical byte form of the signable body. The signature
    field itself is excluded (chicken-and-egg). Sort keys,
    no whitespace, ensure_ascii so the byte stream is stable
    across platforms / Python versions."""
    return json.dumps(
        {k: v for k, v in payload.items() if k != "signature"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sign(payload_dict: dict[str, Any], salt: bytes) -> str:
    """HMAC-SHA256 hex over the canonical signable body."""
    return hmac.new(salt, _canonical_signable(payload_dict), hashlib.sha256).hexdigest()


def build_trust_receipt(
    *,
    decision_type: str,
    user_id: str,
    ai_provider: str,
    prompt_template_id: str,
    prompt_text: str,
    response_text: str,
    salt: bytes,
    issuer_did: str = "did:web:helpmefindthejob.com",
    audit_log_sequence_no: int | None = None,
    audit_log_chain_hmac: str | None = None,
    metadata: dict[str, Any] | None = None,
    decided_at: str | None = None,
    receipt_id: str | None = None,
) -> TrustReceipt:
    """Construct + sign a Trust Receipt.

    All fields are stable hashes / IDs / timestamps — never raw
    PII. The receipt is safe to display on screen, store in
    sessionStorage, or download to the user's disk.

    Raises ``ValueError`` if ``decision_type`` is not in
    :data:`KNOWN_DECISIONS` — this guards against silent typos
    that would later produce un-categorisable receipts.
    """

    if decision_type not in KNOWN_DECISIONS:
        raise ValueError(f"unknown_decision_type:{decision_type!r}")
    if not isinstance(salt, (bytes, bytearray)) or len(salt) < 16:
        raise ValueError("salt_must_be_bytes_of_at_least_16_bytes")

    receipt_id_resolved = receipt_id or f"rcpt-{uuid.uuid4().hex[:12]}"
    decided_at_resolved = decided_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    unsigned_payload = {
        "receiptId": receipt_id_resolved,
        "schemaVersion": RECEIPT_SCHEMA_VERSION,
        "decisionType": decision_type,
        "decidedAt": decided_at_resolved,
        "userIdOpaque": _hash_user_id(user_id, salt),
        "aiProvider": ai_provider,
        "promptTemplateId": prompt_template_id,
        "promptHash": _short_content_hash(prompt_text),
        "responseHash": _short_content_hash(response_text),
        "auditLogSequenceNo": audit_log_sequence_no,
        "auditLogChainHmac": audit_log_chain_hmac,
        "issuerDid": issuer_did,
        "signatureAlgorithm": "HMAC-SHA256-v1",
        "metadata": dict(metadata or {}),
    }
    signature = _sign(unsigned_payload, salt)
    return TrustReceipt(
        receipt_id=receipt_id_resolved,
        schema_version=RECEIPT_SCHEMA_VERSION,
        decision_type=decision_type,
        decided_at=decided_at_resolved,
        user_id_opaque=unsigned_payload["userIdOpaque"],
        ai_provider=ai_provider,
        prompt_template_id=prompt_template_id,
        prompt_hash=unsigned_payload["promptHash"],
        response_hash=unsigned_payload["responseHash"],
        audit_log_sequence_no=audit_log_sequence_no,
        audit_log_chain_hmac=audit_log_chain_hmac,
        issuer_did=issuer_did,
        signature=signature,
        signature_algorithm="HMAC-SHA256-v1",
        metadata=dict(metadata or {}),
    )


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of :func:`verify_trust_receipt`. Both fields are
    primitive so the result serialises cleanly into JSON for
    audit tooling."""

    ok: bool
    reason: str | None = None


def verify_trust_receipt(receipt: dict[str, Any], salt: bytes) -> VerificationResult:
    """Recompute the signature over the canonical body and
    compare against the stored ``signature``. Returns
    ``VerificationResult(ok=True)`` on pass,
    ``VerificationResult(ok=False, reason=<code>)`` on fail.

    Reasons:
    - ``missing_signature``    — receipt has no ``signature`` field
    - ``invalid_shape``        — receipt is not a JSON object
    - ``schema_version_unknown`` — receipt advertises a schema
      version this verifier doesn't know
    - ``signature_mismatch``   — recomputed signature differs;
      receipt has been tampered with OR was signed with a
      different salt
    """

    if not isinstance(receipt, dict):
        return VerificationResult(ok=False, reason="invalid_shape")
    if receipt.get("schemaVersion") != RECEIPT_SCHEMA_VERSION:
        return VerificationResult(ok=False, reason="schema_version_unknown")
    stored = receipt.get("signature")
    if not isinstance(stored, str) or not stored:
        return VerificationResult(ok=False, reason="missing_signature")
    recomputed = _sign(receipt, salt)
    if not hmac.compare_digest(stored, recomputed):
        return VerificationResult(ok=False, reason="signature_mismatch")
    return VerificationResult(ok=True)


# ---------------------------------------------------------------------------
# Markdown rendering for human-readable receipt download
# ---------------------------------------------------------------------------


_MD_TEMPLATE = """\
# Trust Receipt

| Field | Value |
|---|---|
| Receipt ID | `{receiptId}` |
| Schema version | `{schemaVersion}` |
| Decision type | `{decisionType}` |
| Decided at | `{decidedAt}` |
| User ID (opaque) | `{userIdOpaque}` |
| AI provider | `{aiProvider}` |
| Prompt template ID | `{promptTemplateId}` |
| Prompt hash | `{promptHash}` |
| Response hash | `{responseHash}` |
| Audit log sequence_no | `{auditLogSequenceNo}` |
| Audit log chain_hmac | `{auditLogChainHmac}` |
| Issuer DID | `{issuerDid}` |
| Signature algorithm | `{signatureAlgorithm}` |
| Signature | `{signature}` |

## How to verify this receipt

This receipt is signed by the deployer's salt. To verify
independently you need:

1. This file (you have it — you just downloaded it)
2. The deployer's verification public key reference (see
   `issuerDid` above — resolves via DID:web to the deployer's
   public verification material)
3. A copy of the audit log fragment that includes
   `sequence_no = {auditLogSequenceNo}` (request from the
   deployer under GDPR Article 15)

Then either:

- Use the CLI tool at <https://helpmefindthejob.com/tools/verify-receipt>
- OR run the open-source verifier:
  `python -m company_discovery.verify_receipt_cli <this-file.json>`

If the signature verifies AND the sequence_no chain in the
audit log fragment is intact, the decision recorded here is
**cryptographically proven** to have been produced by the
deployer's system at the recorded timestamp.

## What this proves

This receipt is **mathematical evidence** of what the system
did on your behalf. The deployer cannot deny the decision was
made (they signed it). The deployer cannot change the decision
after the fact (any change breaks the signature). The audit
log chain ensures the deployer cannot quietly delete this
receipt from their own records.

## Metadata

```json
{metadata}
```
"""


def render_receipt_markdown(receipt: TrustReceipt | dict[str, Any]) -> str:
    """Render a Trust Receipt as a human-readable markdown
    document the user can save / print / forward."""
    payload = receipt.to_dict() if isinstance(receipt, TrustReceipt) else dict(receipt)
    payload["metadata"] = json.dumps(
        payload.get("metadata") or {}, sort_keys=True, indent=2
    )
    # Defensive: cast None to "null" for the markdown table
    for key in list(payload.keys()):
        if payload[key] is None:
            payload[key] = "null"
    return _MD_TEMPLATE.format(**payload)


_RECEIPT_ID_PATTERN = re.compile(r"^rcpt-[0-9a-f]{12}$")


def looks_like_receipt_id(value: str) -> bool:
    """Filename-safety check for downloaded receipt files —
    used by the HTTP handler so a user can't inject paths."""
    return bool(_RECEIPT_ID_PATTERN.match(value or ""))
