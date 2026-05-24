#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Housing-stub-client — a runnable demonstration of MCP composition.

Spawns the Helpmefindthejob MCP server as a stdio subprocess, walks
through the two main composition modes documented in
``docs/grant/09-mcp-composition.md``, and prints a narrated trace so
a reader can see exactly what each step looks like on the wire.

This is the **mock stub** per Decision 20 — it stands in for a real
housing-agent collaborator until one is confirmed. The protocol
surface it exercises is real; only the housing-side logic is
simulated.

Run it from the repository root::

    python examples/housing-stub-client/main.py

No external services are needed. Total runtime: ~3 seconds.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Narration helpers
# ---------------------------------------------------------------------------


def banner(text: str) -> None:
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


def step(text: str) -> None:
    print()
    print(f"-- {text}")


def show(label: str, payload: Any) -> None:
    print(f"   {label}:")
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    for line in rendered.splitlines():
        print(f"     {line}")


# ---------------------------------------------------------------------------
# Minimal stdio MCP client
# ---------------------------------------------------------------------------


class StdioMCPClient:
    """Bare-bones synchronous JSON-RPC over stdio MCP client.

    A real housing-agent would use a library; this implementation is
    deliberately compact so a reader can see the entire protocol
    surface in one file.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc
        self._next_id = 0

    def _write(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message) + "\n"
        self._proc.stdin.write(payload.encode("utf-8"))
        self._proc.stdin.flush()

    def _read(self) -> dict[str, Any]:
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout unexpectedly")
        return json.loads(line.decode("utf-8"))

    def _next(self) -> int:
        self._next_id += 1
        return self._next_id

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        message = {
            "jsonrpc": "2.0",
            "id": self._next(),
            "method": method,
            "params": params or {},
        }
        self._write(message)
        return self._read()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self._write(message)


# ---------------------------------------------------------------------------
# Housing-agent stub
# ---------------------------------------------------------------------------


class HousingAgentStub:
    """A simulated housing-search agent.

    Carries enough state to drive Mode 1 (sequential handoff) and
    Mode 2 (profile-shared composition). The housing logic itself is
    a printout — the point of the demo is the MCP composition, not
    the housing-search algorithm.
    """

    LISTINGS = [
        {
            "id": "listing-001",
            "city": "Berlin",
            "rent_eur": 850,
            "requires_proof_of_employment": True,
            "deposit_months": 3,
        },
        {
            "id": "listing-002",
            "city": "Berlin",
            "rent_eur": 620,
            "requires_proof_of_employment": False,
            "deposit_months": 2,
        },
        {
            "id": "listing-003",
            "city": "Berlin",
            "rent_eur": 1100,
            "requires_proof_of_employment": True,
            "deposit_months": 3,
        },
    ]

    def __init__(self, mcp: StdioMCPClient, user_id: str) -> None:
        self._mcp = mcp
        self._user_id = user_id

    # --- Mode 1 --------------------------------------------------------

    def request_employment_referral(self) -> dict[str, Any]:
        """User asked about housing but mentioned they have no
        Anschreiben yet. The housing agent can't help with that —
        it calls Helpmefindthejob's `propose_referral` to construct
        a referral the user can then opt into."""

        response = self._mcp.call(
            "tools/call",
            {
                "name": "propose_referral",
                "arguments": {
                    "userId": self._user_id,
                    "targetAgent": "helpmefindthejob",
                    "reason": (
                        "User asked about housing but said they have no "
                        "Anschreiben yet — they need employment-application "
                        "help, which is outside our scope."
                    ),
                    "context": {
                        "userMessage": (
                            "Ich suche eine Wohnung in Berlin, aber ich habe "
                            "noch kein Anschreiben für meine Bewerbungen."
                        ),
                        "domain": "employment",
                    },
                },
            },
        )
        return response

    # --- Mode 2 --------------------------------------------------------

    def fetch_employment_profile(self) -> dict[str, Any]:
        """User has consented to share their employment status. The
        housing agent calls `get_user_profile_for_consent` with the
        single `employment` scope (privacy by least-privilege)."""

        response = self._mcp.call(
            "tools/call",
            {
                "name": "get_user_profile_for_consent",
                "arguments": {
                    "userId": self._user_id,
                    "scopes": ["employment"],
                },
            },
        )
        return response

    def filter_listings_by_profile(self, profile_payload: Any) -> list[dict[str, Any]]:
        """Apply the housing-side filtering logic. The point isn't
        that this filter is sophisticated — it's that the housing
        agent took an employment-context input and used it to make
        a domain-appropriate recommendation."""

        # Read the user's employment situation. The Helpmefindthejob
        # profile schema names this field `currentStatus`; a missing
        # or null value falls back to "unknown".
        employment_status = "unknown"
        if isinstance(profile_payload, dict):
            outer = profile_payload.get("profile") or profile_payload
            employment_block = outer.get("employment") or {}
            current = employment_block.get("currentStatus")
            if current:
                employment_status = current

        # Filter heuristic: if the user reports trial-period or
        # job-seeking, exclude listings that require proof of
        # full-time employment. Unknown counts as unstable for
        # least-harm defaults (don't recommend listings the user
        # cannot apply for).
        unstable_states = {"job_seeking", "trial_period", "unemployed", "unknown"}
        if employment_status in unstable_states:
            return [
                listing for listing in self.LISTINGS if not listing["requires_proof_of_employment"]
            ]
        return list(self.LISTINGS)


# ---------------------------------------------------------------------------
# Demo orchestrator
# ---------------------------------------------------------------------------


def spawn_server(data_dir: Path) -> subprocess.Popen:
    """Launch the Helpmefindthejob MCP server as a stdio subprocess.

    The server reads stdin / writes stdout for JSON-RPC; stderr is
    swallowed in this demo so the narration stays clean."""

    repo_root = Path(__file__).resolve().parent.parent.parent
    env = dict(os.environ)
    env["HELPMEFINDTHEJOB_DATA_DIR"] = str(data_dir)
    env.setdefault("HELPMEFINDTHEJOB_DISABLE_NETWORK", "1")
    return subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        cwd=str(repo_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def run_demo() -> int:
    banner("Housing-stub-client — composing with Helpmefindthejob MCP")
    print()
    print(
        textwrap.dedent(
            """\
            This stub stands in for a real housing-agent collaborator. It
            demonstrates two composition modes from the protocol spec:

              Mode 1 — sequential handoff (propose_referral)
              Mode 2 — profile-shared composition (get_user_profile_for_consent)

            All MCP traffic shown below is real — the only thing simulated
            is the housing-side recommendation logic.
            """
        )
    )

    with tempfile.TemporaryDirectory(prefix="housing-stub-") as tmp:
        data_dir = Path(tmp)
        proc = spawn_server(data_dir)
        try:
            mcp = StdioMCPClient(proc)

            step("Handshake: initialize")
            init_response = mcp.call(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "housing-stub-client", "version": "0.1.0"},
                    "capabilities": {},
                },
            )
            show("server reply", init_response.get("result"))

            step("Handshake: notifications/initialized")
            mcp.notify("notifications/initialized")

            step("Discover the tool catalogue (tools/list)")
            list_response = mcp.call("tools/list")
            tools = list_response.get("result", {}).get("tools", [])
            print(f"   server advertises {len(tools)} tools")
            for tool in tools:
                print(f"     - {tool['name']}")

            user_id = "demo-user-aicha"
            housing = HousingAgentStub(mcp, user_id=user_id)

            banner("Mode 1 — sequential handoff")
            step("User: 'Ich suche eine Wohnung in Berlin, aber ich habe")
            print("        noch kein Anschreiben für meine Bewerbungen.'")
            step("Housing agent calls helpmefindthejob.propose_referral")
            referral = housing.request_employment_referral()
            show("referral object returned", referral.get("result"))
            step("Housing agent presents this to the user:")
            print("     'I can keep helping you with housing, but you also")
            print("     mentioned needing an Anschreiben. Would you like me")
            print("     to hand you over to Helpmefindthejob for that?'")
            print()
            print("     [user accepts] → handoff completes; housing agent")
            print("     remains available for the housing thread.")

            banner("Mode 2 — profile-shared composition")
            step("User has consented to share their employment status.")
            step("Housing agent calls helpmefindthejob.get_user_profile_for_consent")
            print("        with scopes=['employment'] (least-privilege)")
            profile_response = housing.fetch_employment_profile()
            show("profile returned (scope=employment)", profile_response.get("result"))

            step("Housing agent applies the employment context to its filter")
            # Extract the structured content the tool returned. The MCP
            # server returns a content array; the JSON profile is inside.
            inner = (profile_response.get("result") or {}).get("content") or []
            profile_payload: Any = {}
            for block in inner:
                if block.get("type") == "text":
                    try:
                        profile_payload = json.loads(block.get("text", "{}"))
                    except json.JSONDecodeError:
                        profile_payload = {}
                    break
            filtered = housing.filter_listings_by_profile(profile_payload)
            print(f"   filter retained {len(filtered)} of {len(housing.LISTINGS)} listings")
            for listing in filtered:
                print(
                    f"     - {listing['id']}: €{listing['rent_eur']}/mo, "
                    f"deposit {listing['deposit_months']} months, "
                    f"PoE-required={listing['requires_proof_of_employment']}"
                )

            banner("Demo complete")
            print()
            print("Both composition modes exercised against a real MCP server.")
            print("No housing logic of substance was shipped — that's the point.")
            print()

            return 0
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)


if __name__ == "__main__":
    raise SystemExit(run_demo())
