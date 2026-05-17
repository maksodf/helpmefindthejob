# 4-Week Execution Plan — NGI0 Grant Readiness

**Created**: 2026-05-17
**Target submission**: ~4 weeks from creation (verify exact NGI0 call deadline before submitting)
**Estimated total effort**: 85–95 hours of focused non-feature work
**Owner**: maintainer + agent sessions

This is the live tracker. **Tick boxes as work is completed. Add notes when scope changes.**

For each task: `[ ]` = not done, `[x]` = done, `[~]` = in progress, `[!]` = blocked.

---

## Pre-flight checklist (do before Week 1 starts)

- [ ] Confirm the exact NGI0 Commons Fund call deadline (next opening or current open call)
- [ ] Decide repo hosting: stay on `github.com/maksodf/directjob-scout` or migrate to a `directjob-scout` GitHub org for the institutional-wrapper signal
- [ ] Switch maintainer workstation from mobile to computer for execution (mobile is fine for review only)
- [ ] Skim `01-project-brief.md` end-to-end so the strategic context is fresh
- [ ] Create a `claude/week-1-foundations` branch off `claude/project-analysis-bpHCo` (or whatever the working branch is at start)

---

## Week 1 — Legal and narrative foundations

**Goal**: by end of week 1, the repo passes the "is this a real open-source project" sniff test. LICENSE, governance, README mission, no internal residue.

**Estimated effort**: ~20 hours.

### 1.1 Licensing (2 h) — BLOCKER FIX

