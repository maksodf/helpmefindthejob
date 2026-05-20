# Claude Desktop manual walk — PART 7 Loop 23

Date: 2026-05-21
Audience: NLnet evaluators, operator (Fouad), external maintainers

This document captures the **manual procedure** for registering the
`helpmefindthejob` MCP server with Anthropic's Claude Desktop and
exercising it through the real production-class MCP client. It is the
human-driven companion to the automated harness work (Loops 20–22).

The automated suite proves protocol compliance end-to-end via stdio
JSON-RPC (96 tests across `test_phase11_mcp_input_validation` /
`test_phase11_mcp_tools_v2` / `test_phase12_mcp_integration_e2e` /
`test_mcp_per_tool_matrix` / `test_composability_flows`). This walk
proves the **same surface works inside a real, GUI-driven MCP client
on macOS** — the canonical user-of-tools experience the grant
narrative depends on.

---

## Why a manual walk in addition to the automated suite

The automated harness boots `mcp_server.py` as a subprocess and
exchanges JSON-RPC messages directly. That covers everything on the
wire. What it does **not** cover, but Claude Desktop does:

1. **Real MCP-client config parsing** — Claude Desktop reads
   `claude_desktop_config.json` and spawns the server itself. The
   environment-variable plumbing, working-directory handling, and
   restart-on-crash behavior all live in Claude Desktop, not our code.
2. **User-visible tool listing UX** — the operator sees the 13 tool
   descriptions in Claude Desktop's "Available tools" panel. Drift
   between schema descriptions and reality surfaces immediately.
3. **Schema enforcement client-side** — Claude Desktop refuses to send
   malformed `tools/call` payloads before they hit the wire. Confirms
   our schema is `Draft-7` compliant from the client's perspective.
4. **Audit-log emission under a real workload** — every tool call
   emits `mcp_tool_invocation` to the audit log; the manual walk
   produces real events with the same shape an external auditor would
   see.

---

## Setup

### 1. Locate the Claude Desktop config

```sh
# macOS:
open ~/Library/Application\ Support/Claude/
# The file is claude_desktop_config.json
```

If the file does not exist yet, create it with `{ "mcpServers": {} }`.

### 2. Register helpmefindthejob as an MCP server

Add the `helpmefindthejob` block to `mcpServers`:

```json
{
  "mcpServers": {
    "helpmefindthejob": {
      "command": "/path/to/python3",
      "args": [
        "/path/to/NasserMCPserver/mcp_server.py"
      ],
      "env": {
        "HELPMEFINDTHEJOB_DATA_DIR": "/path/to/walk-data-dir",
        "HELPMEFINDTHEJOB_AUDIT_SALT": "<32-byte-base64>"
      }
    }
  }
}
```

Replacement values for this branch / this machine:

| Placeholder | Value |
|---|---|
| `/path/to/python3` | `/Users/fouad./miniconda3/bin/python3` |
| `/path/to/NasserMCPserver/mcp_server.py` | absolute path to this repo's `mcp_server.py` |
| `/path/to/walk-data-dir` | dedicated walk dir, e.g. `/tmp/claude-desktop-walk-2026-05-21` |
| `<32-byte-base64>` | generate with `python3 -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"` |

**Never** put `GHOST_API_KEY`, real AI provider keys, or production
salts into this file. Walk-only credentials, tempdir storage.

### 3. Restart Claude Desktop

`Cmd+Q` and reopen. On startup Claude Desktop spawns the `mcp_server.py`
subprocess and exchanges `initialize` + `tools/list` automatically.

### 4. Verify the 13 tools are surfaced

Open the "Available tools" / "MCP" panel in Claude Desktop. Expected:

```
helpmefindthejob (13 tools)
  - suggest_relevant_companies
  - add_company_to_watchlist
  - find_company_career_page
  - scan_company_career_page
  - extract_direct_jobs_from_company_site
  - import_discovered_job
  - deduplicate_discovered_jobs
  - get_company_watchlist_summary
  - get_user_profile_for_consent
  - propose_referral
  - query_esco_skill
  - export_eures_compatible
  - record_user_outcome
```

If the count is wrong, check `/tmp/claude-desktop-walk-2026-05-21/`
for the server stderr.

---

## The walk: an operator drives Aïcha's composability flow through Claude

The operator opens a new Claude Desktop chat and types something like:

> Aïcha is on the §16d Anerkennungsweg. She is a Tunisian nurse looking
> for clinical placements in Berlin where she can complete her German
> nursing recognition. Use the helpmefindthejob MCP tools to:
>
> 1. Find the ESCO occupation code for Pflegehelfer
> 2. Suggest healthcare-management companies in Berlin
> 3. Add the top suggestion to her watchlist
> 4. Tell me what scopes are available for sharing her profile with a
>    housing agent
> 5. Propose a referral to housing-agent so she can find housing close
>    to wherever she gets placed

Claude (the model, in Claude Desktop) reads the prompt + tool catalogue
and orchestrates calls to:
- `query_esco_skill(query="Pflegehelfer", type="occupation")`
- `suggest_relevant_companies(targetRoles=["Pflegehelfer"], industry="healthcare", location="Berlin")`
- `add_company_to_watchlist(...)` for one suggestion
- `get_user_profile_for_consent(userId, scopes=["identity","residence","employment"])`
- `propose_referral(userId, targetAgent="housing-agent", reason=...)`

The composition pattern matches Loop 22 Flow 1 exactly, but is now
**driven by a real foundation model orchestrating MCP calls in
response to a natural-language user request**. The grant narrative
hinges on this: civic-commons knowledge captured as MCP tools is usable
by any modern AI agent without our application code in the loop.

### Evidence to capture

For the grant pack, capture:

1. **Screenshot of the Claude Desktop tool panel** showing 13 tools
   listed under `helpmefindthejob`. File:
   `claude-desktop-tool-panel.png` (operator captures manually)
2. **Markdown transcript** of the Claude chat — Claude's
   natural-language replies + the tool calls it chose + the
   structured-data responses it received. The chat-export feature in
   Claude Desktop produces a JSON transcript; convert to markdown via
   `scripts/format_claude_transcript.py` (Phase 2 backlog item — for
   now, paste manually).
3. **Audit-log tail** from the walk directory's `audit_log.jsonl`
   showing real `mcp_tool_invocation` events for each tool the model
   chose to call. This is the AI Act Article 12 audit trail under a
   real workload.

### Failure modes worth screenshotting

- Tool description renders truncated / misformatted in the panel
- Claude refuses a tool call because schema-validation fails client-side
- Server subprocess crashes on first call (would surface a Claude
  Desktop banner)

---

## Status

Documented and runnable on operator hardware. The automated harness
(Loops 20–22) already proves the wire-level surface is correct; this
walk proves the **GUI client experience** is correct.

This document is the procedure. The artifacts (screenshots, transcript,
audit-log tail) are operator-captured and stored under
`docs/grant/mcp-walks-2026-05-21/claude-desktop-artifacts/`.

Phase 2 candidate (#79): automate the Claude Desktop walk via the
Ghost-OS MCP — drive the Claude Desktop app's accessibility tree
programmatically so the screenshots + transcript regenerate on every
release. Not in scope for the NLnet submission; the manual procedure
+ the automated harness together are sufficient.
