# The Cost-Saving Doctrine

**Status**: project-level design principle. Applies to every feature decision, every milestone, every public artifact.

**Why this exists**: To win institutional funding (NLnet, Sovereign Tech Fund, government budgets), and to win institutional adoption (Beratungsstellen, Jobcenter, university career services), the project must offer *value creation*, not *charity*. We do not ask funders or institutions to choose between helping people and saving money. We claim that this project does both simultaneously, and every feature is evaluated against that claim.

> **Measurement status (important)**: the euro figures and percentages in this document are *modelled projections* — built from per-instance mechanisms and publicly reported reference costs — not measured results from a live deployment. No institution has yet deployed the tool at caseload scale, so none of the savings below has been observed in production. They are stated as design intent and testable hypotheses so a reviewer can audit the *reasoning*; they will be replaced with measured numbers after the first partner-NGO pilot (Phase 2, per `ROADMAP.md`).

## Addressable population

Per Decision 21 in `04-research-and-decisions.md`, the doctrine's addressable population is **anyone facing structural friction in the European labor market** — not migrants alone. Migrants and EU-mobile workers are the most acute use case and provide the densest concentration of friction per user, which is why they are the strongest specific cost-saving evidence. The same mechanisms apply to career changers, returning workers after caregiving or extended absence, the long-term unemployed re-entering, returning expats, older workers facing implicit-bias filtering, and first-generation graduates without family-networked guidance.

The cost-saving math expands materially under the friction-class framing: a Jobcenter serves all Bürgergeld recipients, not only the migrant subset. The "advisor caseload" mechanism applies to every advisor-client interaction, not only migrant cases. "Multilingual built in" continues to save the migrant subset specifically; "shorter time-to-employment" applies across all friction classes. Where a specific mechanism applies most strongly to a sub-population, that is noted in the mechanism's description.

---

## The doctrine in one sentence

> **Every feature must reduce institutional operational cost while improving end-user outcomes. When the two diverge, the cost-saving path wins, with the user-outcome impact preserved through a smaller-cost-but-still-effective alternative.**

---

## The evaluation test

Before any feature is built or any milestone is committed, ask:

1. **Who pays for the equivalent work today?** (Advisor time, vendor licensing, manual translation, missed placements, etc.)
2. **What does this feature substitute or augment?**
3. **What is the per-instance saving?** (Hours, euros, error rate, cycle time.)
4. **At what scale does this save?** (One advisor, 10 cases per week, 700 MBE service points.)
5. **What is the user-outcome impact?** (Time to employment, application quality, agent satisfaction.)
6. **Is the cost-saving and outcome-improvement provable, or only plausible?**

A feature passes if it can answer 1–5 specifically and 6 with at least a credible plausibility argument.

A feature fails — and is dropped or deferred — if it only improves user outcomes without reducing institutional cost (we then ask: can we redesign it to do both?).

---

## The eight built-in cost-saving mechanisms

These are the specific ways Helpmefindthejob reduces institutional operational cost. Each is documented because each is a defensible claim in funding proposals and partner conversations.

### 1. Lower advisor caseload per case served

The migrant subset is the densest concentration of cases per advisor visit and is therefore the strongest specific evidence for this mechanism; the same mechanism applies more broadly to any advisor-client interaction in the friction class (Jobcenter caseloads with all Bürgergeld recipients, university career-service appointments, Beratungsstelle visits across all client types).

**How**: The agent handles routine queries (CV format, application tracking, common bureaucratic FAQ, "what should my motivation letter look like for a German Pflegedienst", "how do I follow up after an interview"). Trained advisors at MBE / JMD / Beratungsstelle / Jobcenter / university career services spend their time on cases requiring human judgement (complex Anerkennung paths, legal questions referred to lawyers, mental-health-adjacent situations, family-reunification timing, Wiedereinstieg programme planning, public-sector career-pivot guidance) rather than triaging CV format questions.

**Per-instance saving**: An MBE advisor session averages 60 minutes per visit and is fully booked. If the agent absorbs 20 minutes of routine work per visit, the advisor can serve 33% more clients with the same FTE allocation.

**At scale**: Across the nationwide network of Migrationsberatungsstellen (MBE) service points alone, even a 15% caseload reduction translates to thousands of additional clients served per year without hiring; the same mechanism applied across the autonomous Optionskommunen Jobcenter (operating Bürgergeld under §6a SGB II — a federal cap historically up to 110 — serving all Bürgergeld recipients, of which the migrant subset is one significant share) and the university career-service network materially compounds the addressable saving.

