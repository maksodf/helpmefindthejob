# Standards we implement

Helpmefindthejob is **standards-anchored on purpose**. Adopters inherit interoperability and the ability to switch out individual layers without forking. This file is the manifest. If a row claims a standard, the implementing file is named so a reviewer can verify.

## Licensing + governance

| Standard | Where | Status |
|---|---|---|
| [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) | [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`TRADEMARK.md`](TRADEMARK.md), SPDX headers in every Python file | Shipped |
| Apache Individual Contributor License Agreement model | [`cla.md`](cla.md) — adapted, no novel terms | Shipped |
| [SPDX-License-Identifier](https://spdx.org/) | `# SPDX-License-Identifier: Apache-2.0` on every Python source file; `.pre-commit-config.yaml` enforces on staged files | Shipped |
| [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) | [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) (adopted by reference to canonical CC BY 4.0 source) | Shipped |
| [Semantic Versioning 2.0.0](https://semver.org/) | MCP tool catalogue version policy in [`docs/mcp-server.md`](docs/mcp-server.md); applied to release tags from `v0.1.0` onward | Shipped (policy); first tagged release in Week 3 §3.3 |
| [Keep a Changelog](https://keepachangelog.com/) | `CHANGELOG.md` format committed in Week 3 §3.3 | Planned |

## Protocols + interfaces

| Standard | Where | Status |
|---|---|---|
| [Model Context Protocol](https://modelcontextprotocol.io) v `2024-11-05` | [`mcp_server.py`](mcp_server.py); validated end-to-end by [`tests/test_phase11_mcp_input_validation.py`](tests/test_phase11_mcp_input_validation.py) | Shipped |
| [JSON-RPC 2.0](https://www.jsonrpc.org/specification) | MCP transport in `mcp_server.py` (over stdio) | Shipped |
| [JSON Schema Draft 7](https://json-schema.org/specification-links#draft-7) | Every tool's `inputSchema` in [`company_discovery/mcp_tools.py`](company_discovery/mcp_tools.py); enforced by `jsonschema.Draft7Validator` before `tools/call` dispatch | Shipped |
| [RFC 7807 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc7807) | MCP `tools/call` validation-failure payloads (`status`, `type`, `title`, `detail`, `instance`, `validationPath`, `violatedRule`) | Shipped |
| [RFC 9116 — `/.well-known/security.txt`](https://www.rfc-editor.org/rfc/rfc9116) | [`static/.well-known/security.txt`](static/.well-known/security.txt) served by `app.py` at `/.well-known/security.txt` (`text/plain; charset=utf-8`, 200 verified via curl probe 2026-05-19). Lists GitHub Security Advisories + placeholder email per Decision 12. Cross-referenced from [`SECURITY.md`](SECURITY.md). | Shipped |
| [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) date/time | All timestamps server-side and in audit-log entries (`data/admin_audit.log`) | Shipped |
| [ISO 639-1](https://www.loc.gov/standards/iso639-2/php/code_list.php) language tags | i18n locale identifiers (`en`, `de`); locale parser normalises `en_US`/`en-GB`/`DE` etc. | Shipped |

## Employment + civic-data vocabularies

| Standard | Where | Status |
|---|---|---|
| [schema.org JobPosting](https://schema.org/JobPosting) | Output shape of `scan_company_career_page`, `extract_direct_jobs_from_company_site`, `import_discovered_job` | Shipped (shape); SEO `/jobs/<slug>` pages emit JSON-LD JobPosting |
| [schema.org Organization](https://schema.org/Organization) | Output shape of `suggest_relevant_companies`, `add_company_to_watchlist` | Shipped |
| [ESCO](https://esco.ec.europa.eu/) — European Skills, Competences, Qualifications and Occupations | Persona skill mapping; planned `query_esco_skill` MCP tool in §2.3 will expose taxonomy lookup | §2.3 expansion + §2.4 dataset integration |
| [EURES](https://eures.europa.eu/) job-posting schema | Planned `export_eures_compatible` MCP tool in §2.3 will emit EURES-shaped exports | §2.3 + §2.4 |
| [BIBB / Anabin](https://anabin.kmk.org/anabin.html) Anerkennung references | German Anerkennung path guidance in journey state machine; not directly schema-imported, but cited in user-facing flows | Cited (content); schema-import is post-grant scope |

## Accessibility + transparency

| Standard | Where | Status |
|---|---|---|
| [WCAG 2.2 Level AA](https://www.w3.org/TR/WCAG22/) | Audit + remediation shipped in [`ACCESSIBILITY.md`](ACCESSIBILITY.md) | Shipped — 16 fixes across 3 + 1 audit passes; 0/0/0/0 across 33 audited surfaces (8 app + 5 docs unauth + 8 auth × 2 schemes + 4 dynamic). HAN University manual review remains a post-Commons-Conservancy-admission option. |
| German Impressum per [§ 5 TMG](https://www.gesetze-im-internet.de/tmg/__5.html) | [`static/impressum.html`](static/impressum.html) | Shipped — references `helpmefindthejob.com` (canonical domain per [Decision 22](docs/grant/04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob)); maintainer wires the DNS to land the surface. |
| EU AI Act ([Regulation 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)) — high-risk AI obligations under Annex III §4 | Compliance pack at [`compliance/`](compliance/): risk-management plan (Art. 9), data governance (Art. 10), technical documentation aligned with Annex IV (Art. 11), audit logging (Art. 12), transparency notice + deployer operating manual (Art. 13), human-oversight guide + `/api/admin/oversight/queue` (Art. 14), accuracy and bias testing methodology (Art. 15), database registration template (Art. 49), Fundamental Rights Impact Assessment template (Art. 27) | Shipped — 11 documents covering Articles 9–15 + 27 + 49, with audit-log emitter and human-oversight admin endpoint wired into the runtime. |

## Privacy + security

| Standard | Where | Status |
|---|---|---|
| [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj) — data-minimisation, user-export, user-deletion paths | Throughout; audit-log for admin actions, encrypted PII at rest, 7-day deletion grace, per-user data isolation | Shipped (process); legal counsel review in Week 3 |
| [ChaCha20-Poly1305 AEAD](https://www.rfc-editor.org/rfc/rfc8439) | [`company_discovery/crypto_kit.py`](company_discovery/crypto_kit.py) for `profile.cv_text` and `users.totp_secret` columns; AAD = user_id; HKDF-SHA256 ([RFC 5869](https://www.rfc-editor.org/rfc/rfc5869)) for key derivation from `DIRECTJOB_SECRET_KEY` | Shipped |
| [TOTP / HOTP (RFC 6238 / RFC 4226)](https://www.rfc-editor.org/rfc/rfc6238) 2FA | [`company_discovery/auth.py`](company_discovery/auth.py) `verify_totp`, `_totp_at` | Shipped |
| [otpauth:// URI scheme](https://github.com/google/google-authenticator/wiki/Key-Uri-Format) for QR-code provisioning | `_format_otpauth_url` in `auth.py` | Shipped |

## Operational

| Standard | Where | Status |
|---|---|---|
| [OCI image format](https://github.com/opencontainers/image-spec) | `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`; image named `helpmefindthejob:latest` independent of local repo directory | Shipped |
| [Nix flake reproducible build](https://nixos.wiki/wiki/Flakes) | [`flake.nix`](flake.nix) + [`flake.lock`](flake.lock) at repo root; pins `nixos-25.05` nixpkgs commit + Python 3.12; `nix develop` / `nix run` / `nix flake check` documented in [`docs/deployment-recipe.md`](docs/deployment-recipe.md) §12 | Shipped |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | Workflow + badge in Week 3 §3.2 | Planned |
| [CycloneDX SBOM](https://cyclonedx.org/) | [`docs/releases/v0.1.0-sbom.json`](docs/releases/v0.1.0-sbom.json) generated by `cyclonedx-py environment` v7.3.0 (CycloneDX 1.6 format; 91 components covering runtime + dev deps + transitives). Committed under `docs/releases/` AND attached to the v0.1.0 GitHub Release. | Shipped |
| [cosign](https://docs.sigstore.dev/cosign/overview/) signed releases | v0.1.0 source tarball cosign-signed with a long-lived ECDSA P-256 key pair (cosign 3.0.6, model b). Bundle + public key: [`docs/releases/v0.1.0-source.tar.gz.sigstore`](docs/releases/v0.1.0-source.tar.gz.sigstore) + [`docs/releases/v0.1.0-cosign.pub`](docs/releases/v0.1.0-cosign.pub). Verify with `cosign verify-blob ... --insecure-ignore-tlog`. v0.2.0+ plans to switch to keyless via GH Actions OIDC; full doc at [`docs/releases/v0.1.0-signing.md`](docs/releases/v0.1.0-signing.md). | Shipped |
| [Conventional Commits](https://www.conventionalcommits.org/) | Commit-message convention in [`CONTRIBUTING.md`](CONTRIBUTING.md) | Shipped |

## Internal protocols (work-in-progress, may become open standards)

These are project-internal protocols today. As cross-civic-agent composition matures (Phase 2 of the post-grant arc — see [`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md)) we may propose them as open specs through a W3C Community Group or an informal cross-civic-agent working group.

| Spec | Where | Status |
|---|---|---|
| Portable civic profile schema | Planned `/static/.well-known/civic-profile.schema.json` — see [`docs/grant/09-mcp-composition.md`](docs/grant/09-mcp-composition.md) §"The portable civic profile" | Internal; open-spec candidate for Phase 2 |
| Cross-civic-agent referral protocol | `propose_referral` MCP tool, lands Week 2 §2.3 | Internal; open-spec candidate for Phase 2 |
| Audit-log entry schema (EU AI Act Article 12 conformant) | Documented in Week 2 §2.8 compliance pack; canonical shape in `data/admin_audit.log` | Designed; shipping Week 2 |

## Where each claim is verifiable

For a NLnet reviewer or institutional adopter doing a 10-minute deep-check of the standards claims:

- **License + governance**: open [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`cla.md`](cla.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). All are at repo root.
- **MCP composition**: spawn `python3 mcp_server.py`, send the JSON-RPC `initialize` and `tools/list` calls documented in [`docs/mcp-server.md`](docs/mcp-server.md). Catalogue version + 8 tools + per-tool `inputSchema` come back.
- **Schema enforcement**: send a deliberately-malformed `tools/call` (e.g., omit a required field) and observe the RFC 7807 Problem Details payload with `violatedRule: "required"`. The test file [`tests/test_phase11_mcp_input_validation.py`](tests/test_phase11_mcp_input_validation.py) automates this.
- **AEAD encryption**: read [`company_discovery/crypto_kit.py`](company_discovery/crypto_kit.py) (142 lines) and [`tests/test_phase9_totp_aead_migration.py`](tests/test_phase9_totp_aead_migration.py) for the round-trip / tamper / AAD-mismatch / nonce-uniqueness assertions.
- **AI Act compliance**: open `compliance/` (lands Week 2 §2.8).
- **i18n parity**: run `python3 -m unittest tests.test_round5_i18n` — the parity check is part of the 925-test suite.
- **Full test suite**: `python3 -m unittest discover tests` runs in ~18 s on a bare host (verified 2026-05-18; full results in [`docs/grant/feature-verification-2026-05-18.md`](docs/grant/feature-verification-2026-05-18.md) §8).
