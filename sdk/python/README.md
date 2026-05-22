<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# helpmefindthejob — Python SDK

Stdlib-only client for the Helpmefindthejob REST API. Vendor the
`helpmefindthejob_sdk/` directory directly into your project — no
pip install required, no third-party dependencies, no
transitive supply chain.

## Install

```bash
# From this repo
cp -r sdk/python/helpmefindthejob_sdk /path/to/your/project/

# Or as a tar
tar -czf helpmefindthejob_sdk.tar.gz -C sdk/python helpmefindthejob_sdk/
```

## Quickstart

```python
from helpmefindthejob_sdk import Client

client = Client(
    base_url="https://app.helpmefindthejob.org",
    session_cookie="<value-from-/api/auth/login>",
    csrf_token="<value-from-/api/auth/login>",
)

# Discover the catalogue
tools = client.list_tools()
for tool in tools:
    print(tool["name"], "→", tool["restPath"])

# Call any tool by name
result = client.call_tool(
    "suggest_relevant_companies",
    {"targetRoles": ["Pflegekraft"], "industry": "Healthcare"},
)

# Or use the typed Pythonic wrappers
result = client.suggest_relevant_companies(
    target_roles=["Pflegekraft"],
    industry="Healthcare",
)
```

## Error handling

```python
from helpmefindthejob_sdk import (
    AuthRequiredError,
    ToolNotFoundError,
    ToolValidationError,
)

try:
    result = client.call_tool("suggest_relevant_companies", {})
except ToolValidationError as exc:
    # The server told us which required fields are missing.
    print("Validation:", exc)
except AuthRequiredError:
    # Session cookie expired — re-login.
    print("Re-login required")
except ToolNotFoundError:
    # Tool name not in catalogue.
    print("Unknown tool")
```

## Versioning

The SDK pins to API version `v1`. When the server ships `v2` with
breaking changes, this SDK will continue to work against the
`v1` endpoints — both versions are kept alive for a deprecation
window. A future `helpmefindthejob_sdk_v2` package will mirror
the new surface.

## Discovery for other languages

The server publishes an OpenAPI 3.0 spec at
`/api/v1/openapi.json`. Feed it to:

- **TypeScript**: `openapi-typescript` for typed fetch clients
- **Go**: `oapi-codegen` for typed clients + server stubs
- **Java/Kotlin**: `openapi-generator` for typed clients
- **Rust**: `openapi-generator` or `progenitor`

The Python SDK in this directory is a hand-written reference
implementation; the OpenAPI spec is the cross-language
source of truth.

## License

Apache 2.0 (same as the rest of the project).
