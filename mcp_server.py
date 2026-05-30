# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

from company_discovery import audit_log
from company_discovery.env_compat import get_env
from company_discovery.http_fetcher import HTTPFetcher
from company_discovery.mcp_tools import TOOL_SCHEMAS, CompanyDiscoveryMCPTools
from company_discovery.service import CompanyDiscoveryService, ScanConfig
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository

# MCP protocol + server identity. Exposed as module-level constants
# so the HTTP catalogue endpoints in app.py (/mcp/version,
# /mcp/schemas.json) can report exactly the values the stdio
# JSON-RPC initialize response advertises — single source of truth.
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_NAME = "helpmefindthejob"
MCP_SERVER_VERSION = "0.1.0"

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
DATA_ROOT = Path(get_env("HELPMEFINDTHEJOB_DATA_DIR", str(ROOT / "data")))
DATA_PATH = DATA_ROOT / "company_discovery.sqlite3"

# Identity of the agent currently composing with this server, captured from
# ``clientInfo.name`` at ``initialize`` and attached to each tool call's
# Article-12 audit record as ``composition_source`` so the audit trail shows
# *which* civic agent drove each cross-agent call. stdio serves one client per
# process, so a module-level value is the correct lifetime here.
_COMPOSITION_SOURCE: str | None = None


def jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    # ``is_dataclass`` returns True for both dataclass instances and dataclass
    # classes; ``asdict`` only accepts instances. The class-object case is
    # narrowed away with ``not isinstance(value, type)``.
    if is_dataclass(value) and not isinstance(value, type):
        return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def build_tools(data_path: Path = DATA_PATH) -> CompanyDiscoveryMCPTools:
    repository = SqliteCompanyDiscoveryRepository(data_path)
    # CompanyDiscoveryService's signature historically declares StaticFetcher
    # for ergonomics with the test suite; HTTPFetcher satisfies the
    # duck-typed contract the service relies on (``.fetch(url) -> str``).
    # Tightening the service signature to a Protocol is a typing-debt
    # follow-up tracked outside this commit.
    service = CompanyDiscoveryService(
        repository,
        HTTPFetcher(),  # type: ignore[arg-type]
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


def handle_request(
    message: dict[str, Any], tools: CompanyDiscoveryMCPTools
) -> dict[str, Any] | None:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params")
    if not isinstance(params, dict):  # JSON-RPC positional (array) params, or junk
        params = {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        global _COMPOSITION_SOURCE
        client_info = params.get("clientInfo")
        client_name = client_info.get("name") if isinstance(client_info, dict) else None
        _COMPOSITION_SOURCE = (
            client_name.strip()[:120]
            if isinstance(client_name, str) and client_name.strip()
            else None
        )
        return rpc_response(
            message_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": MCP_SERVER_VERSION,
                },
                "capabilities": {"tools": {}},
            },
        )
    if method == "ping":
        return rpc_response(message_id, {})
    if method == "tools/list":
        return rpc_response(message_id, {"tools": TOOL_SCHEMAS})
    if method == "tools/call":
        return _handle_tools_call(message_id, params, tools)
    return rpc_error(message_id, -32601, f"Unknown method: {method}")


