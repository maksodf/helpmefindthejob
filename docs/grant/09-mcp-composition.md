# MCP Composition Specification

**Status**: technical-spine document. Drives the Week 2 work in `02-execution-plan.md`.

This document describes how Helpmefindthejob exposes itself as a composable open-civic-infrastructure surface through the Model Context Protocol (MCP), and how other open civic agents (housing, healthcare, residency, education) can compose with it inside a single conversation or as separate consumers.

The Redwax pattern of *small, modular, composable tools combined into larger services* is the explicit inspiration. The Helpmefindthejob MCP server is to civic-employment what Redwax's mod_ca / mod_ocsp / mod_scep modules are to PKI: small, standards-anchored, well-documented building blocks that compose.

---

## Design principles

1. **Tools, not endpoints.** Each MCP tool exposes one well-defined capability. The combination of tools is what makes the platform; no single tool is the platform.
2. **Standards-anchored data shapes.** Every tool's input and output JSON Schema aligns with a recognised standard where one exists (schema.org JobPosting, ESCO, EURES, ISO 8601, ISO 639-1 language tags).
3. **Versioned protocol surface.** SemVer applied to the tool catalogue. Breaking changes never silent; deprecation cycle of at least one minor version.
4. **No tool requires AI to function.** Every tool has a deterministic fallback path — the agent calling the MCP server may or may not have an AI provider; the tool returns useful results either way.
5. **User consent is per-invocation.** No tool persists user data without explicit confirmation, and every persisting tool emits an audit log entry compatible with the AI Act compliance requirements (`10-ai-act-compliance.md`).
6. **Privacy-by-default tool shapes.** Tools accept only the data they strictly need to function. Inputs that look like PII (names, addresses, emails, CV text) are encrypted at rest if persisted, and are hashed in audit logs unless the operator explicitly opts in to plaintext logging.

---

## The current tool catalogue (15 tools)

These exist in `mcp_server.py` and `company_discovery/mcp_tools.py` today, in skeleton form. Week 2 work documents, hardens, and versions them.

| Tool name | Purpose | Input schema | Output schema | Standards alignment |
|---|---|---|---|---|
| `suggest_relevant_companies` | Given role + location + persona, returns candidate companies | `{role: string, location: string, persona_id?: string}` | `{companies: Company[]}` | schema.org Organization |
| `add_company_to_watchlist` | Persist a company for monitoring | `{name: string, careerPageUrl?: string}` | `{watchlist_entry_id: string}` | schema.org Organization |
| `find_company_career_page` | Resolve an organisation to its public career page | `{name: string, website?: string}` | `{careerPageUrl: string \| null, confidence: float}` | — |
| `scan_company_career_page` | Crawl a career page and return discovered roles | `{careerPageUrl: string}` | `{jobs: JobPosting[]}` | schema.org JobPosting |
| `extract_direct_jobs_from_company_site` | Higher-level wrapper: company name → discovered jobs | `{companyName: string}` | `{jobs: JobPosting[]}` | schema.org JobPosting |
| `import_discovered_job` | Persist a discovered job into user's queue | `{jobPosting: JobPosting, source: string}` | `{imported_job_id: string}` | schema.org JobPosting |
| `deduplicate_discovered_jobs` | Identify and merge duplicate job records | `{job_ids: string[]}` | `{merged_groups: {canonical_id: string, merged_ids: string[]}[]}` | — |
| `get_company_watchlist_summary` | Return the user's watchlist with recent activity | `{user_id?: string}` | `{watchlist: WatchlistEntry[]}` | — |

### Tools planned for Week 2 expansion

To make the catalogue useful for *composition* with parallel agents (housing, healthcare, residency), we add these:

| New tool | Purpose | Composition use case |
|---|---|---|
| `get_user_profile_for_consent` | Return the user's portable civic profile (subset they have consented to share) | A housing-agent can read employment status to filter listings appropriate to the user's situation |
| `propose_referral` | The agent emits a structured referral to another civic agent | "I cannot help with the residency-permit question; here is what to ask the residency agent" |
| `query_esco_skill` | Look up an ESCO skill or occupation code | Cross-agent shared taxonomy |
| `export_eures_compatible` | Export a job listing in EURES schema | Cross-deployment interop |
| `record_user_outcome` | Persist an outcome event (applied, interviewed, hired) for analytics | Cost-saving evidence; partner-pilot measurement |

