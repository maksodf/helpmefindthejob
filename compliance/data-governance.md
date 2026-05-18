<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Data Governance

**Audience**: provider, deployer, and any external reviewer assessing how the project handles personal data flowing through the AI system.
**Article**: AI Act Article 10 (data and data governance).
**Status**: living document. Reviewed alongside the risk register every six months.

---

## 1. Why Article 10 applies differently here

Article 10 of the AI Act requires that **training, validation, and testing data sets** be relevant, representative, free of errors, and complete, with documented bias detection.

DirectJob Scout **does not train models on user data**. The project orchestrates prompts to third-party general-purpose AI providers through the BYO-AI abstraction at [`company_discovery/ai_providers.py`](../company_discovery/ai_providers.py). The user (or the deployer in an institutional configuration) supplies the AI provider. We compose prompts, we do not train.

The consequence: our Article 10 scope shifts from training-corpus governance to:

1. **What user data flows through prompts** to the AI provider (data minimisation, consent).
2. **What we log** about that flow (the audit log, Article 12).
3. **What we retain** locally for the user's profile (encryption-at-rest, retention policy).
4. **The quality of the prompts and fit-scoring rules** that constrain the AI's output (the validation surface).
5. **The bias-testing methodology** that anchors the fit-scoring against the persona panel (see [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md)).

This document describes each of those five layers. The user-facing equivalent is [`transparency-notice.md`](transparency-notice.md); the deployer-facing summary is in [`deployer-operating-manual.md`](deployer-operating-manual.md) §"Data handling".

---

## 2. Data categories handled

| Category | Examples | Storage | Encryption-at-rest | Sent to AI provider? | Retention default |
|---|---|---|---|---|---|
| Profile (identity-light) | Display name (user-chosen), preferred language, journey-phase state | Local DB | ChaCha20-Poly1305 | No | Until user deletes |
| CV facts | Profession, years of experience, certifications, ESCO-mapped skills, education | Local DB | ChaCha20-Poly1305 | Yes — minimised slice per AI call | Until user deletes |
| Job history (user-curated) | Roles applied to, employer, application status, application outcomes | Local DB | ChaCha20-Poly1305 | No | Until user deletes |
| Discovered jobs (system-curated) | Title, employer, posting URL, source, location, ESCO mapping, fit-score | Local DB | At rest only by storage engine; not field-level | Yes — sent in prompt context for fit-scoring and tailoring | Per `DIRECTJOB_DISCOVERED_JOBS_TTL_DAYS` (default 90 days) |
| Prompts and AI responses | The actual text sent to the AI and received back | Audit log (`ai_act_audit.log`) | At rest only by storage engine; PII fields hashed by default | n/a (this *is* the AI flow) | Default 6 months; configurable per deployer |
| Audit-log events | Tool invocations, AI invocations, persistence-confirmations | `ai_act_audit.log` (JSONL) | At rest only by storage engine; PII fields hashed by default | No | Default 6 months; configurable |
| Session / authentication | Login, 2FA TOTP secrets, session tokens | Local DB; TOTP-secret with AEAD wrapping | ChaCha20-Poly1305 (AEAD) for TOTP secrets | No | Per session lifetime / user-managed |

**PII hashing convention**: in the audit log, the `user_opaque_id` is a per-deployment SHA-256 over the user's stable internal ID plus a per-deployment salt (configured via `DIRECTJOB_AUDIT_SALT`). This lets a deployer reconstruct event sequences for a single user (for incident review or Article 86 explanation rights) without persisting the user's natural identifier in the audit log itself.

---

## 3. Encryption-at-rest

The profile-at-rest crypto is implemented in [`company_discovery/crypto_kit.py`](../company_discovery/crypto_kit.py) using **ChaCha20-Poly1305** (an AEAD cipher) from the `cryptography` library. The deployment-time secret key is configured via `DIRECTJOB_SECRET_KEY` (env var). Profile fields covered by encryption-at-rest:

- All free-text CV bullets (`experience.*`, `education.*`, `motivation.*`)
- The portable civic profile blob (the structured JSON sent in MCP composition)
- The 2FA TOTP secret (the AEAD migration in commit `fbeb2dc`)
- Email addresses and other contact info in the profile

The discovered-jobs and audit-log tables are not field-level encrypted; they are protected by storage-layer encryption-at-rest at the deployer's filesystem (typically LUKS-encrypted volume on a self-hosted deployment).

The maintainer's `crypto_kit` tests exercise the AEAD round-trip plus tampering detection; see `tests/test_phase0_encryption_at_rest.py` and `tests/test_aead_fuzzing.py`.

