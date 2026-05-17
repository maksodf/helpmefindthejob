# DirectJob Scout Sellable-Readiness Gap Analysis

Status as of 2026-05-09 Pass 5: the local branch is code-complete
against the agreed P0/P1/P2 checklist *and* the production-prep
checklist (readiness panel + script, off-host backups with dry-run,
admin export-before-delete, log-redaction checker, real Stripe
Checkout via stdlib with redacted errors, legal-version metadata,
deployment handoff doc, all-green fake env fixture, expanded E2E +
unit tests). 134 tests pass; restore drill passes against a synthetic
fixture; readiness exits 2 on `.env.example` and 0 on
`deploy/readiness-fake.env`. Live `https://app.khalo.org/api/health`
still reports version `0.3.1`, so production verification is still
pending operator approval. See `docs/deployment-handoff.md` for the
rollout sequence and `docs/sellable-readiness-final-report.md` for
the Pass 5 summary.

This document is the honest tracker for what stands between the current local
branch and a product we can ship to paying customers. The old 2026-05-08
open-item inventory has been superseded by the Pass 3 matrix below and by
`docs/sellable-readiness-final-report.md`.

## Round-2 — 2026-05-09 PM (deployed as 0.6.0)

Live at `https://app.khalo.org`, version `0.6.0`. 161/161 tests green
(125 baseline + 22 round-1 + 14 round-2). Pre-deploy DB snapshots taken
inside the container (`/app/data/*.pre-0.6.0.bak`); previous image
retained as `directjob-scout-directjob-scout:previous-0.5.0`.

- **A4 — regional employer templates.** Five new watchlist templates:
  `paris_tech_fr`, `amsterdam_tech_nl`, `milan_tech_it`,
  `london_finance_uk`, `zurich_tech_ch`. Each carries persona
  membership so the UI surfaces them per persona.
- **B2 — real-time saved-search alerts.** New
  `company_discovery/saved_search_alerts.py` matcher (role tokens +
  location + sector). `SavedSearch.last_seen_at` field tracks when
  the user last reviewed matches. Bootstrap enriches each saved
  search with `{matchCount, unseenCount, latestMatchAt}`. New
  endpoints `POST /api/saved-searches/<id>/matches` and
  `POST /api/saved-searches/<id>/mark-seen`. UI: unseen-count badge
  + "Show N new" button on each saved search; clicking it marks seen.
- **B5 — application tracker depth.** New `INTERVIEW_STAGES`
  enum (`screening / phone / take_home / technical / onsite / panel /
  offer`). `ImportedJob` now carries `interview_stage`,
  `reminder_at`, `application_history`. Status, stage, and history
  notes auto-append to a per-job timeline (capped at 50 entries). UI:
  new dropdown + reminder field + history-note input + timeline panel
  under the application form.
- **B1 (full, slim PDF) — DOCX/TXT CV upload.** New
  `company_discovery/cv_extract.py` (stdlib `zipfile` + `xml.etree`,
  no new deps). Endpoint `POST /api/profile/cv-upload` accepts
  base64-encoded `.docx` or `.txt` (5 MiB cap), extracts the visible
  text, and writes it to `UserProfile.cv_text`. UI: file-picker
  button next to the CV textarea. PDF support intentionally deferred
  — pure-stdlib PDF parsing is fragile; round 3 adds an explicit dep.

Deferred to round 3 (in priority order):

- **A2 i18n** — UI strings extracted; German + English first.
- **B1 PDF** — pick `pdfminer.six` or `pypdf`, add to requirements.
- **B4 search-provider integration** — needs API-key choice.
- **A5 multi-tenant workspaces** — bigger architectural change.
- **B6 PWA + push** — service worker + iOS/Android web push.
- **A4 expansion** — Madrid, Barcelona, Stockholm, Copenhagen,
  Warsaw templates.

## Round-1 globalisation + depth — 2026-05-09 PM (built locally, not yet deployed)

Bumped `APP_VERSION` to `0.5.0`. All four round-1 features land at the
local-branch level with passing tests (147/147 — 125 prior + 22 new in
`tests/test_round1.py`). Deploy is **paused** until the friend-tester
session on `0.4.0` is finished so we don't reset their cookie / state
mid-flow.

- **A1 — persona expansion.** New `company_discovery/personas.py`
  registry with five personas: `healthcare-management` (default), `tech`,
  `marketing`, `finance`, `product-management`. Each persona owns its
  sector weights, default target roles, default industry, industry-match
  terms, role→sector boosts, and category-suggestion list. The three
  formerly healthcare-only modules — `persona_ranking`,
  `curated_companies`, `watchlist_templates` — now consult the registry.
  `CURATED_COMPANIES` and `_TEMPLATES` carry a `personas: tuple[str, ...]`
  field; new tech / marketing / finance / product-management entries
  added to both. Existing healthcare data is unchanged.
