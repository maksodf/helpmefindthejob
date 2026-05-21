# Database-error surfacing policy (Phase 2 #78)

Date: 2026-05-21
Status: **policy document**, binding on every database-write path
License: Apache 2.0
Origin: surfaced during PART 6 Loop 16 (Gate 6.5) error-layer audit
as Layer 11; deferred from PART 6 closure with an explicit
"cross-cutting design decision" framing.

---

## Why this policy exists

Pre-policy state: database-error handling was inconsistent across
the codebase. Some sites returned friendly 400 JSON with a `code`
field; others returned generic 500s with no recovery guidance; others
silently swallowed exceptions in best-effort `except Exception`
blocks. A user hitting two different DB errors got two completely
different experiences, sometimes with no clear next action.

This policy classifies database failures into 5 cases + assigns a
user-facing message + recovery path to each. Every existing
write-site is audited against the policy in subsequent commits;
new write-sites adopt the pattern at authorship time.

---

## The 5 cases

### Case A — Concurrency lock (sqlite `OperationalError: database is locked`)

**When it happens:** Two writers race for the same row under WAL.
Most commonly when a background job (audit log emit, analytics event
flush) collides with a user-facing write.

**User-facing message (EN/DE):**
- "Saving in progress — give us a couple of seconds and try again."
- "Speichern läuft — bitte einen Moment warten und nochmal versuchen."

**Recovery path:** Automatic retry-with-backoff inside the write
helper, 3 attempts with 50ms / 200ms / 500ms backoff. If all 3 fail,
surface the friendly message to the user with the option to retry.

**HTTP status:** 503 (Service Unavailable) with `code: db_lock_busy`
when the retry helper exhausts attempts.

**Implementation pattern:**
```python
from company_discovery.db_errors import retry_on_lock

@retry_on_lock(attempts=3, backoff_ms=(50, 200, 500))
def write_user_profile(...):
    ...
```

---

### Case B — Disk-full / quota exceeded (sqlite `OperationalError: disk I/O error` or `database or disk is full`)

**When it happens:** Disk volume full, sqlite quota hit, or
filesystem write error.

**User-facing message (EN/DE):**
- "Saving is temporarily unavailable on this deployment. The
  operator has been alerted. Your work is preserved in this session
  — try again in a few minutes, or contact your deployment admin."
- "Speichern ist auf dieser Instanz vorübergehend nicht verfügbar.
  Der Betreiber wurde benachrichtigt. Deine Arbeit ist in dieser
  Sitzung erhalten — versuche es in ein paar Minuten erneut oder
  wende dich an den Administrator."

**Recovery path:** No client-side retry (filesystem state won't
self-resolve). Operator alert via the audit log emitter
(`system_event_kind="db_disk_full"`) for ops visibility. Client
shows the friendly message + preserves the in-flight form data in
sessionStorage so a retry-after-fix-on-admin-side doesn't lose
work.

**HTTP status:** 507 (Insufficient Storage) with `code: db_disk_full`.

---

### Case C — Referential integrity / orphaned foreign key (sqlite `IntegrityError`)

**When it happens:** User tries to operate on a row whose dependency
was deleted by another session or background cleanup. E.g., trying
to add notes to a saved-search whose owning workspace was deleted.

**User-facing message (EN/DE):**
- "That record no longer exists. Refresh the page and try again."
- "Dieser Eintrag existiert nicht mehr. Bitte Seite neu laden und
  erneut versuchen."

**Recovery path:** No retry (the referenced record won't
re-materialise). Client suggests refresh; on refresh the UI re-syncs
state from /api/bootstrap and the stale reference disappears.

**HTTP status:** 409 (Conflict) with `code: db_referential_missing`.

---

### Case D — Schema drift (sqlite `OperationalError: no such column/table` or `OperationalError: type mismatch`)

**When it happens:** Production database state diverges from code
expectations. Should be IMPOSSIBLE in well-managed production but
worth a guard for misconfigured deployments / failed migrations.

**User-facing message (EN/DE):**
- Generic error: "Something went wrong on the server. The operator
  has been alerted."
- "Ein Serverfehler ist aufgetreten. Der Betreiber wurde benachrichtigt."

The user-facing message DOES NOT name the column/table — schema
detail is sensitive (informs attackers of internal structure).

**Recovery path:** Operator alert via the audit log emitter
(`system_event_kind="db_schema_drift"`) with the underlying error
message captured in operator-only audit detail. Client retries via
normal UX patterns; no automated recovery from drift.

**HTTP status:** 500 (Internal Server Error) with `code:
db_internal_error` (intentionally generic to the client).

