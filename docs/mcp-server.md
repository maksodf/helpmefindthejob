# Helpmefindthejob MCP Server

**Audience**: integrators who want to call Helpmefindthejob from another agent, deployers who want to understand the catalogue contract, NLnet reviewers who want to verify the project's "MCP-composable open civic infrastructure" claim.

**Strategic context** lives in [`docs/grant/09-mcp-composition.md`](grant/09-mcp-composition.md) (composition spec) and [`docs/grant/01-project-brief.md`](grant/01-project-brief.md) (overall positioning). This document is the operational reference for the server itself.

---

## What this is

`mcp_server.py` is a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes Helpmefindthejob's civic-employment capabilities as a small, well-documented tool catalogue. It is the project's **composition surface**: other open civic agents (housing, healthcare, residency, education) can call Helpmefindthejob via the same protocol used by any MCP-aware client (Claude Desktop, Cursor, Continue, Cline, custom JSON-RPC clients), without forking either project.

The current catalogue exposes **fifteen tools**, including the composition-oriented tools (`get_user_profile_for_consent`, `propose_referral`, `list_referrals`, `update_referral_status`, `query_esco_skill`, `export_eures_compatible`, `record_user_outcome`) that let other open civic agents discover, refer, and hand off work.

## Protocol surface

| Field | Value |
|---|---|
| Transport | JSON-RPC 2.0 over stdio |
| MCP `protocolVersion` | `2024-11-05` |
| `serverInfo.name` | `helpmefindthejob` |
| `serverInfo.version` | `0.2.0` (catalogue SemVer; see versioning policy below) |
| Capabilities advertised | `{"tools": {}}` |
| Source | [`mcp_server.py`](https://github.com/maksodf/helpmefindthejob/blob/main/mcp_server.py) (top-level entry point) |
| Tool implementations | [`company_discovery/mcp_tools.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/mcp_tools.py) |
| Tool schemas | `TOOL_SCHEMAS` in the same module (canonical source of truth) |

The supported JSON-RPC methods are:

- `initialize` — version handshake; returns the `protocolVersion`, `serverInfo`, and capabilities.
- `notifications/initialized` — no-op acknowledgement; standard MCP initialise-complete signal.
- `ping` — returns `{}`; useful for liveness checks.
- `tools/list` — returns the full catalogue including each tool's `name`, `description`, and `inputSchema`.
- `tools/call` — invokes a named tool with a JSON-object `arguments` payload. Every payload is **JSON-Schema-validated against the tool's `inputSchema`** before dispatch (see "Argument validation" below).

Anything else returns a JSON-RPC error `-32601` "Unknown method".

## Argument validation (the contract that's actually enforced)

Every `tools/call` payload is validated against the registered tool's `inputSchema` using [`jsonschema.Draft7Validator`](https://python-jsonschema.readthedocs.io/) **before** the tool method is invoked. The validation rules that `inputSchema` advertises in `tools/list` are real: a deployer can write a client against the published catalogue and trust the server to enforce the shape.

Specifically:

- **Missing required field** — returns an RFC 7807 Problem Details payload with `status: "invalid_arguments"`, `violatedRule: "required"`, `validationPath` pointing to the missing field, and `detail` quoting the validator's message. The tool method is not invoked.
- **Wrong type** — same shape with `violatedRule: "type"`.
- **Non-object arguments** — `tools/call` requires `arguments` to be a JSON object; anything else returns the same problem document with `violatedRule: "type"`.
- **Unknown tool name** — returns `status: "unknown_tool"` before any schema lookup.
- **Tool body raises an exception** — wrapped into a Problem Details payload with `status: "tool_error"` and the exception message in `detail`. Tracebacks are not leaked.

**Additional properties policy**: the current catalogue schemas do not set `additionalProperties: false`, so unknown keys pass validation. This is documented and pinned by test (`tests/test_phase11_mcp_input_validation.py::AdditionalPropertiesPolicyTests`). A future catalogue-tightening that flips `additionalProperties: false` is a deliberate decision, not an accident, and will bump the catalogue's MINOR version per the policy below.

## Catalogue versioning policy

The tool catalogue follows [Semantic Versioning](https://semver.org/) independently of the MCP protocol version:

- **MAJOR** — backwards-incompatible change to any tool's input or output schema; removal of a tool; change of `protocolVersion`.
- **MINOR** — addition of a tool; addition of an optional field on an input/output schema; tightening of `additionalProperties` (because clients may have relied on extra fields being silently ignored).
- **PATCH** — bug fixes, performance changes, schema clarifications that do not change validity.

The MCP `protocolVersion` advertised in the `initialize` response is pinned to the version the server has been tested against (currently `2024-11-05`). Upgrading to a newer MCP protocol version is a MAJOR change to the catalogue.

The `/mcp/version` and `/mcp/schemas.json` HTTP endpoints expose the catalogue version and the full schema set without spawning the stdio process.

### Per-tool versioning (since v0.80.0)

In addition to the catalogue-level `serverInfo.version`, every entry in `TOOL_SCHEMAS` carries a per-tool `version` field as of v0.80.0. The field flows through `tools/list` JSON-RPC responses + the per-tool `mcp_server/schemas/<tool>.json` exported files, so an MCP client can pin against a specific tool-version contract:

```jsonc
{
  "name": "find_jobs",
  "version": "0.2.0",
  "description": "...",
  "inputSchema": { ... }
}
```

Tool-version policy:

- The v0.80.0 catalogue ships every tool at the `0.2.0` baseline (the catalogue went from v0.1.0 to v0.2.0 with the post-Phase-1 expansion).
- Future per-tool schema changes bump the individual tool's `version` (MAJOR if backwards-incompatible, MINOR if additive, PATCH if clarifying). The catalogue-level `serverInfo.version` ALSO bumps following its own SemVer rules above.
- A client targeting an older per-tool version that has since been bumped MAJOR should refuse to call the tool until the client is updated — graceful downgrade behaviour described per-client in [`docs/mcp-integration-guide.md`](mcp-integration-guide.md).
- The contract is locked in by `tests/test_mcp_tool_schema_versioning.py` (5 tests: every tool has a version, every version is SemVer-shaped, the v0.2.0 baseline is pinned, the catalogue size of 15 tools is pinned, every tool keeps name + description + inputSchema + version as required keys).

## The 15-tool catalogue (current)

Each tool's full JSON `inputSchema` is the canonical definition in [`company_discovery/mcp_tools.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/mcp_tools.py). This table summarises the required-fields surface and the standards alignment per tool; consult the source for the complete property list and types.

| # | Tool | Required input | Purpose | Standards alignment |
|---|---|---|---|---|
| 1 | `suggest_relevant_companies` | `targetRoles[]`, `industry` | Suggest curated companies from role, industry, location preferences | schema.org Organization |
| 2 | `add_company_to_watchlist` | `userId`, `name`, `websiteUrl` | Persist a company watchlist entry without scanning external pages | schema.org Organization |
| 3 | `find_company_career_page` | `userId`, `companyId` | Resolve a watched company to its public career page (respects `robots.txt`) | — |
| 4 | `scan_company_career_page` | `userId`, `companyId` | Crawl a career page and surface discovered roles | schema.org JobPosting |
| 5 | `extract_direct_jobs_from_company_site` | `userId`, `companyId`, `pageUrl`, `html` | Extract job postings from a fetched career page | schema.org JobPosting |
| 6 | `import_discovered_job` | `userId`, `discoveredJobId` | Persist a discovered job into the user's queue | schema.org JobPosting |
| 7 | `deduplicate_discovered_jobs` | `userId` | Identify and merge duplicate job records | — |
| 8 | `get_company_watchlist_summary` | `userId` | Return the user's watchlist with recent activity | — |
| 9 | `query_esco_skill` | `query` | Look up ESCO skill/occupation codes by free-text query (cross-agent shared taxonomy) | ESCO |
| 10 | `export_eures_compatible` | `userId`, `discoveredJobId` | Export a stored job in EURES-compatible schema fields for cross-deployment interoperability | EURES, schema.org JobPosting |
| 11 | `get_user_profile_for_consent` | `userId`, `scopes` | Return the user's portable civic profile (consented subset) for other civic agents to read | — |
| 12 | `propose_referral` | `userId`, `targetAgent`, `reason` | Emit a structured referral to another open civic agent; the user retains the choice | — |
| 13 | `list_referrals` | `userId` | List referrals issued for a user (optional status filter) | — |
| 14 | `update_referral_status` | `userId`, `referralId`, `status` | Advance a referral's lifecycle status (proposed → accepted → followed_up, …) | — |
| 15 | `record_user_outcome` | `userId`, `jobId`, `outcomeType` | Persist an append-only outcome event (applied / replied / interviewing / offer / rejected / withdrawn) | — |

Optional input fields per tool (full list in the source): `add_company_to_watchlist` accepts `careerPageUrl`, `sector`, `notes`, `watchEnabled`; `scan_company_career_page` accepts `careerPageUrl`; `suggest_relevant_companies` accepts `location`.

## Composition patterns

See [`docs/grant/09-mcp-composition.md`](grant/09-mcp-composition.md) for the full spec. Summary:

1. **Sequential handoff** — agent A identifies an out-of-scope question, calls `propose_referral` on agent B, presents the structured referral to the user, hands over on consent. **Lowest coupling**: each agent runs independently; the only shared surface is the referral protocol. **Available** now.
2. **Profile-shared composition** — multiple agents in the same deployment read the user's portable civic profile via `get_user_profile_for_consent` (with explicit consent). **Medium coupling**: shared profile schema; both agents trust the same persistence layer. **Available** now.
3. **Orchestrated multi-agent conversation** — a meta-orchestrator routes a single conversation between multiple agents. **Highest coupling**, **Phase 2+ scope**.

A reference integration with an open housing agent demonstrates pattern 1 and ships under [`examples/housing-stub-client/`](https://github.com/maksodf/helpmefindthejob/tree/main/examples/housing-stub-client).

## Example client invocations

### Python (stdlib only)

```python
"""Drive the Helpmefindthejob MCP server from a Python client over stdio.

Spawns the server as a subprocess, performs the MCP handshake, lists
tools, and invokes get_company_watchlist_summary. No external
dependencies beyond the Python standard library.
"""
import json
import subprocess
import sys

proc = subprocess.Popen(
    [sys.executable, "mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

def call(message):
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())

# Handshake.
hello = call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
assert hello["result"]["protocolVersion"] == "2024-11-05"

# Catalogue.
catalogue = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
print(f"{len(catalogue['result']['tools'])} tools available")

# Tool invocation. inputSchema is validated server-side; missing
# required fields return an RFC 7807 problem document.
summary = call({
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {
        "name": "get_company_watchlist_summary",
        "arguments": {"userId": "u-123"},
    },
})
print(summary["result"]["content"][0]["text"])

proc.stdin.close()
proc.wait()
```

Sample invalid-argument response (missing `name` + `websiteUrl` on `add_company_to_watchlist`):

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"status\":\"invalid_arguments\",\"type\":\"about:blank\",\"title\":\"Tool arguments failed schema validation\",\"detail\":\"'userId' is a required property\",\"instance\":\"add_company_to_watchlist\",\"validationPath\":\"(root)\",\"violatedRule\":\"required\"}"
    }],
    "isError": true
  }
}
```

### TypeScript

```typescript
/**
 * Drive the Helpmefindthejob MCP server from a Node.js client over
 * stdio. Standard child_process; no external SDK assumed.
 */