- **A3 — international career-page terms.** `CAREER_LINK_TERMS` extended
  with French, Dutch, Spanish, Italian, Polish, and Portuguese tokens
  (`carrières`, `vacatures`, `empleos`, `lavoro`, `kariera`,
  `carreiras`, etc.). `_career_link_score` and `_looks_like_job_link`
  updated to recognise the same tokens in href + path. `JOB_TITLE_TERMS`
  expanded so the heuristic-anchor pass picks up tech / marketing /
  finance role names too.
- **B1 (slim) — user profile + AI Brief personalization.** New
  `UserProfile` model (per-user, `cv_text`, `target_roles`, `industry`,
  `location`, `seniority`, `years_experience`, `languages`, `notes`,
  `persona_id`). Persisted via in-memory + sqlite repo. Endpoints:
  `GET /api/personas`, `GET/POST /api/profile`. `Settings → Persona &
  profile` panel in the UI. `analysis.build_job_decision_brief_prompt`
  now inlines persona + CV; `prepare-brief` and `analyze` look up the
  profile automatically. `suggest-companies` and `discover-companies`
  use the profile's persona by default.
- **B3 — cover-letter brief.** New `analysis.build_cover_letter_brief_prompt`
  + `execute_cover_letter_brief`. Endpoints
  `POST /api/imported-jobs/<id>/prepare-cover-letter` (handoff prompt)
  and `POST /api/imported-jobs/<id>/draft-cover-letter` (executes
  through the configured AI provider; populates
  `imported_job.cover_letter_draft`). UI: two new buttons next to the
  cover-letter textarea on the application form.

Remaining round-1 items deliberately deferred:

- A2 (German + English i18n) — content-heavy; planned for round 2.
- A4 (more regional employer templates beyond the four added now).
- A5 (multi-tenant) — bigger architectural change.
- B1 (full) — PDF/DOCX upload + auto-fit scoring on every discovered
  job. Today's ship is "paste your CV" + manual prepare-brief.
- B2 (real-time saved-search alerts), B4 (search providers), B5
  (tracker depth), B6 (PWA + push) — not in this round.

## Pass 5.5 status — 2026-05-09 PM

Live deployment at `https://app.khalo.org` is on `0.4.0` and verified.
Operator-side env upgrades since the rollout:

- **Public URL** wired (`DIRECTJOB_PUBLIC_URL=https://app.khalo.org`).
- **Email**: SMTP via Resend on port 2587 (DigitalOcean blocks 25/465/587 outbound; Resend supports 2587 STARTTLS as a fallback). Domain `khalo.org` DKIM/SPF verified at united-domains. Test-email and invite-accept round-trip both succeeded.
- **Backups**: Backblaze B2 bucket `khalo-directjob-backups` (region `eu-central-003`) wired via `rclone`. First off-host tarball verified.
- **Monitoring + log shipping**: Better Stack Uptime + Telemetry. Uptime monitor on `https://app.khalo.org/api/health` (3-min interval); Telemetry collector running as `better-stack-collector` + `better-stack-ebpf` containers, source `directjob-scout-prod`, status Active.
- **Legal review**: brief prepared at `docs/legal-review-brief.md`; counsel review engaged. `DIRECTJOB_LEGAL_REVIEWED` stays `false` until sign-off.
- **External penetration test**: formally deferred for the unpaid friend-tester pilot, backed by `docs/threat-model.md`, `docs/security-review-checklist.md`, and the 134-test suite. Re-opens on first paid customer / real personal health data / >25 users / operator-committed hard date.

Readiness check on the live `.env` exits **PARTIAL** — every input is set; remaining `[partial]` rows are intentional pilot decisions (manual billing, pending counsel review, cosmetic scheduler/audit signals that exist inside the container but are invisible to the host readiness script).

## Current State

Local branch status:

- Modern app UI, guided workflow, account lifecycle, admin audit log, safe
  scanner, durable scheduler, quotas, legal pages, monitoring scripts, backup
  scripts, restore drill, browser E2E, ATS adapters, stronger dedupe, structured
  fit scoring, job tracker, application preparation, templates, digests, exports,
  saved searches, analytics, billing abstraction, and support flow are complete
  in code.
- The production site at `https://app.khalo.org` is still the older deployment
  until this branch is explicitly rolled out and smoke-tested.
- Remaining blockers are external-only: SMTP credentials, off-host backup
  target, uptime/log monitor vendor, Stripe decision/credentials, counsel
  review, external pen-test, and deployment approval.

## Original Feature Promise Mapping

Implemented in the current local branch:

- Manual company add.
- Company watchlist.
- Career-page URL storage.
- Safe known-page scan.
- robots.txt checks.
- structured-data extraction for JobPosting.
- HTML fallback extraction for simple pages.
- discovered jobs queue.
- import discovered job.
- provider-neutral AI handoff/run path.
- session-only API key support.
- hosted deployment.
- admin-created tester accounts.

