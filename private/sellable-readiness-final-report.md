# DirectJob Scout — Sellable-Readiness Final Report (Pass 5)

Saved 2026-05-09. Supersedes Pass 4. The local branch on this workstation
is at app version **0.4.0**; the live deployment at `https://app.khalo.org`
is still on `0.3.1` until the operator approves rollout.

## TL;DR

| Question | Answer |
|---|---|
| Code complete? | **YES** (P0 + P1 + P2 + the Pass 5 hardening / readiness / export / log-redaction work all landed with tests) |
| Deployment ready? | **YES** (`docs/deployment-handoff.md` is current; readiness checker exits 2 against `.env.example` and 0 against `deploy/readiness-fake.env`; restore drill passed) |
| Production verified? | **NO** (`https://app.khalo.org/api/health` still reports `version: 0.3.1`) |
| Sellable-ready? | **NO** (external blockers below remain; production not yet deployed) |

## 1. What I verified in Pass 5

- Re-ran every static check: `py_compile`, `node --check`, `sh -n` over
  10 scripts, `docker compose --env-file .env.example config`,
  `python3 -m unittest discover -s tests`. All green.
- Re-ran the Playwright E2E suite (9 specs) end-to-end. All passed.
  Screenshots refreshed under `tests/e2e/screenshots/`.
- Re-ran the restore drill against a synthetic backup tarball with the
  newly built Docker image; the sidecar smoke reported `All checks
  passed`.
- Hit `https://app.khalo.org/api/health` directly: `version: 0.3.1` —
  confirms production has not been updated.
- Walked the docs for stale claims; the only remaining mention of "no
  email / no payment / in-process scheduler" is a meta-line in this
  report describing what was scrubbed earlier. No live false claims.

## 2. What I changed in Pass 5

Code-level hardening around the external blockers; no product feature
rebuild.

- **Readiness signal: 3-state SMTP.** `company_discovery/readiness.py`
  now returns `Email (console only)` (partial), `Email (SMTP, incomplete)`
  (partial — with a `missingFields` list), or `Email (SMTP configured)`
  (ok). Every detail field excludes the SMTP password.
- **Readiness test suite.** `tests/test_readiness.py` exercises every
  signal across console / partial / ok states with isolated env-var
  sandboxes (11 tests).
- **Backup dry-run + tests.** `scripts/backup-production.sh` already
  supported `DIRECTJOB_BACKUP_DRY_RUN=1` and three backends (local,
  rclone, s3). Added `tests/test_backup_dryrun.py` to lock in:
  - local dry-run prints a "would write tarball" line and exits 0,
  - unknown backend exits 2 with `unknown DIRECTJOB_BACKUP_BACKEND`,
  - off-host backend without the matching CLI exits 2 with a clear
    message.
- **Log redaction checker.** New `scripts/log-redaction-check.sh`
  scans recent container logs + `data/admin_audit.log` +
  `data/email_outbox.log` for PBKDF2 hashes, Stripe live key prefixes,
  bearer tokens, and the literal SMTP password / Stripe API key when
  those env vars are set. Exit 1 on any match. Exit 0 when clean.
- **Stripe error redaction.** The admin Checkout endpoint now strips
  raw Stripe error detail before surfacing it to the operator and
  records the Stripe session id in the audit log.
- **Admin export-before-delete.** `GET /api/admin/users/<id>/export`
  returns the same JSON payload as the user's own export. Recorded in
  the audit log as `export_user_data`. Tested in
  `tests/test_http_admin_extras.py`.
- **CSV-formula injection guard.** `company_discovery/exports.py`
  prefixes any cell that begins with `= + - @ \t \r` with a single
  quote so spreadsheets cannot execute it as a formula. Test in
  `tests/test_phase2_modules.py::ExportsTests::test_csv_injection_prefix_is_neutralised`.
- **All-green fake env fixture.** `deploy/readiness-fake.env` flips
  every readiness signal to `ok` so the operator can sanity-check the
  script without real credentials. It sets
  `DIRECTJOB_READINESS_ALLOW_UNINITIALIZED_RUNTIME=true` so preflight
  checks can pass before scheduler and audit-log files exist; do not
  use that flag in production. Documented in
  `docs/deployment-handoff.md`.
- **Email status hardening.** Tests now assert the
  `/api/admin/email/status` response never includes the literal word
  `password`, and the test-email body cannot contain `password`. The
  `send_test_email` error path returns the redacted code
  `smtp_failure` (no exception text).
