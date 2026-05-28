<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Service Level Agreement — Template

**Audience**: institutional deployers (Beratungsstellen, IQ-Netzwerk
regional networks, integrated NGO partners, government adopters)
who need a procurement-ready SLA before signing a deployment
agreement with a Helpmefindthejob hosting party.

**Status**: TEMPLATE. Not a binding agreement until both parties
fill in the bracketed variables and sign. The Helpmefindthejob
maintainers do **not** themselves provide a hosted service —
this document is a starting-point template that deployment
partners (the entities running their own instance) can adopt
or adapt to their own legal context.

**Tier framing**: this template defines the discipline a
production-grade hosting party should commit to. Adoption is the
deployer's decision; the project's reference deployment may
operate at lower or higher targets than the values here.

---

## 1. Service description

### 1.1 Covered services

This SLA covers the following surfaces of a Helpmefindthejob
deployment operated by **{HOSTING_PARTY}** for
**{INSTITUTIONAL_DEPLOYER}**:

- The web application at **{PUBLIC_URL}**
- The MCP server endpoints exposed by the same deployment
- The REST API at **{PUBLIC_URL}/api/public/v1/\***
- The background job queue (deduplication scans, aggregator
  searches, alert delivery)

### 1.2 Not covered

- Third-party services (AI providers — OpenAI / Gemini /
  Anthropic / Ollama; aggregator job boards — StepStone /
  Indeed / Arbeitnow / Muse / Bundesagentur; email delivery —
  SMTP provider).
  Outages of these external services are reported as **degraded
  dependencies** but do not count against the uptime targets
  below.
- User-side errors: invalid inputs, exceeded user-level quotas,
  user-misconfigured AI providers.
- Network failures between the user and the deployment that
  occur outside the deployment's network boundary.

---

## 2. Uptime targets

| Tier | Monthly uptime | Maximum monthly downtime | Best-fit deployer |
|---|---|---|---|
| **Community** | 99.0% | 7h 18m | Volunteer-run instances, small NGOs |
| **Standard** | 99.5% | 3h 39m | Beratungsstellen, regional NGOs |
| **Institutional** | 99.9% | 43m 30s | IQ-Netzwerk, federal-state deployments |

**Uptime definition**: the percentage of one-minute intervals in a
calendar month during which the public-facing health endpoint
(`/api/health`) returns `{"status": "ok"}` within 5 seconds.

**Measurement**: the deployment's own health-history surface
(`/api/health/history`) is the canonical record. The deployer
SHOULD also subscribe to an independent uptime monitor
(UptimeRobot / Better Uptime / similar) for adversarial evidence.

---

## 3. Performance targets

| Endpoint class | p50 response | p95 response | p99 response |
|---|---|---|---|
| Static asset (`/styles.css`, `/app.js`, icons) | < 100 ms | < 250 ms | < 500 ms |
| Health check (`/api/health`) | < 50 ms | < 150 ms | < 300 ms |
| MCP catalogue (`/mcp/schemas.json`) | < 100 ms | < 300 ms | < 500 ms |
| REST API read (no AI) | < 200 ms | < 500 ms | < 1 s |
| REST API write (no AI) | < 300 ms | < 800 ms | < 1.5 s |
| AI-backed (fit-score, cover letter, tailor) | < 5 s | < 15 s | < 60 s* |

\* AI-backed responses depend on the chosen provider (Ollama local
inference is 5–10× slower than OpenAI cloud); the deployment is
not held to the AI-provider-side latency, only to the time
between request receipt and provider dispatch.

---

## 4. Incident response

### 4.1 Severity levels

| Severity | Definition | First-response target | Resolution target |
|---|---|---|---|
| **P0 — Site down** | `/api/health` returns non-200 for > 5 minutes | 15 minutes | 4 hours |
| **P1 — Major degradation** | One subsystem (auth / DB / push) fully unavailable; or > 10% of requests failing | 1 hour | 12 hours |
| **P2 — Minor degradation** | One non-critical feature impaired; or 1–10% of requests failing | 4 hours | 3 business days |
| **P3 — Cosmetic / non-blocking** | UI bug, doc typo, missing translation | Next business day | Next minor release |

### 4.2 Communication

- **P0 / P1**: posted within 30 minutes to the deployment's
  status page (`{PUBLIC_URL}/status`) AND emailed to all
  designated incident contacts at the institutional deployer.
- **P2 / P3**: posted to the status page within 4 business hours;
  monthly summary emailed.

### 4.3 Post-incident reports (P0 / P1 only)

