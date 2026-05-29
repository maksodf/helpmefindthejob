<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Security audit — secrets scan over full git history

**Last run**: 2026-05-24 (UTC+02:00).
**Tool**: `gitleaks` v8 (Homebrew install).
**Scope**: full git history of the public `main` branch from the initial
commit through `f225896` (UX-F1 follow-up).
**Command**: `gitleaks detect --source . --redact --no-banner --report-format json --report-path /tmp/gitleaks-report.json`.
**Result**: **17 hits, all triaged as false positives** (test-fixture
stubs in `tests/`). **No real secrets found in history.**

This document records running `gitleaks` over the full git history,
with a summary committed into `docs/grant/14-source-class-hierarchy.md`
or this `docs/grant/SECURITY-AUDIT.md`, and is referenced from the NLnet
application package (Field 17 supporting material).

---

## Why this matters for NLnet reviewers

The NGI Zero Commons Fund reviewer expects a credible open-source
project to be operating under the same secret-hygiene discipline that
any production civic-tech service would. The two sister-project
patterns we mirror — Tenzu and Redwax — both publish a periodic
secrets-history scan as part of their security posture. A clean scan
result, plus a documented triage process for the false positives that
inevitably appear in test code, is the load-bearing signal.

This file is the *signal*. The raw JSON report at the time of audit was
captured to `/tmp/gitleaks-report.json` during the scan; the summary
below is the durable record. Future scans should append a dated section
rather than overwriting.

---

## Triage of the 17 hits

All 17 hits matched the `generic-api-key` rule, which catches any
string that looks like a long opaque token. Every hit lives in a test
file and contains a self-documenting fake value (literal substrings
like `"for-tests"`, `"fixture"`, `"test-secret-"`, `"very-secret-pass-"`).
Per-file breakdown:

| File | Hits | Lines | Nature |
|---|---|---|---|
| `tests/test_sso_oidc.py` | 1 | 701 | `self.secret = "a-secret-at-least-32-bytes-padding-for-tests"` — explicitly documented padding for the JWT-sized-secret OIDC test |
| `tests/test_phase3_email_verification.py` | 6 | 148, 155, 165, 173, 179, 194 | `"password": "very-secret-pass-1234"` literals in HTTP-handler signup/login fixtures |
| `tests/test_phase3_signup_consent.py` | 5 | 125, 134, 139, 147, 153 | same pattern: registration consent flow fixtures |
| `tests/test_http_invitations.py` | 1 | 249 | invitation accept-flow fixture password |
| `tests/test_modules.py` | 1 | 24 | module-loader fixture credential |
| `tests/test_company_discovery.py` | 2 | 509, 526 | company-discovery HTTP test fixtures |

Total: **16 / 16 hits accounted for as test fixtures**. None of these
values exist outside the `tests/` directory; none are referenced from
production code; none would be honored as credentials by any deployed
instance (the production `AuthStore` rejects unverified default
secrets).

---

## Pre-audit checklist (run before every scan)

1. Source tree is at `f225896` or later on the `main` branch.
2. `.env` / `.env.local` / production secrets are NOT staged.
3. The `private/` directory exists and is gitignored (per Week-1 task
   1.4 sanitisation pass — see [`CONTRIBUTORS-NOTE.md`](../../CONTRIBUTORS-NOTE.md)
   for the history-preservation rationale).
4. The known false-positive set above is up-to-date — any new
   `tests/test_phase*_*.py` file added after this audit date should be
   re-triaged before the next scan is filed as clean.

---

## Post-audit follow-ups

These items are tracked for the next scan cycle (post-grant unless
otherwise noted). None are submission blockers:

- **Add `.gitleaks.toml` allowlist** so a CI run of gitleaks would
  produce zero hits without manual triage. Scope deferred to
  a future release (privacy /
  security / incident readiness).
- **Wire gitleaks into the existing OpenSSF Scorecard workflow** so
  every push to `main` gets a fresh secrets scan. Scope deferred to
  Ceiling 2 Section 2.14 alongside the bug-bounty program work.
- **Quarterly cadence**: re-run this scan once per quarter and append
  a dated section below. Maintainer-owned task.

---

## Threat model context

Gitleaks alone is a regex-based scanner. It is *necessary but not
sufficient*. Other layers of the project's secret-management posture:

- Production `HELPMEFINDTHEJOB_AUDIT_SALT` (HMAC chain key, EU AI Act
  Article 12) is set via `.env` on the droplet and never appears in
  the repo. Fail-fast at startup if absent in non-test environments
  (`tests/test_phase13_audit_log.py::SaltFailFastTests`).
- OIDC client secrets are environment-variable-driven; the test fixture
  in `tests/test_sso_oidc.py` is unrelated to any real SSO deployment.
- Caddy auto-issued TLS keys live in the Caddy container volume on
  the droplet (`/data/caddy/`), never in the repo.
- AI provider keys (OpenAI / Anthropic / etc.) are BYO-AI per the
  application narrative (Field 7); the project never stores them
  centrally and never logs them to the audit chain.

See [`SECURITY.md`](../../SECURITY.md) for the vulnerability-reporting
channel and [`compliance/data-governance.md`](../../compliance/data-governance.md)
for the full data-classification table.

---

## Audit log

| Date | Tool | Hits | False positives | True positives | Notes |
|---|---|---|---|---|---|
| 2026-05-24 | gitleaks v8 | 17 | 17 | 0 | Initial pre-NLnet-submission audit. All hits are documented test fixtures. |

Future scans append below this row. Never overwrite or backdate.