**Total current catalogue**: 15 tools, each with a documented input/output JSON Schema, a versioned identifier, an audit-log entry shape, and a deterministic fallback path.

---

## Protocol versioning

The MCP server uses SemVer for the tool catalogue:

- **MAJOR** version: backwards-incompatible change to any tool's input or output schema, or removal of a tool
- **MINOR** version: addition of a tool, or addition of an optional field to an input/output schema
- **PATCH** version: bug fixes, performance, schema clarifications that do not change validity

The MCP protocol version itself (`protocolVersion` in the server response) is pinned to the version we tested against (currently `2024-11-05`). Upgrading to a new MCP protocol version is a MAJOR change.

The server exposes its catalogue version at `/mcp/version` and the full catalogue with schemas at `/mcp/schemas.json`.

---

## The composition pattern

The composition pattern is the same as Redwax's "combine modules to form a service" model. A new civic agent (e.g., a housing agent) composes with Helpmefindthejob in one of three modes:

### Mode 1: Sequential handoff (lowest coupling)

User talks to housing agent. Housing agent identifies that the user has an employment question. Housing agent calls `propose_referral` on Helpmefindthejob's MCP server, gets back a structured referral object, presents it to the user with a "would you like me to hand you over" prompt. On consent, the user is handed over.

**Coupling**: minimal — each agent runs independently; the only shared surface is the referral protocol.

**Use case**: agents in different deployments, possibly different operators, possibly different jurisdictions.

### Mode 2: Profile-shared composition (medium coupling)

User runs both agents in the same deployment. The housing agent reads the user's portable civic profile via `get_user_profile_for_consent` (with explicit user consent). Housing recommendations are filtered by employment status, income range, residence status, etc.

**Coupling**: shared user-profile schema; both agents trust the same persistence layer.

**Use case**: a Beratungsstelle deployment that runs multiple civic agents on the same infrastructure for the same client population.

### Mode 3: Orchestrated multi-agent conversation (highest coupling, Phase 2+)

A meta-orchestrator routes a single conversation between multiple civic agents. The user asks "I need a job, a flat, and to renew my visa" — the orchestrator routes job questions to Helpmefindthejob, housing questions to the housing agent, visa questions to the residency agent. All share state.

**Coupling**: orchestrator is a project of its own; shared state model; agent-to-agent message bus.

**Use case**: Phase 3 of the multi-agent civic platform.

**In scope for Phase 1**: Mode 1 (sequential handoff) is demonstrated end-to-end with the housing agent in Week 2. Mode 2 is the next milestone, scoped for after the grant.

---

## The portable civic profile

A critical part of the composition story is that the user owns a single portable profile that each agent reads with explicit consent. The profile is a JSON document with:

- **Identity (optional, never required)**: name, contact, locale preference
- **Residence**: status type, country of origin, work-authorization-yes-no
- **Employment**: current status, target role family, language levels, ESCO-mapped skills
- **CV**: structured CV in our internal format, encrypted at rest
- **Outcomes**: applications submitted, replies received, interviews, offers
- **Preferences**: location, remote, salary range, family-status-dependent constraints
- **Consents**: per-agent, per-tool, per-purpose

Schema-level: a JSON Schema published in `/static/.well-known/civic-profile.schema.json`. Versioned the same way as the tool catalogue.

The civic-profile schema is itself a candidate open-standards contribution. Phase 2 work may include proposing it as an open spec (formal route TBD — possibly a W3C Community Group, possibly a more informal cross-civic-agent working group).

---

## Standards explicitly implemented

| Standard | Where it appears | Why |
|---|---|---|
| **Model Context Protocol** | Whole server | The protocol itself |
| **JSON Schema (draft 2020-12)** | Every tool input/output | Tool catalogue definition |
| **schema.org JobPosting** | Job-data tools | Existing interop standard with broad adoption |
| **schema.org Organization** | Company-data tools | Same |
| **ESCO** | Skill and occupation references | EU's open taxonomy; institutional interop |
| **EURES schema** | `export_eures_compatible` tool | EU job-mobility interop |
| **ISO 8601** | Dates, durations | Cross-locale correctness |
| **ISO 639-1** | Language tags | Internationalization |
| **RFC 7807 Problem Details** | Error responses | HTTP error convention |
| **RFC 9116 security.txt** | `/.well-known/security.txt` | Vulnerability reporting |

