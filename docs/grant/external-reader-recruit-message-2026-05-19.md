<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# External-reader recruit message — paste-ready

This file is a paste-ready message for the maintainer to send to a
trusted external reader who can do a cold-clarity pass on the
NLnet application draft at
[`application-draft-2026-05-19.md`](application-draft-2026-05-19.md).

**Per §4.4 sub-task 4 of `02-execution-plan.md`**: NLnet's
guide-for-applicants assessment criteria weight Relevance/Impact
40% — the most-rewarded thing the application can do is read as
honest, specific, and convincing to a reviewer with no prior
context. The cold-clarity pass is the maintainer's last
opportunity before submission to surface what reads off.

Paste structure below. The maintainer fills `[Reader name]` +
`[Maintainer name]` + `[Maintainer email]` + the actual project
URL once GH Pages is live. Tone is calibrated to be light + low-
pressure; the reader is doing a favour, not a chore.

---

## Paste-ready message

```
Subject: Quick favour — read 10k words of a grant draft cold and tell me what reads off?

Hi [Reader name],

Hope you're well. I'm reaching out for a small favour with a real deadline.

I've spent the last four weeks getting an open-source project — Helpmefindthejob —
into shape for a grant submission to NLnet (the EU's Next Generation Internet
funder). The project is a civic-employment commons for the European labour
market: think a calm, multilingual, privacy-preserving job-search copilot
designed specifically for people facing structural friction. Aïcha (Tunisian
nurse, §16d Anerkennung in Berlin), Käthe (German nurse returning after a
12-year caregiving gap) — the same hospital-ward role is open for both, and
the friction is bureaucratic and CV-shape, not capability. The architecture
is friction-driven, not migrant-only.

The grant ask is €37k across 6 milestones for the work already shipped during
the sprint plus the remaining institutional readiness (Conservancy admission,
letters of support, final outreach). Deadline is 2026-06-01 12:00 CEST —
twelve days from when I'm writing this.

I have a draft of the application body and I'm about to submit it. But
**you've never seen this project before**, and that's exactly what the NLnet
reviewers will be — strangers reading it cold. I'd love your read.

**The ask**

Could you spend ~1 hour reading the application draft and telling me
what reads off? Specifically NOT a copy-editing pass — I'm not chasing
typos. Focus on:

  * **Where does it not make sense?** Anywhere you stop and re-read because
    you've lost the thread.
  * **Where does it over-claim?** Anything that reads like marketing or
    promises more than the project can deliver. Be ruthless — the project
    is pre-launch, there's one private tester, zero paying users.
  * **What would a fair-but-skeptical reviewer push back on?** Sections
    where you can imagine someone saying "wait, how do you actually know
    that?" or "this sounds aspirational, not backed."
  * **Where does it drag?** I wrote ~10k words across 22 form fields.
    Some sections will be tighter than others. Tell me what feels padded.

**Output format**

Inline-comment-style notes, a brief list, or just a Slack/email reply with
"around the budget section the 'cost-saving doctrine' line sounds too pat" —
whatever's natural for you. **Specific sentence + concern beats "section X
feels off."** Suggested fixes welcome but not required.

**Timeline (gentle)**

If you can get me feedback by **2026-05-25**, I can fold it in and submit
by 2026-05-30 with comfortable buffer before the 2026-06-01 12:00 CEST
deadline. If that doesn't work — no pressure. Whatever fits.

**Where to read it**

  [Maintainer fills: GitHub link to docs/grant/application-draft-2026-05-19.md
   OR the live docs-site URL once Pages serves it OR an exported PDF
   attached to the email]

If you want to skip context and just dive in, the most useful sections
are Field 9 (Abstract — ~200 words), Field 12 (Budget usage — the
six-milestone breakdown), and Field 14 (Project comparison — the
13-row capability matrix). Those are the highest-stakes; the others
are evidence-attached.

If you'd rather not, that's completely fine — just say so and I'll
recruit someone else. No awkwardness either way.

Thank you for considering. I genuinely don't have a better idea than
"someone with no project context reads it cold," and you're someone I
trust to tell me the truth.

Talk soon,
[Maintainer name]
[Maintainer email]
```

---

## Notes for the maintainer

1. **Pick a reader who will tell you the truth**, not someone who'll
   say "looks great" out of friendship. The reviewer audit of the
   §4.4 closeout flagged that the draft is ~10k words; that risk
   gets dramatically lower if a real outside reader pushes back on
   what feels padded.
2. **Don't ask for a copy-edit**. Copy-editing is later. This pass
   is for clarity + over-claim detection + reviewer-pushback
   anticipation.
3. **Skim feedback works**. If your reader reads the abstract +
   budget + project-comparison sections only and tells you those
   three are strong/weak, that's enough signal. They don't need to
   read the verification table.
4. **Two readers > one**. If you have time, ask two people. They
   surface different things.
5. **The 1-hour estimate is optimistic**. A careful reader spends
   2–3 hours. Set expectations honestly: "I'm budgeting 1 hour of
   your time, expect 2 if you go deep, no pressure either way."
6. **Don't send the cosign + SBOM + accessibility evidence
   attachments unless the reader asks**. Most outside readers won't
   know what to do with them; the application body cites them
   inline.

## When to skip the external read

Per the PART 7 "what is NOT in scope" note + the application-
draft adversarial-self-review #2 in the §4.4 closeout: the external
read is **strongly recommended but not strictly required**. If the
maintainer cannot recruit a reader within ~5 days of submission, the
acceptable fallback is:

- Self-review the draft against the NLnet Guide-for-Applicants
  scoring criteria (30% Technical / 40% Relevance-Impact / 30%
  Cost-effectiveness, pass threshold 5.0/7.0); ask "would this hit
  5.0 from a cold reader?"
- Re-verify the 2 still-flagged numbers in the verification table
  (~46,000 healthcare unfilled + ~700 MBE) via the maintainer's
  own primary-source check.
- Submit with the honest framing intact (pre-launch, projected
  cost-saving, friction-class architecture, etc. as written).

The external read maximises the application's review score; the
self-review fallback is acceptable if recruitment doesn't land in
time.
