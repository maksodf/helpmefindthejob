<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Civic Agent Composition Protocol (CACP) v0.1

**Status:** draft for community comment · **Version:** 0.1 · **License:** Apache-2.0

CACP is an open, consent-bound, audit-attributed contract for **composing
independent civic agents** (employment, housing, residency, education,
healthcare) over the [Model Context Protocol](https://modelcontextprotocol.io).
It lets a user-facing agent in one civic domain compose with a peer in another —
handing off a referral, or reading a scope-filtered portable profile with the
user's consent — without either project forking the other, and with every
cross-agent action recorded in a tamper-evident audit trail.

Helpmefindthejob's MCP server (`mcp_server.py`) is the **reference
implementation**; it passes the conformance suite in `conformance/cacp/`
(`python -m conformance.cacp`). This document is the normative spec; it promotes
and formalises the design in
[`docs/grant/09-mcp-composition.md`](https://github.com/maksodf/helpmefindthejob/blob/main/docs/grant/09-mcp-composition.md).

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are to be
interpreted as in RFC 2119. Each normative requirement carries a `CACP-Ln-NN`
identifier; the conformance harness asserts each one and cites the same id.

---

## 1. Composition model

A CACP **server** exposes civic capabilities as versioned MCP tools. A CACP
**consumer** (another civic agent) composes with it in one of three modes:

1. **Sequential handoff** (lowest coupling) — the consumer detects an
   out-of-domain need and issues a `propose_referral`; the user retains the
   choice to follow it. *(Shipped.)*
2. **Consent-bound profile sharing** (medium coupling) — with explicit,
   least-privilege consent, the consumer reads a scope-filtered portable civic
   profile via `get_user_profile_for_consent` and tailors its own output.
   *(Shipped.)*
3. **Orchestrated mesh** (highest coupling) — a planner routes one user goal
   across several agents. *(Partially shipped via the federated `mesh/`; a
   planner lands in the post-v0.1 roadmap.)*

Every tool **MUST** have a deterministic, no-AI fallback path; CACP composition
**MUST NOT** require any AI provider to function.

---

## 2. Conformance levels & normative requirements

A server is **CACP-conformant at level L** if it satisfies every requirement at
that level. Levels are cumulative-by-intent but independently testable.

### L1 — Catalogue

- **CACP-L1-01** — The server **MUST** answer `tools/list` with a non-empty tool
  catalogue.
- **CACP-L1-02** — Every catalogue entry **MUST** carry `name`, `description`,
  `inputSchema`, and a `version`.
- **CACP-L1-03** — Every tool `version` **MUST** be a SemVer string.
- **CACP-L1-04** — The server **MUST** expose the CACP composition tools:
  `get_user_profile_for_consent`, `propose_referral`, `list_referrals`,
  `update_referral_status`, `query_esco_skill`, `export_eures_compatible`,
  `record_user_outcome`.
- **CACP-L1-05** — Every `inputSchema` **MUST** be a valid JSON Schema, and the
  server **MUST** reject malformed tool arguments with an [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807)
  problem document (`status: invalid_arguments`).

### L2 — Referral lifecycle

- **CACP-L2-01** — `propose_referral` **MUST** return a persisted referral with
  a `referralId`, `status: "proposed"`, and a `userConsentRequired` flag.
- **CACP-L2-02** — `list_referrals` **MUST** return previously proposed
  referrals for the owning user.
- **CACP-L2-03** — `update_referral_status` **MUST** apply legal lifecycle
  transitions (`proposed → accepted | declined | expired`;
  `accepted → followed_up | declined | expired`; terminal: `expired`).
- **CACP-L2-04** — The server **MUST** reject an illegal transition (e.g.
  `proposed → followed_up`) rather than silently applying it.
- **CACP-L2-05** — Referrals **MUST** be tenant-isolated: a user **MUST NOT**
  read or mutate another user's referral (the server returns `not_found`, never
  leaking existence).

### L3 — Consent & audit

- **CACP-L3-01** — `get_user_profile_for_consent` **MUST** return exactly the
  requested scopes (from `identity`, `residence`, `employment`, `cv`,
  `outcomes`, `preferences`) plus `schemaVersion` and `consentRecordedAt`, and
  **MUST NOT** include unrequested scopes.
- **CACP-L3-02** — The server **MUST** reject an unknown consent scope
  (`status: invalid_arguments`).
- **CACP-L3-03** — The returned profile **MUST** validate against the published
  [civic-profile schema](https://helpmefindthejob.org/.well-known/civic-profile.schema.json)
  (served at `/.well-known/civic-profile.schema.json`).
- **CACP-L3-04** — Every cross-agent tool call **MUST** be recorded in a
  tamper-evident (HMAC-chained) audit log, attributed to the composing agent
  (`clientInfo.name` → `composition_source`), and the chain **MUST** verify.

---

## 3. The portable civic profile

The consent-bound profile is the cross-agent data contract. Its machine-readable
shape is published at `/.well-known/civic-profile.schema.json` (JSON Schema
Draft 2020-12) and pinned to the implementation by
`tests/test_civic_profile_schema.py`. Scope blocks are returned only when
requested; `additionalProperties` is permitted for forward-compatible additive
evolution.

---

## 4. Versioning & deprecation

- The tool catalogue follows SemVer independently of the MCP protocol version
  and of this CACP version. Additive changes bump MINOR; breaking changes bump
  MAJOR and **MUST** retain the prior surface for at least one MINOR cycle so
  older consumers degrade gracefully.
- CACP itself versions via this document (`cacp-vX.Y.md`). The conformance
  harness reports the CACP version it tested.

---

## 5. Running the conformance suite

```console
$ python -m conformance.cacp            # human-readable PASS/FAIL summary
$ python -m conformance.cacp --json     # machine-readable report
```

Point it at any candidate MCP server (the reference server is the default). The
report cites each `CACP-Ln-NN` id. The reference implementation's conformance is
itself pinned by `tests/test_cacp_conformance.py`.

---

## 6. Provenance

CACP formalises the composition design developed across
[`09-mcp-composition.md`](https://github.com/maksodf/helpmefindthejob/blob/main/docs/grant/09-mcp-composition.md),
[`agent-architecture.md`](../agent-architecture.md), and the federated `mesh/`.
Standards anchored: MCP `2024-11-05`, JSON Schema 2020-12, schema.org
JobPosting, ESCO/ISCO (via `escolib`), EURES, ISO 8601, ISO 639-1, RFC 7807.
