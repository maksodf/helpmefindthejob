# Operator launch runbook

Every item the operator must do before, during, and after public launch. Each section maps to a tracker line. Engineering side is shipped — these are the human-driven actions.

Read in order on launch day. Items marked **[blocking]** must be done before flipping `DIRECTJOB_ALLOW_REGISTRATION=true`. Everything else can run in parallel.

---

## Phase 0 — pre-launch operator decisions

### 1. Flip registration on (#1) — [blocking]

```sh
ssh -i ~/.ssh/directjob_scout root@161.35.76.8 \
  "sed -i 's/^DIRECTJOB_ALLOW_REGISTRATION=false/DIRECTJOB_ALLOW_REGISTRATION=true/' /opt/directjob-scout/.env && \
   cd /opt/directjob-scout && docker compose -f docker-compose.prod.yml up -d --wait"
```

Verify with `curl https://app.khalo.org/api/auth/status | jq .registrationOpen` — must return `true`. Reverse with the same `sed` flipped.

Pre-condition: items #5 (pen-test deferral signed), #8 (legal review approved), #29 (VAT decision) all closed.

### 3. SQLite vs Postgres (#3)

Decision criteria: if active-user count is < 100 and concurrent writers < 5, **stay on SQLite**. The handoff doc covered this — single-droplet + WAL-mode + named volume + `.backup()` API works through to ~mid-double-digit concurrent writers. Migrate when:

- Active users cross 100 **and** writes >5/sec sustained
- Multi-region requirement appears
- Operator wants zero-downtime deploys (SQLite needs a brief pause on volume mount)

If migrating, the migration plan is: `pg_dump` the in-flight schema + add a Drizzle/SQLAlchemy adapter, swap `SqliteCompanyDiscoveryRepository` for a Postgres repo (the in-memory protocol is the boundary). Budget 2 weeks of focused engineering.

**Today: stay SQLite. Re-evaluate at the 100-user mark.**

### 5. Pen-test booking (#5)

Formally deferred for the unpaid pilot per `docs/operator-final-punchlist.md` item 8. Re-open triggers (any one fires → schedule before expanding scope):

- First paying customer signs up
- Real personal health data ingested by any user
- Active user count exceeds 25
- Operator picks a hard go-live date

Vendors: Cure53, SEC Consult, Code Intelligence (EU). Budget €5–15k for a 3–5 day app pen-test. Brief them with `docs/threat-model.md` + `docs/security-review-checklist.md` + a test admin credential + `docs/legal-review-brief.md` data-shape doc.

### 8. Legal review (#8) — [blocking]

Brief at `docs/legal-review-brief.md`. German Datenschutz lawyer options:

- **Legalbird** — consumer-grade, fast, ~€500–1k for the package
- **Klugo** — tech-friendly, mid-range, ~€1.5–3k
- **IT-Recht Kanzlei** — specialised, more thorough, ~€2–5k

Steps:

1. Email the brief + drafts of `static/privacy.html`, `static/terms.html`, `static/impressum.html` (operator filled), `static/data-retention.html`.
2. Apply redlines (likely: privacy wording, retention specifics, AVVs with Resend / Backblaze B2 / Better Stack).
3. Set `DIRECTJOB_LEGAL_REVIEWED=true` in prod env, restart container.
4. Update `docs/sellable-readiness-final-report.md` with the sign-off date.

Force-trigger to engage now: first paid customer, real personal health data, >25 active testers.

---

## Phase 1 — apex marketing surface

### 13. Buy + configure khalo.org apex DNS (#13) — [blocking for marketing launch]

Apex `khalo.org` currently doesn't resolve (only `app.khalo.org`). Steps:

1. Confirm domain ownership in your registrar dashboard.
2. Cloudflare or registrar DNS:
   - `A khalo.org → <marketing-host-ip>` (or the same droplet IP, with Caddy multi-domain)
   - `A www.khalo.org → <same>`
