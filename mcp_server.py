from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from company_discovery.http_fetcher import HTTPFetcher
from company_discovery.mcp_tools import CompanyDiscoveryMCPTools, TOOL_SCHEMAS
from company_discovery.service import CompanyDiscoveryService, ScanConfig
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository


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
        if not isinstance(name, str) or not hasattr(tools, name):
            return rpc_response(message_id, text_result({"status": "error", "error": "unknown_tool"}, True))
        try:
            result = getattr(tools, name)(**arguments)
        except Exception as error:  # noqa: BLE001 - tool boundary
            return rpc_response(message_id, text_result({"status": "error", "error": str(error)}, True))
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
