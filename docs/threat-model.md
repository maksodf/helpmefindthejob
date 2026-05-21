# Helpmefindthejob — Internal Threat Model

Last updated: 2026-05-21. Author: workspace engineering. Status:
internal. This document is not a substitute for an external penetration
test. Track an external review as **P0.K BLOCKED until vendor engaged**
in the gap analysis.

The 2026-05-21 sprint added six new attack surfaces (transparency
dashboard, Verifiable Credentials federation, multilingual scaffolding,
audit-log integrity assertions, supply-chain attestations, versioned
migrations) and an end-to-end demo-walk canary. See §8 for the
sprint addendum and §9 for the cross-invariant tamper guards.

The model targets the production hosted deployment at
`https://app.helpmefindthejob.com`, with admin-managed tester accounts and
provider-neutral AI handoff.

## 1. Assets and trust boundaries

| Asset | Sensitivity | Stored | Boundary crossings |
|---|---|---|---|
| User email, password hash | High | `auth.sqlite3` | Login form; admin reset |
| Session tokens | High | `auth.sqlite3` (HMAC-hashed) | HTTP cookie |
| Per-user companies, jobs, scans | Medium | `company_discovery.sqlite3` | App API |
| Provider configuration (env-var refs only) | Medium | `ai_provider.json` | Settings UI |
| Session-only AI keys | Critical (transient) | Never persisted | Single Run AI request |
| Invitation / reset tokens | High | `tokens.sqlite3` (HMAC-hashed) | Email outbound |
| Admin audit log | Medium | `data/admin_audit.log` | Local only |
| Backup tarballs | High (contains DBs) | `./backups` | Operator-controlled |

Trust boundaries:

- Browser ↔ App (over HTTPS via Caddy)
- App ↔ Public career pages (outbound, robots-checked)
- App ↔ User-chosen AI provider (outbound, only on Run AI)
- App ↔ SMTP relay (outbound, only when invites/resets fire)
- Operator host ↔ Backup destination (operator-controlled)

## 2. STRIDE walkthrough

### Spoofing

| Risk | Mitigation | Residual |
|---|---|---|
| Stolen session reused from another origin | `SameSite=Lax`, `HttpOnly`, `Secure` in production; HMAC-hashed token storage | Low |
| Phishing of invite/reset links | Single-use tokens, 48h / 1h TTL, plain-text emails with the actual product link | Low — relies on user vigilance |
| Brute-force login | Per-IP login rate limit (10 / 10 min); generic `invalid_login` error | Low |

### Tampering

| Risk | Mitigation | Residual |
|---|---|---|
| Cross-site request forgery | `X-CSRF-Token` required on every mutation, bound to the session | Low |
| HTTP header injection via static path | `serve_static` resolves the path against `STATIC_ROOT.resolve()` and rejects any candidate that escapes it | Low |
| Tampering with admin audit log | Append-only file owned by the container; operator reviews via diff | Medium — log integrity depends on host hygiene; off-host shipping is open work |

### Repudiation

| Risk | Mitigation | Residual |
|---|---|---|
| Admin denies creating/disabling a tester | Audit log captures actor email + timestamp + diff (old/new role/active) | Low |
| Tester denies password reset request | Reset token records `created_by=null`; audit log only fires on admin-initiated resets | Medium — voluntary self-resets are not logged today |

### Information disclosure

| Risk | Mitigation | Residual |
|---|---|---|
| Cross-tenant data read | All repository methods scope by `user_id`; cross-user read paths raise `KeyError` | Low |
| Raw AI keys persisted | `validate_provider_config` rejects values matching `sk-`, `key=`, `token=` patterns; session keys never written to disk | Low |
| Forgot-password account enumeration | Endpoint always returns 202; outbox is local-only | Low |
| Backup leaks | Operator-controlled; documented as the responsibility of the operator | Medium until off-host encrypted destination is wired |
| Server-side request forgery via scanner | `HTTPFetcher` rejects localhost / private / link-local hosts; redirects re-validated against `robots.txt` | Low |

### Denial of service

| Risk | Mitigation | Residual |
|---|---|---|
| User exhausts scan budget | Per-user daily scan quota + active-scan cap | Low |
| Single domain hammered across users | Per-domain hourly bucket (default 30 / hour) | Low |
| Login flood | Per-IP login rate limit | Medium — distributed attacks unhandled, document Cloudflare/ALB integration |
| Password-reset flood | Per-IP reset request rate limit (5 / 10 min) | Low |
| AI quota | Per-user daily AI cap | Low |

### Elevation of privilege

| Risk | Mitigation | Residual |
|---|---|---|
| Member promotes self via PATCH `/api/admin/users/<id>` | Endpoint requires `admin` role; backend self-modify guard | Low |
| Admin demotes self leaving zero admins | `auth_store.update_user` checks `count_active_admins()` | Low |
| Invite token guessed | 32-byte url-safe token; HMAC-stored; single-use | Low |
| Stale session after password change/deactivation | `auth_store.update_user` deletes the user's sessions when password or active flag changes | Low |

