# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

from company_discovery.http_fetcher import HTTPFetcher
from company_discovery.mcp_tools import CompanyDiscoveryMCPTools, TOOL_SCHEMAS
from company_discovery.service import CompanyDiscoveryService, ScanConfig
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository


_TOOL_INDEX: dict[str, dict[str, Any]] = {tool["name"]: tool for tool in TOOL_SCHEMAS}


def _problem_document(
    *,
    tool_name: str,
    detail: str,
    validation_path: str = "",
    violated_rule: str = "",
) -> dict[str, Any]:
    """RFC 7807 Problem Details payload, embedded as the tool-call
    error content. MCP carries the payload inside the standard
    ``content[0].text`` channel with ``isError=True``."""

    return {
        "status": "invalid_arguments",
        "type": "about:blank",
        "title": "Tool arguments failed schema validation",
        "detail": detail,
        "instance": tool_name,
        "validationPath": validation_path,
        "violatedRule": violated_rule,
    }


def validate_tool_arguments(tool_name: str, arguments: Any) -> dict[str, Any] | None:
    """Return ``None`` on success, or an RFC 7807 problem document on
    failure. Validates ``arguments`` against the named tool's
    ``inputSchema`` from :data:`TOOL_SCHEMAS`. Unknown tools return a
    ``unknown_tool`` problem so the caller can short-circuit dispatch."""

    tool = _TOOL_INDEX.get(tool_name)
    if tool is None:
        return {
            "status": "unknown_tool",
            "type": "about:blank",
            "title": "Unknown tool",
            "detail": f"Tool {tool_name!r} is not in the published catalogue.",
            "instance": tool_name,
        }
    schema = tool.get("inputSchema") or {"type": "object"}
    if not isinstance(arguments, dict):
        return _problem_document(
            tool_name=tool_name,
            detail="arguments must be a JSON object.",
            validation_path="",
            violated_rule="type",
        )
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(arguments), key=lambda e: list(e.path))
    if not errors:
        return None
    first = errors[0]
    return _problem_document(
        tool_name=tool_name,
        detail=first.message,
        validation_path="/".join(str(p) for p in first.absolute_path) or "(root)",
        violated_rule=first.validator,
    )


ROOT = Path(__file__).parent
DATA_ROOT = Path(os.environ.get("COMPANY_DISCOVERY_DATA_DIR", str(ROOT / "data")))
DATA_PATH = DATA_ROOT / "company_discovery.sqlite3"


def jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def build_tools(data_path: Path = DATA_PATH) -> CompanyDiscoveryMCPTools:
    repository = SqliteCompanyDiscoveryRepository(data_path)
    service = CompanyDiscoveryService(
        repository,
        HTTPFetcher(),
        ScanConfig(max_pages_per_scan=5, request_delay_seconds=0.25),
    )
    return CompanyDiscoveryMCPTools(service)


def text_result(payload: dict[str, Any], is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(jsonable(payload), ensure_ascii=False)}],
        "isError": is_error,
    }


def rpc_response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def rpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def handle_request(message: dict[str, Any], tools: CompanyDiscoveryMCPTools) -> dict[str, Any] | None:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return rpc_response(
            message_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "company-discovery", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        )
    if method == "ping":
        return rpc_response(message_id, {})
    if method == "tools/list":
        return rpc_response(message_id, {"tools": TOOL_SCHEMAS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return rpc_response(
                message_id,
                text_result(
                    {
                        "status": "invalid_arguments",
                        "type": "about:blank",
                        "title": "Tool name missing or wrong type",
                        "detail": "params.name must be a string.",
                        "instance": "",
                    },
                    True,
                ),
            )
        problem = validate_tool_arguments(name, arguments)
        if problem is not None:
            return rpc_response(message_id, text_result(problem, True))
        if not hasattr(tools, name):
            return rpc_response(
                message_id,
                text_result(
                    {
                        "status": "unknown_tool",
                        "type": "about:blank",
                        "title": "Tool dispatch target missing",
                        "detail": f"No method named {name!r} on the tools object.",
                        "instance": name,
                    },
                    True,
                ),
            )
        try:
            result = getattr(tools, name)(**arguments)
        except Exception as error:  # noqa: BLE001 - tool boundary
            return rpc_response(
                message_id,
                text_result(
                    {
                        "status": "tool_error",
                        "type": "about:blank",
                        "title": "Tool raised an exception",
                        "detail": str(error),
                        "instance": name,
                    },
                    True,
                ),
            )
        return rpc_response(message_id, text_result(result))
    return rpc_error(message_id, -32601, f"Unknown method: {method}")


def run_stdio(tools: CompanyDiscoveryMCPTools | None = None) -> None:
    active_tools = tools or build_tools()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            response = rpc_error(None, -32700, str(error))
        else:
            response = handle_request(message, active_tools)
        if response is not None:
            sys.stdout.write(json.dumps(jsonable(response), ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio()
