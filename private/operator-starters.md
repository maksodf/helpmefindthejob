# Operator starters — concrete drafts to iterate on

Companion to `docs/operator-launch-playbook.md`. The playbook lists
WHAT each operator-side domain needs; this file ships STARTER DRAFTS
for each so you can red-pen rather than start from blank page. Each
section's content is "first-draft, replace with your voice" — but it
is engineering-tested-safe (no broken references, no dead links).

## 1. Performance marketing — first-month media plan

**Budget hypothesis (kill if CAC > €15 after week 2):**

| Channel | Monthly | Targeting | KPI |
|---|---:|---|---|
| Google Ads (Search) | €500 | "Lebenslauf bauen", "ATS resume builder Germany", "honest CV builder" | Cost per signup + imported job |
| LinkedIn (Sponsored Content) | €300 | Job title: Software Engineer / Data Scientist; location: Berlin, Munich, Vienna, Zurich | CTR + signup |
| Reddit (organic only) | €0 | r/cscareerquestionsEU, r/de, r/Berlin job-search threads — answer questions, drop link only when relevant | Referrer signups |
| Hacker News launch post | €0 | "Show HN: honest CV builder that refuses to lie for you" | Front-page hours + signups |

**Kill switch:** if CAC > 3× monthly subscription price after 14 days,
pause that channel. Document why in `docs/operator-decisions/`.

## 2. Growth / SEO — keyword cluster (Round-1 picks)

These cluster around the "honesty" angle since that's our differentiator
no competitor can claim:

| Keyword | Intent | Difficulty (Ahrefs-ish) | Notes |
|---|---|---:|---|
| `lebenslauf ohne ki halluzinationen` | Differentiator | Low | Direct match for our headline |
| `honest cv builder` | Differentiator | Low | English variant |
| `ats lebenslauf vorlage` | Commercial | Medium | Standard DACH-CV intent |
| `cv builder dach jobs` | Commercial | Low | Geographic + product |
| `senior backend engineer berlin lebenslauf` | Long-tail | Low | High-intent SEO traffic |
| `lebenslauf foto position` | Informational → product | Low | Educational content → CV builder |

**Content pillars to write (start with 3):**
1. *"Warum dein CV von der KI abgelehnt wird — und wie du das verhinderst"* (DE)
2. *"DACH vs. US CVs: 7 Unterschiede die du kennen musst"* (DE)
3. *"The honest CV builder pitch — why we refuse to invent your career"* (EN)

## 3. CRO — first-week experiments

Hypotheses worth testing once we have ≥100 signups:

| Hypothesis | Metric | Direction |
|---|---|---|
| Removing the AI-provider step from onboarding lifts CV-builder completion by 20% | Wizard completion rate | Up |
| Showing a "10 testers built CVs this week" badge on the landing page lifts signup CTR | Signup conversion | Up |
| Switching the primary CTA from "Create account" to "Build my CV" lifts CTR by 15% | Hero-CTA clicks | Up |
| Showing the photo upload BEFORE the summary section reduces wizard abandonment | Section drop-off | Down |

We do NOT have the A/B framework yet. Engineering ships it when 1+ of
these hypotheses become urgent — until then, list lives here.

## 4. Brand — minimum-viable identity

**Color palette (starter — replace with brand designer's pick):**
- Primary accent: `#7c5cff` (current dev purple — used in CV "Modern One-Page" template)
- Surface: `#171924` (current dev dark — engineering won't touch this without your sign-off)
- Text primary: `#e6e7ed`
- Subtle border: `#2a2b36`
- Error / warning: `#ff6b6b`

**Logo:** placeholder SVG in `static/icons/icon.svg`. Brand designer's
job to ship a real wordmark + icon-mark; engineering swaps the file.

**OG card:** none yet. Operator ships a 1200×630 PNG to
`static/icons/og-card.png`; engineering wires the meta tags.

## 5. Content / copywriter — first-week deliverables

**Landing page hero (3 versions to A/B):**
1. *"The honest CV builder. It refuses to lie for you."*
2. *"Your job search, your CV, your facts. We just help you find roles."*
3. *"Built for DACH. Photo top-right, dates in TT.MM.JJJJ, never invents."*

**Email-nurture sequence (5 emails — copy-edit before sending):**

- **Day 0 — welcome.** Subject: *"Your DirectJob Scout account is live."* — already wired (`email_ingest.py`). Operator copy-edits.
- **Day 1 — first action.** Subject: *"Build your CV in 6 minutes."* — NEW; targets users who registered but didn't open CV Builder.
- **Day 3 — bookmarklet pitch.** Subject: *"Capture LinkedIn / Indeed jobs in one click."* — already drafted in code.
- **Day 7 — skill-gap insight.** Subject: *"3 skills that unlock 8 more roles in your queue."* — needs operator copy.
- **Day 14 — Pro upgrade.** Subject: *"You've imported N roles. Here's what Pro unlocks."* — needs operator copy.

## 6. Email deliverability — pre-launch DNS checklist

For sending domain `mail.khalo.org` (replace with your actual subdomain):

```
mail.khalo.org IN TXT "v=spf1 include:_spf.resend.com ~all"
resend._domainkey.mail.khalo.org IN TXT "<the DKIM key Resend gave you>"
_dmarc.mail.khalo.org IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@khalo.org; pct=100"
```

**Pre-launch checklist:**
- [ ] SPF / DKIM / DMARC records propagated (use `dig +short txt`)
- [ ] Send a test welcome email to Gmail, Outlook, iCloud, GMX, Web.de — primary inbox in all 5
- [ ] Verify `list-unsubscribe` header lands on the nurture emails (`grep` the email module)
- [ ] Bounce-monitoring alert configured (Resend dashboard → bounce rate > 2% → email + Slack)

## 7. Social media — launch-week content calendar

**Day 0 (Launch day):**
- LinkedIn: *"Today we launched DirectJob Scout — a job-search tool that..."* (founder voice; under 200 words)
- Twitter/X: 3-post thread on the "honest CV builder" pitch + screenshot
- Hacker News: "Show HN" post, no marketing fluff, link directly to the demo
- Reddit (r/cscareerquestionsEU): launch-share post — clearly marked as creator, link to free tier

**Day 1–7 (every weekday):**
- 1 LinkedIn post — career-advice angle, link to a blog article
- 1 Twitter post — engineering / product-detail screenshot
- Reddit: ONLY in answer to specific questions; never as a top-level promotional post

**Response cadence:**
- Every @mention / DM / Reddit comment: replied within 4h during launch week, 24h after.
- Founder personally signs off on first 20 testimonial requests.

---

## How to use this file

1. **Don't edit the playbook (`operator-launch-playbook.md`) directly** —
   it's the meta-doc of what each domain needs. This file is your
   working scratchpad.
2. Red-pen each section as you complete the work. Move done items to
   `docs/operator-decisions/<date>.md` so we have a record.
3. Engineering will swap any concrete deliverable (logo, OG card,
   landing-page copy, DNS records) on request — just open an issue
   or ping me with the file/asset.

**None of this content is engineering-blocking.** The product ships
defensibly to 10 testers TODAY. Everything in this file is what stands
between "10 testers" and "public Twitter/HN drop."
