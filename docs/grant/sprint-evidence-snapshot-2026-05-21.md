# Sprint Evidence Snapshot — 4-week Plan, Day 5

**Date**: 2026-05-21
**Branch**: `claude/project-analysis-bpHCo`
**Test suite**: 2075 passing, 14 skipped, 0 failing
**Working tree**: clean

This document is the single-page evidence map a reviewer can use
to verify every claim in the NLnet application against the
running codebase. Each row lists one invariant from the 4-week
plan, where the implementation lives, where the contract tests
live, and the runtime proof (if any).

The snapshot is dated so it ages honestly: a reviewer comparing
this against a later HEAD will see exactly what was true on the
date the application was prepared.

---

## The 15 invariants

| # | Invariant | Implementation | Contract tests | Runtime proof |
|---|---|---|---|---|
| 1 | **Friction-class spec** (published CC-BY-4.0 standard) | `commons/friction-class-spec-v0.1.md`, `company_discovery/persona_fixtures.py` | `tests/test_friction_class_spec_drift_guard.py` (5 tests) | Spec lists all 7 persona slugs; code-spec drift fails CI |
| 2 | **Civic-services mesh** (federation protocol with realistic agents) | `mesh/anerkennung_agent.py`, `mesh/social_services_agent.py`, `mesh/housing_agent.py`, `mesh/common.py` | `tests/test_mesh_agents.py` (21 tests) | Demo walks: `mesh/demo_aicha_walk.py` (5-step), `mesh/demo_yusuf_walk.py`, `mesh/demo_olga_walk.py` |
| 3 | **Trust Receipts** (HMAC-signed AI decision attestations) | `company_discovery/trust_receipt.py`, `company_discovery/trust_receipt_store.py`, `company_discovery/verify_receipt_cli.py` | `tests/test_trust_receipt.py` (19), `tests/test_trust_receipt_integration.py` (8), `tests/test_receipt_coverage_drift_guard.py` (1) | CLI verifier: `python -m company_discovery.verify_receipt_cli <file>.json` |
| 4 | **Bias comparative report** (cross-provider methodology runner) | `scripts/bias_comparative_report.py` | `tests/test_bias_comparative_runner.py` (17 tests) | Cached runs: `data/bias_comparative_cache/{deepseek,ollama}.jsonl` (70 cells each); report: `docs/grant/bias-comparative-report-2026-05-21.md` |
| 5 | **Public transparency dashboard** (DP-noised aggregates) | `company_discovery/transparency.py`, `/transparency` + `/transparency.json` routes in `app.py` | `tests/test_transparency_dashboard.py` (35 tests) | `curl http://localhost:8732/transparency.json` — returns DP-noised counts with privacy mechanism disclosed |
| 6 | **AI Act Article 12 audit log** (HMAC chain) | `company_discovery/audit_log.py` | `tests/test_phase13_audit_log.py` + drift guards | Audit-log chain head visible in `/transparency` response |
| 7 | **Cost-saving doctrine** (proven/plausible/aspirational confidence tagging) | `company_discovery/cost_saving_metrics.py`, `docs/grant/08-cost-saving-doctrine.md` | `tests/test_cost_saving_metrics_69.py` | 8 named mechanisms; thresholds: ≥200 events = proven, ≥30 = plausible |
| 8 | **W3C Verifiable Credentials** (real Ed25519 signatures) | `mesh/verifiable_credentials.py`, `mesh/verify_credential_cli.py` | `tests/test_verifiable_credentials.py` (28 tests) | Sign + verify roundtrip; CLI: `python -m mesh.verify_credential_cli <vc>.json --did-document <did>.json` returns exit 0 on PASS, 1 on FAIL |
| 9 | **No-AI / no-network fallback** | `company_discovery/analysis.py` (manual-mode dispatch branch at line 949) | `tests/test_no_ai_fallback_e2e.py` (10 tests) | Manual provider returns `handoff_required` + prompt; batch `/auto-fit-all` includes per-job prompts |
| 10 | **GDPR Article 17 / 20 plumbing** | `app.py` GDPR endpoints; `company_discovery/audit_log.py` | `tests/test_gdpr_article_20_export.py` | Export endpoint returns user-data dump |
| 11 | **Reproducible build + supply-chain attestations** | `flake.nix`, `docs/releases/v0.1.0-{cosign.pub,sbom.json,source.tar.gz.sigstore,signing.md}`, `static/.well-known/security.txt` | `tests/test_release_supply_chain.py` (17 tests) | CycloneDX SBOM lists all 91 deps; cosign + sigstore artifacts verifiable; security.txt Expires 2027-05-19 (in future per RFC 9116 §2.5.5) |
| 12 | **Accessibility AAA-leaning** (WCAG 2.2 AA achieved, AAA-flavored static contracts) | `static/styles.css` (focus-visible + prefers-reduced-motion + RTL block + text-decoration on `a`), `static/index.html` (skip-link + landmarks + aria-live) | `tests/test_accessibility_static.py` (20 tests), `ACCESSIBILITY.md`, `scripts/accessibility-audit-auth-surfaces.py` | 3 axe-core CLI 4.11 audits passed with 0 violations; static contracts pin against regression |
| 13 | **MCP composability** (5 catalog tools v0.2.0) | `company_discovery/mcp_tools.py`, `mcp_server.py` | `tests/test_mcp_*.py` + `.github/workflows/mcp-integration.yml` | `TOOL_SCHEMAS` exposes ≥5 tools each with name + description + inputSchema |
| 14 | **AI Act compliance pack** | `compliance/transparency-notice.md` (Art. 13), `compliance/deployer-operating-manual.md` (Art. 50), `docs/grant/10-ai-act-compliance.md`, `docs/grant/16-dpia-friction-class.md` | Mirror via `docs/hooks/compliance_mirror.py` | Audit-log + oversight queue wired (admin: `/api/admin/oversight-queue`) |
| 15 | **Multilingual scaffolding** (Phase 2 locales ready) | `static/i18n/locales.json` (registry), `static/app.js` (`loadLocaleRegistry`, `tPlural` via Intl.PluralRules), `static/styles.css` (RTL override block), `.weblate`, `TRANSLATING.md` | `tests/test_multilingual_scaffolding.py` (20 tests) | Registry served via `/i18n/locales.json`; en + de bundles ship; ar/uk/tr/ro listed as `planned` |

