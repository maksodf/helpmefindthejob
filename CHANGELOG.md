<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Changelog

All notable changes to **Helpmefindthejob** are documented in this file.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning 2.0.0](https://semver.org/).

Section order per release: **Added · Changed · Deprecated · Removed ·
Fixed · Security**.

---

## [Unreleased]

Tracked in `docs/grant/02-execution-plan.md` §3.4 – §4.6 plus Phase 2 cleanup
items in `docs/grant/03-post-grant.md`.

This block covers every commit landed on `claude/project-analysis-bpHCo`
between the `v0.1.0` tag (commit `0cdf13e`) and the pre-submission
scope-tightening slice. Cuts into a future v0.2.0 once the maintainer
green-lights the application + closes the maintainer-side actions
listed under "Maintainer follow-ups" in
[`docs/grant/quality-dashboard-2026-05-19.md`](docs/grant/quality-dashboard-2026-05-19.md).

### Added

- **Project renamed to Helpmefindthejob** with the canonical domain at
  `helpmefindthejob.com` ([Decision 22](docs/grant/04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob),
  forward-going per Decision 12). 271 files renamed; intentional
  dual-name content preserved in the identity-of-record files
  (`CHANGELOG.md`, `CONTRIBUTORS-NOTE.md`, `docs/releases/v0.1.0*`,
  `docs/grant/04-research-and-decisions.md`).
- **`company_discovery/env_compat.py`** — env-var compatibility shim
  exposing `get_env(new, legacy, default)`, `get_env_int`, and
  `get_env_bool`. Tries the canonical `HELPMEFINDTHEJOB_*` prefix
  first; falls back to `DIRECTJOB_*` and `COMPANY_DISCOVERY_*` with
  a `DeprecationWarning`. Tests in `tests/test_env_compat.py`
  (17 cases). Doctrine + migration path in
  [`docs/deployment-recipe.md`](docs/deployment-recipe.md).
- **Audit-log production fail-fast** — when the application
  environment is anything other than `development`/`dev`/`test`/
  `testing`, `_resolve_salt` refuses to start without
  `HELPMEFINDTHEJOB_AUDIT_SALT` (legacy `DIRECTJOB_AUDIT_SALT`).
  6 regression tests in
  `tests/test_phase13_audit_log.py::SaltFailFastTests`. Documented
  in [`compliance/audit-log-schema.md`](compliance/audit-log-schema.md).
- **Quality dashboard** at
  [`docs/grant/quality-dashboard-2026-05-19.md`](docs/grant/quality-dashboard-2026-05-19.md)
  capturing every PART 1–7 probe result from the pre-submission
  comprehensive QA pass (1020 / 1029 tests across Python 3.9 + 3.12,
  axe-core + axe-playwright accessibility coverage, cosign verify,
  fresh-clone Docker, ESCO/EURES surface counts).
- **Phase 2 backlog index** at
  [`docs/grant/phase2-backlog-2026-05-19.md`](docs/grant/phase2-backlog-2026-05-19.md)
  enumerating ~53 inventory items tracked for post-grant cycles
  (2026 Q3 / Q4 / 2027 Q1).
- **mkdocs-material documentation site** (§3.5) with deploy workflow
  to GitHub Pages and `mkdocs build --strict` green.
- **OpenSSF Scorecard SHA-pinning** — all 6 GitHub Actions workflows
  pinned to full 40-char commit SHAs (`scorecard.yml`, `test.yml`,
  `quality.yml`, `mcp-integration.yml`, `fresh-clone-install.yml`,
  `docs-publish.yml`).
- **`ACCESSIBILITY.md`** (§3.6) — three audit passes documenting
  the first automated WCAG 2.2 AA pass + auth-surface follow-on
  via Playwright + light-mode / dynamic-state polish; cumulative
  32 violation instances closed across 22 (later 33) audited
  captures. Fix 15 + Fix 16 from the pre-submission slice closed
  pygments-contrast + landmark-unique regressions surfaced on
  the post-rename re-audit.
- **`docs/translating.md`** (§3.7) — translator contributor
  pathway (terminology hygiene, parity test, preserved-German-
  terms lint, HTML fallback drift contract).
- **Nix flake** (§3.8) at [`flake.nix`](flake.nix) pinning
  `nixos-25.05` (commit `ac62194`); `nix flake check` and
  `nix develop --command python3 -m unittest discover -s tests`
  both green on aarch64-darwin.
- **cosign-signed v0.1.0 + CycloneDX 1.6 SBOM + RFC 9116
  security.txt** (§4.2). Cosign key model b (long-lived ECDSA
  P-256, `--insecure-ignore-tlog`); SBOM with 91 components;
  security.txt at [`static/.well-known/security.txt`](static/.well-known/security.txt)
  citing `helpmefindthejob.com` as the canonical reporting URL.
- **`SUSTAINABILITY.md`** (§4.1) — post-grant story, grant arc,
  community pathway.
- **Application draft** at
  [`docs/grant/application-draft-2026-05-19.md`](docs/grant/application-draft-2026-05-19.md)
  (22 fields, ~13.5k words); NLnet form-fields cross-reference at
  [`docs/grant/nlnet-form-fields-2026-05-19.md`](docs/grant/nlnet-form-fields-2026-05-19.md);
  outreach drafts at [`docs/grant/outreach-drafts/`](docs/grant/outreach-drafts/);
  external-reader recruit message at
  [`docs/grant/external-reader-recruit-message-2026-05-19.md`](docs/grant/external-reader-recruit-message-2026-05-19.md).
- **Bias-testing dated reports** —
  [`bias-testing-2026-05-18.md`](docs/grant/bias-testing-2026-05-18.md),
  [`bias-testing-2026-05-18-broadened.md`](docs/grant/bias-testing-2026-05-18-broadened.md),
  [`bias-testing-2026-05-18-polish.md`](docs/grant/bias-testing-2026-05-18-polish.md),
  [`bias-testing-2026-05-19.md`](docs/grant/bias-testing-2026-05-19.md).
- **`friction_keywords_for(persona_id)`** helper in
  `company_discovery/persona_fixtures.py`, wired into the production
  chat-router CV-tailoring path at `app.py:3411` + `app.py:7702`
  (closes deferred remediation #1 of the prompt-enhancement
  bias-test run; 6 regression tests in `tests/test_round4.py`).
- **`CONTRIBUTORS-NOTE.md`** rename-paragraph + git-archaeology
  guidance for the 2026-05-19 rename.

### Changed

- **README, STANDARDS, application-draft, 12-application-package**
  reframed with honesty caveats (pre-submission scope-tightening
  slice PART 2): ESCO described as a curated reference dataset
  (full taxonomy = Phase 2); EURES described as a projection
  contract (live API transport = Phase 2); WCAG 2.2 AA framed as
  target with axe-coverage caveat (HAN University manual review =
  next pathway); AI Act compliance described as a documented
  pack with Articles 12 + 14 wired in code and the remaining
  articles as deployer-doctrine artefacts; BYO-AI described as a
  seven-provider abstraction with Ollama exercised live and the
  cloud providers covered by mocked dispatcher tests; cost-saving
  doctrine described as a testable hypothesis pending measured
  outcomes.
- **CV-tailoring production prompt** (`company_discovery/analysis.py`
  `build_cv_tailoring_prompt`) now asks the model to acknowledge
  persona friction context — closes the polish-run criterion-(d)
  finding. Bias-test re-run at `bias-testing-2026-05-19.md`:
  criterion (d) pass-rate 43/70 → 65/70 (92.9 %); overall pass-rate
  43/70 → 61/70 (87.1 %; above the 70 % threshold).
- **README badges** + `mkdocs.yml site_url` + `static/.well-known/
  security.txt Canonical` field point at `helpmefindthejob.com`.
- **Audit-log emitter** docstring + variable references in
  `compliance/audit-log-schema.md` updated to name the
  `HELPMEFINDTHEJOB_*` prefix as canonical; legacy
  `DIRECTJOB_*` named for back-compat.
- **MCP integration test client** (`tests/test_phase12_mcp_integration_e2e.py`)
  now closes subprocess stdout/stderr pipes + tempdir in a
  `finally` block — `ResourceWarning` no longer surfaces under
  `python3 -W error::ResourceWarning`.

### Deprecated

- **`DIRECTJOB_*` environment-variable prefix** (60+ variables) —
  accepted with `DeprecationWarning` through Phase 2; removed in
  Phase 3 (see `docs/deployment-recipe.md` migration path).
- **`COMPANY_DISCOVERY_*` environment-variable prefix** (4
  variables: `_ENV`, `_DATA_DIR`, `_HOST`, `_PORT`) — same migration
  schedule.

### Removed

- (intentionally empty for this block)

### Fixed

- **Accessibility regressions** surfaced by the post-rename axe
  re-run on the 4 mkdocs surfaces (`/mcp-server/`, `/deployment-recipe/`,
  `/production-deployment/`, `/esco-integration/`): pygments
  comment/docstring/variable contrast bumped from 4.47:1 → ~6.1:1
  via scoped overrides in `docs/stylesheets/accessibility.css`
  (Fix 15); each `<nav class="md-code__nav">` copy-button container
  gets a unique aria-label via
  `docs/javascripts/accessibility.js` (Fix 16).
- **`company_discovery/audit_log.py` SPDX-License-Identifier
  header** — pre-existing gap from the Week 2 task 2.8 commit
  closed during the rename slice's no-gaps-behind sweep.
- **i18n parity test** generalisation + **preserved-German-terms
  lint** + **HTML fallback drift test** (§3.7 hardening, three
  contracts added to `tests/test_phase0_i18n_parity.py`).
- **Cosign verification post-rename** — verification commands in
  `docs/releases/v0.1.0-signing.md` + `docs/releases/v0.1.0.md`
  now download the original signed `directjob-scout-0.1.0.tar.gz`
  by `--pattern` + `--output v0.1.0-source.tar.gz` so the SHA-256
  match holds regardless of the GitHub repo's current name. The
  maintainer follow-up to attach the original tarball as a v0.1.0
  release asset is recorded in
  [`CONTRIBUTORS-NOTE.md`](CONTRIBUTORS-NOTE.md).

### Security

- **Audit-log production fail-fast** (see Added) materially
  hardens Article 12 record-keeping by refusing to start a
  production process whose audit-log salt is unset (which would
  silently produce uncorrelatable hashes across restarts).
- **cosign-signed source tarball** + **CycloneDX 1.6 SBOM** +
  **RFC 9116 security.txt** ship with v0.1.0 (`docs/releases/v0.1.0-*`,
  `static/.well-known/security.txt`).
- **TOTP-secret column AEAD migration** (ChaCha20-Poly1305
  AAD-bound to user_id) — already in v0.1.0; no behaviour change
  in this block.

---

## [0.1.0] — 2026-05-18

First stable pre-publication release. Closes the four-week
**NLnet NGI Zero Commons Fund grant-readiness sprint** that ran from
**2026-05-17** through this tag. The release deliberately frames the
project as a **civic commons** under Apache 2.0 + CLA, application
to The Commons Conservancy pending, EU AI Act compliant by design.

### Added

- **Apache 2.0 licensing pack** — `LICENSE`, `NOTICE`, `TRADEMARK.md`,
  `cla.md`, and SPDX-License-Identifier headers across every Python
  source file. Pre-commit hook enforces the SPDX header on every commit
  (Week 1 task 1.1).
- **Governance pack** — `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), `SECURITY.md`, `SUPPORT.md`,
  `AUTHORS.md` (consent-first authorship placeholders),
  `ACKNOWLEDGMENTS.md`, `.github/ISSUE_TEMPLATE/`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `.github/CODEOWNERS`
  (Week 1 task 1.2).
- **Civic-commons-positioned README** with the persona-anchored opening
  (Aïcha + Käthe vignette), Standards we implement section, MCP
  composition section, self-hosting steps, Apache 2.0 + Commons
  Conservancy framing (Week 1 task 1.3).
- **Grant-application planning workspace** at `docs/grant/` — 14
  documents covering the project brief, decisions log, execution plan,
  research findings, risk register, stakeholder map, glossary, persona
  panel, cost-saving doctrine, MCP composition spec, EU AI Act
  compliance plan, institutional-outreach strategy, application
  package draft, behavioural rules / lessons-learned for advisory
  sessions.
- **Commons Conservancy Programme application draft** at
  `docs/grant/commons-conservancy-application-2026-05-18.md`
  (Week 2 task 2.1).
- **MCP server documentation** at `docs/mcp-server.md` + standards
  manifest at `STANDARDS.md` (Week 2 task 2.2).
- **MCP catalogue v0.2.0** — five composition-oriented tools added on
  top of the legacy 8 (`propose_referral`, `summarise_outcomes`,
  `bundle_civic_context`, `query_esco_skill`,
  `export_eures_compatible`) — 13 tools total with JSON Schema
  Draft 7 inputs documented and enforced server-side
  (Week 2 task 2.3).
- **ESCO + EURES integration** — curated reference dataset
  (30 occupations, 51 skills) under `reference/esco/`, German +
  English labels, persona-panel cross-link, with the `query_esco_skill`
  tool and the `export_eures_compatible` projection
  (Week 2 task 2.4).
- **Reference housing-agent integration scope** — `docs/grant/` Decision
  20 narrows the §2.5 deliverable to Option A (mock stub) or Option B
  (real friend collaboration), with self-built variants deferred to
  Phase 2.
- **MCP integration end-to-end CI test** —
  `tests/test_phase12_mcp_integration_e2e.py` spawns the MCP server as
  a real subprocess, drives it over JSON-RPC over stdio, asserts the
  13-tool catalogue + protocol version + happy-path tools/call +
  schema-validation failure path. README badge added
  (Week 2 task 2.6).
- **ARCHITECTURE.md** at repo root with Mermaid diagram and component
  map (Week 2 task 2.7).
- **EU AI Act compliance pack** at `/compliance/` — 11 documents
  covering Articles 9, 10, 11+AnnexIV, 12, 13 (user-facing +
  deployer-facing), 14, 15, 27 (FRIA template), 49 (EU AI database
  registration template), plus an audience-split index README.
  Friction-class framing per Decision 21 embedded in the four
  user-base-facing files (Week 2 task 2.8).
- **AI Act Article 12 audit-log emitter** at
  `company_discovery/audit_log.py` — JSONL schema v1 with seven event
  types, SHA-256 PII hashing keyed by per-deployment
  `DIRECTJOB_AUDIT_SALT`, ContextVar-based caller-context propagation,
  microsecond-precision rotation with collision nonce, plaintext-PII
  opt-in. Integrated into `mcp_server.py::_handle_tools_call` and
  `company_discovery/analysis.py::_dispatch_provider`. New
  `tests/test_phase13_audit_log.py` exercises emitter + caller-context
  + MCP integration + analysis-pipeline integration + tail helper
  (20 tests).
- **AI Act Article 14 minimum-viable human-oversight admin endpoint**
  at `/api/admin/oversight/queue` (admin-gated, controlled by
  `DIRECTJOB_HUMAN_OVERSIGHT_MODE`). Returns recent audit-log events
  for deployer review with `event_type` filter and `limit` query
  params. Tail helper `_read_ai_act_audit_tail` reads live + rotated
  siblings sorted most-recent-first.
- **Lessons-learned workspace** at `docs/grant/13-lessons-learned.md`
  — 10 behavioural rules captured from prior advisory sessions
  (Friction-driven not demographic-driven framing, verify numerical
  claims, calibrate response length, etc.).
- **Friction-class framing** (Decision 21) — public-facing artifacts
  reframed from "for migrants" to "for anyone facing structural
  labor-market friction in Europe, with migrants and EU-mobile
  workers as the most acute use case."
- **Seven-persona panel** (Decision 21) — Käthe (German nurse returning
  after 12 years caregiving) and Tobias (German backend developer
  pivoting commercial → civic-tech) added alongside the existing
  five (Aïcha, Yusuf, Olga, Mahmoud, Maria).
- **Template H** at `docs/grant/11-institutional-outreach.md` — the
  invitation-to-co-create-a-sibling-civic-agent letter for developer
  friends who could build a housing agent from scratch (German text).
- **`pyproject.toml`** — single-source-of-truth config for ruff (lint
  + format-check), mypy (permissive with strict overrides for
  audit_log + crypto_kit + mcp_server), coverage (branch coverage).
- **`requirements-dev.txt`** — pinned dev tooling: pre-commit, ruff,
  mypy, types-jsonschema, types-requests, coverage, codespell,
  pip-audit (Week 3 task 3.2).
- **`.codespellrc`** — codespell config with German-vocabulary
  ignore list and intentional-skip paths.
- **Extended `.pre-commit-config.yaml`** — ruff (lint + format-check)
  and codespell hooks alongside the SPDX-header check.
- **`renovate.json`** — Renovate dependency-automation config
  (activates on Renovate GitHub App install). Groups minor/patch
  updates weekly; major releases get explicit PRs;
  `cryptography` major releases tagged `security-review-needed`.
- **`.github/workflows/quality.yml`** — five-job quality workflow
  (ruff-lint, mypy-strict-subset, codespell, pip-audit, coverage with
  Codecov upload via `codecov-action@v5`).
- **`.github/workflows/scorecard.yml`** — OpenSSF Scorecard via
  `ossf/scorecard-action@v2.4.0` (weekly cron + push-to-main).
- **`.github/workflows/fresh-clone-install.yml`** — matrix over
  `python:3.11-slim` and `python:3.12-slim` containers; verifies fresh
  `pip install -r requirements.txt` + cryptography import +
  representative smoke-test slice (Week 3 task 3.1).
- **README badges**: tests, quality, MCP integration, fresh-clone
  install, OpenSSF Scorecard, Codecov coverage.
- **`ROADMAP.md`** at repo root — quarterly milestones 2026 Q3 → 2028
  Q2 (this release).
- **`CHANGELOG.md`** at repo root (this file).
- **994 tests in the suite** — up from ~925 pre-sprint; new coverage
  for the MCP integration end-to-end path, the AI Act audit-log
  layer, the §2.3 composition tools, the §2.4 ESCO + EURES surface,
  and the AEAD migration for TOTP secrets.

### Changed

- **MCP catalogue version**: v0.1.0 → **v0.2.0** (8 → 13 tools); all
  inputs schema-enforced via `jsonschema.Draft7Validator` server-side
  prior to dispatch.
- **Python minimum**: explicit `requires-python = ">=3.9"` declared in
  `pyproject.toml`; CI matrix tests 3.9 + 3.12.
- **Dependency pins**: `cryptography>=42.0.0,<50.0.0` added explicitly
  to `requirements.txt` with broad-wheel coverage rationale.
- **Cost-saving doctrine mechanism 1**: "Lower advisor caseload per
  migrant served" → "Lower advisor caseload per case served," with
  inline note that the migrant subset remains the densest concentration
  per advisor visit.
- **Housing-agent integration default** (Decision 20, partially
  supersedes Decision 11): §2.5 default is now Option A (mock stub);
  Option B (real friend integration) only if a collaborator confirms;
  self-built (Option C / D) deferred to Phase 2.
- **Persona panel composition** (Decision 21): expanded from five to
  seven personas without removing any; the migrant five remain the
  primary narrative anchor.
- **Codebase format** (one-time normalisation): `ruff format` applied
  across 124 files. No semantic changes; pre-existing inconsistent
  formatting normalised.

### Removed

- **`khalo.org` references** — replaced with `directjob-scout.example`
  placeholders in code, docs, tests, and configuration
  (Week 1 task 1.4). _(Note: per [Decision 22](docs/grant/04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob), the `directjob-scout.example` placeholder convention was subsequently superseded on 2026-05-19 by the real domain `helpmefindthejob.com` when the project was renamed and the domain acquired; the v0.1.0 release shipped with the placeholder convention as the identity-of-record at sign time.)_
- **Tester-name leakage** in code comments and test fixtures
  (Week 1 task 1.4).
- **`keepbuildingtill100%tracker.MD`** at repo root (per Decision 14).
- **`private/` content from git tracking** — pre-sprint commercial-
  vision docs (sellable-readiness, operator-launch, marketing-copy,
  press-kit, launch-day-content, operator-package, operator-starters,
  operator-final-punchlist, legal-review-brief, deployment-handoff)
  relocated to a gitignored `private/` directory.
- **README "Pro / Free" commercial framing** — superseded by the
  civic-commons positioning (Week 1 task 1.3).
- **Outdated commercial-narrative docs from `docs/`** —
  `sellable-readiness-*.md`, `marketing-copy.md`, and related
  pre-sprint materials moved to `private/`.

### Fixed

- **TOTP-secret column AEAD migration** in `auth.py` —
  ChaCha20-Poly1305 wraps the TOTP secret at rest (was previously
  plaintext on the DB column). Migration ladder + decrypt-and-re-wrap
  on first read. Tested in
  `tests/test_phase9_totp_aead_migration.py` and the AEAD fuzz suite.
- **MCP `tools/call` inputSchema enforcement** in `mcp_server.py` —
  pre-dispatch validator returns RFC 7807 Problem Details on schema
  violations and on unknown tool names. Closes the previous gap where
  malformed payloads could reach handler code.
- **Yes/no parser locale awareness** in `company_discovery/locale_parser.py`
  — German `ja/nein` plus colloquial variants accepted; help-prompt
  escape disambiguates from yes/no commands.
- **Pre-existing `mcp-integration.yml` post-success script PYTHONPATH
  bug** — the catalogue-print step had been failing on every push
  since §2.6. `PYTHONPATH=.` env on the step fixes the import resolution.
- **B039 mutable `ContextVar` default** in `audit_log.py` — replaced
  `{}` default with `None`; call sites normalise via `ctx.get() or {}`.
- **F821 forward-reference imports** in `auth.py`,
  `tests/test_phase1_seo_pages.py`, and
  `tests/test_phase3_onboarding_drip.py` — hoisted into
  `TYPE_CHECKING` blocks so the annotations resolve for tooling
  without forcing a runtime import.
- **B005/B030 false positives** in `journey.py` and `chat_router.py`
  — annotated with `# noqa` comments explaining the intentional
  patterns (character-set strip, conditional except).
- **Mypy issues in `mcp_server.py`** — `jsonable` narrows `is_dataclass`
  to instances-only via `not isinstance(value, type)`; `build_tools`
  HTTPFetcher arg tagged with a single targeted
  `# type: ignore[arg-type]` and a follow-up note; `run_stdio` local
  `response` typed explicitly as `dict[str, Any] | None`.
- **Mypy issue in `crypto_kit.py`** — `is_aead_blob` narrows
  `Optional[str]` via `value is not None` (was `bool(value)`).
- **One real misspelling** of "download" in
  `company_discovery/journey.py` and
  `tests/test_journey_edge_cases.py` (caught by codespell on its
  first CI run).

### Security

- **AEAD-at-rest extended to TOTP secrets** — ChaCha20-Poly1305 wraps
  the TOTP-secret column with the same key derivation chain as the
  CV-text column. AAD-binds the ciphertext to the user identifier so
  a row-swap attacker cannot lift another user's TOTP secret.
- **MCP tool-input validation enforced server-side** — every
  `tools/call` dispatch is gated on schema validation prior to
  handler invocation; eliminates the previous risk that a misbehaving
  composing agent could trigger handler-side parse errors.
- **AI Act Article 12 audit-log layer** — every AI invocation, MCP
  tool invocation, and override event is recorded in JSONL with
  PII-hashed identifiers. Per-deployment salt prevents linkability
  across deployments.
- **`cryptography` explicitly pinned** in `requirements.txt`
  (`>=42.0.0,<50.0.0`) — closes the previous fragility where the
  encryption-at-rest layer relied on `pywebpush`'s transitive
  dependency.
- **`pypdf` upgraded** 5.1.0 → 6.10.2+ — closes 22 CVEs flagged by
  `pip-audit --strict` (CVE-2025-55197, CVE-2025-62707,
  CVE-2025-62708, CVE-2025-66019, CVE-2026-22690 through
  CVE-2026-41314).
- **`pip-audit --strict` runs on every push** — fails CI on any new
  vulnerability across runtime + dev dependencies.
- **OpenSSF Scorecard workflow** — weekly automated security-best-
  practices scoring; SARIF results uploaded to GitHub Security tab.
- **`.well-known/security.txt`** at repo root per [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)
  — vulnerability-reporting channel anchored.

---

## [0.0.x] — pre-2026-05-17 (pre-sprint, commercial product)

The codebase pre-dates the grant-readiness sprint as a self-hosted
commercial product with a Pro/Free tier (see Round 1–21 in the
Git log). The active project direction shifted to a **civic-employment
commons** at the start of the four-week sprint; the sanitisation pass
in Week 1 task 1.4 cleared the commercial-vision residue from the
working tree.

The full pre-sprint history is preserved in the Git log (no
history rewrite was performed — see Decision 12 in
`docs/grant/04-research-and-decisions.md`). The honest project
history including the deprecated commercial framing is documented
in [`CONTRIBUTORS-NOTE.md`](CONTRIBUTORS-NOTE.md).

This entry is deliberately brief; the pre-sprint commits are
listed individually only via `git log --before="2026-05-17"`.

---

## How to update this file

When shipping a new release:

1. Move the [Unreleased] section's bullets into a new dated section
   above this paragraph, with the version number (e.g., `[0.2.0] — YYYY-MM-DD`).
2. Re-open an empty [Unreleased] section at the top.
3. Tag the release annotated and create the GitHub Release pointing
   at the new entry plus `docs/releases/vX.Y.Z.md` for the longer-form
   public release notes.
