# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Minimal stdio JSON-RPC MCP client + server-session helpers.

This is the single canonical MCP-over-stdio client in the repo: the CACP
conformance harness uses it to talk to a candidate server, and the housing
reference agent (``examples/housing-stub-client/main.py``) re-imports
``StdioMCPClient`` from here so there is one client implementation, not two.

Only the Python standard library is used, so the conformance tooling has the
same minimal dependency surface as ``mcp_server.py`` itself.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import TracebackType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_SERVER = REPO_ROOT / "mcp_server.py"


class StdioMCPClient:
    """Bare-bones synchronous JSON-RPC over stdio MCP client.

    A real composing agent would use a library; this implementation is
    deliberately compact so a reader can see the entire protocol surface in one
    file.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc
        self._next_id = 0

    def _write(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message) + "\n"
        self._proc.stdin.write(payload.encode("utf-8"))
        self._proc.stdin.flush()

    def _read(self) -> dict[str, Any]:
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout unexpectedly")
        return json.loads(line.decode("utf-8"))

    def _next(self) -> int:
        self._next_id += 1
        return self._next_id

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        message = {
            "jsonrpc": "2.0",
            "id": self._next(),
            "method": method,
            "params": params or {},
        }
        self._write(message)
        return self._read()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return the parsed JSON payload the tool emitted
        (unwrapping the MCP ``content`` envelope)."""

        response = self.call("tools/call", {"name": name, "arguments": arguments})
        result = response.get("result") or {}
        for block in result.get("content") or []:
            if block.get("type") == "text":
                try:
                    return json.loads(block.get("text", "{}"))
                except json.JSONDecodeError:
                    return {}
        return {}

    def call_tool_raw(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Like :meth:`call_tool` but return the full JSON-RPC response (so a
        caller can inspect ``isError`` / the content envelope)."""
        return self.call("tools/call", {"name": name, "arguments": arguments})

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self._write(message)


def spawn_server(
    data_dir: Path | str,
    *,
    audit_salt_b64: str | None = None,
    disable_network: bool = True,
    server_path: Path | None = None,
) -> subprocess.Popen:
    """Launch an MCP server as a stdio subprocess.

    ``data_dir`` holds the SQLite store (profiles + referrals) and the
    HMAC-chained audit log. Pass ``audit_salt_b64`` (base64 of 32 bytes) so the
    caller can later verify the audit chain with the same salt.
    """
    env = dict(os.environ)
    env["HELPMEFINDTHEJOB_DATA_DIR"] = str(data_dir)
    env["HELPMEFINDTHEJOB_DATA_ROOT"] = str(data_dir)
    if audit_salt_b64 is not None:
        env["HELPMEFINDTHEJOB_AUDIT_SALT"] = audit_salt_b64
    if disable_network:
        env.setdefault("HELPMEFINDTHEJOB_DISABLE_NETWORK", "1")
    return subprocess.Popen(
        [sys.executable, str(server_path or MCP_SERVER)],
        cwd=str(REPO_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )


class MCPSession:
    """Context manager: spawn an MCP server, complete the handshake, yield a
    connected :class:`StdioMCPClient`, and shut the server down on exit.

    ``client_name`` becomes the ``clientInfo.name`` the server records as the
    ``composition_source`` on every audit record — i.e. the composing agent's
    identity in the audit trail.
    """

    def __init__(
        self,
        data_dir: Path | str,
        *,
        client_name: str = "cacp-conformance",
        audit_salt_b64: str | None = None,
        disable_network: bool = True,
        server_path: Path | None = None,
        protocol_version: str = "2024-11-05",
    ) -> None:
        self._data_dir = data_dir
        self._client_name = client_name
        self._audit_salt_b64 = audit_salt_b64
        self._disable_network = disable_network
        self._server_path = server_path
        self._protocol_version = protocol_version
        self._proc: subprocess.Popen | None = None
        self.initialize_result: dict[str, Any] = {}

    def __enter__(self) -> StdioMCPClient:
        self._proc = spawn_server(
            self._data_dir,
            audit_salt_b64=self._audit_salt_b64,
            disable_network=self._disable_network,
            server_path=self._server_path,
        )
        client = StdioMCPClient(self._proc)
        response = client.call(
            "initialize",
            {
                "protocolVersion": self._protocol_version,
                "clientInfo": {"name": self._client_name, "version": "1.0.0"},
                "capabilities": {},
            },
        )
        self.initialize_result = response.get("result") or {}
        client.notify("notifications/initialized")
        return client

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=2)
