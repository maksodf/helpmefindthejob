<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Audit Log Schema

**Audience**: provider, deployer, oversight person, and any auditor reviewing the system's Article 12 record-keeping.
**Article**: AI Act Article 12 (record-keeping).
**Pairs with**: [`../company_discovery/audit_log.py`](../company_discovery/audit_log.py) (the emitter) and the `/api/admin/oversight/queue` admin endpoint.
**Status**: living document. The on-disk schema is versioned; this document reflects schema **v1**.

---

## 1. Why this exists

Article 12 of [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) requires high-risk AI systems to automatically record events ("logs") with sufficient granularity to identify situations that may result in the system presenting a risk, and to enable post-market monitoring (Article 72) and any operational checks under Article 26.

The Helpmefindthejob audit log is **append-only JSONL** stored at `${DATA_ROOT}/ai_act_audit.log` (configurable). It is **separate from** the existing admin-action audit log (`admin_audit.log`) — admin actions and AI Act compliance events have different audiences, retention requirements, and access patterns.

---

## 2. File format

- **One JSON object per line**, newline-terminated. UTF-8. No leading byte-order mark.
- **Append-only**: emitters open with `O_APPEND` semantics; rotation is a background job, not in-band.
- **Rotation**: when the file exceeds `DIRECTJOB_AUDIT_ROTATE_BYTES` (default 64 MiB), it is renamed to `ai_act_audit.log.{YYYYMMDD-HHMMSS}` and a new file is opened.
- **Retention**: files older than `DIRECTJOB_AUDIT_RETENTION_DAYS` (default 180) are eligible for deletion by the deployer's retention job. The provider does **not** delete; the deployer holds the retention decision per their jurisdiction.

---

## 3. Common envelope

Every event record has these fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | Always `"v1"` for this schema. |
| `event_id` | string (UUID v4) | yes | Unique identifier for this event. |
| `event_type` | string (enum) | yes | One of the event types in §4. |
| `timestamp` | string (ISO 8601, UTC, microsecond precision) | yes | When the event happened. |
| `user_opaque_id` | string (64-char hex SHA-256) or `null` | yes | Stable per-user opaque ID, hashed from the user's internal ID + `DIRECTJOB_AUDIT_SALT`. `null` for system-internal events. |
| `session_opaque_id` | string (64-char hex SHA-256) or `null` | yes | Stable per-session opaque ID. `null` for non-session contexts (e.g. MCP stdio invocations from a sibling agent). |
| `caller` | string | yes | One of `"web"`, `"mcp"`, `"cli"`, `"system"`. |
| `journey_phase` | string (enum) | no | The 12-phase journey state machine phase active when the event happened, if applicable. |
| `prompt_template_id` | string (8-char hex) | no | Stable hash of the prompt template used (AI-invocation events only). |
| `ai_provider` | string | no | Identifier of the AI provider used (AI-invocation events only). `"none"` for deterministic fallback. |
| `tokens_in` | integer | no | Prompt tokens (AI-invocation events only). |
| `tokens_out` | integer | no | Response tokens (AI-invocation events only). |
| `duration_ms` | integer | yes | Wall-clock duration of the event. |
| `outcome` | string (enum) | yes | One of `"ok"`, `"declined"`, `"error"`, `"timeout"`. |
| `error_class` | string | no | The exception class name (outcome=`"error"` only). |
| `event_payload` | object | no | Event-type-specific structured fields (see §4). PII fields are hashed by default. |

---

## 4. Event types

### 4.1 `ai_invocation`

Emitted for every call to an AI provider in [`../company_discovery/analysis.py`](../company_discovery/analysis.py) or [`../company_discovery/ai_providers.py`](../company_discovery/ai_providers.py).

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `purpose` | string (enum) | `"fit_score"` / `"cover_letter"` / `"tailor_cv"` / `"motivation_letter"` / `"skill_gap_brief"` / `"application_outcome_analysis"` |
| `job_opaque_id` | string (hashed) or `null` | The job the AI call relates to (if any). |
| `cv_section_opaque_ids` | array of strings (hashed) | Which CV sections were included in the prompt slice. |
| `prompt_hash` | string (16-char hex SHA-256 prefix) | Stable hash of the exact prompt sent. |
| `response_hash` | string (16-char hex SHA-256 prefix) | Stable hash of the AI's response. |
| `score_adjustment_factor` | float or `null` | The AI's bounded adjustment factor for fit-scoring (capped at ±0.15). |

### 4.2 `mcp_tool_invocation`

Emitted for every MCP tool call dispatched by [`../company_discovery/mcp_tools.py`](../company_discovery/mcp_tools.py).

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `tool_name` | string | The MCP tool name (e.g., `"find_company_career_page"`). |
| `arguments_hash` | string (16-char hex SHA-256 prefix) | Hash of the validated arguments JSON. |
| `response_size_bytes` | integer | Size of the JSON response. |
| `composition_source` | string or `null` | Identifier of the composing civic agent if known (from the MCP `clientInfo`); `null` for direct invocations. |

### 4.3 `persistence_confirmation`

Emitted when a user explicitly confirms a database write (job applied, application withdrawn, profile field edited).

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `entity_type` | string (enum) | `"application"` / `"profile_field"` / `"cv_section"` / `"saved_search"` / `"job_bookmark"`. |
| `entity_opaque_id` | string (hashed) | The opaque ID of the affected entity. |
| `action` | string (enum) | `"create"` / `"update"` / `"delete"` / `"export"`. |

### 4.4 `consent_event`

