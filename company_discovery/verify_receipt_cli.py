# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline Trust Receipt verifier.

Usage:

    python -m company_discovery.verify_receipt_cli <receipt.json>

The verifier reads the deployer's salt from one of:

1. ``HELPMEFINDTHEJOB_AUDIT_SALT`` env var (base64-encoded) —
   the same salt the audit-log emitter uses
2. ``HELPMEFINDTHEJOB_AUDIT_SALT`` env var (legacy alias)
3. ``--salt-b64 <base64-string>`` CLI flag

Exit codes:

- 0 — signature OK
- 1 — signature mismatch / receipt tampered / missing fields
- 2 — usage error (missing file, missing salt, etc.)

The verifier is **standalone** — it does not import the main
app, so a user can run it on any machine with just Python +
this file + the deployer's published salt fingerprint. That's
the agency claim: the user does not need to trust the deployer
to verify the receipt.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# We import the verifier function from the trust_receipt module
# rather than reimplementing it — single source of truth for the
# canonical-bytes computation.
from company_discovery.trust_receipt import verify_trust_receipt


def _resolve_salt(salt_b64: str | None) -> bytes:
    """Decode salt from CLI flag or environment. Returns the
    raw bytes. Raises SystemExit(2) with a friendly message if
    no salt is available."""
    raw_b64 = (
        salt_b64
        or os.environ.get("HELPMEFINDTHEJOB_AUDIT_SALT")
        or os.environ.get("HELPMEFINDTHEJOB_AUDIT_SALT")
    )
    if not raw_b64:
        print(
            "ERROR: deployer salt required.\n"
            "  Either pass --salt-b64 <base64-string>\n"
            "  OR set HELPMEFINDTHEJOB_AUDIT_SALT env var\n"
            "  (request the salt from the deployer per GDPR Article 15)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        return base64.b64decode(raw_b64)
    except (base64.binascii.Error, ValueError) as exc:
        print(f"ERROR: salt is not valid base64: {exc}", file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a Trust Receipt signature offline")
    parser.add_argument("receipt_file", type=Path, help="path to the receipt JSON file")
    parser.add_argument(
        "--salt-b64",
        default=None,
        help="deployer salt as base64 (defaults to env var HELPMEFINDTHEJOB_AUDIT_LOG_SALT)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress success output; exit code 0/1/2 only",
    )
    args = parser.parse_args(argv)

    if not args.receipt_file.exists():
        print(f"ERROR: receipt file not found: {args.receipt_file}", file=sys.stderr)
        return 2

    salt = _resolve_salt(args.salt_b64)

    try:
        with args.receipt_file.open("r", encoding="utf-8") as fh:
            receipt = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"ERROR: receipt is not valid JSON: {exc}", file=sys.stderr)
        return 2

    result = verify_trust_receipt(receipt, salt)

    if result.ok:
        if not args.quiet:
            print("✓ signature OK")
            print(f"  receipt   = {receipt.get('receiptId')}")
            print(f"  decision  = {receipt.get('decisionType')}")
            print(f"  decidedAt = {receipt.get('decidedAt')}")
            print(f"  provider  = {receipt.get('aiProvider')}")
        return 0
    else:
        print(f"✗ verification FAILED: {result.reason}", file=sys.stderr)
        print(f"  receipt = {receipt.get('receiptId')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
