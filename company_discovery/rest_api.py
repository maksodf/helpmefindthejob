# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Public REST API surface — thin wrapper over the MCP tool
catalogue (13-plan item 7/13; gap #28).

The MCP server exposes :data:`company_discovery.mcp_tools.
TOOL_SCHEMAS` for AI-agent consumers. Partners who want
plain-REST access (HTTP clients, no MCP protocol) need a
parallel surface. This module is that surface:

- **One endpoint per tool** at ``POST /api/v1/tools/<name>`` with
  the tool's input schema as the request body.
- **OpenAPI 3.0 spec** auto-generated from TOOL_SCHEMAS at
  ``GET /api/v1/openapi.json``.
- **Tool catalogue** at ``GET /api/v1/tools`` (same data
  TOOL_SCHEMAS carries, but JSON-renderable).

The wiring lives in app.py; this module is pure functions so
tests can exercise dispatch without booting an HTTP server.

Design choices:

- **Same input schema as MCP**: zero divergence between MCP +
  REST surfaces. A tool that takes ``{userId, companyId}`` in
  MCP takes the same body in REST.
- **CamelCase property names**: matches the existing TOOL_SCHEMAS
  + the MCP tool method signatures. REST clients used to snake_case
  can convert at the edges.
- **Errors as JSON**: every error response is a
  ``{"error": {"code": "...", "message": "..."}}`` shape. No
  HTML 500 pages.
- **No new state**: this module reads from TOOL_SCHEMAS +
  dispatches to CompanyDiscoveryMCPTools. The existing rate-limit,
  CSRF, and auth gates in app.py wrap it.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from .mcp_tools import TOOL_SCHEMAS

if TYPE_CHECKING:
    from .mcp_tools import CompanyDiscoveryMCPTools


# API version pinned in the URL prefix. Bump to v2 when we
# break input/output schemas; keep v1 around with the legacy
# behavior to give partners a deprecation window.
API_VERSION = "v1"


def list_tools_for_rest() -> list[dict[str, Any]]:
    """Return the tool catalogue in a JSON-renderable shape. The
    HTTP route returns this verbatim wrapped in ``{tools: [...]}``."""

    return [
        {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "inputSchema": tool.get("inputSchema", {"type": "object"}),
            "restPath": f"/api/{API_VERSION}/tools/{tool['name']}",
        }
        for tool in TOOL_SCHEMAS
    ]


def build_openapi_spec(*, base_url: str = "") -> dict[str, Any]:
    """Generate an OpenAPI 3.0 spec from TOOL_SCHEMAS. Pure
    function — no app state, no I/O. Easy to test + easy for a
    partner to fetch + feed into their OpenAPI client generator."""

    paths: dict[str, dict[str, Any]] = {}
    for tool in TOOL_SCHEMAS:
        tool_name = tool["name"]
        path = f"/api/{API_VERSION}/tools/{tool_name}"
        input_schema = tool.get("inputSchema") or {"type": "object"}
        paths[path] = {
            "post": {
                "summary": tool.get("description", ""),
                "operationId": tool_name,
                "tags": ["tools"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": input_schema,
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Successful tool execution",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid input (schema validation failed)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                            }
                        },
                    },
                    "401": {"description": "Authentication required"},
                    "404": {
                        "description": "Tool not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                            }
                        },
                    },
                    "500": {
                        "description": "Internal tool execution error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                            }
                        },
                    },
                },
            }
        }
    # Catalogue endpoint
    paths[f"/api/{API_VERSION}/tools"] = {
        "get": {
            "summary": "List all available tools.",
            "operationId": "list_tools",
            "tags": ["catalogue"],
            "responses": {
                "200": {
                    "description": "Tool catalogue",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        }
                    },
                }
            },
        }
    }
    spec: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Helpmefindthejob — Public REST API",
            "version": "1.0.0",
            "description": (
                "Plain-HTTP surface mirroring the MCP tool catalogue at "
                f"company_discovery.mcp_tools.TOOL_SCHEMAS. Every MCP tool "
                f"is also available as POST /api/{API_VERSION}/tools/<name>."
            ),
            "license": {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0",
            },
        },
        "paths": paths,
        "components": {
            "schemas": {
                "Error": {
                    "type": "object",
                    "required": ["error"],
                    "properties": {
                        "error": {
                            "type": "object",
                            "required": ["code", "message"],
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                            },
                        }
                    },
                }
            },
            "securitySchemes": {
                "sessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session",
                    "description": (
                        "Session cookie issued by the /api/auth/login "
                        "endpoint. Same auth surface as the SPA."
                    ),
                }
            },
        },
        "security": [{"sessionCookie": []}],
    }
    if base_url:
        spec["servers"] = [{"url": base_url}]
    return spec


def _validate_required_fields(payload: dict[str, Any], required: list[str]) -> list[str]:
    """Return the list of required fields missing from payload.
    Empty list means valid."""

    return [field for field in required if field not in payload]


class ToolNotFoundError(KeyError):
    """Raised when dispatch_tool_call is given an unknown name."""


class ToolValidationError(ValueError):
    """Raised when payload fails schema validation (required-
    fields check). The HTTP layer maps this to 400."""


def dispatch_tool_call(
    tool_name: str,
    payload: dict[str, Any],
    tools: CompanyDiscoveryMCPTools,
    *,
    inject_user_id: str | None = None,
) -> Any:
    """Look up ``tool_name`` in TOOL_SCHEMAS, validate ``payload``
    against the tool's required fields, dispatch to the matching
    method on ``tools``, and return the result.

    If ``inject_user_id`` is set, it's set onto ``payload["userId"]``
    BEFORE dispatch — this is how the HTTP route injects the
    authenticated session user without trusting client-supplied
    user IDs.

    Raises:
        ToolNotFoundError — unknown tool_name (caller maps to 404)
        ToolValidationError — required field missing (caller maps to 400)
        Anything the tool method raises — caller maps to 500
    """

    tool_spec = next((t for t in TOOL_SCHEMAS if t["name"] == tool_name), None)
    if tool_spec is None:
        raise ToolNotFoundError(tool_name)

    # Resolve the method on the tools instance. The TOOL_SCHEMAS
    # name uses snake_case (e.g., "add_company_to_watchlist") and
    # the method follows the same convention.
    method = getattr(tools, tool_name, None)
    if method is None or not callable(method):
        raise ToolNotFoundError(tool_name)

    # Inject the authenticated user id BEFORE validation so a
    # request that omits userId (relying on the server to fill it)
    # still passes required-fields check.
    if inject_user_id and "userId" in tool_spec.get("inputSchema", {}).get("properties", {}):
        payload = {**payload, "userId": inject_user_id}

    required = tool_spec.get("inputSchema", {}).get("required", [])
    missing = _validate_required_fields(payload, required)
    if missing:
        raise ToolValidationError(f"missing_required_fields:{','.join(sorted(missing))}")

    # Filter payload to only kwargs the method accepts so an
    # over-eager client doesn't get a TypeError. Inspect the
    # method's signature.
    try:
        sig = inspect.signature(method)
        accepted = set(sig.parameters.keys())
        # `**payload` style — accept everything (e.g.,
        # add_company_to_watchlist uses **payload)
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
    except (TypeError, ValueError):
        accepts_kwargs = True
        accepted = set()

    if accepts_kwargs:
        filtered_payload = payload
    else:
        filtered_payload = {k: v for k, v in payload.items() if k in accepted}

    return method(**filtered_payload)
