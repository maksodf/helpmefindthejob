<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Nasser's Checklist — bureaucratic + vendor-relations tasks

**Audience**: Nasser (partner, non-coding role).
**Coordinator**: Fouad (dev side).
**Created**: 2026-05-21.

This file is the working checklist for the seven bureaucratic
items that block our institutional + commercial readiness. None
of these require writing code. Each one is a vendor, contract,
or partnership negotiation.

---

## ⚠ Read this before you start

### 1. Safety rules — what NEVER goes in this file

This file lives in our **public** GitHub repository. Anyone can
read it. That's fine for task descriptions, but the following
MUST NEVER appear here (or in any committed file):

- API keys, passwords, tokens, credentials of any kind
- Vendor pricing quotes (gives the vendor leverage if they see it)
- Draft contract clauses before legal review
- Names of NGO contacts or any other personal identifiers
- Internal financial information

Share those with me **out-of-band**:
- **Credentials**: 1Password share link OR encrypted email
- **Pricing / contracts**: email or a private channel
- **Personal contacts**: same — email or private message

### 2. How to update this checklist

Each task below has a **Status** line. When you make progress:

- Tick the appropriate checkbox: `[x]`
- Add a one-line note in the **Activity log** for the task
- Commit + push your edit (this creates the audit trail)

When you think a task is **done**:

- Change Status to `[x] Done — awaiting coder verification`
- I'll review against the Acceptance criteria + tick the
  **Coder verification** checkbox
- Only after both ticks is the task truly closed

### 3. How to ask me questions

Every task has a **Notes / questions from Nasser** section.
Write your question there, commit, and tag me in the commit
message. I'll answer in the same section in my next pass.

### 4. Priority order

