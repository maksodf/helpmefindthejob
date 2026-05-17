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

- [ ] Open with the new positioning: "DirectJob Scout is an open civic employment commons for the European labor-shortage gap..."
- [ ] First sentence references at least one persona concretely (e.g., "Aïcha, a Tunisian-trained nurse working through Anerkennung in Berlin, opens DirectJob Scout.")
- [ ] Add badges row: license (Apache 2.0), CI status, latest release, code coverage, languages, MCP-protocol version
- [ ] Add one screenshot or animated GIF demoing the chat journey end-to-end
- [ ] Add "Standards we implement" section: MCP, schema.org JobPosting, ESCO, EURES schema, WCAG 2.2 AA (target), RFC 9116, GDPR-aligned, Apache 2.0
- [ ] Move Pro/Free billing section below the fold or out of public README entirely
- [ ] Add "Hosted by" notice for The Commons Conservancy (placeholder if not yet admitted)
- [ ] Add quickstart that genuinely works in 5 minutes from a clean machine
- [ ] Add link to documentation site (placeholder if not built yet — built in Week 3)
- [ ] Add link to public demo (placeholder if not built yet — built in Week 3)

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

### 1.5 GitHub repo housekeeping (1 h)

- [ ] Update the repo description to match the new positioning
- [ ] Add topic tags: `civic-tech`, `mcp`, `model-context-protocol`, `jobs`, `employment`, `open-source`, `germany`, `eu`, `migration`, `apache-2-0`, `self-hosted`, `civic-commons`
- [ ] Enable GitHub Discussions
- [ ] Verify default branch is appropriately named

### 1.6 Outreach drafting and sending (6 h)

- [ ] Identify one specific named contact per top-ranked partner (MBE, IQ-Netzwerk, university career service) — use the BAMF database, IQ-Netzwerk regional pages, and university career-service pages
- [ ] Personalise the cold-contact templates in `11-institutional-outreach.md` for each named target
- [ ] Send the first wave of cold contacts (3 outbound: one MBE, one IQ-Netzwerk, one university career service)
- [ ] Draft the housing-agent collaboration message together with the maintainer (Template F in `11-institutional-outreach.md`)
- [ ] Maintainer sends the housing-agent message
- [ ] Send the single optional TU Berlin email (Template G)
- [ ] Update the outreach tracker in `11-institutional-outreach.md`

### 1.7 Production-deployment alignment (3 h)

- [ ] Snapshot the current production deployment state
- [ ] Decide: bring it into alignment with new positioning, take it offline, or replace it with the Week 3 demo deployment
- [ ] Execute the decision

### Week 1 Definition of Done

- LICENSE file present, recognised by GitHub
- All 6+ governance files at root
- README opens with the new positioning, badges visible, one persona referenced
- Zero occurrences of `khalo.org` in code
- Commercial docs moved out of `docs/`
- GitHub repo description and topics updated
- A fresh-clone smoke test passes
- First wave of outreach sent (3 cold contacts + housing-agent friend + optional TU Berlin)
- Production-deployment state addressed

---

## Week 2 — MCP composition, Commons Conservancy, AI Act compliance

**Goal**: the central pitch claim — "MCP-composable, AI-Act-compliant civic-agent infrastructure" — is verifiable by any reviewer reading the repo for 5 minutes. The Commons Conservancy application is submitted.

**Estimated effort**: ~50 hours.

### 2.1 Commons Conservancy application (4 h)

- [ ] Read `commonsconservancy.org/how/` end-to-end
- [ ] Prepare the Programme application: mission alignment, signed Pledge, declared free/open-software commitment
- [ ] Submit the Programme application
- [ ] Confirm receipt; note expected response timing in `04-research-and-decisions.md`

### 2.2 MCP server documentation (6 h) — BLOCKER FIX

- [ ] Create `docs/mcp-server.md` covering the catalogue (initial 8 tools + 5 new Week-2 tools):
  - Tool name, purpose, JSON Schema for input and output, audit-log entry shape, deterministic fallback behaviour, standards alignment, example invocation in Python and TypeScript
  - Protocol version pinned at `2024-11-05`
  - Catalogue version (SemVer): start at v0.1.0
  - Composition patterns explained: sequential handoff, profile-shared, orchestrated (future)
  - Portable civic profile schema linked
  - Error conventions (RFC 7807)
- [ ] Publish JSON Schema for every tool input/output as separate files in `mcp_server/schemas/`
- [ ] Add an `/mcp/schemas.json` endpoint exposing the full catalogue
- [ ] Add a `/mcp/version` endpoint
- [ ] Create `STANDARDS.md` at repo root listing every standard cited

### 2.3 New MCP tools (8 h) — composition expansion

- [ ] Implement `get_user_profile_for_consent` — returns the user's portable civic profile (subset they have consented to share)
- [ ] Implement `propose_referral` — emits a structured referral to another civic agent
- [ ] Implement `query_esco_skill` — looks up an ESCO skill or occupation code
- [ ] Implement `export_eures_compatible` — exports a job listing in EURES schema
- [ ] Implement `record_user_outcome` — persists an outcome event for analytics
- [ ] Add JSON Schemas for all new tools
- [ ] Add unit tests for each new tool

### 2.4 ESCO and EURES integration (4 h)

