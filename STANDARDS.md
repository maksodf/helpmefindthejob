# Standards we implement

Helpmefindthejob is **standards-anchored on purpose**. Adopters inherit interoperability and the ability to switch out individual layers without forking. This file is the manifest. If a row claims a standard, the implementing file is named so a reviewer can verify.

## Licensing + governance

| Standard | Where | Status |
|---|---|---|
| [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) | [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`TRADEMARK.md`](TRADEMARK.md), SPDX headers in every Python file | Shipped |
| Apache Individual Contributor License Agreement model | [`cla.md`](cla.md) — adapted, no novel terms | Shipped |
| [SPDX-License-Identifier](https://spdx.org/) | `# SPDX-License-Identifier: Apache-2.0` on every Python source file; `.pre-commit-config.yaml` enforces on staged files | Shipped |
| [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) | [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) (adopted by reference to canonical CC BY 4.0 source) | Shipped |
| [Semantic Versioning 2.0.0](https://semver.org/) | MCP tool catalogue version policy in [`docs/mcp-server.md`](docs/mcp-server.md); applied to release tags from `v0.1.0` onward | Shipped — `v0.1.0` released 2026-05-18 with annotated tag, cosign signature, CycloneDX SBOM. |
| [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) | [`CHANGELOG.md`](CHANGELOG.md) at repo root; `[Unreleased]` + `[0.1.0]` blocks with Added/Changed/Deprecated/Removed/Fixed/Security sections. | Shipped. |

## Protocols + interfaces

| Standard | Where | Status |
|---|---|---|
| [Model Context Protocol](https://modelcontextprotocol.io) v `2024-11-05` | [`mcp_server.py`](mcp_server.py); validated end-to-end by [`tests/test_phase11_mcp_input_validation.py`](tests/test_phase11_mcp_input_validation.py) | Shipped |
| [JSON-RPC 2.0](https://www.jsonrpc.org/specification) | MCP transport in `mcp_server.py` (over stdio) | Shipped |
| [JSON Schema Draft 7](https://json-schema.org/specification-links#draft-7) | Every tool's `inputSchema` in [`company_discovery/mcp_tools.py`](company_discovery/mcp_tools.py); enforced by `jsonschema.Draft7Validator` before `tools/call` dispatch | Shipped |
| [RFC 7807 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc7807) | MCP `tools/call` validation-failure payloads (`status`, `type`, `title`, `detail`, `instance`, `validationPath`, `violatedRule`) | Shipped |
| [RFC 9116 — `/.well-known/security.txt`](https://www.rfc-editor.org/rfc/rfc9116) | [`static/.well-known/security.txt`](static/.well-known/security.txt) served by `app.py` at `/.well-known/security.txt` (`text/plain; charset=utf-8`, 200 verified via curl probe 2026-05-19). Lists GitHub Security Advisories + `security@helpmefindthejob.org`. Cross-referenced from [`SECURITY.md`](SECURITY.md). | Shipped |
| [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) date/time | All timestamps server-side and in audit-log entries (`data/admin_audit.log`) | Shipped |
| [ISO 639-1](https://www.loc.gov/standards/iso639-2/php/code_list.php) language tags | i18n locale identifiers (`en`, `de`); locale parser normalises `en_US`/`en-GB`/`DE` etc. | Shipped |

## Employment + civic-data vocabularies

| Standard | Where | Status |
|---|---|---|
| [schema.org JobPosting](https://schema.org/JobPosting) | Output shape of `scan_company_career_page`, `extract_direct_jobs_from_company_site`, `import_discovered_job` | Shipped (shape); SEO `/jobs/<slug>` pages emit JSON-LD JobPosting |
| [schema.org Organization](https://schema.org/Organization) | Output shape of `suggest_relevant_companies`, `add_company_to_watchlist` | Shipped |
| [ESCO](https://esco.ec.europa.eu/) — European Skills, Competences, Qualifications and Occupations | **ESCO-aligned curated reference dataset** at [`reference/esco/`](reference/esco/) — 30 occupations + 50 skills covering the seven-persona panel + the Bundesagentur 2025 shortage list. Consumed by the `query_esco_skill` MCP tool. | Shipped — curated subset only. Full taxonomy integration (~3 000 occupations + ~13 500 skills) is Phase 2 work. |
| [EURES](https://eures.europa.eu/) job-posting schema | **EURES-compatible projection contract** — `export_eures_compatible` MCP tool emits a JSON shape matching the EURES schema; tested by [`tests/test_phase12_esco_eures.py`](tests/test_phase12_esco_eures.py). | Shipped — projection only. Live EURES API transport is Phase 2 work. |
| [BIBB / Anabin](https://anabin.kmk.org/anabin.html) Anerkennung references | German Anerkennung path guidance in journey state machine; not directly schema-imported, but cited in user-facing flows | Cited (content); schema-import is post-grant scope |

## Accessibility + transparency

| Standard | Where | Status |
|---|---|---|
| [WCAG 2.2 Level AA](https://www.w3.org/TR/WCAG22/) | Audit + remediation shipped in [`ACCESSIBILITY.md`](ACCESSIBILITY.md) | Shipped — 16 fixes across 3 + 1 audit passes; 0/0/0/0 across 33 audited surfaces (8 app + 5 docs unauth + 8 auth × 2 schemes + 4 dynamic). HAN University manual review remains a post-Commons-Conservancy-admission option. |
| German Impressum per [§ 5 TMG](https://www.gesetze-im-internet.de/tmg/__5.html) | [`static/impressum.html`](static/impressum.html) | Shipped — references `helpmefindthejob.org` (canonical domain); maintainer wires the DNS to land the surface. |
| EU AI Act ([Regulation 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)) — high-risk AI obligations under Annex III §4 | Compliance pack at [`compliance/`](compliance/): risk-management plan (Art. 9), data governance (Art. 10), technical documentation aligned with Annex IV (Art. 11), audit logging (Art. 12), transparency notice + deployer operating manual (Art. 13), human-oversight guide + `/api/admin/oversight/queue` (Art. 14), accuracy and bias testing methodology (Art. 15), database registration template (Art. 49), Fundamental Rights Impact Assessment template (Art. 27) | Shipped — 11 documents covering Articles 9–15 + 27 + 49, with audit-log emitter and human-oversight admin endpoint wired into the runtime. |

## Privacy + security

| Standard | Where | Status |
|---|---|---|
| [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj) — data-minimisation, user-export, user-deletion paths | Throughout; audit-log for admin actions, encrypted PII at rest, 7-day deletion grace, per-user data isolation | Shipped (process); legal counsel review remains Phase 2 — no independent DPIA published. |
| [ChaCha20-Poly1305 AEAD](https://www.rfc-editor.org/rfc/rfc8439) | [`company_discovery/crypto_kit.py`](company_discovery/crypto_kit.py) for `profile.cv_text` and `users.totp_secret` columns; AAD = user_id; HKDF-SHA256 ([RFC 5869](https://www.rfc-editor.org/rfc/rfc5869)) for key derivation from `HELPMEFINDTHEJOB_SECRET_KEY` | Shipped |
| [TOTP / HOTP (RFC 6238 / RFC 4226)](https://www.rfc-editor.org/rfc/rfc6238) 2FA | [`company_discovery/auth.py`](company_discovery/auth.py) `verify_totp`, `_totp_at` | Shipped |
| [otpauth:// URI scheme](https://github.com/google/google-authenticator/wiki/Key-Uri-Format) for QR-code provisioning | `_format_otpauth_url` in `auth.py` | Shipped |

## Operational

| Standard | Where | Status |
|---|---|---|
| [OCI image format](https://github.com/opencontainers/image-spec) | `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`; image named `helpmefindthejob:latest` independent of local repo directory | Shipped |
| [Nix flake reproducible build](https://nixos.wiki/wiki/Flakes) | [`flake.nix`](flake.nix) + [`flake.lock`](flake.lock) at repo root; pins `nixos-25.05` nixpkgs commit + Python 3.12; `nix develop` / `nix run` / `nix flake check` documented in [`docs/deployment-recipe.md`](docs/deployment-recipe.md) §12 | Shipped |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | [`.github/workflows/scorecard.yml`](.github/workflows/scorecard.yml) (weekly cron + push-to-main) — SARIF results uploaded to the GitHub Security tab. All six project workflows pinned to full 40-char commit SHAs per OpenSSF "pinned-dependencies". README badge linked at the top of the project README. | Shipped |
| [CycloneDX SBOM](https://cyclonedx.org/) | [`docs/releases/v0.1.0-sbom.json`](docs/releases/v0.1.0-sbom.json) generated by `cyclonedx-py environment` v7.3.0 (CycloneDX 1.6 format; 91 components covering runtime + dev deps + transitives). Committed under `docs/releases/` AND attached to the v0.1.0 GitHub Release. | Shipped |
| [cosign](https://docs.sigstore.dev/cosign/overview/) signed releases | v0.1.0 source tarball cosign-signed with a long-lived ECDSA P-256 key pair (cosign 3.0.6, model b). Bundle + public key: [`docs/releases/v0.1.0-source.tar.gz.sigstore`](docs/releases/v0.1.0-source.tar.gz.sigstore) + [`docs/releases/v0.1.0-cosign.pub`](docs/releases/v0.1.0-cosign.pub). Verify with `cosign verify-blob ... --insecure-ignore-tlog`. v0.2.0+ plans to switch to keyless via GH Actions OIDC; full doc at [`docs/releases/v0.1.0-signing.md`](docs/releases/v0.1.0-signing.md). | Shipped |
| [Conventional Commits](https://www.conventionalcommits.org/) | Commit-message convention in [`CONTRIBUTING.md`](CONTRIBUTING.md) | Shipped |

## Composition protocol + internal specs

The cross-civic-agent composition contract has been promoted from internal to a published draft spec — **CACP v0.1** ([`docs/protocol/cacp-v0.1.md`](docs/protocol/cacp-v0.1.md)) — with a runnable conformance suite (`python -m conformance.cacp`; the reference server passes 14/14). Further cross-civic-agent specs may follow through a W3C Community Group or an informal working group (Phase 2 of the post-grant arc — see [`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md)).

| Spec | Where | Status |
|---|---|---|
| Civic Agent Composition Protocol (CACP) v0.1 | [`docs/protocol/cacp-v0.1.md`](docs/protocol/cacp-v0.1.md) + conformance suite `conformance/cacp/` | Published draft; reference server passes conformance 14/14 |
| Portable civic profile schema | [`static/.well-known/civic-profile.schema.json`](static/.well-known/civic-profile.schema.json) (served; the CACP v0.1 data contract) | Shipped — pinned by `tests/test_civic_profile_schema.py` |
| Cross-civic-agent referral protocol | `propose_referral` + lifecycle tools, formalised in CACP v0.1 §2 | Shipped |
| Audit-log entry schema (EU AI Act Article 12 conformant) | Documented in the compliance pack; tamper-evident HMAC chain + external anchoring (`company_discovery/audit_anchor.py`) | Shipped |

## Where each claim is verifiable

For a NLnet reviewer or institutional adopter doing a 10-minute deep-check of the standards claims:

- **Everything, one command per dimension**: the [claims ledger](docs/claims-ledger.md) maps each headline claim to the single command that verifies it (`python -m conformance.cacp`, `python -m escolib`, `python -m biasprobe`, `./scripts/verify_reproducibility.sh`, `./scripts/sign_release_local.sh`, …), gated by [`tests/test_claims_ledger.py`](tests/test_claims_ledger.py).
- **License + governance**: open [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`cla.md`](cla.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). All are at repo root.
- **MCP composition**: spawn `python3 mcp_server.py`, send the JSON-RPC `initialize` and `tools/list` calls documented in [`docs/mcp-server.md`](docs/mcp-server.md). Catalogue version + 15 tools + per-tool `inputSchema` come back.
- **Schema enforcement**: send a deliberately-malformed `tools/call` (e.g., omit a required field) and observe the RFC 7807 Problem Details payload with `violatedRule: "required"`. The test file [`tests/test_phase11_mcp_input_validation.py`](tests/test_phase11_mcp_input_validation.py) automates this.
- **AEAD encryption**: read [`company_discovery/crypto_kit.py`](company_discovery/crypto_kit.py) (142 lines) and [`tests/test_phase9_totp_aead_migration.py`](tests/test_phase9_totp_aead_migration.py) for the round-trip / tamper / AAD-mismatch / nonce-uniqueness assertions.
- **AI Act compliance**: open `compliance/`.
- **i18n parity**: run `python3 -m unittest tests.test_round5_i18n` — the parity check is part of the 925-test suite.
- **Full test suite**: `python3 -m unittest discover tests` runs in ~18 s on a bare host (verified 2026-05-18; the dated feature-verification report was removed in the 2026-05-23 docs cleanup).
