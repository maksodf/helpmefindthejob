# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Thin Python MCP client harness for end-to-end composability work.

Wraps ``mcp_server.py`` as a subprocess and exchanges JSON-RPC messages
over stdio -- the same transport Claude Desktop, Cursor, Cline, and the
2.5 housing-agent reference integration use. Importable from any test
module; runnable as a script for a one-shot smoke check::

    python tests/e2e/mcp_client_harness.py

Designed for PART 7 (MCP composability with real client). Loops 21-23
layer on top: per-tool regression matrix, the two composability flows
(Aicha discovery+letters and Krankenschwester ESCO+EURES), and the
Claude Desktop manual-walk evidence path.

Why a separate harness rather than reusing test_phase12 directly: that
test asserts protocol-level invariants (handshake, schema, RFC 7807,
shutdown). The harness extracts the *transport mechanics* so other
modules can compose tool calls without re-implementing subprocess +
stdio bookkeeping.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_SERVER = REPO_ROOT / "mcp_server.py"

# Deterministic 32-byte test salt. The MCP server's audit-log emitter
# lazy-initialises in dev mode and raises a UserWarning when
# HELPMEFINDTHEJOB_AUDIT_SALT is absent; subprocesses don't inherit the
# tests/__init__.py setdefault because unittest.discover doesn't import
# the test package when test_phase12-style E2E runs detached.
_TEST_AUDIT_SALT = base64.b64encode(b"\x00" * 32).decode("ascii")


class MCPHarnessError(RuntimeError):
    """Raised when the MCP server subprocess returns no response, the
    pipe breaks mid-call, or the response is shaped wrong. Carries
    server stderr tail so test failures are diagnosable."""


