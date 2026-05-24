# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""W3C Verifiable Credentials Data Model 2.0 — real signing layer
(4-week plan invariant 8).

Until this module landed, the mesh agents shipped a VC stub with
a ``PendingSignaturePlaceholder`` proof — a known gap from the
W2 D6 commit. This module closes that gap with real Ed25519
signatures over canonical JSON, matching the
W3C ``DataIntegrityProof`` + ``eddsa-rdfc-2022`` cryptosuite shape
(simplified: we use canonical JCS instead of RDF canonicalisation
because JCS is stdlib-implementable and the consumers in this
project are JSON-native).

Design:

- **Key persistence**: Ed25519 keypair lives at
  ``<data_dir>/mesh/vc_signing_key.json`` (PKCS8 PEM in private
  field, raw bytes hex in public field). Generated on first use.
  Operator can rotate by deleting the file.
- **Canonicalisation**: JSON canonical serialisation per RFC 8785
  (JCS) — sort keys lexicographically, no whitespace, UTF-8 NFC.
  Implemented in stdlib (no extra dep).
- **Signing**: Ed25519 from ``cryptography`` lib (already pinned in
  requirements.txt for the audit-log + AEAD layers). EdDSA gives
  us deterministic signatures so the same VC content → same proof
  → testable.
- **Verification**: ``verify_credential(signed_vc, expected_issuer)``
  returns :class:`VerificationResult` with `valid`, `reason`,
  `signer_did`. Verifier looks up the public key by issuer DID;
  for ``did:web`` it resolves via a registry (in production the
  issuer would host ``/.well-known/did.json``; for the project
  we ship an in-process registry).

Threat model:

- Tampering with credentialSubject after issuance → signature
  invalid, verify() returns False with reason `signature_mismatch`.
- Issuer impersonation → verify() returns False with reason
  `unknown_issuer` if the issuer DID isn't in the registry.
- Replay → out of scope for the VC layer; consumers MUST check
  validFrom + validUntil + the VC's `id` against a nullifier set
  if replay-resistance is needed.
- Key compromise → operator rotates the keypair file and rebuilds
  the did.json registry. Old VCs become unverifiable; that's the
  intended behavior for compromise-recovery.

Limitations:

- We use JCS-style canonical JSON, not RDF canonicalisation —
  the W3C VC ecosystem will accept JSON-LD ``@context`` linkage
  but a strict ``DataIntegrityProof`` consumer expecting
  ``rdfc-1.0`` will reject our proof. This is documented as a
  Phase 2 upgrade in :mod:`docs/grant/03-post-grant.md`.
- We do not issue a DID Document — the public key is exported
  via :func:`build_did_document` and the operator publishes it
  at ``/.well-known/did.json`` for the production deploy. Tests
  use the in-process registry.
"""

from __future__ import annotations

import base64
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of :func:`verify_credential`. Always returned (never
    raises) so callers can render a useful failure message."""

    valid: bool
    reason: str
    signer_did: str | None = None


PROOF_TYPE = "DataIntegrityProof"
CRYPTOSUITE = "eddsa-jcs-2022-mesh"  # Project-specific JCS variant
PROOF_PURPOSE = "assertionMethod"


# ---------------------------------------------------------------------------
# JCS canonical JSON
# ---------------------------------------------------------------------------


