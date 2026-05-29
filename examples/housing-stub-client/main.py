#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Housing reference agent — a runnable, *real* MCP composition.

(The directory name ``housing-stub-client`` is legacy; what runs here is
a real composition, not a stub.) A second, independent civic agent — a
housing-search agent — composes with Helpmefindthejob entirely over the
Model Context Protocol, and the demo then *proves* the consent + audit
guarantees rather than asserting them.

Everything below is REAL and a reviewer can replay all of it:

  * **Transport** — JSON-RPC over stdio against the actual MCP server
    (``mcp_server.py``), the same wire Claude Desktop / Cursor / Cline use.
  * **Consent-bound profile handoff** — ``get_user_profile_for_consent``
    returns the seeded user's REAL stored civic profile (target roles,
    languages, locale, location), scope-filtered — not null placeholders.
  * **Full referral lifecycle** — ``propose_referral`` → ``list_referrals``
    → ``update_referral_status``, persisted server-side and read back.
  * **Tamper-evident audit trail** — every tool call emits an EU-AI-Act
    Article-12 ``mcp_tool_invocation`` record into an HMAC-chained log;
    the demo reads the log back and runs ``verify_chain()`` to PROVE the
    chain is intact.

What is ILLUSTRATIVE (stated honestly): the housing-search recommendation
logic (a few hard-coded listings). The point of this example is the MCP
*composition* — the consent-bound data handoff and the verifiable audit
trail — not a housing-search algorithm.

Run it from the repository root::

    python examples/housing-stub-client/main.py

No external services or API keys are needed. Total runtime: ~3 seconds.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Imported from the parent process to (1) seed a real civic profile the
# spawned server will read, and (2) verify the audit-log HMAC chain the
# server writes. Importing the package is why REPO_ROOT is on sys.path.
from company_discovery.audit_log import verify_chain  # noqa: E402
from company_discovery.models import UserProfile  # noqa: E402
from company_discovery.sqlite_repository import (  # noqa: E402
    SqliteCompanyDiscoveryRepository,
)

# A fixed 32-byte demo salt so the audit chain is deterministic and the
# parent process can re-derive + verify it. A real deployment supplies its
# own secret salt via HELPMEFINDTHEJOB_AUDIT_SALT and never commits it.
DEMO_SALT_BYTES = b"helpmefindthejob-composition-demo!!!"[:32]
DEMO_USER_ID = "demo-user-aicha"


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

    A real housing agent would use a library; this implementation is
    deliberately compact so a reader can see the entire protocol surface
    in one file.
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

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return the parsed JSON payload the tool emitted
        (unwrapping the MCP ``content`` envelope)."""

        response = self.call("tools/call", {"name": name, "arguments": arguments})
        result = response.get("result") or {}
        for block in result.get("content") or []:
            if block.get("type") == "text":
                try:
                    return json.loads(block.get("text", "{}"))
                except json.JSONDecodeError:
                    return {}
        return {}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self._write(message)


# ---------------------------------------------------------------------------
# Housing reference agent
# ---------------------------------------------------------------------------


class HousingReferenceAgent:
    """An independent housing-search agent that composes with
    Helpmefindthejob over MCP. The MCP calls are real; the listings are
    illustrative."""

    LISTINGS = [
        {"id": "listing-001", "city": "Berlin", "rent_eur": 850, "near_clinics": True},
        {"id": "listing-002", "city": "Berlin", "rent_eur": 620, "near_clinics": False},
        {"id": "listing-003", "city": "Potsdam", "rent_eur": 1100, "near_clinics": True},
    ]

    def __init__(self, mcp: StdioMCPClient, user_id: str) -> None:
        self._mcp = mcp
        self._user_id = user_id

    def refer_to_employment(self) -> dict[str, Any]:
        """The user asked about housing but has no Anschreiben yet — the
        housing agent refers them to Helpmefindthejob via ``propose_referral``."""

        return self._mcp.call_tool(
            "propose_referral",
            {
                "userId": self._user_id,
                "targetAgent": "helpmefindthejob",
                "reason": (
                    "User asked about housing but said they have no Anschreiben "
                    "yet — they need employment-application help, outside our scope."
                ),
                "context": {
                    "userMessage": (
                        "Ich suche eine Wohnung in Berlin, aber ich habe noch "
                        "kein Anschreiben für meine Bewerbungen."
                    ),
                    "domain": "employment",
                },
            },
        )

    def list_referrals(self, status: str | None = None) -> dict[str, Any]:
        args: dict[str, Any] = {"userId": self._user_id}
        if status:
            args["status"] = status
        return self._mcp.call_tool("list_referrals", args)

    def accept_referral(self, referral_id: str) -> dict[str, Any]:
        return self._mcp.call_tool(
            "update_referral_status",
            {
                "userId": self._user_id,
                "referralId": referral_id,
                "status": "accepted",
                "outcomeNote": "User opted in to the employment hand-off.",
            },
        )

    def fetch_consented_profile(self, scopes: list[str]) -> dict[str, Any]:
        """Fetch the user's portable civic profile with explicit consent,
        least-privilege scoped."""

        return self._mcp.call_tool(
            "get_user_profile_for_consent",
            {"userId": self._user_id, "scopes": scopes},
        )

    def recommend_using(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Tailor housing recommendations using the REAL consented
        employment context. The recommendation logic is illustrative; the
        point is that it consumed live cross-agent data."""

        employment = (profile.get("profile") or {}).get("employment") or {}
        target_roles = employment.get("targetRoleFamilies") or []

        # Real signal in use: the user targets clinical roles, so prioritise
        # listings near clinics. (The consented profile also carries the
        # user's languages + locale, shown in the demo narration.)
        clinical = any(
            any(term in role.lower() for term in ("nurse", "pfleg", "krankensch"))
            for role in target_roles
        )

        ranked = sorted(
            self.LISTINGS,
            key=lambda listing: (0 if (clinical and listing["near_clinics"]) else 1, listing["rent_eur"]),
        )
        return ranked


