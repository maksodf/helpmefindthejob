# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 3 (CACP) — the published civic-profile JSON Schema is the data
contract, and the live ``get_user_profile_for_consent`` output cannot drift
from it.

Three guarantees:
1. ``static/.well-known/civic-profile.schema.json`` is a valid Draft 2020-12
   schema.
2. The live consent-tool output (all scopes, populated + unknown-user) VALIDATES
   against it.
3. Completeness: every field the code actually emits is DESCRIBED in the schema
   (a new code field that the schema doesn't document fails this test) — so the
   published contract stays honest as the code evolves.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import jsonschema

import mcp_server
from company_discovery.models import UserProfile

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "static" / ".well-known" / "civic-profile.schema.json"

ALL_SCOPES = ["identity", "residence", "employment", "cv", "outcomes", "preferences"]

# Blocks that are fixed-field objects (subject to the completeness check).
# ``languageLevels`` / ``counts`` are open maps (additionalProperties), so their
# dynamic keys are intentionally not enumerated in the schema.
_FIXED_FIELD_BLOCKS = ("identity", "residence", "employment", "cv", "preferences")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _populated_profile() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="cacp-profile-")) / "c.sqlite3"
    tools = mcp_server.build_tools(data_path=tmp)
    tools.service.repository.save_user_profile(
        UserProfile(
            user_id="u1",
            target_roles=["Krankenpfleger"],
            languages=["German (B1)"],
            locale="de",
            location="Berlin",
            cv_text="x",
        )
    )
    tools.record_user_outcome(userId="u1", jobId="j1", outcomeType="applied")
    return tools.get_user_profile_for_consent(userId="u1", scopes=ALL_SCOPES)["profile"]


class CivicProfileSchemaIsValid(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        schema = _schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        # Raises SchemaError if the schema itself is malformed.
        jsonschema.Draft202012Validator.check_schema(schema)


class LiveOutputValidatesAgainstSchema(unittest.TestCase):
    def test_populated_profile_validates(self):
        jsonschema.Draft202012Validator(_schema()).validate(_populated_profile())

    def test_unknown_user_placeholder_validates(self):
        tmp = Path(tempfile.mkdtemp(prefix="cacp-profile-")) / "c.sqlite3"
        tools = mcp_server.build_tools(data_path=tmp)
        profile = tools.get_user_profile_for_consent(userId="nobody", scopes=ALL_SCOPES)["profile"]
        jsonschema.Draft202012Validator(_schema()).validate(profile)

    def test_single_scope_subset_validates(self):
        tmp = Path(tempfile.mkdtemp(prefix="cacp-profile-")) / "c.sqlite3"
        tools = mcp_server.build_tools(data_path=tmp)
        profile = tools.get_user_profile_for_consent(userId="u1", scopes=["employment"])["profile"]
        jsonschema.Draft202012Validator(_schema()).validate(profile)


class SchemaDocumentsEveryEmittedField(unittest.TestCase):
    """The published contract must describe every field the code emits."""

    def setUp(self):
        self.schema = _schema()
        self.profile = _populated_profile()

    def _assert_documented(self, keys, described, where):
        undocumented = sorted(k for k in keys if k not in described)
        self.assertEqual(
            undocumented,
            [],
            f"{where}: code emits undocumented field(s) {undocumented} — "
            "update static/.well-known/civic-profile.schema.json to match.",
        )

    def test_top_level_fields_documented(self):
        self._assert_documented(self.profile.keys(), self.schema["properties"], "profile")

    def test_fixed_field_blocks_documented(self):
        for block in _FIXED_FIELD_BLOCKS:
            described = self.schema["properties"][block]["properties"]
            self._assert_documented(self.profile[block].keys(), described, f"profile.{block}")

    def test_outcomes_block_documented(self):
        outcomes_schema = self.schema["properties"]["outcomes"]["properties"]
        self._assert_documented(self.profile["outcomes"].keys(), outcomes_schema, "profile.outcomes")
        event_props = outcomes_schema["events"]["items"]["properties"]
        for event in self.profile["outcomes"]["events"]:
            self._assert_documented(event.keys(), event_props, "profile.outcomes.events[]")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class CivicProfileSchemaServedOverHttp(unittest.TestCase):
    """The schema is genuinely PUBLISHED at /.well-known/civic-profile.schema.json
    as application/json — proven by a real HTTP GET against the running app, not
    just by the file existing on disk."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_DATA_DIR": cls._tmp.name,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "A" * 43 + "=",
        }
        cls._proc = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "app.py"), "--port", str(cls.port)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(60):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=0.5)
                conn.request("GET", "/api/health")
                resp = conn.getresponse()
                healthy = resp.status == 200
                resp.read()
                conn.close()
                if healthy:
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"server did not become healthy on port {cls.port}")

    @classmethod
    def tearDownClass(cls):
        if cls._proc.poll() is None:
            cls._proc.terminate()
            try:
                cls._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls._proc.kill()
                cls._proc.wait()
        for stream in (cls._proc.stdout, cls._proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:  # noqa: BLE001
                    pass
        cls._tmp.cleanup()

    def test_schema_served_as_application_json_and_validates_live_output(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request("GET", "/.well-known/civic-profile.schema.json")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        content_type = resp.getheader("Content-Type") or ""
        conn.close()

        self.assertEqual(resp.status, 200, "civic-profile schema is not served over HTTP")
        self.assertIn("application/json", content_type)
        served = json.loads(body)
        self.assertEqual(
            served["$id"],
            "https://helpmefindthejob.org/.well-known/civic-profile.schema.json",
        )
        # The schema a third party would actually fetch must validate real output.
        jsonschema.Draft202012Validator(served).validate(_populated_profile())


if __name__ == "__main__":
    unittest.main()