def _handle_tools_call(
    message_id: Any,
    params: dict[str, Any],
    tools: CompanyDiscoveryMCPTools,
) -> dict[str, Any]:
    """Dispatch a ``tools/call`` request and emit the AI Act Article 12
    ``mcp_tool_invocation`` audit-log event for every outcome (success,
    schema rejection, unknown tool, tool exception)."""
    name = params.get("name")
    arguments = params.get("arguments") or {}
    started = time.monotonic()
    outcome = "ok"
    error_class: str | None = None
    response: dict[str, Any] | None = None
    try:
        if not isinstance(name, str):
            outcome = "declined"
            error_class = "InvalidName"
            response = rpc_response(
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
            return response
        problem = validate_tool_arguments(name, arguments)
        if problem is not None:
            outcome = "declined"
            error_class = (
                "UnknownTool" if problem.get("status") == "unknown_tool" else "SchemaViolation"
            )
            response = rpc_response(message_id, text_result(problem, True))
            return response
        if not hasattr(tools, name):
            outcome = "declined"
            error_class = "UnknownTool"
            response = rpc_response(
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
            return response
        try:
            result = getattr(tools, name)(**arguments)
        except Exception as error:  # noqa: BLE001 - tool boundary
            outcome = "error"
            error_class = type(error).__name__
            response = rpc_response(
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
            return response
        response = rpc_response(message_id, text_result(result))
        return response
    finally:
        _emit_tool_call_audit(
            name=name if isinstance(name, str) else "<invalid>",
            arguments=arguments if isinstance(arguments, dict) else {},
            response=response,
            started=started,
            outcome=outcome,
            error_class=error_class,
        )


def _emit_tool_call_audit(
    *,
    name: str,
    arguments: dict[str, Any],
    response: dict[str, Any] | None,
    started: float,
    outcome: str,
    error_class: str | None,
) -> None:
    """Compose and emit the ``mcp_tool_invocation`` audit-log event.
    Never raises."""
    duration_ms = int((time.monotonic() - started) * 1000)
    try:
        emitter = audit_log.default_emitter()
        arg_payload = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        args_hash = emitter.short_hash(arg_payload)
        response_size_bytes = (
            len(json.dumps(response, ensure_ascii=False)) if response is not None else 0
        )
        audit_log.emit_mcp_tool_invocation(
            tool_name=name,
            arguments_hash=args_hash,
            response_size_bytes=response_size_bytes,
            composition_source=_COMPOSITION_SOURCE,
            duration_ms=duration_ms,
            outcome=outcome,
            error_class=error_class,
            emitter=emitter,
        )
    except Exception:  # noqa: BLE001, S110 - audit logging is best-effort; failure must never break the MCP server's user-facing dispatch
        # Audit logging never breaks the MCP server.
        pass


def _install_signal_handlers() -> None:
    """Install SIGTERM + SIGINT handlers that raise SystemExit so the
    ``run_stdio`` finally block runs (emits the `mcp_server_stopped`
    audit event + resets the caller context). Without this, SIGTERM
    (e.g. from `docker stop`) terminates the process immediately and
    skips the cleanup path.

    SIGINT already raises KeyboardInterrupt by default which unwinds
    finally, but we install an explicit handler for symmetry + so
    SystemExit code 0 is returned (not 130).
    """
    import signal

    def _shutdown(signum: int, _frame: object) -> None:
        # SystemExit causes Python to unwind try/finally blocks.
        raise SystemExit(0)

    try:
        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)
    except (ValueError, OSError):
        # Not on the main thread (or signal not supported on this
        # platform — e.g. some embedded contexts). Skip silently;
        # default behaviour still kicks in.
        pass


def run_stdio(tools: CompanyDiscoveryMCPTools | None = None) -> None:
    _install_signal_handlers()
    active_tools = tools or build_tools()
    ctx_token = audit_log.set_caller_context(caller="mcp")
    try:
        audit_log.emit_system_event(system_event_kind="mcp_server_started")
    except Exception:  # noqa: BLE001, S110 - server-started event is best-effort; never block startup on the audit log
        pass
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            response: dict[str, Any] | None
            try:
                message = json.loads(line)
            except json.JSONDecodeError as error:
                response = rpc_error(None, -32700, str(error))
            else:
                if not isinstance(message, dict):
                    response = rpc_error(
                        None, -32600, "Invalid Request: message must be a JSON object"
                    )
                else:
                    try:
                        response = handle_request(message, active_tools)
                    except Exception as error:  # noqa: BLE001 - one bad frame must never kill the loop
                        response = rpc_error(
                            message.get("id"), -32603, f"Internal error: {error}"
                        )
            if response is not None:
                sys.stdout.write(json.dumps(jsonable(response), ensure_ascii=False) + "\n")
                sys.stdout.flush()
    finally:
        try:
            audit_log.emit_system_event(system_event_kind="mcp_server_stopped")
        except Exception:  # noqa: BLE001, S110 - server-stopped event is best-effort; never block shutdown on the audit log
            pass
        audit_log.reset_caller_context(ctx_token)


if __name__ == "__main__":
    run_stdio()
