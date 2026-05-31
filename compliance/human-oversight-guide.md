<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Human Oversight Guide

**Audience**: the **human-oversight person appointed by the deployer** (and the deployer who appoints them).
**Article**: AI Act Article 14 (human oversight).
**Pairs with**: the `HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE` configuration flag and the `/api/admin/oversight/queue` admin endpoint.
**Status**: living document. Updated alongside any change to the oversight UI or kill-switch behaviour.

---

## What Article 14 requires

Article 14 of [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) requires high-risk AI systems to be designed for **effective human oversight**. The oversight person must be able to:

- **Understand the capabilities and limitations** of the system and monitor its operation
- **Remain aware** of the possible tendency of automatically relying on the output ("automation bias")
- **Correctly interpret** the high-risk AI system's output
- **Decide, in any particular situation, not to use** the high-risk AI system or otherwise disregard, override, or reverse its output
- **Intervene in the operation** or interrupt the system through a "stop" function

This guide describes how each of those capabilities is achieved in Helpmefindthejob. The provider provides the affordances; the deployer appoints the oversight person; the oversight person follows this guide.

---

## 1. Appointment record

The deployer fills in this section before going live and updates it whenever the oversight person changes.

- **Oversight person name**: `[TBD: deployer to fill]`
- **Role and organisation**: `[TBD: deployer to fill]`
- **Contact (email + phone)**: `[TBD: deployer to fill]`
- **Backup oversight person (in case of absence)**: `[TBD: deployer to fill]`
- **Date of appointment**: `[TBD: deployer to fill]`
- **Date of next review of the appointment**: `[TBD: deployer to fill]`
- **Specific competence basis for the appointment** (training, professional qualification, experience in the relevant sector): `[TBD: deployer to fill]`

The competence basis matters: an oversight person who does not understand the recognition pipeline of nursing credentials cannot meaningfully review a fit-scoring output for Aïcha's situation. An oversight person who has not navigated TVöD-tier hiring conventions cannot meaningfully review a motivation-letter draft for Tobias's situation. Appoint someone whose competence matches your caseload.

---

## 2. The four oversight modes

Helpmefindthejob supports four oversight postures, listed from least to most intervention. The deployer chooses one (or a hybrid) and configures the system accordingly. The chosen posture is recorded in the audit log on every config reload.

### Mode A: Passive monitoring (default)

`HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE=disabled`

AI outputs reach the user directly. The oversight person monitors via the audit log (sampling, weekly review of patterns, drill-down on user-reported concerns).

**When this is appropriate**: stable deployments with a track record, non-public-authority deployers, and contexts where the system's outputs are advisory and well-understood.

### Mode B: Advisor-review queue (active)

`HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE=enabled`

AI outputs are appended to a review queue at `/api/admin/oversight/queue` before they reach the user. The oversight person reviews, approves, edits, rejects, or annotates each output. The user sees the approved (possibly edited) output.

**When this is appropriate**: initial deployment, public-authority deployers, sectors with elevated regulatory scrutiny, and any period of elevated risk (post-incident, post-AI-provider-switch, post-bias-testing-divergence).

### Mode C: Per-action gates

The 12-phase journey state machine already enforces that consequential actions (sending applications, accepting offers, persisting profile changes) require explicit user confirmation. This is a **structural** oversight mechanism that operates regardless of the configuration flag. It cannot be turned off; it is hard-wired into the journey state machine ([`../company_discovery/journey.py`](../company_discovery/journey.py)).

The oversight person verifies during commissioning that the per-action gates are active by exercising at least one full journey end-to-end and confirming that no journey phase auto-advances past a confirmation gate.

### Mode D: Kill-switch (system-wide)

`HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true`

