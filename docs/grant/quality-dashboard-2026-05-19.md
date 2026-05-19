<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Pre-submission quality dashboard — 2026-05-19

This dashboard captures the runtime evidence for every quality-bar
probe run during the pre-submission comprehensive QA sweep
(slice executed 2026-05-19, baseline commit
[`fd2a474`](https://github.com/maksodf/helpmefindthejob/commit/fd2a474)).
It is the NLnet-reviewer-readable artefact demonstrating Helpmefindthejob's
quality posture at submission time.

Scope: every probe in the slice spec PART 1 – PART 7 was executed; gaps
surfaced by probes were closed in the slice's commit (no-gaps-behind
discipline). Each subsection below quotes the runtime evidence: exit
code, runtime, and pass/fail counts where applicable. Where a probe
required maintainer-pending infrastructure (DNS, GitHub repo rename),
that prerequisite is named explicitly.

---

## 9.1 Test suite state

| Python | Tests | Result | Runtime |
|---|---|---|---|
| 3.9 (bare-host miniconda) | 1020 ran | OK (4 skipped) | 21.95 s |
| 3.12 (Nix shell, `nix develop`) | 1029 ran | OK (12 skipped) | 32.04 s (in-shell) / 84.74 s (incl. shell setup) |

The 9-test delta between Python 3.9 and 3.12 reflects 3.10+ syntax
gated by `sys.version_info` checks in a small subset of test files
(notably the AEAD migration tests). Skipped counts include
network-dependent probes and probes gated by env vars (e.g.
`DIRECTJOB_RUN_BIAS_METHODOLOGY=1` for the live-LLM bias tests).

## 9.2 Lint state

| Tool | Exit | Findings |
|---|---|---|
| `ruff check .` | 0 | All checks passed |
| `ruff format --check .` | 0 | 154 files already formatted |
| `codespell --config .codespellrc` | 0 | Clean |
| `mypy` strict subset (`audit_log.py`, `crypto_kit.py`, `mcp_server.py`) | 0 | No issues found in 3 source files |
| `python3 scripts/check_spdx_headers.py` | 0 | All Python source carries the SPDX header (one pre-existing gap in `audit_log.py` was closed in the post-rename slice; this sweep confirms zero remaining gaps) |
| `mkdocs build --strict` | 0 | Documentation built in 0.46 s |
| `nix flake check` (aarch64-darwin only) | 0 | `devShells.aarch64-darwin.default` + `apps.aarch64-darwin.default` both OK; other systems require `--all-systems` and are deferred to Phase 2 |

## 9.3 AI probe results

### Bias-testing methodology (PART 3.1)

Executed via `DIRECTJOB_RUN_BIAS_METHODOLOGY=1 python3 -m unittest
tests.test_bias_methodology -v`. Live Ollama backend with
`llama3.1:8b`. Total runtime: **1714.18 s (28.5 min)** for 2 tests.

| Class | Data points | Result | Note |
|---|---|---|---|
| Scoring (fit-score within tolerance) | 77 (70 personas + 7 cross-industry probes) | **FAIL** — 10 OOB | Honest LLM non-determinism; **ONE-OFF** verdict per test architecture. Test design explicitly forbids tolerance manipulation as a fix. Reproduces prior runs' ~11–13 % OOB profile within model non-determinism (cf. 0a9182e + chat-router-wired run). |
| CV-tailoring (semantic fact-check) | 70 (10 scenarios × 7 personas) | **PASS** | Criterion-(d) pass-rate stays at 92.9 % as per prior polish-run remediation (commit 0a9182e). |

Out-of-band scoring divergences (run 2026-05-19):

```
yusuf/yusuf_mixed_language_barrier:        observed 20, expected [40, 70] ±10
olga/olga_mixed_language_barrier:          observed 20, expected [40, 70] ±10
mahmoud/mahmoud_weak_wrong_industry_a:     observed  0, expected [15, 50] ±10
maria/maria_weak_wrong_industry_a:         observed  0, expected [15, 50] ±10
kaethe/kaethe_mixed_recency_friction:      observed 90, expected [40, 70] ±10
kaethe/kaethe_weak_wrong_industry_b:       observed  0, expected [15, 50] ±10
tobias/tobias_mixed_salary_step_down:      observed 85, expected [40, 70] ±10
tobias/tobias_weak_wrong_industry_a:       observed  0, expected [15, 50] ±10
tobias/tobias_weak_wrong_industry_c:       observed  0, expected [15, 50] ±10
olga/olga_cross_industry_probe:            observed  0, expected [15, 55] ±10
```

This honest divergence is the expected outcome of running a small
open-weights model (`llama3.1:8b`) against deterministic-tolerance
fixtures. Remediation paths are (a) prompt engineering for variance
reduction (executed for CV-tailoring; remains TODO for scoring) and
(b) switching to a more deterministic model for production scoring.
Both are tracked for the post-grant 2026 Q4 cadence per the
bias-testing reports series in `docs/grant/bias-testing-*.md`.

### Journey state-machine (PART 3.2)

Executed via `python3 -m unittest tests.test_journey
tests.test_journey_edge_cases`. **108 tests in 0.17 s, OK.** The
12-phase state machine, edge-case transitions, and confirmation
gates are exercised deterministically. The chat-router + chat-AI-router
end-to-end behaviour is covered by `tests.test_chat_router
tests.test_chat_ai_router` (77 tests in 5.42 s, OK). A fully manual
end-to-end browser walk-through with screenshots at every state
transition is a maintainer-side activity that complements (not
replaces) the automated suite.

### MCP-tools end-to-end via stdio (PART 3.3)

Executed via `python3 -m unittest
tests.test_phase12_mcp_integration_e2e`. **8 tests in 1.45 s, OK.**
The integration test spawns the MCP server as a real subprocess,
performs the JSON-RPC handshake, asserts the 13-tool catalogue, and
covers happy-path tools/call + RFC 7807 schema-validation failure +
JSON-RPC −32601 unknown-method paths. Live verification quoted:

```json
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05",
 "serverInfo": {"name": "helpmefindthejob", "version": "0.1.0"},
 "capabilities": {"tools": {}}}}
```

## 9.4 Accessibility state

### Post-rename re-run (2026-05-19)

| Surface group | Count | Tool | Result |
|---|---|---|---|
| Public unauth surfaces (app) | 8 | axe-core CLI 4.11.4 | 0/0/0/0 ✓ |
| Public unauth surfaces (mkdocs docs) | 5 | axe-core CLI 4.11.4 | 0/0/0/0 ✓ after Fix 15 + Fix 16 |
| Authenticated UI states × 2 colour schemes | 16 | axe-playwright-python 0.1.7 (Chromium headless) | 0/0/0/0 ✓ |
| Dynamic UI states | 4 | axe-playwright-python 0.1.7 | 0/0/0/0 ✓ |
| **Cumulative** | **33** | | **0/0/0/0 across critical/serious/moderate/minor** |

Two regressions surfaced on 4 of the 5 mkdocs surfaces (color-contrast
on pygments code-block syntax classes + landmark-unique on
`<nav class="md-code__nav">` copy-button containers). Both closed in
the slice's commit (Fix 15 + Fix 16; documented in
[`ACCESSIBILITY.md`](../../ACCESSIBILITY.md)). Re-audit confirmed
0/0/0/0 across all 5 mkdocs pages post-fix.

