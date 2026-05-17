# Operator Launch Playbook

Companion to `docs/deferred-test-backlog.md`. Where the test backlog
lists what *engineering* still needs to verify before a public drop,
this playbook lists what **the operator** has to do that isn't a
coding task — performance marketing, growth/SEO, CRO, brand, content,
email deliverability, social. Each section gives a concrete checklist
you can tick off before flipping the switch on public sign-up.

> **Read this first.** Engineering says the product is defensible for
> 10 invited testers right now (828 live checks pass, 17 bugs fixed,
> zero regressions across 13 rounds). Everything below is what's
> needed to take it from "10 friendly testers" to "Twitter / HN drop".

---

## 1. Performance marketing strategist

**What this role does:** designs the paid-acquisition strategy —
which channels, at what budget, with what creatives, measured against
what conversion goal.

**Operator checklist:**

- [ ] **Pick a primary conversion goal.** Examples:
  - "Signed-up user who imported a job" (deep funnel — good signal)
  - "Signed-up user who finished CV builder + uploaded a photo"
  - "Free → Pro conversion within 14 days"
- [ ] **Decide budget envelope.** Sensible v1 split for DACH:
  - €500/month — Google Search Ads on "Lebenslauf bauen", "honest CV builder", "DACH job search tool"
  - €300/month — LinkedIn Ads to "Software Engineer in Berlin/Munich/Wien" (interest-based)
  - €0 — organic Reddit / Hacker News launch posts (see Social)
- [ ] **Wire UTM parameters into every paid ad** and verify they
  reach `analytics_events` (`channel`, `utm_source`, `utm_campaign`).
- [ ] **CAC calculation method documented** — what's "cost per
  signed-up user that imported ≥1 job" by channel?
- [ ] **Kill-switch criteria** — at what CAC do you pause each
  channel? (Suggest: pause when CAC > 3× monthly subscription price.)

**Eng surface:** analytics_events already records signups, imports,
applies. UTM source/campaign capture is implemented at signup. No
new code needed unless a specific channel requires server-side
tracking pixel.

---

## 2. Growth / SEO specialist

**What this role does:** earns free traffic from search engines and
inbound links.

**Operator checklist:**

- [ ] **Keyword research deliverable** — a CSV of ≥30 keywords
  ranked by (search volume × intent strength × difficulty).
  Examples to cluster around:
  - "ATS resume builder Germany" / "ATS Lebenslauf"
  - "honest CV builder" / "CV ohne KI-Halluzinationen"
  - "Lebenslauf Vorlage modern" / "Lebenslauf DACH"
  - "job search Berlin senior backend" (long-tail)
- [ ] **Sitemap + robots.txt** — engineering provides these; review
  what's included and what's excluded (excluded: `/api/*`, `/share/*` for now).