3. If reusing the existing droplet, extend the Caddyfile:
   ```
   khalo.org, www.khalo.org {
     redir https://khalo.org{uri} permanent
     root * /opt/khalo-marketing/static
     file_server
     encode gzip
   }
   ```
4. `docker compose restart caddy`. Caddy auto-issues the cert via ACME.
5. Verify with `curl -I https://khalo.org` returning 200, and `https://khalo.org/sitemap.xml` 200.

Order-of-operations to avoid the SSL-provisioning hang loop: provision DNS first (wait ≥5min for propagation), **then** restart Caddy. CAA records on the apex domain should not block Let's Encrypt; if you have any, allow `letsencrypt.org`.

### 15. Visual design (#15)

Three deliverables before marketing launch:

- **Hero screenshot** — annotated `static/icons/hero-screenshot.png`, 1600×1000, dark theme, queue triage view. Tools: Figma + Cleanshot for the actual capture.
- **Animated UI loop** — 8–12s WebM/MP4, queue triage with `j`/`k`/`a`/`x` keystrokes shown as overlay. Tool: Cleanshot record + ffmpeg trim.
- **Three product screenshots** — the application form (showing the structured fit ring + gaps + reply-rate card), the AI mode picker, the bookmarklet card. PNG, 1600×1000.

Drop into `static/icons/` and reference from `docs/marketing-copy.md` once ready.

### 18. Demo video (#18)

90-second screen recording. Walk-through script:

1. **0:00–0:10** — Land on the home page. Sign in.
2. **0:10–0:25** — Open Companies tab, add 3 example companies (Acme Health, Demo Insurance, Sample SaaS via the suggestions card).
3. **0:25–0:45** — Click "Find me jobs". Watch the skeleton loaders. Show the queue populating.
4. **0:45–1:05** — Triage with `j`/`k`/`a`/`x`. Import one role.
5. **1:05–1:20** — Click "Tailor CV" on the imported role. Show the AI mode picker (Manual). Walk through copy-paste handoff to ChatGPT.
6. **1:20–1:30** — Show the dashboard cards (reply rate, skill gaps, recent activity).

Record at 1080p with Cleanshot or OBS. Trim with iMovie or ffmpeg. No music. No voice-over (the video should read on mute).

---

## Phase 2 — pricing decision

### 21. Stripe pricing model (#21) — [blocking for paid launch]

**Decision needed**: Free / Pro €5 / Pro Annual €40 (single-user B2C) **OR** keep Team €79 / Org €249 (multi-seat B2B).

The two are not necessarily exclusive. Tracker spec wants Free/Pro single-user; existing code ships Team/Org multi-seat. Both can co-exist in `company_discovery/billing.py PLANS`.

Recommendation: **start with Free / Pro €5 / Pro Annual €40 single-user** — the DACH job-seeker individual is the pilot persona. Multi-seat (Team/Org) is a later sales-led motion when an enterprise asks.

To implement after deciding:

1. Edit `company_discovery/billing.py PLANS` tuple — add:
   ```python
   Plan(id="free", label="Free", monthly_price_eur=0, seats_included=1, features=("3 saved searches", "Manual AI", "30-day retention")),
   Plan(id="pro_monthly", label="Pro", monthly_price_eur=5, seats_included=1, features=("Unlimited saved searches", "Managed AI", "90-day retention", "Daily digest")),
   Plan(id="pro_annual", label="Pro (annual)", monthly_price_eur=4, seats_included=1, features=("All Pro features", "8 months for 12", "Annual billing")),
   ```
2. Stripe → Products → create the two paid SKUs (5€/mo + 40€/yr, both with the **Pro** product).
3. Copy price IDs into `.env`:
   ```
   DIRECTJOB_STRIPE_PRICE_PRO_MONTHLY=price_...
   DIRECTJOB_STRIPE_PRICE_PRO_ANNUAL=price_...
   ```