## Grant-demo canary

A single test in `tests/test_grant_demo_walk_e2e.py` walks all 15
invariants end-to-end (17 sub-tests + 2 cross-invariant tamper
guards). A failure there means a specific claim in this snapshot
is no longer true on HEAD — diagnose, fix at root.

## Honesty annotations

Per the project doctrine:
- **Stated WCAG target remains 2.2 Level AA**, not AAA. The
  static a11y contracts add CI guardrails for AA invariants
  plus some AAA-leaning extras (prefers-reduced-motion, link
  text-decoration); they do not constitute a full AAA audit.
- **VC encoding uses base64 multibase under the `z` prefix**
  (W3C strict spec is base58btc) and **JCS canonical JSON**
  (W3C is URDNA2015). Documented as Phase 2 upgrades in the
  module docstring at `mesh/verifiable_credentials.py`. Mesh-
  internal interop is full; strict-W3C external interop is a
  Phase 2 upgrade path.
- **Phase 2 locales (ar/uk/tr/ro) ship as scaffolding only.**
  Status `planned`, translationCoverage 0.0. The CLAUDE.md
  doctrine defers actual translations to the post-grant
  roadmap; the scaffolding lands so translator community work
  can plug in via Weblate without engineering review.
- **Reproducible build verification is contract-only.** We
  test the SBOM / cosign / sigstore artifacts are present and
  well-formed; we don't run the Nix flake in CI (Nix on CI is
  out of scope for the 4-week sprint).

## Test count progression (sprint timeline)

| Date | Commit | Tests | New work |
|------|--------|-------|----------|
| 2026-05-21 ~17:00 | (pre-sprint) | 1928 | Baseline after W1 work |
| 2026-05-21 20:24 | a305b36 | 1958 | Invariant 5: transparency dashboard (+30) |
| 2026-05-21 20:48 | e7c8724 | 1986 | Invariant 8: Verifiable Credentials (+28) |
| 2026-05-21 21:06 | a4f8f97 | 1996 | Invariant 9: no-AI fallback (+10) |
| 2026-05-21 21:12 | 5e800c6 | 2001 | Privacy parity: DP on cost-saving (+5) |
| 2026-05-21 21:24 | 70516c8 | 2018 | Invariant 11: supply-chain contracts (+17) |
| 2026-05-21 21:44 | 4fe3b5e | 2038 | Invariant 15: multilingual scaffolding (+20) |
| 2026-05-21 22:00 | 8f4078f | 2058 | Invariant 12: a11y contracts + WCAG 1.4.1 fix (+20) |
| 2026-05-21 22:12 | a1e85b2 | 2075 | Grant-demo walk: cross-invariant canary (+17) |

Cumulative this session: **+147 tests, 8 commits, 0 regressions
introduced.** Every commit ran the full 2000+ regression suite
before landing; every panic-round bug discovered in implementation
was fixed at root, not deferred.

## How to verify this snapshot

```bash
git checkout claude/project-analysis-bpHCo
python -m unittest discover -s tests
# Expect: Ran 2075 tests, OK (skipped=14)

python -m unittest tests.test_grant_demo_walk_e2e -v
# Expect: Ran 17 tests, OK
```

The single canary at `tests/test_grant_demo_walk_e2e.py` is the
fastest way to confirm every claim above is currently true on
HEAD.
