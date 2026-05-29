# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for MCP per-tool schema versioning.

Schema versioning —
each MCP tool advertises a semver; clients downgrade gracefully.

The v0.80.0 slice adds a per-tool `version` field to every entry
in `company_discovery.mcp_tools.TOOL_SCHEMAS`. Downstream MCP
clients reading via `tools/list` get the version inline with the
tool's name + description + inputSchema; clients targeting an
older catalogue version can pin per-tool versions in their config
and the server's verify-on-call layer can decide whether to
accept a call against a now-bumped tool schema.

This test pins three invariants:

1. Every tool entry has a `version` field.
2. Every `version` is a SemVer-shaped string (`MAJOR.MINOR.PATCH`).
3. The set of tool versions is exactly `{0.2.0}` at v0.80.0 — i.e.,
   future schema changes will bump individual tool versions away
   from the v0.2.0 baseline, and this test will surface the
   intentional drift.
"""

from __future__ import annotations

import re
import unittest

from company_discovery.mcp_tools import TOOL_SCHEMAS

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?$")


class ToolSchemaVersioning(unittest.TestCase):
    def test_every_tool_has_a_version(self) -> None:
        for tool in TOOL_SCHEMAS:
            with self.subTest(tool=tool.get("name")):
                self.assertIn(
                    "version",
                    tool,
                    f"tool {tool.get('name')!r} missing `version` field",
                )

    def test_every_version_is_semver(self) -> None:
        for tool in TOOL_SCHEMAS:
            with self.subTest(tool=tool.get("name")):
                v = tool.get("version", "")
                self.assertIsInstance(v, str, f"tool version not a string: {v!r}")
                self.assertRegex(
                    v,
                    SEMVER_RE,
                    f"tool {tool.get('name')!r} version {v!r} does not match SemVer "
                    "MAJOR.MINOR.PATCH[-prerelease] form",
                )

    def test_catalogue_baseline_at_v0_2_0(self) -> None:
        # At v0.80.0 every tool ships at v0.2.0 (the catalogue
        # baseline — the catalogue went from v0.1.0 to v0.2.0 with
        # the post-Phase-1 expansion). Future per-tool schema changes
        # will bump individual tool versions; when that happens, this
        # test is the place to record the bump — change the expected
        # set to include the new version + record the rationale in
        # the comment above. The test makes the bump visible to the
        # reviewer instead of letting it land silently.
        versions = {tool["version"] for tool in TOOL_SCHEMAS}
        self.assertEqual(
            versions,
            {"0.2.0"},
            f"expected every tool at v0.2.0 baseline; got {versions} — "
            "if this is an intentional bump, update the expected set",
        )

    def test_tool_count(self) -> None:
        # Locks the catalogue size; new tools should add to this test
        # explicitly so a reviewer notices the catalogue surface
        # expansion.
        self.assertEqual(
            len(TOOL_SCHEMAS),
            15,
            f"expected 15 tools in catalogue; got {len(TOOL_SCHEMAS)} — "
            "if you added/removed a tool, update this count + the "
            "13/15 tool catalogue narrative in docs/grant/09-mcp-composition.md",
        )


class ToolSchemaVersioningPreservesRequiredKeys(unittest.TestCase):
    """Adding the version field must not break the other required
    keys per the MCP protocol contract (name + description +
    inputSchema)."""

    def test_every_tool_has_name_description_inputSchema_and_version(self) -> None:
        required = {"name", "description", "inputSchema", "version"}
        for tool in TOOL_SCHEMAS:
            with self.subTest(tool=tool.get("name")):
                self.assertTrue(
                    required.issubset(tool.keys()),
                    f"tool {tool.get('name')!r} keys {tool.keys()} missing "
                    f"required {required - tool.keys()}",
                )


if __name__ == "__main__":
    unittest.main()