4. Update `StripeBillingBackend.price_lookup` to map the new ids.
5. Wire tier-limit enforcement (#24, #25 — already scaffolded).
6. Restart container.

### 29. EU VAT / MOSS (#29)

**Stripe Tax** is the cheapest path: Stripe → Tax → Activate. €0.50/transaction or 0.5% (whichever lower). Auto-collects VAT for EU consumers, generates the OSS-compatible report.

Threshold: if all annual cross-EU revenue stays below €10 000, you can charge German VAT on every sale. Above the threshold, Stripe Tax + OSS registration in Germany is required. Operator registers at <https://www.bzst.de/EN/Businesses/VAT/OSS_VATone-stop-shop_OSS_node.html>.

Set `DIRECTJOB_LEGAL_REVIEWED=true` only after confirming with the lawyer (item #8) that the chosen VAT model is correctly disclosed in the Impressum + ToS.

---

## Phase 5 — public visibility

### 50. Public status page (#50)

**Better Uptime** (now Better Stack) free tier: <https://betterstack.com/uptime/pricing>. Steps:

1. Sign up at Better Uptime → New monitor → URL `https://app.khalo.org/api/health`.
2. Add a public status page at `status.khalo.org`. Configure DNS:
   ```
   CNAME status.khalo.org → status.betterstack.com
   ```
3. Add a link in `static/help.html` footer + `docs/marketing-copy.md` once live.

Free tier covers 1 monitor + 1 status page, which is enough for pilot.

---

## Phase 6 — launch coordination

### 53. Closed beta invites (#53)

Send 30–50 invites via the existing admin invitation flow:

```
curl -X POST https://app.khalo.org/api/admin/invitations \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <admin-csrf>" \
  -b /tmp/khalo-cookies \
  -d '{"email":"<beta-tester>","role":"member"}'
```

Source pool, in priority order:

1. Operator's LinkedIn / Mastodon / personal network (highest open + reply rate).
2. r/cscareerquestionsEU + r/europe — hand-curated pool, **don't** spam-DM.
3. Indie Hackers + Hacker News (a thoughtful "Show HN: looking for 30 beta testers" post).
4. DACH-specific Slack / Discord communities (e.g. `dach.tech`, ITDevConnected).

Two-week feedback window. Track via the existing `analytics_events` table; query `SELECT user_id, COUNT(*) FROM analytics_events GROUP BY user_id` to find active vs ghost-invited.

### 54. Top-3 beta complaints fixed (#54)

Depends on #53. After the feedback window, review the support inbox + analytics. Apply fixes via the standard PR flow. Ship before public launch.

### 57. Public launch (#57)

**Day-of checklist:**

- [ ] All Phase 0 + Phase 2 + Phase 5 items closed.
- [ ] Production smoke (`./scripts/production-smoke.sh`) green.
- [ ] Off-host backup tarball < 24h old.
- [ ] Better Stack monitor green.
- [ ] Status page reachable.
- [ ] Press kit assets in `static/icons/`.
- [ ] Operator at the keyboard for the next 6h.

**Submission order** (don't simultaneously — stagger so you can respond to comments):

1. **08:00 CET** — Indie Hackers post.
2. **10:00 CET** — Hacker News (Show HN: title format `Show HN: DirectJob Scout — calm job tool, no LinkedIn feed (DACH)`).
3. **12:00 CET** — Product Hunt (if you maintain a hunter relationship).
4. **14:00 CET** — r/cscareerquestionsEU + r/europe.

Pitch templates in `docs/press-kit.md`.

### 58. First-week monitoring (#58)

Solo operator → phone alerts via VAPID push (already wired) + Better Stack SMS escalation on a 5xx spike or container-unhealthy >5min.

Watch:

- Signup funnel: `SELECT COUNT(*), DATE(created_at) FROM users GROUP BY DATE(created_at)`
- Activation: % of new users who completed at least one saved-search scan in 24h
- Churn (early): % of new users who didn't return after day 1
- Error rate: tail Better Stack `directjob-scout-prod` source for 5xx spikes
- Reply rate to onboarding emails

Daily 09:00 + 21:00 CET review for the first 7 days. Drop to once-daily after the second week.

### 59. Press pitch (#59)

After ~200 active users + 1 month uptime. Outlets in `docs/press-kit.md` (Heise, t3n, The Register, indie tech press). Cold email template included.

Don't pitch press before you have a clear "100 users in N weeks" or "first paying customer" story — outlets ignore announcements without a concrete data point.

---

## Phase 7 — post-launch growth

### 63. Social content (#63)

Cadence: 1 LinkedIn post + 1 Twitter / Mastodon thread per week. Topics rotate:

- Week 1: "What I learned building DirectJob Scout in public" — operator's personal story.
- Week 2: anonymised aggregate stats from the user base ("78% of our users hate the LinkedIn feed").
- Week 3: a specific feature deep-dive (skill-gap atlas; bookmarklet).
- Week 4: a customer interview (with consent).

Repeat. Cross-post via Buffer if you maintain it; otherwise post manually so the engagement is actual.

### 64. Outreach (#64)

Three cold-outreach channels in order:

- **Career coaches + bootcamps** — refer-a-cohort partnerships. Coach gets a small kickback (or affiliate code via #46), bootcamp gets a free Pro for graduating students for 3 months.
- **University career centers** — DACH unis specifically (TU Berlin, TUM, ETH Zürich). Free Pro for current students.
- **Indie / OSS communities** — sponsor a small newsletter (Indie Hackers Weekly, ChangeLog) for a 6-week run.

Budget: €0–2k for the first 3 months. Track conversions via the referral program (#46).

### 65. Iterate based on usage data (#65)

After 100 paying users, run a quarterly review:

- Reply-rate aggregator (the dashboard card from #43): which user segments have the highest rate? Why?
- Skill-gap atlas (#41): which 5 gaps come up most across the queue?
- CV variant attribution (#44): which kind of variant wins?
- Onboarding funnel: where do users drop off? Day 0 / day 3 / day 7?

Use the answers to drive the next quarter's roadmap. Don't iterate on speculation — let the data lead.

---

## Operator-only blockers (#66–#72)

These are decisions the operator must make once. They block specific Phase 0 items.

| Tracker | Decision | When to make it |
|---|---|---|
| **66** | SQLite or Postgres | Today: SQLite. Re-evaluate at 100 active users. |
| **67** | KMS provider | When `DIRECTJOB_DATA_KEY` rotation policy needs vendor backing. AWS KMS is cheapest in EU; Vault if self-hosted. Today: HKDF-derived from `SECRET_KEY` (acceptable per `crypto_kit.py` docstring). |
| **68** | Pen-test vendor | Per #5. Before first paid customer / before >25 testers. |
| **69** | EU counsel | Per #8. Engaged before public sign-up flips on. |
| **70** | Legal entity | Sole proprietor (`Einzelunternehmen`) for the first year — fast + cheap. GmbH only when revenue justifies the €25k stamm-kapital. |
| **71** | Business bank + Stripe Atlas | Wise Business or Vivid Money for the EU side. Once entity is registered, Stripe Atlas is overkill (it's US-targeted). Direct Stripe registration with the German entity. |
| **72** | Vendor accounts under entity | After #70 + #71. Adzuna / Resend / Better Stack / DO Spaces — all under the entity, not the operator's personal email. |

Do these in order: 70 → 71 → 72 → 67 → 68 → 69 → 66.

---

## Reading the trail

Each tracker line that closes via this runbook should reference the section above. The tracker is the index; this doc is the procedure. Keep both in sync — when the runbook changes, update the tracker line; when the tracker line moves, update the runbook section.
