# Security review checklist

Run through this list before any production rollout, after any auth /
admin / scanner change, and on a quarterly cadence. Pair it with
`docs/threat-model.md`.

## Auth and admin

- [ ] Password hashes use PBKDF2-SHA256 with at least 200k iterations and a per-user salt.
- [ ] Session tokens are stored as HMAC of `secret_key` + raw token; raw tokens never touch disk.
- [ ] Session cookies use `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- [ ] Login endpoint rate-limited per IP.
- [ ] Forgot-password endpoint rate-limited per IP.
- [ ] CSRF token required on every mutating call (`tests/test_http_auth.py::test_csrf_required_for_mutating_calls`).
- [ ] Admin self-modify of role/active status rejected.
- [ ] Last active admin cannot be demoted or deactivated.
- [ ] Admin actions logged to `data/admin_audit.log` with actor, target, action, timestamp.
- [ ] Email invite tokens are 32-byte url-safe, single-use, expire ≤ 48 h.
- [ ] Password reset tokens are 32-byte url-safe, single-use, expire ≤ 1 h.
- [ ] Token consume is atomic (UPDATE with conditional WHERE).
- [ ] No password / API key / token appears in error messages or logs.
- [ ] Forgot-password 202 response identical for known and unknown emails.

## Scanner

- [ ] Restricted-platform domains blocked at fetch *and* at job-link extraction.
- [ ] `HTTPFetcher` rejects `localhost`, `127.0.0.0/8`, `::1`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `*.internal`, link-local hostnames.
- [ ] robots.txt fetched per host and per redirect target before any page fetch.
- [ ] robots.txt redirects rejected (security against open redirect).
- [ ] Per-fetch redirect cap, response-size cap, page-count cap, request delay all enforced.
- [ ] Response not loaded into memory beyond `max_response_chars`.
- [ ] No JS execution: only static HTML + JSON + XML adapters.

## Quotas

- [ ] Per-user daily scan cap enforced.
- [ ] Per-user daily AI cap enforced.
- [ ] Per-user concurrency cap enforced.
- [ ] Per-domain hourly bucket enforced across users.
- [ ] Quota errors return 429 with a code (`scan_quota_exhausted`, `ai_quota_exhausted`, `scan_concurrency_limit`, `domain_rate_limited`).

## AI provider handoff

- [ ] Raw secrets rejected in `credential_reference` (`raw_secret_not_allowed`).
- [ ] Session-only API keys consumed once and never written.
- [ ] CLI provider commands run as subprocesses with stdin only, no shell expansion.
- [ ] Server logs do not include request bodies.

## Data isolation

- [ ] Every repository read filters by `user_id`.
- [ ] Cross-user direct dict reads raise `KeyError`.
- [ ] Cascade delete of a company removes scans, runs, discovered jobs, imported jobs for that user.
- [ ] Backup export covers only the requesting user's data.

## Static + transport

- [ ] `serve_static` rejects any path that resolves outside `STATIC_ROOT`.
- [ ] Security headers present on every response: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`.
- [ ] HTTPS termination and HSTS configured at the reverse proxy.
- [ ] CSP forbids inline scripts and external network sources.
- [ ] No `innerHTML` of user-controlled data in `static/app.js`.

## Operations

- [ ] `.env` is not committed.
- [ ] `data/*.sqlite3*` are not committed (`.dockerignore` covers them).
- [ ] Backups are encrypted at rest if the operator chose off-host storage.
- [ ] Backup retention configured (default 30 days).
- [ ] TLS cert renewal monitored (`scripts/tls-expiry-check.sh`).
- [ ] Uptime probe runs every 5 minutes (`scripts/uptime-check.sh`).
- [ ] Admin audit log rotated by the host (`logrotate` or equivalent).
- [ ] Restore drill rehearsed monthly (`scripts/restore-drill.sh`).

## External

- [ ] Engage external pen-test vendor (BLOCKED until vendor selected).
- [ ] Counsel review of `static/privacy.html`, `static/terms.html`, `static/data-retention.html` before commercial sale.

## Test coverage tied to this checklist

- `tests/test_company_discovery.py::CompanyDiscoveryTests` — scanner safety + dedup.
- `tests/test_http_auth.py` — CSRF, last-admin, deactivated login, password change session invalidation, audit log.
- `tests/test_http_invitations.py` — invite + reset round-trips, admin metrics, member-only quotas.
- `tests/test_modules.py` — quotas, scheduler, dedup, ATS adapters, tokens, email transport.
- `tests/e2e/test_browser_flow.py` — UI flows including admin lockout for members.
