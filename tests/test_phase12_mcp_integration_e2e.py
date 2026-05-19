# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""End-to-end MCP integration test.

Spawns ``mcp_server.py`` as a real subprocess and drives it over
JSON-RPC over stdio — the same transport an external MCP client (e.g.
Claude Desktop, Cursor, Continue, Cline, the §2.5 housing-agent
reference integration) uses. The CI workflow at
``.github/workflows/mcp-integration.yml`` runs this module as its
green-light check.

Coverage:

- ``initialize`` returns protocolVersion ``2024-11-05`` and
  serverInfo.name ``helpmefindthejob``
- ``tools/list`` returns 13 tools (catalogue v0.2.0), each with a
  Draft-7-valid inputSchema
- Representative ``tools/call`` happy paths for three tools spanning
  the data flow:
    * ``find_company_career_page`` — read-side legacy catalogue tool
    * ``propose_referral`` — §2.3 composition-pattern-1 tool
    * ``query_esco_skill`` — §2.4 ESCO-backed lookup with German label
- Schema-validation failure path: a deliberately-malformed
  ``tools/call`` payload returns the RFC 7807 problem document via
  the standard MCP ``isError=True`` channel
- Clean shutdown: subprocess exits 0 within a bounded wait

Runs in any environment where Python 3.11+ and `jsonschema` are
available. The CI workflow installs from requirements.txt before
invoking the test.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER = REPO_ROOT / "mcp_server.py"


