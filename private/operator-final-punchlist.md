# Operator final punchlist

After round 7 (`0.12.0`) every code-side roadmap item is shipped. The
seven remaining items below are operator-side work — they need a
human action you can't delegate to the deploy script. This page is the
runbook for each one.

---

## Item 3 — Brave Search activation

**Code state:** ready. `BraveSearchProvider` is wired into the
`DiscoveryEngine` and activates the moment `DIRECTJOB_BRAVE_API_KEY`
appears in the prod env. Free tier: 2,000 queries/month.

**Steps:**

1. Sign up at <https://api.search.brave.com>. Pick the free *Data for
   AI* plan (no credit card needed at the free tier).
2. Generate a Web Search API token. Copy the value (starts with
   `BSA…`).
3. SSH to the droplet:
   ```
   ssh -i ~/.ssh/directjob_scout root@161.35.76.8
   ```
4. Open `/opt/directjob-scout/.env` and add the line:
   ```
   DIRECTJOB_BRAVE_API_KEY=BSA<your-key-here>
   ```
5. Restart the app container only — Caddy stays up:
   ```
   cd /opt/directjob-scout && docker compose -f docker-compose.prod.yml up -d directjob-scout
   ```
6. Verify by calling discover-companies as `admin@khalo.org` with a
   non-curated persona (e.g. tech). You should see results with
   `source: "brave_search"` mixed in.

**Failure modes:** quota exhaustion (HTTP 429) — the provider returns
empty list and the curated path keeps working. Re-enable on the 1st
of next month.

---

## Item 5 — Better Stack collector secret rotation

**State:** still waiting on Better Stack support. Memory note
`better-stack-collector-rotation-pending.md` has the full context.
The exposed value is `qNWdQBAU9KmjKJUYbFkr6kdUY5FxqmDK` — only allows
log writes to source `directjob-scout-prod`, no read or app access,
but operator hygiene says rotate.

**Steps when Better Stack replies:**

1. Copy the new install command they send out of the Better Stack
   chat.
2. Run it on the droplet (auto-replaces the two collector
   containers):
   ```
   ssh -i ~/.ssh/directjob_scout root@161.35.76.8 \
     'curl -sSL https://raw.githubusercontent.com/BetterStackHQ/collector/main/install.sh | COLLECTOR_SECRET="<NEW>" bash'
   ```
3. Confirm logs flow at <https://telemetry.betterstack.com> →
   Sources → `directjob-scout-prod` → Live tail.
4. Delete the memory note (`memory/better-stack-collector-rotation-pending.md`)
   and the line in `MEMORY.md` so it stops flagging.

**Severity:** hygiene, not a deploy blocker. Readiness signal
`Monitoring + log shipping` is already `[ok]`.

---

## Item 6 — Legal review

**State:** brief prepared at `docs/legal-review-brief.md`. Counsel
review *engaged* but not signed off. `DIRECTJOB_LEGAL_REVIEWED=false`
in prod env.

**Steps:**

