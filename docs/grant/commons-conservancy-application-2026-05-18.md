# Application to The Commons Conservancy — DirectJob Scout Programme

**Status**: DRAFTED 2026-05-18 — pending maintainer review before send.
**Target send channel**: `website@commonsconservancy.org` (the public contact published in the Conservancy footer; if Conservancy has since published a more specific application address, route there). The site's `/how/` page describes a six-phase process beginning with **Initiation**, where the Conservancy verifies eligibility and assigns a case officer; this letter is the Initiation notification.

**Reference**: Decision 2 in `04-research-and-decisions.md` — institutional wrapper is The Commons Conservancy, application target Week 2 of the grant sprint.

**Pre-send checklist** (maintainer):

- [ ] Resolve `[MAINTAINER_NAME]` and `[MAINTAINER_EMAIL]` placeholders with the public-facing identity you want associated with the Conservancy record.
- [ ] Decide whether to surface the partner co-maintainer in this letter or defer naming per the consent-first authorship policy (Decision 18 in `04-research-and-decisions.md`). The current draft uses the consent-first phrasing.
- [ ] Confirm the licence statement matches what landed in `LICENSE` and `cla.md` (it does, at branch HEAD).
- [ ] Add an attachment list if you want to include the README, project brief, or AI Act compliance pack preview alongside the email.
- [ ] Send.

**Post-send checklist** (agent + maintainer):

- [ ] Log the send date and recipient in the new Open R11 entry in `04-research-and-decisions.md` Part C.
- [ ] Watch the inbox for the case-officer assignment; the Conservancy `/how/` page does not publish an explicit timeline, so the expected response window is recorded as "2–6 weeks based on observed cadence of recent Programme admissions" until we have concrete data.

---

## Letter text

> **Subject**: Notification of intention to apply as a Programme — DirectJob Scout (civic-employment commons; NLnet NGI Zero Commons Fund applicant)

To the Board and Case-Officer Team of The Commons Conservancy,

I write on behalf of **DirectJob Scout**, an early-stage open-source civic-employment commons project, to notify The Commons Conservancy of our intention to apply for admission as a Programme.

We have read the Conservancy's mission statement (DRACC 0001), the framework documents at `/how/`, and the FileSender founding statutes (DRACC 0017) as a worked example. We understand the six-phase admission process — Orientation, Initiation, Setup, Operational, and the optional Graduation / Hibernation paths — and this letter constitutes our Initiation notification. We are ready to engage with the assigned case officer to draft Programme statutes modelled on the FileSender / Redwax pattern, to sign the Pledge, and to align our governance with the IEEE-ethics-based Code of Conduct referenced in the founding documents.

### About the project

DirectJob Scout is an **open-source EU-wide civic-employment commons**. The project captures specialist HR and bureaucratic-navigation knowledge — currently locked in advisors' heads, HR departments, recruiter networks, and overworked migrant-services case workers — and puts that knowledge directly into the hands of skilled and semi-skilled migrants and EU-mobile workers across Europe.

The first concrete reference implementation is a conversational copilot deployed in Germany (because that is where the maintainer is based); the architecture is country-neutral and the cross-border story is a localisation exercise, not a re-engineering effort.

The technical contribution is the **architecture, not the application**. The project is exposed as composable civic infrastructure via the Model Context Protocol (MCP), with a versioned tool catalogue documented under JSON Schema. Parallel open civic agents — housing, healthcare, residency, education — compose with DirectJob Scout without forking. A reference housing-agent integration is shipping in Week 2 of the current sprint as proof of the composition pattern.

The project repository (Apache 2.0 with Contributor License Agreement) is at `https://github.com/maksodf/directjob-scout`. The Week 1 grant-readiness hardening — LICENSE, NOTICE, TRADEMARK, CLA, SPDX headers across every Python source file, a Contributor Covenant 2.1 Code of Conduct, SECURITY / SUPPORT / AUTHORS / ACKNOWLEDGMENTS, issue + PR templates, CODEOWNERS, civic-commons-positioning README rewrite, and a published feature-verification report — has been completed and is visible on the project's active working branch.

### Mission alignment with DRACC 0001

DRACC 0001 frames the Conservancy's purpose as enabling "a fair and balanced global information society in which individuals can collectively scrutinise, reconfigure and improve upon the technology" and as "endurably making available and promoting free and open technology and content … at the largest possible scale."

DirectJob Scout is an explicit implementation of that purpose in the civic-employment domain:

