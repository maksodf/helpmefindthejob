<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Audit-log key rotation playbook

**Article**: AI Act Article 12 (automatically generated logs of high-risk AI systems) and Article 26(6) (deployer log-retention obligation). Also relevant: GDPR Article 32 (security of processing) and Article 5(1)(f) (integrity and confidentiality principle).
**Audience**: deployer's named oversight person + the operations engineer who has root access to the production droplet.
**Frequency**: scheduled rotation every 12 months (calendar-driven), or unscheduled rotation triggered by any of the incident classes in §3.
**Status**: living document. Updated alongside every major audit-log schema change.

---

## 1. What this document is

The audit log uses a per-deployment HMAC key (`HELPMEFINDTHEJOB_AUDIT_SALT`, 32 random bytes, base64-encoded) to (a) anonymise the `user_id` field into an opaque per-deployment identifier and (b) chain successive log entries together so tampering is detectable. The key is a **secret** in the strict sense: anyone with the key can re-link historical entries to the user IDs they came from, or forge new entries that pass chain validation. **Therefore the key must be rotatable.**

This playbook is the operational procedure the deployer follows to rotate the key — both as a scheduled cadence and as an incident response. It satisfies the Article 12 implicit requirement that a high-risk AI system's log infrastructure must be operable for the full lifetime of the deployment (which is longer than any one key's safe service life).

---

## 2. What rotation does and does not change

| Aspect | Pre-rotation | Post-rotation | Notes |
|---|---|---|---|
| New audit-log entries | HMAC-chained with old key | HMAC-chained with new key | The new key takes effect immediately on next entry write. |
| Old audit-log entries | Chain valid under old key | Chain still valid under old key | Old entries are immutable; you keep the old key in a sealed archive for as long as you retain those entries. |
| `user_opaque_id` linkage | Stable per user across the old key's life | Resets to a new opaque value per user | Per-user analytics across the rotation boundary require either bridging via the user-real-id (off-limits per pseudonymisation discipline) or accepting a discontinuity. |
| GDPR Article 20 export | Includes only entries hashable with one of the keys you still hold | Same | The export logic accepts a list of historical keys, in newest-first order, and tries each against entries that fail validation with the newest. See `company_discovery/verify_receipt_cli.py` for the multi-key verification flow. |
| Chain-tamper detection | Detected if any entry's HMAC does not match the chained predecessor under the in-force key at write time | Same | Tamper detection works per-key-era. A rotation is a discontinuity, not an obfuscation; rotation does not mask earlier tampering, nor does earlier tampering mask later integrity. |

---

## 3. When to rotate

**Scheduled** — every 12 months. Calendar event in the deployer's operations calendar. Coincide with the bias-testing re-run (`deployer-operating-manual.md` §9.2) if possible — one operational window, two compliance obligations closed.

**Unscheduled — incident-driven**:

1. The 32-byte secret may have been disclosed (any breach scenario where the prod `.env`, the prod environment-variable dump, or a memory snapshot of the running process was exfiltrated or shared with an unauthorized party).
2. A team member who had access to the secret leaves the organisation.
3. The hosting provider has had a publicly-disclosed credential-leak incident that may have affected your tenant's secrets.
4. A successful penetration of the production droplet was confirmed (root-level access by an unauthorized actor).
5. A key-management tooling change (e.g., migrating from `.env` on disk to a secrets manager) — rotation is the cleanest cutover.
6. As part of the migration-of-deployer handover (the outgoing deployer rotates the key one final time, the incoming deployer rotates again on day 1 so the outgoing party cannot validate against the live chain).

**Do NOT rotate** to "freshen" the audit log without a documented driver. Rotation has operational cost (analytics-discontinuity, multi-key verification load) and frequent unjustified rotation degrades the integrity story.

---

## 4. Pre-rotation checklist

Before initiating rotation:

- [ ] Confirm the previous rotation date and the storage location of every prior key. Each key is referenced by a short identifier (key generation: `kid_2026Q1`, etc.); the in-force key plus all keys still needed to verify retained entries are in the **active set**.
- [ ] Verify the audit-log retention policy (`deployer-operating-manual.md` §6.2). Any key whose era's entries are still within retention is still **active**; older keys can move to the **sealed archive**.
- [ ] Confirm that any open Article 22 right-to-human-review requests (`deployer-operating-manual.md` §8.1) have completed their entry-pulling step. Rotation mid-investigation creates avoidable confusion.
- [ ] Confirm no in-flight Article 20 GDPR export requests are mid-flight; if there is one, complete it first.
- [ ] Take a backup of the current audit log via `scripts/backup-*.sh`.
- [ ] Take a backup of the current `.env` and the prior-keys metadata (see §6 below for the metadata file).
- [ ] Brief the oversight person and the data-protection officer — both must know the rotation window and the verification commands.