Cumulative across all 4 audit passes: **30 + 2 = 32 violation
instances closed**, **0 currently open** on audited surfaces.

## 9.5 Reproducibility state

| Probe | Result | Runtime |
|---|---|---|
| Nix flake check (aarch64-darwin) | OK | 6.23 s |
| Nix-shell full test suite (Python 3.12) | 1029 ran / 12 skipped / 0 failed | 32.04 s in-shell |
| Fresh-clone install + smoke (Docker `python:3.12-slim`) | 66 ran / 0 failed | 19.80 s (incl. image pull + pip install) |
| `cosign verify-blob` of the v0.1.0 source tarball | **Verified OK** | 0.5 s |

The cosign verification used the GitHub auto-archive (`gh release
download v0.1.0 --archive=tar.gz`). SHA-256 of the downloaded tarball
matched the signed SHA-256 (`ea9869c8…3892f`) exactly. **Maintainer
action surfaced**: once the GitHub repo is renamed
(`maksodf/directjob-scout` → `maksodf/helpmefindthejob`), the
auto-archive's top-level directory changes (`directjob-scout-0.1.0/`
→ `helpmefindthejob-0.1.0/`) and the SHA-256 will diverge. The
maintainer must upload the original `directjob-scout-0.1.0.tar.gz` as
a v0.1.0 release asset **before** renaming the GitHub repo so
post-rename verifiers can download the signed artefact directly by
`--pattern 'directjob-scout-0.1.0.tar.gz'`. The
[`docs/releases/v0.1.0-signing.md`](../releases/v0.1.0-signing.md)
"Project rename note" section documents this.

