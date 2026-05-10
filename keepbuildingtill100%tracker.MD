# Keep building till 100% — tracker

**Definition of "100%":** a stranger lands on khalo.org, signs up with email + password, gets onboarded, picks a plan if they want, uses the product daily, and we make money — same standard as any commercial SaaS.

Each item is one slice. Tick `[x]` when done. Order is rough; some can ship in parallel.

---

## Phase 0 — Pre-launch security & reliability

1. [ ] Flip `DIRECTJOB_ALLOW_REGISTRATION=true` on prod once ready (currently closed-off; admin-only)
2. [ ] CV / profile-text at-rest encryption (real envelope encryption, not the current XOR-with-secret-key)
3. [ ] Postgres migration decision: stay-on-SQLite (single droplet, accept downtime ceiling) or migrate (zero-downtime + multi-node ready)
4. [ ] Off-host backups proven: run a restore drill from S3 snapshot to a fresh droplet
5. [ ] Pen-test booked + delivered (Cure53 / Cobalt / Hackrate quote-shopping operator-side)
6. [ ] Production monitoring: Better Stack pipelines + 4-eyes alerts on healthcheck fail / 5xx spike / RAM > 80%
7. [ ] Rate-limit + brute-force protection re-verified end-to-end (login, signup, password-reset, AI calls)
8. [ ] Final legal review of Terms of Service, Privacy Policy, DPA — engage EU counsel
9. [ ] German Impressum (legal disclosure) page at `/impressum` — required by §5 TMG
10. [ ] GDPR data-deletion flow tested with real user (export → delete account → verify wipe)
11. [ ] Cookie banner audit — currently no third-party trackers, confirm no consent banner needed (or add one)
12. [ ] Privacy-first stance documented: no third-party analytics, no surveillance — leverage as a brand pillar

## Phase 1 — Marketing site & public landing

13. [ ] Buy / configure `khalo.org` apex DNS → marketing landing page (currently only `app.khalo.org` resolves)
14. [ ] Marketing copy: hero promise ("calm job tool"), 3 use-case sections, pricing, "anti-LinkedIn" positioning
15. [ ] Visual design: hero screenshot, animated UI loop, 3 product screenshots
16. [ ] SEO basics: per-page title + meta description + OpenGraph + Twitter card + sitemap.xml + robots.txt
17. [ ] Public job-alert SEO pages: e.g. `/jobs/data-engineer-berlin` rendered server-side from saved-search results, indexable by Google
18. [ ] Demo video (90s screen-recording walking through queue → bookmarklet → AI brief)
19. [ ] Press kit: logo PNG/SVG, screenshots, one-line description, founder bio
20. [ ] Sign-up CTA on every marketing page

## Phase 2 — Pricing & payments

21. [ ] Stripe Products: **Free** (no Stripe), **Pro €5/mo**, **Pro €40/year** (~33% off)
22. [ ] Stripe Customer Portal enabled — users self-manage subscription, see invoices, cancel without contacting us
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
32. [ ] Welcome email triggered on first sign-in
33. [ ] First-run wizard already shipped — verify edge cases (skip path, abort, resume on next session)
34. [ ] Demo data option: "Try it with sample jobs" button on empty queue → seeds 5 fake matched roles
35. [ ] Daily digest end-to-end test: user with saved search + cron run → email delivered
36. [ ] Web Push notifications end-to-end test: VAPID keys deployed → user opts in → real push received
37. [ ] Onboarding email drip: day-0 welcome, day-3 "set up bookmarklet", day-7 "did you find a role?"
38. [ ] Account-deletion email confirmation + 7-day grace period before hard delete

## Phase 4 — Differentiator features (the real moat)

39. [ ] Skill-gap atlas: extend `auto_fit` LLM prompt to extract 1–3 skills mentioned in the JD that are missing from the user's CV. Store as `imported_job.gaps`
40. [ ] Inline render: under the fit ring, show "Add **{skill}** to your CV → unlocks **N** more roles in your queue" with N = count of queue jobs requiring same gap
41. [ ] Aggregated skill-gap dashboard: one card on the Today view: "Top 3 skills holding you back across your queue"
42. [ ] Outcome tracking: per-application status timeline already exists. Add `replied_at` checkbox on the application form
43. [ ] Outcome analytics: render "Your reply rate is X%. Patterns: companies <50 people reply 3× more" once user has 5+ replies
44. [ ] CV variant attribution: every "Tailor CV" produces a saved variant. Track which variant gets replies. Recommend the winner for next role
45. [ ] Share-a-job public link: `/share/job/<id>` renders an SEO-indexable preview page with sign-up CTA. Owner can disable per-job
46. [ ] Referral program: each user gets `khalo.org/r/<token>` link. New signup via that link → both get 1 month Pro free
47. [ ] "Anti-LinkedIn" brand voice in marketing + in-app empty states ("calm by default", "no algorithm, no feed, no surveillance")

## Phase 5 — Help, support, transparency

48. [ ] Help docs site at `khalo.org/help` — at minimum: getting started, bookmarklet, AI modes, billing, GDPR
49. [ ] Contact form / `support@khalo.org` mailbox + 24h response-time SLA
50. [ ] Public status page (UptimeRobot / Better Uptime free tier) at `status.khalo.org`
51. [ ] Public changelog at `khalo.org/changelog` — auto-generated from git tags, surfaces real shipping cadence
52. [ ] In-app "What's new" toast for users who haven't logged in for >7 days

## Phase 6 — Launch readiness

53. [ ] Closed beta: invite 30–50 users (LinkedIn job-seeker network, indie communities), 2-week feedback window
54. [ ] Top-3 beta complaints fixed
55. [ ] Incident playbook: 1-pager of "what to do when prod goes down" — owner, rollback command, comms template
56. [ ] Customer-support inbox triage rules (Filip / Better Stack-style: SLA tagging, priority queue)
57. [ ] Public launch: Product Hunt + Hacker News "Show HN" + r/europe + r/cscareerquestionsEU + Indie Hackers
58. [ ] First-week monitoring: oncall rotation (or: solo with phone alerts), watch error rate + signup funnel + churn
59. [ ] Press: pitch to The Register / Heise / German tech press once we have a few hundred users

## Phase 7 — Post-launch growth & iteration

60. [ ] Set up product analytics (privacy-friendly: Plausible.io or self-hosted Umami) for signup funnel + activation
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
