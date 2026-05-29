<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Data Processing Agreement — Template

**For**: institutional buyers (Beratungsstellen, NGOs, public-
sector deployers, university career services) deploying
Helpmefindthejob on their own infrastructure for the benefit of
end-users who would, in GDPR terms, be the "data subjects."

**Status**: open-source template. Adapt to your jurisdiction.
This document is NOT legal advice. Have your DPO + counsel
review before signing.

**Roles in the typical deployment**:

| Party | GDPR role | Typical example |
|---|---|---|
| The deployer (you, the institutional buyer) | **Controller** of end-user personal data | Beratungsstelle X running its own deploy |
| The Helpmefindthejob project | **Software provider** (not a processor) — ships open-source code | The Commons Conservancy / NLnet-funded project |
| The end-user (data subject) | **Data subject** | A migrant in Aïcha's situation using the deployer's instance |
| Third-party AI provider (if BYO-key) | **Sub-processor** (only if the deployer configures one) | OpenAI, DeepSeek, Anthropic, Google, or local Ollama |
| Self-hosted LLM (Ollama) | **No sub-processor** — runs on the deployer's own machine | The deployer's Ollama instance |

**Critical clarification**: because helpmefindthejob is a
self-hosted open-source project (not a SaaS), the project
maintainers are NOT a processor in the GDPR sense — we do not
receive end-user data. The deployer self-hosts, controls the
data, and is solely responsible for the data flows.

