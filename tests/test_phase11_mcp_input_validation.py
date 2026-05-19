# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Tests for MCP tools/call inputSchema enforcement.

The MCP catalogue published at ``tools/list`` advertises an
``inputSchema`` per tool. Pre-migration the server did not actually
validate ``tools/call`` arguments against these schemas — the
``**arguments`` spread relied on Python's own positional-argument
check, which produces a useful error string but bypasses the schema
contract entirely.

This module pins the post-migration behaviour: every ``tools/call``
payload is validated against the registered tool's inputSchema before
dispatch, and validation failures return an RFC 7807 Problem Details
payload via the standard MCP ``isError=True`` channel.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import jsonschema

import mcp_server


class ValidateToolArgumentsTests(unittest.TestCase):
    """Pure-function tests for :func:`mcp_server.validate_tool_arguments`."""

    def test_valid_arguments_return_none(self) -> None:
        # ``add_company_to_watchlist`` requires userId + name + websiteUrl.
        problem = mcp_server.validate_tool_arguments(
            "add_company_to_watchlist",
            {
                "userId": "u-1",
                "name": "Charité",
                "websiteUrl": "https://charite.de",
            },
        )
        self.assertIsNone(problem)

    def test_missing_required_field_returns_problem(self) -> None:
        problem = mcp_server.validate_tool_arguments(
            "add_company_to_watchlist",
            {"name": "Charité"},  # userId + websiteUrl absent
        )
        self.assertIsNotNone(problem)
        assert problem is not None  # type narrowing for mypy
        self.assertEqual(problem["status"], "invalid_arguments")
        self.assertEqual(problem["type"], "about:blank")
        self.assertEqual(problem["instance"], "add_company_to_watchlist")
        self.assertEqual(problem["violatedRule"], "required")
        # Either userId or websiteUrl will be the first reported missing
        # field — both are missing, jsonschema picks one deterministically.
        self.assertTrue("userId" in problem["detail"] or "websiteUrl" in problem["detail"])

    def test_wrong_type_returns_problem(self) -> None:
        # All required fields present; one has the wrong type.
        problem = mcp_server.validate_tool_arguments(
            "add_company_to_watchlist",
            {
                "userId": 42,  # should be string
                "name": "Charité",
                "websiteUrl": "https://charite.de",
            },
        )
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertEqual(problem["status"], "invalid_arguments")
        self.assertEqual(problem["violatedRule"], "type")

    def test_non_object_arguments_returns_problem(self) -> None:
        problem = mcp_server.validate_tool_arguments(
            "get_company_watchlist_summary",
            "not an object",  # type: ignore[arg-type]
        )
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertEqual(problem["status"], "invalid_arguments")
        self.assertEqual(problem["violatedRule"], "type")
        self.assertIn("must be a JSON object", problem["detail"])

    def test_unknown_tool_returns_problem(self) -> None:
        problem = mcp_server.validate_tool_arguments(
            "definitely_not_a_real_tool",
            {},
        )
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertEqual(problem["status"], "unknown_tool")
        self.assertEqual(problem["instance"], "definitely_not_a_real_tool")

    def test_every_tool_in_catalogue_has_resolvable_schema(self) -> None:
        """Sanity: every published tool can be schema-validated."""

        for tool in mcp_server.TOOL_SCHEMAS:
            schema = tool.get("inputSchema") or {"type": "object"}
            # Compile the schema — jsonschema will raise on a malformed
            # schema, which would be a regression we want to catch.
            jsonschema.Draft7Validator.check_schema(schema)


class HandleRequestDispatchTests(unittest.TestCase):
    """End-to-end through :func:`mcp_server.handle_request`, using a real
    tools object backed by a throwaway sqlite DB."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tools = mcp_server.build_tools(data_path=Path(self._tmp.name) / "company.sqlite3")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _call(self, name: str, arguments: Any) -> dict[str, Any]:
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        return response

    def _extract_text_payload(self, response: dict[str, Any]) -> dict[str, Any]:
        text = response["result"]["content"][0]["text"]
        return json.loads(text)

    def test_valid_dispatch_returns_non_error(self) -> None:
        response = self._call(
            "get_company_watchlist_summary",
            {"userId": "u-1"},
        )
        self.assertNotIn("error", response)
        # The tool executes; isError should be False (or absent for non-error
        # paths). Some tool implementations may still return a structured
        # empty payload — we only assert that the catalogue contract is
        # honoured (no schema-level rejection).
        self.assertFalse(response["result"].get("isError", False))

    def test_missing_required_field_returns_structured_error(self) -> None:
        response = self._call("add_company_to_watchlist", {})
        self.assertTrue(response["result"]["isError"])
        payload = self._extract_text_payload(response)
        self.assertEqual(payload["status"], "invalid_arguments")
        self.assertEqual(payload["instance"], "add_company_to_watchlist")
        self.assertEqual(payload["violatedRule"], "required")

    def test_wrong_type_returns_structured_error(self) -> None:
        response = self._call(
            "add_company_to_watchlist",
            {
                "userId": ["not", "a", "string"],
                "name": "Charité",
                "websiteUrl": "https://charite.de",
            },
        )
        self.assertTrue(response["result"]["isError"])
        payload = self._extract_text_payload(response)
        self.assertEqual(payload["status"], "invalid_arguments")
        self.assertEqual(payload["violatedRule"], "type")

    def test_unknown_tool_returns_structured_error(self) -> None:
        response = self._call("does_not_exist", {})
        self.assertTrue(response["result"]["isError"])
        payload = self._extract_text_payload(response)
        self.assertEqual(payload["status"], "unknown_tool")

    def test_validation_short_circuits_before_dispatch(self) -> None:
        """Validation failures must not reach the tool implementation."""

        with patch.object(self.tools, "add_company_to_watchlist") as mock_tool:
            response = self._call("add_company_to_watchlist", {})
            self.assertTrue(response["result"]["isError"])
            mock_tool.assert_not_called()

    def test_tool_raised_exception_returns_structured_error(self) -> None:
        """Exceptions inside a successfully-validated tool body still
        return a structured error (with ``status='tool_error'``), not a
        bare Python traceback."""

        # Make the tool raise. Schema validation should pass; the tool
        # body throws; the response should be a tool_error problem.
        with patch.object(
            self.tools,
            "get_company_watchlist_summary",
            side_effect=RuntimeError("simulated"),
        ):
            response = self._call(
                "get_company_watchlist_summary",
                {"userId": "u-1"},
            )
        self.assertTrue(response["result"]["isError"])
        payload = self._extract_text_payload(response)
        self.assertEqual(payload["status"], "tool_error")
        self.assertIn("simulated", payload["detail"])


class AdditionalPropertiesPolicyTests(unittest.TestCase):
    """Document the additionalProperties posture per tool. The current
    catalogue does not set ``additionalProperties: false`` on its
    schemas, so unknown keys pass validation. This test pins that
    behaviour explicitly so a future tightening is a deliberate
    decision rather than an accident."""

    def test_unknown_key_currently_accepted(self) -> None:
        problem = mcp_server.validate_tool_arguments(
            "add_company_to_watchlist",
            {
                "userId": "u-1",
                "name": "Charité",
                "websiteUrl": "https://charite.de",
                "totallyUnknownKey": "ignored",
            },
        )
        # If the maintainer later sets additionalProperties=false on the
        # catalogue schemas, this test should be updated to assert the
        # problem document is returned. Until then, extra keys pass.
        self.assertIsNone(problem)


if __name__ == "__main__":
    unittest.main()
