# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""PART 7 Loop 21: per-tool subprocess matrix + JSON-RPC error envelope.

Drives every published MCP tool through the real stdio transport
(:class:`MCPHarness`). Extends the existing test_phase12 coverage from
3 example tools (propose_referral / query_esco_skill /
find_company_career_page) to ALL 15 tools, and adds complete JSON-RPC
error-envelope coverage (-32601 unknown method, -32700 parse error).

The phase11 input-validation suite covers the dispatcher in-process;
this file proves the *real subprocess transport* surfaces every shape
correctly. Both layers are kept: dispatcher unit tests are fast feedback
loops; this file is the "real MCP client" verification PART 7 needs.

Test shape:
- One subprocess per class (setUpClass) -- 15 tools each get three round-trips
  (happy-shaped, missing required, wrong type), totalling ~40 assertions
- Each tool's happy-shape is "schema-valid args that the round-trip
  accepts"; some tools then fail in the service layer because the
  empty test data dir has no prior state. Those are documented as
  isError=True with a recognised status (tool_error / blocked / etc).
- JSON-RPC error envelope coverage: unknown method -> -32601, parse
  error on malformed JSON -> -32700
"""

from __future__ import annotations

import unittest

from tests.e2e.mcp_client_harness import (
    MCPHarness,
    assert_jsonrpc_error,
    assert_ok,
    assert_tool_error,
    parse_tool_result,
)

# Per-tool happy-shape inputs. Each entry is (tool_name, kwargs,
# expected_outcome) where expected_outcome is "ok" (assert_ok) or one of
# {"tool_error", "ok_or_tool_error"}. Tools that need pre-existing repo
# state surface as tool_error in a fresh tempdir -- that still proves the
# subprocess round-trip is wired correctly through schema validation +
# dispatch + service layer + error formatting.
_HAPPY_INPUTS: list[tuple[str, dict[str, object], str]] = [
    (
        "suggest_relevant_companies",
        {"targetRoles": ["nurse"], "industry": "healthcare"},
        "ok",
    ),
    (
        "add_company_to_watchlist",
        {
            "userId": "u-matrix-1",
            "name": "Matrix Test Company",
            "websiteUrl": "https://example.invalid",
        },
        "ok",
    ),
    (
        "find_company_career_page",
        {"userId": "u-matrix-2", "companyId": "co-does-not-exist"},
        "tool_error",
    ),
    (
        "scan_company_career_page",
        {"userId": "u-matrix-3", "companyId": "co-does-not-exist"},
        "tool_error",
    ),
    (
        "extract_direct_jobs_from_company_site",
        {
            "userId": "u-matrix-4",
            "companyId": "co-does-not-exist",
            "pageUrl": "https://example.invalid/careers",
            "html": "<html><body>no jobs</body></html>",
        },
        "tool_error",
    ),
    (
        "import_discovered_job",
        {"userId": "u-matrix-5", "discoveredJobId": "dj-does-not-exist"},
        "tool_error",
    ),
    (
        "deduplicate_discovered_jobs",
        {"userId": "u-matrix-6"},
        "ok",
    ),
    (
        "get_company_watchlist_summary",
        {"userId": "u-matrix-7"},
        "ok",
    ),
    (
        "get_user_profile_for_consent",
        {"userId": "u-matrix-8", "scopes": ["identity"]},
        "ok",
    ),
    (
        "propose_referral",
        {
            "userId": "u-matrix-9",
            "targetAgent": "housing-agent",
            "reason": "matrix test referral",
        },
        "ok",
    ),
    (
        "query_esco_skill",
        {"query": "Krankenpfleger"},
        "ok",
    ),
    (
        "export_eures_compatible",
        {"userId": "u-matrix-11", "discoveredJobId": "dj-does-not-exist"},
        "ok_or_tool_error",
    ),
    (
        "record_user_outcome",
        {"userId": "u-matrix-12", "jobId": "job-matrix-1", "outcomeType": "applied"},
        "ok",
    ),
    (
        "list_referrals",
        {"userId": "u-matrix-13"},
        "ok",
    ),
    (
        "update_referral_status",
        {"userId": "u-matrix-14", "referralId": "ref-does-not-exist", "status": "accepted"},
        "ok_or_tool_error",
    ),
]

# Per-tool missing-required: pick a representative required arg to omit.
# Tuples are (tool_name, kwargs_minus_one_required_field). The dispatcher
# returns status=invalid_arguments with violatedRule=required.
_MISSING_REQUIRED: list[tuple[str, dict[str, object]]] = [
    ("suggest_relevant_companies", {"industry": "healthcare"}),  # targetRoles missing
    ("add_company_to_watchlist", {"userId": "u-x", "name": "X"}),  # websiteUrl missing
    ("find_company_career_page", {"userId": "u-x"}),  # companyId missing
    ("scan_company_career_page", {"userId": "u-x"}),  # companyId missing
    (
        "extract_direct_jobs_from_company_site",
        {"userId": "u-x", "companyId": "c-x", "pageUrl": "https://example.invalid"},
    ),  # html missing
    ("import_discovered_job", {"userId": "u-x"}),  # discoveredJobId missing
    ("deduplicate_discovered_jobs", {}),  # userId missing
    ("get_company_watchlist_summary", {}),  # userId missing
    ("get_user_profile_for_consent", {"userId": "u-x"}),  # scopes missing
    (
        "propose_referral",
        {"userId": "u-x", "targetAgent": "housing-agent"},
    ),  # reason missing
    ("query_esco_skill", {}),  # query missing
    ("export_eures_compatible", {"userId": "u-x"}),  # discoveredJobId missing
    ("record_user_outcome", {"userId": "u-x", "jobId": "j-x"}),  # outcomeType missing
    ("list_referrals", {}),  # userId missing
    ("update_referral_status", {"userId": "u-x", "referralId": "r-x"}),  # status missing
]

# Per-tool wrong-type: pick a field with a well-defined non-object type
# and send the wrong shape. Returns invalid_arguments with violatedRule=type.
_WRONG_TYPE: list[tuple[str, dict[str, object]]] = [
    (
        "suggest_relevant_companies",
        {"targetRoles": "nurse", "industry": "healthcare"},  # targetRoles must be array
    ),
    (
        "add_company_to_watchlist",
        {
            "userId": 123,
            "name": "X",
            "websiteUrl": "https://example.invalid",
        },  # userId must be string
    ),
    (
        "find_company_career_page",
        {"userId": "u-x", "companyId": 42},  # companyId must be string
    ),
    (
        "scan_company_career_page",
        {"userId": "u-x", "companyId": "c-x", "careerPageUrl": 5},  # careerPageUrl must be string
    ),
    (
        "extract_direct_jobs_from_company_site",
        {
            "userId": "u-x",
            "companyId": "c-x",
            "pageUrl": "https://example.invalid",
            "html": 0,  # html must be string
        },
    ),
    (
        "import_discovered_job",
        {"userId": "u-x", "discoveredJobId": []},  # discoveredJobId must be string
    ),
    ("deduplicate_discovered_jobs", {"userId": True}),  # userId must be string
    ("get_company_watchlist_summary", {"userId": []}),
    (
        "get_user_profile_for_consent",
        {"userId": "u-x", "scopes": "identity"},  # scopes must be array
    ),
    (
        "propose_referral",
        {
            "userId": "u-x",
            "targetAgent": "housing-agent",
            "reason": "x",
            "context": "should-be-object",  # context must be object
        },
    ),
    ("query_esco_skill", {"query": "x", "type": "INVALID"}),  # type must be in enum
    ("export_eures_compatible", {"userId": "u-x", "discoveredJobId": 0}),
    (
        "record_user_outcome",
        {"userId": "u-x", "jobId": "j-x", "outcomeType": "ghosted"},  # outcomeType must be in enum
    ),
    (
        "list_referrals",
        {"userId": "u-x", "status": "INVALID"},  # status must be in enum
    ),
    (
        "update_referral_status",
        {"userId": "u-x", "referralId": "r-x", "status": "INVALID"},  # status must be in enum
    ),
]


class MCPPerToolMatrixE2E(unittest.TestCase):
    """One shared subprocess across the class. Each test does one
    schema-validation round-trip; the MCP server is stateless across
    distinct userIds so tests don't interfere."""

    harness: MCPHarness

    @classmethod
    def setUpClass(cls) -> None:
        cls.harness = MCPHarness().start()
        cls.harness.initialize()

    @classmethod
    def tearDownClass(cls) -> None:
        exit_code = cls.harness.close()
        if exit_code != 0:
            raise AssertionError(f"MCP server exited with code {exit_code}, expected 0")

    # ---------- happy-path round-trips for all 15 tools ----------

    def _assert_happy(self, tool_name: str, kwargs: dict[str, object], expected: str) -> None:
        response = self.harness.call_tool(tool_name, **kwargs)
        if expected == "ok":
            assert_ok(response)
        elif expected == "tool_error":
            payload, is_error = parse_tool_result(response)
            self.assertTrue(
                is_error,
                msg=f"{tool_name}: expected isError=True with empty repo, got payload={payload!r}",
            )
            self.assertEqual(payload["type"], "about:blank", msg=tool_name)
        elif expected == "ok_or_tool_error":
            # export_eures_compatible: implementation may surface 'not_found'
            # inside an ok payload OR as a tool_error. Either is acceptable as
            # a round-trip proof; both shapes are documented MCP contracts.
            payload, _ = parse_tool_result(response)
            self.assertIn(
                payload.get("status"),
                {"ok", "not_found", "tool_error"},
                msg=f"{tool_name}: unexpected status {payload.get('status')!r}",
            )
        else:
            raise AssertionError(f"unknown expected outcome {expected!r}")

    def test_01_happy_suggest_relevant_companies(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[0])

    def test_02_happy_add_company_to_watchlist(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[1])

    def test_03_happy_find_company_career_page(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[2])

    def test_04_happy_scan_company_career_page(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[3])

    def test_05_happy_extract_direct_jobs_from_company_site(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[4])

    def test_06_happy_import_discovered_job(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[5])

    def test_07_happy_deduplicate_discovered_jobs(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[6])

    def test_08_happy_get_company_watchlist_summary(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[7])

    def test_09_happy_get_user_profile_for_consent(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[8])

    def test_10_happy_propose_referral(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[9])

    def test_11_happy_query_esco_skill(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[10])

    def test_12_happy_export_eures_compatible(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[11])

    def test_13_happy_record_user_outcome(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[12])

    def test_14_happy_list_referrals(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[13])

    def test_15_happy_update_referral_status(self) -> None:
        self._assert_happy(*_HAPPY_INPUTS[14])

    # ---------- missing-required round-trips for all 15 tools ----------

    def _assert_missing_required(self, tool_name: str, kwargs: dict[str, object]) -> None:
        response = self.harness.call_tool(tool_name, **kwargs)
        payload = assert_tool_error(response, status="invalid_arguments")
        self.assertEqual(payload["instance"], tool_name)
        self.assertEqual(
            payload["violatedRule"],
            "required",
            msg=f"{tool_name}: expected violatedRule=required, got {payload!r}",
        )

    def test_20_missing_required_suggest_relevant_companies(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[0])

    def test_21_missing_required_add_company_to_watchlist(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[1])

    def test_22_missing_required_find_company_career_page(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[2])

    def test_23_missing_required_scan_company_career_page(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[3])

    def test_24_missing_required_extract_direct_jobs_from_company_site(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[4])

    def test_25_missing_required_import_discovered_job(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[5])

    def test_26_missing_required_deduplicate_discovered_jobs(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[6])

    def test_27_missing_required_get_company_watchlist_summary(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[7])

    def test_28_missing_required_get_user_profile_for_consent(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[8])

    def test_29_missing_required_propose_referral(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[9])

    def test_30_missing_required_query_esco_skill(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[10])

    def test_31_missing_required_export_eures_compatible(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[11])

    def test_32_missing_required_record_user_outcome(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[12])

    def test_33_missing_required_list_referrals(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[13])

    def test_34_missing_required_update_referral_status(self) -> None:
        self._assert_missing_required(*_MISSING_REQUIRED[14])

    # ---------- wrong-type round-trips for all 15 tools ----------

    def _assert_wrong_type(self, tool_name: str, kwargs: dict[str, object]) -> None:
        response = self.harness.call_tool(tool_name, **kwargs)
        payload = assert_tool_error(response, status="invalid_arguments")
        self.assertEqual(payload["instance"], tool_name)
        # Wrong-type rejections surface as violatedRule in {"type", "enum"}
        # depending on whether the field is a primitive type or a constrained
        # string. Both are JSON-Schema Draft-7 validation outcomes.
        self.assertIn(
            payload["violatedRule"],
            {"type", "enum"},
            msg=f"{tool_name}: expected violatedRule type|enum, got {payload!r}",
        )

    def test_40_wrong_type_suggest_relevant_companies(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[0])

    def test_41_wrong_type_add_company_to_watchlist(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[1])

    def test_42_wrong_type_find_company_career_page(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[2])

    def test_43_wrong_type_scan_company_career_page(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[3])

    def test_44_wrong_type_extract_direct_jobs_from_company_site(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[4])

    def test_45_wrong_type_import_discovered_job(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[5])

    def test_46_wrong_type_deduplicate_discovered_jobs(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[6])

    def test_47_wrong_type_get_company_watchlist_summary(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[7])

    def test_48_wrong_type_get_user_profile_for_consent(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[8])

    def test_49_wrong_type_propose_referral(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[9])

    def test_50_wrong_type_query_esco_skill(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[10])

    def test_51_wrong_type_export_eures_compatible(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[11])

    def test_52_wrong_type_record_user_outcome(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[12])

    def test_53_wrong_type_list_referrals(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[13])

    def test_54_wrong_type_update_referral_status(self) -> None:
        self._assert_wrong_type(*_WRONG_TYPE[14])

    # ---------- per-tool docstring sanity (catalogue completeness) ----------

    def test_60_every_tool_has_nonempty_description(self) -> None:
        tools = self.harness.list_tools()
        for tool in tools:
            with self.subTest(tool=tool["name"]):
                self.assertGreater(
                    len(tool.get("description", "").strip()),
                    20,
                    msg=f"{tool['name']}: description too short for an MCP catalogue entry",
                )

    def test_61_every_tool_inputschema_is_object_with_required_list(self) -> None:
        tools = self.harness.list_tools()
        for tool in tools:
            with self.subTest(tool=tool["name"]):
                schema = tool.get("inputSchema")
                self.assertIsInstance(schema, dict, msg=tool["name"])
                self.assertEqual(schema.get("type"), "object", msg=tool["name"])
                self.assertIn("required", schema, msg=tool["name"])
                self.assertIsInstance(schema["required"], list, msg=tool["name"])
                self.assertGreater(len(schema["required"]), 0, msg=tool["name"])


