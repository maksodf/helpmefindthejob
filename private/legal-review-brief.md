# DirectJob Scout — Legal review brief

For counsel review of three public-facing legal pages before any paid
pilot or real personal-data ingestion. Forward this whole document to
your lawyer along with the three URLs at the top of §1.

Last updated: 2026-05-09. App version: 0.4.0. Operator: Fouad Maksoud
(`fouad@khalo.org` / `maksodf@gmail.com`). Live at
`https://app.khalo.org`.

---

## 1. The three pages to review

- `https://app.khalo.org/privacy`
- `https://app.khalo.org/terms`
- `https://app.khalo.org/data-retention`

Each carries the version metadata "Version 1.0 · Last updated
2026-05-09 · App version 0.4.0" and an explicit "must be reviewed by
counsel before commercial sale" notice.

## 2. What DirectJob Scout does (in plain words)

A self-hosted job-search assistant for healthcare-management
candidates. The user maintains a watchlist of companies, the app
fetches each company's public career page (with `robots.txt` checks
and strict per-domain rate limits), extracts job postings, lets the
user import them into a personal pipeline, and prepares a
provider-neutral AI brief which the user can analyse with their own
AI subscription (OpenAI / Gemini / DeepSeek / Anthropic / Ollama / a
local CLI / manual).

Today the product is in a controlled pilot with a single operator
(me) and a small number of friend-testers. No real patient data is
expected; testers use it for their own job search.

## 3. Data the app stores

| Category | Examples | Storage |
|---|---|---|
| Account | Email, PBKDF2-SHA256 password hash, role (admin/member), active flag, last_login_at, last_active_at | `auth.sqlite3` (Docker volume on a DigitalOcean droplet in Frankfurt) |
| Sessions | HMAC-hashed session tokens, CSRF tokens, expiry | same DB |
| User watchlist | Company name, website URL, career page URL, sector, free-text notes | `company_discovery.sqlite3` |
| Discovered jobs | Title, location, source URL, scraped description, JSON-LD payload, confidence score, scan history | same DB |
| Imported jobs | Same fields plus optional AI-analysis text + structured fit score, application status, application notes, cover-letter draft | same DB |
| AI provider config | Provider name, model name, **environment-variable name** of the API key, never the key value itself | `ai_provider.json` |
| Saved searches, support tickets, opt-in analytics events | role-target keywords, free text, audit metadata | same DB |
| Admin audit log | Actor + target + action + timestamp for every admin user-management action | `admin_audit.log` (JSON Lines) |
| Email outbox | Local-only fallback when SMTP is not configured | `email_outbox.log`; not in use today (SMTP active) |
| Backups | All of the above as gzipped tarballs | Local disk + Backblaze B2 (off-host, EU region) |
| Telemetry | Application logs streamed to Better Stack (EU region) | Better Stack collector → `telemetry.betterstack.com` |

What the app **does not** store:

- Raw AI provider API keys (only the env-var name is persisted; users
  may paste a session-only key in the UI, which is sent only with one
  Run AI request and never written to disk).
- Health records, diagnoses, or any patient data. The product is for
  the *user's own job search*, not for clinical use.
- Tracking pixels, third-party analytics, marketing cookies. The
  privacy page explicitly says so.

## 4. External data flows

- **Email**: Resend (HQ San Francisco, EU region for sending domain
  `khalo.org`). Used for invitations and password resets only.
- **Object storage / backups**: Backblaze B2 (HQ California, EU
  endpoints). Used only for backup tarballs.
- **Logs**: Better Stack (HQ Czech Republic, EU region). Used for
  application log shipping.