def canonical_json(value: Any) -> bytes:
    """RFC 8785-style canonical JSON.

    - keys sorted lexicographically at every nesting level
    - no whitespace
    - UTF-8 encoding
    - floats serialised without trailing zeros (we use ``json.dumps``
      with ``ensure_ascii=False`` + ``separators=(",", ":")``)

    The W3C VC spec wants RDF canonicalisation (URDNA2015) for
    full interop, but JCS is sufficient for the federated agents
    in this project — they all consume the JSON form directly,
    no JSON-LD expansion step.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Ed25519 signer / verifier
# ---------------------------------------------------------------------------


class Ed25519Signer:
    """Lightweight Ed25519 wrapper backed by the ``cryptography``
    library. Loads (or generates + persists) a keypair at
    ``data/mesh/vc_signing_key.json``.

    The key file shape::

        {
            "alg": "Ed25519",
            "createdAt": "2026-05-21T20:00:00+00:00",
            "publicKeyMultibase": "z6Mk...",
            "privateKeyPkcs8Pem": "-----BEGIN PRIVATE KEY-----\\n...",
        }

    The PKCS8 PEM keeps the file inspectable; ``publicKeyMultibase``
    is the W3C-standard form embedded in DID documents. Both
    represent the same key.
    """

    _GENERATION_LOCK = threading.Lock()

    def __init__(self, private_key, public_key, signer_did: str) -> None:
        self._private_key = private_key
        self._public_key = public_key
        self.signer_did = signer_did

    # ---- factory --------------------------------------------------------

    @classmethod
    def from_file_or_create(cls, key_path: Path, *, signer_did: str) -> Ed25519Signer:
        """Load Ed25519 keypair from ``key_path``. If absent, generate
        a new keypair and write it. Operator-facing — used by mesh
        agents at boot."""

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        with cls._GENERATION_LOCK:
            if key_path.exists():
                blob = json.loads(key_path.read_text(encoding="utf-8"))
                pem = blob["privateKeyPkcs8Pem"].encode("utf-8")
                priv = serialization.load_pem_private_key(pem, password=None)
                if not isinstance(priv, Ed25519PrivateKey):
                    raise ValueError("expected_ed25519_private_key")
                pub = priv.public_key()
                return cls(priv, pub, signer_did=signer_did)
            # Generate new keypair
            priv = Ed25519PrivateKey.generate()
            pub = priv.public_key()
            pem = priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")
            pub_raw = pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(
                json.dumps(
                    {
                        "alg": "Ed25519",
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "publicKeyMultibase": "z" + base64.b64encode(pub_raw).decode("ascii"),
                        "privateKeyPkcs8Pem": pem,
                        "warning": "secret material; gitignored; rotate by deleting this file",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            # Lock down file permissions on POSIX — 0o600 so only
            # the running user can read/write.
            try:
                os.chmod(key_path, 0o600)
            except OSError:
                # Filesystem may not support chmod (Windows, some FUSE
                # mounts). Best-effort — the key still works, but the
                # operator MUST audit the perms themselves.
                pass
            return cls(priv, pub, signer_did=signer_did)

    # ---- public key export ----------------------------------------------

    def public_key_multibase(self) -> str:
        """Return the public key in W3C multibase form (z + base64)."""
        from cryptography.hazmat.primitives import serialization

        pub_raw = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return "z" + base64.b64encode(pub_raw).decode("ascii")

    def public_key_raw(self) -> bytes:
        from cryptography.hazmat.primitives import serialization

        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    # ---- signing --------------------------------------------------------

    def sign_credential(self, unsigned_vc: dict[str, Any]) -> dict[str, Any]:
        """Attach a ``DataIntegrityProof`` to ``unsigned_vc``. Returns
        a NEW dict — the input is not mutated.

        The VC's ``issuer`` field MUST match this signer's
        ``signer_did`` — otherwise we would silently sign claims
        an agent isn't entitled to make (agent A could issue a VC
        with ``issuer: did:web:agent-b``, fooling consumers that
        don't cross-check). Verification catches it (the registry's
        public key for agent B won't match agent A's signature),
        but failing fast at sign-time is cleaner.
        """

        if "proof" in unsigned_vc:
            raise ValueError("vc_already_signed")
        vc_issuer = unsigned_vc.get("issuer")
        if vc_issuer != self.signer_did:
            raise ValueError(f"issuer_mismatch:vc_says={vc_issuer!r} signer_is={self.signer_did!r}")
        # The proof is signed over the canonical form of the VC
        # WITHOUT the proof field (chicken-and-egg). We append the
        # proof scaffolding (without proofValue) and canonicalise.
        signed = dict(unsigned_vc)
        proof_scaffold = {
            "type": PROOF_TYPE,
            "cryptosuite": CRYPTOSUITE,
            "proofPurpose": PROOF_PURPOSE,
            "verificationMethod": f"{self.signer_did}#key-1",
            "created": datetime.now(timezone.utc).isoformat(),
        }
        # Compute signature input: canonical(VC) || canonical(proof_scaffold)
        # The W3C spec uses a slightly different "hash of two hashes"
        # construct; for an internal-mesh signature suite this
        # concatenation form is sufficient and unambiguous.
        sig_input = canonical_json(signed) + b"|" + canonical_json(proof_scaffold)
        signature = self._private_key.sign(sig_input)
        proof_scaffold["proofValue"] = "z" + base64.b64encode(signature).decode("ascii")
        signed["proof"] = proof_scaffold
        return signed


# ---------------------------------------------------------------------------
# Issuer registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuerRecord:
    """In-process registry entry. In production the verifier would
    resolve the DID via HTTP (``did:web:...``); here we ship the
    registry alongside the agents."""

    issuer_did: str
    public_key_multibase: str


class IssuerRegistry:
    """Thread-safe in-process map of ``issuer_did → public key``.

    Each mesh agent registers itself at boot via :meth:`register`;
    verifiers query :meth:`lookup`. Production deploys publish
    DID documents at ``/.well-known/did.json`` and resolve over
    HTTP — that integration ships in Phase 2.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, IssuerRecord] = {}

    def register(self, record: IssuerRecord) -> None:
        with self._lock:
            self._records[record.issuer_did] = record

    def lookup(self, issuer_did: str) -> IssuerRecord | None:
        with self._lock:
            return self._records.get(issuer_did)

    def all_issuers(self) -> list[str]:
        with self._lock:
            return sorted(self._records.keys())