---

## 5. Rotation procedure (scheduled or incident-driven)

Run from the operations engineer's workstation; the live droplet only sees the final secret values during the docker compose restart.

### Step 1 — Generate the new key

```bash
python3 -c 'import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())'
```

Treat the output as a top-tier secret. Do not paste into chat, do not commit to git, do not leave in shell history (use a here-document or `read -s`).

### Step 2 — Record the old key into the prior-keys metadata

The deployer maintains a file at `${DATA_ROOT}/audit_log_keys.json` with the following shape (see §6 for the schema). Append a new entry for the OLD key with an `archived_at` timestamp and the era it covered (`first_entry_at`, `last_entry_at`).

```bash
# On the droplet, capture the current key's era from the audit log itself.
# These two commands run BEFORE the new secret is wired in.
docker compose -f /opt/helpmefindthejob/docker-compose.prod.yml exec helpmefindthejob \
  python3 -c "from company_discovery.audit_log import _audit_log_singleton; \
              al = _audit_log_singleton(); print(al.first_entry_at, al.last_entry_at)"
```

Update `audit_log_keys.json` (kept under encrypted backup, NOT in git; see §6 below).

### Step 3 — Update the prod `.env`

Edit `/opt/helpmefindthejob/.env` and replace the `HELPMEFINDTHEJOB_AUDIT_SALT=...` line with the new value. The `:?` Docker Compose guard in `docker-compose.prod.yml` will refuse to start the container if the new value is empty or malformed, so a typo here fails fast rather than silently regenerating a per-process salt.

### Step 4 — Restart the container

```bash
cd /opt/helpmefindthejob
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
# Wait ~10s for the container to come up.
docker compose -f docker-compose.prod.yml logs --tail=20 helpmefindthejob | grep -i "audit_log\|FATAL"
```

Confirm zero `FATAL` lines and zero `HELPMEFINDTHEJOB_AUDIT_SALT not set` warnings. The `tests/test_phase13_audit_log.py::SaltFailFastTests::test_production_env_with_configured_salt_emits_no_warning` test pins the same invariant in CI.

### Step 5 — Write a single canary entry under the new key

The first post-rotation entry is the canary. Trigger it via a synthetic admin action (e.g., open `/api/admin/oversight/queue` while logged in as the admin) so the audit log records an `admin_action` event. Then verify the entry HMAC-chains correctly under the new key:

```bash
# From the operations engineer's workstation, with the new salt exported:
export HELPMEFINDTHEJOB_AUDIT_SALT="<new-key-base64>"
python3 -m company_discovery.verify_receipt_cli --tail 1 \
  --salt-b64 "$HELPMEFINDTHEJOB_AUDIT_SALT"
# Expected: ✓ chain valid under provided key
```

### Step 6 — Verify the multi-key path

Take the most recent pre-rotation entry (the second-to-last in the log) and verify it still chains correctly under the OLD key:

```bash
export HELPMEFINDTHEJOB_AUDIT_SALT="<old-key-base64>"
python3 -m company_discovery.verify_receipt_cli --tail-offset 1 --count 1 \
  --salt-b64 "$HELPMEFINDTHEJOB_AUDIT_SALT"
# Expected: ✓ chain valid under provided key
```

### Step 7 — Document the rotation

Append a dated entry to the rotation log (§7 below) with: rotation reason (scheduled vs incident class), new `kid`, the era boundary, verifier names, the two canary-verification outputs. The dated entry is the audit trail.

### Step 8 — Brief downstream users if applicable

If the deployer maintains analytics dashboards that use `user_opaque_id` for cohort analysis, brief the analytics owner that the next dashboard refresh will show a discontinuity for any user active across the rotation boundary. This is expected; it is also why the rotation cadence is 12 months and not shorter.

---

## 6. The prior-keys metadata file

Schema for `${DATA_ROOT}/audit_log_keys.json` (NOT in git; encrypted-at-rest backup):

