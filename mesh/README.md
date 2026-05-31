<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# helpmefindthejob civic-services mesh

This directory ships **reference implementations of three
cooperating civic agents** — housing, Anerkennung, social-
services — so the employment-agent's outbound MCP tools have
concrete receivers we can demonstrate against end-to-end.

## Why this exists

The MCP tools at `company_discovery/mcp_tools.py` (`propose_referral`,
`get_user_profile_for_consent`, `query_esco_skill`, `export_eures_compatible`)
let the employment-agent **hand work off to other civic agents**.
Without working receivers, the federated-mesh story is just a
spec document. With them, the architecture is testable +
demonstrable + integrator-grade documentation in code form.

The three simulator agents are **NOT** connected to any real
Wohnungsamt, BIBB, Anabin, Jobcenter, Sozialamt, or
Familienkasse endpoint. They carry **realistic-enough fixture
data** so the end-to-end demo can walk 2–3 plausible scenarios
per agent, and so partner integrators have a worked example
to read instead of a spec.

## Architecture

```
                ┌─────────────────────────────────────────────────┐
                │  employment-agent (this project)                │
                │  http://127.0.0.1:8765                          │
                │                                                  │
                │  exposes 15 MCP tools at /api/mcp                │
                │  emits propose_referral, profile-consume,        │
                │  query_esco_skill, eligibility-check             │
                └────────────┬─────────────┬─────────────┬─────────┘
                             │             │             │
              ┌──────────────┘             │             └──────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
   ┌────────────────────┐      ┌────────────────────┐       ┌────────────────────┐
   │  housing-agent     │      │  anerkennung-agent │       │ social-services-   │
   │  127.0.0.1:8101    │      │  127.0.0.1:8102    │       │  agent             │
   │                    │      │                    │       │  127.0.0.1:8103    │
   │  POST /v1/intake   │      │  POST /v1/verify-  │       │  POST /v1/         │
   │  GET  /v1/status   │      │       credential   │       │   eligibility-     │
   │                    │      │  POST /v1/issue-vc │       │   check            │
   │  3 demo cohorts:   │      │                    │       │  POST /v1/profile- │
   │   - berlin §16d    │      │  3 pathways:       │       │   consume          │
   │   - munich blue    │      │   - pflege Drittst.│       │                    │
   │     card           │      │   - eng BQFG       │       │  3 cohorts:        │
   │   - leipzig §24    │      │     blue card      │       │   - aicha §16d     │
   │     family         │      │   - IT unregulated │       │   - olga §24 family│
   │                    │      │                    │       │   - tobias Querein-│
   │  audit log →       │      │  audit log →       │       │     stieg          │
   │  data/mesh/        │      │  data/mesh/        │       │                    │
   │  housing-agent-    │      │  anerkennung-agent-│       │  audit log →       │
   │  audit.log         │      │  audit.log         │       │  data/mesh/social- │
   │                    │      │                    │       │  services-agent-   │
   │                    │      │                    │       │  audit.log         │
   └────────────────────┘      └────────────────────┘       └────────────────────┘
```

All four agents speak JSON-over-HTTP and emit per-agent
append-only audit logs with monotonic `sequence_no` markers, so
the end-to-end demo can replay the full decision trail by
reading each agent's `/v1/audit-trail` endpoint.

## Running it

### Option A — single Python process (development)

```bash
# Terminal 1 — start all 3 agents in one process
python -m mesh.run_all

# Terminal 2 — run the demo
python -m mesh.demo_aicha_walk
```

### Option B — docker-compose (closer to production)

```bash
# Bring up all 3 agents
docker compose -f mesh/mesh-docker-compose.yml up -d

# Wait for healthchecks
docker compose -f mesh/mesh-docker-compose.yml ps

# Run the demo
python -m mesh.demo_aicha_walk

# Bring down
docker compose -f mesh/mesh-docker-compose.yml down
```

## The Aïcha demo walk

`mesh/demo_aicha_walk.py` executes a 5-step end-to-end scenario:

1. **Verify Anerkennung** — Aïcha's Tunisian nursing diploma →
   `anerkennung-agent` → Pflegekräfte-aus-Drittstaaten pathway
   → partial recognition + Anpassungslehrgang requirement.
2. **Issue Verifiable Credential** — `anerkennung-agent` issues
   a W3C VC stub Aïcha can carry to other agents.
3. **Housing referral** — `propose_referral` to `housing-agent`
   with §16d context → Berlin §16d cohort → S-Bahn-proximity
   single-occupant intake.
4. **Social-services eligibility** — consent-scoped profile to
   `social-services-agent` → §16d Aufstockung cohort →
   Bürgergeld-Aufstockung during Anpassungslehrgang.
5. **Trace audit trail** — reads `/v1/audit-trail` from each
   agent and prints the full decision sequence so a reviewer
   sees every step end-to-end.

Each step prints the actual returned payload so a reviewer
walking the demo can see realistic decisions, not just "OK".

## What this proves to a reviewer

- **The MCP tools have receivers.** Not a spec promise — a
  runnable system.
- **Cross-agent decisions are traceable.** Each agent has its
  own audit log; the demo stitches them together.
- **Consent is scoped + bounded.** The social-services-agent
  records `consentExpiresAt` on every profile consume.
- **The protocol is integrator-readable.** A real Wohnungsamt
  wanting to integrate reads `mesh/housing_agent.py` as a
  worked example instead of a 30-page spec.
- **No external dependencies.** All agents run on Python
  stdlib — zero FastAPI, zero Flask, zero Node.js. A
  Beratungsstelle pays no operational tax for the mesh.

## Extending the mesh

To add a new receiver agent (e.g. `legal-aid-agent`):

1. Copy `mesh/housing_agent.py` to `mesh/legal_aid_agent.py`
2. Define your cohorts + decision logic
3. Register it in `mesh/run_all.py` and `mesh/mesh-docker-compose.yml`
4. Wire the employment-agent's `propose_referral` MCP tool to
   target the new agent (no code change needed —
   `targetAgent="legal-aid-agent"` is enough on the caller's
   side)

That's it. The protocol is the contract.
