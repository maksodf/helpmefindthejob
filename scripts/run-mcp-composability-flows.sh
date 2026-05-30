#!/usr/bin/env sh
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Runs both PART 7 Loop 22 composability flows and writes their
# markdown evidence to docs/grant/mcp-walks-2026-05-21/. Designed for
# the grant pack -- regenerate evidence whenever the MCP surface
# changes (tool schemas, ESCO dataset, EURES projection contract).
#
# The flows themselves are also exercised by the regular test suite at
# tests.e2e.test_composability_flows so CI catches regressions; this
# script is the artifact-producing wrapper.

set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT_DIR="$ROOT/docs/grant/mcp-walks-2026-05-21"
mkdir -p "$OUT_DIR"

echo "[mcp-composability] Flow 1: Aicha 7-step chain"
"$PYTHON_BIN" -m tests.e2e.composability_flows aicha \
  > "$OUT_DIR/composability-flow-aicha.md"

echo "[mcp-composability] Flow 2: Krankenschwester ESCO + EURES"
"$PYTHON_BIN" -m tests.e2e.composability_flows esco-eures \
  > "$OUT_DIR/composability-flow-esco-eures.md"

echo "[mcp-composability] Evidence captured:"
wc -l "$OUT_DIR"/composability-flow-*.md