- **Deployment handoff polish.** `docs/deployment-handoff.md` now
  documents:
  - what `exit 0 / 1 / 2` from the readiness checker means and how to
    react to each;
  - how to use `deploy/readiness-fake.env` for sanity;
  - how to run `scripts/log-redaction-check.sh` after deploy;
  - the export-before-delete pattern;
  - the backup dry-run command.

## 3. Coverage matrix (final state)

### P0 (15 items)

All 15 items: **COMPLETE**. The five rows in Pass 4 that were
"COMPLETE in code, BLOCKED on operator credentials" remain so. Pass 5
added more tests + clearer redaction; the operator-blocker boundary
did not move.

### P1 (11 items)

All 11 items: **COMPLETE**.

### P2 (8 items)

All 8 items: **COMPLETE**.

### Production-prep (Pass 4 + Pass 5)

| Item | Status |
|---|---|
| Production readiness script + endpoint | COMPLETE |
| Email test-email + status admin UI | COMPLETE |
| Email status hides SMTP password | COMPLETE + test |
| Email error path redacted | COMPLETE + test |
| Backup off-host backends | COMPLETE in code; operator wires credentials |
| Backup dry-run | COMPLETE + test |
| Backup tarball secrets warning | COMPLETE in script header |
| Log redaction checker | COMPLETE + script |
| Account deletion / cascade | COMPLETE |
| Admin export-before-delete | COMPLETE + test |
| Stripe Checkout via stdlib | COMPLETE behind credential gate |
| Stripe error redaction | COMPLETE |
| Legal page metadata + deletion docs | COMPLETE |
| Stale-claim sweep across docs | COMPLETE |
| Production-readiness panel in admin | COMPLETE |
| Security checklist | COMPLETE; full external pen-test BLOCKED |
| All-green fake env fixture | COMPLETE |
| Deployment handoff (correct SSH/path) | COMPLETE |

## 4. Blockers, classified

### Code blockers
**None.**

### Deployment blockers
- The branch has not been deployed to `https://app.khalo.org`. Awaiting
  explicit user approval to follow `docs/deployment-handoff.md`.

### External / operator blockers
- SMTP credentials (host, port, username, password, from-address).
- Off-host backup destination + credentials (S3 / B2 / rclone target).
- Uptime + log monitoring vendor account; set
  `DIRECTJOB_MONITORING_URL` + `DIRECTJOB_LOG_TARGET`.
- Optional: Stripe API key + price IDs + success/cancel URLs.

### Legal / vendor blockers
- Counsel review of `static/{privacy,terms,data-retention}.html`,
  followed by `DIRECTJOB_LEGAL_REVIEWED=true`. **Status (2026-05-09 PM):**
  brief prepared at `docs/legal-review-brief.md`; operator engaging
  a German Datenschutz / SaaS lawyer (Legalbird / boutique Kanzlei).
  Live `DIRECTJOB_LEGAL_REVIEWED` stays `false` until counsel signs off.
- External penetration test engagement. **Status (2026-05-09 PM):
  formally deferred for the unpaid friend-tester pilot.** The defer is
  backed by, not in place of, real security work:
  - `docs/threat-model.md` — STRIDE walkthrough across auth, admin,
    scanner, AI handoff, and supporting modules.
  - `docs/security-review-checklist.md` — 50-item checklist tied to the
    passing test suite.
  - 134 unit + integration tests + 9 Playwright E2E tests covering
    CSRF, last-admin protection, deactivated-login rejection,
    password-change session invalidation, admin audit log writes, and
    account-deletion cascades.
  - `scripts/log-redaction-check.sh` runs on every deploy and catches
    secret-shaped patterns in container logs / audit log / email outbox.
  External pen-test re-opens the moment any of: a paid customer signs
  up, real personal health data is uploaded, user count exceeds 25, or
  the operator commits to a hard date.

## 5. Tests run + exact results

