#!/usr/bin/env sh
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Drives the PART 7 Loop 20 MCP client harness as a standalone smoke
# check. Boots a real mcp_server.py subprocess (via the harness) and
# verifies: initialize handshake, tools/list returns 13 tools, one
# representative tools/call round-trip.
#
# No HTTP server boot here -- the MCP transport is stdio. The harness
# owns the subprocess lifecycle.

set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-/Users/fouad./miniconda3/bin/python3}"
exec "$PYTHON_BIN" tests/e2e/mcp_client_harness.py "$@"