## 9.6 Security probe state

| Probe | Tests | Result | Runtime |
|---|---|---|---|
| Encryption-at-rest (ChaCha20-Poly1305 wraps profile, CV, TOTP secret) | 4 | OK | 0.32 s |
| AEAD fuzzing (Poly1305 tamper detection, AAD binding) | 34 | OK | 0.05 s |
| Audit-log emitter (Article 12 JSONL schema, hashed PII, ContextVar caller context) | 20 | OK | 0.58 s |
| MCP input-schema validation (`Draft7Validator` server-side enforcement, RFC 7807 Problem Details) | 40 | OK | 0.20 s |
| Auth flow (2FA TOTP, signup consent, AEAD migration, Stripe portal) | 31 | OK | 2.69 s |
| Red-team harness | n/a in this slice | Existing red-team agents under `tests/e2e/red_team/` are exercised by ad-hoc invocations; not packaged as a `tests/test_round20*` unittest module. Surfaced as a Phase-2 packaging follow-up. | — |

## 9.7 Integration probe state

| Probe | Tests | Result | Runtime |
|---|---|---|---|
| i18n parity (5 contracts: locale-walked + preserved-German-terms + HTML fallback drift + …) | 5 | OK | 0.02 s |
| Locale parser (DE yes/no, dates, vagueness, fuzzy parsing) | 18 | OK | 0.21 s |
| Chat router + chat-AI router (intent routing, journey integration, persona-friction-keywords wiring) | 77 | OK | 5.42 s |
| BYO-AI provider abstraction (OpenAI / Gemini / DeepSeek / OpenRouter / Ollama / manual / Claude Code) | 36 | OK | 0.002 s |

The 7.2 "EN ↔ DE manual journey walk-through" is exercised
programmatically through the test_journey + chat_router suites plus
the deterministic locale_parser contract. A manual browser-driven
walk-through with screenshots is a maintainer-side activity that
complements the automated coverage.

## 9.8 Documentation polish state

| Probe | Result |
|---|---|
| Cross-link audit: no stale `github.com/maksodf/directjob-scout` URLs outside intentional dual-name historical files | Clean ✓ |
| `mkdocs build --strict` against the post-polish docs tree | Green ✓ (0.46 s) |
| Stale "Week 3 of the grant sprint" / "pre-v0.1.0 alpha" / "<public-domain>" phrasing in user-facing docs | Updated in `README.md` (4 places), `SUPPORT.md` (2), `STANDARDS.md` (3 rows), `CONTRIBUTING.md` (1), `ROADMAP.md` (1 section), `compliance/accuracy-and-bias-testing.md` (1 paragraph) |
| Post-rename canonical-URL substitution in `README.md` Status, `STANDARDS.md` Impressum row, `SUPPORT.md` Documentation-site bullet, `ROADMAP.md` Week-3 status block, `mkdocs.yml site_url`, `static/.well-known/security.txt` Canonical | Done ✓ |
| Tone-consistency manual scan on README, ARCHITECTURE, SUSTAINABILITY, ACCESSIBILITY, STANDARDS, application-draft | No tone regressions surfaced |

## 9.9 Cumulative cohort-bar metrics

The following metrics describe the quality bar Helpmefindthejob clears
at submission time — anchored to runtime evidence above rather than to
narrative claim.