## 3. Scanner-specific risks

| Risk | Mitigation | Residual |
|---|---|---|
| robots.txt bypass | Robots fetched per host via redirect-validated path; redirects on robots itself rejected | Low |
| Restricted-platform scrape (LinkedIn, etc.) | Domain blocklist enforced at fetch and at job-link extraction | Low |
| Page-size DoS on tag soup | `max_response_chars` cap + redirect cap + page cap | Low |
| Adapter-induced JSON parse blow-up | `_safe_json` returns `None` on parse error; XML adapter catches `ParseError` | Low |
| Misclassification of unsupported ATS | `detect_unsupported_ats` flags Workday / SuccessFactors so the UI can guide manual paste | Medium — copy in the UI is generic; refine after pilot feedback |

## 4. AI provider handoff risks

| Risk | Mitigation | Residual |
|---|---|---|
| Session key leaked via logs | Server never logs request bodies; key is consumed and discarded inside `execute_job_decision_brief` | Low |
| Outbound to attacker-controlled CLI | `command` field is operator-trusted; UI labels it as such; server runs the configured command in a subprocess with stdin only | Medium — CLI mode is intentionally restrictive but still requires operator due diligence |
| Provider rate limits reached | UI surfaces provider error verbatim; AI quota caps user volume | Low |

## 5. Identified gaps (tracked in gap analysis)

- External penetration test not yet commissioned — **BLOCKED** on vendor engagement.
- Centralised log shipping with redaction not configured — open as a P1 ops task.
- Backup destination is local-only by default — operator must configure off-host destination for production.
- No anomaly detection on the audit log; review is manual today.

## 6. Detection signals to wire up

When monitoring is in place (P0.D), surface the following:

- Spike in `invalid_login` rate per IP > 30 / 10 min.
- Sudden drop in `scheduler.activeJobs` (worker stopped).
- Audit log lines with `update_role: member→admin` outside business hours.
- Quota errors > 1 % of attempted scans (suggests an abusive user or a broken target).
- Unhandled `internal_error` rate above baseline.

## 7. Update cadence

Re-run this checklist whenever any of the following change:

- New endpoints or new authentication paths.
- Changes to scanner blocklist, redirect handling, or robots logic.
- Changes to credential handling (storage shape, transport path, env names).
- New external integrations (ATS adapters, monitoring backends).

## 8. Sprint addendum — 2026-05-21

The 4-week NLnet sprint added these surfaces. Each gets a STRIDE
row capturing the threats and the defenses landed.

### 8.1 Public transparency dashboard (`/transparency`, `/transparency.json`)

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| Stored XSS | Attacker plants `<script>` in an audit-log `event_payload.purpose`; rendered into the public dashboard | `_esc()` HTML-escapes every interpolated value; CSP `script-src 'none'` is defense-in-depth | Shipped (W2 D8-9 panic round 1) |
| CSS class injection | Attacker-controlled `confidence` value flows into a `class="confidence-{value}"` attribute | Allowlist confidence to `{proven, plausible, aspirational}`; unknown values fall back to `aspirational` | Shipped (W2 D8-9 panic round 1) |
| Unauthenticated DoS | Public endpoint scanned 20k audit-log records per request | 60-second TTL cache keyed on `(window_days, log_path, mtime, ttl_bucket)` | Shipped (W2 D8-9 panic round 2) |
| Re-identification via small counts | A unique persona attribute appears in `byPurpose`, attacker correlates | Laplace ε-differential privacy noise (ε=1.0) + k-anonymity suppression below k=5 | Shipped |
| Cost-saving snapshot leaks user-base size | Raw event counts proportional to user count | Same DP + suppression applied to `render_public_cost_saving_snapshot` (privacy parity commit) | Shipped |
| Cache-poisoning via `window=` param | Adversarial values (huge ints, non-numeric, SQL keywords) | Clamped to [1, 90]; `try/except (TypeError, ValueError)` falls back to 30 | Shipped |
| Malformed `event_payload` | Buggy emitter or federation peer plants a string/list instead of dict | Defensive `isinstance(payload_raw, dict)` coercion; non-dict → empty dict | Shipped (W2 D8-9 panic round 2) |