class MCPHarness:
    """Spawn ``mcp_server.py`` and exchange JSON-RPC messages over stdio.

    Designed as a context manager::

        with MCPHarness() as harness:
            harness.initialize()
            tools = harness.list_tools()
            response = harness.call_tool("query_esco_skill", query="Krankenpfleger")
            payload = assert_ok(response)

    Each instance owns its own temp data dir (unless ``data_dir`` is
    supplied). Use one instance per logical scenario for isolation;
    composability flows that need to chain tool calls (e.g. discover ->
    scan -> import -> consent) share an instance across calls.
    """

    def __init__(
        self,
        *,
        data_dir: Path | str | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> None:
        self._owns_tempdir = data_dir is None
        if self._owns_tempdir:
            self._tmp: tempfile.TemporaryDirectory[str] | None = tempfile.TemporaryDirectory()
            self._data_dir = Path(self._tmp.name)
        else:
            self._tmp = None
            self._data_dir = Path(data_dir)
            self._data_dir.mkdir(parents=True, exist_ok=True)
        self._env_overrides = dict(env_overrides or {})
        self._proc: subprocess.Popen[str] | None = None
        self._next_id = 0

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def start(self) -> "MCPHarness":
        if self._proc is not None:
            raise MCPHarnessError("harness already started")
        env = os.environ.copy()
        env["HELPMEFINDTHEJOB_DATA_DIR"] = str(self._data_dir)
        env.setdefault("HELPMEFINDTHEJOB_AUDIT_SALT", _TEST_AUDIT_SALT)
        env.update(self._env_overrides)
        self._proc = subprocess.Popen(
            [sys.executable, str(MCP_SERVER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        return self

    def close(self) -> int:
        if self._proc is None:
            return 0
        try:
            try:
                if self._proc.stdin is not None:
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                exit_code = self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                exit_code = self._proc.wait(timeout=5)
        finally:
            for stream in (self._proc.stdout, self._proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            if self._owns_tempdir and self._tmp is not None:
                self._tmp.cleanup()
        self._proc = None
        return exit_code

    def __enter__(self) -> "MCPHarness":
        return self.start()

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def raw(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC request and return the raw decoded response.
        Escape hatch for callers that need to drive non-standard methods
        (e.g. ``notifications/initialized``) or inspect the JSON-RPC
        error envelope."""

        if self._proc is None:
            raise MCPHarnessError(
                "harness not started; call start() or use the context manager"
            )
        self._next_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params or {},
        }
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        try:
            self._proc.stdin.write(json.dumps(message) + "\n")
            self._proc.stdin.flush()
        except BrokenPipeError as error:
            raise MCPHarnessError(
                f"MCP server pipe broken during {method!r} -- server may have crashed.\n"
                f"stderr tail:\n{self._read_stderr_tail()}"
            ) from error
        line = self._proc.stdout.readline()
        if not line:
            raise MCPHarnessError(
                f"MCP server returned no response for {method!r} -- server may have exited.\n"
                f"stderr tail:\n{self._read_stderr_tail()}"
            )
        return json.loads(line)

    def _read_stderr_tail(self, max_bytes: int = 4000) -> str:
        if self._proc is None or self._proc.stderr is None:
            return "<no stderr available>"
        try:
            tail = self._proc.stderr.read()
            return tail[-max_bytes:] if tail else "<empty>"
        except Exception:
            return "<failed to read stderr>"

    def initialize(self) -> dict[str, Any]:
        """Send the MCP ``initialize`` handshake and return the result
        object (protocolVersion / serverInfo / capabilities)."""

        return self.raw("initialize", {})["result"]

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the published tool catalogue (list of tool schema dicts)."""

        return self.raw("tools/list", {})["result"]["tools"]

    def call_tool(self, tool_name: str, **arguments: Any) -> dict[str, Any]:
        """Invoke a tool. Returns the raw JSON-RPC response so callers
        can inspect both successful payloads (via :func:`parse_tool_result`)
        and JSON-RPC error envelopes (via ``response['error']``)."""

        return self.raw(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )


def parse_tool_result(response: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Decode an MCP ``tools/call`` response into ``(payload, is_error)``.

    ``payload`` is the JSON-decoded body of ``content[0].text``;
    ``is_error`` is the MCP-protocol ``isError`` flag.

    Raises :class:`MCPHarnessError` if the response is a JSON-RPC error
    envelope (``response['error']``) -- those should be handled
    separately, not parsed as tool results.
    """

    if "error" in response:
        err = response["error"]
        raise MCPHarnessError(
            f"JSON-RPC error envelope; not a tool result. "
            f"code={err.get('code')!r} message={err.get('message')!r}"
        )
    result = response.get("result")
    if not isinstance(result, dict):
        raise MCPHarnessError(
            f"response missing dict 'result'; got {type(result).__name__}"
        )
    is_error = bool(result.get("isError", False))
    content = result.get("content") or []
    if not content or "text" not in content[0]:
        raise MCPHarnessError("response result has no content[0].text payload")
    payload = json.loads(content[0]["text"])
    return payload, is_error


def assert_ok(response: dict[str, Any]) -> dict[str, Any]:
    """Assert a tools/call succeeded (``isError=False`` and
    ``payload['status']`` is ``ok``). Returns the payload for chaining."""

    payload, is_error = parse_tool_result(response)
    if is_error:
        raise AssertionError(f"expected ok, got isError=True payload={payload!r}")
    status = payload.get("status")
    if status != "ok":
        raise AssertionError(
            f"expected payload.status='ok', got {status!r} payload={payload!r}"
        )
    return payload


def assert_tool_error(
    response: dict[str, Any], *, status: str | None = None
) -> dict[str, Any]:
    """Assert a tools/call surfaced a tool-level error
    (``isError=True``). Optionally check ``payload['status']``. Returns
    the payload."""

    payload, is_error = parse_tool_result(response)
    if not is_error:
        raise AssertionError(
            f"expected isError=True, got isError=False payload={payload!r}"
        )
    if status is not None and payload.get("status") != status:
        raise AssertionError(
            f"expected payload.status={status!r}, got {payload.get('status')!r} "
            f"payload={payload!r}"
        )
    return payload


def assert_jsonrpc_error(response: dict[str, Any], *, code: int | None = None) -> dict[str, Any]:
    """Assert the response is a JSON-RPC error envelope. Optionally
    check the JSON-RPC error code (e.g. ``-32601`` for unknown method,
    ``-32700`` for parse error). Returns the error dict."""

    if "error" not in response:
        raise AssertionError(f"expected JSON-RPC error envelope, got {response!r}")
    err = response["error"]
    if code is not None and err.get("code") != code:
        raise AssertionError(
            f"expected JSON-RPC error code={code!r}, got {err.get('code')!r} error={err!r}"
        )
    return err


def _smoke() -> int:
    """Standalone smoke check: server starts, tools/list returns 13
    tools, one happy-path tool call (query_esco_skill -> Krankenpfleger)
    round-trips. Exit code 0 on success, 1 on assertion failure."""

    print("[mcp-harness-smoke] booting server subprocess")
    with MCPHarness() as harness:
        info = harness.initialize()
        protocol_version = info.get("protocolVersion")
        server_name = info.get("serverInfo", {}).get("name")
        assert protocol_version == "2024-11-05", (
            f"expected protocolVersion '2024-11-05', got {protocol_version!r}"
        )
        assert server_name == "helpmefindthejob", (
            f"expected serverInfo.name 'helpmefindthejob', got {server_name!r}"
        )
        print(f"  initialize ok -- protocolVersion={protocol_version!r} server={server_name!r}")

        tools = harness.list_tools()
        assert len(tools) == 13, f"expected 13 tools, got {len(tools)}"
        print(f"  tools/list ok -- {len(tools)} tools registered")
        for tool in sorted(tools, key=lambda t: t["name"]):
            print(f"    - {tool['name']}")

        response = harness.call_tool("query_esco_skill", query="Krankenpfleger")
        payload = assert_ok(response)
        match_labels = [m.get("label_de", "") for m in payload.get("matches", [])]
        assert any("Krankenpfleger" in label for label in match_labels), (
            f"expected at least one Krankenpfleger match, got {match_labels}"
        )
        print(
            f"  tools/call query_esco_skill ok -- "
            f"{payload.get('totalCandidates', 0)} candidates, "
            f"{len(payload.get('matches', []))} matches"
        )

    print("[mcp-harness-smoke] PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_smoke())
    except AssertionError as exc:
        print(f"[mcp-harness-smoke] FAIL -- {exc}", file=sys.stderr)
        raise SystemExit(1)
    except MCPHarnessError as exc:
        print(f"[mcp-harness-smoke] FAIL -- {exc}", file=sys.stderr)
        raise SystemExit(1)