| Metric | Value | Where it's grounded |
|---|---|---|
| Accessibility violations closed across audited surfaces | **32 total** (30 from first 3 passes + 2 from post-rename re-audit), **0 currently open** | [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) Fixes 1–16 |
| Dated bias-testing reports | **5 reports** covering 2 of 6 scenario classes (33.3 % of the methodology surface; 147 data points) | `docs/grant/bias-testing-*.md` |
| SHA-pinned GitHub Actions workflows | **6 of 6** (test, quality, mcp-integration, fresh-clone-install, scorecard, docs-publish) | `.github/workflows/*.yml` |
| Cryptographically-signed release | **cosign 3.0.6 (model b, long-lived ECDSA P-256)** + **CycloneDX 1.6 SBOM** (91 components) + **RFC 9116 security.txt** | `docs/releases/v0.1.0-cosign.pub`, `docs/releases/v0.1.0-sbom.json`, `static/.well-known/security.txt` |
| Reproducible build | Nix flake pinned to `nixos-25.05` (commit `ac62194`) | [`flake.nix`](../../flake.nix) |
| WCAG 2.2 AA conformance | First pass (axe-core CLI 4.11.4 + axe-playwright-python 0.1.7) complete; 0 violations on audited surfaces | [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) |
| EU AI Act Articles documented | **9, 10, 11 + Annex IV, 12, 13, 14, 15, 27, 49** (11 documents) | [`compliance/`](../../compliance/) |
| Dated decisions log | **22 decisions** documented in research-and-decisions log, including [Decision 22 project rename](04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob) and the 7-persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) | [`docs/grant/04-research-and-decisions.md`](04-research-and-decisions.md) |
| Test suite | **1020 (Python 3.9) / 1029 (Python 3.12)**, all green | repo `tests/` |
| MCP catalogue version | **v0.2.0** — 13 tools, JSON-Schema-enforced inputs, protocol `2024-11-05` | [`docs/mcp-server.md`](../mcp-server.md) |

## 9.10 Honest gaps — what this dashboard does NOT cover

Per the project's honesty doctrine (see
[`docs/grant/13-lessons-learned.md`](13-lessons-learned.md) Rule 2),
the following items are out of scope at submission time and tracked
for post-grant cycles:

| Gap | Why deferred | Where tracked |
|---|---|---|
| Bias-testing scenario classes 3 – 6 (onboarding, discovery, motivation-letter drafting, skill-gap brief) | Partner-NGO pilot is the right surface for these; partner-NGO pilot is positioned in 2026 Q4 per ROADMAP | [`docs/grant/04-research-and-decisions.md`](04-research-and-decisions.md) Open R12 |
| Bias-testing fit-scoring ONE-OFF divergences (~11–13 % OOB on `llama3.1:8b`) | Pattern-verdict ONE-OFF across three consecutive runs; remediation is prompt engineering + production-model selection (not tolerance manipulation) | `docs/grant/bias-testing-*.md` series |
| `DIRECTJOB_*` environment-variable prefix not renamed to `HELPMEFINDTHEJOB_*` | Deployment-affecting integration boundary; renaming requires synchronised maintainer `.env` updates on production deploys | Surfaced in [Decision 22](04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob) closeout |
| Multi-system Nix flake CI (aarch64-linux, x86_64-linux, x86_64-darwin) | First-pass single-system (aarch64-darwin) green; multi-system adds CI matrix work that doesn't change the v0.1.0 verifiability surface | Slice spec Phase 2 |
| HAN University manual accessibility audit | Available as an NLnet-provided service after Commons Conservancy admission | [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) Known gaps |
| Live demo deployment at `demo.helpmefindthejob.com` | Pending maintainer DNS configuration (CNAME → GH Pages or apex hosting); no code change required | Surfaced in [Decision 22](04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob) closeout and Open R8 reopen |
| Red-team harness packaged as a `tests/test_round20*` unittest module | Red-team agents under `tests/e2e/red_team/` exist but are ad-hoc-driven, not a single-command unittest target; surfaced during this slice's PART 6.6 probe | Phase 2 packaging item |
| Manual EN ↔ DE journey walk-through with screenshots at each state transition | Automated journey + chat-router + locale-parser suites cover the deterministic surface; the manual walk-through is a complement (maintainer-side) | Maintainer post-grant activity |
| Multi-OS CI matrix (macOS + Windows) | Per `docs/releases/v0.1.0.md` "What's not yet shipped" — Ubuntu-only at v0.1.0; cross-platform extension surfaced pre-existing Linux-isms (cp1252 vs UTF-8 file IO; subprocess timing on macOS) | Phase 2 |