- [ ] Add `LICENSE` file at repo root with full AGPL-3.0 text
- [ ] Add `NOTICE` file if any third-party AGPL-incompatible code is detected (run `pip-licenses` to check dependencies)
- [ ] Add SPDX-License-Identifier header to every Python source file (script-driven; ~30 min)
- [ ] Add `.license_header_template.txt` (copy Tenzu's pattern)
- [ ] Add a pre-commit hook that checks SPDX headers in new files
- [ ] Update `README.md` to display license badge (shields.io AGPL-3.0)

### 1.2 Governance pack (8 h) — BLOCKER FIX

- [ ] `CONTRIBUTING.md` — even if it says "early-stage, limited PRs accepted" (Tenzu pattern). Cover: dev setup, code style, commit message convention, PR process, DCO sign-off requirement.
- [ ] `CODE_OF_CONDUCT.md` — full Contributor Covenant 2.1 text with maintainer email for reports
- [ ] `SECURITY.md` — vulnerability reporting channel, response SLA, PGP key (or just an email), supported versions
- [ ] `SUPPORT.md` — where to ask questions, expected response times
- [ ] `AUTHORS.md` — start with the lone maintainer; add co-maintainers and translator credits as they appear
- [ ] `ACKNOWLEDGMENTS.md` — credit MCP ecosystem, NLnet if funded, any prior art
- [ ] `FUNDING.yml` in `.github/` — point to GitHub Sponsors or Open Collective
- [ ] `.github/ISSUE_TEMPLATE/` — bug, feature, security templates
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `CODEOWNERS` — at minimum, the lone maintainer until co-maintainers join

### 1.3 README rewrite (4 h) — BLOCKER FIX

- [ ] Open with a single-sentence value prop containing either a quantified claim or a continuity claim. **Draft**: *"DirectJob Scout is an open-source civic employment agent for the labor-shortage gap in Germany: multilingual, privacy-preserving, MCP-composable, and self-hostable by individuals and migrant-services NGOs alike."*
- [ ] Add badges row: license (AGPL-3.0), CI status, latest release, code coverage, languages, MCP-protocol version
- [ ] Add one screenshot or animated GIF demoing the chat journey end-to-end (use anchor persona Aïcha)
- [ ] Add "Standards we implement" section: MCP, schema.org JobPosting, WCAG 2.2 AA (target), RFC 9116, AGPL-3.0
- [ ] Move Pro/Free billing section below the fold (or out of public README entirely — see 1.5)
- [ ] Add "Funded by" placeholder for NLnet (fill in only if/when funded)
- [ ] Add quickstart that genuinely works in 5 minutes from a clean machine
- [ ] Add link to docs site (placeholder if site not built yet; build in Week 3)

### 1.4 Sanitize internal residue (4 h) — BLOCKER FIX

- [ ] Replace all 29 `khalo.org` occurrences in `app.py` with `example.com` or environment-variable placeholders
- [ ] Replace `support@khalo.org` with a sanitized contact or `security@<your-domain>`
- [ ] Add a `CONTRIBUTORS-NOTE.md` (or note in CONTRIBUTING.md) explaining that early commits may reference internal tester names — do not retroactively rewrite history (loses signed commits, costs more than it gains)
- [ ] Delete `keepbuildingtill100%tracker.MD` from repo root (move content to private gist or `private/` if you want to keep it)
- [ ] Sanitize `.env.example` (verify no real keys leaked)
- [ ] Run a secret-scan with `gitleaks` over the full history; fix anything found

### 1.5 Hide / relocate commercial docs (1 h) — narrative fix

- [ ] Move these files to a `private/` folder (gitignored) OR a separate private repo:
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
- [ ] Decide on retention or deletion of `keepbuildingtill100%tracker.MD` (recommended: delete from repo, archive privately)

### 1.6 GitHub repo housekeeping (1 h)

- [ ] Update the repo description on GitHub to match the new positioning ("Open-source civic employment agent — multilingual, privacy-preserving, MCP-composable")
- [ ] Add topic tags: `civic-tech`, `mcp`, `model-context-protocol`, `jobs`, `employment`, `open-source`, `germany`, `migration`, `agpl-3-0`, `self-hosted`
- [ ] Enable GitHub Discussions
- [ ] Pin the most relevant repos to the user/org profile
- [ ] Verify default branch is appropriately named (`main` or `develop`)

### Week 1 Definition of Done

- LICENSE file present, recognized by GitHub
- All 6 governance files at root
- README opens with the new positioning, badges visible, anchor-persona screenshot included
- Zero occurrences of `khalo.org` in code
- Commercial docs moved out of `docs/` (gitignored or relocated)
- GitHub repo description and topics updated
- A fresh-clone smoke test passes: `git clone && docker compose up` works on a clean machine without secret-leak

---

## Week 2 — Prove the MCP composition story (central pitch artifact)

**Goal**: the central pitch claim — "MCP-composable, civic-agent platform" — is verifiable by any reviewer who reads the repo for 5 minutes.

**Estimated effort**: ~24–36 hours.

### 2.1 MCP server documentation (6 h) — BLOCKER FIX

- [ ] Create `docs/mcp-server.md` (or expand `mcp_server.py` README) covering:
  - Tool catalog (currently 8 tools — list each with name, purpose, schema)
  - JSON Schema for inputs and outputs
  - Protocol version pinned (currently `2024-11-05`)
  - Versioning policy: SemVer for the tool surface
  - Error semantics: what does the server return on failure
  - Authentication / session model
  - Example client invocations (Python, TypeScript)
- [ ] Add a `STANDARDS.md` listing every standard we implement or commit to (see §6 of `01-project-brief.md`)

### 2.2 Reference integration — proving composition (8–20 h) — BLOCKER FIX

Pick option A or option B depending on what's achievable in the window.

**Option A — Mock second consumer (safer, ~8 h)**:

- [ ] Create `examples/housing-stub-client/` — a minimal Python script that connects to the DirectJob Scout MCP server, calls `find_company_career_page`, then "hands off" a mock housing-search request showing how composition would route across agents
- [ ] Include a recorded terminal session (asciinema or plain log) showing the composition working end-to-end
- [ ] Document the integration in `examples/README.md`

**Option B — Real housing agent published (gold standard, ~20 h)**:

- [ ] Coordinate with the existing housing agent codebase
- [ ] Publish it (even minimally) under AGPL-3.0
- [ ] Add `examples/housing-agent-integration/` showing it consuming the DirectJob Scout MCP
- [ ] Cross-link both repos

**Recommendation**: start Option A immediately; pursue Option B in parallel if the housing agent is closer to publishable than feared.

### 2.3 Architecture documentation (4 h)

- [ ] `ARCHITECTURE.md` at repo root with a Mermaid diagram showing:
  - DirectJob Scout web app (the reference implementation)
  - The MCP server as the composition surface
  - The future-housing-agent slot (and any other future agents)
  - Data flow: user → chat router → journey state machine → MCP tool → underlying service
  - BYO-AI provider abstraction layer
  - Encrypted profile-at-rest layer
- [ ] Caption every component with which file/module implements it (linkable navigation)

### 2.4 MCP integration test in CI (4 h)

- [ ] Add a CI test that spawns `mcp_server.py` and runs a mock client through 3 tool calls
- [ ] Add a badge to README showing MCP-integration test status

### 2.5 Schema endpoint (2 h)

- [ ] Expose the MCP tool schemas via a public endpoint (e.g., `/mcp/schemas.json`) so external consumers can discover tools without running the server
- [ ] Document the endpoint in `docs/mcp-server.md`

### Week 2 Definition of Done

- `docs/mcp-server.md` exists and is complete
- `STANDARDS.md` lists every standard we cite
- A reference integration (Option A minimum) exists in `examples/`
- `ARCHITECTURE.md` exists with a system diagram
- CI runs an MCP integration test and the badge is green in README
- A reviewer can verify the composition story by reading the repo in 5 minutes

---

## Week 3 — Quality signals and contributor pathway

**Goal**: from "personal MVP" to "looks like a project a community could contribute to."

**Estimated effort**: ~19 hours.

### 3.1 Fix the local test environment (3 h) — MAJOR FIX

- [ ] Diagnose the `cryptography` / `cffi` build failure on fresh clones
- [ ] Pin runtime deps in `requirements.txt` and dev deps in `requirements-dev.txt`
- [ ] Document the install order in `CONTRIBUTING.md`
- [ ] Verify `python -m unittest discover` passes on a clean machine

### 3.2 CI expansion (8 h)

- [ ] Add `ruff` lint + format check
- [ ] Add `mypy` type check (start with `--ignore-missing-imports`, tighten over time)
- [ ] Add coverage upload to Codecov; add coverage badge to README
- [ ] Add `pip-audit` for CVE scanning
- [ ] Add `Renovate` (preferred over Dependabot for NGI0 cohort signal) config
- [ ] Add `codespell` workflow
- [ ] Add `locale_check` workflow (verify en.json and de.json are key-parity, fail if not)
- [ ] Optionally add multi-OS matrix (Ubuntu + macOS for the test job)
- [ ] Add CI badges to README for each new workflow

### 3.3 Roadmap and release discipline (5 h)

- [ ] `ROADMAP.md` at repo root with quarterly milestones for 2026 Q3 → 2028 Q2
  - Q3 2026: Grant-funded hardening complete; v0.2 with MCP integration test, full governance, public roadmap
  - Q4 2026: Third UI language (Arabic or Ukrainian)
  - Q1 2027: First external NGO deployment
  - Q2 2027: Housing-agent live composition (Phase 2 grant)
  - Q3 2027: Healthcare-agent composition prototype
  - Q4 2027: Multi-country expansion (Austria / France)
  - Q1 2028: Sustainability model proven
- [ ] `CHANGELOG.md` in Keep-a-Changelog format, backfilled from git log
- [ ] First tagged release: `v0.1.0` with release notes
- [ ] Set up GitHub Releases workflow to automate future tagging

### 3.4 Documentation site (3 h)

- [ ] Set up mkdocs-material with a basic site structure (Quickstart, Architecture, Deployment, Contributing, MCP API, Standards)
- [ ] Auto-deploy via GitHub Actions to GitHub Pages
- [ ] Link from README

### Week 3 Definition of Done

- Tests pass on a clean machine without manual hacks
- README displays at least 5 CI badges (license, build, coverage, lint, MCP integration)
- `ROADMAP.md` and `CHANGELOG.md` present
- `v0.1.0` tagged with release notes
- Documentation site deployed to GitHub Pages

---

## Week 4 — Sustainability, differentiation, and application polish

**Goal**: clear the winner bar, plant the differentiation flags, write the application.

**Estimated effort**: ~23 hours.

### 4.1 Sustainability and post-grant story (3 h)

- [ ] `SUSTAINABILITY.md` describing the post-grant model:
  - NGO/Beratungsstelle deployment partners
  - Hosted Pro tier as the sustainability layer (mention it here, not in the main README)
  - Support contracts for institutional deployments
  - Plan for Phase 2 / Phase 3 grant arcs

### 4.2 Differentiation moves (10 h)

- [ ] `ACCESSIBILITY.md` committing to WCAG 2.2 AA *as a deliverable of the grant* (Tenzu pattern)
- [ ] OpenSSF Scorecard workflow + badge in README
- [ ] `security.txt` per RFC 9116 in `static/.well-known/security.txt`
- [ ] Cosign-sign `v0.1.0` release; attach an SBOM in CycloneDX format (`cyclonedx-py`)
- [ ] Optional stretch: add a `flake.nix` for reproducible builds (skip if time-pressed)

### 4.3 Translator pathway (2 h)

- [ ] `docs/translating.md` explaining the JSON file structure and how to add a new locale
- [ ] Native-speaker review of `de.json` for quality — find a German speaker for 2 hours
- [ ] Credit reviewers in AUTHORS.md

### 4.4 Letter of support from an NGO (coordination — ~1 h your time)

- [ ] Cold email 5–7 German migrant-services orgs in Week 1; follow up Week 3
- [ ] Targets: Handbook Germany, Diakonie Berlin Migrationsberatung, Caritas, ProAsyl, IQ Netzwerk, Triple Win, Jobs4Refugees
- [ ] Goal: 1 letter of support attached to the application

### 4.5 Write and dry-run the application (8 h)

- [ ] Draft the proposal against NGI0's application form (questions are public; review the template before drafting)
- [ ] Structure with milestones, each as a verifiable deliverable with a budget line
- [ ] **Pre-empt NLnet's support services**: list which of (a11y audit by HAN, packaging by NixOS Foundation, security audit, mentoring, governance advice) you intend to use
- [ ] Have one person outside the project read it cold for clarity
- [ ] Revise based on feedback

### Week 4 Definition of Done

- `SUSTAINABILITY.md`, `ACCESSIBILITY.md`, `security.txt` all present
- OpenSSF Scorecard badge green in README
- `v0.1.0` release signed with cosign + SBOM attached
- At least one NGO letter of support secured (or active outreach with reply expected)
- Application drafted, reviewed by one outside reader, ready to submit

---

## Application submission checklist (final 24 hours)

- [ ] Final repo state matches the application's claims
- [ ] All blocker fixes from `01-project-brief.md` §"Honest current state" are addressed
- [ ] Application proposal reviewed end-to-end one more time
- [ ] Milestones are concrete, verifiable, and budgeted
- [ ] Letter(s) of support attached
- [ ] Anchor user persona (Aïcha) referenced consistently throughout
- [ ] Standards we implement explicitly listed
- [ ] Submission email/portal used
- [ ] Confirmation received and archived

---

## Tracking notes

Use this section for free-form notes during execution. Date each entry.

**2026-05-17**: Plan created. Pre-flight checklist pending.

<!-- Add new dated notes below this line as execution proceeds -->