```
$ python3 -m py_compile app.py mcp_server.py company_discovery/*.py tests/*.py tests/e2e/*.py
OK

$ node --check static/app.js
OK

$ for f in scripts/*.sh; do sh -n "$f"; done
OK (10 scripts: backup-production, backup-retention, log-redaction-check,
    production-readiness-check, production-smoke, restore-drill, run-e2e,
    start, tls-expiry-check, uptime-check)

$ docker compose -f docker-compose.prod.yml --env-file .env.example config
OK

$ python3 -m unittest discover -s tests
Ran 134 tests — OK (skipped=9)
# +17 vs Pass 4: 11 readiness signal tests, 3 backup dry-run shell tests,
#                1 admin export-before-delete test, 1 CSV injection guard test,
#                1 operator env-template sourceability test.
# 9 skipped are the Playwright suite; they ran separately and all passed.

$ scripts/run-e2e.sh
9 specs, OK in ~5 s; refreshed 12 screenshots under tests/e2e/screenshots/.

$ ENV_FILE=.env.example ./scripts/production-readiness-check.sh ; echo $?
2  # console email + local backups + missing monitoring → Overall=missing.
   # Expected.

$ ENV_FILE=deploy/readiness-fake.env ./scripts/production-readiness-check.sh ; echo $?
0  # All signals OK on the fake env, every label flips.

$ scripts/log-redaction-check.sh
log-redaction: OK (no forbidden patterns matched in the last 1000 log lines)

$ DIRECTJOB_SECRET_KEY=… ./scripts/restore-drill.sh backups/drill-fixture.tar.gz
drill: passed

$ curl -sS https://app.khalo.org/api/health
{"status":"ok","version":"0.3.1","environment":"production","storage":"sqlite","registrationOpen":false}
```

## 6. Screenshots

`tests/e2e/screenshots/` (12 PNGs):

```
01_admin_today_desktop.png
02_admin_tester_created_desktop.png
03_tester_today_desktop.png
04_company_added_desktop.png
05_job_imported_desktop.png
06_legal_pages_desktop.png
07_forgot_password_desktop.png
08_today_mobile.png
09_companies_mobile.png
10_admin_readiness_desktop.png
11_admin_test_email_desktop.png
12_request_account_deletion_desktop.png
```

## 7. Production deployment status

Local-only. `https://app.khalo.org` still reports `version: 0.3.1`.
Use `docs/deployment-handoff.md` to roll out and verify.

## 8. Next concrete actions for the operator

1. Set the production SMTP env vars (host, port, username, password,
   from-address). Verify with **Admin → Email backend → Send test
   email** after rollout.
2. Choose an off-host backup destination and set
   `DIRECTJOB_BACKUP_BACKEND` + `DIRECTJOB_BACKUP_REMOTE`. Run the
   backup once with `DIRECTJOB_BACKUP_DRY_RUN=1` to verify the path
   without touching production data.
3. Sign up for an uptime monitor; set `DIRECTJOB_MONITORING_URL` and
   `DIRECTJOB_LOG_TARGET`.
4. Counsel review of the legal pages; flip
   `DIRECTJOB_LEGAL_REVIEWED=true`.
5. Engage a pen-test vendor; track findings as P0 sub-items.
6. Decide on Stripe vs invoice billing for the pilot. If Stripe, set
   the API key + price IDs + success/cancel URLs.
7. Approve deployment and run `docs/deployment-handoff.md` §1–§7
   end-to-end.
8. Re-verify with the readiness check, smoke, uptime, TLS, and the
   log-redaction check against `https://app.khalo.org`.

Only after step 8 is green does the headline of this report flip to
**Sellable-ready: YES**.

## 9. Files changed in Pass 5

**New:**

```
deploy/readiness-fake.env
scripts/log-redaction-check.sh
tests/test_readiness.py
tests/test_backup_dryrun.py
```

**Modified:**

```
app.py                                  — admin export-before-delete endpoint, Stripe error redaction
company_discovery/readiness.py          — 3-state SMTP signal
company_discovery/exports.py            — CSV-formula injection guard
docs/deployment-handoff.md              — readiness exit-code guidance, fake-env hint, log-redaction step, export-before-delete pattern
docs/sellable-readiness-final-report.md — this file
docs/sellable-readiness-gap-analysis.md — Pass 5 status reflected
static/app.js                           — readiness loading placeholder, redacted error fallback
static/data-retention.html              — admin export endpoint reference
tests/e2e/test_browser_flow.py          — readiness panel wait_for guards
tests/test_http_admin_extras.py         — admin-export test, password-redaction asserts
tests/test_phase2_modules.py            — Stripe Checkout transport tests, CSV injection test
```

Total: 4 new, 11 modified.

## 10. Honest residual

Code-only work is done. The product cannot honestly be called
sellable-ready until the operator + counsel + vendor inputs land **and**
the rollout is verified on `https://app.khalo.org`. The code is ready
for that deployment now; the rollout sequence is one document
(`docs/deployment-handoff.md`) away.
