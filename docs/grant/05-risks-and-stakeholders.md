# Risk Register and Stakeholder Map

**Status**: living document. Review at the start of each execution week. Update when a risk crystallizes, a mitigation succeeds, or a new stakeholder is identified.

This document combines two related strategic artifacts because they shape each other:

- **The risk register** lists everything that could go wrong and how we mitigate or accept it.
- **The stakeholder map** lists everyone whose action or non-action affects the project, what we need from them, and how to engage them.

---

## Part A — Risk Register

Risks are scored on two axes:
- **Likelihood**: how probable. Low / Medium / High.
- **Impact**: severity if it materialises. Low / Medium / High / Critical.

A risk is **Critical** if it can sink the application or the project entirely.

### R1 — Application deadline mismatch (Likelihood: High, Impact: Critical)

**Risk**: Maintainer believes the deadline is "4 weeks from now"; actual NLnet call 13 deadline was 1 June 2026 (only ~2 weeks from 2026-05-17). If our actual target is call 13, the execution plan compresses by 2 weeks. If our target is call 14 (~1 August 2026), the plan has buffer.

**Trigger**: deadline mismatch revealed too late to recover.

**Mitigation**: verify the actual target NLnet call deadline within the first 24 hours of execution. If call 13, drop Week 4 scope, compress Weeks 1–3 into ~14 days, accept a less polished application. If call 14, follow the full 4-week plan.

**Owner**: maintainer.

### R2 — Single-author sustainability concern (Likelihood: High, Impact: High)

**Risk**: NLnet reviewers see one person as the entire team and question whether the project survives if that person stops working on it. The "what if Fouad disappears" question.