- **AI provider** (only on user's explicit click): provider chosen by
  the user (OpenAI / Gemini / DeepSeek / Anthropic / Ollama / local
  CLI). The user's prompt and any pasted session key go to that
  provider. Their respective Terms apply.
- **Public company career pages**: scanned according to `robots.txt`,
  with per-domain rate limits, with hard blocks on LinkedIn / XING /
  StepStone / Indeed and on private/internal/local hosts.

## 5. Safety controls already implemented

- robots.txt is read for every host before any fetch, and re-read on
  every redirect.
- Per-fetch limits: max pages per scan, max redirect chain, max
  response size, request delay.
- Domain blocklist for LinkedIn, XING, StepStone, Indeed.
- Private/internal/link-local hosts are rejected at the fetcher.
- Login is rate-limited (10 failures / 10 minutes per IP). Forgot-
  password is rate-limited (5 / 10 minutes per IP). Tokens are
  HMAC-hashed in the DB, single-use, time-limited.
- CSRF token required on every mutating call. Sessions are HttpOnly,
  SameSite=Lax, Secure.
- Last admin cannot be deactivated, demoted, or deleted.
- Account deletion: user-requested → admin-confirmed → cascades across
  all per-user records, sessions, scheduler entries, quota counters,
  AI provider preferences. Audit log retains the action with email
  but not contents.

## 6. Specific questions for counsel

Please review the three pages with these questions in mind:

1. **GDPR / DSGVO compliance** of the privacy page for German users.
   Are the lawful bases (Art. 6 (1) (b) contract performance for the
   account, Art. 6 (1) (a) consent for the optional analytics toggle)
   correctly stated?
2. **Auftragsverarbeitung** (data processor agreements) required with
   Resend, Backblaze, Better Stack, and any AI provider the operator
   chooses. Which DPAs need to be in place and where do we surface
   them on the privacy page?
3. **Healthcare-management persona caveat**. The product targets
   healthcare-management *candidates* (their own job search). Do we
   need additional language ruling out clinical / patient-data use?
4. **Data-retention** windows on the data-retention page. Are the
   defaults (sessions 14 days; tokens 1–48 hours; export-on-deletion;
   30-day backup retention) defensible? What needs adjustment?
5. **Account export + deletion** workflow. Is the user-initiated
   request → admin-executed delete cascade sufficient under Art. 17?
   Do we need an automated SLA?
6. **Imprint (Impressum)**. Required for the German market;
   currently not added. Where should it live and what fields must it
   contain?
7. **Cookie banner**. Currently zero analytics cookies are set
   without explicit user opt-in (the analytics toggle is opt-in by
   default). Is a banner still required or can we omit?
8. **AI handoff disclosure**. The Terms note that AI analysis is
   informational and not advice. Is the wording strong enough for
   healthcare-adjacent use?
9. **Restricted-platform clause**. The Terms forbid users from
   bypassing scan limits / robots blocks / restricted-platform
   blocks. Is this enforceable? Sufficient?
10. **Anything missing.** Imprint, AGB, Widerrufsrecht (only if we
    sell to consumers), liability cap clauses, governing law clause,
    SCCs for non-EU sub-processors.

## 7. Deliverable I'd love back

A redlined version of the three pages (or specific paragraphs to
add/replace), plus a one-line decision on each numbered question
above. Quote, hourly rate, and turnaround estimate also welcome.

---

## How to find the right lawyer

For a German healthcare-adjacent SaaS pilot:

- **Legalbird** / **Klugo** / **Smartlaw** — online consult flat-fee,
  fastest, ~€200–€400 for a one-pass review. Good for first
  iteration.
- **A boutique IT/Datenschutz Kanzlei** — slower, ~€400–€800, but
  produces a redline you can hand to the next reviewer.
- **Local Anwaltsverein** — referral service for vetted lawyers in
  your city. Slowest but cheapest for repeat work.

Search terms that work well: `Datenschutz Anwalt SaaS`,
`IT-Recht Kanzlei DSGVO`, `Auftragsverarbeitung Beratung Berlin`
(or your city). Many such firms offer a free 15-minute call to
scope the work.

## After counsel signs off

1. Apply their redlines to `static/privacy.html`,
   `static/terms.html`, and `static/data-retention.html`.
2. Bump the "Version" header on the affected pages and the
   "Last updated" date.
3. Set `DIRECTJOB_LEGAL_REVIEWED=true` in `/opt/directjob-scout/.env`.
4. Restart the app: `docker compose -f docker-compose.prod.yml --env-file .env up -d`.
5. Run the readiness check; **Legal review** row flips to `[ok]`.
6. Update `docs/sellable-readiness-final-report.md` to record who
   reviewed, on what date, and any remaining caveats.