Partially implemented or deliberately bounded:

- Company discovery: provider abstraction, curated provider, and public
  Greenhouse/Lever feed providers are implemented; broader web-scale search is
  intentionally not built to avoid unsafe crawling.
- ATS compatibility: Greenhouse, Lever, Personio, SmartRecruiters, and
  Teamtailor are supported; Workday and SAP SuccessFactors route to manual
  fallback because reliable public extraction is too brittle for the pilot.
- Billing: manual billing backend is production-usable for a pilot; Stripe
  backend is a credential-gated placeholder until the operator chooses Stripe
  products/prices.

Not implemented because it requires external decisions or would be unsafe for
the current product boundary:

- Broad unrestricted crawling.
- Restricted-platform scraping.
- Workday/SAP SuccessFactors scraping beyond safe manual fallback.
- Production SMTP, off-host backups, monitoring vendor wiring, Stripe live
  billing, legal approval, and external pen-test.

## Release Gate For "Sellable Pilot"

Do not call the product sellable until all P0/P1/P2 code items are deployed,
production smoke passes, and the external blockers above are closed or formally
accepted for the paid pilot.

Minimum acceptance checklist:

- A non-technical tester can receive an invite, log in, create a watchlist, scan at least one supported fixture/company, import a job, and produce an AI handoff without help.
- Admin can create, deactivate, and reset tester accounts without SSH.
- There is a tested backup and restore path.
- There is uptime monitoring and a deploy smoke script.
- UI is modern, responsive, and clearly communicates next steps.
- Real-world limitations are visible to the user and do not look like crashes.
- No raw secrets are persisted through UI workflows.
- No unsafe crawling or restricted-platform scraping is possible through default flows.

## P0 Coverage Against Strict Sellable-Ready Definition

This section tracks the *strict* P0 list — the one we use to decide whether the
product can be sold. An item is COMPLETE only when code, tests, and docs all
land, with concrete evidence.

| # | P0 item | Status (2026-05-09 Pass 3) |
|---|---|---|
| 1 | Modern UI/UX redesign | COMPLETE |
| 2 | Guided non-technical workflow | COMPLETE — onboarding checklist on Today + next-step suggestion + nav |
| 3 | Email invite flow | COMPLETE — admin invite → console outbox in dev / SMTP in prod; tests prove single-use + expiry |
| 4 | Forgot / reset password flow | COMPLETE — public endpoint + rate-limited; tests prove single-use + replay-rejected |
| 5 | Admin audit log | COMPLETE |
| 6 | Automated backups + tested restore | COMPLETE in this pass — `scripts/restore-drill.sh` was actually run end-to-end against a snapshot tarball and the smoke script passed; cron stanzas + retention shipped. Off-host destination still operator-supplied (BLOCKED on operator credentials). |
| 7 | Monitoring / alerting | COMPLETE in code — `/api/admin/metrics`, `scripts/uptime-check.sh`, `scripts/tls-expiry-check.sh`, recommended cron entries. External vendor wiring (UptimeRobot / Better Stack / log shipper) BLOCKED on operator decision. |
| 8 | Production deploy smoke script | COMPLETE |
| 9 | Durable background worker for scheduled scans | COMPLETE |
| 10 | Better scan rate limits, queue limits, concurrency | COMPLETE |
| 11 | Real browser E2E tests | COMPLETE in this pass — Playwright suite was actually run end-to-end (`6 tests in 3.0s, OK`) and 9 desktop+mobile screenshots captured under `tests/e2e/screenshots/` |
| 12 | More robust ATS / career-page extraction | COMPLETE |
| 13 | Stronger deduplication | COMPLETE |
| 14 | Privacy / Terms / Data-retention pages | COMPLETE in code — counsel review still required before commercial sale |
| 15 | Security review of auth / admin / scanning flows | COMPLETE internally — `docs/threat-model.md` + `docs/security-review-checklist.md`. External penetration test **BLOCKED** until vendor engaged |

15 / 15 strict P0 items: **code complete**.
External-only blockers remain: SMTP credentials, off-host backup destination,
monitoring/logging vendor wiring, Stripe production credentials or manual-billing
decision, counsel review of legal pages, external pen-test vendor, and
production deployment approval.

The product is **not sellable-ready** until those external decisions land *and* a production deployment is verified. The code is, however, ready for that deployment now.

## Changes Closed Across Readiness Passes

These specific items moved from open to closed in this pass and have evidence
attached:

