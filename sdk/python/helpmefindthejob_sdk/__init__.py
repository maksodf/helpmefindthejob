# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Helpmefindthejob Python SDK — partner client (13-plan item
8/13; gap #29).

Thin client over the public REST API at /api/v1. Stdlib-only;
no requests, no httpx, no third-party deps so partners can
vendor this file directly.

Quickstart::

    from helpmefindthejob_sdk import Client

    client = Client(
        base_url="https://app.helpmefindthejob.org",
        session_cookie="<session-value>",
    )

    # Call any tool by name (typed errors on failure)
    result = client.call_tool(
        "suggest_relevant_companies",
        {"targetRoles": ["Pflegekraft"], "industry": "Healthcare"},
    )

    # Or use the typed wrappers for the most common tools
    result = client.suggest_relevant_companies(
        target_roles=["Pflegekraft"],
        industry="Healthcare",
    )

    # Discover the full tool catalogue dynamically
    tools = client.list_tools()
    for tool in tools:
        print(tool["name"], "→", tool["restPath"])

The SDK mirrors the surface defined in
``company_discovery/rest_api.py`` exactly. Partners running
against a deployment running this version of the project get
the same shape as the production-tested test suite.
"""

from .client import (
    AuthRequiredError,
    Client,
    HelpmefindthejobError,
    ToolNotFoundError,
    ToolValidationError,
)

__all__ = [
    "Client",
    "HelpmefindthejobError",
    "AuthRequiredError",
    "ToolNotFoundError",
    "ToolValidationError",
]

__version__ = "0.1.0"
