<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Quarterly impact report — template

**Purpose**: a standardised template for the maintainer's quarterly project-impact report. The first issue (Q1 2027) is the inaugural reporting cycle; this template ships in v0.80.0 so future quarters have a stable shape to fill in.

**Article anchor**: pairs with the cost-saving doctrine at [`docs/grant/08-cost-saving-doctrine.md`](grant/08-cost-saving-doctrine.md) (the metric framework) and with the persona-friction-class architecture (the cohort framework). The aim is reviewer-readable evidence that the project's claims about institutional cost-reduction + user-outcome-improvement are measured, not asserted.


**Cadence**: every 3 calendar months. The maintainer authors; the deployer-side data flows from each pilot deployment's audit-log aggregates (HMAC-salted opaque user ids only — never identifying).

**Status**: living template. First filled instance lands at `docs/impact-reports/2027-Q1.md` when Q1 2027 closes.

---

## Why this report exists

The cost-saving doctrine is the project's load-bearing claim to civic-tech reviewers + institutional adopters: every feature evaluated against "does it reduce institutional operational cost while improving end-user outcomes?". Without quarterly evidence the doctrine is rhetoric. With quarterly evidence — even when the numbers are small in the early quarters — the doctrine becomes a testable, falsifiable, audit-trail-grounded claim.

The report serves three audiences:
1. **NLnet + downstream-grant reviewers** auditing whether the project's claims hold under measurement.
2. **Institutional deployers** evaluating whether the project's documented outcomes are realistic for their context.
3. **The project maintainer + contributors** as the honest-state self-check that keeps scope-creep + over-claim in check.

---

## Report structure (sections to fill)

### 1. Reporting period + scope

| Field | Value |
|---|---|
| Quarter | YYYY-QN |
| Date range | YYYY-MM-DD to YYYY-MM-DD |
| Project release(s) in scope | `vX.Y.Z` → `vA.B.C` |
| Deployments contributing data | (list deployer-IDs that opted in) |
| Total active users across deployments | N (aggregated; per-deployer breakdown in §5) |

### 2. Headline numbers

| Metric | This quarter | Prior quarter | Δ | Notes |
|---|---|---|---|---|
| Users served (unique user_opaque_ids active in the quarter) | | | | |
| Sessions per user (median, p90) | | | | |
| Jobs surfaced in discover/queue | | | | |
| Fit scores generated | | | | |
| Cover letters drafted | | | | |
| Applications marked-applied | | | | |
| Applications with response received | | | | |
| Reply rate | | | | response÷applied; reported only if ≥30 applications |
| Outcomes recorded (interview / offer / hired) | | | | per `record_user_outcome` MCP tool |

These numbers come from the deployer's audit-log aggregates per `compliance/audit-log-schema.md` §7 query examples. Per-user identity NEVER leaves the deployment.

### 3. Per-persona-cohort numbers

For each of the seven canonical personas, surface the cohort-aware aggregates. Anonymised; minimum-count threshold of 5 active users per cohort to surface a row (below 5 the aggregate is too small to publish without re-identification risk).

| Persona | Active users | Median session count | Median time-to-first-application | Reply rate | Top friction context |
|---|---|---|---|---|---|
| Aïcha-class (§16d Anerkennung, healthcare) | | | | | |
| Yusuf-class (Blue Card pending, engineering) | | | | | |
| Olga-class (§24 protection, English-team tech) | | | | | |
| Mahmoud-class (§4 Subsidiärer Schutz, trade Ausbildung) | | | | | |
| Maria-class (EU Blue Card, underemployed architect) | | | | | |
| Käthe-class (Wiedereinsteigerin, returner) | | | | | |
| Tobias-class (long-term unemployed, career changer) | | | | | |

### 4. Employment outcomes (with persona consent)

For users who explicitly consented to outcome-reporting + provided the outcome event via `record_user_outcome`:

| Outcome class | This quarter | Cumulative since project start | Notes |
|---|---|---|---|
| First-interview-scheduled | | | |
| Offer-received | | | |
| Hired (signed contract) | | | |
| Continued-search (no offer in the quarter) | | | |
| Off-platform-transition (user found role via channel outside the project) | | | |

Consent gate: outcome events are opt-in via the SPA's Settings → Privacy → outcome-reporting toggle. No outcome is recorded without explicit consent at event time.

### 5. Per-deployer breakdown

| Deployer (anonymised label) | Type | Active users | Notable outcomes | Maintainer-deployer interaction notes |
|---|---|---|---|---|
| Deployer A | Beratungsstelle / Migration office | | | |
| Deployer B | IQ-Netzwerk regional | | | |
| Deployer C | Optionskommune Jobcenter | | | |
| Deployer D | University career service | | | |
| Deployer E | NGO returner-network | | | |
| (self-hosters opting in) | individual | | | |

Deployers are anonymised in the public report (Deployer A / B / C / ...). The maintainer maintains a private deployer-name ↔ anonymous-label mapping. Deployers opt in to publication of their identity per-quarter if they want public credit.

### 6. Cost-saving evidence

Translates the headline numbers into the cost-saving-doctrine framework. Each mechanism in `08-cost-saving-doctrine.md` gets a row + the quarter's measurement.

