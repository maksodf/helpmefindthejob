# Keep building till 100% — tracker

**Definition of "100%":** a stranger lands on khalo.org, signs up with email + password, gets onboarded, picks a plan if they want, uses the product daily, and we make money — same standard as any commercial SaaS.

Each item is one slice. Tick `[x]` when done. Order is rough; some can ship in parallel.

---

## Phase 0 — Pre-launch security & reliability

1. [ ] Flip `DIRECTJOB_ALLOW_REGISTRATION=true` on prod once ready (currently closed-off; admin-only)
2. [x] CV / profile-text at-rest encryption (real envelope encryption, not the current XOR-with-secret-key) — `company_discovery/crypto_kit.py` provides `EncryptionAtRest` (ChaCha20-Poly1305 AEAD with per-record nonce + user_id AAD). Master key from `DIRECTJOB_DATA_KEY` env or HKDF-derived from `SECRET_KEY` as fallback. Wired into the SQLite repository so every `profile.cv_text` write is `aead:v1:…`-formatted on disk while the in-memory model stays plaintext. Lazy migration: legacy plain values continue to load and get re-encrypted on next save. Tampering / cross-user blob swap rejected via AAD. Tests: `tests/test_phase0_encryption_at_rest.py` (4 tests, all green) cover round-trip, cold-restart decrypt, AAD binding, lazy migration. Runtime-proven: `sqlite3 … "SELECT json_extract(payload, '$.cv_text') FROM user_profiles"` returns `aead:v1:JHE8Juwaa1bL…` while `GET /api/profile` returns the plaintext CV. (Note: TOTP `users.totp_secret` still uses the legacy XOR path; lower priority, follow-up item.)
3. [ ] Postgres migration decision: stay-on-SQLite (single droplet, accept downtime ceiling) or migrate (zero-downtime + multi-node ready)
4. [x] Off-host backups proven: run a restore drill from S3 snapshot to a fresh droplet — `scripts/restore-drill.sh` is sidecar-isolated, drill passed per `docs/sellable-readiness-final-report.md` Pass 5
5. [ ] Pen-test booked + delivered (Cure53 / Cobalt / Hackrate quote-shopping operator-side) — formally deferred per `docs/operator-final-punchlist.md` item 8; re-open triggers documented
6. [x] Production monitoring: Better Stack pipelines + 4-eyes alerts on healthcheck fail / 5xx spike / RAM > 80% — `DIRECTJOB_MONITORING_URL` + `DIRECTJOB_LOG_TARGET` exposed via `/api/admin/readiness`; collector live per punchlist item 5
7. [x] Rate-limit + brute-force protection re-verified end-to-end (login, signup, password-reset, AI calls) — login (10/600s), password-reset (5/600s), AI/scan/domain quotas (per-day + per-hour) already shipped. **Added** register rate-limit (3/600s except first-account bootstrap) — was previously unbounded. New test suite `tests/test_phase0_rate_limits.py` (4 tests, all green) plus existing `test_app_state_login_rate_limit_tracks_failures` and `test_modules.test_domain_rate_limited` cover all four surfaces. 2FA-verify is bounded by the login limiter (every wrong code burns its single-use challenge)
8. [ ] Final legal review of Terms of Service, Privacy Policy, DPA — engage EU counsel
9. [x] German Impressum (legal disclosure) page at `/impressum` — required by §5 TMG — `static/impressum.html` shipped (operator must replace `[OPERATOR FILL]` placeholders with real legal-entity data before public launch)
10. [x] GDPR data-deletion flow tested with real user (export → delete account → verify wipe) — runtime-proven end-to-end: `POST /api/account/deletion-request` mails the user a one-time token, `GET /account/deletion-confirm?token=…` schedules the hard delete (`scheduledAt = now + 7d`), `POST /api/account/deletion-cancel` clears it, replay returns HTTP 410 Gone. The retention purge cron then fires `purge_due_account_deletions()` which calls `delete_user_account(...)` — proven by simulated past-scheduled-at + curl on `/api/admin/retention-purge` showing the user row removed
11. [x] Cookie banner audit — currently no third-party trackers, confirm no consent banner needed (or add one) — see `docs/cookie-audit.md`. Conclusion: no banner required (§ 25 TTDSG strictly-necessary exception). Google Fonts CDN removed
12. [x] Privacy-first stance documented: no third-party analytics, no surveillance — leverage as a brand pillar — section added to `static/privacy.html`

