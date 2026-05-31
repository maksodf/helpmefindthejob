# Housing reference agent — a real MCP composition with Helpmefindthejob

> The directory name `housing-stub-client/` is **legacy**. What runs here
> is a *real* composition, not a stub: an independent civic agent (a
> housing-search agent) composes with Helpmefindthejob entirely over the
> Model Context Protocol, receives **real consent-scoped profile data**,
> drives the **full referral lifecycle**, and the run **proves the audit
> chain**. Only the housing-search listings themselves are illustrative.

This is the runnable proof behind the architectural claim that "the MCP
server is composable with parallel civic agents"
([`09-mcp-composition.md`](../../docs/grant/09-mcp-composition.md)). A
production integration with an external housing-agent collaborator is a
separate, partner-dependent track (Decision 20 Option B); this reference
agent makes the *composition mechanics* — consent, lifecycle, audit —
real and replayable today.

---

## What is real (replay it and check)

- **Transport** — JSON-RPC over stdio against the actual `mcp_server.py`,
  the same wire Claude Desktop / Cursor / Cline use.
- **Consent-bound profile handoff** — `get_user_profile_for_consent`
  returns the seeded user's **real stored civic profile** (target roles,
  languages, locale, location), scope-filtered to least privilege — not
  null placeholders.
- **Full referral lifecycle** — `propose_referral` → `list_referrals` →
  `update_referral_status` (proposed → accepted), persisted server-side.
- **Tamper-evident audit trail** — every tool call emits an EU-AI-Act
  Article-12 `mcp_tool_invocation` record attributed to the composing
  agent (`composition_source`); the demo reads the log back and runs
  `verify_chain()` to prove the HMAC chain is intact.

## What is illustrative (stated honestly)

The housing-search recommendation logic (three hard-coded listings). The
point of this example is the *composition* — consent + lifecycle + audit
— not a housing-search algorithm. The agent does, however, demonstrably
consume the real consented data (e.g. clinical target roles prioritise
clinic-proximate listings).

---

## The two composition modes

### Mode 1 — Sequential handoff (full referral lifecycle)

The housing agent detects an employment-context concern it can't resolve,
calls `propose_referral` on Helpmefindthejob, lists the persisted
referral, and — on user opt-in — advances it with
`update_referral_status`. The user retains the choice
(`userConsentRequired`).

### Mode 2 — Consent-bound profile-shared composition

With explicit, least-privilege consent, the housing agent calls
`get_user_profile_for_consent` and tailors its recommendations using the
real employment context returned. The agent requests only the scopes it
needs.

---

## How to run it

From the repository root:

    python examples/housing-stub-client/main.py

You'll see the MCP handshake, `tools/list` returning the **15-tool**
catalogue, the full Mode 1 referral lifecycle, the Mode 2 consent handoff
carrying real data, and a final audit-trail section ending in
`verify_chain() → ok=True`. The demo asserts each of these, so a
non-zero exit means the composition contract drifted. No external
services or API keys are needed; total runtime is a few seconds.

---

## License

Apache 2.0 — same as the rest of the project. Re-use freely.
