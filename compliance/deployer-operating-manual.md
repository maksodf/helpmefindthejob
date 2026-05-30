<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Deployer Operating Manual

**Audience**: **you, the institutional deployer of Helpmefindthejob** — a Beratungsstelle, IQ-Netzwerk regional office, Optionskommune Jobcenter, university career service, NGO, civic-tech operator, or self-hoster running the system on your own infrastructure.
**Article**: AI Act Article 13 (transparency to deployers) and Article 26 (deployer obligations).
**Status**: living document. Updated alongside every major release.

---

## What this manual is, and what it is not

This is the working manual you need to operate Helpmefindthejob under your AI Act Article 26 deployer obligations. It covers configuration, human-oversight setup, retention controls, data-subject-request handling, incident reporting, and the local-context fields you must complete before going live.

This is **not** legal advice. Where you have specific legal questions — your jurisdiction's data-protection regime, your sector-specific employment regulations, the exact contours of your Article 26 obligations — those go to your counsel. This manual reduces the technical and documentation burden, not the legal review.

---

## 1. Who you can serve with this tool

Helpmefindthejob serves **anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work**. This is the architectural design target, encoded in Decision 21 of the project's planning workspace.

In practical terms for you as a deployer:

- **If you are a Migrationsberatungsstelle (MBE)**, an IQ-Netzwerk office, or a Jugendmigrationsdienst (JMD)**: the migrant subset of the friction class is your mandate. The tool's most-acute-use-case persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria) was designed against the situations your clients face. Recognition-friendly employer matching, ESCO mapping for foreign credentials, multilingual support, Anerkennung-aware journey paths — these are the system's strongest evidence base. Deploy with confidence.
- **If you are an Optionskommune Jobcenter**: you serve **all** Bürgergeld recipients, not just the migrant subset. The friction-class framing means you can deploy the same tool for *your full caseload*. Migrant clients receive the most-acute features; non-migrant clients facing CV-currency gaps, career transitions, or re-entry after extended absence (the kind of friction Käthe and Tobias represent in the persona panel) receive the same tool tuned to their situation. You do not need to procure separate tools for "the migrant caseload" and "the rest of the caseload."
- **If you are a university career service**: your population is international graduates (who become migrant jobseekers post-graduation) **plus** first-generation graduates without family-networked guidance through professional conventions **plus** career changers among your alumni. The friction-class framing covers all three; the persona panel includes both the migrant-graduate scenarios and the career-pivot scenario (Tobias — German native, commercial-tech to civic-tech).
- **If you are an NGO operating in adult education, return-to-work programmes, or career-coaching for workers re-entering after caregiving**: Käthe is the persona built around your population. The tool handles Wiedereinstieg-programme matching, twelve-year-CV-gap reframing, and 2026-format-CV scaffolding — alongside everything the migrant features provide.
- **If you are a self-hoster running Helpmefindthejob for yourself or a small community**: there is no separate enterprise tier; the same tool, same features.

