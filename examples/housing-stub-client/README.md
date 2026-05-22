# Housing-stub-client — composing with Helpmefindthejob

A self-contained example showing how a parallel civic agent (a
housing-search agent, in this case) composes with Helpmefindthejob
through the MCP protocol.

This is the **mock stub** referenced in
[Decision 20](../../docs/grant/04-research-and-decisions.md) and
the Week 2 §2.5 task in
[`02-execution-plan.md`](../../docs/grant/02-execution-plan.md).
It is intentionally not a real housing agent; it is a working
demonstration of the composition pattern so the architectural claim
("the MCP server is composable with parallel civic agents") is
backed by runnable code, not just specification.

If a real housing-agent collaborator confirms (Option B per Decision
20), the stub gets replaced with a real integration in a separate
directory (`housing-agent-integration/`).

---

## What this demonstrates

The two composition modes from
[`09-mcp-composition.md`](../../docs/grant/09-mcp-composition.md):

### Mode 1 — Sequential handoff

The housing agent receives a user query about housing. It detects
the user mentions an employment-context concern that the housing
agent itself cannot resolve. It calls `propose_referral` on the
Helpmefindthejob MCP server, gets back a structured referral
descriptor, and presents it to the user with a "would you like to
follow this referral?" prompt. The user retains the choice.

### Mode 2 — Profile-shared composition

With explicit user consent, the housing agent calls
`get_user_profile_for_consent` on the Helpmefindthejob MCP server
to retrieve the user's employment status. It then uses that
context to filter its own listings (e.g., it excludes listings
that require proof of full-time employment if the user is in a
trial-period role).

The user remains in control: the housing agent must obtain
consent before each fetch, and only requests the scopes it needs.

---

## How to run it

From the repository root:

    python examples/housing-stub-client/main.py

You'll see:

- The MCP server starting up as a stdio subprocess
- The MCP handshake (initialize + initialized)
- `tools/list` returning the 13-tool catalogue
- Mode 1 demo: housing agent calling `propose_referral`, printing
  the structured referral, and simulating user consent
- Mode 2 demo: housing agent calling `get_user_profile_for_consent`
  with the `employment` scope, printing the response, and
  simulating filtering against a mock housing-listing set

Total runtime: a few seconds. No external services needed.

---

## What it doesn't do

- It doesn't include a real housing agent. The housing-side logic
  is a one-file stub that prints what it would do.
- It doesn't persist anything. The Helpmefindthejob MCP server uses
  a tmp data directory for the duration of the demo and cleans up.
- It doesn't run any AI provider. The demo uses the deterministic
  fallback paths of the Helpmefindthejob tools so it's reproducible
  without network access or API keys.

Each of these is intentional — the demo's job is to prove the
**composition surface works**, not to ship a housing product.

---

## License

Apache 2.0 — same as the rest of the project. Re-use freely.