- **Free and open technology**, with no commercial gate: Apache 2.0 with CLA, BYO-AI architecture (including a fully-offline Ollama path), encrypted user data, exportable user records, and no per-seat licensing.
- **Endurably available**: the institutional wrapper provided by the Conservancy is precisely what allows this project to outlast any one contributor. The maintainer is a TU Berlin student; the project is not (and must not become) hostage to the maintainer's individual continuity.
- **Largest possible scale**: the architecture is EU-wide, the language strategy is multilingual (English and German shipped; Arabic, Ukrainian, Turkish, and Romanian on the post-grant roadmap), and the standards-anchored MCP composition surface invites integration with other open civic agents.
- **Scrutiny and reconfiguration**: every AI invocation is constrained to a phase of a deterministic state machine, every database write is user-confirmed, and the project ships an audit-log infrastructure designed to make institutional deployments inspectable under EU AI Act high-risk-AI obligations effective from 2 August 2026.

### Free and open software commitment

The project is and will remain licensed under the Apache License 2.0. The Contributor License Agreement we use is an unmodified adaptation of the Apache Individual CLA model; we have introduced no novel CLA terms. Trademark, NOTICE, and rights ownership are documented at the repository root.

We pledge that:

- Source code will remain published under an OSI-recognised licence.
- Any scientific or research outputs of the project will be open access.
- We will not introduce a vendor-locked deployment path or close future versions to commercial-only access.
- We will sign the Pledge during the Setup phase and abide by the IEEE-ethics-based Code of Conduct referenced in the Conservancy's founding documents (we have already adopted the Contributor Covenant 2.1 in `CODE_OF_CONDUCT.md`, which is broadly compatible).

### Governance shape on entry

On admission to the Conservancy as a Programme we anticipate a small founding Board, with at minimum the maintainer and one co-maintainer (already an active contributor; identity to be added publicly per the project's consent-first authorship policy documented in `AUTHORS.md`). We will adopt the standard DRACC pattern for statutes — modelled on FileSender (DRACC 0017) or, where applicable, on Redwax — and we are open to the case officer's guidance on whether the project's small initial scale warrants a leaner variant.

We do not anticipate a budget on entry. The project's first concrete funding ask is an in-flight application to the NLnet NGI Zero Commons Fund (Call 14, deadline approximately 1 August 2026) for €37,000 across six milestones to harden the project for institutional deployment. Conservancy admission would substantively strengthen that application by providing the institutional wrapper NGI0 reviewers look for.

### What we are asking for at this stage

A case officer assignment, per the Initiation phase described at `/how/`. We are ready to participate in scope-alignment and governance-model selection conversations at the case officer's convenience.

If admission is granted in time to be cited in the NGI0 application, that would be ideal; if not, the project's intention to apply to the Conservancy is itself a credible signal of institutional intent that the application can cite.

### Logistics

- **Project repository**: <https://github.com/maksodf/directjob-scout>
- **Active working branch** (Week 1 grant-readiness hardening visible): `claude/project-analysis-bpHCo`
- **Strategic planning workspace**: `docs/grant/` in the repository — full project brief, four-week execution plan, decisions log, AI Act compliance plan, MCP composition spec, and a 374-line feature-verification report are all public.
- **Primary contact**: [MAINTAINER_NAME], [MAINTAINER_EMAIL]
- **Maintainer affiliation**: student at the Technische Universität Berlin
- **Geographic base**: Berlin, Germany

We would be glad to provide any additional material — a demo video, a longer mission statement, draft Programme statutes for case-officer review — at your request.

With thanks for considering our application, and in advance for the time of whichever case officer is assigned,

Sincerely,
[MAINTAINER_NAME]
DirectJob Scout maintainer

---

## Attachments mentioned in the letter (optional, on send)

- `README.md` — project README at the active branch HEAD
- `docs/grant/01-project-brief.md` — strategic source of truth
- `docs/grant/feature-verification-2026-05-18.md` — verification report demonstrating the project's current technical state
- `LICENSE`, `NOTICE`, `cla.md` — licence pack
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1 reference

Sending each as a direct link rather than as a binary attachment keeps the email short and lets the case officer browse the repository.

---

## Notes for the post-submission tracker

Once sent, record the following in `docs/grant/04-research-and-decisions.md` Open R11 (to be created on send):

- Send date and recipient address
- Any case-officer name + email returned
- Each round-trip exchange (date, summary)
- Final outcome: admitted / declined / withdrawn

Until response, the expected window is **2–6 weeks** based on observed admission cadences for recent Programmes (Redwax, QLever-similarity, etc. — exact dates not in the Conservancy public site). If no response within 4 weeks, send one polite nudge to the same address and update the tracker.