### 8.2 Verifiable Credentials federation (mesh agents)

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| Issuer impersonation via the signer API | Agent A calls `sign_credential(vc)` where `vc["issuer"]` is agent B's DID | Signer raises `ValueError("issuer_mismatch")` before producing the proof | Shipped (W2 D10 panic round) |
| Wire-rewrite forgery | Attacker signs a VC as agent B, then rewrites the `issuer` field to claim agent A | Registry-based verifier — agent A's public key won't validate agent B's signature → `signature_mismatch` | Shipped |
| Signing key exfiltration | Keypair file readable to other users on the host | `0o600` permissions on the JSON keypair file; `data/` is gitignored | Shipped |
| Replay of an old VC | Attacker re-presents a previously valid VC | Out of scope for the VC layer (consumers MUST check `validFrom` + maintain a nullifier set if replay matters) | Documented in module docstring |
| Tampering with the credential subject | Any byte flip in subject fields | Ed25519 signature over JCS canonical JSON; verify recomputes + compares | Shipped |

### 8.3 Multilingual scaffolding

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| Locale-driven XSS (translated strings used as raw HTML) | Translator (or compromised Weblate account) submits `<script>` as a value | Frontend uses `textContent` / `_interpolate` (not `innerHTML`) for translated strings; pluralisation wrapper escapes too | Existing pattern from i18n parity tests |
| Directionality confusion | RTL locale activated but UI elements stuck LTR (or vice versa) | `_applyLocaleDirection` sets `html[dir]` from registry; CSS RTL override block flips text-align + flex + sidebar position | Shipped (W3 D15) |
| Plural-form attack | Translator submits a `{{count}}` template injecting arbitrary HTML | Interpolation is via `String.prototype.replace` against `{{name}}` regex; output is set via `textContent`, never `innerHTML` | Shipped |

### 8.4 Audit-log integrity (existing + sprint additions)

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| Transparency dashboard claims a sequence_no that doesn't exist | Public surface advertises `chainHead.sequenceNo`; an auditor would request the log and find it missing | `chainHead.sequenceNo` is computed by iterating the actual records, never inferred | Shipped |
| HMAC chain forgery | Attacker rewrites multiple records to produce a self-consistent chain | Requires the audit salt, which lives only in `HELPMEFINDTHEJOB_AUDIT_SALT` env var (never persisted) | Shipped (existing) |
| Chain-head fingerprint disclosure leaks salt | The 12-char HMAC prefix is exposed on `/transparency` | 12 hex chars (48 bits) is too short for offline brute force of a 256-bit HMAC; the chain remains computationally infeasible to forge | Acceptable |

### 8.5 Supply-chain attestations

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| SBOM-drift (deploy ships deps the SBOM doesn't list) | Contributor adds a dep without regenerating the SBOM | `tests/test_release_supply_chain.py` fails CI if any direct dep in `requirements.txt` is missing from the SBOM | Shipped (W3 D13-14) |
| Stale security.txt Expires | Researchers can't trust the contact is monitored | `test_security_txt_not_expired` asserts the Expires field is in the future (per RFC 9116 §2.5.5) | Shipped |
| Signed release tarball tampered | Attacker swaps the published v0.1.0 source tarball | Sigstore signature at `docs/releases/v0.1.0-source.tar.gz.sigstore` verifies against cosign pub key | Shipped |

### 8.6 Versioned SQLite migrations

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| Half-applied migration | Migration script fails mid-way leaving DB in inconsistent state | Per-migration transaction: schema change + `PRAGMA user_version` bump committed atomically. ROLLBACK on any failure | Shipped (gap #20) |
| Migration replay | Operator re-runs the app; migrations re-applied | Forward-only: runner reads `current_version`, skips any migration with `version <= current` | Shipped |
| Version-number gap (lost file in rebase) | A 002 file is present, 001 is missing | Runner raises `ValueError("migration version gap")` on discovery; fails loudly at boot | Shipped |
| Misnamed migration file | Contributor uploads `migration_for_x.sql` (no version number) | Runner logs warning + skips. Contract test pins that the live `migrations/` dir is discoverable | Shipped |

## 9. Cross-invariant tamper guards

The end-to-end grant-demo walk (`tests/test_grant_demo_walk_e2e.py`)
includes two cross-invariant tamper guards because some integrity
claims depend on multiple invariants composing:

1. **Trust Receipt ↔ audit-log linkage**: a Trust Receipt MUST
   carry the audit-log `sequence_no` + `chain_hmac_prefix` it was
   emitted alongside. Without this linkage, the "audit-linked AI
   decision" claim is unverifiable — an attacker who only sees the
   receipt can't cross-check it against the audit log.

2. **VC signer ↔ DID enforcement**: an `Ed25519Signer` MUST refuse
   to sign a VC whose `issuer` field doesn't match its own
   `signer_did`. Without this, agent A could silently sign VCs as
   agent B and the wire-rewrite attack would never happen because
   the signer itself emits the forged credential. The signer-side
   enforcement + verifier-side signature check are two independent
   defenses (defense in depth — §4).

A failure of either guard means the project's integrity story
ships with a hole. Fix at root.

---

## 10. Active defects

When a security defect surfaces, log it here with a remediation
deadline. An empty section means no known active defects on the
date the doc was last updated.

_None as of 2026-05-21._
