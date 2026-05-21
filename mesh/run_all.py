# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Single-process launcher for all 3 mesh simulator agents.

Useful for local development and CI tests where spinning up
docker-compose would be heavier than necessary. Each agent
binds to its own port; this script starts all 3 in background
threads and blocks until SIGTERM / Ctrl-C.

Run:

    python -m mesh.run_all

Then in another shell:

    python -m mesh.demo_aicha_walk
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path

from mesh.anerkennung_agent import AGENT_NAME as ANERKENNUNG_NAME
from mesh.anerkennung_agent import make_handler as make_anerkennung_handler
from mesh.common import AgentAuditLog, serve_until_stopped
from mesh.housing_agent import AGENT_NAME as HOUSING_NAME
from mesh.housing_agent import make_handler as make_housing_handler
from mesh.social_services_agent import AGENT_NAME as SOCIAL_NAME
from mesh.social_services_agent import make_handler as make_social_handler


def main() -> int:
    parser = argparse.ArgumentParser(description="run all 3 mesh agents in one process")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--housing-port",
        type=int,
        default=int(os.environ.get("MESH_HOUSING_PORT", "8101")),
    )
    parser.add_argument(
        "--anerkennung-port",
        type=int,
        default=int(os.environ.get("MESH_ANERKENNUNG_PORT", "8102")),
    )
    parser.add_argument(
        "--social-port",
        type=int,
        default=int(os.environ.get("MESH_SOCIAL_PORT", "8103")),
    )
    parser.add_argument(
        "--audit-dir",
        default=os.environ.get("MESH_AUDIT_DIR", "data/mesh"),
    )
    args = parser.parse_args()

    audit_dir = Path(args.audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    servers = []
    for name, port, make_handler in (
        (HOUSING_NAME, args.housing_port, make_housing_handler),
        (ANERKENNUNG_NAME, args.anerkennung_port, make_anerkennung_handler),
        (SOCIAL_NAME, args.social_port, make_social_handler),
    ):
        audit = AgentAuditLog(audit_dir / f"{name}-audit.log")
        handler = make_handler(audit)
        server = serve_until_stopped(handler, args.host, port)
        servers.append((name, server))
        print(f"[{name}] listening on http://{args.host}:{port}", flush=True)

    print(f"\nAudit logs: {audit_dir}/", flush=True)
    print("Press Ctrl-C to stop all agents.", flush=True)

    stop = {"flag": False}

    def _handler(_signum: int, _frame) -> None:
        stop["flag"] = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    try:
        while not stop["flag"]:
            time.sleep(0.5)
    finally:
        for name, server in servers:
            server.shutdown()
            server.server_close()
            print(f"[{name}] stopped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
