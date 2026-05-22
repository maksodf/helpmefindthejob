#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Export every MCP tool schema to its own JSON file.

Writes ``mcp_server/schemas/<tool-name>.json`` for each entry in
``company_discovery.mcp_tools.TOOL_SCHEMAS`` plus a manifest
``mcp_server/schemas/index.json`` listing the tools + server identity.

Why: the canonical schemas live in Python (``TOOL_SCHEMAS``) and the
stdio server exposes them via ``tools/list``. The HTTP catalogue
endpoint ``/mcp/schemas.json`` (added Week 2 follow-up) covers
in-process consumers. The per-tool filesystem mirror is the
build-artefact form that downstream tooling can consume without
running the server:

- CI contract checks (validate a downstream client against the schema
  for a single tool without parsing the whole catalogue)
- MCP marketplace registries that index per-tool docs
- Static IDE schema lookups (Cursor, JetBrains, VS Code extensions)

The contract test in ``tests/test_mcp_schema_export.py`` keeps the
on-disk files in sync with TOOL_SCHEMAS so they cannot silently
drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / "mcp_server" / "schemas"
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(repo_root))
    from company_discovery.mcp_tools import TOOL_SCHEMAS
    from mcp_server import (
        MCP_PROTOCOL_VERSION,
        MCP_SERVER_NAME,
        MCP_SERVER_VERSION,
    )

    # Wipe stale per-tool files so a deleted tool doesn't linger
    for stale in out_dir.glob("*.json"):
        stale.unlink()

    written: list[str] = []
    for tool in TOOL_SCHEMAS:
        name = tool["name"]
        target = out_dir / f"{name}.json"
        target.write_text(
            json.dumps(tool, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(name)
        print(f"wrote {target.relative_to(repo_root)}")

    manifest = {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "serverInfo": {
            "name": MCP_SERVER_NAME,
            "version": MCP_SERVER_VERSION,
        },
        "toolCount": len(written),
        "tools": written,
    }
    manifest_path = out_dir / "index.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {manifest_path.relative_to(repo_root)} ({len(written)} tools)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
