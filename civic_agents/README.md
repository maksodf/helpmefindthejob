<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# civic_agents — typed specialist contracts + a deterministic planner

`civic_agents` is the multi-agent layer that
[`docs/agent-architecture.md`](../docs/agent-architecture.md) §2 specifies: a
**planner** decomposes a user goal into sub-goals and routes each to a
**specialist agent** across a typed, JSON-Schema contract, emitting a
**trust receipt** into the Article-12 audit chain at every handoff.

Unlike `escolib` and `biasprobe` (standalone, import-isolated libraries), this is
an in-application subsystem: it composes with the project's audit chain and is
designed to bind to existing capabilities (in-process `company_discovery`
helpers and the federated `mesh/` HTTP agents) via injected handlers — so it is
transport-agnostic and AI-optional by construction.

## Use it

```python
from civic_agents import Goal, run
from company_discovery.audit_log import AuditLogEmitter

goal = Goal(
    goal_id="aicha-healthcare-berlin",
    persona_slug="aicha",
    needs=("cv", "search", "anerkennung", "letter"),   # routed in canonical order
    context={"role": "Krankenschwester", "location": "Berlin", "target_lang": "de"},
)

handlers = {                      # inject in-process or mesh-backed specialists
    "cv_agent": my_cv_handler,
    "search_agent": my_search_handler,
    # ...
}

trace = run(goal, handlers, AuditLogEmitter(log_path, salt))
assert trace.ok
```

`run` = `decompose` (rule-based, deterministic — the same goal always yields the
same plan; this is the **no-AI fallback floor**) + `execute` (per step: validate
input against the contract → call the handler → validate output → emit a trust
receipt). A contract violation or missing handler is recorded **and** receipted
as a failed step, never allowed to corrupt downstream state.

## The contracts

`civic_agents.contracts.CONTRACTS` holds the six specialist contracts
(`cv_agent`, `search_agent`, `anerkennung_agent`, `letter_agent`,
`housing_agent`, `compliance_agent`), each a JSON-Schema-validated input → output
boundary. `get_contract(name)` returns one; `validate_input` / `validate_output`
raise an attributable `ContractViolation` on mismatch.

## Trust receipts

Every planner step writes an `mcp_tool_invocation`-class record carrying digests
(never raw payloads — no PII in the chain) into the HMAC-chained audit log. The
golden-trace test (`tests/test_civic_agents.py`) replays a canonical plan and
proves the receipts verify (`verify_chain`) and are externally anchorable
(`company_discovery.audit_anchor.verify_anchor`).

## License

Apache-2.0.