Items 1-4 are the most time-sensitive (they have external lead
times we don't control). Items 5-7 are lower urgency.

Suggested attack order:
**1 → 2 → 6 → 7 → 3 → 4 → 5**

Reasoning: SOC 2 + pentest have 8-12 week vendor lead times,
start now. NGO pilot has 4-6 weeks of partnership courting.
SLA can be drafted in parallel. Reviews / skills / salary
licensing have shorter lead times and can wait until pilot
shape is clearer.

---

## 1. SOC 2 / ISO 27001 audit engagement

**Goal**: Sign an engagement letter with an EU-qualified auditor
for either SOC 2 Type 1 OR ISO 27001 Annex A assessment of
helpmefindthejob.

**Why it matters**: Institutional buyers (NGOs, Beratungsstellen,
public sector) won't deploy without one of these. The grant
positions us as institutional-deployment-ready; an audit
engagement signed (even if the audit hasn't completed) is the
signal we have.

**Steps**:

1. Decide: SOC 2 Type 1 (faster, ~3-month engagement) OR
   ISO 27001 Annex A (longer, ~6-month, more recognised in EU).
   My recommendation: **ISO 27001** for EU positioning, unless
   a US-based NGO partner specifically asks for SOC 2.
2. Research 3-5 EU-based audit firms. Avoid Big 4 unless we
   already have a relationship — boutique EU audit firms are
   cheaper + faster. Suggested search: "ISO 27001 auditor
   Germany boutique" + LinkedIn outreach.
3. Send each a short scoping email. Attach (a) our
   [THREAT-MODEL.md](docs/THREAT-MODEL.md), (b) our
   [SECURITY.md](SECURITY.md), (c) our
   [compliance/](compliance/) directory README.
4. Get **3+ written quotes** with: scope, timeline, fixed price,
   re-test clause, deliverable format.
5. Compare quotes; pick one.
6. Negotiate engagement letter. Get our lawyer to review.
7. Sign.

**Deliverable**:

- Signed engagement letter (PDF) — share via encrypted email
- Confirmed start date
- Auditor's primary contact name (share name only, not personal
  contact details, in the Activity log)

**Acceptance criteria** (Fouad will verify before marking done):

- ✓ Auditor is registered to issue ISAE 3000 reports for the EU
- ✓ Scope covers GDPR controls + EU AI Act Article 12 audit-log
  requirements
- ✓ Re-test clause included (so we don't pay full price for the
  remediation round)
- ✓ Deliverable format = PDF report with executive summary + per-
  finding remediation guidance

**Risks to avoid**:

- ❌ "Compliance theater" boutiques that just sell certifications
  without real testing — check their reference clients
- ❌ US-only auditors who can't issue EU-recognised reports
- ❌ Engaging without lawyer review of the engagement letter
- ❌ Disclosing pricing in this file

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## 2. External penetration test

**Goal**: Sign a Statement of Work with an EU-based pentest
vendor for black-box + grey-box assessment of our deployed app.

**Why it matters**: Gap #27 in our 40-item analysis. A pentest
finding (with remediation) is a strong credibility signal for
institutional buyers + NLnet review.

**Steps**:

1. Identify **3-5 EU-based pentest firms** with web-app +
   AI-system experience. Suggested starting list to research:
   Cure53 (Germany), SEC Consult (Austria), Recurity Labs
   (Germany), NCC Group (UK/EU). Check their published
   advisories for recent web-app work.
2. Send each firm our [THREAT-MODEL.md](docs/THREAT-MODEL.md)
   as the scoping document. Ask for a fixed-bid quote for:
   - Web app pentest (black-box, ~5 days)
   - AI-specific tests (prompt injection, model abuse, training
     data poisoning) — ~2 days
   - Optional grey-box / white-box delta (~2 days)
3. **Sign NDA before sharing the deployment URL** with any
   vendor. NDA template they provide is usually fine.
4. Get **3+ quotes**, compare.
5. Pick one; have lawyer review the SoW.
6. Sign SoW.

**Deliverable**:

- Signed NDA (PDF) — out-of-band
- Signed SoW (PDF) — out-of-band
- Confirmed pentest start date
- Deliverable format agreed (CVSS scoring + remediation guidance
  + retest in the price)

**Acceptance criteria** (Fouad will verify):

- ✓ Scope includes OWASP Top 10 + AI-specific tests
- ✓ Report format = CVSS + remediation guidance per finding
- ✓ Retest after our fixes is included (or fixed-price add-on)
- ✓ Vendor signs NDA + DPA before deployment URL is shared
- ✓ Vendor has published advisories from at least 2 prior
  engagements (proves they actually test)

**Risks to avoid**:

- ❌ Vendors who only do automated scanning (vs manual testing)
- ❌ Vendors who won't sign NDA before scoping
- ❌ Sharing deployment URL or staging credentials in this file
  or any commit
- ❌ Vendors based outside the EEA without an EU subprocessor

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## 3. Company reviews data licensing

**Goal**: Negotiate a commercial license + API access with a
company-review data provider (Glassdoor, Kununu, or Indeed).

**Why it matters**: Gap #6. Top-tier job search products show
company reviews + ratings. We have the integration shape; we
need the data source.

**Steps**:

1. Identify **3 candidate providers**: Glassdoor, Kununu
   (German market leader), Indeed. Skip LinkedIn (closed ToS
   for this use case).
2. Email each provider's partnerships / API team. Ask for:
   - API access for read-only company review data
   - EU-region data hosting (GDPR Schrems II compliance)
   - Tiered pricing for non-profit / civic-tech use
   - DPA template
3. Get **commercial quote + DPA + ToS** from each.
4. Lawyer review.
5. Sign whichever fits our budget + ToS.

**Deliverable**:

- Signed commercial agreement (PDF) — out-of-band
- Signed DPA (PDF) — out-of-band
- API credentials handed off **via 1Password share link** — NEVER
  paste credentials into this file or any committed file
- Pricing terms (for our records only, NOT for this file)

**Acceptance criteria** (Fouad will verify):

- ✓ Coverage includes German market (Kununu strongest here)
- ✓ DPA explicitly permits processing in EU + supports our
  controller role
- ✓ Rate limits sufficient for ~10k API calls / day at minimum
- ✓ ToS permits use within an aggregator product (some
  providers forbid this)

**Risks to avoid**:

- ❌ Pasting any API key, password, or token into this file
- ❌ Signing without lawyer review
- ❌ Providers without an EU-region option
- ❌ Providers whose ToS forbid aggregator use

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## 4. Skill assessment tests licensing

**Goal**: Negotiate a commercial license with a skill assessment
provider (Codility, TestGorilla, HackerRank, or open-source
alternative).

**Why it matters**: Gap #8. Lets users self-assess + employers
verify skills. Phase 2 product feature; the licensing has long
lead time so it makes sense to scope now.

**Steps**:

1. Decide commercial vs open-source first. Commercial options:
   Codility, TestGorilla, HackerRank for Work. Open-source:
   CodeRunner, OpenAssessment. **Recommendation: get quotes
   from 2 commercial AND evaluate one OSS option in parallel.**
2. For commercial: request demo, get pricing for ~1k user/month
   tier, get DPA + ToS.
3. **Specifically ask** about: bias-audit reports on their test
   bank (do they verify their tests don't systematically
   disadvantage any demographic?), data residency, retention
   period for completed assessments.
4. Lawyer review of DPA + ToS.
5. Sign.

**Deliverable**:

- Vendor comparison summary (pricing redacted) — out-of-band
- Signed commercial + DPA — out-of-band
- API credentials via 1Password
- Bias-audit report from vendor (if available) — out-of-band

**Acceptance criteria** (Fouad will verify):

- ✓ Test bank covers programming + language proficiency + soft
  skills relevant to our personas
- ✓ Vendor provides a bias-audit report OR has a documented
  bias-review process
- ✓ Data stored in EEA
- ✓ Retention policy is configurable (we want short retention)

**Risks to avoid**:

- ❌ Vendors with proven discriminatory bias in test bank
  (check news / academic literature before committing)
- ❌ Vendors with data outside EEA + no EU subprocessor
- ❌ Long-term contracts (start with 6-12 months max)

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## 5. Salary insights data licensing

**Goal**: Decide between free public datasets (Eurostat / OECD /
Destatis) and commercial data (Glassdoor / Levels.fyi) for
salary insights. Sign agreement if commercial.

**Why it matters**: Gap #4. Salary transparency is table stakes
for top-tier job search products. Public EU data may be enough.

**Steps**:

1. **Free-first audit**: research what Eurostat
   (https://ec.europa.eu/eurostat) + OECD + Destatis (Germany)
   already publish. Categories to look for: median salary by
   role + region + experience level.
2. Decide: free is sufficient OR we need commercial augmentation.
3. If commercial needed: email Glassdoor Economic Research,
   Levels.fyi, Payscale. Ask for licensing + DPA.
4. For free sources: document attribution requirements per
   dataset; many require "Source: Eurostat" footer.
5. Lawyer review (less heavy lift for free sources — usually
   just attribution language).

**Deliverable**:

- Data-source decision matrix: free vs commercial coverage per
  field (role / region / experience / industry)
- IF commercial: signed agreement + credentials via 1Password
- IF free: documented attribution requirements

**Acceptance criteria** (Fouad will verify):

- ✓ Covers German + at least 5 other EU member states
- ✓ Breakdown by role + region + experience level (at minimum)
- ✓ Update frequency at least quarterly
- ✓ Attribution / ToS permits use in an aggregator product
- ✓ For free sources: the dataset has been updated in the
  last 12 months

**Risks to avoid**:

- ❌ Scraping ToS-protected data (Glassdoor, LinkedIn, Indeed
  all prohibit scraping)
- ❌ Misrepresenting third-party data as our own
- ❌ Stale datasets (Eurostat has a lag of 1-2 years on some
  series — check before committing)

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## 6. NGO pilot — MOU + DPA

**Goal**: Sign an MOU + DPA with a German NGO that will run the
first pilot deployment of helpmefindthejob.

**Why it matters**: Gap #16 (NGO pilot) + Gap #17 (case studies)
+ Gap #33 (measured outcomes). All three depend on this. The
cost-saving doctrine stays at "aspirational" until we have one
real deployment generating real events.

**Steps**:

1. **Identify 3-5 candidate NGOs**. Strong fits:
   - Diakonie Deutschland — large welfare network
   - Caritas — Catholic welfare network
   - AWO (Arbeiterwohlfahrt) — social-democratic welfare
   - IQ Netzwerk — Integration through Qualification (perfect
     persona fit)
   - Regional refugee-support organisations (e.g.,
     Flüchtlingsrat Berlin, Hamburg's Integrationsbüros)
2. Initial outreach: short email introducing the project +
   linking to the public README + Trust Receipt + transparency
   dashboard. **Do NOT share NGO contact names in this file.**
3. Scope the pilot. Target shape: **50-200 end-users, 3-6
   months, free-of-charge to the NGO** in exchange for
   structured outcome data (apply rate, reply rate, time-to-
   interview, advisor hours saved).
4. Draft MOU. Use our
   [`compliance/dpa-template.md`](compliance/dpa-template.md)
   as the data-processing-agreement basis.
5. NGO's legal review.
6. Sign.

**Deliverable**:

- Signed MOU (PDF) — out-of-band
- Signed DPA (PDF based on our template) — out-of-band
- Pilot start date + end date
- Agreed outcome-measurement plan (which metrics, how often
  shared, by whom)
- Named pilot coordinator on NGO side (their name only, no
  personal contact in this file)

**Acceptance criteria** (Fouad will verify):

- ✓ Pilot covers ≥ 50 end-users
- ✓ Pilot runs ≥ 3 months
- ✓ Outcome measurement includes apply rate, reply rate, time-
  to-interview, advisor hours saved
- ✓ DPA is based on `compliance/dpa-template.md` or is
  functionally equivalent
- ✓ NGO's DPO has co-signed

**Risks to avoid**:

- ❌ NGOs without a DPO who can co-sign the DPA
- ❌ Sharing personal contact details in this file
- ❌ Pilots smaller than 50 users (won't produce statistically
  meaningful outcome data)
- ❌ Promising features we don't have yet

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## 7. SLA terms — drafted, legal-reviewed

**Goal**: Draft a service-level agreement template institutional
buyers can co-sign. We commit to specific uptime, response
times, and breach notification windows.

**Why it matters**: Gap #30. Institutional procurement requires
this. The SLA is a NEGOTIATING DOCUMENT — we promise what we
can actually deliver in Phase 1, not what we wish we could.

**Steps**:

1. Draft commitments at honest Phase-1 levels:
   - **Uptime**: 99.0% (not 99.9% — we don't have HA infra yet)
   - **Incident response**: critical = 4 business hours,
     non-critical = 2 business days
   - **Data backup**: daily encrypted backup, 30-day retention
   - **Breach notification**: 24 hours to controller, 72 hours
     to authority (matches DPA template)
   - **Support tiers**: community support free; paid support
     deferred to Phase 2
   - **Termination**: 30 days written notice
2. Lawyer review. Specific focus: don't accidentally create
   liability beyond what Apache 2.0 LICENSE allows.
3. Publish as `compliance/sla-template.md` in the repo.

**Deliverable**:

- Final SLA template — **commit to repo** at
  `compliance/sla-template.md` (this one CAN be public; it's a
  template not a signed instance)
- Lawyer sign-off (PDF or email) — out-of-band

**Acceptance criteria** (Fouad will verify):

- ✓ Uptime promise matches what we can deliver (no 99.99%)
- ✓ Breach notification windows match the DPA template
- ✓ Doesn't contradict Apache 2.0 LICENSE warranty disclaimer
- ✓ Doesn't promise features we don't have (24/7 on-call,
  dedicated CSM, etc.)
- ✓ Lawyer-reviewed

**Risks to avoid**:

- ❌ Over-committing on uptime
- ❌ Promising 24/7 support without on-call rotation
- ❌ Contradicting LICENSE warranty disclaimer
- ❌ Skipping lawyer review

**Status**: `[ ] Not started`
**Last updated**: ___

**Activity log**:
- ___

**Notes / questions from Nasser**:
- ___

**Coder verification (Fouad)**: `[ ]` Verified against acceptance criteria

---

## How to read the status across all 7 tasks

When all 7 tasks have both their `Status: Done` AND `Coder
verification` checkboxes ticked, this checklist is closed.

A quick visual scan: tick the boxes below as you close items.

- [ ] 1. SOC 2 / ISO 27001 audit engagement
- [ ] 2. External penetration test
- [ ] 3. Company reviews data licensing
- [ ] 4. Skill assessment tests licensing
- [ ] 5. Salary insights data licensing
- [ ] 6. NGO pilot — MOU + DPA
- [ ] 7. SLA terms — drafted, legal-reviewed

---

## Questions / open issues across all tasks

Use this as a global scratch space for questions that span
multiple tasks.

- ___
