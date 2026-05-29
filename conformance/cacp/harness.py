# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""CACP v0.1 conformance harness.

Drives a candidate MCP server through three conformance levels and emits a
machine-readable report. Each check has a numbered, citable id (``CACP-Ln-NN``)
that maps to a normative requirement in ``docs/protocol/cacp-v0.1.md``.

    L1  Catalogue     — versioned tool catalogue, JSON-Schema-validated inputs,
                        the required CACP composition tools present.
    L2  Referral      — the referral lifecycle state machine + cross-tenant
                        isolation.
    L3  Consent+Audit — scope-filtered consent profile (validates against the
                        published civic-profile schema) + tamper-evident audit
                        attribution of every cross-agent call.

Run against this repo's reference server::

    python -m conformance.cacp            # human summary + exit code
    python -m conformance.cacp --json     # machine-readable report

The only application dependency is ``company_discovery.audit_log.verify_chain``
(for L3's audit-chain check); everything else is stdlib + jsonschema.
"""

from __future__ import annotations

import base64
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from conformance.cacp.stdio_client import REPO_ROOT, MCPSession, StdioMCPClient

CACP_VERSION = "0.1"

#: Composition tools a CACP server MUST expose (the consent + referral + ESCO +
#: EURES + outcomes surface that makes cross-agent composition possible).
REQUIRED_TOOLS = (
    "get_user_profile_for_consent",
    "propose_referral",
    "list_referrals",
    "update_referral_status",
    "query_esco_skill",
    "export_eures_compatible",
    "record_user_outcome",
)

CONSENT_SCOPES = ("identity", "residence", "employment", "cv", "outcomes", "preferences")

_PROBE_CLIENT_NAME = "cacp-conformance-probe"
_PROBE_SALT_B64 = base64.b64encode(b"cacp-conformance-probe-salt-32!!!"[:32]).decode()
_CIVIC_PROFILE_SCHEMA = REPO_ROOT / "static" / ".well-known" / "civic-profile.schema.json"


@dataclass
class Check:
    id: str
    level: str
    title: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "passed": self.passed,
            "detail": self.detail,
        }


@dataclass
class ConformanceReport:
    cacp_version: str
    server: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    def levels(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for c in self.checks:
            out[c.level] = out.get(c.level, True) and c.passed
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "cacpVersion": self.cacp_version,
            "server": self.server,
            "ok": self.ok,
            "levels": self.levels(),
            "passed": sum(1 for c in self.checks if c.passed),
            "total": len(self.checks),
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary(self) -> str:
        lines = [f"CACP v{self.cacp_version} conformance — {self.server}"]
        for c in self.checks:
            lines.append(f"  [{'PASS' if c.passed else 'FAIL'}] {c.id}  {c.title}")
            if not c.passed and c.detail:
                lines.append(f"          → {c.detail}")
        passed = sum(1 for c in self.checks if c.passed)
        verdict = "CONFORMANT" if self.ok else "NON-CONFORMANT"
        lines.append(f"  {verdict}: {passed}/{len(self.checks)} checks; levels={self.levels()}")
        return "\n".join(lines)


def _is_semver(value: Any) -> bool:
    import re

    return isinstance(value, str) and bool(
        re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", value)
    )


def _tool_error_status(raw: dict[str, Any]) -> str | None:
    """Return the RFC-7807 ``status`` of an isError tool result, else None."""
    result = raw.get("result") or {}
    if not result.get("isError"):
        return None
    for block in result.get("content") or []:
        if block.get("type") == "text":
            try:
                return json.loads(block.get("text", "{}")).get("status")
            except json.JSONDecodeError:
                return None
    return None


class ConformanceHarness:
    """Runs the CACP conformance battery against a connected client."""

    def __init__(self, client: StdioMCPClient) -> None:
        self.client = client
        self.checks: list[Check] = []

    def _record(self, id_: str, level: str, title: str, passed: bool, detail: str = "") -> None:
        self.checks.append(Check(id=id_, level=level, title=title, passed=passed, detail=detail))

    # -- L1: catalogue -----------------------------------------------------

    def run_l1_catalogue(self) -> None:
        tools = self.client.call("tools/list").get("result", {}).get("tools", [])
        self._record("CACP-L1-01", "L1", "tools/list returns a non-empty catalogue", bool(tools))

        required_keys = ("name", "description", "inputSchema", "version")
        missing = [
            t.get("name", "<unnamed>") for t in tools if not all(k in t for k in required_keys)
        ]
        self._record(
            "CACP-L1-02",
            "L1",
            "every tool carries name + description + inputSchema + version",
            not missing,
            f"tools missing required keys: {missing}" if missing else "",
        )

        bad_versions = [t.get("name") for t in tools if not _is_semver(t.get("version"))]
        self._record(
            "CACP-L1-03",
            "L1",
            "every tool version is SemVer",
            not bad_versions,
            f"non-SemVer versions: {bad_versions}" if bad_versions else "",
        )

        names = {t.get("name") for t in tools}
        absent = [t for t in REQUIRED_TOOLS if t not in names]
        self._record(
            "CACP-L1-04",
            "L1",
            "the required CACP composition tools are present",
            not absent,
            f"missing tools: {absent}" if absent else "",
        )

        invalid_schema = []
        for t in tools:
            schema = t.get("inputSchema") or {"type": "object"}
            try:
                jsonschema.Draft7Validator.check_schema(schema)
            except jsonschema.SchemaError:
                invalid_schema.append(t.get("name"))
        self._record(
            "CACP-L1-05",
            "L1",
            "every tool inputSchema is a valid JSON Schema",
            not invalid_schema,
            f"invalid schemas: {invalid_schema}" if invalid_schema else "",
        )

    # -- L2: referral lifecycle -------------------------------------------

    def run_l2_referral_lifecycle(self) -> None:
        user = "cacp-probe-user"
        other = "cacp-probe-other"

        r1 = self.client.call_tool(
            "propose_referral",
            {"userId": user, "targetAgent": "housing-agent", "reason": "conformance probe"},
        )
        referral = r1.get("referral") or r1
        referral_id = referral.get("referralId")
        self._record(
            "CACP-L2-01",
            "L2",
            "propose_referral returns referralId + status=proposed + userConsentRequired",
            bool(referral_id)
            and referral.get("status") == "proposed"
            and "userConsentRequired" in referral,
            f"referral={referral}",
        )

        listed = self.client.call_tool("list_referrals", {"userId": user})
        ids = [r.get("referralId") for r in (listed.get("referrals") or [])]
        self._record(
            "CACP-L2-02",
            "L2",
            "list_referrals returns the proposed referral",
            referral_id in ids,
            f"listed ids={ids}",
        )

        updated = self.client.call_tool(
            "update_referral_status",
            {"userId": user, "referralId": referral_id, "status": "accepted"},
        )
        updated_ref = updated.get("referral") or updated
        self._record(
            "CACP-L2-03",
            "L2",
            "update_referral_status advances proposed → accepted",
            updated_ref.get("status") == "accepted",
            f"updated={updated}",
        )

        # A fresh proposed referral; proposed → followed_up is NOT allowed.
        r2 = self.client.call_tool(
            "propose_referral",
            {"userId": user, "targetAgent": "housing-agent", "reason": "invalid-transition probe"},
        )
        r2_id = (r2.get("referral") or r2).get("referralId")
        bad = self.client.call_tool(
            "update_referral_status",
            {"userId": user, "referralId": r2_id, "status": "followed_up"},
        )
        bad_ref = bad.get("referral") or bad
        self._record(
            "CACP-L2-04",
            "L2",
            "an illegal lifecycle transition (proposed → followed_up) is rejected",
            bad.get("status") != "ok" or bad_ref.get("status") != "followed_up",
            f"unexpectedly accepted illegal transition: {bad}",
        )

        cross = self.client.call_tool(
            "update_referral_status",
            {"userId": other, "referralId": referral_id, "status": "declined"},
        )
        # Do NOT trust the attacker-call's echoed body — a leaking server could
        # perform the write yet return a benign shape. Re-read the victim's
        # referral AS THE OWNER and confirm the cross-tenant attempt persisted
        # nothing. referral_id was advanced to "accepted" in CACP-L2-03.
        owner_view = self.client.call_tool("list_referrals", {"userId": user})
        victim = next(
            (r for r in (owner_view.get("referrals") or []) if r.get("referralId") == referral_id),
            None,
        )
        call_rejected = cross.get("status") in ("not_found", "error")
        state_unchanged = victim is not None and victim.get("status") == "accepted"
        self._record(
            "CACP-L2-05",
            "L2",
            "cross-tenant isolation: another user cannot mutate a referral",
            call_rejected and state_unchanged,
            f"cross-tenant update leaked: call={cross}, owner-side status="
            f"{(victim or {}).get('status')!r} (must stay 'accepted')",
        )

    # -- L3: consent + audit ----------------------------------------------

    def run_l3_consent(self) -> None:
        requested = ["identity", "employment"]
        result = self.client.call_tool(
            "get_user_profile_for_consent",
            {"userId": "cacp-probe-user", "scopes": requested},
        )
        profile = result.get("profile") or {}
        only_requested = set(profile.get("scopes", [])) == set(requested) and all(
            scope in profile for scope in requested
        ) and not any(s in profile for s in CONSENT_SCOPES if s not in requested)
        self._record(
            "CACP-L3-01",
            "L3",
            "consent profile returns exactly the requested scopes + provenance fields",
            only_requested
            and "schemaVersion" in profile
            and "consentRecordedAt" in profile,
            f"profile keys={sorted(profile.keys())}",
        )

        bad_scope = self.client.call_tool_raw(
            "get_user_profile_for_consent",
            {"userId": "cacp-probe-user", "scopes": ["not-a-scope"]},
        )
        self._record(
            "CACP-L3-02",
            "L3",
            "an unknown consent scope is rejected (invalid_arguments)",
            _tool_error_status(bad_scope) == "invalid_arguments",
            f"status={_tool_error_status(bad_scope)}",
        )

        full = self.client.call_tool(
            "get_user_profile_for_consent",
            {"userId": "cacp-probe-user", "scopes": list(CONSENT_SCOPES)},
        ).get("profile") or {}
        schema_ok, schema_detail = True, ""
        try:
            schema = json.loads(_CIVIC_PROFILE_SCHEMA.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(full)
        except jsonschema.ValidationError as exc:
            schema_ok, schema_detail = False, str(exc)[:200]
        except OSError as exc:
            schema_ok, schema_detail = False, f"schema unreadable: {exc}"
        self._record(
            "CACP-L3-03",
            "L3",
            "consent profile validates against the published civic-profile schema",
            schema_ok,
            schema_detail,
        )

    def run_all(self) -> None:
        self.run_l1_catalogue()
        self.run_l2_referral_lifecycle()
        self.run_l3_consent()


def _verify_audit(data_dir: Path, client_name: str) -> Check:
    """Post-session L3-04: every tool call is in a verifiable HMAC chain and is
    attributed to the composing agent (clientInfo.name → composition_source)."""
    from company_discovery.audit_log import verify_chain

    log_paths = sorted(data_dir.glob("ai_act_audit.log*"))
    invocations: list[dict[str, Any]] = []
    for path in log_paths:
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("event_type") == "mcp_tool_invocation":
                invocations.append(obj)

    salt = base64.b64decode(_PROBE_SALT_B64)
    chain = verify_chain(log_paths, salt)
    attributed = bool(invocations) and all(
        (e.get("event_payload") or {}).get("composition_source") == client_name for e in invocations
    )
    passed = chain.ok and attributed
    detail = ""
    if not passed:
        detail = f"chain.ok={chain.ok}, invocations={len(invocations)}, attributed={attributed}"
    return Check(
        id="CACP-L3-04",
        level="L3",
        title="every cross-agent tool call is attributed + in a verifiable audit chain",
        passed=passed,
        detail=detail,
    )


def run_conformance(server_path: Path | None = None) -> ConformanceReport:
    """Spawn the candidate server, run all conformance levels, return a report."""
    server_label = str((server_path or (REPO_ROOT / "mcp_server.py")).name)
    report = ConformanceReport(cacp_version=CACP_VERSION, server=server_label)
    with tempfile.TemporaryDirectory(prefix="cacp-conformance-") as tmp:
        data_dir = Path(tmp)
        with MCPSession(
            data_dir,
            client_name=_PROBE_CLIENT_NAME,
            audit_salt_b64=_PROBE_SALT_B64,
            server_path=server_path,
        ) as client:
            harness = ConformanceHarness(client)
            harness.run_all()
            report.checks.extend(harness.checks)
        # Server has shut down → the audit log is flushed; verify it.
        report.checks.append(_verify_audit(data_dir, _PROBE_CLIENT_NAME))
    return report
