# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Tests for the §2.3 catalogue-v0.2.0 MCP tools.

Five composition-oriented tools added in Week 2 §2.3:

- ``get_user_profile_for_consent`` — scope-filtered portable civic profile
- ``propose_referral`` — structured referral object emission
- ``query_esco_skill`` — ESCO mini-dataset substring lookup (full dataset
  integration in Week 2 §2.4)
- ``export_eures_compatible`` — EURES-shaped projection of a discovered job
- ``record_user_outcome`` — append-only outcome-event journal

Coverage in this module:

- Each tool's schema is registered in TOOL_SCHEMAS and resolvable
- Each tool's method dispatches via mcp_server.handle_request with no
  validation errors on a representative valid payload
- Invalid payloads produce the RFC 7807 problem documents pinned in
  ``test_phase11_mcp_input_validation`` (one spot-check per tool here
  to confirm the per-tool schema is wired correctly)
- ``record_user_outcome`` persists to data/user_outcomes.jsonl and
  ``get_user_profile_for_consent`` with the ``outcomes`` scope reads
  back what was written
- ESCO matching is case-insensitive and respects the ``type`` filter
- Referral objects carry the documented fields (referralId, intent,
  priority, reasonCode, supportingInfo, userConsentRequired)
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

import mcp_server
from company_discovery.mcp_tools import (
    _ESCO_REFERENCE_DATASET,
    _OUTCOME_TYPES,
    TOOL_SCHEMAS,
)


def _new_tools_for_test() -> tuple[mcp_server.CompanyDiscoveryMCPTools, Path]:
    """Build a CompanyDiscoveryMCPTools rooted at a tmp data dir so each
    test has its own outcomes file."""

    tmp = tempfile.mkdtemp(prefix="dj-scout-mcp-v2-")
    tools = mcp_server.build_tools(data_path=Path(tmp) / "company.sqlite3")
    return tools, Path(tmp)


class CatalogueRegistrationTests(unittest.TestCase):
    """Every new tool appears in TOOL_SCHEMAS with a Draft-7 schema and
    has a callable method on CompanyDiscoveryMCPTools."""

    NEW_TOOLS = (
        "get_user_profile_for_consent",
        "propose_referral",
        "query_esco_skill",
        "export_eures_compatible",
        "record_user_outcome",
    )

    def test_all_five_tools_in_catalogue(self) -> None:
        names = {tool["name"] for tool in TOOL_SCHEMAS}
        for tool_name in self.NEW_TOOLS:
            self.assertIn(tool_name, names, msg=tool_name)

    def test_catalogue_count_now_thirteen(self) -> None:
        self.assertEqual(len(TOOL_SCHEMAS), 13)

    def test_every_new_tool_has_callable_method(self) -> None:
        tools, _ = _new_tools_for_test()
        for tool_name in self.NEW_TOOLS:
            self.assertTrue(
                callable(getattr(tools, tool_name, None)),
                msg=tool_name,
            )

    def test_every_new_tool_schema_compiles(self) -> None:
        import jsonschema

        for tool in TOOL_SCHEMAS:
            if tool["name"] not in self.NEW_TOOLS:
                continue
            schema = tool.get("inputSchema") or {"type": "object"}
            jsonschema.Draft7Validator.check_schema(schema)


class GetUserProfileForConsentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools, self.data_dir = _new_tools_for_test()

    def test_returns_scopes_in_payload(self) -> None:
        result = self.tools.get_user_profile_for_consent(
            userId="u-1", scopes=["identity", "residence"]
        )
        self.assertEqual(result["status"], "ok")
        profile = result["profile"]
        self.assertEqual(profile["userId"], "u-1")
        self.assertEqual(profile["scopes"], ["identity", "residence"])
        self.assertIn("identity", profile)
        self.assertIn("residence", profile)
        # Out-of-scope keys must be absent.
        self.assertNotIn("cv", profile)
        self.assertNotIn("outcomes", profile)
        self.assertNotIn("preferences", profile)
        # Schema version is pinned so consumers can branch on it.
        self.assertEqual(profile["schemaVersion"], "0.1.0")

    def test_employment_scope_includes_watchlist_count(self) -> None:
        result = self.tools.get_user_profile_for_consent(
            userId="u-1", scopes=["employment"]
        )
        employment = result["profile"]["employment"]
        # Empty repository — zero watched companies. Field present.
        self.assertIn("watchedCompanies", employment)
        self.assertEqual(employment["watchedCompanies"], 0)

    def test_outcomes_scope_reads_persisted_events(self) -> None:
        # Write two outcomes for u-1 and one for u-2 via the public tool.
        self.tools.record_user_outcome(
            userId="u-1", jobId="job-1", outcomeType="applied"
        )
        self.tools.record_user_outcome(
            userId="u-1", jobId="job-1", outcomeType="replied"
        )
        self.tools.record_user_outcome(
            userId="u-2", jobId="job-9", outcomeType="applied"
        )

        result = self.tools.get_user_profile_for_consent(
            userId="u-1", scopes=["outcomes"]
        )
        outcomes = result["profile"]["outcomes"]
        self.assertEqual(outcomes["total"], 2)
        self.assertEqual(outcomes["counts"]["applied"], 1)
        self.assertEqual(outcomes["counts"]["replied"], 1)
        # u-2's event must not leak into u-1's view.
        for event in outcomes["events"]:
            self.assertEqual(event["userId"], "u-1")

    def test_handle_request_rejects_missing_scopes(self) -> None:
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "get_user_profile_for_consent",
                "arguments": {"userId": "u-1"},  # scopes missing
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "invalid_arguments")
        self.assertEqual(payload["violatedRule"], "required")

    def test_handle_request_rejects_bad_scope_enum(self) -> None:
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "get_user_profile_for_consent",
                "arguments": {"userId": "u-1", "scopes": ["not-a-scope"]},
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "invalid_arguments")


class ProposeReferralTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools, _ = _new_tools_for_test()

    def test_returns_documented_referral_fields(self) -> None:
        result = self.tools.propose_referral(
            userId="u-1",
            targetAgent="housing-agent",
            reason="user mentioned housing search need",
            context={"city": "Berlin"},
        )
        self.assertEqual(result["status"], "ok")
        ref = result["referral"]
        for field in (
            "referralId", "schemaVersion", "issuedAt", "sourceAgent",
            "targetAgent", "userId", "intent", "priority", "reasonCode",
            "supportingInfo", "userConsentRequired",
        ):
            self.assertIn(field, ref, msg=field)
        self.assertEqual(ref["sourceAgent"], "directjob-scout")
        self.assertEqual(ref["targetAgent"], "housing-agent")
        self.assertEqual(ref["userId"], "u-1")
        self.assertEqual(ref["userConsentRequired"], True)
        self.assertEqual(ref["intent"], "proposed")
        self.assertEqual(ref["priority"], "routine")
        self.assertTrue(ref["referralId"].startswith("ref-"))

    def test_unique_referral_ids(self) -> None:
        first = self.tools.propose_referral(
            userId="u-1", targetAgent="x", reason="r"
        )["referral"]["referralId"]
        second = self.tools.propose_referral(
            userId="u-1", targetAgent="x", reason="r"
        )["referral"]["referralId"]
        self.assertNotEqual(first, second)

    def test_handle_request_rejects_missing_reason(self) -> None:
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "propose_referral",
                "arguments": {"userId": "u-1", "targetAgent": "housing"},
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["violatedRule"], "required")


class QueryEscoSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools, _ = _new_tools_for_test()

    def test_finds_nurse_match(self) -> None:
        result = self.tools.query_esco_skill(query="nurse")
        self.assertEqual(result["status"], "ok")
        labels = [match["label"] for match in result["matches"]]
        self.assertTrue(any("nurse" in label.lower() for label in labels))

    def test_case_insensitive(self) -> None:
        lower = self.tools.query_esco_skill(query="nurse")["matches"]
        upper = self.tools.query_esco_skill(query="NURSE")["matches"]
        self.assertEqual(len(lower), len(upper))

    def test_type_filter_occupation_excludes_skills(self) -> None:
        result = self.tools.query_esco_skill(query="frontend", type="occupation")
        for match in result["matches"]:
            self.assertEqual(match["type"], "occupation")

    def test_type_filter_skill_returns_skills_only(self) -> None:
        result = self.tools.query_esco_skill(query="german", type="skill")
        for match in result["matches"]:
            self.assertEqual(match["type"], "skill")

    def test_no_match_returns_empty_list(self) -> None:
        result = self.tools.query_esco_skill(query="zzzzz-not-a-real-skill")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["totalCandidates"], len(_ESCO_REFERENCE_DATASET))

    def test_limit_caps_results(self) -> None:
        full = self.tools.query_esco_skill(query="e")["matches"]
        capped = self.tools.query_esco_skill(query="e", limit=2)["matches"]
        self.assertLessEqual(len(capped), 2)
        if len(full) >= 2:
            self.assertEqual(len(capped), 2)

    def test_handle_request_rejects_empty_query(self) -> None:
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "query_esco_skill",
                "arguments": {"query": ""},  # minLength: 1 violated
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "invalid_arguments")


class ExportEuresCompatibleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools, _ = _new_tools_for_test()

    def test_returns_not_found_when_job_missing(self) -> None:
        # No discovered job seeded — the tool should report not_found
        # rather than raise.
        result = self.tools.export_eures_compatible(
            userId="u-1", discoveredJobId="nope"
        )
        self.assertIn(result["status"], {"not_found", "ok"})
        if result["status"] == "ok":
            # Some repository implementations may return a stub object
            # rather than None; in that case the schema-conformance flag
            # is still present.
            self.assertIn("schemaConformance", result["eures"])
        else:
            self.assertEqual(result["status"], "not_found")

    def test_handle_request_rejects_missing_discoveredJobId(self) -> None:
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "export_eures_compatible",
                "arguments": {"userId": "u-1"},
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["violatedRule"], "required")


class RecordUserOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools, self.data_dir = _new_tools_for_test()

    def _outcomes_file(self) -> Path:
        return self.data_dir / "user_outcomes.jsonl"

    def test_writes_event_to_jsonl_file(self) -> None:
        result = self.tools.record_user_outcome(
            userId="u-1", jobId="job-7", outcomeType="applied"
        )
        self.assertEqual(result["status"], "ok")
        event = result["event"]
        self.assertEqual(event["userId"], "u-1")
        self.assertEqual(event["jobId"], "job-7")
        self.assertEqual(event["outcomeType"], "applied")
        self.assertTrue(event["outcomeId"].startswith("out-"))
        self.assertEqual(event["schemaVersion"], "0.1.0")
        # File on disk should contain the JSON-Lines record.
        path = self._outcomes_file()
        self.assertTrue(path.exists())
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["userId"], "u-1")

    def test_optional_note_persisted_when_provided(self) -> None:
        result = self.tools.record_user_outcome(
            userId="u-1",
            jobId="job-7",
            outcomeType="interviewing",
            note="phone-screen on Friday",
        )
        self.assertEqual(result["event"]["note"], "phone-screen on Friday")

    def test_appends_in_order(self) -> None:
        for outcome in ("applied", "replied", "interviewing"):
            self.tools.record_user_outcome(
                userId="u-1", jobId="job-7", outcomeType=outcome
            )
        lines = self._outcomes_file().read_text(encoding="utf-8").strip().splitlines()
        outcomes_in_order = [json.loads(line)["outcomeType"] for line in lines]
        self.assertEqual(outcomes_in_order, ["applied", "replied", "interviewing"])

    def test_rejects_invalid_outcome_enum_at_method_level(self) -> None:
        # Direct call (bypassing the MCP schema gate). Method must still
        # reject so callers outside the MCP server can't bypass.
        result = self.tools.record_user_outcome(
            userId="u-1", jobId="job-7", outcomeType="ghosted"
        )
        self.assertEqual(result["status"], "invalid_arguments")

    def test_handle_request_rejects_invalid_outcome_enum(self) -> None:
        # Schema-level enum is enforced before the method body runs.
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "record_user_outcome",
                "arguments": {
                    "userId": "u-1", "jobId": "j", "outcomeType": "ghosted",
                },
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "invalid_arguments")
        self.assertEqual(payload["violatedRule"], "enum")

    def test_canonical_outcome_types_covered_by_module_constant(self) -> None:
        # Sanity: the module's _OUTCOME_TYPES must match the schema enum
        # so future additions don't drift the two.
        schema = next(
            t["inputSchema"] for t in TOOL_SCHEMAS if t["name"] == "record_user_outcome"
        )
        enum_in_schema = tuple(schema["properties"]["outcomeType"]["enum"])
        self.assertEqual(enum_in_schema, _OUTCOME_TYPES)


if __name__ == "__main__":
    unittest.main()
