#!/usr/bin/env bash
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Local cosign signing dry-run. Proves the release signing flow end-to-end —
# build the reproducible source tarball, generate an EPHEMERAL ECDSA key, sign
# the tarball, verify the signature — with NO network, NO OIDC, NO operator
# tag-push. Any contributor can run it to confirm the mechanics work on their
# machine before the operator performs the real signing with the long-lived key
# documented in docs/releases/v0.80.0-signing.md.
#
#   ./scripts/sign_release_local.sh
#
# The ephemeral key lives only in a temp dir and is deleted on exit — it never
# touches the repo. This is a *flow* proof, not the release signature.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v cosign >/dev/null 2>&1; then
  echo "cosign not installed — see https://docs.sigstore.dev/cosign/system_config/installation/" >&2
  exit 2
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

tarball="$work/source.tar.gz"
echo "Building reproducible source tarball..."
python3 -m scripts.build_reproducible_source_dist --output "$tarball"
sha="$(python3 -m scripts.build_reproducible_source_dist --print-sha)"
echo "  source-tar sha256: $sha"

echo "Generating ephemeral signing key (temp dir, deleted on exit)..."
export COSIGN_PASSWORD=""   # unencrypted ephemeral key — non-interactive dry-run only
( cd "$work" && cosign generate-key-pair >/dev/null )

echo "Signing the tarball (offline, no transparency-log upload)..."
# --use-signing-config=false drops cosign 3.x's default Sigstore signing config
# (whose Rekor URL would otherwise force a network upload); --tlog-upload=false
# then keeps the key-based signature fully offline.
cosign sign-blob --yes --key "$work/cosign.key" \
  --use-signing-config=false --tlog-upload=false \
  --bundle "$work/source.tar.gz.sigstore" "$tarball" >/dev/null

echo "Verifying the signature with the public key..."
if cosign verify-blob --key "$work/cosign.pub" \
     --bundle "$work/source.tar.gz.sigstore" \
     --insecure-ignore-tlog=true "$tarball" >/dev/null 2>&1; then
  echo "SIGNING DRY-RUN OK: cosign signature verified locally (ephemeral key, no network)."
  exit 0
fi
echo "SIGNING DRY-RUN FAILED: verification did not pass." >&2
exit 1