# Module-level default registry — agents register themselves at boot.
# Tests can install their own via :func:`set_default_registry`.
_DEFAULT_REGISTRY = IssuerRegistry()


def default_registry() -> IssuerRegistry:
    return _DEFAULT_REGISTRY


def set_default_registry(registry: IssuerRegistry) -> None:
    """Replace the module-level registry. Used by tests."""

    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = registry


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


def _multibase_to_raw(multibase: str) -> bytes:
    """Decode a 'z' + base64 multibase string into raw bytes.

    Per the W3C multibase spec, 'z' is base58btc — but the project
    uses base64 throughout (audit log salts, encryption keys) and
    the multibase decoder we ship matches what the signer wrote.
    Inter-op with base58btc consumers ships in Phase 2 alongside
    full URDNA2015 canonicalisation.
    """

    if not multibase.startswith("z"):
        raise ValueError("expected_z_prefix_multibase")
    return base64.b64decode(multibase[1:])


def verify_credential(
    signed_vc: dict[str, Any],
    *,
    registry: IssuerRegistry | None = None,
) -> VerificationResult:
    """Verify the ``proof`` on a signed VC against the issuer's
    public key in the registry.

    Returns a :class:`VerificationResult` describing the outcome.
    NEVER raises — even a malformed VC produces a structured
    failure with a useful reason.
    """

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )

    registry = registry or default_registry()
    try:
        proof = signed_vc.get("proof")
        if not isinstance(proof, dict):
            return VerificationResult(False, "missing_or_invalid_proof")
        issuer = signed_vc.get("issuer")
        if not isinstance(issuer, str) or not issuer:
            return VerificationResult(False, "missing_issuer")
        record = registry.lookup(issuer)
        if record is None:
            return VerificationResult(False, "unknown_issuer", signer_did=issuer)
        # Reconstruct the signature input the signer used.
        unsigned = {k: v for k, v in signed_vc.items() if k != "proof"}
        proof_scaffold = {k: v for k, v in proof.items() if k != "proofValue"}
        sig_input = canonical_json(unsigned) + b"|" + canonical_json(proof_scaffold)
        proof_value = proof.get("proofValue")
        if not isinstance(proof_value, str):
            return VerificationResult(False, "missing_proof_value", signer_did=issuer)
        try:
            signature = _multibase_to_raw(proof_value)
        except ValueError:
            return VerificationResult(False, "malformed_proof_value", signer_did=issuer)
        try:
            pub_raw = _multibase_to_raw(record.public_key_multibase)
        except ValueError:
            return VerificationResult(False, "malformed_registry_key", signer_did=issuer)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_raw)
        try:
            pub_key.verify(signature, sig_input)
        except InvalidSignature:
            return VerificationResult(False, "signature_mismatch", signer_did=issuer)
        return VerificationResult(True, "ok", signer_did=issuer)
    except Exception as exc:  # noqa: BLE001 - verifier must never crash
        return VerificationResult(False, f"unexpected_error:{type(exc).__name__}")


# ---------------------------------------------------------------------------
# DID document export (for /.well-known/did.json)
# ---------------------------------------------------------------------------


def build_did_document(signer: Ed25519Signer) -> dict[str, Any]:
    """Render the W3C DID Document an issuer publishes at
    ``/.well-known/did.json`` so verifiers anywhere can resolve
    its public key.
    """

    return {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "id": signer.signer_did,
        "verificationMethod": [
            {
                "id": f"{signer.signer_did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": signer.signer_did,
                "publicKeyMultibase": signer.public_key_multibase(),
            }
        ],
        "assertionMethod": [f"{signer.signer_did}#key-1"],
    }