Emitted when the user grants, revokes, or modifies any consent (AI-provider consent, third-party-share consent, MCP-composition consent).

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `consent_topic` | string (enum) | `"ai_provider"` / `"third_party_share"` / `"mcp_composition"` / `"audit_log_plaintext_pii"`. |
| `consent_state` | string (enum) | `"granted"` / `"revoked"` / `"modified"`. |
| `consent_scope` | string or `null` | Free-text scope for `"modified"`, otherwise `null`. |

### 4.5 `export_event`

Emitted on every export of personal data (GDPR Article 20 portability, profile export, audit-log extract for the user's own data).

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `export_kind` | string (enum) | `"profile_full"` / `"profile_partial"` / `"audit_log_self"` / `"eures_export"`. |
| `export_size_bytes` | integer | Size of the exported artefact. |
| `format` | string | The MIME type or schema name of the export. |

### 4.6 `override_event`

Emitted when the human-oversight person edits, rejects, or annotates an AI output in advisor-review mode.

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `original_event_id` | string (UUID v4) | The `event_id` of the AI invocation being overridden. |
| `override_action` | string (enum) | `"approve"` / `"edit"` / `"reject"` / `"annotate"`. |
| `override_note_hash` | string (16-char hex SHA-256 prefix) or `null` | Hash of the annotation note (if `"annotate"`). |
| `overseer_opaque_id` | string (hashed) | The hashed identifier of the human-oversight person. |

### 4.7 `system_event`

Emitted for system-level events that do not fit the above types (config reload, AI-provider failover, kill-switch activation).

`event_payload`:

| Field | Type | Description |
|---|---|---|
| `system_event_kind` | string | Free-form identifier of the event class. |
| `details` | object | Event-specific structured fields. |

---

## 5. PII hashing default and the plaintext opt-in

By default, all PII fields (`user_opaque_id`, `session_opaque_id`, `job_opaque_id`, `entity_opaque_id`, `overseer_opaque_id`, `cv_section_opaque_ids`, `override_note_hash`, `prompt_hash`, `response_hash`, `arguments_hash`) are stored as **hashes**, not plaintext.

The hash function is **SHA-256** over the canonical value + the deployment-time `DIRECTJOB_AUDIT_SALT` (32-byte random secret). The salt is set per deployment. If the salt is rotated, prior hashes are no longer linkable to current ones; this is a deliberate retention-control mechanism the deployer may use to enforce time-bounded linkability.

**Plaintext opt-in**: a deployer with a specific legal need (court order, regulatory request) may set `DIRECTJOB_AUDIT_PLAINTEXT_PII=true`. In that mode, certain fields hold plaintext values rather than hashes. Plaintext mode is logged as a `consent_event` with `consent_topic="audit_log_plaintext_pii"` and `consent_state="modified"` on each config reload, so the policy change is itself auditable.

---

## 6. Retention

The default retention is 180 days. Deployers configure via `DIRECTJOB_AUDIT_RETENTION_DAYS`. The minimum recommended retention is **6 months** to satisfy typical post-incident investigation windows under Article 26(6) and to allow for the 6-monthly bias-testing methodology re-run.

The deployer's retention job is **not provided** by the project (deployer responsibility). A sample cron script is included in [`../scripts/`](../scripts/) showing how to rotate and prune old log files.

---

## 7. Query examples

### 7.1 Count AI invocations by purpose in the last 30 days

```bash
cat ${DATA_ROOT}/ai_act_audit.log{,.*} | \
  jq -c 'select(.event_type=="ai_invocation" and (now - (.timestamp|fromdateiso8601)) < 30*86400) | .event_payload.purpose' | \
  sort | uniq -c | sort -rn
```

### 7.2 Find all events for a specific user_opaque_id

```bash
cat ${DATA_ROOT}/ai_act_audit.log{,.*} | \
  jq -c --arg uid "${USER_OPAQUE_ID}" 'select(.user_opaque_id==$uid)'
```

### 7.3 Surface kill-switch activations

```bash
cat ${DATA_ROOT}/ai_act_audit.log{,.*} | \
  jq -c 'select(.event_type=="system_event" and .event_payload.system_event_kind=="kill_switch_activated")'
```

### 7.4 Surface fit-scoring outcomes with notable AI adjustment

```bash
cat ${DATA_ROOT}/ai_act_audit.log{,.*} | \
  jq -c 'select(.event_type=="ai_invocation" and .event_payload.purpose=="fit_score" and ((.event_payload.score_adjustment_factor // 0) | fabs) > 0.10)'
```

---

## 8. Schema evolution

If the schema needs to evolve, a new `schema_version` is introduced. The emitter is updated to write the new version. The previous version's emitter logic is retained for any in-flight rotation. Downstream tooling reads `schema_version` and dispatches accordingly.

The migration discipline mirrors the project's approach to other schemas (JSON Schema for MCP tools, encrypted-profile-at-rest format) — additive, with read-side back-compatibility.

---

## 9. What the audit log is **not**

- It is **not** a substitute for application logs. Operational debugging logs live separately and have their own retention.
- It is **not** a record of every HTTP request. It records the AI-relevant events specifically.
- It is **not** intended for user-visible activity logs. Users see their own activity in the chat journey and profile views, which read from the primary database, not from the audit log.
- It is **not** shipped to the provider. The provider has no access to deployer audit logs; the log lives on the deployer's infrastructure.

---

## 10. Append log

- **2026-05-18**: schema v1 drafted as part of Week 2 task 2.8 of the NLnet NGI Zero Commons Fund grant sprint. Emitter implementation in [`../company_discovery/audit_log.py`](../company_discovery/audit_log.py) and tests in `tests/test_phase13_audit_log.py`.
