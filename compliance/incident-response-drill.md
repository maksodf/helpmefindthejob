<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Incident-response drill — methodology + dated log

**Article**: AI Act Article 73 (serious-incident reporting) + GDPR Article 33 (breach notification within 72 h) + Article 26(5) (deployer monitoring obligation).
**Audience**: deployer's named oversight person + the data-protection officer + the operations engineer who has root access to the production droplet.
**Pairs with**: [`deployer-operating-manual.md`](deployer-operating-manual.md) §10 (the 5-step incident workflow that this drill exercises).
**Frequency**: quarterly drill recommended (PlanTowardPerfection box 2.14.3); annual minimum.
**Status**: living document. Append a dated drill record on every execution.

---

## 1. Why drill

The Article 26(5) monitoring obligation is not a paperwork exercise; the deployer must be able to *act* when an incident actually happens. The chain in `deployer-operating-manual.md` §10 (stabilise → document → notify → remediate → post-incident review) has 5 steps and ~12 sub-decisions. Running through it cold during a real incident — at 2 AM, under regulatory time pressure — is the wrong time to discover that a step assumes a tool you don't have or a contact you haven't briefed.

The drill is the rehearsal. The dated drill log is the accountability evidence under Article 5(2) GDPR and Article 13 AI Act.

The drill is also where the deployer-side process meets the project-side process: the upstream `incident-ai-act`-tagged issue path, the security disclosure channel in `SECURITY.md`, the response-SLA the maintainer commits to, the audit-log slice the deployer pulls and shares.

---

## 2. Drill scenarios

Run one per quarter. Rotate through these four classes so the deployer's runbook gets exercised across the realistic spectrum:

### Scenario A — Personal-data breach (GDPR Article 33)

**Premise**: a misconfigured backup target accidentally writes the SQLite database (encrypted profile + chat data) to a public S3-compatible bucket. The maintainer is notified by a researcher via security@helpmefindthejob.org.

**Tested behaviours**:
- 72-hour notification clock (GDPR Article 33) — does the deployer's DPO process trigger within 24 h of notification?
- Audit-log capture: deployer extracts the audit-log slice covering the affected period.
- User notification timeline: does the deployer's user-comms template (Article 34 if high-risk) fire correctly?
- Containment: the misconfigured backup target is locked; the leaked data is pulled where possible.
- Forensic record: each step is timestamped.

### Scenario B — Compromised audit-log key (Article 12 + GDPR Article 32)

**Premise**: a former contractor still has access to the `HELPMEFINDTHEJOB_AUDIT_SALT` env var because the rotation was never executed after their departure. Their access is discovered during an unrelated audit.

**Tested behaviours**:
- Key rotation procedure (`audit-log-key-rotation.md`) — does the operator complete the 8-step rotation in the documented order?
- Prior-keys metadata correctness — does the rotated key land in the `sealed` array with correct era boundaries?
- Canary verification — does the post-rotation entry HMAC-chain correctly under the new key, AND do the pre-rotation entries still HMAC-chain correctly under the sealed-old key?
- Communication: the security-policy update is posted via the maintainer's chosen channel.

### Scenario C — AI-output bias incident (AI Act Article 26(5) monitoring obligation)

**Premise**: a Beratungsstelle advisor reports that a §16d-pathway user (Aïcha-class) consistently receives fit-scores below 30 for clearly-Anerkennungs-friendly employer roles. The advisor has 3 documented examples covering 6 weeks.

**Tested behaviours**:
- Kill-switch activation: does the operator reach for `HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true` while the analysis is in flight?
- Investigation: the audit-log slice covering the affected user + affected scenarios is pulled; the AI-output text + prompt + provider + model + cost-cap context all flow through.
- Root-cause analysis: maps the failure to one of the known finding classes (F1 friction-harshness, F2 anchor-parking, OR a new class).
- Upstream notification: the deployer files an `incident-ai-act`-tagged issue at the project repository per `deployer-operating-manual.md` §10.
- Article 22 right-to-human-review surface: the affected user gets a structured response within the 1-month SLA.

### Scenario D — Supply-chain compromise (Article 11 + SLSA scope)

**Premise**: a dependency in `requirements.txt` (suppose `psycopg`) is the subject of a published CVE with active exploitation in the wild. The CVE is announced 2 hours ago via the Sigstore/GitHub Advisory database.

**Tested behaviours**:
- Discovery: does the deployer's dependency-monitoring (OpenSSF Scorecard cron / pip-audit / Renovate) catch the CVE within the same 24 h window?
- Mitigation: temporarily disable the affected code path (or apply the upstream patch via pinned-fork).
- Audit-log correlation: was the affected code-path executed during the vulnerable window? Pull the audit-log evidence.
- User notification: was any user data exposed? If yes, fall back to Scenario A workflow.