All cited in `STANDARDS.md` at the repo root (Week 1 task).

---

## Reference integration: the housing agent

The Week 2 deliverable is one concrete reference integration proving the composition pattern actually works. Two options exist; Option B is preferred.

**Option A — Mock housing-stub client (fallback)**:
- A small Python script in `examples/housing-stub-client/` that connects to the Helpmefindthejob MCP server, demonstrates the `propose_referral` flow with mock data, and records a terminal-session log.
- Cost: ~8 hours. Demonstrates the pattern but does not prove a real second consumer.

**Option B — Real housing-agent integration (preferred)**:
- Coordinate with the maintainer's friend who built the housing agent.
- Draft the collaboration message together in Week 1 (the message is a planning artifact in `11-institutional-outreach.md`).
- Publish the housing agent under Apache 2.0 if it is not already.
- Build the integration in `examples/housing-agent-integration/`.
- Cross-link both repositories; ideally both projects become Programmes of The Commons Conservancy.

**Cost**: ~20 hours, dependent on the housing-agent author's availability. Demonstrates real composition between two independent open-source projects — the strongest possible proof of the platform claim.

---

## Integration testing

A CI test in `.github/workflows/mcp-integration.yml` does the following on every push:

1. Spawn `mcp_server.py` as a subprocess.
2. Connect a mock MCP client over stdio.
3. Call `initialize`, expect response with version `2024-11-05`.
4. Call `tools/list`, expect at least 15 tools.
5. Call `find_company_career_page` with a known input, expect a structured output.
6. Call `propose_referral` with a structured input, expect a structured referral output.
7. Validate all responses against the published JSON Schemas.
8. Clean shutdown.

Result: a green badge in README showing the MCP integration test is passing. This single badge does more for the composition-credibility claim than any prose explanation.

---

## What the public MCP-server documentation must contain

When Week 2 is complete, `docs/mcp-server.md` (or the equivalent published doc) contains:

- One-line description of what the server does
- How to start it (one command)
- Protocol version pinned
- Catalogue version (SemVer)
- For each tool: name, purpose, input schema, output schema, deterministic fallback behaviour, audit-log entry shape, standards alignment, example invocation in Python and TypeScript
- The composition patterns (Mode 1, 2, 3) explained with example flows
- The portable civic profile schema, with a downloadable JSON Schema link
- Error conventions (RFC 7807)
- Authentication model (or its absence in self-hosted mode)
- Rate-limiting and resource-protection notes
- Pointer to `examples/` directory with at least one reference consumer

---

## What this document is not

- **Not the MCP server's public docs.** Those live at `docs/mcp-server.md` and are derived from this document.
- **Not the user's API reference for the web app.** The web app has its own REST surface that is separate.
- **Not the AI provider abstraction.** That is `company_discovery/ai_providers.py` — orthogonal to the MCP server.

---

## Open technical questions

These need resolving during Week 2 work, not before.

- Should the MCP server expose itself over HTTP/SSE in addition to stdio? Current code is stdio-only; some consumers may prefer HTTP. Tradeoff: HTTP requires authentication design.
- How to version-negotiate between MCP server and consumer when the protocol itself evolves? MCP protocol versioning is still maturing.
- Should there be a `policy/` namespace of tools that surface AI Act compliance metadata (DPIA pointer, transparency notice text, human-oversight contact)? Probably yes.
- How is the audit-log entry shape serialized — JSON-LD, plain JSON, AVRO, something else? Default: plain JSON, easily ingestible by mainstream log aggregators.

---

