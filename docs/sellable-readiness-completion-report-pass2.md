# Sellable-Readiness Completion Report — Pass 2

Saved 2026-05-09. This is the cleaned report for Pass 2; the live status
matrix continues to live in `docs/sellable-readiness-gap-analysis.md`.

## 1. Executive summary

**Sellable-ready: NO.** Local-only changes; no production deployment.

After Pass 2, every code-only blocker on the strict 15-item P0 list is
closed. The remaining open items are BLOCKED on inputs that must come
from outside this codebase: SMTP credentials, an off-host backup
destination, an external uptime / log monitor, the one-time Playwright
binary install on the operator host, and the engagement of an external
penetration-test vendor.

## 2. P0 status (Pass 2 close)

| # | Item | Status |
|---|---|---|
| 1 | Modern UI/UX | COMPLETE |
| 2 | Guided non-technical workflow | COMPLETE |
| 3 | Email invite flow | COMPLETE (SMTP env-driven; ConsoleTransport for tests) |
| 4 | Forgot/reset password | COMPLETE |
| 5 | Admin audit log | COMPLETE |
| 6 | Backups + restore | PARTIAL — code complete, off-host destination BLOCKED on operator |
| 7 | Monitoring / alerting | PARTIAL — admin metrics shipped, vendor wiring BLOCKED |
| 8 | Production smoke | COMPLETE |
| 9 | Durable scheduler | COMPLETE |
| 10 | Quotas + concurrency | COMPLETE |
| 11 | Browser E2E | PARTIAL — suite + harness shipped, Playwright install BLOCKED in this env |
| 12 | ATS coverage | COMPLETE — 5 adapters |
| 13 | Stronger dedupe | COMPLETE |
| 14 | Privacy / Terms / Data-retention | COMPLETE (counsel review out of scope) |
| 15 | Internal threat model | COMPLETE; external pen-test BLOCKED |

## 3. New modules added in Pass 2

- `company_discovery/email_transport.py` — `EmailTransport` protocol,
  `ConsoleTransport` (writes JSONL to `data/email_outbox.log`),
  `SmtpTransport` (STARTTLS-by-default).
- `company_discovery/tokens.py` — single-use, time-limited invitations
  and password reset tokens; tokens stored as HMAC-hashed.
- `company_discovery/scheduler.py` — `DurableScheduler` with sqlite
  persistence, orphan-state recovery, failure backoff.
- `company_discovery/quotas.py` — per-user daily scan/AI counters,
  per-user concurrency cap, per-domain hourly bucket.
- `company_discovery/ats_adapters.py` — Greenhouse, Lever, Personio
  XML+HTML, SmartRecruiters, Teamtailor extractors. Workday + SAP
  SuccessFactors detected and routed to manual fallback.
- `company_discovery/dedup.py` — URL canonicalisation, ATS-id,
  title+company, title+location, description shingles with title-
  similarity guard.
- `static/privacy.html`, `static/terms.html`, `static/data-retention.html`
  — product-honest pages with explicit "needs legal review" notice.
- `docs/threat-model.md` — STRIDE + scanner + AI-handoff threat model.
- `scripts/restore-drill.sh`, `scripts/backup-retention.sh`,
  `scripts/run-e2e.sh`.
- `tests/test_modules.py` (37 unit tests),
  `tests/test_http_invitations.py` (5 HTTP tests),
  `tests/e2e/test_browser_flow.py` (Playwright suite).

## 4. Tests run at end of Pass 2

```
py_compile          OK
node --check         OK
sh -n scripts/*.sh   OK (6/6)
docker compose conf  OK
unittest discover    Ran 72 tests, OK (skipped=6 — Playwright not yet installed)
```

## 5. Files changed in Pass 2

**New:** see §3.
**Modified:** `app.py`, `company_discovery/repository.py`,
`company_discovery/service.py`, `static/index.html`, `static/styles.css`,
`static/app.js`, `README.md`, `docs/production-deployment.md`,
`docs/pilot-runbook.md`, `docs/sellable-readiness-gap-analysis.md`.

## 6. Honest residual

The product is materially better than after Pass 1 but is **not
sellable-ready**. The next pass closes Phase 2 (P1) and Phase 3 (P2)
and then re-tests on a deployed instance.