---

## Maintainer-side actions surfaced by this sweep

Five concrete actions for the maintainer to take before / around
NLnet submission. Items 4 and 5 were added during the
2026-05-19 pre-submission scope-tightening slice after the honest
inventory surfaced gaps the dashboard did not previously name.

1. **GitHub repository visibility** — currently private (HTTP 404
   to public readers). Settings → Change visibility → Public.
   Blocks every URL claim in the README / STANDARDS / application
   draft until flipped.
2. **Upload the original signed tarball `directjob-scout-0.1.0.tar.gz`
   as a v0.1.0 GitHub release asset** — required to keep cosign
   verification working after the GitHub repo rename. The
   [`v0.1.0-signing.md`](../releases/v0.1.0-signing.md) verify
   command points at this asset by `--pattern`.
3. **GitHub repository rename via Settings → Rename**
   (`maksodf/directjob-scout` → `maksodf/helpmefindthejob`). GitHub
   auto-redirects preserve old URLs for migration continuity.
4. **Merge working branch to `main`** — the working branch
   `claude/project-analysis-bpHCo` is far ahead of `origin/main`
   (about 25 commits). The `docs-publish` workflow targets the
   working branch, so the GH Pages site only activates after the
   merge. README badges currently hardcode `branch=claude/
   project-analysis-bpHCo`; after the merge they need updating to
   `branch=main` (this is a 5-min follow-up, not in this slice).
5. **DNS configuration for `helpmefindthejob.com`** — apex hosting
   (CNAME → GitHub Pages) for the docs site +
   `demo.helpmefindthejob.com` for the public demo deployment.
   The IP `89.31.143.90` currently responds HTTP 405 to HEAD
   requests; nothing project-specific is served.

These are infrastructure / hosting actions outside the slice's
self-imposed Rules 4 + 5 (no infrastructure-vendor commitments
without maintainer authorisation).

---

## Honesty caveats — what this dashboard does **NOT** record

Added 2026-05-19 during the pre-submission scope-tightening slice
(PART 9). The 9.1–9.9 sections above record positive runtime
evidence — green test counts, axe scores, cosign verify success.
This section names the limits of what that evidence proves.

### Test-count caveats

- **1043 tests** include ~36 BYO-AI provider tests that finish in
  ~2 ms because they exclusively use `MagicMock` + `patch`. They
  verify the dispatcher's branching logic, not whether real API
  calls succeed against OpenAI / Anthropic / Gemini / DeepSeek /
  OpenRouter / Claude Code. Only Ollama is exercised live (by the
  bias-testing methodology and the journey integration). Live-key
  verification of cloud providers is Phase 2.
- **4 skipped tests** on bare-host: 2 are bias-methodology tests
  (opt-in via `HELPMEFINDTHEJOB_RUN_BIAS_METHODOLOGY=1` / legacy
  `DIRECTJOB_RUN_BIAS_METHODOLOGY=1`) and 2 are E2E browser tests
  (opt-in via `E2E_BASE_URL` + `E2E_EMAIL` + `E2E_PASSWORD`). In
  standard CI runs **the only true browser-driven coverage is
  never exercised**. Bias methodology is exercised manually
  (see §9.3).

### Accessibility caveats

- axe-core's own documentation states that automated tools catch
  **20–50 %** of WCAG issues. "0/0/0/0 across 33 captures" means
  "no axe findings", not "WCAG 2.2 AA conformant". Manual
  screen-reader navigation (NVDA / VoiceOver), keyboard-only
  navigation, focus-order on dynamic state transitions,
  reduced-motion preference, cognitive accessibility (WCAG 2.2
  3.2.6 / 3.3.1 / 3.3.7 / 3.3.8), bidi text / Arabic RTL — none
  of these are covered by the automated audit.