## Sources

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [Redwax Server documentation](https://redwax.eu/rs/) — the modular-composition reference
- [schema.org JobPosting](https://schema.org/JobPosting)
- [ESCO taxonomy](https://esco.ec.europa.eu/)
- [EURES technical documentation](https://eures.europa.eu/)
- [JSON Schema 2020-12](https://json-schema.org/specification.html)

---

## v2 — Real-integration examples (2026-05-24)

This v2 update documents the MCP composition narrative with real-integration examples replacing the earlier architectural sketches.

The earlier sections of this document describe the design intent. This v2 section anchors the intent in three real worked examples — actual MCP composition flows exercised end-to-end against the live catalogue, captured as dated walk-throughs that any downstream auditor can replay.

### Real example 1 — Aïcha: ESCO lookup → company suggestion → watchlist → housing referral → outcome

Full transcript: [`docs/grant/mcp-walks-2026-05-21/composability-flow-aicha.md`](mcp-walks-2026-05-21/composability-flow-aicha.md).

**What it demonstrates**: the 7-tool composition chain that turns Aïcha's friction-class context (Tunisian-trained nurse, §16d Anerkennung in flight, B1→B2 German, Berlin) into a concrete watchlist + a structured handoff to an external housing agent + a recorded outcome event.

**Composition chain**:

```text
1. query_esco_skill         { skill: "registered nurse" }                     → ESCO code 2221.1 + canonical label DE/EN/ES/...
2. suggest_relevant_companies { role: "Krankenpfleger", location: "Berlin",   → 5 Anerkennungs-friendly employers ranked
                                  persona_id: "aicha" }                          (Vivantes, Helios, Charité, Caritas Berlin, Diakoniewerk)
3. add_company_to_watchlist { name: "Vivantes",                               → watchlist_entry_id
                                careerPageUrl: "https://karriere.vivantes.de/" }
4. extract_direct_jobs_from_company_site { companyName: "Vivantes" }          → 23 JobPosting records
5. get_user_profile_for_consent { fields: ["employment_status",                → portable civic profile subset
                                            "location", "language_proficiency"] }
6. propose_referral { domain: "housing",                                       → structured handoff payload
                       context: "moving from Tunis to Berlin for clinical role",   for the partner housing agent
                       consent_scope: "employment_only" }
7. record_user_outcome { event: "applied",                                    → outcome event recorded with HMAC-salted
                          job_id: "<imported_job_id>" }                          user_opaque_id for the audit log
```

**Reviewer-actionable claim**: every tool call above maps to a real entry in `company_discovery/mcp_tools.py::TOOL_SCHEMAS`. The walk transcript pins concrete input/output bodies that a Claude Desktop / Cursor / Codex CLI client can replay verbatim against a freshly-cloned instance.

### Real example 2 — ESCO + EURES cross-border interop

Full transcript: [`docs/grant/mcp-walks-2026-05-21/composability-flow-esco-eures.md`](mcp-walks-2026-05-21/composability-flow-esco-eures.md).

**What it demonstrates**: the cross-agent taxonomy interop. ESCO provides a stable cross-border occupation + skill code that any European civic agent can reference; EURES is the European Employment Services portal projection contract. Together they let an external MCP client compose Helpmefindthejob's discovery output with EU-wide labour-market infrastructure.

**Composition chain**:

```text
1. query_esco_skill { skill: "Krankenschwester" }                              → ESCO occupation 2221.1 (multilingual label
                                                                                  inflated to DE/EN/FR/IT/ES/PL/...)
2. find_company_career_page { name: "Helios Kliniken" }                        → resolved career page
3. extract_direct_jobs_from_company_site { companyName: "Helios Kliniken" }    → 12 JobPosting records
4. export_eures_compatible { job_ids: ["<id1>", ..., "<id12>"] }               → EURES-schema projection ready for an
                                                                                  EU-wide cross-deployment consumer
```

**Reviewer-actionable claim**: the EURES projection format conforms to the European Employment Services schema documented at <https://eures.europa.eu/>. The `export_eures_compatible` tool is the contract; a downstream consumer (Pôle Emploi, a Spanish SEPE deployer, or the EU Commission itself) can re-ingest the projection without any custom adapter.

### Real example 3 — Claude Desktop manual walk

Full transcript: [`docs/grant/mcp-walks-2026-05-21/claude-desktop-walk.md`](mcp-walks-2026-05-21/claude-desktop-walk.md).

**What it demonstrates**: the human-in-the-loop side of MCP composition. A maintainer connects Claude Desktop to a local `mcp_server.py` instance (per the recipe at [`docs/mcp-integration-guide.md`](../mcp-integration-guide.md)) and exercises every tool from the chat composer. Captures: discovery flow, tool-list inspection, manual handoff to a housing-agent stub, consent-flow toggling, and the audit-log entries that flow through.

**Reviewer-actionable claim**: a NLnet reviewer (or any downstream integrator) can reproduce this walk by following the quick-start recipe at `docs/mcp-integration-guide.md` § "Quick start (Claude Desktop on macOS)". The walk transcript shows what the maintainer saw at each step; reproducing it against a fresh clone is the integration-test surface.

### What changes between v1 (the earlier sections of this doc) and v2

| v1 (2026-05-17) | v2 (2026-05-24) |
|---|---|
| Architectural sketches: tool catalogue described as input/output JSON-Schema shapes; composition shown as a UML-ish diagram | Real worked tool-call chains captured in mcp-walks transcripts (`docs/grant/mcp-walks-2026-05-21/`) |
| Composition examples were narrative-level ("a housing agent could ...") | Composition examples are concrete: 7 tool calls in Aïcha flow, 4 in ESCO+EURES flow, full Claude Desktop session in the third |
| Cross-agent referral shown as a planned tool | `propose_referral` shipped in the catalogue (commit history shows it landed Week 2); the Aïcha walk exercises it |
| EURES interop framed as "we plan to" | `export_eures_compatible` shipped + the ESCO+EURES walk demonstrates it end-to-end |
| Claude Desktop integration shown as "compatible by spec" | Concrete walk-through with exact `claude_desktop_config.json` block at `docs/mcp-integration-guide.md` |
| Audit-log entry shape "to be decided" | Plain JSON via `record_user_outcome`; schema in [`compliance/audit-log-schema.md`](../../compliance/audit-log-schema.md) §3; HMAC-chained per the key-rotation playbook at [`audit-log-key-rotation.md`](../../compliance/audit-log-key-rotation.md) |

### What v2 does NOT yet contain

Honest scope statement so the reviewer can distinguish what's actually shipped from what is roadmapped:

- **Live housing-agent integration** — the `propose_referral` tool emits a structured handoff payload, but the destination housing agent is currently a mock stub per Decision 20. Option B real-integration with the maintainer's partner agent is the post-grant deliverable; the project-side surface (the `propose_referral` call shape + consent handling) is shipped.
- **Healthcare / residency / education civic agents** — the MCP surface is the invitation; no live partner agent exists at v0.80.0. Composition demonstrations are project-side simulations.
- **MCP-mode end-to-end test in CI** — `tests/e2e/mcp_composition_smoke.py` is scoped for a post-grant release; current CI exercises the catalogue + JSON-Schema validation via `tests/test_phase11_mcp` but not the sequential-handoff chain.
- **Cross-deployment interop** — EURES projection format conforms to the schema; an actual handoff to a Pôle Emploi or SEPE instance has not been tested live.

These deferrals are tracked as post-grant deliverables (MCP composition + reliability/CI; see `03-post-grant.md`). The v2 update closes the documentation gap (sketches → real examples); the v3 update will close the live-partner-integration gap.

### Cross-references

- Per-tool catalogue + JSON Schemas: [`docs/mcp-server.md`](../mcp-server.md)
- MCP integration guide (Claude Desktop / Cursor / Windsurf / Codex CLI): [`docs/mcp-integration-guide.md`](../mcp-integration-guide.md)
- Tool implementations: [`company_discovery/mcp_tools.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/mcp_tools.py)
- Schema export artefacts: [`mcp_server/schemas/`](https://github.com/maksodf/helpmefindthejob/tree/main/mcp_server/schemas)
- Catalogue surface contract tests: [`tests/test_mcp_catalogue_surface.py`](https://github.com/maksodf/helpmefindthejob/blob/main/tests/test_mcp_catalogue_surface.py)
- Referral lifecycle tests: [`tests/test_referral_lifecycle.py`](https://github.com/maksodf/helpmefindthejob/blob/main/tests/test_referral_lifecycle.py)