**Mitigation**: apply to The Commons Conservancy (institutional wrapper supplies continuity); recruit one co-maintainer for AUTHORS.md (delegated to maintainer's partner); secure one letter of support from an institutional partner; document the post-grant governance plan.

**Acceptance threshold**: Commons Conservancy application submitted + at least one named co-maintainer in AUTHORS.md by submission day = risk reduced to Medium.

**Owner**: maintainer + partner (recruitment) + this planning workspace (governance docs).

### R3 — Housing-agent author declines collaboration (Likelihood: Medium, Impact: High)

**Risk**: The maintainer's friend (housing-agent author) either does not reply, declines, or cannot ship integration in time. Loses the strongest proof of the MCP-composition claim.

**Mitigation**: draft the friendly collaboration message together in Week 1 (`11-institutional-outreach.md` Template F); if no reply in 7 days, follow up once; if still no reply or a decline, fall back to Option A (mock housing-stub client). Option A is a credible second-best.

**Owner**: maintainer (relationship) + planning workspace (fallback path documented).

### R4 — Tests fail to run locally on a clean machine (Likelihood: High, Impact: Medium)

**Risk**: A reviewer or potential contributor clones the repo, runs the tests, hits the `cryptography`/`cffi` failure, concludes the project is broken. Damages credibility immediately.

**Mitigation**: Week 3 task — fix the test environment, document setup in `CONTRIBUTING.md`, verify on a clean Docker container. Add a CI badge to README so the green status is visible without cloning.

**Owner**: agent execution (Week 3 task).

### R5 — Reviewer skepticism of MCP as a "civic-tech standard" (Likelihood: Medium, Impact: Medium)

**Risk**: MCP is Anthropic-led and only ~18 months old. A reviewer could decide it is too new / single-vendor-anchored to count as legitimate open infrastructure.

**Mitigation**: cite MCP's open specification status; cite the existence of multiple independent MCP implementations (Anthropic Claude, Cursor, Continue, Cline, multiple OSS clients); explain we contribute *to* the MCP ecosystem as the first civic-services reference implementation; position MCP as JSON Schema + JSON-RPC over stdio (a maturity-preserved standard combination) rather than as Anthropic's protocol.

**Owner**: planning workspace (framing) + Week 2 documentation (MCP specifics).

### R6 — Cost-saving claims viewed as unverified marketing language (Likelihood: Medium, Impact: Medium)

**Risk**: Reviewer reads the cost-saving doctrine and treats the numerical claims as bluster. Per-claim sourcing is currently mix of proven / plausible / aspirational.

**Mitigation**: in the cost-saving doctrine and the application text, every numerical claim is tagged with its category (proven / plausible / aspirational) and its source. Aspirational claims are paired with their measurement plan. No exaggerated figures.

**Owner**: planning workspace (doctrine doc) + application text (Week 4).

### R7 — Sanitisation introduces new bugs (Likelihood: Medium, Impact: Medium)

**Risk**: Replacing 29 `khalo.org` references in `app.py` and reorganising docs causes a regression — production-deployment URLs break, some feature stops working in the demo environment.

**Mitigation**: do sanitisation on a branch; run the full test suite after; smoke-test the running app before merging; do not push to any production deployment until verified locally.

**Owner**: agent execution (Week 1 task).

### R8 — German translation quality not native (Likelihood: Medium, Impact: Medium)

**Risk**: A German-speaking reviewer (NLnet has Dutch and German reviewers in the cohort historically) reads the German UI and finds it stilted or incorrect. Damages credibility.

**Mitigation**: Week 3 — native-speaker review of `de.json`. Find one German speaker for 2 hours of read-through. Credit them in AUTHORS.md. Acceptable cost.

**Owner**: maintainer (recruit native speaker) + agent execution (process the feedback).

### R9 — Public demo deployment goes down during application review (Likelihood: Low, Impact: Medium)

**Risk**: Reviewer visits the demo URL and sees a 500 error or down page. Bad signal.

**Mitigation**: Week 3 — use the **existing deployment infrastructure** the maintainer already operates (per `docs/production-deployment.md` and the existing `scripts/deploy.sh` / `scripts/production-smoke.sh` toolchain). Existing infrastructure is the default; introducing a new hosting provider for the demo is out of scope for §3.4. Health-check monitoring via `/api/health` is already in `docker-compose.prod.yml`; external uptime probes are provider-neutral per `docs/production-deployment.md` (the operator picks one and configures it themselves). Status-check before submission; accept a brief "we are a small project" caveat in README if uptime cannot be guaranteed.

**Owner**: agent execution against existing infrastructure (Week 3 task).

### R10 — Scope creep during execution (Likelihood: High, Impact: Medium)

**Risk**: With 18 h/day available and many tempting deliverables on the differentiation list (Nix flake, OpenSSF Scorecard, demo deployment, ESCO mapping, EURES export), the maintainer adds feature work that delays the core deliverables.

**Mitigation**: hard rules in the project's working guidelines — no new product features, no framework extraction. Reread the rules at the start of each day. The execution plan is the source of truth; off-plan work is added only by explicit decision logged in `04-research-and-decisions.md`.

**Owner**: maintainer (discipline) + planning workspace (rules).

### R11 — NLnet reviewer pool overloaded (Likelihood: Medium, Impact: Low)

**Risk**: NLnet runs multiple sub-funds with rolling calls; the reviewer pool can be slow. A "no answer for 2 months" outcome is possible even with a strong application.

**Mitigation**: design the project to be valuable even if the grant is delayed or denied. The hardening work in the 4-week sprint produces a credible commons project regardless. Apply to call 14 if call 13 is missed. Apply to Sovereign Tech Fund as a parallel path if NLnet declines (see `03-post-grant.md`).

**Owner**: planning workspace (post-grant plan).

### R12 — Maintainer burnout (Likelihood: Medium, Impact: High)

**Risk**: 18 hours per day for 4 weeks is unsustainable. Burnout in week 3 could collapse the application before submission.

**Mitigation**: protect sleep and break time. Use the cloud-execution environment for parallel-able tasks (agent doing one thing while maintainer reviews another). Schedule one full rest day per week. If burnout signals appear (sleeplessness, decision fatigue, scope confusion), drop differentiation moves before dropping blocker fixes.

**Owner**: maintainer (self-monitoring).

### R13 — Reviewer expects more institutional partners than we can secure (Likelihood: Low, Impact: Medium)

**Risk**: Reviewer expects multiple letters of support; we have one.

**Mitigation**: one credible letter is sufficient if the partner is well-respected. Pair the letter with the Commons Conservancy application as the second institutional signal. Frame the letter as proof of demand, not proof of distribution.

**Owner**: planning workspace (positioning).

### R14 — Encryption / data-handling claims do not hold up under scrutiny (Likelihood: Low, Impact: High)

**Risk**: We claim ChaCha20-Poly1305 encrypted-at-rest. A reviewer (or future security audit) finds the actual implementation is weaker than claimed.

**Mitigation**: Week 2–3 — verify the actual encryption implementation in `company_discovery/cv_builder.py` and related modules; document with code references; if the implementation is weaker than claimed, either fix it or revise the claim. Honesty over branding.

**Owner**: agent execution (verification).

### R15 — Existing production deployment leaks or surprises reviewer (Likelihood: Low, Impact: Low — downgraded 2026-05-17)

**Risk** (original framing, retained for history): Maintainer's existing deployment is publicly accessible, contains test data, has commercial framing, or otherwise contradicts the new commons positioning when a reviewer visits.

**Downgrade note (2026-05-17)**: The project has never been publicly launched. The only running deployment is a single private instance for one tester (the maintainer's partner — see Decision 17 in `04-research-and-decisions.md`). There is no public URL for a reviewer to find, no paying users, no commercial framing reachable from outside the maintainer's network. The risk surface for this item is effectively the maintainer's own laptop / private VPS, not a public-internet deployment. Likelihood remains Low (only the maintainer can leak it); Impact moves from High to Low because what leaks is a single-tester instance, not commercial product copy or PII at scale.

**Mitigation** (residual): The Week 3 public demo (`02-execution-plan.md` task 3.4) becomes the canonical reference for any reviewer. Until then, the private instance stays private; no public-traffic URL is shared in the application. Sanitisation in Week 1 task 1.4 is treated as a one-way removal rather than a coordinated migration (no users to migrate).

**Owner**: maintainer (private-instance hygiene) + agent execution (Week 3 demo deployment).

---

## Part B — Stakeholder Map

For each stakeholder: their role, what we need from them, what they need from us, current engagement status, suggested next step.

### S1 — NLnet Foundation

- **Role**: the funder. Reviewers, programme officers, contract administrators.
- **What we need from them**: a positive funding decision; access to NLnet's support services (accessibility audit, packaging support, security audit, mentoring) if funded.
- **What they need from us**: a credible application aligned with NGI0 strategic relevance, technical merit, value for money; milestone-based deliverables; open-source outputs.
- **Engagement status**: pre-application. No direct contact yet.
- **Next step**: submit application; if funded, sign contract.

### S2 — The Commons Conservancy

- **Role**: institutional wrapper for the project.
- **What we need from them**: acceptance as a Programme; the legal-entity wrapper; governance scaffolding; access to the NLnet thematic-fund automatic-creation mechanism.
- **What they need from us**: signed Pledge; agreement to their Code of Conduct (IEEE-ethics-based); alignment with their mission; clear commitment to free/open software.
- **Engagement status**: not yet contacted.
- **Next step**: Week 2 — submit application to join. See `02-execution-plan.md`.

### S3 — Maintainer's partner (refined 2026-05-17 — see Decision 17 in `04-research-and-decisions.md`)

- **Role(s)**: collapsed identity covering co-maintainer, sole current tester of the private deployment, HR / bureaucratic-navigation domain expert (the project's substantive credibility on civic-employment know-how), and co-owner of the bureaucratic / community-organising side of the project.
- **What we need from them**:
  - Confirmation of preferred public name / handle for `AUTHORS.md` (one-time, Week 1)
  - Pre-check before any cold-outreach send: do they have pre-existing contacts at MBE-equivalent or IQ-Netzwerk-equivalent organisations through their bureaucratic-domain network? (1 question, sub-1-hour turnaround — warm intros are worth 10× cold emails)
  - Continued domain-expertise input on persona panel, German bureaucratic flows, ESCO/Anerkennung mappings
  - Eventual Verein or legal-entity decision contribution if the Commons Conservancy wrapper does not cover everything
- **What they need from us**: clarity on what falls in their scope vs. the maintainer's; small, well-scoped asks rather than open-ended pulls; consistent communication; credit in `AUTHORS.md` from day one.
- **Engagement status**: active contributor since project inception. Not a recruitment target — already on the team.
- **Next step**:
  - Week 1 (governance commit): maintainer confirms partner's preferred public name / handle before the governance pack is pushed.
  - Week 1 (outreach): maintainer asks partner the pre-existing-contacts question before any cold message goes out.
  - Ongoing: maintainer is the side-channel for all partner coordination; executing agents do not block on partner unless explicitly told otherwise.

### S4 — Housing-agent author (the maintainer's friend)

- **Role**: collaborator on the MCP-composition reference integration.
- **What we need from them**: agreement to publish housing agent under Apache 2.0; ~4–8 hours of integration work; permission to be listed in `AUTHORS.md` / `ACKNOWLEDGMENTS.md`.
- **What they need from us**: a friendly request from the maintainer (not a cold pitch); clear scope; mutual cross-linking; future recognition.
- **Engagement status**: contact pending. Message drafted in `11-institutional-outreach.md` Template F.
- **Next step**: Week 1 — maintainer sends the message.

### S5 — One partner Beratungsstelle (MBE / IQ-Netzwerk / university career service)

- **Role**: institutional pilot partner and letter-of-support author.
- **What we need from them**: letter of support for the application; optionally, willingness to pilot a deployment after the grant.
- **What they need from us**: low-effort engagement (template letter, demo video, no procurement obligations); honest scoping (we are early-stage); follow-through if they sign on.
- **Engagement status**: not yet contacted. Templates ready in `11-institutional-outreach.md`.
- **Next step**: Week 1 — maintainer identifies one specific named contact per top-ranked target and sends the first three cold contacts. Follow-up at day 7.

### S6 — German Native Speaker — Translation Reviewer

- **Role**: ensures the German UI is native-quality.
- **What we need from them**: 2 hours reading `static/i18n/de.json` and flagging awkward phrasing.
- **What they need from us**: credit in `AUTHORS.md`; small gesture of thanks; clear scope.
- **Engagement status**: not yet identified.
- **Next step**: Week 3 — maintainer recruits one person (friend, fellow student, social circle).

### S7 — NLnet's Optional Support Services

- **Role**: provided to funded projects: accessibility audit (HAN University), packaging (NixOS Foundation), security audit, mentoring, governance advice.
- **What we need from them**: if funded — use accessibility audit and packaging support during the project execution; mention in the application proposal which services we anticipate using.
- **What they need from us**: a funded grant; engagement in the standard process.
- **Engagement status**: pre-application.
- **Next step**: in the application proposal, name explicitly which services we intend to use.

### S8 — Future contributors (translators, developers, NGOs)

- **Role**: post-grant community. Translation contributors per new language; developers extending the MCP tool catalogue; NGOs deploying.
- **What we need from them**: contributions, deployment feedback, bug reports.
- **What they need from us**: low-friction contribution pathway (`CONTRIBUTING.md`), responsive maintainer presence, clear governance, fair attribution.
- **Engagement status**: not yet a real community.
- **Next step**: Week 3 onward — `CONTRIBUTING.md` is in place; enable GitHub Discussions; document the translation contributor pathway in `docs/translating.md`.

### S9 — TU Berlin academic contact (optional)

- **Role**: nice-to-have academic affiliation.
- **What we need from them**: brief letter of support OR endorsement.
- **What they need from us**: clear scope (no obligation to fund, host, or commit students).
- **Engagement status**: one email sent or pending.
- **Next step**: Week 1 — send one well-crafted email; do not follow up.

### S10 — End users (the panel of personas and their real-world counterparts)

- **Role**: the people the project exists to serve.
- **What we need from them** (long-term): adoption, feedback, anonymised stories that can replace fictional personas.
- **What they need from us**: a tool that actually solves their problems while respecting their autonomy and data.
- **Engagement status**: indirect (some maintainer-known testers exist per Decision 5 in `04-research-and-decisions.md`).
- **Next step**: before submission, see if any real testers will consent to share an anonymised quote or story for the application.

### S11 — Maintainer

- **Role**: lead engineer, application author, primary decision-maker.
- **Self-care obligations**: sleep, breaks, energy management (per R12 Risk).
- **Next step**: protect sustainability across the 4-week sprint.

---

## How this document is used

- **At the start of each execution week**: review every risk; update Likelihood and Impact if conditions have changed; note mitigation progress.
- **At the start of each execution day**: scan the top-3 risks; ensure today's work does not increase any of them.
- **When a new stakeholder is identified**: add them to the map with status and next step.
- **At submission day**: verify every Medium+ risk has its mitigation in place; if not, decide whether to delay or proceed.
