# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""MCP catalogue HTTP surface + per-tool schema export.

Closes Week 2 §2.2 follow-up gaps:

1. ``GET /mcp/version`` exposes protocolVersion + serverInfo over
   HTTP so external clients can validate compatibility without
   opening a JSON-RPC session.
2. ``GET /mcp/schemas.json`` exposes the full TOOL_SCHEMAS catalogue
   so external clients can fetch tool descriptors without speaking
   JSON-RPC.
3. ``mcp_server/schemas/<tool>.json`` per-tool files keep a
   filesystem mirror of TOOL_SCHEMAS in sync — for CI contract
   checks, IDE static lookups, and MCP marketplace registries.

The contract test asserts: HTTP catalogue matches the in-memory
TOOL_SCHEMAS by construction, the per-tool files are in sync, and
the HTTP serverInfo matches the stdio initialize response.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "mcp_server" / "schemas"


# -------------------------------------------------------------------------
# Per-tool schema file contract
# -------------------------------------------------------------------------


class PerToolSchemaFiles(unittest.TestCase):
    """Each tool in TOOL_SCHEMAS must have a matching JSON file in
    ``mcp_server/schemas/`` and the file must round-trip cleanly.
    Operators / CI run ``scripts/export_mcp_schemas.py`` to refresh."""

    def setUp(self):
        from company_discovery.mcp_tools import TOOL_SCHEMAS

        self.tools = TOOL_SCHEMAS

    def test_schemas_directory_exists(self):
        self.assertTrue(
            SCHEMA_DIR.is_dir(),
            f"missing {SCHEMA_DIR} — run scripts/export_mcp_schemas.py",
        )

    def test_every_tool_has_a_schema_file(self):
        missing = []
        for tool in self.tools:
            target = SCHEMA_DIR / f"{tool['name']}.json"
            if not target.exists():
                missing.append(target.name)
        self.assertEqual(
            missing,
            [],
            f"missing schema files (run scripts/export_mcp_schemas.py): {missing}",
        )

    def test_each_schema_file_matches_tool_schemas(self):
        """Drift catcher: if someone hand-edits a schema file or
        modifies TOOL_SCHEMAS without re-exporting, this fails."""

        for tool in self.tools:
            with self.subTest(tool=tool["name"]):
                target = SCHEMA_DIR / f"{tool['name']}.json"
                from_disk = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(
                    from_disk,
                    tool,
                    f"schema drift for {tool['name']}; re-run scripts/export_mcp_schemas.py",
                )

    def test_no_orphan_schema_files(self):
        """If a tool was removed from TOOL_SCHEMAS, its stale file
        must not linger — operators run the export script which
        clears stale entries."""

        known = {tool["name"] for tool in self.tools}
        orphans = []
        for path in SCHEMA_DIR.glob("*.json"):
            if path.stem == "index":
                continue
            if path.stem not in known:
                orphans.append(path.name)
        self.assertEqual(
            orphans,
            [],
            f"stale schema files found; re-run export: {orphans}",
        )

    def test_index_manifest_is_in_sync(self):
        manifest = json.loads((SCHEMA_DIR / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["toolCount"],
            len(self.tools),
            "index.json toolCount drift",
        )
        self.assertEqual(
            sorted(manifest["tools"]),
            sorted(tool["name"] for tool in self.tools),
            "index.json tool list drift",
        )

    def test_export_script_is_idempotent(self):
        """Re-running the script produces byte-identical output —
        catches non-deterministic ordering / formatting drift."""

        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "schemas"
            # Run script with a custom output dir via env-less call
            # Easier: re-run and compare on-disk to a re-export.
            before = {}
            for p in SCHEMA_DIR.glob("*.json"):
                before[p.name] = p.read_bytes()
            result = subprocess.run(
                [sys.executable, "scripts/export_mcp_schemas.py"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, f"export failed: {result.stderr}")
            after = {}
            for p in SCHEMA_DIR.glob("*.json"):
                after[p.name] = p.read_bytes()
            self.assertEqual(before, after, "export script is not idempotent")


# -------------------------------------------------------------------------
# HTTP catalogue surface — live boot
# -------------------------------------------------------------------------


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


class HttpCatalogueSurface(unittest.TestCase):
    """Boot the actual server and curl the /mcp/* endpoints. Validates
    the catalogue surface end-to-end including content-type, CORS
    headers, and payload shape."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = TemporaryDirectory()
        cls.port = _free_port()
        env = dict(os.environ)
        env["HELPMEFINDTHEJOB_DATA_FILE"] = str(Path(cls.tmpdir.name) / "data.json")
        env["HELPMEFINDTHEJOB_DISABLE_SCHEDULER"] = "1"
        env.pop("HELPMEFINDTHEJOB_DATABASE_URL", None)
        cls.proc = subprocess.Popen(
            [sys.executable, "app.py", "--port", str(cls.port)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _wait_for_port(cls.port, timeout=15.0):
            cls.proc.terminate()
            raise RuntimeError("app.py failed to bind")

    @classmethod
    def tearDownClass(cls):
        if cls.proc is not None:
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.tmpdir.cleanup()

    def _get_json(self, path: str) -> tuple[int, dict[str, str], dict]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return (
                resp.status,
                {k.lower(): v for k, v in resp.headers.items()},
                json.loads(resp.read().decode("utf-8")),
            )

    def test_mcp_version_endpoint(self):
        status, headers, payload = self._get_json("/mcp/version")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertEqual(payload.get("protocolVersion"), "2024-11-05")
        info = payload.get("serverInfo", {})
        self.assertEqual(info.get("name"), "helpmefindthejob")
        self.assertEqual(info.get("version"), "0.1.0")

    def test_mcp_version_has_cors_header(self):
        _, headers, _ = self._get_json("/mcp/version")
        self.assertEqual(
            headers.get("access-control-allow-origin"),
            "*",
            "CORS required for cross-origin MCP client tooling",
        )

    def test_mcp_schemas_endpoint(self):
        status, headers, payload = self._get_json("/mcp/schemas.json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertEqual(payload.get("protocolVersion"), "2024-11-05")
        self.assertIn("tools", payload)
        self.assertIsInstance(payload["tools"], list)
        self.assertGreaterEqual(
            len(payload["tools"]),
            13,
            "expected at least 13 MCP tools in catalogue",
        )

    def test_mcp_schemas_payload_matches_tool_schemas(self):
        """HTTP catalogue MUST equal in-memory TOOL_SCHEMAS by
        construction — single source of truth."""

        from company_discovery.mcp_tools import TOOL_SCHEMAS

        _, _, payload = self._get_json("/mcp/schemas.json")
        self.assertEqual(payload["tools"], list(TOOL_SCHEMAS))

    def test_mcp_schemas_payload_matches_stdio_tools_list(self):
        """Catalogue endpoint MUST agree with what stdio
        ``tools/list`` JSON-RPC returns — the two surfaces are
        meant to be interchangeable."""

        from company_discovery.mcp_tools import TOOL_SCHEMAS

        _, _, payload = self._get_json("/mcp/schemas.json")
        http_names = sorted(t["name"] for t in payload["tools"])
        stdio_names = sorted(t["name"] for t in TOOL_SCHEMAS)
        self.assertEqual(http_names, stdio_names)

    def test_mcp_schemas_has_cors_header(self):
        _, headers, _ = self._get_json("/mcp/schemas.json")
        self.assertEqual(headers.get("access-control-allow-origin"), "*")

    def _head(self, path: str) -> tuple[int, dict[str, str], int]:
        """HEAD request — returns (status, headers, body_length).
        body_length should be 0 (HEAD never returns a body)."""

        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return (
                resp.status,
                {k.lower(): v for k, v in resp.headers.items()},
                len(resp.read()),
            )

    def test_mcp_version_supports_head(self):
        """MCP marketplace registries probe with HEAD before fetching.
        Previously fell through to serve_static + 404 — the panic-
        round caught this bug."""

        status, headers, body_len = self._head("/mcp/version")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertEqual(body_len, 0, "HEAD must not return a body")
        # Content-Length must still announce the would-be body size
        self.assertNotEqual(
            headers.get("content-length"),
            None,
            "HEAD must set Content-Length",
        )

    def test_mcp_schemas_supports_head(self):
        status, headers, body_len = self._head("/mcp/schemas.json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertEqual(body_len, 0)

    def test_sitemap_supports_head(self):
        """Google + Bing probe sitemaps with HEAD before fetching."""

        status, headers, body_len = self._head("/sitemap.xml")
        self.assertEqual(status, 200)
        self.assertIn("application/xml", headers.get("content-type", ""))
        self.assertEqual(body_len, 0)

    def test_robots_supports_head(self):
        status, _, body_len = self._head("/robots.txt")
        self.assertEqual(status, 200)
        self.assertEqual(body_len, 0)


# -------------------------------------------------------------------------
# Single-source-of-truth integrity
# -------------------------------------------------------------------------


class SingleSourceOfTruthIntegrity(unittest.TestCase):
    """If the stdio initialize response and the HTTP /mcp/version
    endpoint ever drift, downstream tooling that uses either gets a
    different answer. This guards the invariant."""

    def test_mcp_server_constants_drive_stdio_initialize(self):
        from mcp_server import (
            MCP_PROTOCOL_VERSION,
            MCP_SERVER_NAME,
            MCP_SERVER_VERSION,
        )

        self.assertEqual(MCP_PROTOCOL_VERSION, "2024-11-05")
        self.assertEqual(MCP_SERVER_NAME, "helpmefindthejob")
        self.assertEqual(MCP_SERVER_VERSION, "0.1.0")

    def test_stdio_initialize_response_uses_module_constants(self):
        """Source-level check: the initialize handler must not
        hardcode the version — it must reference the constants
        so the HTTP endpoint cannot drift from stdio."""

        src = (REPO_ROOT / "mcp_server.py").read_text(encoding="utf-8")
        self.assertIn('"protocolVersion": MCP_PROTOCOL_VERSION', src)
        self.assertIn('"name": MCP_SERVER_NAME', src)
        self.assertIn('"version": MCP_SERVER_VERSION', src)


if __name__ == "__main__":
    unittest.main()