**Caveat**: This claim depends on the agent's outputs being *good enough* that advisors trust them. We measure this via the Week-3 partner-NGO pilot and refine accordingly.

### 2. Shorter time-to-employment

**How**: Better CV-to-role matching, structured application tracking, fit-score guidance, multilingual interview prep, all available in the user's home language. Reduces the trial-and-error cycle that currently lengthens unemployed periods.

**Per-instance saving**: Bürgergeld pays approximately €563 / month per single adult in 2026 (plus housing and ancillary costs). Every month of unemployment averted saves the state ~€1,000+ in direct welfare cost alone, with significant additional indirect costs (lost tax revenue, social-insurance contributions).

**At scale**: If the agent reduces average time-to-employment by even 30 days across a population of 10,000 served, the direct welfare-cost saving is in the tens of millions of euros annually. This number is plausibly conservative.

**Caveat**: Counterfactual measurement is genuinely hard — we cannot easily run a randomised trial. The honest claim is: *plausible significant reduction in time-to-employment, to be measured at the partner-NGO pilot stage with a before-after comparison.*

### 3. Zero per-seat licensing fees

**How**: The project is open-source under Apache 2.0. Institutions self-host on existing infrastructure. There is no per-user, per-advisor, per-client subscription.

**Per-instance saving**: Commercial alternatives (LinkedIn Talent Insights, SaaS career-platforms) commonly cost €15–€80 per user per month. For a Beratungsstelle serving 200 clients with 8 advisors, that range translates to €1,400 to €19,200 monthly recurring cost. Helpmefindthejob is €0.

**At scale**: A Jobcenter serving 5,000 clients with 50 advisors avoids €5–€50k per month of recurring software cost.

**Caveat**: There are hosting and IT-operations costs to running the open-source version. Those are real but typically a small fraction of the avoided licensing cost, especially with the Nix-flake-driven reproducible build (point 6 below).

### 4. No vendor lock-in

**How**: Apache 2.0 license, open standards (MCP, schema.org JobPosting, ESCO, EURES schema), BYO-AI provider abstraction, encrypted user data in standard formats, exportable user records.

**Per-instance saving**: Vendor switching costs in public-sector IT routinely run into tens of thousands of euros per migration. Avoiding lock-in means the institution never pays this.

**At scale**: Hard to quantify per-deployment, but vendor lock-in is one of the top three procurement risks public-sector IT decision-makers cite.

### 5. AI Act compliance built in

**How**: The project ships with a DPIA template, transparency notice, human-oversight UI, audit logging, explainability layer, technical documentation aligned with EU AI Act Annex IV. Institutions deploying the agent inherit a compliant configuration; they do not have to do the compliance engineering themselves.

**Per-instance saving**: A typical AI Act high-risk-system compliance project for an institution adopting AI in employment context costs €30–€200k in external consulting plus internal staff time. We make this cost zero (or near-zero — a deployer still needs to do the legal review specific to their context, but not the technical compliance engineering).

**At scale**: Multiplied across every institution that wants to use AI in employment in the EU after 2 August 2026, this is potentially the single largest cost-avoidance mechanism in the project.

**Caveat**: Our compliance pack is a template / reference implementation. Each deployer remains the legal operator of their instance and bears their own compliance accountability. We reduce the burden, we do not transfer it.

### 6. Reproducible build via Nix flake — lower IT-maintenance burden

**How**: A `flake.nix` ships with the project. Anyone deploying can reproduce the exact build, with pinned dependencies, deterministically. Reduces the "it works on my machine" debugging time, simplifies updates, makes security patches trivially auditable.

**Per-instance saving**: Public-sector IT operations are chronically understaffed (EU-wide). Reproducible builds reduce per-deployment maintenance hours by an estimated 30–60% over the lifetime of the deployment, based on industry data from NixOS-using institutions.

**At scale**: This addresses the named EU IT-workforce shortage directly. The cost saving is in avoided hires or avoided overtime across hundreds of deployment sites.

### 7. Multilingual built in — no separate translation budget

**How**: English + German shipped at v1; Arabic, Ukrainian, Turkish, Romanian on the post-grant language roadmap. Each language addition is a translation cost paid once, not a per-interaction translation-service cost.

**Per-instance saving**: Professional advisor-client translation services in Germany cost approximately €60–€120 per hour. An MBE service point that uses these for 5 hours per week pays €15,000–€30,000 per year.