class MCPJSONRPCErrorEnvelopeE2E(unittest.TestCase):
    """JSON-RPC error envelope coverage (separate class so its tighter
    shutdown contract is independent of the per-tool matrix class)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.harness = MCPHarness().start()
        cls.harness.initialize()

    @classmethod
    def tearDownClass(cls) -> None:
        exit_code = cls.harness.close()
        if exit_code != 0:
            raise AssertionError(f"MCP server exited with code {exit_code}, expected 0")

    def test_01_unknown_method_returns_minus_32601(self) -> None:
        response = self.harness.raw("tools/nonexistent", {})
        err = assert_jsonrpc_error(response, code=-32601)
        self.assertIn("Unknown method", err.get("message", ""))

    def test_02_unknown_top_level_method_returns_minus_32601(self) -> None:
        """A method outside the MCP namespace must also be rejected with
        -32601 (not silently dropped or treated as a tool)."""

        response = self.harness.raw("some_random_method", {})
        assert_jsonrpc_error(response, code=-32601)

    def test_03_malformed_json_returns_minus_32700_parse_error(self) -> None:
        """RFC: invalid JSON received by the server -> -32700 parse error."""

        response = self.harness.send_raw_line("{not valid json")
        err = assert_jsonrpc_error(response, code=-32700)
        # JSON-RPC -32700 responses use id=null per spec when the request
        # couldn't be parsed.
        self.assertIsNone(response.get("id"))
        # Message body should reflect a parse failure mode.
        self.assertTrue(
            any(
                token in err.get("message", "").lower() for token in ("expect", "delimiter", "char")
            ),
            msg=f"unexpected parse-error message {err!r}",
        )

    def test_04_tools_call_with_unknown_tool_returns_tool_error_not_jsonrpc(self) -> None:
        """Unknown tool name is a tool-level error (RFC 7807 inside
        isError=True), NOT a JSON-RPC -32601. This is the documented MCP
        contract -- the JSON-RPC layer dispatched correctly, the tool
        layer is what rejected the request."""

        response = self.harness.call_tool("not_a_real_tool")
        payload = assert_tool_error(response, status="unknown_tool")
        self.assertEqual(payload["instance"], "not_a_real_tool")

    def test_05_tools_call_with_non_string_name_returns_invalid_arguments(self) -> None:
        """``params.name`` is required to be a string. A non-string name
        returns isError=True with status=invalid_arguments, not a
        JSON-RPC error."""

        response = self.harness.raw("tools/call", {"name": 42, "arguments": {}})
        payload = assert_tool_error(response, status="invalid_arguments")
        self.assertIn("string", payload["detail"].lower())


if __name__ == "__main__":
    unittest.main()