- [ ] **schema.org JobPosting markup** — verify our `/share/job/{id}`
  pages emit valid JobPosting JSON-LD. Use the [Google Rich Results
  Test](https://search.google.com/test/rich-results) on 3 share URLs
  before launch.
- [ ] **Content calendar** — list of ≥10 blog/landing-page topics
  (e.g., "How to write a Lebenslauf for a DACH role as a non-native
  speaker", "Why your CV gets rejected by ATS — and how to fix it",
  "The 5 skills DACH employers look for in 2026 data engineers").
- [ ] **Internal-linking strategy** — every blog post links to at
  least 2 product pages with the right anchor text.

**Eng surface:** the share URLs already emit metadata + canonical
links + JobPosting JSON-LD. The blog is NOT built yet — needs a
decision: ship a static `/blog/<slug>` route on app.py, or host
externally (Substack / Ghost) and link in.

---

## 3. Conversion rate optimization (CRO) specialist

**What this role does:** runs experiments to lift conversion rate at
each step of the funnel.

**Operator checklist:**

- [ ] **Funnel definition document** — every step from "landed on
  /" to "imported first job" listed with the analytics event that
  marks completion of each step.
- [ ] **Drop-off analysis tool** — once weekly, look at where users
  fall off. (Engineering provides `analytics_events`; the
  visualisation is operator-side — Looker Studio / Metabase / a
  Google Sheet pivot.)
- [ ] **A/B test infrastructure** — engineering will need to ship
  this if/when CRO has experiments to run. Until then, this is a
  zero-cost backlog item; not a launch blocker.
- [ ] **First-experiment hypotheses written down** — e.g., "the
  Settings → AI provider step has 60% drop-off; testing a 'skip for
  now' button will reduce drop-off by 20%".

**Eng surface:** analytics_events exists. A/B framework does NOT
exist; if the operator wants to run experiments before public launch,
that's an explicit add to the engineering backlog.

---

## 4. Brand designer

**What this role does:** owns the visual identity beyond the
functional UI.

**Operator checklist:**

- [ ] **Logo finalized** — current is a placeholder SVG. Needs a
  proper wordmark + icon mark in SVG + PNG @ 1x/2x/3x.
- [ ] **Color palette beyond dev tones** — currently the app uses
  generic dark-mode tones. Pick a brand accent color that also
  works for the CV's "Modern One-Page" template accent.
- [ ] **Empty-state illustrations** — small SVGs for empty queue,
  no companies watched, no imported jobs, no AI provider configured.
- [ ] **OG / Twitter card image** — single hero card the social
  meta tags reference.
- [ ] **Favicons** — 16/32/192/512 PNGs + Apple touch icon.

**Eng surface:** the app already has SVG icon slots throughout. Drop
new icons into `static/` and update the few references in
`static/index.html`. No code change beyond asset swap.

---

## 5. Content strategist / marketing copywriter

**What this role does:** writes everything the user reads outside
the product itself.

**Operator checklist:**

- [ ] **Landing-page copy** — currently the app's `/` is the signed-
  in product UI. We need a real marketing landing page with
  headline, value props, screenshots, a "Try free" CTA. Draft 3
  versions, pick one, run by 5 testers.
- [ ] **Email-nurture sequence** — at minimum:
  - Day 0 (welcome email — already shipped via `email_ingest`)
  - Day 3 (the bookmarklet pitch — already shipped)
  - Day 7 (skill-gap insight — needs operator copy)
  - Day 14 (Pro upgrade offer — needs operator copy)
- [ ] **In-product copy review** — every error message, every
  empty state, every button label. Ship a CSV of "current copy →
  proposed copy" for review.
- [ ] **Tone guide** — 1-pager: voice (direct, anti-corporate,
  DACH-pragmatic?), forbidden words, preferred words. Without
  this, copy drifts.

**Eng surface:** existing transactional emails are templated; copy
swaps are 1-line edits. Landing page is NOT built; needs a decision.

---

## 6. Email deliverability specialist

**What this role does:** makes sure transactional + nurture emails
land in the primary inbox, not spam.

**Operator checklist:**

- [ ] **SPF record** set for the sending domain (`v=spf1 include:_spf.resend.com ~all` for Resend; adjust for other ESPs).
- [ ] **DKIM key** rotated into the sending domain's DNS.
- [ ] **DMARC policy** at `p=quarantine` minimum; review the
  aggregate reports weekly for the first month.
- [ ] **Inbox-placement test** — send a verification email to each:
  Gmail, Outlook, iCloud, GMX, Web.de. Confirm primary inbox.
- [ ] **Unsubscribe link** present in every nurture email + the
  list-unsubscribe header. (Engineering: present on the daily-
  digest path; verify it works.)
- [ ] **Bounce-handling alerting** — if bounce rate > 2% for any
  send, get an alert.

**Eng surface:** transport is `Resend` by default; SMTP fallback is
wired. `EmailTransport` records bounce state. No new code needed
unless the operator changes ESPs.

---

## 7. Social media manager / native-content creator

**What this role does:** builds organic distribution and community.

**Operator checklist:**

- [ ] **Channel pick** — which platforms get real attention from us?
  My read: **LinkedIn** (DACH professional audience for the product),
  **Twitter/X** (tech-launcher community), **Reddit** (r/cscareerquestionsEU
  + r/cscareerquestions for organic mentions, NEVER spam — answer
  questions, drop product link only when asked).
- [ ] **Launch posts drafted** — 3 versions of "Show HN" / Reddit
  intro / LinkedIn launch with the "honest CV builder" hook.
- [ ] **Content calendar (first 30 days)** — 3 posts/week per
  channel. Mix: 30% "we shipped X", 30% career-advice / SEO content,
  30% user stories / testimonials, 10% memes / personality.
- [ ] **Response cadence** — every comment / DM / @-mention gets a
  human reply within 4h during launch week, 24h after.
- [ ] **Community guidelines** for tester Slack / Discord (if you
  set one up).

**Eng surface:** none. Pure operator/community work.

---

## Launch readiness gates (final go/no-go)

Before flipping public sign-up on (`DIRECTJOB_ALLOW_REGISTRATION=true`
on a public host), every line below must be true. If any are not,
**don't ship publicly — stay at 10 invited testers.**

- [ ] All 6 sections above have at least the "minimum-viable"
  checklist done (not all items, but the launch-critical subset).
- [ ] Engineering deferred backlog (separate doc) — Stripe billing,
  email deliverability live test, mobile/responsive, bookmarklet on
  real LinkedIn/Indeed pages, multi-day workflow — at least 3 of
  the 5 must be done.
- [ ] At least 3 invited testers report "I would tell a friend
  about this" unprompted.
- [ ] Daily digest has fired and landed correctly in real inboxes
  on at least 3 consecutive days.
- [ ] Backup + restore drill done at least once on production data.
- [ ] DPO sign-off on the DSGVO audit log + deletion request
  cascade (we run the deletion ourselves; verify it cascades).

When all of these are ✅, the operator decides launch date.