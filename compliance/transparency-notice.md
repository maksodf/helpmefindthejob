<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Transparency Notice for Users

**Audience**: **you, the user of DirectJob Scout.** This notice explains how the system works, what data flows where, and your rights.
**Article**: AI Act Article 13 (transparency to deployers — adapted here as the user-facing surface) and Article 50 (transparency to natural persons interacting with AI systems).
**Surface**: this notice is shown at first run and is always available from the Settings screen.
**Status**: living document. The user-facing rendered version is at `/settings/transparency`; the source of truth lives here in the repo.

---

## What this is

DirectJob Scout is an open-source civic-employment copilot. It helps you navigate the European job market — including parts of that market that are often hard to navigate alone: foreign-credential recognition (Anerkennung), CV conventions that vary by country, multilingual application processes, employment-services bureaucracy, and the differences between sectors.

**Who is DirectJob Scout built for?** Anyone facing structural friction between what they can actually do and what the European labor market is set up to recognise. Migrants and EU-mobile workers face this friction most acutely — language barriers, foreign-credential opacity, residency complexities make it densest there — and they are the strongest example users the system was designed around. The same friction also affects, for example, someone returning to clinical nursing after twelve years out of practice for childcare; someone pivoting from commercial tech to public-sector civic-tech work; someone re-entering the labour market after long-term unemployment; someone moving back to their home country after years working abroad; or anyone working outside the bureaucratic system they grew up navigating. If you recognise yourself in any of those situations — or in something structurally similar — this tool is built for you.

You do not need to be a migrant for DirectJob Scout to be useful, and migrants are not the only users. The tool is built around the **friction** you face in connecting your capability to a role, not around who you are.

---

## What DirectJob Scout does

The tool combines:

- **Job discovery** from career pages, public job aggregators, and bookmarklet captures you make.
- **A structured conversation** that walks you through a 12-phase journey: discover, profile, scope, score, draft, send, follow-up, accept, onboard.
- **AI-assisted suggestions** for job-to-CV fit, CV tailoring, motivation-letter drafting, and application-outcome analysis.

At every step, the suggestions are **suggestions** — never decisions. You confirm each consequential action before it happens. The system never submits an application, never accepts an offer, never makes any binding decision on your behalf without your explicit click-to-confirm.

---

## How AI is used

Some actions in DirectJob Scout invoke an AI model. These are:

| Action | What the AI does | What the AI does not do |
|---|---|---|
| Compute a fit score for a job | Generates a re-ranking adjustment within ±15% of the structured score, plus a free-text rationale | Does not produce the score from scratch — the structured rule-based scoring is the source of truth |
| Tailor your CV for a specific role | Proposes edits to existing CV sections you've selected | Does not invent CV facts or experience you haven't entered |
| Draft a motivation letter | Composes a first-draft letter grounded in your confirmed CV bullets | Does not send the letter; you read, edit, confirm, and send |
| Analyse your application history | Surfaces patterns: which CV variant gets replies, which sectors respond, which application timings work | Does not decide what you should do next; offers observations |
| Generate a skill-gap brief | Compares your skills to a role's required ESCO skills and surfaces gaps | Does not enrol you in any course or programme |

Other actions in DirectJob Scout are **deterministic** — no AI involved. Examples: job discovery from configured sources, locale-aware yes/no parsing in chat, profile-field editing, application persistence, calendar reminders.

---

## What data is sent to the AI

When an AI action runs, the system sends **only the slice of data needed for that action** to the AI provider. Specifically:

- **Fit-scoring** sends the job posting and the relevant CV section that matches the job's ESCO codes — not your full profile, not your name, not your email, not your application history.
- **Motivation-letter drafting** sends the job posting and the CV bullets you confirmed for this role — not your job history with other employers.
- **CV tailoring** sends the job posting and the CV sections you select — not your other CV sections.

The full minimisation rules are documented in [`data-governance.md`](data-governance.md) §4 and live in the project's open-source codebase. You can verify them.

---

## You choose the AI provider

DirectJob Scout does not force a single AI provider on you. The deployment can be configured to use:

- **OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter** (commercial cloud AI providers)
- **Ollama** (fully offline, your own machine, no data leaves)
- **Manual handoff** (the system constructs the prompt, you copy-paste it into your AI of choice)
- **Claude Code** (if you have a Claude Code subscription)
- **Deterministic templates** (no AI at all — every AI-assisted action falls back to a clear, deterministic template)

If you are not comfortable sending your CV slice to a third-party AI provider, choose Ollama (your own machine, no egress) or manual handoff (you control exactly what is sent and where) or deterministic templates (no AI).

You can change your AI provider at any time. You can revoke AI consent at any time. The system records each consent change in the audit log so you have a record of what was active when.

---

## What is logged