When the deployer signs a DPA with their data subjects (or with
upstream controllers if the deployment is sub-contracted by
e.g. a city's social services department), this template
captures the typical structure.

---

## 0. Legal basis for this DPA

This Data Processing Agreement is concluded under **GDPR Article
28** (Processor), which mandates a binding contract between a
controller and any party that processes personal data on the
controller's behalf. The clauses below cover the minimum content
that Article 28(3) requires: subject matter, duration, nature
and purpose, type of data, categories of subjects, and the
controller's obligations + rights.

## 1. Subject matter

This DPA governs the processing of personal data by **{{DEPLOYER
NAME}}** (hereinafter "the Deployer") through the
Helpmefindthejob software instance deployed at **{{DEPLOYMENT
URL}}**, on behalf of **{{CONTROLLER NAME}}** (hereinafter "the
Controller"), in connection with the labour-market navigation
service the Controller provides to data subjects.

The processing covers:

- Employment-history data (CV text, work experience)
- Qualification claims (Anerkennung pathway status, certifications)
- Application-tracking data (which jobs the user has applied to)
- Communication context (chat messages with the AI assistant)
- Operational metadata (login timestamps, audit-log entries)

---

## 2. Duration of processing

Processing begins on the effective date of this agreement and
continues until terminated by either party with **30 days'
written notice**, OR until the data subject revokes consent under
Article 7(3) GDPR (whichever is sooner).

On termination, the Deployer SHALL:

1. Delete or return all personal data within **30 days**
2. Provide the Controller with a deletion certificate signed by
   the Deployer's DPO
3. Continue to honor outstanding GDPR Article 15 (access) and
   Article 17 (erasure) requests received before termination

---

## 3. Nature and purpose of processing

| Processing activity | Purpose | Legal basis (GDPR Art. 6) |
|---|---|---|
| Storing CV text, encrypted at rest | Enable AI-assisted job search | (a) consent or (f) legitimate interest (controller assessment) |
| Sending CV + job description to an AI provider when the user invokes `/auto-fit` etc. | Generate a fit score, cover letter, or CV tailoring | (a) consent — captured before first AI invocation |
| Recording AI invocations in an audit log | EU AI Act Article 12 compliance | (c) legal obligation |
| Generating Trust Receipts | Right to explanation of automated decisions (Art. 22 GDPR + Art. 86 AI Act) | (c) legal obligation |
| Aggregating cost-saving metrics (opt-in) | Demonstrate measured outcomes for funding renewal | (f) legitimate interest of the Controller |
| Computing public transparency aggregates with DP noise | Public accountability + Art. 50 disclosure transparency | (c) legal obligation + (f) legitimate interest |
| Issuing W3C Verifiable Credentials for recognised qualifications | Portable proof the user can carry to other systems | (b) contract / (a) consent |

---

## 4. Types of personal data + categories of data subjects

**Personal data categories** processed by the Deployer through
the software:

- **Contact data**: email address, optional name
- **Authentication data**: password hash (scrypt), TOTP secret
  (AEAD-encrypted)
- **Profile data**: CV text (AEAD-encrypted at rest), persona ID,
  friction-class classification, target roles, languages
- **Behavioural data**: job-search history, application status,
  chat messages with the AI assistant
- **Technical metadata**: session timestamps, IP address (in
  request logs only — never persisted to the application DB),
  user-agent
- **Audit metadata**: AI invocation events with opaque-hashed
  user IDs

**Special categories** (Art. 9 GDPR) — generally NOT processed,
but the deployer SHOULD verify because CV content may include:

- Health information (if a user discloses a disability in their
  CV)
- Religious / philosophical beliefs (if a user lists religious
  community work)
- Trade-union membership (if listed in work history)

The Deployer's privacy notice (per Art. 13 GDPR) MUST warn
users that voluntarily disclosing special-category data in
their CV creates additional processing they may not intend.

**Categories of data subjects**:

- End-users of the deployer's labour-market service
- Optionally: caseworkers / advisors using the back-office surface

---

## 5. Sub-processors

The Deployer SHALL maintain a current list of sub-processors at
**{{SUB-PROCESSOR REGISTRY URL}}** and notify the Controller
**14 days** in advance of any change.

**Typical sub-processors** for a default Helpmefindthejob
deployment:

| Sub-processor | Service | Data shared | Location |
|---|---|---|---|
| {{HOSTING PROVIDER}} (e.g., Hetzner, Scaleway, AWS Frankfurt) | Compute + storage | Encrypted backups; runtime DB | Specify EU region |
| {{LLM PROVIDER if BYO-key}} (e.g., OpenAI EU, DeepSeek, Anthropic, Google Gemini) | AI inference for `/auto-fit`, cover letter, CV tailoring | Prompts including CV text + job description; no opaque-hashed user ID is shared (the provider sees the AI request, not the user identity) | Specify region; refer to provider's DPA |
| {{EMAIL PROVIDER}} (SMTP relay for password resets + invites) | Transactional email | Email addresses, token URLs (single-use, 1-48h TTL) | Specify region |
| {{NONE if Ollama}} — self-hosted LLM | AI inference (local) | Runs on Deployer's machine; no third-party flow | Deployer infrastructure |

**Default Helpmefindthejob deployment**: NO sub-processor for AI
inference if the deployer uses manual mode (default) or local
Ollama. AI calls only fire when the user explicitly opts into a
paid provider.

---

## 6. Data subject rights

The Deployer SHALL support the data subject in exercising the
rights guaranteed under GDPR Articles 15-22 + Article 86 (AI
Act-specific). The software ships:

| Right | Article | Software surface | Manual fallback |
|---|---|---|---|
| Access | Art. 15 GDPR | `GET /api/user/export` returns full user record as JSON | DPO emails the JSON dump |
| Rectification | Art. 16 GDPR | User can edit profile + CV via Settings UI | DPO updates manually |
| Erasure | Art. 17 GDPR | `DELETE /api/account` cascades to all repository tables | DPO runs deletion script |
| Restriction | Art. 18 GDPR | User can mark profile inactive; AI calls refused while inactive | Manual flag in DB |
| Portability | Art. 20 GDPR | Same `/api/user/export` returns machine-readable JSON | DPO emails the JSON dump |
| Object | Art. 21 GDPR | Opt-out toggles per processing type in Settings | DPO honors written objection |
| No automated decision | Art. 22 GDPR | AI Act Article 13 transparency notice; no decision affects legal rights without human review; cost-cap refusals are not solely-automated for legal purposes | Deployer's human-oversight queue per `compliance/human-oversight-guide.md` |
| Trust Receipt | Art. 86 AI Act + transparency doctrine | Every AI decision auto-emits a downloadable Trust Receipt | CLI: `python -m company_discovery.verify_receipt_cli` |

The Deployer SHALL respond to data subject requests within **30
days** (or 90 days for complex requests, with notice within the
first 30) per Article 12(3) GDPR.

---

## 7. Security measures

The Deployer SHALL implement at minimum the technical and
organisational measures (TOMs) shipped with the software AND
maintained by the operator. Reference:
[`THREAT-MODEL.md`](../docs/THREAT-MODEL.md),
[`SECURITY.md`](../SECURITY.md), and
[`compliance/deployer-operating-manual.md`](deployer-operating-manual.md).

Minimum:

- **Encryption in transit**: TLS 1.2+ on all public endpoints
  (typically Caddy auto-issues Let's Encrypt certs)
- **Encryption at rest**: AEAD (ChaCha20-Poly1305) for CV text +
  TOTP secrets via `crypto_kit.py`; `HELPMEFINDTHEJOB_DATA_KEY` env var
  MUST be set to a 32-byte random value (not the default
  HKDF-from-SECRET_KEY fallback)
- **Authentication**: scrypt password hashing (N=2^15); optional
  TOTP 2FA
- **Access control**: per-user data scoping at the repository
  layer; admin-only endpoints gated by `require_admin()`
- **Audit logging**: AI Act Article 12 HMAC-chained audit log;
  admin actions captured in `data/admin_audit.log`
- **Backups**: operator-managed, encrypted, off-host destination
- **Vulnerability management**: monitor SECURITY.md for advisories;
  CycloneDX SBOM at `docs/releases/v0.1.0-sbom.json` enables
  external CVE matching

The Deployer SHALL conduct a **DPIA (Data Protection Impact
Assessment)** before going live — template at
[`compliance/fundamental-rights-impact-assessment-template.md`](fundamental-rights-impact-assessment-template.md).

---

## 8. International transfers

If any sub-processor is outside the EEA, the Deployer SHALL
ensure at minimum one of:

1. **Adequacy decision** (UK, Switzerland, etc. per EC list)
2. **Standard Contractual Clauses (SCCs)** signed with the
   sub-processor (Module Two: controller → processor)
3. **Binding Corporate Rules** if intra-group

For US-based AI providers (OpenAI, Anthropic, Google), the
Deployer should consult the provider's published DPA + Schrems
II transfer-impact assessment.

**Default Helpmefindthejob position**: the software runs entirely
on the Deployer's infrastructure with no mandatory third-party
flows. International transfers happen ONLY when the user opts
into a non-EU AI provider, AND the Deployer's privacy notice
discloses this.

---

## 9. Breach notification

In the event of a personal data breach the Deployer SHALL:

- Notify the Controller within **24 hours** of becoming aware
- Notify the relevant supervisory authority within **72 hours**
  per Art. 33 GDPR
- Provide breach particulars: nature, categories, approximate
  number of data subjects + records, likely consequences,
  measures taken

The software's audit log + admin audit log provide the forensic
basis for breach investigation. Operators MUST retain at least
**12 months** of audit-log history.

---

## 10. Audit + inspection

The Controller may audit the Deployer's processing activities
once per year with **30 days' written notice**, or at any time
following a breach. The audit SHALL be limited to verifying
compliance with this DPA and SHALL NOT disrupt service.

Self-audit artefacts the Deployer SHIPS ready-to-share:

- [`/transparency`](#) endpoint — public aggregate of AI
  invocations, DP-noised
- Audit log access via GDPR Article 15 request (per data subject)
- Trust Receipt CLI verifier: `python -m company_discovery.verify_receipt_cli`
- SBOM: `docs/releases/v0.1.0-sbom.json`
- Reproducible-build chain: `docs/releases/v0.1.0-signing.md`

---

## 11. Liability

Standard mutual indemnification. **The Helpmefindthejob project
itself is NOT a party to this DPA** — the deployer is the
controller of their own deploy. Any warranty disclaimer in the
Apache 2.0 LICENSE applies.

For institutional deployments where the buyer requires a
warranted SaaS instead of self-hosted, contact the Commons
Conservancy for a list of partner integrators who offer this
commercially under a separate contract.

---

## 12. Signatures

| Party | Name | Title | Signature | Date |
|---|---|---|---|---|
| Controller | {{NAME}} | {{TITLE}} | _____________ | _____________ |
| Deployer (Data Controller for end-users) | {{NAME}} | {{TITLE}} | _____________ | _____________ |
| DPO (Deployer side) | {{NAME}} | DPO | _____________ | _____________ |

---

## How to use this template

1. **Replace every double-brace placeholder** — the `DEPLOYER_NAME`,
   `DEPLOYMENT_URL`, `CONTROLLER_NAME`, sub-processor, and signature-table slots —
   with the relevant party name or value, by hand or with
   `python -m scripts.fill_template … --strict` against a JSON config (see
   `compliance/starter-kit/`). `--strict` fails if any slot is left unfilled.
2. **Customise §5 sub-processors** based on your actual deploy:
   delete the LLM row if you're manual-mode-only, delete the
   email-provider row if you've configured local-only outbox.
3. **Re-validate §6 surfaces** against the running app: every
   API endpoint mentioned MUST be deployed in your instance.
4. **Have counsel review** before signing.
5. **File a copy** with your DPO and the Controller.

## License

This template is released under Apache 2.0 (same as the rest of
the project). Adapt freely. We welcome upstream contributions
that improve the template's clarity, accuracy, or coverage of
edge cases.
