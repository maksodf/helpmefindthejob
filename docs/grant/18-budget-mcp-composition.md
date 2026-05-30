<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Budget: Pilot-Ready Civic Employment Commons

## Definition of objectives

The key objective of this action is maturing Helpmefindthejob into a
self-hostable, institution-ready civic employment assistant for a
first real pilot.

The action will achieve this through six concrete work areas:
multi-agent orchestration, persona-specific employment intelligence,
improved search and provider reliability, accessibility and
end-to-end user journeys, operational trust infrastructure, and
institutional pilot readiness.

## Timing

The project is planned as a 9-month execution period starting from the
grant agreement / MoU signature, not from the application date. This
avoids depending on the exact review and award timeline. The work is
milestone-based, and payment is requested only when the relevant public
deliverable is complete.

The schedule assumes part-time execution alongside existing work/study
obligations. A 9-month window is chosen to keep the milestones
deliverable without relying on unrealistic full-time availability.

| Milestone | Amount | Hours | Target Timing |
|---|---:|---:|---|
| M1 Legal, governance, and compliance trust package | €5,000 | 83.3h | Months 1-2 |
| M2 MCP composition and agent handoff | €8,000 | 133.3h | Months 1-3 |
| M3 Guided chat workflow and priority commands | €6,000 | 100h | Months 3-4 |
| M4 Employment-friction intelligence and matching quality | €7,000 | 116.7h | Months 4-6 |
| M5 Search quality, accessibility, and persona proof | €6,000 | 100h | Months 6-8 |
| M6 Operator readiness and first-pilot package | €5,000 | 83.3h | Months 8-9 |
| **Total** | **€37,000** | **~616.7h** | **9 months** |

## Budget formula

Cost = hours × €60/hour.

The budget funds one solo maintainer-developer at a frugal blended
rate of €60/hour. It does not include employees, overhead/F&A,
hardware, travel, per-seat software, license fees, or external legal
counsel.

## Budget building steps

### M1: Legal, governance, and compliance trust package — €5,000 / 83.3h

**What this milestone is:**

Preparing the legal and institutional trust package: license, NOTICE,
and CLA consistency; security disclosure process; privacy/support
documentation; DPA template; human-review pathway; and compliance
index.

This does not pay for the Apache-2.0 license itself. The license
already exists. The funded work is the labour to verify, align,
document, and package the legal/compliance layer so that institutions
can review it.

**Specific benefit:**

An NGO, funder, or civic deployer can review the project and
understand who owns the code, how it can be used, how security issues
are reported, how personal data is handled, and how human review is
available.

**Why this is important:**

Helpmefindthejob works with employment-related personal data and
AI-assisted recommendations. Without a clear legal/compliance package,
institutions will not responsibly pilot or self-host it.

### M2: MCP composition and agent handoff — €8,000 / 133.3h

**What this milestone is:**

Building the Helpmefindthejob-side MCP composition layer. This
includes a versioned MCP tool catalogue, JSON Schemas for tool inputs,
an `mcp/discover` capability listing, consent-aware profile and
handoff payloads, sequential handoff tests, and documented examples
showing how an MCP client can call Helpmefindthejob employment tools.

**Specific benefit:**

Other MCP clients or future civic agents can safely discover and call
Helpmefindthejob capabilities such as job discovery, fit scoring,
profile access with consent, data export, and referral handoff.

**Why this is important:**

This makes Helpmefindthejob a composable employment component instead
of an isolated app. It proves the project's MCP promise while keeping
the budget focused on the employment assistant, not on building full
external housing, healthcare, or education agents.

### M3: Guided chat workflow and priority commands — €6,000 / 100h

**What this milestone is:**

Turning the chat into a guided workflow surface for the highest-value
user actions. Implement visible sub-goals in chat and the priority
commands:

- `/export`
- `/scan now`
- `/schedule`
- `/quota`
- `/provider`
- `/undo`

**Specific benefit:**

Users can complete essential actions directly from chat: export their
data, trigger a job scan, manage scan cadence, check usage limits,
choose provider/manual mode, and reverse mistakes.

**Why this is important:**

The chat is the main user interface. If essential actions are hidden
across screens or unavailable in chat, users get stuck. This milestone
makes the product feel like a guided assistant rather than a loose
chatbot.

### M4: Employment-friction intelligence and matching quality — €7,000 / 116.7h

**What this milestone is:**

Building employment-specific intelligence into matching and
application support. This includes German-language requirement
warnings, recognition-status checklist, informational Section 24 /
Section 16d / Section 18 / Blue Card work-status flags,
credential-equivalence hints, Wiedereinstieg support,
long-term-unemployment cover-letter framing, ESCO lookup improvements,
EURES-compatible export/import structure, friction-aware job
re-ranking, and fit-scoring regression tests.

**Specific benefit:**

Users see which jobs are realistically reachable for their language
level, documents, recognition status, qualifications, work status, and
employment history, not only which jobs match keywords.

**Why this is important:**

This is the core product value. Generic job boards already list
vacancies. Helpmefindthejob must help users understand realistic
opportunity and reduce the need for repeated advisor explanations.

### M5: Search quality, accessibility, and persona proof — €6,000 / 100h

**What this milestone is:**

Verifying that the main user journeys work for the seven defined
personas. This covers sign-up, chat, job brief, CV builder,
cover-letter generation, and data export. It also includes
keyboard-only checks, screen-reader review, reduced-motion support,
mobile-flow fixes, and accessibility regression tests.

**Specific benefit:**

Reviewers and pilot partners can see evidence that the app works for
realistic users, not only in technical demos.

**Why this is important:**

The target users already face language, bureaucratic, confidence, or
accessibility barriers. The product must reduce friction, not create
more.

### M6: Operator readiness and first-pilot package — €5,000 / 83.3h

**What this milestone is:**

Preparing the app for a first institutional pilot: backup/restore
verification, basic uptime/error monitoring, audit-log search/export,
simple operator dashboard, Docker/self-hosting package, partner
onboarding guide, and impact-report template.

**Specific benefit:**

A pilot partner can deploy or evaluate the app with basic operational
confidence: how to run it, monitor it, recover it, review actions, and
report outcomes.

**Why this is important:**

Operational readiness is not only product polish. The project must become usable
by real NGOs or civic institutions, and that requires operational
readiness, not just code.

## Total

**Total requested**: €37,000 / approximately 616.7 hours.