- [ ] Verify ESCO data licensing (Creative Commons)
- [ ] Download the ESCO taxonomy dataset
- [ ] Map at least 30 high-value occupations covering the persona panel (nursing, engineering, frontend, plumbing trades, elderly care)
- [ ] Map at least 50 corresponding skills
- [ ] Document the mapping in `docs/esco-integration.md`
- [ ] Verify the EURES schema export endpoint produces valid output for sample jobs

### 2.5 Reference integration with the housing agent (8–20 h)

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

- [ ] Add `.github/workflows/mcp-integration.yml`
- [ ] Test spawns the MCP server as subprocess
- [ ] Connects a mock MCP client over stdio
- [ ] Calls `initialize`, expects version `2024-11-05`
- [ ] Calls `tools/list`, expects at least 13 tools
- [ ] Calls `find_company_career_page` and `propose_referral` with known inputs
- [ ] Validates all responses against the published JSON Schemas
- [ ] Clean shutdown
- [ ] Green badge in README

### 2.7 ARCHITECTURE.md (4 h)

- [ ] Write `ARCHITECTURE.md` at repo root
- [ ] Mermaid diagram showing: web app, MCP server as composition surface, future-housing-agent slot, BYO-AI provider abstraction, encrypted profile-at-rest layer, audit-log layer, journey state machine
- [ ] Caption every component with the implementing file/module
- [ ] Cross-link to `09-mcp-composition.md`

### 2.8 AI Act compliance pack (12 h) — BLOCKER FIX

Per `10-ai-act-compliance.md`. Create the `/compliance/` directory and ship:

- [ ] `compliance/risk-management-plan.md` (Article 9)
- [ ] `compliance/data-governance.md` (Article 10)
- [ ] `compliance/technical-documentation.md` (Article 11 + Annex IV — all 9 sections)
- [ ] Audit-log schema documented + audit-log infrastructure integrated into MCP server and web app
- [ ] `compliance/transparency-notice.md` (user-facing, Article 13)
- [ ] `compliance/deployer-operating-manual.md` (Article 13)
- [ ] `compliance/human-oversight-guide.md` + minimal human-oversight UI for deployers (Article 14)
- [ ] `compliance/accuracy-and-bias-testing.md` (Article 15)
- [ ] `compliance/eu-database-registration-template.md` (deployer pre-fill, Article 49)
- [ ] `compliance/fundamental-rights-impact-assessment-template.md` (deployer pre-fill, Article 27)
- [ ] Cross-link from README and from `10-ai-act-compliance.md`

### Week 2 Definition of Done

- Commons Conservancy application submitted
- `docs/mcp-server.md` complete with 13 tools documented
- `STANDARDS.md` lists every standard cited
- ESCO integration covering 30+ occupations
- EURES schema export verified
- Reference integration with housing agent (Option B preferred, Option A fallback acceptable) — shipped in `examples/`
- CI runs MCP integration test, badge is green
- ARCHITECTURE.md with system diagram
- Complete AI Act compliance pack in `/compliance/`

---

## Week 3 — Quality, demo deployment, accessibility, contributor pathway

**Goal**: from "personal MVP" to "looks like a project a community can contribute to and an institution can adopt."

**Estimated effort**: ~40 hours.

### 3.1 Fix the local test environment (3 h)

- [ ] Diagnose the `cryptography` / `cffi` build failure on fresh clones
- [ ] Pin runtime dependencies in `requirements.txt` and dev dependencies in `requirements-dev.txt`
- [ ] Document install order in `CONTRIBUTING.md`
- [ ] Verify `python -m unittest discover` passes on a clean machine
- [ ] Add a fresh-clone Docker smoke-test workflow

### 3.2 CI expansion (8 h)

- [ ] Add `ruff` lint + format check
- [ ] Add `mypy` type check (start with `--ignore-missing-imports`, tighten over time)
- [ ] Add coverage upload to Codecov; add coverage badge to README
- [ ] Add `pip-audit` for CVE scanning
- [ ] Add `Renovate` (preferred over Dependabot for NGI0 cohort signal) config
- [ ] Add `codespell` workflow
- [ ] Add `locale_check` workflow verifying en.json and de.json key parity
- [ ] Add multi-OS matrix (Ubuntu + macOS) where applicable
- [ ] Add OpenSSF Scorecard workflow + badge in README
- [ ] All CI badges visible in README

### 3.3 Roadmap and release discipline (5 h)

- [ ] `ROADMAP.md` at repo root with quarterly milestones for 2026 Q3 → 2028 Q2 (see `03-post-grant.md` for the multi-phase view)
- [ ] `CHANGELOG.md` in Keep-a-Changelog format, backfilled from git log
- [ ] First tagged release: `v0.1.0` with release notes
- [ ] Set up GitHub Releases workflow to automate future tagging

### 3.4 Public demo deployment (6 h)

- [ ] Pick hosting provider (Hetzner Cloud, OVH, Scaleway — all EU-anchored)
- [ ] Secure domain (`directjob-scout.eu` or similar)
- [ ] Deploy the canonical reference implementation
- [ ] Pre-seed with the persona-panel example users (Aïcha, Yusuf, Olga, Mahmoud, Maria)
- [ ] Add health-check monitoring
- [ ] Document the deployment recipe in `docs/deployment-recipe.md`
- [ ] Add the demo URL to README and to the application package

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

<!-- Add new dated notes below this line as execution proceeds -->
