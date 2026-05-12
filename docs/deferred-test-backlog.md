# Deferred test backlog

Tracked here so we don't lose them. **Do NOT work on these** until the
three priority items below are 100% green:

1. ✅ / 🟡 / 🔴 — Adversarial chaos inputs (functionality + desktop UX)
2. ✅ / 🟡 / 🔴 — AI quality (real analysis, not just prompt assembly)
3. ✅ / 🟡 / 🔴 — AEAD encryption pass under fuzzing

When all three turn ✅, revisit this list.

## Deferred (date: 2026-05-11)

### Scale / multi-user
- 50–500 parallel registrations from distinct IPs (load + rate-limit semantics)
- 100 imported jobs / 1000 imported jobs in one account (queue render, dedup correctness)
- 10 testers running scheduled scans simultaneously (DB lock contention, scheduler fairness)
- Admin panel under load (readiness + stats still accurate?)

### Billing / Stripe
- Subscribe → cancel → re-subscribe → invoice end-to-end
- Webhook handling: payment.failed, subscription.deleted, customer.deleted
- Annual vs monthly plan switch (proration, downgrade behavior)
- Refund flow
- Stripe Customer Portal session creation under real key
- Plan-limit enforcement at the *boundary* (creating saved-search #4 on free plan)

### Email
- Verification email landing in Gmail / Outlook / iCloud inboxes (not spam)
- Password-reset flow end-to-end via real SMTP
- Daily-digest delivery timing + content correctness
- Bounce + unsubscribe handling
- Multi-recipient invites (tester invitation flow)

### Bookmarklet
- Click on LinkedIn job page → capture URL → appears in queue
- Click on Indeed / StepStone / Xing / native German boards
- Token expiry / refresh
- Captured-job dedup against existing queue
- Capture from inside a popover / iframe

### Mobile / tablet
- 390×844 (iPhone) viewport: every screen renders correctly
- 768×1024 (iPad): same
- Tap targets ≥ 44pt, no overflow, no horizontal scroll
- Keyboard shortcuts gracefully no-op on touch devices
- First-run wizard usability on small screens

### Multi-day workflows
- Day 1: import + apply, Day 2: scheduled scan dedupes, Day 3: reply tracked correctly
- Daily-digest content over 7 days
- Retention policy: 30-day data actually expires when configured
- Watchlist scan over a long-running fixture (does it actually find new jobs daily?)

### Security beyond unit tests
- CSRF defense on every state-changing endpoint
- XSS surface: every user-input field that renders into HTML
- SQL injection fuzzing on every field
- Path traversal on file upload (CV extraction)
- Rate-limit edge cases (X-Forwarded-For spoofing, IPv6 same-prefix)
- Session-token entropy + expiry
- OAuth / API-key leakage in error responses

### Cross-cutting
- Public-launch readiness checklist
- Performance: TTFB, render time, server resource footprint per concurrent user
- Backup + restore drill (does the export/import actually round-trip lossless?)
- DSGVO deletion request: does it cascade correctly?
- Multi-language: locale flag works, UI text renders correctly in DE/EN

### Operator / business-side domains — DEFERRED (not coding tasks)

The operator's hat list included six business/marketing roles that
require human judgement, brand strategy, or external services rather
than code. Listed here so the gap is explicit and the work isn't
forgotten:

- **Performance marketing strategist** — channel-mix planning (Google
  Ads / Meta / LinkedIn / programmatic), CAC budgeting, attribution
  setup. Engineering provides the analytics surface; this is operator
  decision territory.
- **Growth / SEO specialist** — keyword research for "ATS CV builder
  Germany", "Lebenslauf Vorlage", "honest job search DACH"; sitemap,
  meta tags, schema.org JobPosting markup (we already emit some).
  Needs an external audit + content calendar before launch.
- **Conversion rate optimization (CRO) specialist** — landing page
  A/B testing, signup-funnel teardown, drop-off analysis on the
  wizard. Engineering ships analytics; this role designs the
  experiments.
- **Brand designer** — logo finalization, color palette beyond the
  current dev tones, illustration system for empty states, marketing
  site visuals. Brand work is design-craft, not code.
- **Content strategist / marketing copywriter** — landing-page copy,
  email-nurture sequence text, blog/SEO articles, social-media
  templates. Engineering ships transactional email scaffolding; this
  role writes what goes inside.
- **Email deliverability specialist** — SPF / DKIM / DMARC config,
  IP warmup if leaving Resend's shared pool, inbox-placement testing
  across Gmail/Outlook/iCloud. Partially engineering (DNS records)
  but mostly an external service + monitoring relationship.
- **Social media manager / native-content creator** — content
  cadence on Twitter/LinkedIn/Reddit, community management, launch
  posts. Pure operator role.

**What this means for the test suite:** these don't get synthetic
testers because there's nothing to assert programmatically. They DO
each need a written launch checklist before public rollout — that's
deferred to a separate "operator launch playbook" doc.