A blameless post-incident report (PIR) is published within
**5 business days** of resolution. The PIR includes: timeline,
root cause, contributing factors, what worked, what didn't,
concrete remediation actions with owners + dates.

---

## 5. Data protection + GDPR

### 5.1 Roles

- **{HOSTING_PARTY}** acts as **Auftragsverarbeiter** (processor) per
  Art. 28 GDPR.
- **{INSTITUTIONAL_DEPLOYER}** is the **Verantwortlicher** (controller)
  for end-user data processed through the deployment.

### 5.2 Data Processing Agreement (DPA)

A separate DPA per GDPR Art. 28 governs the data-processing
relationship. Template DPA at
[`compliance/dpa-template.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/dpa-template.md).
The DPA covers:

- Categories of personal data processed (identity / CV / outcomes
  / chat content)
- Purposes of processing
- Sub-processor list (AI providers, aggregator job boards, SMTP)
- Data location (EU / EEA only, by default)
- Technical and organisational measures (TOMs) — encryption at
  rest via ChaCha20-Poly1305 AEAD; encryption in transit via TLS
  1.3; access control via SSO when configured; audit log per
  Art. 12

### 5.3 Recovery point + recovery time objectives

| Metric | Target | Notes |
|---|---|---|
| **RPO** (max data loss) | 24 hours | Encrypted nightly backups; backup-verify drill quarterly |
| **RTO** (max recovery time after total loss) | 8 hours | Cold-start from latest backup + DNS cutover |

---

## 6. Maintenance windows

- **Planned**: weekly window **{WEEKDAY} {TIME_RANGE} {TZ}**.
  Up to 60 minutes per occurrence. Notified to deployer
  contacts ≥ 72 hours in advance.
- **Emergency**: deployer notified within 30 minutes of decision
  to enter emergency maintenance.

Maintenance windows do not count against the uptime tier targets.

---

## 7. Reporting

| Cadence | Report contents | Delivery |
|---|---|---|
| Monthly | uptime per tier, p50/p95/p99 latencies, incident count by severity, GDPR data-subject-request count, AI-invocation total cost | PDF + raw CSV emailed to designated contact |
| Quarterly | Trend analysis, change-management summary, sub-processor changes, backup-restore drill results | PDF emailed |
| Annual | SLA performance vs target review, recommended tier adjustments | Joint review meeting + PDF |

---

## 8. Limitations of liability

Standard mutual indemnification per the underlying deployment
agreement. SLA credits for tier breaches per **Appendix A**
(populated during contract negotiation; default template: 5%
credit per 0.1% below target, capped at 25% of monthly fee).

---

## 9. Force majeure

Outages caused by events outside the hosting party's reasonable
control — including but not limited to:

- Acts of God, government action, war, civil unrest
- Failures of third-party infrastructure not contracted by the
  hosting party (e.g., hyperscaler regional outages, ISP routing
  failures, EU-wide DNS outages)
- Coordinated attacks (DDoS, supply-chain compromise) that
  exceed the deployment's contracted mitigation capacity

are excluded from uptime calculations. The hosting party will
communicate the impact within the standard incident-response
timelines above and will not claim force majeure for routine
incidents.

---

## 10. Modifications

This SLA may be amended only by mutual written agreement of
both parties. Changes take effect at the start of the calendar
month following signature.

---

## Appendix A — SLA credits

To be negotiated per contract. Default template:

| Uptime achieved | Credit applied |
|---|---|
| ≥ target | 0% |
| 0.1% – 0.5% below | 5% credit |
| 0.5% – 1.0% below | 10% credit |
| 1.0% – 2.0% below | 15% credit |
| > 2.0% below | 25% credit (cap) |

Credits applied against the following month's invoice.

---

## Appendix B — Incident-contact registry

To be filled at contract execution:

| Contact role | Name | Email | Phone | TZ | Hours |
|---|---|---|---|---|---|
| Primary on-call | | | | | |
| Secondary on-call | | | | | |
| Deployer escalation | | | | | |
| GDPR / DPO contact | | | | | |

---

## Provenance

- Authored 2026-05-22 (phase2-backlog #30) as a procurement-ready
  starting template for institutional deployers.
- Mirrors the discipline already enforced in code (HMAC-chained
  audit log per Art. 12, encryption at rest per Art. 32, portable
  export per Art. 20, cost-cap chokepoint, source-class hierarchy
  for AI outputs).
- Not legal advice. Both parties should have a qualified DACH
  data-protection lawyer review the populated version before
  signature.
