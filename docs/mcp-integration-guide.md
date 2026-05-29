<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# MCP integration guide

**Audience**: developers who want to call Helpmefindthejob from Claude Desktop, Cursor, Windsurf, Codex CLI, or any other [Model Context Protocol](https://modelcontextprotocol.io) client. Pairs with [`docs/mcp-server.md`](mcp-server.md) (the operational reference) and [`docs/grant/09-mcp-composition.md`](grant/09-mcp-composition.md) (the composition spec).

**What this gets you**: a working MCP server that exposes Helpmefindthejob's civic-employment knowledge to any MCP-aware AI client. You ask Claude "what jobs would fit this CV in Berlin?" and Claude calls Helpmefindthejob's `find_jobs` tool, gets a structured answer, and renders it.

---

## Quick start (Claude Desktop on macOS)

```bash
# Clone + boot the project (see self-host-tutorial.md for full setup)
git clone https://github.com/maksodf/helpmefindthejob.git
cd helpmefindthejob
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Test the MCP server boots
python3 mcp_server.py --self-check
# Expected: {"ok": true, "tools": 13, "protocol": "2024-11-05"}
```

Then add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "helpmefindthejob": {
      "command": "python3",
      "args": ["/absolute/path/to/helpmefindthejob/mcp_server.py"],
      "env": {
        "HELPMEFINDTHEJOB_DATA_DIR": "/Users/you/Library/Application Support/Helpmefindthejob",
        "HELPMEFINDTHEJOB_AUDIT_SALT": "<base64-32-bytes>"
      }
    }
  }
}
```

Restart Claude Desktop. The `🔧` icon in the chat composer should show "15 tools available" for helpmefindthejob. Ask: "Find me remote frontend jobs in Berlin for someone with React and TypeScript experience."

---

## Quick start (Cursor IDE on any platform)

In `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "helpmefindthejob": {
      "command": "python3",
      "args": ["/absolute/path/to/helpmefindthejob/mcp_server.py"]
    }
  }
}
```

Reopen Cursor. The MCP panel (Cmd-Shift-P → "MCP: List Tools") should show the helpmefindthejob entries.

---

## Quick start (Windsurf)

`~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "helpmefindthejob": {
      "command": "python3",
      "args": ["/absolute/path/to/helpmefindthejob/mcp_server.py"]
    }
  }
}
```

Restart Windsurf. Cascade chat shows the tool catalogue under "External tools".

---

## Quick start (Codex CLI)

Codex CLI auto-discovers MCP servers from `~/.codex/mcp.json`:

```json
{
  "servers": {
    "helpmefindthejob": {
      "transport": "stdio",
      "command": ["python3", "/absolute/path/to/helpmefindthejob/mcp_server.py"]
    }
  }
}
```

After saving, run `codex --list-tools` to confirm registration.

---

## The 15-tool catalogue

The exhaustive list (with JSON-Schema input contracts) lives at [`docs/mcp-server.md`](mcp-server.md) and is also reachable via `tools/list` JSON-RPC against the running server. The headline tools:

| Tool | Purpose |
|---|---|
| `find_jobs` | Search across configured aggregators + the user's company watchlist. Returns `DiscoveredJob[]` with stable IDs. |
| `score_fit` | Score a job against a profile across 4 criteria (skills + experience + location/language + friction-fit). Returns a 0–100 integer + reason + gaps. |
| `tailor_cv` | Produce a per-section CV-edit suggestion list for a given job. Returns structured edits, not freeform prose. |
| `draft_letter` | Draft a DACH-norm motivation letter that proactively names the persona's friction context (Anerkennung, Blue Card, etc.). |
| `query_esco_skill` | Look up an ESCO skill / occupation node. Useful for credential-translation flows. |
| `propose_referral` | Suggest a referral to a sibling civic agent (housing, healthcare, residency, education) for handoffs the system cannot complete itself. |
| `get_user_profile_for_consent` | Read the consented subset of the user's profile (encrypted-at-rest fields are NOT exposed without explicit consent flag). |
| `record_user_outcome` | Log a structured outcome event (interview booked, application replied, offer received) for the bias-methodology cohort tracker. |
| `export_eures_compatible` | Project a user's open positions into the EURES open-data feed schema. |
| ...plus 4 more (full catalogue at `docs/mcp-server.md`) | |

Every tool's input is JSON-Schema-validated; malformed calls return a structured `INVALID_PARAMS` JSON-RPC error rather than a 500. Every tool's output is documented as a TypeScript-style interface in the catalogue doc.

---

## Composition example — chained agent flow

A common civic-tech composition: the user asks for jobs in Berlin, then for help with the relocation aspect.

```text
User → Claude (orchestrator)
  ├── helpmefindthejob.find_jobs(role="Krankenpfleger", location="Berlin")
  │     → 10 matches
  ├── helpmefindthejob.score_fit(job=#1, profile=CURRENT_USER)
  │     → 82/100 (skills 21, experience 19, location/language 20, friction 22)
  ├── helpmefindthejob.draft_letter(job=#1, profile=CURRENT_USER)
  │     → "Sehr geehrte Damen und Herren, ich bewerbe mich auf die …"
  └── helpmefindthejob.propose_referral(domain="housing", context="relocating to Berlin from Tunis for job offer")
        → { "agent": "your-civic-housing-agent", "handoff": { ... } }
User ← chained response (jobs + scoring + draft letter + housing handoff hint)
```

The `propose_referral` tool is the load-bearing composition primitive: it returns a structured handoff payload that the orchestrator can route to a sibling civic agent's MCP server. The two agents never talk directly — the orchestrator brokers, the user controls consent at each handoff.

---

## Authentication and consent

The MCP server runs in the user's local environment (`stdio` transport); there is no network-exposed authentication layer because the server only sees calls from the user's own machine. **Important**: do not expose `mcp_server.py` over a network without adding your own auth layer.

For tools that read user-owned profile data (`get_user_profile_for_consent`, `tailor_cv`, `draft_letter`), the server enforces a per-call consent flag against the user's profile state. The user grants consent by signing into the SPA at `http://127.0.0.1:8765` (or their self-hosted instance URL) and toggling the AI consent preference.

---

## Schema versioning

The MCP catalogue follows semver. The server advertises its catalogue version in `serverInfo.version` so a client can detect schema drift. Currently: `0.2.0`. Breaking schema changes will bump the major; additive changes bump the minor; bugfix-only changes bump the patch.

Clients targeting an older catalogue version: pin the version in your client config and the server will refuse calls to newer-schema tools. We do not back-port new tools to older catalogue versions.

---

## Live integration test

Run the upstream MCP composition smoke test against your locally-installed server:

```bash
python3 -m unittest tests.test_phase11_mcp -v
```

Expected: all tests pass (the suite covers tool catalogue completeness + JSON Schema validation + protocol-version handshake). If any fail, your `pip install -r requirements.txt` likely missed a dependency.

---

## What this guide does NOT cover

- The operational reference for `mcp_server.py` itself (transport, JSON-RPC methods, server-info fields) — see [`docs/mcp-server.md`](mcp-server.md)
- The strategic composition narrative (why Helpmefindthejob ships MCP at all, the Redwax-pattern thinking) — see [`docs/grant/09-mcp-composition.md`](grant/09-mcp-composition.md)
- Building your own MCP server from scratch — see <https://modelcontextprotocol.io/quickstart/server>
- Connecting non-MCP clients (REST API, websocket, gRPC) — use the public HTTP API at `/api/*` instead; see [`docs/api-client-examples.md`](api-client-examples.md)