# ---------------------------------------------------------------------------
# Seeding + server lifecycle
# ---------------------------------------------------------------------------


def seed_user(data_dir: Path, user_id: str) -> UserProfile:
    """Seed a real civic profile so the consent handoff carries live data.

    Writes directly to the SQLite the server reads — the same persistence
    path the ``scripts/seed-personas.py`` reference seeder uses."""

    repo = SqliteCompanyDiscoveryRepository(data_dir / "company_discovery.sqlite3")
    profile = UserProfile(
        user_id=user_id,
        persona_id="aicha",
        friction_class="aicha",
        target_roles=["Registered nurse", "Krankenpfleger", "Pflegefachkraft"],
        languages=["Arabic (native)", "German (B1)", "English (B2)"],
        locale="de",
        location="Berlin",
        seniority="experienced",
        years_experience=6,
    )
    repo.save_user_profile(profile)
    return profile


def spawn_server(data_dir: Path) -> subprocess.Popen:
    """Launch the Helpmefindthejob MCP server as a stdio subprocess.

    The data dir holds both the SQLite store (profiles + referrals) and the
    HMAC-chained audit log; the fixed demo salt lets the parent verify the
    chain afterwards."""

    env = dict(os.environ)
    env["HELPMEFINDTHEJOB_DATA_DIR"] = str(data_dir)
    env["HELPMEFINDTHEJOB_DATA_ROOT"] = str(data_dir)
    env["HELPMEFINDTHEJOB_AUDIT_SALT"] = base64.b64encode(DEMO_SALT_BYTES).decode()
    env.setdefault("HELPMEFINDTHEJOB_DISABLE_NETWORK", "1")
    return subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        cwd=str(REPO_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def verify_audit_trail(data_dir: Path) -> dict[str, Any]:
    """Read back the audit log the server wrote and verify the HMAC chain."""

    log_paths = sorted(data_dir.glob("ai_act_audit.log*"))
    tool_invocations: list[dict[str, Any]] = []
    for path in log_paths:
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("event_type") == "mcp_tool_invocation":
                    tool_invocations.append(obj)

    result = verify_chain(log_paths, DEMO_SALT_BYTES)
    return {
        "log_files": [p.name for p in log_paths],
        "tool_invocations": tool_invocations,
        "chain": result.to_dict(),
    }


# ---------------------------------------------------------------------------
# Demo orchestrator
# ---------------------------------------------------------------------------


def run_demo() -> int:
    banner("Housing reference agent — real MCP composition with Helpmefindthejob")
    print()
    print(
        "An independent housing agent composes with Helpmefindthejob over MCP.\n"
        "Everything below — transport, consent-bound profile handoff, referral\n"
        "lifecycle, and the tamper-evident audit trail — is real and replayable.\n"
        "Only the housing-search listings are illustrative."
    )

    with tempfile.TemporaryDirectory(prefix="housing-composition-") as tmp:
        data_dir = Path(tmp)

        step("Seed a real civic profile (so the consent handoff carries live data)")
        seeded = seed_user(data_dir, DEMO_USER_ID)
        print(f"   seeded {DEMO_USER_ID}: target_roles={seeded.target_roles}")

        proc = spawn_server(data_dir)
        try:
            mcp = StdioMCPClient(proc)

            step("Handshake: initialize")
            init_response = mcp.call(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "housing-reference-agent", "version": "1.0.0"},
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

            housing = HousingReferenceAgent(mcp, user_id=DEMO_USER_ID)

            banner("Mode 1 — sequential handoff (full referral lifecycle)")
            step("Housing agent calls helpmefindthejob.propose_referral")
            referral = housing.refer_to_employment()
            show("referral object returned", referral)
            referral_id = (referral.get("referral") or referral).get("referralId")
            print(f"   referralId = {referral_id!r}; sourceAgent + targetAgent recorded;")
            print("   userConsentRequired is part of the persisted referral object.")

            step("Housing agent lists the user's referrals (list_referrals)")
            listed = housing.list_referrals()
            print(f"   server returned {len(listed.get('referrals') or [])} persisted referral(s)")

            step("User opts in → update_referral_status (proposed → accepted)")
            updated = housing.accept_referral(referral_id)
            show("updated referral", updated)

            banner("Mode 2 — consent-bound profile-shared composition")
            step("Housing agent calls get_user_profile_for_consent")
            print("        with scopes=['identity','employment','preferences'] (least-privilege)")
            profile = housing.fetch_consented_profile(["identity", "employment", "preferences"])
            show("consented profile returned (REAL stored data, not placeholders)", profile)

            step("Housing agent tailors recommendations using the real employment context")
            ranked = housing.recommend_using(profile)
            _emp = (profile.get("profile") or {}).get("employment") or {}
            print(
                "   housing agent consumed real consented data → "
                f"targetRoles={_emp.get('targetRoleFamilies')!r}"
            )
            for listing in ranked:
                print(
                    f"     - {listing['id']}: €{listing['rent_eur']}/mo, "
                    f"near_clinics={listing['near_clinics']}"
                )

            # Close the server so the audit log is fully flushed before we read it.
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.wait(timeout=5)

            banner("Proof — tamper-evident audit trail (EU AI Act Article 12)")
            audit = verify_audit_trail(data_dir)
            invocations = audit["tool_invocations"]
            print(f"   {len(invocations)} mcp_tool_invocation records written by the server:")
            for entry in invocations:
                payload = entry.get("event_payload") or {}
                print(
                    f"     - {payload.get('tool_name')} "
                    f"(composition_source={payload.get('composition_source')!r}, "
                    f"outcome={entry.get('outcome')})"
                )
            chain = audit["chain"]
            print()
            print(f"   verify_chain() → ok={chain['ok']}, recordsChecked={chain['recordsChecked']}")

            # --- Assertions: this is a real check, not just narration ---
            employment = (profile.get("profile") or {}).get("employment") or {}
            assert "Krankenpfleger" in (employment.get("targetRoleFamilies") or []), (
                "consent handoff did not carry the seeded user's real target roles"
            )
            assert referral_id, "propose_referral did not return a referralId"
            assert (updated.get("referral") or updated).get("status") == "accepted", (
                "referral lifecycle did not advance to accepted"
            )
            assert chain["ok"] is True, f"audit chain verification failed: {chain}"
            assert len(invocations) >= 4, "expected audit records for every composed tool call"
            assert all(
                (e.get("event_payload") or {}).get("composition_source") == "housing-reference-agent"
                for e in invocations
            ), "audit records must attribute the composing agent (composition_source)"

            banner("Demo complete — composition is real and the audit chain verifies")
            print()
            print("A second civic agent composed with Helpmefindthejob over MCP, received")
            print("real consent-scoped data, drove the full referral lifecycle, and every")
            print("step is provable in a tamper-evident audit log. Replay it yourself.")
            print()
            return 0
        finally:
            try:
                if proc.stdin and not proc.stdin.closed:
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
