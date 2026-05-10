# Brand voice

Solo-operator product, DACH market, calm-by-default. This is the in-app + marketing voice. Hold the line.

## What we are

- **Calm.** No urgency banners, no countdown timers, no "🚨 NEW" labels.
- **Direct.** Plain noun-verb sentences. If you can cut a word, cut it.
- **Honest.** No fake scarcity, no fake testimonials, no fake celebrity endorsements, no fake "join 10,000+ developers" until it's true.
- **Anti-LinkedIn.** Specifically. We say "no feed, no algorithm, no surveillance" because LinkedIn does the opposite of all three.
- **DACH-aware.** German users are skeptical of marketing-speak. Hyperbole reads as hostile, not enthusiastic. Translate idioms; don't translate cadence.

## What we are not

- We are not "thrilled" to announce things. People announce things. Adults can say "we shipped X" without performing emotion.
- We are not building a community. The product is a queue, not a forum.
- We are not in your inbox uninvited. Daily digest is opt-in, capped, and unsubscribable from a one-click link.
- We are not your hustle-coach. We don't tell users to "level up", "10x", "grind", or "manifest". They are looking for a job, not a personality transplant.

## Vocabulary

| Use | Avoid |
|---|---|
| "queue" | "feed", "stream", "experience" |
| "saved search" | "personalised feed", "curated for you" |
| "discovered jobs" | "matches", "opportunities" (too LinkedIn) |
| "Find me jobs" | "Discover your next career move" |
| "Reply rate" | "Engagement rate", "open rate" |
| "Sign up" | "Get started today", "Claim your spot" |
| "Free" | "Free forever", "$0 → $$$" |
| "Cancel any time" | "Risk-free trial" |
| "operator" | "founder", "CEO" (we don't have a CEO; we have a person who runs the server) |

## Empty states

Empty states tell the user **what to do next**, never **what they're missing**. Pattern: short factual title + one-sentence sub + one CTA. Skip motivational filler.

Good:
> Your queue is empty. Tell us what you want.

Bad:
> Don't worry — your dream job is just a click away! 🚀

## Error messages

State the problem. Suggest one action. No "oops" / "yikes" / "uh-oh". No emoji.

Good:
> Login limiter caught your IP. Try again in 10 minutes.

Bad:
> Oops! Something went wrong on our end. Please try again later! 🙈

## Marketing pillars (for the apex landing once #13 ships)

1. **Calm.** Bullet for: no algorithmic feed, no notification spam, no engagement loop.
2. **Direct career pages.** Bullet for: we watch the company sites you'd actually want to work for.
3. **Bring-your-own AI.** Bullet for: manual mode is free; BYOK lets your own ChatGPT subscription do the heavy lifting; managed-AI is opt-in.
4. **Privacy-first.** Bullet for: no third-party trackers; CV stays encrypted at rest; export + delete in one click.
5. **DACH-native.** Bullet for: German UI, Bundesagentur + StepStone + Arbeitnow ingest, Impressum + DSGVO from day one.

## Anti-pillars (do not invoke even sarcastically)

- "AI-powered" — you can mention AI as a feature, never as a marketing pillar.
- "Powered by GPT-X / Claude X" — provider name belongs in settings, not on the landing page.
- "Built in public" / "100x productivity" / "side hustle" — wrong audience.
- "We use AI to..." — say *what* you do, not which mascot powers it.

## Examples in the wild

These already follow the voice — preserve them when refactoring:

- Queue empty subhead: lists the actual aggregators we watch, not "we look everywhere".
- Privacy page section "Privacy-first by default": six concrete bullets, no abstract claims.
- Help → AI modes: literally "your choice, your billing".
- Status pill: hides on "Ready"; only surfaces on degradation.

## When in doubt

If a sentence would make a German engineer roll their eyes, cut it. If it could be on a SaaS landing page from 2017, cut it. If it works in a terminal log without sounding strange, ship it.