import { spawn } from "node:child_process";
import readline from "node:readline";

const proc = spawn("python3", ["mcp_server.py"]);
const rl = readline.createInterface({ input: proc.stdout });
const responses: AsyncIterator<string> = rl[Symbol.asyncIterator]();

async function call(message: Record<string, unknown>) {
  proc.stdin.write(JSON.stringify(message) + "\n");
  const { value } = await responses.next();
  return JSON.parse(value as string);
}

const hello = await call({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {},
});
console.log(`Connected to ${hello.result.serverInfo.name} v${hello.result.serverInfo.version}`);

const catalogue = await call({
  jsonrpc: "2.0",
  id: 2,
  method: "tools/list",
  params: {},
});
console.log(`${catalogue.result.tools.length} tools in catalogue`);

const summary = await call({
  jsonrpc: "2.0",
  id: 3,
  method: "tools/call",
  params: {
    name: "get_company_watchlist_summary",
    arguments: { userId: "u-123" },
  },
});
console.log(JSON.parse(summary.result.content[0].text));

proc.stdin.end();
```

### Curl (HTTP catalogue endpoints)

```bash
# Schema catalogue (planned)
curl -s https://demo.helpmefindthejob.org/mcp/schemas.json | jq '.tools | length'

# Catalogue version (planned)
curl -s https://demo.helpmefindthejob.org/mcp/version | jq '.catalogueVersion'
```

## Audit logging

Every persisting tool emits an entry into `data/admin_audit.log` (one JSON object per line). The audit schema is documented in the EU AI Act Article 12 compliance section of [`docs/grant/10-ai-act-compliance.md`](grant/10-ai-act-compliance.md). Tool invocations that do **not** persist (read-only summaries, schema lookups) are not audited; the audit boundary follows the same persist=True / persist=False split that the journey state machine uses internally.

## Error model

All `tools/call` responses with `isError: true` carry an [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807) JSON document inside the standard MCP `content[0].text` channel. Fields:

| Field | Meaning |
|---|---|
| `status` | One of `invalid_arguments`, `unknown_tool`, `tool_error`. Machine-readable. |
| `type` | URI identifying the problem type. Currently `about:blank` (the catalogue does not yet host a public problem-type taxonomy). |
| `title` | Short human-readable problem name. |
| `detail` | Specific failure message — for validation errors this is the `jsonschema` validator message; for tool errors this is the exception message (without traceback). |
| `instance` | The tool name that triggered the problem. |
| `validationPath` | JSON Pointer-style path to the offending field, or `(root)` if the failure is at the top level. Present only for `invalid_arguments`. |
| `violatedRule` | The JSON Schema keyword that fired (`required`, `type`, etc.). Present only for `invalid_arguments`. |

A deployer can dispatch on `status` for programmatic handling and surface `detail` to a human operator in the UI.

## Operational notes

- **Startup**: `python3 mcp_server.py` from the repository root. The server reads `HELPMEFINDTHEJOB_DATA_DIR` (default `./data`) to locate its SQLite database, which it shares with the web app — meaning MCP tool invocations and web-app interactions see the same persisted state.
- **No HTTP**: the server speaks JSON-RPC over stdio, not HTTP. Embed it as a subprocess of your agent, or wrap it with a process-supervised stdio bridge.
- **Single-process state**: the server is stateless at the request boundary; all state lives in the SQLite database. Multiple clients can connect via multiple subprocess instances pointed at the same `HELPMEFINDTHEJOB_DATA_DIR`.
- **Encryption**: any persisted user data passes through [`company_discovery/crypto_kit.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/crypto_kit.py) at the storage layer. The CV-text column and TOTP-secret column are AEAD-encrypted at rest (ChaCha20-Poly1305 with AAD = user_id; see [`ARCHITECTURE.md`](https://github.com/maksodf/helpmefindthejob/blob/main/ARCHITECTURE.md) and [`SECURITY.md`](https://github.com/maksodf/helpmefindthejob/blob/main/SECURITY.md)).
- **Logging**: stderr is reserved for human-readable diagnostics. Tool invocations + audit entries go to `data/admin_audit.log`.
- **Subprocess integration-test note**: the JSON-RPC-over-stdio integration test at `tests/test_phase12_mcp_integration_e2e.py` previously emitted `ResourceWarning: unclosed file <TextIOWrapper ...>` on shutdown because the test client did not explicitly close the subprocess's stdout/stderr pipes. The test client now closes both pipes plus the tempdir in a `finally` block — verified clean under `python3 -W error::ResourceWarning -m unittest tests.test_phase12_mcp_integration_e2e`. **The production server itself was never affected**; the warning lived entirely in the test harness.

## Where the schemas live

`TOOL_SCHEMAS` in [`company_discovery/mcp_tools.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/mcp_tools.py) is the canonical source. The schemas are JSON Schema Draft 7 documents. When a deployment serves them over HTTP, the `/mcp/schemas.json` endpoint exposes the full catalogue and `/mcp/version` reports the catalogue version (the `demo.helpmefindthejob.org` host shown in the curl examples above is optional reviewer evidence and not guaranteed live at submission time); the stdio `tools/list` call returns the same schemas without any HTTP endpoint.

The schemas are also exported as individual files under `mcp_server/schemas/<tool-name>.json`, so external tooling (linting, code generation) can read them without spawning the Python process. The canonical definitions stay in `mcp_tools.py`; the filesystem export is a build artefact.

## See also

- [`docs/grant/09-mcp-composition.md`](grant/09-mcp-composition.md) — full composition spec and standards alignment
- [`docs/grant/01-project-brief.md`](grant/01-project-brief.md) §8 — technical positioning and MCP composition story
- [`ARCHITECTURE.md`](https://github.com/maksodf/helpmefindthejob/blob/main/ARCHITECTURE.md) — system-level overview with the MCP server in context
- [`STANDARDS.md`](https://github.com/maksodf/helpmefindthejob/blob/main/STANDARDS.md) — every standard the project implements
- [`SECURITY.md`](https://github.com/maksodf/helpmefindthejob/blob/main/SECURITY.md) — vulnerability disclosure and security posture
- [Model Context Protocol homepage](https://modelcontextprotocol.io)
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
- [RFC 7807 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc7807)
- [JSON Schema Draft 7](https://json-schema.org/specification-links#draft-7)