1. Email `docs/legal-review-brief.md` to a German Datenschutz lawyer.
   Suggested firms (operator's choice):
   - Legalbird (consumer-grade, fast)
   - Klugo (tech-friendly, mid-range)
   - IT-Recht Kanzlei (specialised, more thorough)
2. Apply any redlines they return (likely: privacy policy wording,
   data-retention specifics, Auftragsverarbeitungsverträge with
   Resend / Backblaze B2 / Better Stack).
3. Once signed off, set `DIRECTJOB_LEGAL_REVIEWED=true` in the prod
   `.env` and restart the container.
4. Update `docs/sellable-readiness-final-report.md` to reflect the
   new state.

**Trigger gates that *force* this:** first paid customer, real
personal health data ingested, >25 active testers.

---

## Item 7 — Backup-production cron review

**State:** ad-hoc deploy snapshots are now WAL-aware
(`scripts/pre-deploy-snapshot.sh` uses `sqlite3 .backup`). The
periodic off-host backup script `scripts/backup-production.sh` was
already written WAL-aware (it dumps via `sqlite3 .backup` inside the
container before tarballing).

**Steps:**

1. SSH to the droplet and confirm the cron is still scheduled:
   ```
   crontab -l | grep -i backup
   ```
2. If a cron exists, check the latest tarball is < 24 h old in
   `/var/backups/directjob/` (or wherever `BACKUP_DIR` points).
3. If no cron exists, install one:
   ```
   echo '0 3 * * * cd /opt/directjob-scout && DIRECTJOB_BACKUP_BACKEND=rclone DIRECTJOB_BACKUP_REMOTE=b2:khalo-directjob-backups ./scripts/backup-production.sh >> /var/log/directjob-backup.log 2>&1' | crontab -
   ```
4. Run a one-shot dry-run + a real run, verify the tarball appears in
   B2 (`rclone ls b2:khalo-directjob-backups | tail -3`).

**Severity:** medium. Without this, a droplet failure would lose all
data since the most recent manual backup.

---

## Item 8 — External penetration test

**State:** formally deferred for the unpaid pilot, backed by
`docs/threat-model.md`, `docs/security-review-checklist.md`, and the
~225-test suite. `docs/sellable-readiness-final-report.md` records
the deferral and the re-open triggers.

**Re-open triggers (any one fires → schedule a pen-test before
expanding scope):**

- First paying customer signs up.
- Real personal health data is ingested by any user.
- Active user count exceeds 25.
- Operator picks a hard date for go-live.

**Steps when triggered:**

1. Pick a vendor — typical EU options: Cure53, SEC Consult, Code
   Intelligence. Budget: €5–15k for a 3–5 day app pen-test.
2. Brief them with: `docs/threat-model.md`,
   `docs/security-review-checklist.md`, prod URL, a test admin
   credential, and the data-shape doc from `docs/legal-review-brief.md`.
3. Apply findings. Re-test the high/critical fixes before sign-off.
4. Update `docs/sellable-readiness-final-report.md` with the
   pen-test report date + findings summary.

---

## Item 9 — Stripe billing activation

**Code state:** ready. `StripeBillingBackend` is implemented +
tested. Activation is just env config.

**Steps:**

1. Create a Stripe account at <https://stripe.com>. Switch to the
   live key (test keys are fine for dry-runs first).
2. In Stripe → Products, create the two paid plans matching
   `plans_payload()` in `company_discovery/billing.py`:
   - `Team` (€79/month, 15 seats)
   - `Organization` (€249/month, 60 seats)
3. Copy the price IDs (start with `price_…`).
4. Add to `/opt/directjob-scout/.env`:
   ```
   DIRECTJOB_BILLING_BACKEND=stripe
   DIRECTJOB_STRIPE_API_KEY=sk_live_...
   DIRECTJOB_STRIPE_PRICE_TEAM=price_...
   DIRECTJOB_STRIPE_PRICE_ORG=price_...
   DIRECTJOB_STRIPE_SUCCESS_URL=https://app.khalo.org/?checkout=success
   DIRECTJOB_STRIPE_CANCEL_URL=https://app.khalo.org/?checkout=cancel
   ```
5. Restart the container. Smoke-test from Settings → Subscription:
   "Upgrade to Team" should redirect to Stripe Checkout.
6. Configure a Stripe webhook (events: `checkout.session.completed`,
   `customer.subscription.updated`, `customer.subscription.deleted`)
   pointing at `https://app.khalo.org/api/billing/webhook` once that
   endpoint ships (currently NOT shipped — webhooks are queued).

**Caveat:** the webhook handler is not yet implemented. Today,
subscription state must be reconciled manually via the admin panel
after a successful checkout. Webhook support is a follow-up.

---

## Item 10 — Friend-tester (Naser) acceptance report intake

**State:** invite was sent to `naserhussein64@gmail.com`. Volume swap
on 2026-05-09 left Naser as a `member` row in the production
workspace. He hasn't yet returned a written test report.

**Steps:**

1. Confirm Naser can still log in. If his earlier session got
   confused, send a fresh invitation:
   ```
   curl -X POST https://app.khalo.org/api/admin/invitations \
     -H "Content-Type: application/json" \
     -H "X-CSRF-Token: <admin-csrf>" \
     -b /tmp/khalo-cookies \
     -d '{"email":"naserhussein64@gmail.com","role":"member"}'
   ```
2. Send him the §E acceptance checklist from
   `docs/sellable-readiness-final-report.md` so he has a structured
   list of things to verify.
3. Collect his report. File any concrete bugs as separate issues.
4. When at least one full pass through the checklist comes back
   clean, mark the friend-tester pilot complete in the readiness
   doc.

**No code work blocks this** — it's purely a coordination item.