class _StdioMCPClient:
    """Minimal JSON-RPC-over-stdio MCP client. One per test for
    isolation; each instance owns its own subprocess + data dir."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        env = os.environ.copy()
        env["COMPANY_DISCOVERY_DATA_DIR"] = self._tmp.name
        self._proc = subprocess.Popen(
            [sys.executable, str(MCP_SERVER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        self._next_id = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params or {},
        }
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        return json.loads(line)

    def close(self) -> int:
        # Close every pipe + the tempdir even if the wait raises. The
        # explicit close avoids a ResourceWarning on garbage collection
        # (PART 6 of the pre-submission scope-tightening slice).
        assert self._proc.stdin is not None
        try:
            try:
                self._proc.stdin.close()
            except Exception:
                pass
            return self._proc.wait(timeout=10)
        finally:
            for stream in (self._proc.stdout, self._proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            self._tmp.cleanup()


class MCPIntegrationE2E(unittest.TestCase):
    """The CI workflow runs this class. Treat it as the project's
    'is the MCP server alive and contractually compliant' smoke test."""

    def setUp(self) -> None:
        self.client = _StdioMCPClient()
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        try:
            exit_code = self.client.close()
        except subprocess.TimeoutExpired:
            self.fail("MCP server did not shut down within 10 seconds")
        # The shutdown signal is "stdin closed"; the server should exit 0.
        self.assertEqual(exit_code, 0)

    # ----- protocol handshake -----

    def test_01_initialize_returns_canonical_protocol_version(self) -> None:
        response = self.client.call("initialize", {})
        result = response["result"]
        self.assertEqual(result["protocolVersion"], "2024-11-05")
        self.assertEqual(result["serverInfo"]["name"], "helpmefindthejob")
        self.assertIn("capabilities", result)
        self.assertIn("tools", result["capabilities"])

    def test_02_ping_returns_empty_result(self) -> None:
        self.client.call("initialize", {})
        response = self.client.call("ping", {})
        self.assertEqual(response["result"], {})

    # ----- catalogue -----

    def test_03_tools_list_returns_thirteen_tools_with_draft7_schemas(self) -> None:
        self.client.call("initialize", {})
        response = self.client.call("tools/list", {})
        tools = response["result"]["tools"]
        self.assertEqual(len(tools), 13, msg="catalogue v0.2.0 has 13 tools")
        names = {tool["name"] for tool in tools}
        # Sanity: all 8 baseline + all 5 §2.3 tools are present.
        for required in (
            "suggest_relevant_companies",
            "add_company_to_watchlist",
            "find_company_career_page",
            "scan_company_career_page",
            "extract_direct_jobs_from_company_site",
            "import_discovered_job",
            "deduplicate_discovered_jobs",
            "get_company_watchlist_summary",
            "get_user_profile_for_consent",
            "propose_referral",
            "query_esco_skill",
            "export_eures_compatible",
            "record_user_outcome",
        ):
            self.assertIn(required, names, msg=required)
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)
            jsonschema.Draft7Validator.check_schema(tool["inputSchema"])

    # ----- representative tools/call happy paths -----

    def test_04_propose_referral_happy_path(self) -> None:
        """§2.3 composition-pattern-1 tool: emits a structured referral."""

        self.client.call("initialize", {})
        response = self.client.call(
            "tools/call",
            {
                "name": "propose_referral",
                "arguments": {
                    "userId": "u-aicha",
                    "targetAgent": "housing-agent",
                    "reason": "user mentioned housing search alongside job hunt",
                    "context": {"city": "Berlin"},
                },
            },
        )
        result = response["result"]
        self.assertFalse(result.get("isError", False))
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["status"], "ok")
        referral = payload["referral"]
        for field in (
            "referralId",
            "sourceAgent",
            "targetAgent",
            "userId",
            "intent",
            "priority",
            "reasonCode",
            "userConsentRequired",
        ):
            self.assertIn(field, referral, msg=field)
        self.assertEqual(referral["sourceAgent"], "helpmefindthejob")
        self.assertEqual(referral["targetAgent"], "housing-agent")
        self.assertEqual(referral["userId"], "u-aicha")

    def test_05_query_esco_skill_happy_path(self) -> None:
        """§2.4 ESCO-backed lookup, German label match."""

        self.client.call("initialize", {})
        response = self.client.call(
            "tools/call",
            {
                "name": "query_esco_skill",
                "arguments": {"query": "Krankenpfleger", "type": "occupation"},
            },
        )
        result = response["result"]
        self.assertFalse(result.get("isError", False))
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["datasetVersion"], "v1-curated-2026-05-18")
        self.assertGreater(payload["totalCandidates"], 0)
        # At least one match should be a nurse-shaped occupation.
        match_labels = [m.get("label_de", "") for m in payload["matches"]]
        self.assertTrue(
            any("Krankenpfleger" in label for label in match_labels),
            msg=f"expected at least one Krankenpfleger match, got {match_labels}",
        )

    def test_06_find_company_career_page_happy_path(self) -> None:
        """Read-side legacy catalogue tool. Empty repository — the tool
        returns a structured 'not found / no career page' response
        rather than raising."""

        self.client.call("initialize", {})
        response = self.client.call(
            "tools/call",
            {
                "name": "find_company_career_page",
                "arguments": {"userId": "u-1", "companyId": "company-does-not-exist"},
            },
        )
        result = response["result"]
        # Either the tool returns a structured 'no match' (status: ok or
        # status: not_found inside the payload) or a tool_error problem.
        # The contract for this CI test is: no schema-validation error,
        # and the response carries a parseable payload.
        payload = json.loads(result["content"][0]["text"])
        self.assertIsInstance(payload, dict)
        # Either a happy-path 'status: ok' or a tool_error problem.
        self.assertIn(
            payload.get("status"),
            {"ok", "tool_error", "error"},
            msg=f"unexpected status {payload.get('status')!r}",
        )

    # ----- schema-validation failure path -----

    def test_07_invalid_arguments_returns_rfc7807_problem_document(self) -> None:
        """Deliberately malformed payload — must surface the RFC 7807
        Problem Details via the MCP isError=True channel."""

        self.client.call("initialize", {})
        response = self.client.call(
            "tools/call",
            {
                "name": "record_user_outcome",
                "arguments": {
                    "userId": "u-1",
                    "jobId": "job-1",
                    "outcomeType": "ghosted",  # not in the enum
                },
            },
        )
        result = response["result"]
        self.assertTrue(result["isError"])
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["status"], "invalid_arguments")
        self.assertEqual(payload["type"], "about:blank")
        self.assertEqual(payload["instance"], "record_user_outcome")
        self.assertEqual(payload["violatedRule"], "enum")
        self.assertIn("ghosted", payload["detail"])

    def test_08_unknown_method_returns_jsonrpc_error_minus_32601(self) -> None:
        self.client.call("initialize", {})
        response = self.client.call("not_a_real_method", {})
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