Every AI-assisted code path is disabled — the app invokes no AI provider. Each AI-assisted feature falls back to its no-AI path: motivation/cover-letter drafting falls back to a deterministic templated skeleton (`company_discovery/motivation_letter.py`'s `templated_fallback`, with an honest no-AI banner); fit-scoring and CV-tailoring surface a BYO-AI handoff prompt for the user to run with their own AI; deterministic, rule-based features (persona-aware job ranking, application-outcome aggregation) continue to operate unchanged. No app-initiated AI call occurs while the switch is active.

**When to activate**:

- Ongoing incident affecting users (Sev-1 per [`risk-management-plan.md`](risk-management-plan.md) §5)
- Identified systematic bias against a documented persona class
- AI-provider unavailability for an extended period
- Regulatory or supervisory-authority order
- Discretionary call by the oversight person whenever the deterministic posture is preferable

**How to activate**: set the env var and restart the application. Its effect is recorded in the audit log: while the switch is active, every attempted AI invocation logs as an `ai_invocation` event with `outcome="declined"` (the handoff result), giving a continuous record of the no-AI posture. A dedicated `kill_switch_activated` system event is a Phase-2 observability item.

---

## 3. The advisor-review queue (Mode B detail)

When `HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE=enabled`, the system surfaces a queue of AI outputs awaiting review at `/api/admin/oversight/queue`. The endpoint is admin-gated; only users with `is_admin=True` and a valid session can access it.

### 3.1 What is queued

Every AI invocation is queued, with the following metadata:

- The AI invocation's `event_id` (matches the audit-log entry)
- The user's opaque ID (so the reviewer can spot patterns across one user)
- The journey phase
- The AI purpose (fit_score / cover_letter / tailor_cv / motivation_letter / skill_gap_brief / application_outcome_analysis)
- The AI output text
- The relevant context (job posting hash, CV slice hash, prompt template ID)

### 3.2 What actions the reviewer can take

**Implementation status**: the shipped `/api/admin/oversight/queue` is a **read-only** surface that lists recent AI-invocation audit events for after-the-fact review. The approve/edit/reject/annotate intercept-before-delivery workflow, the `override_event` audit type, and the queue timeout described in this section are the **planned** advisor-review design (Phase-2); they are not wired at this version.

- **Approve**: the output goes to the user as-is.
- **Edit**: the output is modified by the reviewer before reaching the user. The original and edited versions are both retained in the audit log as an `override_event`.
- **Reject**: the output is suppressed; the user sees a deterministic fallback for that action.
- **Annotate**: the output goes to the user, but with a free-text reviewer annotation appended.

In that planned workflow every action is logged as an `override_event` (a planned audit type — see [`audit-log-schema.md`](audit-log-schema.md) §4.6; not yet emitted at this version).

### 3.3 Time-out behaviour

In the planned advisor-review workflow, if the reviewer does not act within `HELPMEFINDTHEJOB_OVERSIGHT_QUEUE_TIMEOUT_SECONDS` (intended default 3600) the user receives a deterministic fallback and is informed that AI suggestions are temporarily delayed, and the timed-out item remains in the queue marked `time_out`. This timeout env var is **not read by the application at this version** (Phase-2 item).

This timeout exists to keep the user-facing experience usable in environments where review depth is high but availability fluctuates. Public-authority deployers may shorten the timeout to accept a higher fallback rate in exchange for tighter oversight; commercial-context deployers may lengthen it if their oversight schedule supports it.

### 3.4 Resource considerations

In Mode B, the reviewer's time is a real cost. The cost-saving doctrine in [`../docs/grant/08-cost-saving-doctrine.md`](../docs/grant/08-cost-saving-doctrine.md) assumes Mode A (passive monitoring) in steady state. Mode B is a transitional or elevated-scrutiny posture, not a permanent operating mode for typical deployments. The trade-off between throughput and oversight depth is the deployer's call.

---

## 4. Monitoring patterns

Even in Mode A, the oversight person actively monitors the audit log on a documented cadence. Suggested cadence and signals:

### 4.1 Daily (~10 minutes)

- Scan the previous-day error count by event type (`outcome="error"` in the audit log).
- Note any spikes; investigate root cause if elevated above baseline.

### 4.2 Weekly (~60 minutes)

- Compute the fit-score adjustment distribution across the persona cohort for the previous week. Look for skew against any persona class.
- Cross-check with user complaints or advisor feedback.
- Note any AI-provider switches and re-run the bias-test for the changed provider.

### 4.3 Monthly (~half a day)

- Run the bias-testing methodology in [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md) at sample scale (one persona per category).
- Review the kill-switch activations and the override-event log.
- Update the operational runbook if patterns suggest configuration changes.

### 4.4 Quarterly (~one day)

- Full bias-testing methodology re-run across all seven personas.
- Audit-log sampling-based review of fit-scoring outputs against a hand-picked sample.
- Update the risk register if any pattern justifies a residual-risk recalibration.

### 4.5 Annually

- Full review of this guide, the appointment record (§1), the chosen mode (§2), and the operational cadence (§4.1–§4.4).
- Document the year's incidents (if any) and the lessons learned.

---

## 5. Awareness of automation bias

The AI Act explicitly calls out automation bias — the human tendency to over-trust automated outputs. The oversight person's competence should explicitly include a defence against this tendency. Practical signals that the team is succumbing to automation bias:

- Advisors stop questioning fit-score outputs even when they obviously contradict the advisor's prior judgement.
- Users stop reading the rationale and act on the score alone.
- Reviewer approval rates trend toward 100% even when the cohort being reviewed is mixed.

If you observe any of these, treat it as a Mode B trigger condition and re-establish active review until the pattern reverts.

---

## 6. Documentation responsibilities

The oversight person maintains:

- The appointment record (§1)
- The monitoring runbook (your local document; based on §4 above)
- The post-incident review log (when incidents occur per [`risk-management-plan.md`](risk-management-plan.md) §5)
- The annual review summary

These documents are organisational records; they are not stored in the project repository.

---

## 7. Limits of the oversight role

The oversight person is **not** legally accountable for individual AI outputs as a substitute for the AI Act's broader deployer-and-provider responsibility framework. The oversight role exists to ensure effective oversight is in place, not to underwrite each output personally. The deployer remains accountable for the deployment; the provider remains accountable for the upstream system. Article 14 oversight is a structural mechanism, not a personal liability.

If you are appointed as the oversight person and find yourself in a context where you are being asked to underwrite each AI output personally, raise the issue with your deployer. Article 14 oversight should not be a defensive shield for under-resourced compliance; it should be a meaningful operational role with the time and authority to do the work described in this guide.

---

## 8. Append log

- **2026-05-18**: initial human-oversight guide drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint.
