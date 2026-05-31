# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for the MCP stdio-loop DoS bug.

A line that is valid JSON but not an object (`42`, `[1,2,3]`, `null`), or an
object whose `params`/`clientInfo` is an array, used to crash `handle_request`
with an AttributeError that propagated out of `run_stdio` and terminated the
whole stdio server — every subsequent request on the connection went unanswered.
The loop now validates the message is an object, coerces non-dict params, and
wraps dispatch so one bad frame can never kill the server.
"""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

import mcp_server


class HandleRequestGuardTests(unittest.TestCase):
    def test_array_params_do_not_crash(self) -> None:
        tools = mcp_server.build_tools()
        resp = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": ["positional"]}, tools
        )
        self.assertIsNotNone(resp)  # an error response, not an exception

    def test_list_client_info_does_not_crash(self) -> None:
        tools = mcp_server.build_tools()
        resp = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"clientInfo": ["bad"]}},
            tools,
        )
        self.assertIsNotNone(resp)


class StdioLoopSurvivalTests(unittest.TestCase):
    def test_malformed_frames_do_not_kill_the_loop(self) -> None:
        lines = [
            '{"jsonrpc":"2.0","id":1,"method":"ping"}',
            "42",  # valid JSON, not an object
            '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":["positional"]}',
            '{"jsonrpc":"2.0","id":4,"method":"initialize","params":{"clientInfo":["bad"]}}',
            '{"jsonrpc":"2.0","id":5,"method":"ping"}',
        ]
        out = io.StringIO()
        with (
            patch.object(mcp_server.sys, "stdin", io.StringIO("\n".join(lines) + "\n")),
            patch.object(mcp_server.sys, "stdout", out),
        ):
            mcp_server.run_stdio()
        answered = {
            json.loads(line).get("id") for line in out.getvalue().splitlines() if line.strip()
        }
        # The well-formed requests (1, 3, 4, 5) must all be answered — proving the
        # loop survived the non-object frame instead of dying on it.
        self.assertTrue({1, 3, 4, 5}.issubset(answered), f"loop died early; answered={answered}")


if __name__ == "__main__":
    unittest.main()