---

### Case E — Best-effort writes (analytics, audit log, telemetry)

**When it happens:** Writes that are semantically "fire and forget"
and whose failure must never break the user's request flow. The
classic examples are:
- `log_analytics(user_id, event_name, payload)` — fire-and-forget
  analytics events
- `audit_log.emit_*` family — Article 12 audit events
- `_emit_dispatch_audit` — AI invocation audit
- `_warm_cache_for_candidate` — DiagnosticEngine cache warming

**User-facing message:** None. The user sees NO failure.

**Recovery path:** Catch `Exception`, log to stderr / structured
log, continue. The audit-log emitter has its own fallback chain;
analytics are append-only JSONL with retry-on-next-event semantics.

**Pattern documentation:** Every site that catches `Exception` from
a DB write MUST have a comment naming the case ("best-effort path;
failure must not break the caller") so the silent-swallow isn't
mistaken for a bug at review time.

---

## Implementation surface

The policy is implemented in three layers:

### Layer 1 — Helper module `company_discovery/db_errors.py`

A small new module providing:
- `classify_db_error(exc: Exception) -> str` — maps the underlying
  sqlite exception to one of {"db_lock_busy", "db_disk_full",
  "db_referential_missing", "db_schema_drift", "db_internal_error"}
- `retry_on_lock(attempts, backoff_ms)` decorator — Case A retry
- `format_user_message(error_code, locale="en") -> str` — friendly
  message lookup; EN + DE seeded; falls back to a generic message
  for unknown codes
- `emit_admin_alert(error_code, detail)` — Case B + D admin-alert
  emission via the audit-log emitter

### Layer 2 — HTTP handler integration

A `_handle_db_error(error, default_status=500)` helper in `app.py`
that:
1. Calls `classify_db_error` on the exception
2. Maps the code to an HTTP status per the table above
3. Returns the friendly message via `send_error_json`
4. Emits the admin alert for cases B + D

Every `except sqlite3.Error`, `except sqlite3.OperationalError`,
`except sqlite3.IntegrityError` block in `app.py` calls this
helper instead of returning ad-hoc 500s.

### Layer 3 — Repository / write-site adoption

`company_discovery/sqlite_repository.py` + every other module that
writes to sqlite:
- Public write methods use `@retry_on_lock` for the Case A path
- Best-effort write callers (analytics, audit) keep the existing
  `try / except Exception / pass` pattern with a NEW required
  comment naming the case
- Repository methods raise `sqlite3.OperationalError` /
  `IntegrityError` upstream rather than swallowing — the HTTP
  handler is the choke point that maps to user-facing messages

---

## Audit checklist

Apply this checklist to every existing + new sqlite write site:

- [ ] Is the write idempotent under retry? (If yes, eligible for
      Case A retry.)
- [ ] Does the write have explicit foreign keys / row dependencies?
      (If yes, expect Case C IntegrityError; handler must surface
      "record no longer exists".)
- [ ] Is the failure mode best-effort (analytics, audit, telemetry)?
      (If yes, Case E silent-swallow with a justifying comment.)
- [ ] Otherwise: the handler must call `_handle_db_error`.

---

## What this policy does NOT cover

- **Non-sqlite database paths** — the project currently uses only
  sqlite. If a future deployment swaps in PostgreSQL, the
  `classify_db_error` mapping extends to PG's error codes; the
  user-facing message + recovery path stays identical.
- **Network-level errors** (provider HTTP failures, AI provider
  unreachable) — those are handled by the AI provider honesty
  matrix doctrine + ERROR_COPY frontend dictionary.
- **Auth / authz failures** — those have their own surface (401 /
  403 with `code: csrf_failed` etc.) per the existing session-
  expiry recovery wiring (PART 6 Loop 16 Gate 6.5).

---

## Cross-references

- PART 6 Loop 16 (Gate 6.5) error-layer audit — surfaced this as
  Layer 11 with cross-cutting framing.
- `compliance/transparency-notice.md` "What is logged" section —
  audit events emitted at admin-alert paths (Cases B + D).
- `docs/grant/10-ai-act-compliance.md` Article 12 — admin-alert
  events are part of the Article 12 audit trail.
- Existing `_NOT_A_CV_TELLS` + `ERROR_COPY` patterns in the
  frontend — friendly-message conventions this policy aligns with.

---

## Append log

- **2026-05-21**: Policy document published as Phase 2 #78 sub-piece
  1 (the load-bearing deliverable). Implementation across the 3
  layers (db_errors helper + HTTP handler integration + repository
  adoption) follows in subsequent commits; this document is the
  reference contract every commit checks against.
