# Helpmefindthejob — Internal Threat Model

Last updated: 2026-05-08. Author: workspace engineering. Status:
internal. This document is not a substitute for an external penetration
test. Track an external review as **P0.K BLOCKED until vendor engaged**
in the gap analysis.

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
