# Customer-support inbox triage

Solo-operator-friendly. Use this until you hit ≥50 paying users — then graduate to a help-desk tool.

## Inbox

`support@directjob-scout.example` is the canonical mailbox. In-app `/api/support` tickets land in `data/admin_audit.log` with `kind=support_ticket`, plus an email to `support@directjob-scout.example`.

Account-deletion request emails land at the same address; treat as P1 (legal SLA pressure).

## SLA targets

| Priority | Definition | Response time |
|---|---|---|
| P1 | Site down, login broken, billing wrong, data export blocked, GDPR deletion request | Acknowledge within 4h, resolve within 24h |
| P2 | Feature broken with workaround, AI-mode misbehaving, non-blocking bug | Acknowledge within 24h, resolve within 72h |
| P3 | Feature request, "how do I…" question | Acknowledge within 72h, no resolve commitment |

The 24h response-time SLA we surface publicly maps to **P1 + P2 acknowledgement**. Don't overpromise resolution on a P3.

## Triage rules

Apply in order:

1. **Is this a person?** Bots, marketing pitches, "I sell SEO services" → archive. No reply.
2. **Is the user paid?** Check Stripe Customer Portal. Paid customers always get a personal reply within 4h.
3. **Is it a bug?** If reproducible, file as a Linear/GitHub issue with `bug` label, link the ticket. Reply with "Confirmed bug, ticket #X" + ETA.
4. **Is it a feature request?** Acknowledge, add to a public-facing roadmap doc (or `docs/roadmap.md`). Don't promise.
5. **Is it a question?** Reply with answer + link to `/help`. If the answer isn't on `/help`, also update `/help` so the next user finds it themselves.
6. **Is it a GDPR request?** Forward to operator-only inbox if you have one; otherwise process directly (export → delete via the existing 7-day grace flow).

## Common categories

| Trigger | Likely category | First response |
|---|---|---|
| "I can't log in" | Auth / 2FA / rate-limit | Check `data/admin_audit.log` for failed-login spam from their IP; reply with one of: "rate-limited, wait 10 min", "2FA reset link", or "deactivated, please use registration" |
| "AI doesn't work" | Provider config | Verify their `aiProvider` settings via admin panel; most often: API key was pasted with surrounding quotes |
| "Where's my CV?" | Profile sync | CV is stored encrypted; check `user_profiles` row; if blob fails to decrypt (rotated key), ask them to re-paste |
| "Stripe charged me twice" | Billing | Check Stripe dashboard for the customer; refund duplicate via Stripe Customer Portal; reconcile in admin panel |
| "Bookmarklet broken" | Frontend / page-level | Ask which platform (LinkedIn / Indeed / StepStone / XING); ship a fix in `static/bookmarklet.js`; users get the new one on next deploy without re-installing |
| "I want my data deleted" | GDPR | Direct them to Settings → Privacy → Request deletion; confirm via the email link; account hard-deletes 7 days after confirmation |

## Reply templates

Keep these short, signed by the operator (not "the team" — solo operator means the human writes back). German users prefer formal Sie unless they used du first.

### Auth / rate-limit (EN)

> Hi <name>,
>
> Looks like the login limiter caught your IP after a few wrong-password tries. It clears after 10 minutes — would you try again then? If you still can't get in, reply here and I'll reset manually.
>
> — [Operator]

### Bug acknowledgement (EN)

> Hi <name>,
>
> Confirmed — I can reproduce <X>. Filed as ticket #<ID>; expected fix within <window>. I'll email you when it's deployed.
>
> Sorry for the friction.
> — [Operator]

### Feature request (EN)

> Hi <name>,
>
> Thanks for the suggestion. I've added it to the roadmap doc; can't promise a date, but I read every request and the most-asked ones get prioritised.
>
> — [Operator]

### Account-deletion confirmation (EN)

> Hi <name>,
>
> Confirmation received. Your account is scheduled for deletion on <date> (7 days from now). You can cancel any time during that window from Settings → Privacy. After the date, all your data — companies, jobs, AI provider settings, application history — is removed; off-host backup tarballs roll out per the configured retention.
>
> — [Operator]

## Escalation paths

- **Stripe issue you can't resolve:** Stripe support has decent SLAs for paid accounts; their chat is the fastest path.
- **Better Stack collector down:** SSH to droplet → `docker logs better-stack-collector` → restart container; if persistent, file with Better Stack support.
- **Caddy TLS expiry:** Caddy auto-renews; if expiry alarm fires, check `docker logs caddy` for ACME bounce; usually CAA record drift.
- **Postgres / SQLite corruption:** Restore from off-host backup (see `docs/incident-playbook.md` "Restore from backup").

## Escalation log

When a P1 fires, write a 3-line note in `docs/incidents/YYYY-MM-DD-<slug>.md`. The first 24h after a customer-impacting incident is when you decide whether the system needs structural changes.

## When to graduate this doc

Replace this with a real help-desk tool (Plain.com, Front, Help Scout, or OSS Chatwoot) when any of:

- Ticket volume > 5/day for two weeks running
- A second person joins customer support
- A regulator pings you (DSGVO request that needs documented chain-of-custody)
- A paid plan promises an SLA tighter than 24h

Until then, this 1-page runbook + a clean `support@directjob-scout.example` inbox is enough.