The cost-saving doctrine ([`docs/grant/08-cost-saving-doctrine.md`](https://github.com/maksodf/helpmefindthejob/blob/main/docs/grant/08-cost-saving-doctrine.md)) is built on the friction-class addressable population, not on the migrant-only one. The "advisor caseload" cost-saving mechanism applies to every advisor-client interaction in the friction class, not only migrant cases. If your finance department asks how the tool's value is bounded by demographic, the answer is: it isn't.

---

## 2. Your Article 26 obligations as the deployer

Article 26 of [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) places the following obligations on you (the deployer of a high-risk AI system):

| Obligation | Article | What this means concretely | Where addressed |
|---|---|---|---|
| Use the system in accordance with its instructions | Art. 26(1) | Follow this manual and `transparency-notice.md`. | This document. |
| Ensure input data is relevant and representative | Art. 26(4) | Make sure user profiles capture the friction your caseload actually faces. | §4 below. |
| Monitor operation | Art. 26(5) | Set up the human-oversight person; review the audit log on the cadence your jurisdiction requires. | §5–§6 below. |
| Inform natural persons | Art. 26(11) + Art. 50 | Tailor the `transparency-notice.md` addendum for your context, surface it at first run. | `transparency-notice.md` and §7 below. |
| Keep automatically generated logs | Art. 26(6) | Retain the audit log per your retention policy; minimum 6 months recommended. | §6 below; `audit-log-schema.md`. |
| Conduct Fundamental Rights Impact Assessment (public-authority deployers) | Art. 27 | Complete the FRIA template before going live. | `fundamental-rights-impact-assessment-template.md`. |
| Register the high-risk AI system in the EU AI database | Art. 49 | Complete the registration template; submit to the EU AI database. | `eu-database-registration-template.md`. |
| Report serious incidents | Art. 73 | Notify your supervisory authority within the regulatory window; the provider supports with technical details. | §10 below. |

This list is not exhaustive. Specific sectors (public-sector employment services, regulated-profession advisors) may have additional sectoral obligations. Check with your counsel.

---

## 3. Pre-deployment checklist

Before going live, complete each of these in order. None is optional.

- [ ] Read this manual end-to-end.
- [ ] Read `transparency-notice.md` and fill in the `[Deployer-managed addendum]` section with your organisation-specific values.
- [ ] Read `audit-log-schema.md` and decide your retention policy (default 180 days; minimum 6 months recommended).
- [ ] Choose your AI provider(s). The transparency notice tells users what to expect; the configuration is per `§4 — Configuration` below.
- [ ] Decide whether to enable human-oversight review mode (`HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE`). See `human-oversight-guide.md`.
- [ ] Appoint the human-oversight person and complete the `human-oversight-guide.md` §"Appointment record" section.
- [ ] If your organisation is a public authority: complete the FRIA in `fundamental-rights-impact-assessment-template.md` and lodge it per Article 27.
- [ ] Complete the EU AI database registration template in `eu-database-registration-template.md` and submit before going live (Article 49).
- [ ] Set the deployment-time secrets: `HELPMEFINDTHEJOB_SECRET_KEY` (32 random bytes), `HELPMEFINDTHEJOB_AUDIT_SALT` (32 random bytes), `HELPMEFINDTHEJOB_PUBLIC_URL`, admin credentials, SMTP for outbound notifications.
- [ ] Run the bias-testing methodology against your chosen AI provider (`accuracy-and-bias-testing.md` §"Pre-deployment re-test").
- [ ] Verify backup and restore drills against your data infrastructure (`scripts/backup-*` and `scripts/restore-*` are provided).
- [ ] Brief your advisors and oversight person on the system's capabilities and limitations (`transparency-notice.md` §"Limitations").
- [ ] Decide which user populations you serve and tailor the chat-router's persona-friendly greetings accordingly (see §4.3 below).
- [ ] Document your **Article 22 right-to-human-review procedure** (see §8.1 below) — who receives escalation requests, the response-time SLA, the artefact retention policy, and how the verdict is communicated back to the user.

---

## 4. Configuration

### 4.1 Environment variables

The complete list lives in [`.env.example`](https://github.com/maksodf/helpmefindthejob/blob/main/.env.example). The AI-Act-relevant ones:

| Variable | Default | What it controls |
|---|---|---|
| `HELPMEFINDTHEJOB_SECRET_KEY` | (required) | The ChaCha20-Poly1305 AEAD key for profile-at-rest encryption. 32 random bytes, base64-encoded. |
| `HELPMEFINDTHEJOB_AUDIT_SALT` | (required) | The per-deployment salt for the user_opaque_id hashing in the audit log. 32 random bytes, base64-encoded. |
| `HELPMEFINDTHEJOB_AUDIT_RETENTION_DAYS` | `180` | Retention window for audit-log files. Deployer-set per jurisdiction. |
| `HELPMEFINDTHEJOB_AUDIT_ROTATE_BYTES` | `67108864` (64 MiB) | Rotation threshold. |
| `HELPMEFINDTHEJOB_AUDIT_PLAINTEXT_PII` | `false` | Set to `true` only with documented legal justification. Logs `consent_event` on each config reload to make policy change auditable. |
| `HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE` | `disabled` | `enabled` activates the advisor-review queue at `/api/admin/oversight/queue`. |
| `HELPMEFINDTHEJOB_AI_PROVIDER` | `manual` | Which AI provider is the default (`openai` / `anthropic` / `gemini` / `deepseek` / `openrouter` / `ollama` / `manual` / `claude-code` / `none`). Users can override per-request. |
| `HELPMEFINDTHEJOB_DETERMINISTIC_ONLY` | `false` | Kill-switch. When `true`, the app invokes no AI provider on any code path; each AI-assisted feature falls back to its no-AI path (letter drafting → a deterministic templated skeleton; fit-scoring / CV-tailoring → a BYO-AI handoff prompt). |

### 4.2 Deployment files

- `docker-compose.prod.yml` — the production Docker Compose configuration with Caddy HTTPS.
- `.env` — your filled-in environment variables.
- `data/` — the application data directory. Encrypted-at-rest profile data lives here. **This directory contains personal data; back it up encrypted and treat it with the care your jurisdiction requires.**

### 4.3 Persona-friendly chat-router greetings

The chat router opens with a greeting that surfaces the most likely user journeys for your population. The default greeting names the seven personas as examples of who the system serves. You can tailor this for your context — e.g., a Jobcenter deployer may add a "starting from a Bürgergeld referral" path; an IQ-Netzwerk deployer may emphasise the Anerkennung path. The tailoring is a one-line entry in your `i18n` override bundle (see `static/i18n/<locale>.override.json`).

### 4.4 Language

EN and DE are shipped. Arabic, Ukrainian, Turkish, and Romanian are on the roadmap as native-speaker contributors join. If your population's languages are not yet shipped, you can either (a) wait for the upstream additions, (b) contribute translations under the translator-contributor pathway, or (c) deploy with EN+DE and accept the limitation in your transparency-notice addendum.

---

## 5. Human oversight setup

The full guide is at [`human-oversight-guide.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/human-oversight-guide.md). Summary for deployment-time:

1. **Appoint a named oversight person.** This must be someone with the competence to assess fit-scoring outputs, motivation-letter drafts, and CV-tailoring suggestions for accuracy and fairness in your sector. For a Beratungsstelle, this is typically a senior advisor. For a Jobcenter, a Case Manager. For a university career service, the head of career advising. The person's contact appears in the `transparency-notice.md` addendum.
2. **Decide review mode**: `HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE=disabled` (default, AI outputs reach the user directly) vs `enabled` (AI outputs queue for advisor review at `/api/admin/oversight/queue`). The trade-off is between throughput and oversight depth. Public-authority deployers typically choose `enabled` at first deployment and de-escalate after a documented track record.
3. **Document the kill-switch policy**: under what conditions the oversight person activates `HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true`. The policy lives in your operational runbook; the kill-switch action itself is recorded in the audit log.

---

## 6. Audit log handling

### 6.1 Where it lives

`${DATA_ROOT}/ai_act_audit.log`, with rotated files alongside.

### 6.2 Retention

Default 180 days. You set the value to match your jurisdiction. Minimum 6 months recommended to satisfy typical post-incident investigation windows. Some jurisdictions or sectors require longer.

### 6.3 Access

Restrict filesystem access to the deployment's data directory. The provider does not access the audit log; it lives only on your infrastructure. The oversight person typically has read access via the `/api/admin/oversight/queue` endpoint and via SSH for direct log inspection.

### 6.4 Query

See [`audit-log-schema.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/audit-log-schema.md) §7 for query examples. Common operational queries:

- Count of AI invocations per user per day (anomaly detection)
- Distribution of fit-score adjustments across the persona cohort (bias indicator)
- Time-to-first-application across the persona cohort (effectiveness indicator)

### 6.5 Export for users (GDPR Article 20)

When a user requests their audit-log slice (Article 86 explanation right or GDPR right of access), the system constructs a per-user export filtered on the user's opaque ID. The export is logged as an `export_event` for completeness.

---

## 7. User-facing transparency

You are responsible for ensuring that users of your deployment see the transparency notice at first run and any time substantive system behaviour changes. The notice at [`transparency-notice.md`](transparency-notice.md) is the source of truth; you complete the `[Deployer-managed addendum]` section before going live. The rendered version is served at `/settings/transparency` in the application.

In addition to the on-screen notice, consider:

- A printed handout in your physical Beratungsstelle / Jobcenter / career-service space that points to the URL.
- A linked entry in your organisation's privacy policy.
- A short briefing for the advisors who will direct users to the tool.

---

## 8. Data subject rights

Users have the GDPR rights enumerated in `transparency-notice.md` §"Your rights". As the deployer, you operationally handle data-subject requests. The system provides the technical primitives (`/api/data/export`, `/api/account/deletion`, audit-log self-export); your team handles the process around them (verifying the requester's identity, responding within the GDPR window, documenting the response).

A request log lives separately from the audit log (it is itself a record of the request, not the technical event); your data-protection officer typically owns this log.

### 8.1 Article 22 / Article 86 right to human review of an AI decision

GDPR Article 22 gives every user the right not to be subject to a decision based solely on automated processing that produces legal effects or similarly significantly affects them. AI Act Article 86 strengthens that right for high-risk AI systems: any user **affected by an output** of a high-risk system can request a structured explanation, and where the output is a decision (or feeds one) they can request human review.

In Helpmefindthejob's context, the AI-assisted outputs that can rise to "significant effect" are:

- Fit scores that influence which jobs the user applies to.
- CV-tailoring suggestions and motivation-letter drafts that go to a real employer.
- Auto-classification of journey state (e.g., flagging a role as "out of scope") that hides options from the user.
- Auto-generated rejection-of-fit narratives that the user might internalise as discouraging.

The user-facing notice at [`transparency-notice.md` §"Right to an explanation (Article 86 and GDPR Article 22)"](transparency-notice.md) tells users this right exists and how to invoke it. **You as deployer own the procedure that handles the request.** This subsection is the operational requirement.

**Mandatory procedure** — document it locally, exercise it on a quarterly drill, log every real invocation:

1. **Receiver**: name the oversight person (or a queue / shared mailbox they monitor) who receives escalation requests. The contact appears in your `transparency-notice.md` `[Deployer-managed addendum]`. For Beratungsstellen this is typically a senior advisor; for Jobcentern a Case Manager; for university career services the head of career advising. The receiver must be **a human, not a chatbot or automated triage tool** — Article 22 explicitly bars automation from being the gatekeeper of its own appeal.

2. **Intake artefact**: when the request arrives, capture (a) the AI output being challenged (copy/paste plus the audit-log entry ID — see `audit-log-schema.md` §3 for the ID format), (b) the user's stated reason for challenging it, (c) the user's preferred outcome. The audit-log entry ID is the load-bearing reference because it lets the reviewer pull the exact prompt, model, version, and provider that produced the output — none of which are stored on the user-facing surface.

3. **Review SLA**: respond substantively within **1 calendar month** of receipt (GDPR Article 12(3)). Acknowledgement of receipt within **3 working days** is the operational target — the user should never wonder whether the request was lost. Where the request is complex you may extend by a further 2 months under GDPR Article 12(3), but you must explain the extension reason to the user within the original 1-month window.

4. **Review depth**: the reviewer is **not** required to re-do the AI's work from scratch. The standard is whether the AI output is **defensible in context** — does the prompt match what the user requested, did the model have the right inputs, are the criteria the AI used appropriate for this user's situation. Where the output is defensible, the reviewer confirms it with a written explanation. Where it is not, the reviewer issues a corrected output, marked clearly as human-issued.

5. **Communicate the verdict**: the response to the user must include (a) whether the AI output stands, is corrected, or is overturned; (b) the reasoning in plain language at the level of the user's stated reason for challenging; (c) the corrected output if applicable; (d) the user's onward rights (right to lodge a complaint with the supervisory authority — see §"Right to lodge a complaint" in `transparency-notice.md`).

6. **Retention**: keep the intake artefact, the reviewer's notes, the verdict, and any corrected output for **the longer of**: (a) your audit-log retention window (§6.2 above; default 180 days), (b) your jurisdiction's data-protection-request retention requirement (typically 3 years for the request log under GDPR accountability obligations), (c) any pending investigation or supervisory authority engagement period. The retention is separate from the audit log because the request itself is a record-of-request, not an AI-output event.

7. **Log the review action itself**: invoke `/api/admin/oversight/review` (or your equivalent operational endpoint) so the **fact that a human review took place** is itself an audit-log entry. The entry records reviewer identity (opaque ID), referenced audit-log entry ID, verdict, and timestamp — never the AI output verbatim, which would defeat the encrypted-at-rest pseudonymisation discipline. This closes the Article 26(6) automatic-log obligation around the review event.

8. **Aggregate review**: at least quarterly, the oversight person produces a short anonymised summary of the requests received, the verdicts, and any patterns. Patterns that recur (e.g., "fit-score for nursing roles consistently challenged by §16d applicants and consistently corrected") feed your next bias-testing run (§9.2) and may merit a `incident-ai-act`-tagged issue to the upstream project.

**Article 22 vs Article 14 vs Article 26**: these obligations layer rather than duplicate. Article 14 (provider obligation) requires the system be **designed for** human oversight — the project ships `HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE`, the `/api/admin/oversight/queue`, and per-output explanation surfaces to satisfy this. Article 26 (deployer obligation) requires you to **exercise** that oversight in practice. Article 22 (user right) creates the **per-request appeal** that this subsection covers. The full chain works only if all three are wired.

**Common drift to avoid**: do not configure the chat router to auto-respond to "show me a human" requests with a templated "your request has been logged" message and no human action. Do not allow Article 22 requests to be triaged by AI to decide whether they merit human review. Do not let the response SLA slip silently — the standard is response, not acknowledgement. Document the procedure even if you have never received a request — the absence of requests is not proof the right is honoured.

---

## 9. Operational tasks

### 9.1 Patching

Subscribe to the project's release feed (GitHub Releases). Apply security patches within 30 days; minor releases within 90 days. Major releases include a compliance-pack review; budget time for the deployer-side re-review accordingly.

### 9.2 Bias-testing re-run

At least every 12 months, re-run the bias-testing methodology against your current AI provider. Document the result. If the result is materially worse than the previous run, treat it as a Sev-2 incident (see §10).

### 9.3 Backup and restore

The project ships `scripts/backup-*.sh` and `scripts/restore-*.sh`. Run a restore drill at least quarterly. Document the result.

### 9.4 TLS renewal

Caddy auto-renews certificates. Verify via the `scripts/check-tls-expiry.sh` monitoring script.

### 9.5 Health checks

`/api/health?detailed=1` exposes a structured health surface, including encryption-at-rest status, audit-log writability, AI-provider reachability, and database integrity. Connect to your monitoring system.

---

## 10. Incident response

If you encounter or are informed of an incident involving Helpmefindthejob in your deployment:

1. **Stabilise**: if the incident is ongoing and involves automatic harm (e.g., systematic bias against a documented persona class), activate the kill-switch (`HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true`) until you have understood and contained the issue.
2. **Document**: capture the relevant audit-log slice, the user's reported experience, and the system state at the time of incident.
3. **Notify**:
   - **Internal**: your data-protection officer, your oversight person, your organisation's relevant senior accountable individual.
   - **The provider**: via [`SECURITY.md`](https://github.com/maksodf/helpmefindthejob/blob/main/SECURITY.md) for security-related incidents or via a GitHub Issue tagged `incident-ai-act` for AI-Act-related incidents. The provider acknowledges within 5 working days and supports with technical analysis.
   - **Supervisory authority**: per Article 73, serious incidents are notified to the relevant market-surveillance authority within the regulatory window (15 days for general serious incidents, 2 days for incidents involving widespread infringement). Your jurisdiction's data-protection authority may also need notification under GDPR Article 33 if the incident is a personal-data breach.
4. **Remediate**: apply the technical and procedural mitigations the joint analysis identifies.
5. **Post-incident review**: document the incident, the remediation, and any policy or configuration changes that result. This documentation feeds your next risk-register review and may inform the provider's risk-register update for the upstream project.

---

## 11. Decommissioning

When you decommission a deployment:

1. Notify users at least 30 days in advance with clear instructions on how to export their data.
2. Honour all in-flight data-subject requests under their original timing.
3. Retain the audit log for the legally-required minimum after decommissioning (typically the longer of your retention policy and any pending investigation period).
4. Securely erase encrypted-at-rest data after the retention window expires.
5. Notify the project provider (via GitHub Discussions or maintainer contact) so we can update our list of known deployers for the post-market monitoring plan.

---

## 12. Limitations of this manual

This manual is a single document. It does not replace:

- Your organisation's privacy policy
- Your organisation's data-protection impact assessment for the deployment context
- Your organisation's sector-specific compliance framework
- Your legal counsel
- Direct dialogue with your jurisdiction's data-protection authority on novel questions

If something in your context is not covered here, raise an issue on the project repository or contact the maintainer; recurring deployer questions will be folded into future revisions.

---

## 13. Append log

- **2026-05-18**: initial deployer operating manual drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint.
- **2026-05-24**: finalised with §8.1 "Article 22 / Article 86 right to human review of an AI decision" — an 8-step operational procedure (receiver, intake artefact, SLA, review depth, verdict communication, retention, log-the-review-action, aggregate review) plus the layering note distinguishing Article 14 (provider) / Article 26 (deployer) / Article 22 (user right). Pre-deployment checklist updated with the corresponding documentation item. Closes the gap that prior versions covered Article 26 obligations table at §2 + provider-side human-oversight at §5, but never spelt out the operational procedure for handling the per-user appeal — leaving deployers to invent the workflow at first request.