---

## 3. Drill procedure (per scenario)

Run the drill in a non-production environment first; promote to prod-shadow only when the drill team has verbalised every step at least once.

### Step 3.1 — Pre-drill setup (T-1 day)

- Confirm the drill date with the named oversight person + the DPO + the operations engineer.
- Pull the audit-log baseline (sha + line count + most-recent timestamp) so post-drill diffs are clean.
- Snapshot the env-var inventory (NOT the values; just the keys).
- Verify the maintainer is reachable for the upstream-notification step (via the `SECURITY.md` channel).

### Step 3.2 — Drill open (T+0:00)

- The drill facilitator presents the scenario premise to the team.
- Start the wall clock; everything timestamped from here.
- The team runs the actual incident-response chain per `deployer-operating-manual.md` §10:
  1. **Stabilise** — apply the kill switch if applicable; verify it took effect.
  2. **Document** — capture the audit-log slice, the user's reported experience, the system state at the time of incident.
  3. **Notify** — DPO + oversight person + senior-accountable individual + maintainer (via SECURITY.md) + supervisory authority if Sev-1.
  4. **Remediate** — apply the documented mitigations.
  5. **Post-incident review** — what worked, what failed, what we changed.

### Step 3.3 — Drill close (T+ realistic, typically 2–4 hours)

- The drill facilitator declares the drill complete.
- The team runs an after-action review (AAR) within 24 h, while the experience is fresh:
  - Which step took longer than expected?
  - Which decision was made by guess vs by documented procedure?
  - Which tool was missing or unavailable?
  - Which contact was harder to reach than the runbook implied?

### Step 3.4 — Documented update

- The runbook (`deployer-operating-manual.md` §10) is updated with whatever the AAR surfaced.
- The drill log below is appended with a dated row.
- Any process-change is propagated to the upstream project via a pull request if it's general-purpose, OR documented in the deployer's local fork.

---

## 4. What the drill is NOT

This drill exercises the **deployer-side process** for an incident affecting their deployment. It does NOT:

- Test the project's own code paths (that's the unit suite + the CI workflows).
- Test the upstream maintainer's incident-response (the maintainer's own drill is documented separately at `SECURITY.md` + the maintainer-side incident playbook).
- Substitute for a full penetration test (pen-test is `PlanTowardPerfection.MD` §2.14.1; this drill is the operational rehearsal, not the offensive-security audit).
- Substitute for a third-party security audit (the audit is `PlanTowardPerfection.MD` §2.14.1 + the operational rehearsal happens here on top of any audit's findings).

The drill complements those other surfaces; it doesn't replace them.

---

## 5. Maintainer-side scenario (project-only)

The maintainer also runs a quarterly drill on the **upstream-project** incident path:

- **Scenario M1 — `incident-ai-act` issue triage**: a deployer files an `incident-ai-act`-tagged issue. The maintainer's response within the documented 5-working-day acknowledgement target?
- **Scenario M2 — security disclosure**: a researcher files a `SECURITY.md`-channel disclosure. The maintainer's response within the documented 5-working-day target? Does the rotation of any affected secret happen within the 30-day target?

The maintainer's drill log is a separate section in the project-side `docs/incident-playbook.md` (operator-private; not the deployer-facing one).

---

## 6. Drill log

| Date | Scenario | Drill team | Wall-clock duration | What broke | What got fixed | Notes |
|---|---|---|---|---|---|---|
| 2026-05-24 | (none — this file landed in the PlanTowardPerfection box 2.14.3 slice; first scheduled drill is **2026-Q4** alongside the first NGO pilot deployment per ROADMAP.md 2026 Q4 row) | n/a | n/a | n/a | n/a | Initial methodology authored. The drill team is the maintainer + the partner-NGO's named oversight person; the maintainer-side scenarios M1 + M2 also start on this cadence. |

Append below this row on every drill. Never overwrite a prior row; the audit trail is the accountability evidence.

---

## 7. Cross-references

- Deployer operating manual §10 (the workflow this drill exercises): [`deployer-operating-manual.md`](deployer-operating-manual.md)
- Audit-log key rotation playbook (Scenario B reference): [`audit-log-key-rotation.md`](audit-log-key-rotation.md)
- Accuracy + bias methodology (Scenario C reference): [`accuracy-and-bias-testing.md`](accuracy-and-bias-testing.md)
- Article 22 right-to-human-review (Scenario C remediation surface): [`deployer-operating-manual.md`](deployer-operating-manual.md) §8.1
- GDPR Article 35 DPIA (the broader risk register this drill validates): [`gdpr-article-35-dpia.md`](gdpr-article-35-dpia.md)
- Security disclosure channel: [`../SECURITY.md`](../SECURITY.md)
- Compliance INDEX: [`INDEX.md`](INDEX.md)
