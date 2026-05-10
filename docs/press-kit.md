# Press kit — DirectJob Scout

For tech press, indie-news outlets, and Mastodon-curious editors.

## One-line description

DirectJob Scout is a calm job tool. Watches direct career pages, dedupes across aggregators, and triages your queue without the LinkedIn feed.

## Two-paragraph description

DirectJob Scout is a self-hosted job-aggregator and application tracker for individuals — not a B2B HR platform, not an ATS. It watches the company career pages you actually want to work for, plus six free public aggregators (Adzuna, Arbeitnow, Bundesagentur, Muse, Brave Web Search, an email-forward inbound rail), dedupes the queue across sources, and gives you keyboard-driven triage (`j`/`k`/`a`/`x`) instead of a recruiter feed.

It is privacy-first by construction: no third-party trackers, no analytics beacons, no algorithmic ranking, no surveillance email. Your CV stays on the operator's server (encrypted at rest with ChaCha20-Poly1305 AEAD). AI handoff is provider-neutral — manual mode, bring-your-own-key, or managed (waitlist). Built on Python stdlib + SQLite + Docker, hosted on a single 2 GB DigitalOcean droplet. Runs in production at https://app.khalo.org.

## Who built it

Solo operator with AI pair-programming, DACH market focus, German-first localisation, single-developer cadence. Operator name + bio: [OPERATOR FILL].

## What's distinctive

- **No LinkedIn feed.** No "people you may know," no algorithm, no engagement loop. Just the queue.
- **Bookmarklet rail for gated platforms.** LinkedIn / Indeed / StepStone / XING block server-side scraping. Our bookmarklet runs in your own logged-in browser, captures URL + title, returns you to the same tab. Compliant with the platforms' ToS by design.
- **Source-merging dedup.** A job posted on Indeed AND on the company's own site collapses to one row, but with `also_seen_at` showing both sources. Same role in DE + EN merges via a small role-glossary fold.
- **Cross-locale freshness.** A role re-found yesterday on a new aggregator but originally seen 4 months ago ranks as today-fresh — `effective_freshness_at = max(discovered_at, max(also_seen_at[*].seen_at))`.
- **Keyboard-first.** Vim-style shortcuts on the queue (`j`/`k`/`a`/`e`/`x`/`?`), Cmd-K command palette, focus-visible audit, `prefers-reduced-motion` honoured.
- **Manual AI mode.** We prepare the prompt and the input. You paste into your existing ChatGPT subscription. Free. (BYOK and managed-AI paths exist.)

## Quotable claim

> "We don't sell ads, attribute clicks, run an algorithmic feed, or charge a recruiter to put a job in front of you. The product is the queue. The customer is you."

## Technical claim sheet

- Stack: Python stdlib HTTP + vanilla JS + SQLite + Docker Compose + Caddy.
- No third-party scripts at load time on the static surface.
- Strictly-necessary cookies only; no DSGVO consent banner needed (audit at `docs/cookie-audit.md`).
- AEAD-encrypted CV text at rest (ChaCha20-Poly1305).
- WAL-aware backups via `sqlite3 .backup`, off-host to S3-compatible storage, restore drill rehearsed every release.
- 130+ tests; i18n parity gate in CI.

## Logo + brand

- Primary logo: SVG mark + wordmark (lives in `static/icons/` once final asset is supplied; current placeholder is the violet "D" square).
- Primary colour: `#7c5cff` (violet).
- Typography: Inter + system-font fallback chain (no third-party font CDN).

[OPERATOR FILL: 1–2 production screenshots of the queue + the Application form. PNG, 1600×1000.]

## Links

- Live app: https://app.khalo.org
- Marketing landing (planned): https://khalo.org
- Help: https://app.khalo.org/help
- Changelog: https://app.khalo.org/changelog
- Privacy: https://app.khalo.org/privacy
- Impressum: https://app.khalo.org/impressum

## Press contact

[OPERATOR FILL: name] · [OPERATOR FILL: email — typically `press@khalo.org`] · [OPERATOR FILL: signal/telegram if you offer it]

## Outlets to pitch

- **Heise Online / heise+** — German tech audience, will cover privacy-first SaaS narratives.
- **The Register** — Loves anti-trend tooling and self-hosted alternatives.
- **t3n** — German indie-tech / startup readership.
- **Indie Hackers** — Builders who appreciate solo-operator stories.
- **Hacker News (Show HN)** — Submit at the right moment with a substantive comment from the operator. Don't pitch HN; submit + show up.
- **r/cscareerquestionsEU** — Real users hunting jobs in the DACH market.
- **r/europe** — When localised correctly, gets traction.
- **EU/DACH Mastodon** — `@operator@<instance>` post + crosspost the launch thread.

## Pitch templates

### Cold press email (50 words)

> Subject: Privacy-first job tracker, no LinkedIn feed
>
> Hi <name> — I built DirectJob Scout, a self-hosted job aggregator + application tracker for individuals. No tracking, no algorithm, no recruiter feed — just the queue. Live in DACH at app.khalo.org. Demo + screenshots attached. Happy to do a 20-minute call if useful.
>
> [Operator]

### Show HN headline

> Show HN: DirectJob Scout — calm job tool, no LinkedIn feed, runs on a 2 GB droplet

### Tweet / Mastodon (200 chars)

> Built DirectJob Scout — a calm job tool. Watches the career pages you'd actually want to work for, dedupes across 6 aggregators, no algorithmic feed, no surveillance. Self-hosted, DACH-first. https://app.khalo.org

## Don't pitch

- Mass-personalisation tools that wouldn't read the actual feature set.
- Outlets that monetise via affiliate placement on job ads — conflict of interest.
- Recruiter-press — wrong audience; we are explicitly not a recruiter product.