**At scale**: Built-in multilingual support removes most of this recurring translation cost from institutional budgets, at the cost of a one-time translation contribution per language.

### 8. Faster Anerkennung pipeline

**How**: The agent walks foreign-credentialed users through the Anerkennung path (BIBB / Anabin reference, profession-specific routes, employer-recognition-friendly application strategies). Reduces the percentage of recognition applications that are filed incomplete, rejected, or delayed for missing documentation — and the percentage of qualified workers who give up on the process.

**Per-instance saving**: Each foreign-credentialed worker stuck in extended recognition limbo costs the state ongoing welfare payments + lost productive contribution. Faster recognition translates directly to earlier full employment.

**At scale**: Tens of thousands of foreign-credentialed workers are in active Anerkennung processes at any time in Germany. A small percentage acceleration is significant.

---

## The honesty rules

The cost-saving doctrine works only if the claims are honest. Two rules:

### Rule 1: Distinguish proven, plausible, and aspirational

- **Proven**: backed by measured data from this project or a published primary source. Most of our claims start aspirational and become proven as the partner-pilot data lands.
- **Plausible**: backed by a credible quantitative argument from related data (industry benchmarks, comparable open-source deployments). Most of the eight mechanisms above start here.
- **Aspirational**: a claim we intend to prove but do not yet have data for.

Every claim in a public artifact is tagged with which category it falls into. We do not present aspirational claims as proven.

### Rule 2: Acknowledge costs we add

The project is not free of cost to deploy. There are real costs:

- Initial deployment and configuration time (~4–8 hours of IT operator time)
- Hosting infrastructure (~€50–€200 per month for a Beratungsstelle-scale deployment)
- Ongoing security patching (~1–2 hours per month)
- Onboarding training for advisors (~2–4 hours one-time)
- Backup and disaster-recovery setup (~4 hours one-time)

These costs are real, named, and budgeted in every institutional deployment discussion. They are typically a small fraction of the costs avoided, but pretending they are zero damages credibility when an institution does their own ROI calculation.

---

## How the doctrine reshapes feature decisions

### Examples of feature decisions made under the doctrine

**Feature: "Auto-fit scoring for jobs to user profile."**
- Cost-saving: reduces advisor time spent reviewing job postings for fit; reduces user time spent on wrong-fit applications.
- Outcome: faster, better-targeted applications.
- Decision: **build**.

**Feature: "Premium AI provider with better suggestions."**
- Cost-saving: none — adds cost (premium API).
- Outcome: marginally better drafting.
- Decision: **drop**. Replaced by BYO-AI design where the user (or institution) chooses cost tier.

**Feature: "Standalone chat-only interface without journey state machine."**
- Cost-saving: none — adds variant to maintain.
- Outcome: lower friction for power users.
- Decision: **defer to Phase 2**, and only if a deployer requests it.

**Feature: "Audit logging of every AI invocation."**
- Cost-saving: large — required for AI Act compliance, which institutions otherwise pay consultants to implement.
- Outcome: enables institutional adoption and user-trust transparency.
- Decision: **build, scope to Week 2**.

**Feature: "Built-in video-call advisor handoff."**
- Cost-saving: ambiguous — saves advisor scheduling time but adds maintenance.
- Outcome: better handoff to humans when needed.
- Decision: **defer to Phase 2**. Use existing tools (Jitsi, BBB) for handoff in the meantime.

---

## How the doctrine appears in proposal narrative

When writing the NLnet application, every milestone deliverable is paired with its cost-saving mechanism. Example milestone phrasing:

> **Milestone 3: AI Act compliance pack.** Ship the DPIA template, transparency notice, human-oversight UI, audit logging integration, explainability layer, and technical-documentation pack aligned with EU AI Act Annex IV. **Cost-saving mechanism**: every institution that deploys the agent inherits a compliant configuration, avoiding €30–€200k of external-consultant work otherwise needed for high-risk-AI compliance under the AI Act effective from 2 August 2026.

Every milestone gets this treatment.

---

## Updating the doctrine

The doctrine evolves as we learn what institutions actually value. Update this document when:

- A pilot partner provides specific cost data we can substitute for plausibility arguments
- A new cost-saving mechanism emerges from feature work
- A previously-believed mechanism turns out to be incorrect (the doctrine permits — requires — admitting this)
- A funder or partner explicitly asks for a different framing

Append entries with dates below this line.

**2026-05-17**: doctrine drafted as part of the planning suite.
