# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Standalone verifier CLI for Verifiable Credentials issued by
mesh agents.

Use cases:

- A user takes a VC issued by the Anerkennung agent to a totally
  different system (a Bundesagentur für Arbeit caseworker, a
  housing platform, an EURES portal) and wants to prove the VC
  is authentic. They run this CLI offline and get a clear
  PASS/FAIL with the issuer DID.
- A journalist auditing the mesh wants to verify that a specific
  decision was actually signed by the agent that claims to have
  signed it.
- A future agent in the federation receives a VC from an
  unknown peer; it resolves the peer's DID document and uses
  this code path to verify.

Usage::

    python -m mesh.verify_credential_cli credential.json \\
        --issuer-did did:web:anerkennung-agent.helpmefindthejob.org \\
        --issuer-public-key z6Mkhaxz...

If ``--issuer-public-key`` is omitted, the verifier looks for a
DID document at ``--did-document credential-issuer.did.json``.
If both are omitted, the verifier fails with a clear error
telling the user where the issuer's key should come from.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mesh.verifiable_credentials import (
    IssuerRecord,
    IssuerRegistry,
    verify_credential,
)


def _load_credential(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _resolve_issuer(args, vc: dict[str, Any]) -> IssuerRecord:
    """Resolve the issuer's IssuerRecord from CLI args + the VC's
    declared issuer DID. Operator-friendly errors when the key
    can't be found."""

    declared_issuer = vc.get("issuer")
    if not isinstance(declared_issuer, str):
        raise SystemExit("ERROR: credential is missing the 'issuer' field")
    if args.issuer_did and args.issuer_did != declared_issuer:
        raise SystemExit(
            f"ERROR: --issuer-did={args.issuer_did!r} does not match the "
            f"issuer field in the credential ({declared_issuer!r}). "
            "Refusing to verify against a mismatched DID."
        )
    if args.issuer_public_key:
        return IssuerRecord(
            issuer_did=declared_issuer,
            public_key_multibase=args.issuer_public_key,
        )
    if args.did_document:
        doc = json.loads(Path(args.did_document).read_text(encoding="utf-8"))
        if doc.get("id") != declared_issuer:
            raise SystemExit(
                f"ERROR: DID document id={doc.get('id')!r} does not match the "
                f"credential's issuer={declared_issuer!r}."
            )
        methods = doc.get("verificationMethod") or []
        if not methods:
            raise SystemExit("ERROR: DID document has no verificationMethod entries")
        # Pick the first key — multi-key support is a Phase 2 item.
        pubkey = methods[0].get("publicKeyMultibase")
        if not pubkey:
            raise SystemExit(
                "ERROR: DID document's first verificationMethod lacks "
                "'publicKeyMultibase' — only Ed25519VerificationKey2020 "
                "multibase keys are supported in this verifier"
            )
        return IssuerRecord(issuer_did=declared_issuer, public_key_multibase=pubkey)
    raise SystemExit(
        "ERROR: no issuer key source. Pass either:\n"
        "  --issuer-public-key z6Mk...   (multibase public key)\n"
        "  --did-document path/to/did.json  (DID Document)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a W3C Verifiable Credential issued by a mesh agent.",
    )
    parser.add_argument("credential", type=Path, help="path to the signed VC JSON file")
    parser.add_argument(
        "--issuer-did",
        help="optional — assert that the credential's issuer field matches this DID",
    )
    parser.add_argument(
        "--issuer-public-key",
        help="multibase ('z'+base64) public key of the issuer",
    )
    parser.add_argument(
        "--did-document",
        type=Path,
        help="path to the issuer's DID document JSON (alternative to --issuer-public-key)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the result as JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)

    vc = _load_credential(args.credential)
    record = _resolve_issuer(args, vc)
    registry = IssuerRegistry()
    registry.register(record)
    result = verify_credential(vc, registry=registry)

    if args.json:
        print(
            json.dumps(
                {
                    "valid": result.valid,
                    "reason": result.reason,
                    "signerDid": result.signer_did,
                },
                indent=2,
            )
        )
    else:
        status = "PASS" if result.valid else "FAIL"
        print(f"verification: {status}")
        print(f"reason:       {result.reason}")
        print(f"signer DID:   {result.signer_did or '(none)'}")
    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
