#!/usr/bin/env bash
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Reproducible-build verification. Builds the source tarball twice and confirms
# the SHA-256 is identical — determinism is reproducibility. Because the build
# reads only git-tracked content + git-index modes (no wall-clock, no host
# paths, no env), a stranger who runs this on their own machine from the same
# commit gets the same digest. This is the lightweight, Python-only companion to
# the Nix flake's full reproducible-build environment.
#
#   ./scripts/verify_reproducibility.sh
#
# For a tagged release: record the digest in the release notes; anyone can
# reproduce it from a clean checkout of the tag.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Reproducible source-dist check — building twice..."
sha1="$(python3 -m scripts.build_reproducible_source_dist --print-sha)"
sha2="$(python3 -m scripts.build_reproducible_source_dist --print-sha)"

echo "  pass 1: ${sha1}"
echo "  pass 2: ${sha2}"

if [ "${sha1}" = "${sha2}" ]; then
  echo "REPRODUCIBLE: identical SHA-256 across builds (${sha1})"
  exit 0
fi
echo "NOT REPRODUCIBLE: digests differ — investigate non-determinism in the builder" >&2
exit 1
