# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Red-team runner — invoke via:
E2E_BASE_URL=https://app.directjob-scout.example python -m tests.e2e.red_team
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Make the red_team dir importable as a flat package — no
# __init__.py needed (the parent tests/e2e/__init__.py already
# exists; we want a flat module set inside red_team/).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_ROOT = _HERE.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents import ALL_AGENTS  # noqa: E402
from harness import (  # noqa: E402
    BASE_URL,
    RedTeamAgent,
    render_console_summary,
    write_report,
)


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2
    print(f"Red-team — target {BASE_URL}\n")
    reports = []
    for name, persona, fn in ALL_AGENTS:
        print(f"▶ {name} ({persona})…")
        agent = RedTeamAgent(name, persona)
        if not agent.register():
            reports.append(agent.finish())
            print("  ✗ register failed; skipping")
            time.sleep(1)
            continue
        try:
            fn(agent)
        except Exception as exc:  # noqa: BLE001 — log + continue
            agent.report.errored = True
            agent.report.error_text = repr(exc)
            agent.note("HIGH", "agent_crashed", repr(exc))
        # Post-run universal checks.
        agent.expect_no_500()
        agent.expect_no_leak()
        agent.expect_replies_nonempty()
        reports.append(agent.finish())
        crit = sum(1 for f in agent.report.findings if f.severity == "CRITICAL")
        hi = sum(1 for f in agent.report.findings if f.severity == "HIGH")
        print(
            f"  done · {len(agent.report.transcript)} turns · "
            f"{crit} CRIT / {hi} HIGH / "
            f"{len(agent.report.findings)} total findings"
        )
        # Brief pause to avoid hammering prod aggregators.
        time.sleep(0.8)
    out_path = Path(__file__).resolve().parent.parent / "red_team_report.md"
    write_report(reports, out_path)
    print(render_console_summary(reports))
    print(f"Report written: {out_path}")
    # Exit non-zero ONLY on CRITICAL findings (HIGH is reportable but
    # the operator decides whether to block release).
    total_critical = sum(sum(1 for f in r.findings if f.severity == "CRITICAL") for r in reports)
    return 1 if total_critical else 0


if __name__ == "__main__":
    sys.exit(main())
