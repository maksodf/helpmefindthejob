#!/usr/bin/env python3
# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Print the MCP tool catalogue. Used by the mcp-integration CI workflow."""

from company_discovery.mcp_tools import TOOL_SCHEMAS


def main() -> int:
    print(f"Catalogue tools: {len(TOOL_SCHEMAS)}")
    for tool in TOOL_SCHEMAS:
        print(f"  - {tool['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