---

## 4. Data minimisation in AI invocations

Every AI invocation in [`company_discovery/analysis.py`](../company_discovery/analysis.py) is constructed to send the **minimum prompt necessary** for the task:

| AI call | What it sends | What it does NOT send |
|---|---|---|
| Fit-score (`compute_fit_score`) | Job posting text + relevant CV section (matched by ESCO codes) | Full profile, job-history, email, name |
| Cover-letter draft | Job posting + user-confirmed CV bullets + persona role-frame | Full profile, application history |
| CV tailoring | Job posting + the CV sections the user explicitly selected | Other CV sections, profile metadata |
| Motivation-letter draft | Role description + user-confirmed CV bullets | Job-history, profile metadata |
| Skill-gap brief | ESCO occupation code + user-confirmed skill list | Free-text CV |

The minimisation is enforced at the function-signature level: the call sites do not have access to the user's full profile, only the slice relevant to the call. This makes data over-egress a code change rather than a configuration mistake.

---

## 5. Prompt publication

To make the AI orchestration auditable, the prompt templates used for each AI call are published in code at [`company_discovery/analysis.py`](../company_discovery/analysis.py) and reviewable in any deployed instance. We do not consider prompts to be trade secrets; they are part of the project's design surface.

A change to a prompt template is a code change, reviewed via PR, with the diff visible. The audit log records the **prompt-template ID** (a stable hash over the template) for every AI invocation, so a deployer can correlate output-quality patterns with specific prompt versions.

---

## 6. Bias-testing methodology (cross-reference)

The bias-testing methodology is documented in detail in [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md). Summary anchor: the seven-persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) provides the test cohort. Each persona is run through the canonical journey phases with synthetic-but-realistic inputs; the system's fit-scoring, CV-tailoring, and motivation-letter outputs are compared against documented expectations. Bias is detected when a persona's outputs systematically diverge from the comparable-capability baseline in ways not attributable to documented friction-class differences.

The seven-persona cohort includes the wider-friction-class personas (Käthe and Tobias) specifically so that the bias-testing covers non-migrant users with structurally similar friction. Per Decision 21, the architecture is friction-driven not demographic-driven; the bias-testing follows the same shape.

---

## 7. Data-quality controls

Article 10(3) requires that data sets be "relevant, representative, free of errors and complete." For our prompt-construction surface:

- **Relevant**: prompts are constructed from structured profile data, not from free-text noise. ESCO mapping enforces canonical occupation codes.
- **Representative**: the persona panel covers the seven situations the project anchors on; bias-testing surfaces under-representation.
- **Free of errors**: the persistence layer rejects malformed input (input-schema validation; see `tests/test_phase11_mcp_input_validation.py`). User-edited fields go through the chat-router confirmation gate before any AI invocation.
- **Complete**: missing fields in a profile slice are filled with explicit `null` rather than guessed; the AI prompt is constructed to handle missing fields without hallucinating them.

The data-quality controls are tested in the standing 974-test suite, including:
- `tests/test_phase11_mcp_input_validation.py` — schema enforcement on MCP tool inputs
- `tests/test_phase12_esco_eures.py` — ESCO mapping correctness
- `tests/test_journey.py` — journey state-machine integrity
- `tests/test_phase12_mcp_integration_e2e.py` — full MCP integration

---

## 8. Data subject rights handling

Article 26(11) requires the deployer to enable data subjects to exercise GDPR rights. The system supports:

- **Right of access** (GDPR Art. 15): the user can export their full profile via `/api/profile/export`. The export is a structured JSON file plus the audit-log entries scoped to that user's opaque ID.
- **Right to rectification** (Art. 16): the user can edit any profile field via the chat router or the web UI.
- **Right to erasure** (Art. 17): the user can request deletion via `/api/profile/delete`. Deletion cascades to profile, CV facts, job-history, and discovered-jobs scoped to the user; the audit-log entries are retained for the legally-required retention period but with the user_opaque_id mapping deleted from the deployer's salt store, rendering the audit-log entries unlinkable to the natural person while preserving the compliance audit trail.
- **Right to data portability** (Art. 20): the profile export uses structured JSON Schema-defined formats. The portable civic profile is the cross-civic-agent format documented in the [MCP server docs](../docs/mcp-server.md).
- **Right to object / withdraw consent**: the user can revoke AI-provider consent at any time via `/api/profile/ai-consent`; subsequent flows fall back to deterministic templated mode.

---

## 9. Append log

- **2026-05-18**: initial data-governance documentation drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Next scheduled review: November 2026.
