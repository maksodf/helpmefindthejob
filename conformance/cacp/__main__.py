# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""``python -m conformance.cacp`` — run the CACP v0.1 conformance suite."""

from __future__ import annotations

import argparse
import json

from conformance.cacp.harness import run_conformance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="conformance.cacp",
        description="Run the CACP v0.1 conformance suite against the reference MCP server.",
    )
    parser.add_argument("--json", action="store_true", help="emit the machine-readable JSON report")
    args = parser.parse_args(argv)

    report = run_conformance()
    print(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        if args.json
        else report.summary()
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