DirectJob Scout keeps an audit log for compliance with EU AI Act Article 12. The log records:

- Every AI invocation (timestamp, purpose, AI provider used, tokens in/out, response duration)
- Every system event (MCP tool calls, kill-switch activations, AI-provider failover)
- Every confirmation event when you save, update, or delete data
- Every export of your data

By default, the log uses **hashed identifiers** for you — not your name, not your email. The hash is salted per deployment so it can be used to trace a single user's events across the log (for incident review or your right-to-explanation requests) without being a plaintext personal identifier.

The default retention is **180 days**. The deployer can configure this; in some legal contexts (specific incident investigation, regulatory request) the deployer may retain longer or in a different form. The deployer should disclose their specific retention policy in their deployer-managed addendum to this notice.

---

## Your rights

### Right to know you are interacting with AI (Article 50)

This notice exists to give you that knowledge. Every AI-assisted action in the interface is labelled. The journey state machine never auto-routes you through an AI invocation without you seeing it.

### Right to an explanation (Article 86 and GDPR Article 22)

If an AI-assisted output affects your situation in a way you want to understand, you can request a structured explanation. For fit-scoring, this is built into the UI: click "Show why" on any score to see the per-criterion breakdown and the AI's rationale. For other outputs, contact your deployer's oversight person (see [Deployer-managed addendum] below).

### Right to opt out of AI features

You can disable AI-assisted features entirely at any time from the Settings screen. The system continues to function with deterministic templates. You can re-enable later if you change your mind.

### GDPR rights

You retain all your GDPR rights:

- **Access** — `/api/profile/export` returns your full profile in structured JSON.
- **Rectification** — edit any profile field from the chat or the Settings screen.
- **Erasure** — request deletion from `/api/profile/delete`. Your profile, CV facts, and application history are deleted; audit-log entries are unlinked from your identifier.
- **Portability** — your profile export uses open standard formats (schema.org, ESCO).
- **Objection / withdrawal of consent** — revoke AI-provider consent at any time.

To exercise any of these rights, use the Settings screen or contact your deployer (see below).

### Right to lodge a complaint

You can lodge a complaint with your jurisdiction's data-protection authority (in Germany: the relevant Landesdatenschutzbeauftragte for the state where your deployer operates, or the Bundesbeauftragte für den Datenschutz und die Informationsfreiheit for federal-level deployers). For AI-Act-specific concerns, your jurisdiction's AI Office / market-surveillance authority is the relevant body.

---

## Limitations you should know about

We list these here because honesty about limitations matters more than marketing.

- **AI outputs are suggestions, not decisions.** Even when the system says "fit score: 87/100," that is a recommendation. Your judgement overrides the system.
- **Foreign-credential recognition is slow.** The system helps you find recognition-friendly employers and present your credentials clearly; it cannot expedite the actual Anerkennung process.
- **The job market is incomplete.** We see job postings that are publicly discoverable (career pages, public aggregators) or that you bookmark. We do not see closed-employer applicant-tracking system internals.
- **AI-provider quality varies.** Offline-only operation via Ollama produces lower-quality fit scoring than commercial cloud AI providers. You can switch back and forth; the trade-off is your call.
- **Language coverage**: English and German are shipped at first release. Arabic, Ukrainian, Turkish, and Romanian are on the roadmap as native-speaker contributors join. If you speak a language not yet shipped, you can still use the system in EN or DE; some bureaucratic-context examples will read less naturally to you.

---

## Where the system lives

DirectJob Scout is open-source under Apache License 2.0. The source code is at `https://github.com/maksodf/directjob-scout`. The project is being prepared as a Programme of The Commons Conservancy (a Dutch foundation co-founded by NLnet). You can fork, self-host, audit, or contribute. No vendor lock-in. No commercial gate.

---

## [Deployer-managed addendum]

Your specific deployer fills in the deployment-specific information below. If this section is empty, please contact your deployer to ask them to complete it.

- **Deployer organisation**: `[TBD: deployer to fill]`
- **Deployer contact for AI-Act / data-protection questions**: `[TBD: deployer to fill]`
- **Deployer's appointed human-oversight person**: `[TBD: deployer to fill]`
- **Deployer's specific audit-log retention period**: `[TBD: deployer to fill — default is 180 days unless changed]`
- **Deployer's chosen AI provider(s)**: `[TBD: deployer to fill]`
- **Deployer's data-protection officer (DPO) contact**, if applicable: `[TBD: deployer to fill]`
- **Deployer's data-protection-authority complaint-channel**: `[TBD: deployer to fill]`

---

## Last updated

This notice is currently dated **2026-05-18** (v1, Week 2 of the NLnet NGI Zero Commons Fund grant sprint). The deployer should re-publish on their domain with their addendum complete before going live.
