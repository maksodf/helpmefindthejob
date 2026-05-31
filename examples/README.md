# Examples — composing with Helpmefindthejob

This directory contains worked examples of how other open civic
agents compose with Helpmefindthejob through its MCP server. They
exist for two reasons:

1. **Show the composition pattern.** The Helpmefindthejob MCP server
   is designed to compose with parallel civic agents (housing,
   healthcare, residency, education). The composition modes are
   specified in [`docs/grant/09-mcp-composition.md`](../docs/grant/09-mcp-composition.md);
   the examples here are runnable demonstrations of those modes.
2. **Lower the barrier for new agents.** A new project that wants to
   compose with Helpmefindthejob can copy one of these examples,
   swap their own logic in, and have a working integration in
   minutes rather than reading the protocol spec from scratch.

---

## What's here

### `housing-stub-client/` — local reference/stub housing client (composition mechanics)

A **local reference/stub** housing client — **not** a live external civic
agent — that composes with Helpmefindthejob over MCP, demonstrating the
**sequential handoff** (Mode 1, full referral lifecycle) and
**consent-bound profile-shared composition** (Mode 2) end-to-end against a
real MCP server subprocess. The composition *mechanics* are real: the run
carries real consent-scoped profile data and proves the EU-AI-Act
Article-12 audit chain (`verify_chain`). The housing agent itself is a stub
and the housing listings are illustrative; a live external housing-agent
integration is future work (Option B below).

**Scope note (Decision 20):** the maintainer does not self-build a
production Phase-1 housing *product*. A production integration with an
external housing-agent collaborator is Option B, pending a confirmed
collaborator. This reference agent makes the composition *mechanics* —
consent, lifecycle, audit — real and replayable today, without
committing the project to an out-of-scope housing product.

Run it:

    python examples/housing-stub-client/main.py

Read about it in [`housing-stub-client/README.md`](housing-stub-client/README.md).

---

## Building a new composing agent

The blueprint is the same regardless of domain (housing, healthcare,
residency, energy benefits, etc.):

1. Decide which composition mode fits — sequential handoff (lowest
   coupling), profile-shared (medium coupling), or shared-runtime
   (highest coupling). See
   [`09-mcp-composition.md`](../docs/grant/09-mcp-composition.md)
   for the criteria.
2. Spawn the Helpmefindthejob MCP server as an stdio subprocess
   (it's a Python module — `python mcp_server.py`).
3. Send the standard MCP handshake (`initialize` →
   `notifications/initialized`).
4. Call the tools that fit your composition mode:
   - Mode 1 (sequential): mostly `propose_referral`.
   - Mode 2 (profile-shared): `get_user_profile_for_consent` with
     the scopes the user has agreed to share, then your own logic.
   - Mode 3 (shared-runtime): a richer set including watchlist +
     outcomes tools.
5. Respect user consent at every step. Never persist data the user
   hasn't explicitly agreed to share.

The MCP server's catalogue is also queryable over HTTP at
`/mcp/schemas.json` if you want to discover the tools without
running stdio first.

---

## Adding a new example

Open-source contribution welcome. The bar:

- The example must run end-to-end with a single command and no
  pre-installed services.
- It must include a `README.md` explaining what it demonstrates and
  why.
- It must include at least one test under `tests/` that exercises
  the example and asserts the expected output structure.
- Apache 2.0 licensed; SPDX header on each file.

See CONTRIBUTING.md for the full process.