```jsonc
{
  "active": [
    {
      "kid": "kid_2026Q2",
      "introduced_at": "2026-04-01T00:00:00Z",
      "archived_at": null,
      "first_entry_at": "2026-04-01T00:00:00Z",
      "last_entry_at": null,
      "salt_b64": "<base64-encoded-32-bytes>",
      "rotation_reason": "scheduled annual",
      "rotated_by": "ops@deployer.example",
      "verifier": "oversight@deployer.example"
    }
  ],
  "sealed": [
    {
      "kid": "kid_2025Q2",
      "introduced_at": "2025-04-01T00:00:00Z",
      "archived_at": "2026-04-01T00:00:00Z",
      "first_entry_at": "2025-04-01T00:00:00Z",
      "last_entry_at": "2026-03-31T23:59:59Z",
      "salt_b64": "<base64-encoded-32-bytes>",
      "rotation_reason": "scheduled annual",
      "rotated_by": "ops@deployer.example",
      "verifier": "oversight@deployer.example"
    }
  ],
  "destroyed": [
    {
      "kid": "kid_2024Q2",
      "introduced_at": "2024-04-01T00:00:00Z",
      "archived_at": "2025-04-01T00:00:00Z",
      "destroyed_at": "2026-04-01T00:00:00Z",
      "destruction_method": "shred -uvz",
      "destroyed_by": "ops@deployer.example",
      "verifier": "oversight@deployer.example"
    }
  ]
}
```

Lifecycle:

1. **Active** — the in-force key plus any key whose era's entries are still within the retention window.
2. **Sealed** — keys retained only for verification of historical entries; not used for new writes. Stored encrypted-at-rest, accessible only to the operations engineer and the data-protection officer.
3. **Destroyed** — keys whose era's entries have all aged out of retention. The key material is securely erased; the metadata (without `salt_b64`) is kept indefinitely as part of the audit trail.

A key NEVER moves backward (sealed → active, destroyed → sealed). One-way transitions only.

---

## 7. Rotation log

| Date | Kid | Reason | Era boundary | Operator | Verifier | Canary OK | Notes |
|---|---|---|---|---|---|---|---|
| 2026-05-24 | n/a | (none — first rotation will follow this playbook) | n/a | n/a | n/a | n/a | Playbook authored. Inaugural rotation scheduled for ~2027-04-01 unless an incident triggers earlier. |

Append below this row on every rotation. Never overwrite.

---

## 8. Threat model and what this playbook does not address

This playbook addresses key-lifecycle obligations under Article 12 + Article 26(6) + GDPR Article 32. It does **not** address:

- The decryption key for profile-at-rest (`HELPMEFINDTHEJOB_SECRET_KEY`) — see `compliance/data-governance.md` §"Key management" for that key's lifecycle.
- The TLS private key for the public-facing domain — Caddy auto-rotates these per the Let's Encrypt / ACME flow; out of scope.
- The AI provider credentials (`OPENAI_API_KEY`, etc.) — provider-side rotation is the BYO-AI user's responsibility, not the deployer's.
- The Stripe webhook signing secret — rotated via the Stripe dashboard; out of scope.
- OIDC client secrets for SSO integrations — rotated via the IdP's admin console; out of scope.

Each of those keys has its own lifecycle obligations and is intentionally kept distinct from the audit-log key so a compromise of one does not cascade into the other.

---

## 9. Test coverage

The behaviours this playbook depends on are pinned by:

- `tests/test_phase13_audit_log.py::SaltFailFastTests::test_production_env_with_no_salt_exits_one` — confirms a missing salt in production refuses to start.
- `tests/test_phase13_audit_log.py::SaltFailFastTests::test_production_env_with_configured_salt_succeeds` — confirms a configured salt resolves correctly.
- `tests/test_phase13_audit_log.py::SaltFailFastTests::test_production_env_with_configured_salt_emits_no_warning` — pins the "warning gone" invariant.

Future multi-key verification testing should add:

- A test that loads a synthetic two-era log and verifies the era 1 entries under the era 1 key and era 2 entries under the era 2 key.
- A test that asserts a forged entry inserted across the era boundary fails chain validation under both keys.

Both tests are deferred to Ceiling 2 Section 2.13 (reliability and operations); their absence does not block this playbook from being usable today, because rotation is a manual procedure with a human verifier on every step.