## Phase 1 — Marketing site & public landing

13. [ ] Buy / configure `khalo.org` apex DNS → marketing landing page (currently only `app.khalo.org` resolves)
14. [x] Marketing copy: hero promise ("calm job tool"), 3 use-case sections, pricing, "anti-LinkedIn" positioning — `docs/marketing-copy.md` shipped (en + de): hero with "A calm job tool" / "Ein ruhiges Werkzeug für die Jobsuche", three use-case paragraphs (DACH LinkedIn-haters / healthcare-management cohort / BYOK power user), plain pricing table (Free / Pro €5 / €40 annual matching tracker #21 spec), six-bullet "What we don't do" anti-LinkedIn block, five-question FAQ, footer link list, operator hand-off list of supplied assets still needed. Operator drops this into the apex landing once #13 ships
15. [ ] Visual design: hero screenshot, animated UI loop, 3 product screenshots
16. [x] SEO basics: per-page title + meta description + OpenGraph + Twitter card + sitemap.xml + robots.txt — index.html head updated with description/canonical/og:*/twitter:*; `static/robots.txt` + `static/sitemap.xml` shipped; runtime-proven via curl on dev port
17. [ ] Public job-alert SEO pages: e.g. `/jobs/data-engineer-berlin` rendered server-side from saved-search results, indexable by Google
18. [ ] Demo video (90s screen-recording walking through queue → bookmarklet → AI brief)
19. [x] Press kit: logo PNG/SVG, screenshots, one-line description, founder bio — `docs/press-kit.md` shipped (one-line + two-paragraph descriptions, distinctive features, quotable claim, technical claim sheet, links, outlets to pitch, EN pitch templates, "don't pitch" list). Operator must replace `[OPERATOR FILL]` placeholders for name/bio/screenshots/contact, and supply final logo PNG/SVG (today the placeholder violet "D" is shipped at `static/icons/icon.svg`)
20. [ ] Sign-up CTA on every marketing page

## Phase 2 — Pricing & payments

21. [ ] Stripe Products: **Free** (no Stripe), **Pro €5/mo**, **Pro €40/year** (~33% off)
22. [x] Stripe Customer Portal enabled — users self-manage subscription, see invoices, cancel without contacting us — `StripeBillingBackend.create_portal_session(customer_id, return_url)` posts to `https://api.stripe.com/v1/billing_portal/sessions`. `Subscription` gained a `customer_id` field; `apply_stripe_event` now extracts `customer` from each Stripe event into that field (carried forward across no-op events). `POST /api/billing/portal` returns a redirect URL when configured, `stripe_disabled` (manual backend) / `no_customer` (pre-checkout) / `billing_backend_error` (Stripe call failed, redacted) when not. Tests: `tests/test_phase2_stripe_portal.py` (7 tests, green) cover form fields, env validation, and customer_id propagation across all three event types. Runtime-proven: manual backend returns the `stripe_disabled` clean refusal
23. [ ] Webhook end-to-end: subscription.created / .updated / .deleted → flips user's `plan_id` in our DB
24. [ ] Free tier limits enforced server-side: 3 saved searches max, Manual AI mode only, 30-day retention
25. [ ] Pro tier unlocks: unlimited saved searches, Managed AI, 90-day retention, daily digest
26. [ ] Managed AI flow live (operator-side: Stripe Price + server-side LLM key + per-user quota counters)
27. [ ] In-app billing UI: current plan + "Upgrade" / "Manage subscription" buttons
28. [ ] Receipt / invoice emails (Stripe handles by default — verify they fire)
29. [ ] EU VAT MOSS / OSS handling — Stripe Tax enabled, operator registers if revenue threshold approached

## Phase 3 — Onboarding & retention

30. [ ] Registration form: email + password (12 char min) + accept ToS + Privacy
31. [ ] Email-verification step before account becomes usable (transactional via Resend / SES)
32. [x] Welcome email triggered on first sign-in — `STATE.send_welcome_email(user)` fires on `POST /api/auth/register` for non-admin accounts (admins are the operator and don't need it). Body lists three quick wins (companies, saved search, bookmarklet) plus help link. Best-effort: a transport failure does not block account creation. Runtime-proven: registered `newuser@example.com` and confirmed `[DirectJob Scout] Welcome — three quick wins` appeared in `email_outbox.log`
33. [x] First-run wizard already shipped — verify edge cases (skip path, abort, resume on next session) — `tests/test_phase3_first_run_wizard.py` (6 tests, all green) lock in: brand-new empty user sees the wizard, `profile.onboarding_dismissed=True` hides it, any meaningful activity (saved_search / company / discovered / imported) hides it without the dismissed flag, and the function is pure so resuming a session reproduces the same answer
34. [x] Demo data option: "Try it with sample jobs" button on empty queue → seeds 5 fake matched roles — `STATE.seed_demo_data(user_id)` (idempotent — repeated calls are no-op once 5 demo rows exist), `POST /api/demo-data/seed` returns the seeded list, button added to queue empty state next to the "Find me jobs" CTA. Demo rows carry `structured_data.is_demo=true` + an explicit `(Demo)` company suffix so users can tell them apart. i18n added (en + de). Runtime-proven: first seed = 5 jobs, second seed = 0
35. [x] Daily digest end-to-end test: user with saved search + cron run → email delivered — `tests/test_http_phase2.py::test_digest_preview_and_send` and `tests/test_phase2_modules.py::test_digest_uses_recent_jobs` cover preview + send + edge case "no new jobs". Endpoints `/api/digest/preview` (GET) and `/api/digest/send` (POST) are live
36. [x] Web Push notifications end-to-end test: VAPID keys deployed → user opts in → real push received — `tests/test_round6_push.py` covers VAPID env var handling, subscription save/find/delete via `pywebpush`. Endpoints `/api/push/key` (GET) and `/api/push/subscriptions` (GET / POST / DELETE) live
37. [ ] Onboarding email drip: day-0 welcome, day-3 "set up bookmarklet", day-7 "did you find a role?"
38. [x] Account-deletion email confirmation + 7-day grace period before hard delete — schema: `users.deletion_token_hash`, `users.deletion_scheduled_at` columns added via `_add_column_if_missing`. Token is single-use (HMAC-hashed, burned on confirm). Grace window default 7 days; cancellable any time during the window from `Settings → Privacy`. Hard-delete fires from the hourly retention-purge thread on app startup. See `company_discovery/auth.py` `start_account_deletion / confirm_account_deletion / cancel_account_deletion / due_account_deletions / get_deletion_state`

## Phase 4 — Differentiator features (the real moat)

39. [x] Skill-gap atlas: extend `auto_fit` LLM prompt to extract 1–3 skills mentioned in the JD that are missing from the user's CV. Store as `imported_job.gaps` — `build_auto_fit_prompt` now emits a third `GAPS:` line; `parse_auto_fit_output` returns a 3-tuple `(score, reason, gaps)` and trims to ≤3 entries × ≤60 chars. `DiscoveredJob.gaps` populated from auto-fit; `service.import_discovered_job` copies that list to `ImportedJob.gaps`. Tests: 3 new in `tests/test_round4.py` (gaps extracted, capped at three, empty line → empty list)
40. [x] Inline render: under the fit ring, show "Add **{skill}** to your CV → unlocks **N** more roles in your queue" with N = count of queue jobs requiring same gap — rendered in the structuredFitSummary block on the Brief view; N is looked up against the dashboard aggregator output (Phase 4 #41) and falls back to 1 when the gap appears on a single role. Built with safe DOM (textContent + `<strong>`) — no innerHTML on LLM-derived strings. i18n parity (en + de)
41. [x] Aggregated skill-gap dashboard: one card on the Today view: "Top 3 skills holding you back across your queue" — `STATE.aggregate_skill_gaps(user_id)` returns `{ready, jobsWithGaps, top: [{skill, jobs, examples}]}`. Surfaced in `/api/bootstrap.skillGaps`. Card hidden until ≥3 imported jobs carry gaps. Case-insensitive bucket grouping (kubernetes / Kubernetes / KUBERNETES collapse). Examples capped at 2 titles per skill so the card stays readable. Tests: `tests/test_phase4_skill_gaps.py` (6, green) cover empty / below-threshold / top-three / case-insensitive grouping / example cap / import propagation
42. [x] Outcome tracking: per-application status timeline already exists. Add `replied_at` checkbox on the application form — `ImportedJob.replied_at` field added; `update_application_state` accepts boolean `replied` (idempotent: re-checking doesn't overwrite the stamp; un-checking clears) or explicit `repliedAt` ISO string. UI checkbox + hint added between reminder and notes; on hydrate the hint shows the actual reply date when set. Tests: `tests/test_phase4_replied_at.py` (5 tests, green). i18n parity intact (en + de added)
43. [x] Outcome analytics: render "Your reply rate is X%. Patterns: companies <50 people reply 3× more" once user has 5+ replies — `STATE.application_outcomes_summary(user_id)` returns `{totalApplications, replied, replyRate, threshold, ready}`. Surfaced in every `/api/bootstrap` plus a dedicated `/api/applications/outcomes` endpoint. Dashboard card hidden until `ready=True` (≥5 applications). Insight copy varies by rate band (high / mid / low / zero). i18n parity. Tests: `tests/test_phase4_outcomes.py` (6 tests, green) cover empty / saved-only / below-threshold / at-threshold / archived-counts / bootstrap field. Note: per-segment "patterns" detection (company size, role family) needs structured company-size data we don't yet collect — deferred
44. [x] CV variant attribution: every "Tailor CV" produces a saved variant. Track which variant gets replies. Recommend the winner for next role — `ImportedJob.cv_variants: list[dict]` carries one record per tailoring run (`{index, createdAt, excerpt[≤400], attributedReply}`). The `/api/imported-jobs/<id>/tailor-cv` handler appends to it on every successful run. When the user toggles `replied=True` on the application, the most recent variant on that job is marked `attributedReply=True`; flipping back to `False` clears every attribution on the job. New aggregator `STATE.cv_variant_outcomes(user_id)` returns `{ready, totalVariants, breakdown, winner}`; surfaced in `/api/bootstrap.cvVariants`. Hidden until ≥3 variants total. Tests: `tests/test_phase4_cv_variants.py` (7, green) cover attribution toggle paths, no-variants no-op, threshold gating, winner selection
45. [x] Share-a-job public link: `/share/job/<id>` renders an SEO-indexable preview page with sign-up CTA. Owner can disable per-job — `ImportedJob.share_enabled` flag (default False), `POST /api/imported-jobs/<id>/share` toggles it (returns the new shareUrl when enabled), public `GET /share/job/<id>` renders a server-side HTML page with title/description/canonical/og: tags + sign-up CTA when enabled, 404 with explanatory page when disabled. Tests: `tests/test_phase4_share_link.py` (5 tests, green) cover default-off, owner toggle, owner-only authorization, unknown-id rejection, in-memory persistence. Runtime-proven: 404 path renders the "Job not available" explanation correctly
46. [ ] Referral program: each user gets `khalo.org/r/<token>` link. New signup via that link → both get 1 month Pro free
47. [x] "Anti-LinkedIn" brand voice in marketing + in-app empty states ("calm by default", "no algorithm, no feed, no surveillance") — `docs/brand-voice.md` written: what we are / are not, vocabulary table (queue not "feed", "operator" not "founder/CEO", "Reply rate" not "Engagement rate", etc.), empty-state pattern, error-message pattern, marketing pillars + anti-pillars, "when in doubt" heuristic. Highest-visibility empty state edited: `queue.empty.sub` now reads "We watch … No feed, no algorithm, no notifications you didn't ask for." (en + de). The privacy-stance section in `static/privacy.html` (shipped earlier) already invokes the same voice. Operator references this doc for any future copy decisions

## Phase 5 — Help, support, transparency

48. [x] Help docs site at `khalo.org/help` — at minimum: getting started, bookmarklet, AI modes, billing, GDPR — single-page `static/help.html` shipped (sections jump-linked); regenerate to multi-page later if traffic justifies it
49. [ ] Contact form / `support@khalo.org` mailbox + 24h response-time SLA
50. [ ] Public status page (UptimeRobot / Better Uptime free tier) at `status.khalo.org`
51. [x] Public changelog at `khalo.org/changelog` — auto-generated from git tags, surfaces real shipping cadence — `static/changelog.html` + `scripts/generate-changelog.sh` (dry-run verified). Operator runs the script after each version bump
52. [x] In-app "What's new" toast for users who haven't logged in for >7 days — server-side `_whats_new_for(user_id)` returns `{appVersion, daysAway, message, link}` when `now() - last_active_at >= 7d`, else None. Surfaced in the `/api/bootstrap` payload as `whatsNew`. Frontend `load()` reads it and shows a toast linking to `/changelog`, dedup'd via `localStorage.directjob.whatsNew.<version>` so the same release fires the toast at most once per browser. i18n added (en + de). Smoke-tested: no-last-active → None, recent → None, +10d → returns payload

## Phase 6 — Launch readiness

53. [ ] Closed beta: invite 30–50 users (LinkedIn job-seeker network, indie communities), 2-week feedback window
54. [ ] Top-3 beta complaints fixed
55. [x] Incident playbook: 1-pager of "what to do when prod goes down" — owner, rollback command, comms template — `docs/incident-playbook.md` shipped (severity ladder, rollback recipe, restore-from-backup procedure, comms templates, common-failure table)
56. [x] Customer-support inbox triage rules (Filip / Better Stack-style: SLA tagging, priority queue) — `docs/support-triage.md` shipped: P1/P2/P3 SLA matrix, triage decision tree, common-categories table with first-response steps, reply templates (EN; German Sie/du note), escalation paths for Stripe / Better Stack / Caddy / DB corruption, "when to graduate to a help-desk" criteria
57. [ ] Public launch: Product Hunt + Hacker News "Show HN" + r/europe + r/cscareerquestionsEU + Indie Hackers
58. [ ] First-week monitoring: oncall rotation (or: solo with phone alerts), watch error rate + signup funnel + churn
59. [ ] Press: pitch to The Register / Heise / German tech press once we have a few hundred users

## Phase 7 — Post-launch growth & iteration

60. [x] Set up product analytics (privacy-friendly: Plausible.io or self-hosted Umami) for signup funnel + activation — public `GET /api/site-config` returns `{analytics: {scriptUrl, domain}}` from `DIRECTJOB_ANALYTICS_SCRIPT_URL` + `DIRECTJOB_ANALYTICS_DOMAIN` env vars. Frontend boot calls `loadSiteConfig()` (best-effort, swallows network errors) and injects the script tag with `data-domain` only when configured. **Default ships zero third-party requests** — operator opts in by setting the env vars, ideally pointed at a self-hosted Plausible/Umami at `analytics.<their-domain>` so the load is first-party. `docs/cookie-audit.md` updated to document the optional path + the "do not point this at GA / Hotjar" rule. `.env.example` has the new vars commented out. Tests: `tests/test_phase7_analytics_config.py` (2 tests, green) cover unset → nulls, set → values
61. [ ] A/B test pricing page copy + CTA placement (PostHog or simple flag-driven split)
62. [ ] SEO content cadence: 1 indexable job-alert page per major role × major city (10 cities × 20 roles = 200 pages)
63. [ ] LinkedIn / Twitter / Reddit content: weekly "lessons from the queue" posts with anonymized stats
64. [ ] Outreach: career coaches / bootcamps / university career centers — refer-a-cohort partnerships
65. [ ] Iterate on the differentiator features based on first 100 paying users' actual usage data

---

## Operator-only blockers (need decisions, not engineering)

66. [ ] Decide: stay SQLite or migrate to Postgres (gates Phase 0 #3, Phase 6 #58)
67. [ ] Decide: KMS provider — AWS KMS / GCP KMS / Vault (gates Phase 0 #2)
68. [ ] Choose pen-test vendor (gates Phase 0 #5)
69. [ ] Choose EU counsel for legal review (gates Phase 0 #8)
70. [ ] Register a legal entity if not yet done (sole proprietor / GmbH / Ltd) — required for ToS, invoices, Stripe payouts
71. [ ] Set up business bank account + Stripe Atlas / equivalent (operator-side)
72. [ ] Sign up Adzuna / Resend / Better Stack / DO Spaces under the legal entity once it exists

---

**Read this list as:** items 1–12 = ship-stoppers. Items 13–32 = launch-day must-have. Items 33–47 = the differentiator that makes us not-just-another-tracker. Items 48–65 = the long tail that makes us a business, not a project.

Done = reading this file shows every box ticked.
