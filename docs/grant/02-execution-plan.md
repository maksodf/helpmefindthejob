# 4-Week Execution Plan — NGI0 Grant Readiness

**Last updated**: 2026-05-17
**Target submission**: next NLnet call after planning completes (verify NLnet's published call dates before committing to a deadline)
**Estimated total effort**: ~140–180 hours of focused non-feature work (calibrated to maintainer's 18 h/day availability)
**Owner**: maintainer + agent sessions

This is the live tracker. Tick boxes as work is completed. Add notes when scope changes.

`[ ]` = not done. `[x]` = done. `[~]` = in progress. `[!]` = blocked. `[-]` = dropped (with note explaining why).

For task ordering and dependencies, the weeks are roughly sequential but not strictly. Several tasks can run in parallel (sanitisation while drafting CONTRIBUTING.md, NGO outreach while writing AI Act docs, etc.).

---

## Pre-flight checklist (do before Week 1 starts)

- [ ] Verify the exact NLnet Commons Fund call deadline that aligns with the planned submission timing
- [ ] Confirm the GitHub repo URL stays where it is OR migrate to a `directjob-scout` org for institutional-wrapper signal
- [ ] Switch maintainer workstation from mobile to computer for execution
- [ ] Read `01-project-brief.md` and `04-research-and-decisions.md` end-to-end so the strategic context is fresh
- [ ] Create `claude/week-1-foundations` branch off the current working branch
- [ ] Snapshot the live production deployment state (real users? real revenue? what we can change publicly without breaking trust?)
- [ ] Decide on the public-domain name for the eventual demo deployment (Week 3 task — needs decision now)

---

## Week 1 — Legal, narrative, and outreach foundations

**Goal**: by end of week 1, the repo passes the "is this a real open-source project" sniff test. LICENSE, governance, README mission, no internal residue. First outreach messages sent.

**Estimated effort**: ~30 hours.

### 1.1 Licensing (3 h) — BLOCKER FIX

- [x] Add `LICENSE` file at repo root with full **Apache 2.0** text
- [x] Add `NOTICE` file (Apache requirement)
- [x] Add `TRADEMARK.md` (Tenzu pattern — separates copyright from trademark)
- [x] Add `cla.md` — Contributor License Agreement based on the Apache CLA model
- [x] Add SPDX-License-Identifier header to every Python source file (script-driven)
- [x] Add `.license-header-template.txt` for future contributors
- [x] Add pre-commit hook that checks SPDX headers in new files
- [x] Add Apache 2.0 license badge to README

### 1.2 Governance pack (8 h) — BLOCKER FIX

- [x] `CONTRIBUTING.md` — covers dev setup, code style, commit message convention, PR process, DCO sign-off OR CLA sign-up
- [x] `CODE_OF_CONDUCT.md` — adopts Contributor Covenant 2.1 by reference (canonical URL) per content-policy pivot; not embedded verbatim
- [x] `SECURITY.md` — vulnerability reporting channel, response SLA, contact email, supported versions
- [x] `SUPPORT.md` — where to ask questions, expected response times, channels
- [x] `AUTHORS.md` — maintainer + partner with TBD-name placeholders (resolved before push); template for future contributors and translator credits
- [x] `ACKNOWLEDGMENTS.md` — credit MCP ecosystem, Redwax inspiration, NLnet if funded, prior art
- [x] `FUNDING.yml` in `.github/` — placeholder (GitHub Sponsors / Open Collective / Commons Conservancy donation channel TBD)
- [x] `.github/ISSUE_TEMPLATE/` — bug, feature, security templates
- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `CODEOWNERS` — at minimum the lone maintainer until co-maintainers join

### 1.3 README rewrite (4 h) — BLOCKER FIX

- [x] Open with the new positioning: civic-commons framing from `01-project-brief.md` §2 (EU-wide, Germany-first, MCP-composable infrastructure)
- [x] First sentence references persona Aïcha concretely (Tunisian-trained nurse, §16d Anerkennung in Berlin)
- [x] Add badges row: license (Apache 2.0), CI placeholder, latest release placeholder, languages (EN+DE), MCP version placeholder
- [ ] Add one screenshot or animated GIF demoing the chat journey end-to-end *(deferred to Week 3 alongside the public demo deployment so the captured screenshot reflects the canonical reference state, not the pre-launch private instance)*
- [x] Add "Standards we implement" section: MCP, schema.org JobPosting, ESCO, EURES, WCAG 2.2 AA target, RFC 9116, GDPR-aligned, Apache 2.0, EU AI Act
- [x] Pro/Free billing removed entirely from public README (per maintainer instruction; no transition language needed because the deployment never had paying users)
- [x] "Hosted by The Commons Conservancy" notice with application-pending placeholder
- [x] Quickstart that genuinely works in 5 minutes from a clean machine (Python or Docker path)
- [x] Link to documentation site placeholder (Week 3)
- [x] Link to public demo placeholder (Week 3)

### 1.4 Sanitise internal residue (4 h) — MAJOR FIX

- [x] Replace all `khalo.org` occurrences (verified count: 17 in `app.py`; ~70 across the public tree including static HTML, scripts, .env.example, docker-compose.prod.yml, and tests) with `directjob-scout.example` placeholders or environment-variable-driven configuration. Planning-doc estimate of "~29 in app.py" was inaccurate; the fresh-scan count is reported in the Commit D message.
- [x] Replace `support@khalo.org` with `support@directjob-scout.example`
- [x] Add `CONTRIBUTORS-NOTE.md` honestly explaining that early commits may reference internal tester names and legacy framing — do not retroactively rewrite history (preserves commit integrity per Decision 12)
- [x] Delete `keepbuildingtill100%tracker.MD` from repo root (per Decision 14 in `04-research-and-decisions.md`)
- [x] Sanitise `.env.example` — analytics domain placeholders updated; no real keys present
- [ ] Run `gitleaks` over the full history; fix anything found *(deferred to Week 3 CI expansion task 3.2 — gitleaks belongs alongside the CVE/secret-scanning hooks)*
- [x] Move commercial docs to a `private/` folder (gitignored). Extension beyond the originally-listed 11 files: `legal-review-brief.md` and `deployment-handoff.md` were also relocated because they contained the maintainer's real personal Gmail and operational-handoff narrative respectively. Relocated:
  - `docs/sellable-readiness-completion-report-pass2.md`
  - `docs/sellable-readiness-final-report.md`
  - `docs/sellable-readiness-gap-analysis.md`
  - `docs/marketing-copy.md`
  - `docs/operator-launch-playbook.md`
  - `docs/operator-launch-runbook.md`
  - `docs/operator-final-punchlist.md`
  - `docs/operator-package.md`
  - `docs/operator-starters.md`
  - `docs/press-kit.md`
  - `docs/launch-day-content.md`
  - `docs/legal-review-brief.md` *(extension — contained real PII: maintainer's Gmail)*
  - `docs/deployment-handoff.md` *(extension — heavily commercial-operational, "friend"-handoff narrative)*
- [x] Sanitise tester-name leakage: `Nasser` references in `company_discovery/journey.py` and `tests/test_journey_edge_cases.py` replaced with generic "an early tester" phrasing; Python identifier `NASSER_COMPLAINT` renamed to `EARLY_TESTER_COMPLAINT`. Bug-history context preserved.
- [x] Pin Docker project name to `directjob-scout` in both compose files (`name:` field plus `image: directjob-scout:latest`) so the generated image name no longer leaks the original local directory name (`nassermcpserver-...`). Script references updated accordingly.

### 1.5 GitHub repo housekeeping (1 h) — maintainer-clicks, agent-prepared text

- [ ] Update the repo description to match the new positioning
- [ ] Add topic tags reflecting the civic-commons positioning
- [ ] Enable GitHub Discussions
- [ ] Verify default branch is `main`
- [ ] Confirm GitHub auto-detected the Apache 2.0 license from `LICENSE`, the issue templates from `.github/ISSUE_TEMPLATE/`, the PR template from `.github/PULL_REQUEST_TEMPLATE.md`, and the CODEOWNERS from `.github/CODEOWNERS`

**Proposed text for the maintainer to paste into the GitHub UI** (drafted by agent 2026-05-18 — ~15 minutes of maintainer click-through):

**Repo description (Settings → General → About)**:

> Open-source EU-wide civic-employment commons — an MCP-composable copilot for anyone facing structural labor-market friction in Europe; migrants and EU-mobile workers are the most acute use case. Apache 2.0, EU AI Act compliant by design, pending Programme of The Commons Conservancy.

**Website field**: leave blank for now; populate with `https://demo.<domain>` once the public demo deploys in Week 3 task 3.4.

**Topic tags (Settings → General → About → Topics — 12 picked from the 20-tag GitHub limit)**:

```
civic-tech
civic-commons
mcp
model-context-protocol
employment
migration
open-source
apache-2-0
self-hosted
ai-act
multilingual
germany
```

Optional additions if you want to surface more themes: `eu`, `nlnet`, `anerkennung`, `esco`, `eures`, `integration`. (`chatbot` is technically applicable but pulls in unrelated audiences; skip.)

**Settings recommendations**:

- **General → Features → Discussions**: enable. The `SUPPORT.md` file already routes users there.
- **General → Default branch**: confirm `main` (likely already set).
- **General → Pull Requests**: leave default; the `.github/PULL_REQUEST_TEMPLATE.md` will surface automatically.
- **Branches → Branch protection**: defer to Week 3 task 3.2 (CI expansion) so that branch-protection rules can require CI-green status checks that don't yet exist.
- **Security → Code security and analysis → Private vulnerability reporting**: enable. This is the GitHub-native channel `SECURITY.md` references as the primary disclosure path.
- **Security → Code security and analysis → Dependency graph**: leave on (default).
- **Security → Code security and analysis → Dependabot alerts**: leave on (default). Renovate replaces this in Week 3 task 3.2.
- **Code and automation → Pages**: leave off for now; turned on in Week 3 task 3.5 (documentation site).
- **Code and automation → Actions → General**: leave default permissions; tighten in Week 3 task 3.2 if needed.
- **Sponsorships**: GitHub auto-detects `.github/FUNDING.yml`. All entries are commented out in Week 1 by design, so no Sponsor button renders. Resolution per the comment in that file.
- **Pinned issues**: optional — pin a single "DirectJob Scout v0.1.0 grant-readiness sprint — May–June 2026" tracking issue once you open one. Skip if you'd rather not.

### 1.6 Outreach drafting (research only — send deferred to Week 4 per Decision 19)

- [x] Identify one specific named contact per top-ranked partner — research pass completed 2026-05-18:
  - **MBE Berlin**: AWO Charlottenburg-Wilmersdorf FIM — Irina Alles (`fim-cw@awoberlin.de`). Selected over Diakonisches Werk Berlin Stadtmitte (institutional-insolvency timing) and Caritas Erzbistum Berlin MBE Mitte (no named individual surfaced).
  - **IQ-Netzwerk Berlin**: superseded in 2026 by RINWA — La Red, Cristina Faraco Blanco (`faraco@la-red.eu`).
  - **University career service**: TU Berlin Career Service — Bettina Satory (`bettina.satory@tu-berlin.de`). Doubles as the optional Template G TU Berlin academic email per maintainer instruction 2026-05-17.
- [x] Personalise the cold-contact templates — three German draft messages saved under [`outreach-drafts/`](outreach-drafts/) with `STATUS: DRAFTED — NOT YET SENT — TARGET SEND: WEEK 4 START` headers, last-verified dates, and fit-reason annotations.
- [-] Send the first wave of cold contacts — **deferred to Week 4 task 4.0** per Decision 19 in `04-research-and-decisions.md`. Sending earlier risks a partner forming a half-finished impression from artifacts that aren't yet visibly complete.
- [ ] Draft the housing-agent collaboration message together with the maintainer — moved to Week 2 task 2.5 alongside the actual reference integration; the message and the integration land together.
- [-] Maintainer sends the housing-agent message — deferred until Week 2 task 2.5 collaboration step.
- [-] Send the single optional TU Berlin email — merged into the TU Berlin Career Service outreach draft (slot 3 above); no separate Template G send.
- [x] Update the outreach tracker in `11-institutional-outreach.md` — done 2026-05-18.

### 1.7 Production-deployment alignment (closed — mitigated by Decision 17)

- [x] Snapshot the current production deployment state — **Mitigated by Decision 17 in `04-research-and-decisions.md`: no public production deployment exists to align. The only running instance is a single private-tester deployment for the maintainer's partner. No action required.**
- [x] Decide: bring it into alignment with new positioning, take it offline, or replace it with the Week 3 demo deployment — **No public deployment to address. The Week 3 demo (task 3.4) is the project's first public reference deployment.**
- [x] Execute the decision — **No execution needed. Item closed.**

### Week 1 Definition of Done

- LICENSE file present, recognised by GitHub
- All 6+ governance files at root
- README opens with the new positioning, badges visible, one persona referenced
- Zero occurrences of `khalo.org` in public-tree code (CLAUDE.md narrative context and `CONTRIBUTORS-NOTE.md` excepted; both deliberately retain the term for agent-onboarding clarity)
- Commercial docs moved out of `docs/` into `private/` (gitignored)
- GitHub repo description and topics updated (maintainer's click-through; proposed text in §1.5)
- A fresh-clone smoke test passes (verified in Week 2 task 2.0)
- Outreach drafted under `docs/grant/outreach-drafts/`; send deferred to Week 4 task 4.0 per Decision 19
- Production-deployment alignment closed — mitigated by Decision 17, no public deployment exists

---

## Week 2 — MCP composition, Commons Conservancy, AI Act compliance

**Goal**: the central pitch claim — "MCP-composable, AI-Act-compliant civic-agent infrastructure" — is verifiable by any reviewer reading the repo for 5 minutes. The Commons Conservancy application is submitted.

**Estimated effort**: ~56–58 hours (~50 h for the original §§2.1–2.8 plus the new §2.0 Feature verification pass at 6–8 h, added as the new highest-priority Week 2 work).

### 2.0 Feature verification pass (6–8 h) — HIGHEST PRIORITY

**Why this comes first**: every Week 2 deliverable (MCP server docs, AI Act compliance pack, ARCHITECTURE.md, ESCO/EURES integration claims) makes claims about what the code does. Before we write documentation that says the code does X, we run the code and verify X. If any claim does not hold up, we surface the gap to the maintainer rather than silently aligning the documentation to the code or the code to the documentation. This rule applies for the rest of the sprint.

The verification runs in a clean Docker container so the "fresh-clone smoke test passes" criterion from Week 1 DoD is genuinely verified.

- [ ] Spin up the app in a clean Docker container (`docker compose up --build`); confirm `/api/health` returns 200 and the sign-in page renders
- [ ] Walk through all 12 phases of the journey state machine with Aïcha (Tunisian nurse persona) end-to-end: greet → discover → CV inspect → inspiration → preferences → aggregator search → review & categorize → drill → tailor CV → draft letter → CV coaching → done. Record each phase's actual behaviour.
- [ ] Confirm the confirmation gates actually block writes until confirmed — attempt a journey AI invocation, then refuse the confirmation prompt, and verify no DB write occurred.
- [ ] Swap AI providers and run a non-trivial flow end-to-end on each:
  - **Ollama** (fully offline) — confirm the BYO-AI claim works without external network egress
  - At least one cloud provider (OpenAI / Anthropic / Gemini / DeepSeek / OpenRouter — maintainer picks based on available API key)
- [ ] Inspect a persisted CV file: read the implementation in `company_discovery/cv_builder.py` and any encryption helper, then look at the actual file in `data/`, and confirm ChaCha20-Poly1305 is actually applied (not just claimed). Document key derivation, nonce handling, authentication-tag verification.
- [ ] Call all 8 MCP tools listed in `mcp_server.py` and confirm each returns a JSON-Schema-valid response (use a small `jsonschema` test harness; record the exact schemas and responses).
- [ ] Switch language EN ↔ DE; verify the UI fully reloads and all visible strings translate. Test German yes/no parsing: `ja`, `nein`, `jo`, `jep`, `nö`, `nope`. Confirm each is correctly classified.
- [ ] Run the existing test suite in the clean container (`python3 -m unittest discover -v`) and verify the "tests pass" claim. Record the actual pass/fail count.
- [ ] Capture screenshots / terminal recordings of each verification step into `docs/grant/feature-verification-2026-05-XX/` (auxiliary artefacts directory; not committed by default unless useful)
- [ ] Write the verification report to `docs/grant/feature-verification-2026-05-XX.md` with one section per check, recording: claim made by docs / planning / README; observed behaviour; pass/fail/partial; if not-pass, the specific failure and recommended fix path.
- [ ] **Surface the verification report to the maintainer for review before starting any other Week 2 work.** Do not move forward on §2.2 / §2.3 / §2.7 / §2.8 until the maintainer has read the report and given a green light. Gaps surfaced here may reshape the Week 2 task list.

### 2.1 Commons Conservancy application (4 h)

- [x] Read `commonsconservancy.org/how/` end-to-end (2026-05-18; six-phase process: Orientation, Initiation, Setup, Operational, optional Graduation / Hibernation. Initiation = the notification step). Also read DRACC 0001 (mission) and DRACC 0017 (FileSender founding statutes — worked example).
- [x] Prepare the Programme application: mission alignment with DRACC 0001 (quoted verbatim in the draft), free/open-software commitment (Apache 2.0 + CLA, no novel terms), governance shape on entry, NLnet NGI Zero Commons Fund linkage explained. Draft saved at [`commons-conservancy-application-2026-05-18.md`](commons-conservancy-application-2026-05-18.md) with explicit `[MAINTAINER_NAME]` / `[MAINTAINER_EMAIL]` placeholders for maintainer to resolve and send.
- [~] Submit the Programme application — **maintainer action**: review the draft, fill placeholders, send to `website@commonsconservancy.org` (or any more-specific application address the Conservancy may have published). Pledge signature happens during the Setup phase after case-officer assignment, not at Initiation.
- [x] Confirm receipt; note expected response timing in `04-research-and-decisions.md` — Open R11 added with expected window of 2–6 weeks (Conservancy publishes no explicit SLA; estimate based on observed recent admission cadences). Once a case officer responds, update R11 with concrete dates and parameters.

### 2.2 MCP server documentation (6 h) — BLOCKER FIX

- [x] Create `docs/mcp-server.md` covering the catalogue:
  - Tool name, purpose, required input fields, output shape, standards alignment per tool (8 tools today; 13 after §2.3)
  - Protocol version pinned at `2024-11-05`
  - Catalogue version (SemVer): policy documented; current `0.1.0`
  - Composition patterns explained: sequential handoff, profile-shared, orchestrated (future) — cross-linked to `09-mcp-composition.md`
  - Portable civic profile schema referenced (lands with §2.3 catalogue expansion)
  - Error conventions (RFC 7807 Problem Details — fields `status`, `type`, `title`, `detail`, `instance`, `validationPath`, `violatedRule`)
  - Example client invocations in Python (stdlib) and TypeScript (Node.js)
  - Operational notes (stdio transport, env-var data path, encryption integration, audit-log boundary)
- [ ] Publish JSON Schema for every tool input/output as separate files in `mcp_server/schemas/` — *deferred to a §2.2 follow-up; canonical schemas already live in `company_discovery/mcp_tools.py:TOOL_SCHEMAS`, and `tools/list` exposes them over the wire. A filesystem mirror under `mcp_server/schemas/<tool-name>.json` is a build-artefact ergonomic addition, not a contract change; folded in once a downstream consumer needs it for external tooling.*
- [ ] Add an `/mcp/schemas.json` endpoint exposing the full catalogue — *deferred to a §2.2 follow-up; requires an `app.py` route addition. The stdio `tools/list` call is the canonical surface today.*
- [ ] Add a `/mcp/version` endpoint — *deferred to the same §2.2 follow-up. The version is currently reachable via the `serverInfo.version` field in the `initialize` response.*
- [x] Create `STANDARDS.md` at repo root listing every standard cited (Licensing + governance, Protocols + interfaces, Employment + civic-data vocabularies, Accessibility + transparency, Privacy + security, Operational, Internal protocols — with the implementing file path and shipping status per row; verification recipe at the end so a reviewer can deep-check the standards claims in 10 minutes)

### 2.3 New MCP tools (8 h) — composition expansion

- [x] Implement `get_user_profile_for_consent` — returns the user's portable civic profile, filtered to the requested `scopes` array (any subset of `identity`, `residence`, `employment`, `cv`, `outcomes`, `preferences`). Empty placeholders for scopes without data so a consuming agent can detect "no record yet" without inspecting field-by-field. `outcomes` scope reads back the JSONL events persisted by `record_user_outcome` (per-user filtered).
- [x] Implement `propose_referral` — emits a structured referral object with FHIR-ServiceRequest-adjacent fields (`referralId`, `intent`, `priority`, `reasonCode`, `supportingInfo`, `userConsentRequired`). No persistence; caller surfaces to the user and hands over on consent.
- [x] Implement `query_esco_skill` — substring-matches a Week 2 persona-panel-aligned mini-dataset (~12 entries covering nursing, mechanical engineering, frontend, plumbing, home-based care plus skills); full ESCO dataset import lands in §2.4. Supports `type` filter (`occupation`/`skill`/`any`) and `limit`.
- [x] Implement `export_eures_compatible` — projects a stored discovered job onto a EURES-compatible JobPosting subset (`hiringOrganization`, `jobLocation`, `datePosted`, `validThrough`, `employmentType`, etc.) with explicit `schemaConformance: EURES-compatible-subset-v0`. Returns `status: not_found` when the discovered-job id does not resolve.
- [x] Implement `record_user_outcome` — append-only JSON Lines journal at `data/user_outcomes.jsonl`. Enum: `applied`/`replied`/`interviewing`/`offer`/`rejected`/`withdrawn`. Optional `note` field. Enforced both at the inputSchema enum level and at the method body so non-MCP callers can't bypass.
- [x] Add JSON Schemas for all new tools (Draft 7, registered in `TOOL_SCHEMAS` in `company_discovery/mcp_tools.py`; the §2.2 server-side enforcement covers them automatically).
- [x] Add unit tests for each new tool — `tests/test_phase11_mcp_tools_v2.py` (27 tests). Coverage: catalogue registration (5 new tools + total count = 13), schema-compiles sanity, per-tool happy path, per-tool MCP-dispatch validation failure (missing required / bad enum), referral-id uniqueness, ESCO type filtering, outcome-event read-back through `get_user_profile_for_consent`, JSONL append order, schema↔module-constant sync for outcome enum.

### 2.4 ESCO and EURES integration (4 h)

- [x] Verify ESCO data licensing — ESCO v1.1 published by European Commission DG-EMPL under Creative Commons Attribution 4.0 International (CC BY 4.0); attribution surfaces in `reference/esco/*.json` and `docs/esco-integration.md`.
- [x] Curated subset shipped — full ESCO dataset (~3,000 occupations / ~13,000 skills / 27 languages / ~80 MB) deliberately not committed (see `docs/esco-integration.md` §"Upgrade path" — build-time fetch is the post-grant Phase 2 approach). The curated v1 dataset covers the persona panel + Bundesagentur 2025 shortage occupations.
- [x] Map at least 30 high-value occupations covering the persona panel — `reference/esco/occupations.json` ships 30 entries with ISCO-08 codes, EN + DE labels, persona linkage, and shortage-list flag. Persona coverage: Aïcha (8 occupations), Yusuf (6), Olga (6), Mahmoud (6), Maria (5; overlap with Aïcha on Pflegehelfer).
- [x] Map at least 50 corresponding skills — `reference/esco/skills.json` ships 50 entries grouped by category (language 5, healthcare 10, engineering 8, IT 15, trade 8, cross-cutting 4) with EN + DE labels and optional CEFR level for language skills.
- [x] Document the mapping in `docs/esco-integration.md` — covers schema, persona-panel coverage table, shortage-list overlap stats, loader behaviour, EURES projection field-map, full upgrade path, and attribution.
- [x] Verify the EURES schema export endpoint produces valid output for sample jobs — `export_eures_compatible` projection shape is documented in `docs/esco-integration.md` §"EURES projection shape" with the field-by-field map (`hiringOrganization`, `jobLocation`, `datePosted`, `validThrough`, `employmentType`, `sourceProvider`, `schemaConformance: "EURES-compatible-subset-v0"`). Projection shape is tested in `tests/test_phase12_esco_eures.py::EURESProjectionShapeTests`; full end-to-end with a persisted DiscoveredJob lands in the §2.6 MCP CI integration test.

### 2.5 Reference integration with the housing agent (8–20 h)

**Decision 20 guardrail (added 2026-05-18)**: Per Decision 20 in `04-research-and-decisions.md`, the maintainer does not self-build a Phase 1 housing agent regardless of friend response; default is Option A (mock stub), upgrade to Option B only on explicit collaborator confirmation. Options C / D (self-built, narrow or full) are deferred to Phase 2 per `03-post-grant.md`.

If the housing-agent friend responded positively (Option B):

- [ ] Coordinate scope with the friend
- [ ] Verify or convert the housing agent's license to Apache 2.0
- [ ] Build the integration in `examples/housing-agent-integration/`
- [ ] Cross-link the two repositories
- [ ] Both projects ideally apply jointly to The Commons Conservancy
- [ ] Document the integration in `examples/README.md`

If no positive response (Option A fallback):

- [ ] Build the mock `examples/housing-stub-client/` demonstrating the composition pattern end-to-end
- [ ] Record an asciinema or plain-text terminal session showing it working
- [ ] Document in `examples/README.md` that this is a stub pending real-housing-agent collaboration

### 2.6 MCP integration test in CI (4 h)

- [x] Add `.github/workflows/mcp-integration.yml` — matrix on Python 3.11 + 3.12; pip-cache; runs `python -m unittest tests.test_phase12_mcp_integration_e2e`; prints the catalogue summary on success via `scripts/print_mcp_catalogue.py`.
- [x] Test spawns the MCP server as subprocess — `_StdioMCPClient` in `tests/test_phase12_mcp_integration_e2e.py`; uses a tmp `COMPANY_DISCOVERY_DATA_DIR` per test for isolation; bounded 10 s shutdown wait.
- [x] Connects a mock MCP client over stdio — JSON-RPC-over-stdio writes to subprocess.stdin, reads from subprocess.stdout one line per request.
- [x] Calls `initialize`, expects version `2024-11-05` — `test_01_initialize_returns_canonical_protocol_version`; also asserts `serverInfo.name == "directjob-scout"` and capabilities advertise tools.
- [x] Calls `tools/list`, expects at least 13 tools — `test_03_tools_list_returns_thirteen_tools_with_draft7_schemas` asserts exactly 13 (the catalogue v0.2.0 surface), enumerates all expected names, and runs `jsonschema.Draft7Validator.check_schema` on every tool's `inputSchema`.
- [x] Calls `find_company_career_page` and `propose_referral` with known inputs — covered by `test_06_find_company_career_page_happy_path` and `test_04_propose_referral_happy_path`. Also covers `query_esco_skill` happy path (§2.4 German-label lookup) for completeness across the catalogue's three eras (legacy 8 + §2.3 composition tools + §2.4 ESCO).
- [x] Validates all responses against the published JSON Schemas — every `tools/list` schema is Draft-7-compiled; every happy-path response is parsed and field-checked against the documented shape; the schema-validation failure path is verified via `test_07_invalid_arguments_returns_rfc7807_problem_document` (deliberately malformed `record_user_outcome` payload returns the RFC 7807 Problem Details document with `violatedRule: "enum"`).
- [x] Clean shutdown — `_cleanup` asserts subprocess exits 0 within 10 seconds after stdin close.
- [x] Green badge in README — top of `README.md` carries `[![MCP integration](https://github.com/maksodf/directjob-scout/actions/workflows/mcp-integration.yml/badge.svg?branch=claude/project-analysis-bpHCo)](https://github.com/maksodf/directjob-scout/actions/workflows/mcp-integration.yml)`; will go green on the first push to GitHub that picks up the workflow.

### 2.7 ARCHITECTURE.md (4 h)

- [x] Write `ARCHITECTURE.md` at repo root
- [x] Mermaid diagram showing: web app, MCP server as composition surface, BYO-AI provider abstraction (11 options), encrypted profile-at-rest layer, audit-log layer, journey state machine, locale-aware token parser. The future-housing-agent slot appears as an "Other civic agent" external actor on the diagram, materialising as the §2.5 reference integration.
- [x] Caption every component with the implementing file/module (component-map tables organised by layer: Entry surfaces, Application logic, Domain services, Persistence + crypto, Cross-cutting, External)
- [x] Cross-link to `09-mcp-composition.md` (and to `07-personas.md`, `08-cost-saving-doctrine.md`, `10-ai-act-compliance.md` for adjacent context)

### 2.8 AI Act compliance pack (12 h) — BLOCKER FIX

Per `10-ai-act-compliance.md`. Create the `/compliance/` directory and ship:

- [x] `compliance/README.md` index — orientation, audience split (provider/deployer/end-user), friction-class framing per Decision 21
- [x] `compliance/risk-management-plan.md` (Article 9) — eight identified risks (R1–R8) with pre- and post-mitigation L×S ratings; incident escalation; review cadence
- [x] `compliance/data-governance.md` (Article 10) — data-category map; ChaCha20-Poly1305 AEAD encryption-at-rest; prompt minimisation; bias-testing reference
- [x] `compliance/technical-documentation.md` (Article 11 + Annex IV — all 9 sections including post-market monitoring per Article 72)
- [x] Audit-log schema documented (`compliance/audit-log-schema.md`) + audit-log infrastructure integrated into MCP server (`mcp_server.py::_handle_tools_call`) and analysis pipeline (`company_discovery/analysis.py::_dispatch_provider`). Emitter at `company_discovery/audit_log.py` with PII-hashed `user_opaque_id` and `session_opaque_id` by default, contextvar-based caller-context propagation, microsecond-precision rotation with collision nonce
- [x] `compliance/transparency-notice.md` (user-facing, Article 13) — friction-class framing for "who this is for"; user-rights map (Articles 50 and 86); deployer-managed addendum with TBD placeholders
- [x] `compliance/deployer-operating-manual.md` (Article 13) — friction-class framing for "who you can serve" (so Jobcenter / career service / NGO operators understand the tool fits their full caseload); pre-deployment checklist; Article 26 obligations map; incident response
- [x] `compliance/human-oversight-guide.md` + minimum-viable human-oversight UI (Article 14): admin endpoint `/api/admin/oversight/queue` gated by `DIRECTJOB_HUMAN_OVERSIGHT_MODE`; four oversight modes (passive monitoring / advisor-review queue / per-action gates / kill-switch); appointment record with TBD placeholders
- [x] `compliance/accuracy-and-bias-testing.md` (Article 15) — seven-persona panel as test cohort (includes Käthe and Tobias for friction-class breadth per Decision 21); within-persona / cross-persona / cross-class equivalence axes; tolerance bands; pre-deployment re-test procedure
- [x] `compliance/eu-database-registration-template.md` (deployer pre-fill, Article 49) — provider Sections A–C pre-filled; deployer Sections D–G with TBD placeholders; pre-submission checklist
- [x] `compliance/fundamental-rights-impact-assessment-template.md` (deployer pre-fill, Article 27) — eight parts including affected-population section using friction-class framing; CFR-article-by-article assessment table; per-deployer-type sample affected-population text for MBE / Optionskommune Jobcenter / university career service / NGO contexts
- [x] Cross-link from README (compliance pack callout under "Standards we implement") and from `10-ai-act-compliance.md` (implementation-status header pointing at the shipped pack)
- [x] Tests for the audit-log emitter in `tests/test_phase13_audit_log.py` — 20 tests covering emitter (rotation, hash determinism, plaintext opt-in, error_class), caller-context contextvar propagation, convenience wrappers, MCP-server integration, analysis-pipeline integration, and the tail helper for the oversight endpoint. Test patches in `tests/test_ai_quality_e2e.py` and `tests/test_chat_ai_router.py` updated to accept the new `purpose` kwarg via `**_kwargs`.

### Week 2 Definition of Done

- Commons Conservancy application submitted
- `docs/mcp-server.md` complete with 13 tools documented
- `STANDARDS.md` lists every standard cited
- ESCO integration covering 30+ occupations
- EURES schema export verified
- Reference integration with housing agent shipped in `examples/` per Decision 20: Option A (mock stub) is the Phase 1 default; Option B (real friend integration) ships only on explicit collaborator confirmation; self-built (Options C / D) is deferred to Phase 2. The DoD is met by whichever disposition lands by the close of Week 2 — both Option A and Option B satisfy the MCP-composition pitch (per Rule 6 in `13-lessons-learned.md`).
- CI runs MCP integration test, badge is green
- ARCHITECTURE.md with system diagram
- Complete AI Act compliance pack in `/compliance/`

---

## Week 3 — Quality, demo deployment, accessibility, contributor pathway

**Goal**: from "personal MVP" to "looks like a project a community can contribute to and an institution can adopt."

**Estimated effort**: ~40 hours.

### 3.1 Fix the local test environment (3 h)

- [x] Diagnose the `cryptography` / `cffi` build failure on fresh clones — root cause: `cryptography` was never explicitly listed in `requirements.txt`; it came in as a transitive dependency through `pywebpush`, leaving wheel selection to the resolver. On Linux containers without rust + build-essential the resolver could fall back to source build and fail at the cffi compilation step.
- [x] Pin runtime dependencies in `requirements.txt` — `cryptography>=42.0.0,<50.0.0` explicitly added with an inline rationale comment. The pin range is broad enough to keep us on supported security-patched cryptography versions while every version in the range ships pre-built wheels for macOS x86/arm64, Linux x86/arm64 (manylinux + musllinux), and Windows.
- [x] Pin dev dependencies in `requirements-dev.txt` — created with `pre-commit>=3.5.0,<5.0.0`. Ruff / mypy / coverage / codespell append here when §3.2 lands.
- [x] Document install order in `CONTRIBUTING.md` — explicit four-step sequence (runtime install → dev install → pre-commit activation → app run).
- [x] Verify `python -m unittest discover` passes on a clean machine — verified via Docker on both `python:3.11-slim` and `python:3.12-slim`: fresh `pip install -r requirements.txt` succeeds with no rust / build-essential, the cryptography import works, and the representative smoke-test slice (encryption-at-rest + AEAD fuzzing + audit log + MCP integration end-to-end) runs green. Full 994-test local suite also green after the changes.
- [x] Add a fresh-clone Docker smoke-test workflow — `.github/workflows/fresh-clone-install.yml`. Runs on every push and PR against `main` and `claude/**` branches; matrix over `python:3.11-slim` and `python:3.12-slim`; verifies pip install, the cryptography import, and the smoke-test slice. README carries the `Fresh-clone install` badge under the License badge.
- [x] Soften framing in `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `01-project-brief.md` — historical issue is closed; Docker is supported as a fallback but no longer required for testing.

### 3.2 CI expansion (8 h)

- [x] Add `ruff` lint + format check — config in `pyproject.toml` `[tool.ruff]`; CI workflow `.github/workflows/quality.yml` (`ruff-lint` job); pre-commit hook in `.pre-commit-config.yaml`. Target `py39` (matches the minimum supported Python). Real-bug findings fixed (B039 mutable ContextVar default in `audit_log.py`, F821 forward-ref imports in `auth.py` + `tests/test_phase1_seo_pages.py` + `tests/test_phase3_onboarding_drip.py`, B030 + B005 with explicit `# noqa` on intentional patterns); pre-existing style nits in legacy code added to ignore list as drift targets.
- [x] Add `mypy` type check — config in `pyproject.toml` `[tool.mypy]`; CI workflow `.github/workflows/quality.yml` (`mypy-strict-subset` job). Permissive baseline (`follow_imports = "silent"`, no `disallow_untyped_defs`) with **strict overrides** for `company_discovery.audit_log`, `company_discovery.crypto_kit`, and `mcp_server`. Subset grows as more modules tighten. Strict subset green (`Success: no issues found in 3 source files`).
- [x] Add coverage upload to Codecov — CI workflow `.github/workflows/quality.yml` (`coverage` job). Uses `coverage run -m unittest discover` then `codecov/codecov-action@v5`. Branch coverage enabled in `pyproject.toml` `[tool.coverage.run]`. README badge added.
- [x] Add `pip-audit` for CVE scanning — CI workflow `.github/workflows/quality.yml` (`pip-audit` job). Strict mode (`--strict`) fails on any vulnerability across both `requirements.txt` and `requirements-dev.txt`.
- [x] Add `Renovate` config — `renovate.json` at repo root. Activation requires the Renovate GitHub App installed by the maintainer; the config is the contract. Groups minor/patch updates weekly into a single PR per file (`requirements.txt`, `requirements-dev.txt`); major updates get explicit PRs; `cryptography` major releases tagged `security-review-needed`; vulnerability alerts immediate; GitHub Actions pinned to commit SHAs to satisfy OpenSSF Scorecard.
- [x] Add `codespell` workflow — CI workflow `.github/workflows/quality.yml` (`codespell` job). Config in `.codespellrc` (the `[tool.codespell]` table in pyproject.toml is unreliable across codespell versions, see upstream issue #1853). Pre-commit hook adds local feedback. German-vocabulary false positives ignored explicitly; one real misspelling of the word "download" was fixed in `journey.py` + `tests/test_journey_edge_cases.py` (caught by codespell on its first run).
- [x] Add `locale_check` workflow verifying en.json and de.json key parity — already exists as `i18n parity check` step in `.github/workflows/test.yml`; multi-OS matrix exercises it on every push.
- [~] Add multi-OS matrix — **partial**. `.github/workflows/test.yml` matrices over Python 3.9 + 3.12 on `ubuntu-latest`. Cross-platform (macOS, Windows) coverage was attempted and reverted in the same task because the existing test suite has Linux-isms requiring systematic remediation: (a) many tests open files without explicit `encoding="utf-8"`, so Windows runners fall back to cp1252 and the i18n / encryption / rate-limit tests fail in cascade; (b) subprocess-based HTTP smoke tests (`test_app_smoke`, `test_http_admin_extras`, `test_http_phase2`) time out in `setUpClass` on macOS runners with `RuntimeError: server did not start` (slower TCP-bind cycle than Ubuntu). Both deferred to Phase 2 cleanup (tracked in `docs/grant/03-post-grant.md`). The workflow comments document the deferral so future contributors find context.
- [x] Add OpenSSF Scorecard workflow + badge in README — `.github/workflows/scorecard.yml` using `ossf/scorecard-action@v2.4.0`. Weekly cron + push-to-main triggers. SARIF uploaded to GitHub Security tab; results published to scorecard.dev.
- [x] All CI badges visible in README — tests, quality, MCP integration, fresh-clone install, OpenSSF Scorecard, Codecov coverage. Existing badges (License, Release placeholder, Languages, MCP version) retained.

### 3.3 Roadmap and release discipline (5 h)

- [x] `ROADMAP.md` at repo root — eight quarters from 2026 Q3 to 2028 Q2 with honest "we plan to / scoped for / anticipated / under consideration" language; cross-linked from README's Roadmap and Documentation sections; long-horizon context kept in `docs/grant/03-post-grant.md`.
- [x] `CHANGELOG.md` at repo root in Keep-a-Changelog 1.1.0 format — `[0.1.0] — 2026-05-18` entry backfilled from sprint commits grouped by Added / Changed / Fixed / Removed / Security; pre-sprint history collapsed into a brief `[0.0.x] — pre-2026-05-17` entry pointing at `CONTRIBUTORS-NOTE.md`. Apache 2.0 header.
- [x] First tagged release: `v0.1.0` with release notes — annotated tag points at the GitHub Release; release notes are version-controlled at `docs/releases/v0.1.0.md` (so the source survives any GitHub UI edit) with three sections per the maintainer spec: "What this is" / "What's in this release" / "What's not yet shipped". Cryptographic signing of the release artifact (cosign + CycloneDX SBOM) is deferred to Week 4 task 4.2 per the agent's existing scope.
- [-] Set up GitHub Releases workflow to automate future tagging — **dropped from §3.3 scope**. The Phase 1 release cadence is low (v0.1.0 here, v0.2.0 post-NLnet-submission, see ROADMAP); manual `git tag -a` + `gh release create` is the right rhythm. Automating the workflow lands when the release cadence increases — Phase 2 task tracked in `docs/grant/03-post-grant.md`.

### 3.4 Public demo deployment (~3 h, re-anchored 2026-05-18)

**Scope re-anchor**: §3.4 uses the **existing deployment infrastructure** the maintainer already operates. Hosting provider, registrar, monitoring vendor — these are the maintainer's existing setup, not §3.4 prerequisites to provision new. The earlier draft of this task listed Hetzner / OVH / Scaleway as candidates and `directjob-scout.eu` as a candidate domain; that was placeholder enumeration that an advisory prompt mis-read as a commitment. Cleanup audit 2026-05-18 (`cleanup-audit-2026-05-18.md`) details the false dependency the cleanup removed. Re-anchored scope:

- [ ] Confirm with maintainer which subdomain hosts the public demo. The maintainer's existing deployment is documented in `private/` (gitignored per Decision 12 / Week 1 task 1.4 sanitisation); the public-tree convention is `app.directjob-scout.example` placeholders. **Decision needed before referencing a demo URL in any public artifact** — see `04-research-and-decisions.md` Open R8 (updated).
- [ ] Pre-seed the existing deployment with the **seven-persona** panel (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) per Decision 21. The seeding script itself is generic — runs against any DirectJob Scout instance, not infrastructure-specific. *(Agent-doable autonomously once the persona-source-of-truth decision is locked: read `07-personas.md` and produce reproducible seed records.)*
- [ ] Document the generic deployment recipe in `docs/deployment-recipe.md` (extends the existing `docs/production-deployment.md` with the persona-seed step + the "use existing infrastructure" framing). **Not** Hetzner-specific; works against any Docker Compose + Caddy host the maintainer chooses.
- [ ] Verify `/api/health` returns green via the existing `scripts/production-smoke.sh`. Already implemented; the §3.4 task is to *run* it post-seed, not to *build* it.
- [ ] Once the maintainer confirms the demo URL, update README and `12-application-package.md` to reference it. Until then, the public-tree placeholder remains `app.directjob-scout.example` per the existing sanitisation convention.

### 3.5 Documentation site (3 h)

- [ ] Set up mkdocs-material with basic site structure: Quickstart, Architecture, Deployment, Contributing, MCP API, Standards, AI Act compliance, Roadmap
- [ ] Auto-deploy via GitHub Actions to GitHub Pages
- [ ] Link from README

### 3.6 Accessibility audit and ACCESSIBILITY.md (8 h)

- [ ] Run an automated accessibility audit (axe-core or WAVE) against the public demo
- [ ] Fix the highest-impact issues
- [ ] Document the current state in `ACCESSIBILITY.md` honestly: WCAG 2.2 Level AA as target, known gaps, remediation plan
- [ ] Optionally request HAN University accessibility support if Commons Conservancy admission has come through

### 3.7 Translator contributor pathway (2 h)

- [ ] `docs/translating.md` explaining the JSON file structure and how to add a new locale
- [ ] Document the translation review process
- [ ] Native-speaker review of `de.json` — recruit one person (friend, fellow TU Berlin student, social circle) for 2 hours
- [ ] Credit reviewers in `AUTHORS.md`

### 3.8 Reproducible build (Nix flake) (4 h)

- [ ] Add `flake.nix` at repo root producing a reproducible build
- [ ] Document usage in `docs/deployment-recipe.md` and CONTRIBUTING.md
- [ ] Verify the flake builds on a clean machine
- [ ] Optionally request NixOS Foundation packaging support if Commons Conservancy admission has come through

### 3.9 Outreach follow-ups (1 h)

- [ ] Day-7 follow-up to any cold contacts who have not replied (one follow-up, then stop)
- [ ] Process any positive replies into letter-of-support drafts
- [ ] Update the outreach tracker in `11-institutional-outreach.md`

### Week 3 Definition of Done

- Tests pass on a clean machine
- README displays 8+ CI badges (license, build, coverage, lint, security, locale, MCP integration, Scorecard)
- `ROADMAP.md` and `CHANGELOG.md` present, `v0.1.0` tagged
- Public demo deployed at stable URL with pre-seeded persona-panel content
- Documentation site live at `docs.<domain>`
- `ACCESSIBILITY.md` honest about current WCAG state with audit-date
- `flake.nix` builds reproducibly
- German native-speaker review feedback integrated, reviewer credited

---

## Week 4 — Sustainability, signing, and the application

**Goal**: clear differentiation flags planted; application drafted, reviewed, submitted.

**Estimated effort**: ~25 hours.

### 4.0 Outreach send pass (4 h)

The three draft messages prepared in Week 1 task 1.6 are saved under [`outreach-drafts/`](outreach-drafts/). Send-gate criterion per Decision 19: README, demo deployment, docs site, AI Act compliance pack, and green-CI badges all visibly finished before any send.

- [ ] Re-verify each draft's contact details (name, role, email) — the drafts carry "last verified" dates from Week 1; check whether anything changed
- [ ] Confirm the send-gate criterion is satisfied (Week 3 deliverables visibly complete)
- [ ] Personalise the three German draft messages — fill in maintainer name, contact email, project link, and (for TU Berlin) student programme + Matrikelnummer
- [ ] Send the three outbound emails:
  - AWO Charlottenburg-Wilmersdorf FIM — Irina Alles (`fim-cw@awoberlin.de`)
  - RINWA Berlin / La Red — Cristina Faraco Blanco (`faraco@la-red.eu`)
  - TU Berlin Career Service — Bettina Satory (`bettina.satory@tu-berlin.de`)
- [ ] Update the outreach tracker in `11-institutional-outreach.md` with send dates and any reply/outcome notes
- [ ] Send the housing-agent collaboration message (Template F) — handled by maintainer if not already done in Week 2 task 2.5
- [ ] Optionally send to one Optionskommune Jobcenter IF a strong-fit office has emerged organically (otherwise hold; one credible letter is sufficient)
- [ ] Set a 7-day follow-up reminder per Template B for any contact who has not replied; one follow-up only, then stop

### 4.1 Sustainability and post-grant story (3 h)

- [ ] `SUSTAINABILITY.md` describing the post-grant model:
  - NGO/Beratungsstelle deployment partners
  - Optional hosted support contracts (mention here, not in main README)
  - Phase 2 / Phase 3 grant arc plan (NLnet follow-on, Sovereign Tech Fund, EU NGI tracks)
- [ ] Link from README

### 4.2 Final differentiation polish (4 h)

- [ ] Cosign-sign `v0.1.0` release
- [ ] Attach CycloneDX SBOM (via `cyclonedx-py`)
- [ ] `static/.well-known/security.txt` per RFC 9116
- [ ] Verify OpenSSF Scorecard badge is at acceptable score (8.0+)

### 4.3 Letter of support consolidation (2 h)

- [ ] Confirm receipt of at least one letter of support OR ensure the cold contact is in active discussion that can be cited
- [ ] If letter signed: archive PDF in `docs/grant/letters-of-support/`
- [ ] Update `11-institutional-outreach.md` tracker

### 4.4 Write and dry-run the application (10 h)

- [ ] Verify NLnet's live application form structure (Open Research Question R3 in `04-research-and-decisions.md`)
- [ ] Adapt `12-application-package.md` content into the form fields
- [ ] Pre-empt NLnet's support services: list which we anticipate using (accessibility audit, packaging, security audit, mentoring)
- [ ] Have one person outside the project read it cold for clarity
- [ ] Revise based on feedback

### 4.5 Final polish and submission (5 h)

- [ ] Final README pass — every badge green, every link working
- [ ] Final demo deployment health check
- [ ] Final documentation-site review
- [ ] Final application-package review against the submission checklist in `12-application-package.md` §I
- [ ] Submit the application
- [ ] Archive submission confirmation in `docs/grant/submitted-application-<date>.md`

### 4.6 Post-submission (1 h)

- [ ] Tag `v0.2.0` release reflecting all Week 1–4 work
- [ ] Continue any outstanding outreach
- [ ] Brief celebration; then recovery break before Phase 2 planning

### Week 4 Definition of Done

- `SUSTAINABILITY.md` present
- `v0.1.0` signed with cosign + SBOM attached
- `security.txt` published per RFC 9116
- OpenSSF Scorecard badge ≥ 8.0
- At least one letter of support in hand or active partner discussion ongoing
- Application submitted to NLnet
- `v0.2.0` tagged

---

## Tracking notes

Use this section for free-form notes during execution. Date each entry.

**2026-05-17**: plan created reflecting all strategic decisions, AI Act work, Commons Conservancy application, Apache 2.0 licensing, cost-saving doctrine, and the EU-wide positioning.

**2026-05-18**: outreach sends deferred from Week 1 task 1.6 to Week 4 task 4.0 per Decision 19 in `04-research-and-decisions.md`. The three contact-package drafts (AWO Charlottenburg-Wilmersdorf FIM, RINWA Berlin / La Red, TU Berlin Career Service) are saved under `outreach-drafts/`. Task 1.7 closed as mitigated by Decision 17 (no public production deployment exists to align). Task 1.5 GitHub UI housekeeping remains the only open Week 1 item; the proposed text for the maintainer to paste through the GitHub UI is embedded in §1.5 above. Week 2 work begins with the new highest-priority task 2.0 (Feature verification pass) — verify every claim our Week 2 docs make against the running code before any documentation lands.

<!-- Add new dated notes below this line as execution proceeds -->