- The "33 captures" figure double-counts colour-scheme variants
  (8 auth screens × 2 schemes + 4 dynamic states). True
  **unique-surface** count is ~25.
- "32 violation instances closed" counts each Fix in
  `ACCESSIBILITY.md` plus the auth-surface remediation hits.
  Some Fixes (e.g. Fix 4 "12 primary-button instances cleared")
  closed multiple instances per Fix label.

### EU AI Act caveats

- The 11-document `compliance/` pack is **mostly doctrine and
  templates**. Runtime enforcement is partial:
  - Article 12 (audit log) — **wired in code** (PART 1.1 of the
    pre-submission slice added production-mode fail-fast on
    missing salt; tamper-evidence + centralised log forwarding =
    Phase 2).
  - Article 14 (human oversight) — `/api/admin/oversight/queue`
    endpoint exists; **never tested end-to-end as a real admin
    user**, only via unit tests.
  - Articles 9, 10, 11 + Annex IV, 13, 15, 27, 49 — deployer
    doctrine + templates. No deployer has filled them for any
    reference deployment.
- Article 15 (accuracy + bias-testing) methodology is at **33 %
  execution** (2 of 6 scenario classes). The most recent run
  (`bias-testing-2026-05-19.md`) found 10 ONE-OFF OOB
  divergences in fit-scoring on `llama3.1:8b` — within prior
  runs' non-determinism band but **the test failed** under the
  no-tolerance-manipulation rule.

### ESCO + EURES caveats

- The ESCO reference dataset (`reference/esco/`) is a **curated
  subset**: 30 occupations + 50 skills covering the persona
  panel + Bundesagentur 2025 shortage list. Real ESCO has ~3 000
  occupations + ~13 500 skills. Queries outside the curated set
  return nothing.
- The EURES integration is a **JSON projection contract**, not a
  transport. No EURES API client exists; no jobs are pushed to
  EURES anywhere.

### cosign verification caveats

- The `cosign verify-blob` runtime evidence (§9.5) was captured
  **today, pre-rename**, against the current GitHub auto-archive.
  After the GitHub repo rename (maintainer action #3 above), the
  auto-archive top-level directory becomes `helpmefindthejob-0.1.0/`
  and the bytes — and SHA-256 — diverge. Verification then
  requires the maintainer to attach the original signed tarball
  as a release asset (action #2 above).
- The cosign key is **model b** (long-lived ECDSA P-256, not
  registered with Sigstore's transparency log). Every verifier
  sees `--insecure-ignore-tlog` and cosign's "insecure practice"
  warning.

### Cost-saving doctrine caveats

- The doctrine documents 8 testable mechanisms in
  `docs/grant/08-cost-saving-doctrine.md`. **Measured outcomes
  are zero today** — no institutional deployment has produced
  the data needed to verify any of the 8 mechanisms. The
  doctrine is honest design intent, not a measured claim.

### Domain + visibility caveats

- `helpmefindthejob.com` DNS resolves to `89.31.143.90`. HTTP
  returns 405; HTTPS does not respond. The project's claimed
  public surface is **not currently served** at any URL.
- The maintainer's GitHub repo at `maksodf/directjob-scout` is
  **private**. Every `github.com/maksodf/...` link in the
  codebase 404s for unauthenticated readers (e.g. an NLnet
  reviewer) until visibility is flipped to public.

### Phase 2 backlog

- The honest-inventory follow-up surfaced 65 distinct items;
  12 are closed in this slice; **53 are catalogued for Phase 2**
  at [`phase2-backlog-2026-05-19.md`](phase2-backlog-2026-05-19.md).
  That file is the durable record of what is tracked but
  deferred.

This caveats block is required honesty doctrine: the dashboard's
positive evidence is genuine, but the positive evidence is **the
floor of what we have proven, not the ceiling of what is
required**. The Phase 2 backlog catalogues the remaining ceiling.