| Cost-saving mechanism | Measurement this quarter | Cumulative | Methodology note |
|---|---|---|---|
| Advisor caseload time-saving (per `08-cost-saving-doctrine.md` mechanism 1) | hours saved / advisor / week | | calculated from sessions-per-advisor × time-saved-per-session |
| Anerkennung-friendly employer matching (mechanism 2) | days from CV-ready to first matching role | | per Aïcha-class + Yusuf-class cohorts |
| AI Act compliance inheritance (mechanism 5) | (qualitative; per-deployer interview) | | "would your org have needed consulting for AI Act readiness? estimate of saved cost" |
| Reproducible build via Nix (mechanism 6) | (qualitative; deployer feedback) | | |
| Multilingual built-in (mechanism 7) | translator-service cost avoided per deployer (€/year estimate) | | |
| Faster Anerkennung pipeline (mechanism 8) | weeks saved per case (Aïcha-class) | | |

The € figures in mechanism 5/7 are **deployer-interview estimates**, not measured operational cost. They are tagged as such in the report so a reviewer sees the methodology constraint.

### 7. Bias-testing re-run

| Cell | This quarter | Prior quarter | Δ | Notes |
|---|---|---|---|---|
| OOB rate across `build_auto_fit_prompt` | | | | target <3% (was 13.0% at v0.80.0) |
| Cross-provider mean spread (max cell) | | | | from `bias-comparative-report-<date>.md` |
| Article 22 escalation count | | | | from `/api/admin/oversight/queue` aggregate |
| Article 22 verdict distribution (uphold / correct / overturn) | | | | |

### 8. Incidents + drill log

| Incident class | Count this quarter | Notes |
|---|---|---|
| Sev-1 (active harm) | | |
| Sev-2 (degraded service) | | |
| Sev-3 (latent risk surfaced) | | |
| Drills completed | | per `compliance/incident-response-drill.md` cadence |

If any Sev-1 incident occurred, link to the post-mortem (deployer-side + project-side cross-references).

### 9. Roadmap progress

Snapshot what shipped vs what was scoped against the `ROADMAP.md` quarter-row. Honest about misses.

| ROADMAP item for this quarter | Shipped? | Notes |
|---|---|---|
| (per ROADMAP.md "At a glance" table row for this quarter) | | |

### 10. Sustainability signals

| Signal | This quarter | Cumulative | Notes |
|---|---|---|---|
| New deployers onboarded | | | |
| Active contributors (committers in the quarter) | | | |
| External translators (Weblate or PR) | | | |
| GitHub Sponsors (€) | | | activated only post-launch |
| Open Collective (€) | | | same |
| Paid support contracts signed | | | |
| Grant applications filed | | | |
| Grant applications awarded | | | |
| In-kind partnerships signed | | | |

### 11. Honest closeout

A 3-paragraph maintainer narrative:

1. **What worked this quarter** — concrete wins, evidence-backed.
2. **What didn't work** — misses, scope-creep, things deferred.
3. **What changes for next quarter** — based on the above, what is scoped / anticipated / no-longer-priority.

This section is the discipline anchor. Without it the report degenerates to vanity metrics.

---

## How to fill the report

For each quarter:

1. Pull deployer-side audit-log aggregates from every opted-in deployment via the per-deployer aggregate-export procedure (deployer-side; the project never centralises raw event data).
2. Aggregate cross-deployment per persona-cohort.
3. Anonymise: drop any deployer-identifying field below the minimum-count threshold (≥5 users per cohort or ≥3 deployers per metric).
4. Author the narrative sections (§9 and §11 especially) from the maintainer's own working knowledge of the quarter.
5. Publish at `docs/impact-reports/YYYY-QN.md`.
6. Append a one-line summary to a top-level `docs/impact-reports/INDEX.md` so the chronological audit-trail is one-click navigable.
7. Cross-post a short blog-style version to the maintainer's chosen audience channel (low-volume; no spam).

---

## Privacy + consent discipline

The report is built ENTIRELY on aggregates. Per-user data never leaves the deployer. The HMAC-salted opaque user IDs in the audit log are the upper bound on identifiability; the cohort aggregates above are at a coarser grain. Specifically:

- No individual user's CV text, profile fields, or message content appears in any quarterly report.
- No deployer-identifying information appears below the minimum-count threshold.
- Per-cohort minimum-count threshold of 5 active users — below that, the row is dropped or merged into "other".
- Outcome events are opt-in at event time; opt-out users are not represented in §4.

The DPIA at `compliance/gdpr-article-35-dpia.md` §3 risk row 1 ("data breach") is mitigated by this aggregation pipeline; the report itself is a deployable analytics surface, not a raw-data export.

---

## First-issue (Q1 2027) checklist

For the inaugural report, append a dated row to `docs/impact-reports/INDEX.md` and verify these are in place before publishing:

- [ ] At least one deployer with ≥5 active users opted in to outcome reporting
- [ ] Bias-comparative-report-v2 has executed at least once
- [ ] At least one incident-response drill has been run (per `compliance/incident-response-drill.md` quarterly cadence)
- [ ] At least one Article 22 right-to-human-review request has flowed through (or — honestly — "zero requests this quarter")
- [ ] Audit-log key rotation has executed at least once OR a documented "no rotation needed this quarter; calendar rotation in 2027-Q2"
- [ ] The maintainer's narrative §11 is honest about misses, not only wins
- [ ] No deployer-identifying data below the minimum-count threshold appears in the public document
- [ ] The report is published at `docs/impact-reports/2027-Q1.md` + the INDEX is updated

---

## Append log

| Date | Quarter | Author | Notes |
|---|---|---|---|
| 2026-05-24 | (template — not a real report) | maintainer (Fouad) | Initial template authored for the project's reporting cadence. First filled instance at `docs/impact-reports/2027-Q1.md` when Q1 2027 closes (the project's first NGO pilot deployment is anticipated 2026 Q4 per ROADMAP.md, so Q1 2027 is the earliest defensible reporting quarter). |
