# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Civic Agent Composition Protocol (CACP) — conformance tooling.

A runnable conformance suite that an independent implementer can point at any
candidate MCP server to check whether it implements CACP v0.1 (the
consent-bound, audit-attributed civic-agent composition contract). See
``docs/protocol/cacp-v0.1.md`` for the normative spec and
``conformance/cacp/harness.py`` for the runner.
"""

from conformance.cacp.harness import ConformanceHarness, ConformanceReport, run_conformance
from conformance.cacp.stdio_client import MCPSession, StdioMCPClient, spawn_server

__all__ = [
    "ConformanceHarness",
    "ConformanceReport",
    "run_conformance",
    "MCPSession",
    "StdioMCPClient",
    "spawn_server",
]