- Modern app-shell UI with sidebar navigation and Today / Companies / Discovered Jobs / AI Brief / Settings / Admin views (`static/index.html`, `static/styles.css`, `static/app.js`). Smoke test asserts it serves.
- Empty-state and next-step guidance on every view.
- Human-readable mapping of scan and admin error codes (`SCAN_STATUS_COPY`, `ERROR_COPY` in `static/app.js`).
- Responsive layout collapses sidebar to top tabs at <768px; metric grid stacks 2-up then 1-up; lists become single-column.
- Accessibility primitives: `nav` landmark, `aria-labelledby` on views, `role="status"` on status pills, focus-visible ring, all interactive controls keyboard reachable, skip-link.
- `scripts/production-smoke.sh` (anonymous + optional admin probe) and `scripts/backup-production.sh` (SQLite `.backup` snapshots + `docker cp` + tarball).
- `tests/test_http_auth.py`: 8 HTTP-level admin/auth tests, all passing:
  - member rejected from admin APIs
  - admin self-modify rejected
  - deactivated user cannot log in
  - last admin cannot be demoted/deactivated
  - password change invalidates session
  - admin password reset signs target out
  - CSRF required for mutations
  - admin audit log records actions
- Admin audit log (`data/admin_audit.log`, JSON Lines) for `create_user`, `update_role`, `update_active`, `reset_password`.
- Frontend logout clears all cached per-user state in memory.
- Confirmation prompts before destructive admin actions (deactivate, role change, password reset, company delete).
- README, production deployment, and pilot runbook updated for the new UX language and operational scripts (smoke, restore, rollback, recommended cron).

## Items Still Open

### External-only blockers

- **Off-host backup destination wiring** — code path lives in `scripts/backup-production.sh`; an operator must point it at S3 / rclone / equivalent and rotate credentials. BLOCKED on operator decision.
- **Uptime + TLS monitoring** — recommended providers and the `/api/admin/metrics` endpoint shipped; needs an account at e.g. UptimeRobot or Better Stack. BLOCKED on vendor account.
- **SMTP credentials** — invite, reset, and digest emails are implemented; production delivery requires `DIRECTJOB_SMTP_*`, `DIRECTJOB_EMAIL_FROM`, and `DIRECTJOB_PUBLIC_URL`.
- **Stripe or manual-billing decision** — manual billing is the default. Stripe requires live keys and price IDs before use.
- **Counsel review** — privacy, terms, and data-retention pages are implemented but must be reviewed before commercial use.
- **External penetration test** — internal threat model published in `docs/threat-model.md`. BLOCKED on vendor engagement.
- **Production deployment** — this branch must be rolled out to `app.khalo.org`, then production smoke, uptime, TLS, and a real login flow must pass.

### P1 — closed in Pass 3

- Real search-provider company discovery — `discovery_providers.py` with mock + curated + Greenhouse/Lever feed providers. Tests in `test_phase2_modules.py`.
- Better company relevance ranking with explanations — `persona_ranking.py` with explainable score breakdown.
- Public ATS feed integrations — Greenhouse + Lever feed providers added.
- Structured fit scoring persistence — `ImportedJob` gains `structured_analysis`, `fit_score`, `recommendation`.
- Job status tracker — `application_status` enum + UI in AI Brief.
- Application preparation workflow — notes, cover-letter draft, documents checklist, next action.
- Per-user scan/AI quotas — covered in P0.10.
- Admin metrics view — surfaced in Admin → Workspace metrics card.
- Last-login / last-active — DB columns + populated on login + session use.
- Backup/restore round-trip — `test_export_imports_round_trip` plus a real `restore-drill.sh` run.
- More ATS fixture coverage — fallback paths exercised across all five adapters.

### P2 — closed in Pass 3

- Onboarding checklist — pure-function `onboarding.py` rendered on Today.
- Watchlist templates — three curated templates with bulk-apply endpoint and tests.
- Email digests — `digests.py` + `/api/digest/preview` + `/api/digest/send`.
- CSV + Markdown exports — `/api/exports/{imported,discovered}.{csv,md}` with download buttons.
- Saved searches — full CRUD + UI + tests.
- Privacy-respecting analytics — opt-in toggle + `/api/analytics/event` with admin view.
- Billing / subscription — `billing.py` abstraction with `ManualBillingBackend` (default) and `StripeBillingBackend` (placeholder; raises until credentials).
- Support / contact flow — `/api/support` ticket submission + admin list.

### Still strictly external-only

- Counsel review of `static/privacy.html`, `static/terms.html`, `static/data-retention.html` before commercial sale.
- External penetration test — BLOCKED on vendor engagement.
- SMTP credentials for production invite + reset emails — BLOCKED on operator.
- Off-host encrypted backup destination credentials — BLOCKED on operator.
- Uptime + TLS + log monitoring vendor wiring — BLOCKED on operator.
- Stripe API key + price IDs for production billing — BLOCKED on operator decision.
- **Production deployment of this branch** — local-only this pass; user approval required before deploy.
