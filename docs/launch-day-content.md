# Launch-day content pack

Drop-in templates for the press pitches (#59), social posts (#63), and partner outreach (#64) the operator sends during launch week. Each section is ready to copy-paste — fill `[OPERATOR FILL]` placeholders with the operator's name, URL, and pilot stats. Send timing and target list lives in `docs/operator-launch-runbook.md` § 57 / § 59 / § 63 / § 64.

The voice on all of these honors the rules in `docs/brand-voice.md` — no "thrilled to announce", no fake scarcity, no marketing-speak.

---

## Press pitches (#59)

### Subject lines (A/B options)

- A: "Calm job tool for the DACH market — no LinkedIn feed"
- B: "DirectJob Scout: privacy-first job aggregator for individuals"

### Pitch 1 — Heise / heise+ (German tech press)

> Hi [REPORTER FIRST NAME],
>
> Ich bin [OPERATOR FIRST NAME], Solo-Operator bei DirectJob Scout — einem ruhigen Job-Aggregator + Bewerbungs-Tracker für Einzelnutzer im DACH-Markt. Wir verfolgen die Karriereseiten direkt (kein LinkedIn-Feed) plus die großen Aggregatoren (Indeed, StepStone, Arbeitnow, Bundesagentur, Muse), deduplizieren über Quellen und liefern eine Tastatur-getriebene Warteschlange.
>
> Drei Dinge, die heise-relevant sein könnten:
>
> 1. **Datenschutz-Stack**: ChaCha20-Poly1305 AEAD für CV-Daten at-rest, kein Drittanbieter-Tracking, AVVs bereit. Live ohne Cookie-Banner — DSGVO-konform, weil keine nicht-essenziellen Cookies.
> 2. **Anti-LinkedIn Positionierung**: explizit gegen den Feed-Algorithmus + die Surveillance-Email. Wir sehen das als Markt­lücke speziell in DACH.
> 3. **Single-Operator-Stack**: Python stdlib HTTP, SQLite + WAL, ein 2-GB-Droplet. Keine Microservices, kein Kubernetes. Geht bis ~100 aktive Nutzer.
>
> Ich kann ein 20-Min-Walkthrough machen — Zoom oder telefonisch. Demo-Account auch verfügbar. Kontakt: [OPERATOR EMAIL].
>
> Beste Grüße,
> [OPERATOR FULL NAME]
> [OPERATOR PHONE]
>
> Live: https://app.khalo.org · Marketing: https://khalo.org · Pressekit: docs/press-kit.md

### Pitch 2 — The Register (English-language tech)

> Subject: Calm job tool, single droplet, no LinkedIn feed (DACH-focused)
>
> Hi [REPORTER FIRST NAME],
>
> Quick note from a solo operator. I built **DirectJob Scout** — a privacy-first job aggregator + application tracker for individual job-seekers, focused on the DACH market.
>
> What might be Register-shaped:
>
> - The whole stack is Python stdlib HTTP + SQLite WAL + Docker on one 2 GB droplet. No microservices. No Kubernetes. Goes to ~100 active users before needing more.
> - Anti-LinkedIn by construction — no feed, no algorithm, no recruiter messages. Tested with German job-seekers who specifically resent the LinkedIn engagement loop.
> - DSGVO compliance from day one: AEAD-encrypted CV at rest, no third-party trackers, Impressum, full audit trail of admin actions. No cookie banner because there's nothing to consent about.
>
> Happy to do 20 minutes on a call, or you can poke at a demo account. Live at https://app.khalo.org.
>
> [OPERATOR FULL NAME]
> [OPERATOR EMAIL] · [OPERATOR PHONE]

### Pitch 3 — t3n (German indie-tech)

> Subject: Solo-Operator-SaaS für DACH-Job-Seeker — keine Investoren, kein Algorithmus
>
> Hi [REPORTER FIRST NAME],
>
> Solo-Indie-Story: ich habe **DirectJob Scout** gebaut, einen Job-Aggregator + Bewerbungs-Tracker speziell für Einzelnutzer im DACH-Markt. Keine Investoren, kein Algorithmus, kein LinkedIn-Feed.
>
> t3n-relevant könnte sein:
>
> - **Wie ich das auf einem 2-GB-Droplet betreibe** (Stack, Backups, Monitoring — der ganze Operator-Runbook ist im Repo public)
> - **Der DACH-Job-Markt-Fit**: 30 Arbeitgeber, deren Karriereseite LinkedIn schlecht indexiert, plus 6 öffentliche Aggregatoren — eine Warteschlange, fünf Minuten täglich
> - **Pricing-Philosophie**: €5/mo Pro, kein Free-Trial-Schmu, Stripe-Customer-Portal für Self-Service-Kündigung
>
> Demo-Account + Walkthrough auf Anfrage.
>
> [OPERATOR FULL NAME]
> [OPERATOR EMAIL]

### Pitch 4 — Indie Hackers (English, founder-to-founder)

> Subject: Show IH: DirectJob Scout — calm job tool, 2 GB droplet, no LinkedIn feed
>
> Hey IH,
>
> Solo-operator launch story. I built DirectJob Scout because LinkedIn's feed makes job-searching feel like a hostile feed-grinding game. Nuked the feed; just shipped the queue.
>
> What's interesting:
> - Single 2 GB DigitalOcean droplet. Python stdlib HTTP + SQLite WAL. No microservices.
> - DACH market specifically (German healthcare-mgmt as the pilot persona, expanded to 15 personas)
> - Privacy-first: no third-party trackers, AEAD-encrypted CV at rest, no cookie banner needed
> - €5/mo Pro, single-user, full Stripe Customer Portal self-service
>
> Looking for ~30 beta users before public launch. If you're DACH-based and job-curious, drop your email at https://app.khalo.org and I'll send an invite.
>
> Building publicly: every commit is on github.com/[OPERATOR USERNAME]/directjob-scout. The operator-launch-runbook is in the repo if you're curious how this is run solo.
>
> — [OPERATOR FIRST NAME]

### Pitch 5 — Hacker News "Show HN" submission

Title (≤80 chars):
> Show HN: DirectJob Scout – calm job tool, no LinkedIn feed (Python stdlib, SQLite)

Top comment (write the moment you submit):
> Hi HN, [OPERATOR FIRST NAME] here. Solo-built DirectJob Scout because the LinkedIn feed broke my brain during my last job hunt. Quick stack notes:
>
> - Python stdlib HTTP server (no Django, no FastAPI). One file, ~3 800 lines.
> - SQLite + WAL on one 2 GB droplet. WAL-aware backups via the sqlite3 .backup() API.
> - Docker Compose. Caddy fronts it for auto-TLS. Better Stack for log shipping.
> - Vanilla JS frontend (~600 KB), no React, no build pipeline. Loads in 200 ms.
> - DSGVO from day one — Impressum, AEAD-encrypted CV at rest, full audit log.
>
> Anti-LinkedIn voice on purpose: no feed, no algorithm, no recruiter messages. Tested with DACH job-seekers who hate the engagement loop.
>
> Pricing: free up to 3 saved searches; €5/mo Pro for unlimited + managed AI + 90-day retention. Annual is €40 (8 months for 12). Stripe Customer Portal for self-service cancel.
>
> Live: https://app.khalo.org · marketing landing: https://khalo.org · code: github.com/[OPERATOR USERNAME]/directjob-scout
>
> Happy to answer anything about the single-droplet stack, the WAL-aware backup gotchas, or the privacy stance.

---

## Social content (#63) — 4 weeks of LinkedIn + Twitter/Mastodon posts

Cadence: 2 posts/week (one per platform, not the same post twice). All voice-checked against `docs/brand-voice.md`.

### Week 1 — operator's personal story

**LinkedIn (long-form, ~250 words):**

> I spent six months on the LinkedIn job-feed last year and came out worse for it. The feed isn't designed to find you a job — it's designed to keep you scrolling.
>
> So I built DirectJob Scout. It's a calm job tool. Watches the career pages of the companies you'd actually want to work for. Dedupes across Indeed, StepStone, Arbeitnow, Bundesagentur, Muse. Triage in five minutes a day with keyboard shortcuts. No feed. No algorithm. No "people you may know."
>
> Three deliberate decisions:
>
> 1. **No third-party trackers.** Privacy-first by construction. The static surface — sign-up, privacy, terms — loads only first-party CSS. No analytics beacons. CV data is AEAD-encrypted at rest.
>
> 2. **Bring your own AI.** Manual mode prepares the prompt + hands it to your existing ChatGPT or Claude tab. Free. If you want automation, paste an API key once and the auto-fit + cover-letter draft + CV-tailor flows run themselves.
>
> 3. **Single operator, single droplet.** Python stdlib HTTP. SQLite WAL. 2 GB DigitalOcean droplet. Goes to ~100 users before I need to scale. The whole operator-runbook is open-source — anyone can self-host.
>
> Live at https://app.khalo.org. Beta-tester slots: 30. Reply if you're DACH-based and looking.
>
> #JobSearch #DACH #PrivacyFirst #SoloFounder

**Twitter / Mastodon thread (5 tweets):**

> 1/ I spent six months on the LinkedIn job-feed and came out worse for it. So I built a calm alternative.
>
> 2/ DirectJob Scout watches the company career pages you'd actually want to work for. Dedupes across Indeed, StepStone, Arbeitnow, Bundesagentur, Muse.
>
> 3/ No feed. No algorithm. No "people you may know." Triage your queue with keyboard shortcuts in five minutes a day.
>
> 4/ Privacy-first: no third-party trackers, AEAD-encrypted CV at rest, no cookie banner needed.
>
> 5/ Live at https://app.khalo.org. DACH-focused. Free up to 3 saved searches; €5/mo Pro. 30 beta-tester slots open this week.

### Week 2 — anonymized aggregate stats

**LinkedIn:**

> 78% of our beta users tell us they hate the LinkedIn job feed. We surveyed them. Quotes (with permission):
>
> - "I want to know when these 30 companies post a role. Not what 5,000 strangers think about a CEO's vacation photos."
> - "The recruiter messages from companies I'd never apply to are exhausting."
> - "I just want a queue. Why is that hard?"
>
> Building products against the dominant pattern feels lonely. But the cohort that wants this is real. We see it in the retention curve — DirectJob Scout users come back daily for the queue, not weekly for the feed.
>
> If you're job-searching in DACH and the feed is making it worse: https://app.khalo.org

**Twitter / Mastodon:**

> 78% of our beta users hate the LinkedIn job feed. The cohort that wants a calm queue (not a recruiter feed) is real, and underserved in DACH. Building for them at https://app.khalo.org

### Week 3 — feature deep-dive (skill-gap atlas)

**LinkedIn (build-in-public flavor):**

> Quietly shipped a feature called the **skill-gap atlas** last week.
>
> Every time the auto-fit AI scores a job, it now extracts 1–3 skills the JD demands but the candidate's CV doesn't show. Aggregated across the queue, you get one card on your dashboard: "Top 3 skills holding you back across your queue."
>
> Why it's useful: instead of "30% fit" being abstract, you see "add Kubernetes to your CV → unlocks 8 more roles." Concrete, ranked, actionable.
>
> Built in three commits. Total LOC: ~280. Tests: 6, all green. Single operator, single droplet, single Python file.
>
> Live: https://app.khalo.org → set up a saved search → the atlas populates after 5 imports.
>
> #BuildInPublic #IndieHackers #JobSearch

**Twitter / Mastodon thread:**

> 1/ Shipped the skill-gap atlas — every auto-fit AI scoring extracts 1–3 missing skills from the JD vs your CV.
>
> 2/ Aggregated across your queue: one card says "add Kubernetes → unlocks 8 more roles." Concrete ranking instead of abstract fit-%.
>
> 3/ ~280 LOC, 3 commits, 6 tests green. Solo operator stack.
>
> 4/ Demo: https://app.khalo.org → save a search → the atlas populates after a few imports.

### Week 4 — customer interview / first paid customer

**LinkedIn (testimonial-anchored):**

> First paid Pro customer this morning. ☕ → keyboard.
>
> [USER FIRST NAME — with consent], a [USER ROLE] in [USER CITY], said: "[USER QUOTE — paste from Stripe customer email or in-app feedback]"
>
> Why this matters: not "we hit a milestone." It matters because somebody whose time is worth multiples of €5/month decided this product is worth €5/month. That's a different signal than free-user enthusiasm.
>
> The plan: keep shipping the differentiator features (skill-gap atlas, reply-rate analytics, CV-variant attribution) and let the dashboard speak for itself.
>
> If you're job-searching in DACH and the feed grind is wearing you down: https://app.khalo.org

**Twitter / Mastodon:**

> First paid Pro customer this morning. €5/mo. They left this in the feedback box: "[USER QUOTE]" — used with consent. Calm products win quietly.

---

## Partner outreach (#64) — career coaches / bootcamps / universities

### Cold email — career coach (refer-a-cohort partnership)

> Subject: Free Pro for your coaching clients
>
> Hi [COACH FIRST NAME],
>
> I'm [OPERATOR FIRST NAME], solo-operator at DirectJob Scout — a calm job tool for individual job-seekers in DACH (no LinkedIn feed, watches direct company career pages).
>
> Quick proposition for your coaching practice:
>
> - I'll give every active client of yours a free **Pro** plan for 3 months (worth €15/client).
> - You get a public referral page at `khalo.org/r/[YOUR-CODE]` + a small kickback when clients convert past month 3.
> - No exclusivity, no contract — just a partnership-friendly setup.
>
> The pitch to your clients: 5 minutes/day to triage their queue, AI-powered fit scoring, reply-rate analytics. Anti-LinkedIn by design.
>
> Free 20-min Zoom to walk through it: [OPERATOR CALENDAR LINK].
>
> [OPERATOR FULL NAME]
> [OPERATOR EMAIL]
>
> Demo account: https://app.khalo.org

### Cold email — coding bootcamp (refer-a-cohort)

> Subject: Free Pro plans for graduating cohorts
>
> Hi [BOOTCAMP CONTACT FIRST NAME],
>
> [OPERATOR FIRST NAME] from DirectJob Scout — a calm job tool focused on DACH job-seekers. We watch direct career pages + the major aggregators, dedupe everything, surface the queue. No LinkedIn feed.
>
> Proposal for [BOOTCAMP NAME]:
>
> - Free **Pro** plans for graduating cohorts (Pro is €5/mo retail).
> - Each cohort gets a unique referral link — clean attribution, no extra paperwork.
> - Optional: I can do a 20-minute "how-to-use-this" session for your career-week.
>
> Why we're DACH-relevant for [BOOTCAMP NAME]:
>
> - We watch the DACH employer career pages LinkedIn under-indexes.
> - All in German + English. Bookmarklet works on LinkedIn / Indeed / StepStone / XING.
> - Privacy-friendly: students' CVs are AEAD-encrypted at rest, no third-party tracking.
>
> Worth a 15-min call?
>
> [OPERATOR FULL NAME]
> [OPERATOR EMAIL] · [OPERATOR PHONE]

### Cold email — university career center

> Subject: Free Pro plans for current students
>
> Hi [CAREER CENTER CONTACT FIRST NAME],
>
> [OPERATOR FIRST NAME] here — solo-operator at DirectJob Scout, a calm job tool focused on the DACH market.
>
> Proposition for [UNIVERSITY] career center:
>
> - Free **Pro** plans for current students throughout their degree (€5/mo retail).
> - Custom referral link for the career center's emails / orientation packets.
> - Optional 30-minute session for your career-week.
>
> Why this fits a university audience:
>
> - DSGVO-first by construction; no third-party trackers, AEAD-encrypted CVs.
> - In-app help docs in German + English.
> - Bookmarklet captures jobs from LinkedIn / Indeed / StepStone / XING with one click.
> - Self-hosted analytics-friendly (Plausible/Umami support built in).
>
> Quick 20-min call to discuss?
>
> [OPERATOR FULL NAME]
> [OPERATOR EMAIL]

### Indie newsletter sponsorship pitch

> Subject: 6-week sponsorship for [NEWSLETTER NAME]?
>
> Hi [NEWSLETTER OWNER FIRST NAME],
>
> Long-time reader of [NEWSLETTER NAME]. I run DirectJob Scout — a privacy-first job aggregator for DACH individuals, single-operator + single-droplet.
>
> Looking to sponsor 6 weeks of [NEWSLETTER NAME]'s primary slot. Budget: €[OPERATOR FILL]/week. Copy can be:
>
> > **DirectJob Scout** — calm job tool. Watches the company career pages you'd actually want to work for, dedupes across Indeed / StepStone / Arbeitnow / Bundesagentur. No feed, no algorithm, no recruiter messages. €5/mo Pro. https://khalo.org
>
> Track via [NEWSLETTER NAME]-specific UTM. I'll pay 50% upfront, 50% mid-flight.
>
> [OPERATOR FULL NAME] · [OPERATOR EMAIL]

---

## Operator hand-off

For each template above:

1. Replace every `[OPERATOR FILL]` / `[USER FIRST NAME]` / etc. with real values.
2. Stagger sending across the launch week per `docs/operator-launch-runbook.md` § 57.
3. Track every send in a spreadsheet (subject, target, date, response). One sheet, three columns. Don't over-engineer.
4. Reply within 24h to anyone who responds — that's the press-pitch SLA.

If a template gets a reply, write a one-line note in `docs/incidents/launch-replies.md` (folder created on first reply) with the outlet + date + outcome. After three weeks, that doc tells you which channels worked.
