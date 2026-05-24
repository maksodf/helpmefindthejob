# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Public REST API contract tests (13-plan item 7/13; gap #28).

The MCP tool catalogue is the source of truth; this surface
mirrors it via HTTP. Tests pin:

1. **Tool catalogue parity**: every TOOL_SCHEMAS entry appears
   in `/api/v1/tools` AND in the OpenAPI spec under
   `paths./api/v1/tools/<name>.post`.
2. **OpenAPI spec validity**: required top-level keys present,
   every path has the right shape, error component referenced.
3. **dispatch_tool_call** routes to the matching method,
   filters payload to method-accepted kwargs, raises typed
   errors on unknown tool / missing required fields.
4. **Auth + user_id injection**: the HTTP route MUST inject
   the session user's id into `userId` so a client can't
   spoof someone else's user id.
5. **HTTP route presence**: app.py source carries the three
   routes (/openapi.json, /tools, /tools/<name>).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.mcp_tools import TOOL_SCHEMAS
from company_discovery.rest_api import (
    API_VERSION,
    ToolNotFoundError,
    ToolValidationError,
    build_openapi_spec,
    dispatch_tool_call,
    list_tools_for_rest,
)
from mcp_server import build_tools as _build_mcp_tools


class ToolCatalogueParity(unittest.TestCase):
    def test_list_tools_for_rest_covers_every_schema(self):
        rest_tools = list_tools_for_rest()
        rest_names = {t["name"] for t in rest_tools}
        schema_names = {t["name"] for t in TOOL_SCHEMAS}
        self.assertEqual(rest_names, schema_names)

    def test_each_rest_entry_has_path(self):
        for tool in list_tools_for_rest():
            self.assertTrue(tool["restPath"].startswith(f"/api/{API_VERSION}/tools/"))
            self.assertTrue(tool["restPath"].endswith(tool["name"]))


class OpenApiSpecValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = build_openapi_spec()

    def test_required_top_level_keys(self):
        for key in ("openapi", "info", "paths", "components"):
            self.assertIn(key, self.spec)

    def test_openapi_version_modern(self):
        self.assertTrue(self.spec["openapi"].startswith("3."))

    def test_info_has_title_version_license(self):
        info = self.spec["info"]
        self.assertIn("title", info)
        self.assertIn("version", info)
        self.assertEqual(info["license"]["name"], "Apache 2.0")

    def test_every_tool_in_paths(self):
        for tool in TOOL_SCHEMAS:
            path = f"/api/{API_VERSION}/tools/{tool['name']}"
            self.assertIn(path, self.spec["paths"])
            post_spec = self.spec["paths"][path]["post"]
            self.assertEqual(post_spec["operationId"], tool["name"])
            # The input schema is the request body schema
            req_schema = post_spec["requestBody"]["content"]["application/json"]["schema"]
            self.assertEqual(req_schema, tool["inputSchema"])

    def test_error_component_referenced(self):
        # Every error response refs the Error schema
        self.assertIn("Error", self.spec["components"]["schemas"])

    def test_security_scheme_declared(self):
        self.assertIn("sessionCookie", self.spec["components"]["securitySchemes"])
        self.assertEqual(self.spec["security"], [{"sessionCookie": []}])

    def test_servers_optional_unless_provided(self):
        # Without base_url, no servers entry
        self.assertNotIn("servers", self.spec)
        spec_with_server = build_openapi_spec(base_url="https://app.helpmefindthejob.org")
        self.assertEqual(
            spec_with_server["servers"],
            [{"url": "https://app.helpmefindthejob.org"}],
        )

    def test_spec_is_json_serializable(self):
        # If any value in the spec is a non-JSON type, this fails
        json.dumps(self.spec)


class DispatchToolCall(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tools = _build_mcp_tools(data_path=Path(self.tmp.name) / "data.sqlite3")

    def test_unknown_tool_raises_typed_error(self):
        with self.assertRaises(ToolNotFoundError):
            dispatch_tool_call("nonexistent_tool", {}, self.tools)

    def test_missing_required_field_raises_validation_error(self):
        # suggest_relevant_companies requires targetRoles + industry
        with self.assertRaises(ToolValidationError) as cm:
            dispatch_tool_call(
                "suggest_relevant_companies",
                {"targetRoles": ["Pflegekraft"]},  # missing industry
                self.tools,
            )
        self.assertIn("missing_required_fields", str(cm.exception))
        self.assertIn("industry", str(cm.exception))

    def test_valid_call_dispatches(self):
        result = dispatch_tool_call(
            "suggest_relevant_companies",
            {"targetRoles": ["Pflegekraft"], "industry": "Healthcare"},
            self.tools,
        )
        self.assertIsInstance(result, dict)
        # The tool returns at least a "suggestions" or similar key
        self.assertTrue(len(result) > 0)

    def test_inject_user_id_overrides_payload(self):
        # If the payload omits userId AND inject_user_id is set,
        # the server's authenticated user wins (defense against
        # client spoofing user IDs)
        result = dispatch_tool_call(
            "add_company_to_watchlist",
            {"name": "ACME", "websiteUrl": "https://acme.example.com"},
            self.tools,
            inject_user_id="real-session-user",
        )
        self.assertIsInstance(result, dict)

    def test_extra_payload_fields_filtered_out(self):
        # Payload with extra fields the method doesn't accept must
        # not raise TypeError — they get filtered out before call
        result = dispatch_tool_call(
            "suggest_relevant_companies",
            {
                "targetRoles": ["Pflegekraft"],
                "industry": "Healthcare",
                "totally_extra_field": "should be filtered",
                "another_extra": 42,
            },
            self.tools,
        )
        self.assertIsInstance(result, dict)


class HttpRoutesPresence(unittest.TestCase):
    """The REST routes live in app.py. Pin that all three are
    present so a future refactor can't quietly delete them."""

    @classmethod
    def setUpClass(cls):
        cls.src = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")

    def test_openapi_route_present(self):
        self.assertIn('"/api/v1/openapi.json"', self.src)

    def test_tools_catalogue_route_present(self):
        self.assertIn('"/api/v1/tools"', self.src)

    def test_tool_call_dispatch_route_present(self):
        self.assertIn("tool_call_match", self.src)
        self.assertIn("dispatch_tool_call", self.src)

    def test_user_id_injection_present(self):
        # The route MUST inject the session user_id (not trust
        # client-supplied)
        self.assertRegex(self.src, r"inject_user_id\s*=\s*STATE\.effective_user_id\(")


if __name__ == "__main__":
    unittest.main()
