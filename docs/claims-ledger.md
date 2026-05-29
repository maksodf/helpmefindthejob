<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Claims ledger

Every headline claim this project makes, mapped to the **one command a stranger
runs to verify it** — without trusting the maintainer and without reading the
source. The machine-readable source of truth is
[`claims-ledger.json`](https://github.com/maksodf/helpmefindthejob/blob/main/claims-ledger.json);
[`tests/test_claims_ledger.py`](https://github.com/maksodf/helpmefindthejob/blob/main/tests/test_claims_ledger.py)
is its build gate (every artefact, asserting test, and one-command must resolve;
the human-track items must stay un-built).

## Buildable + verifiable now

Each row is backed by a committed artefact and a test that exercises the shipped
path. Run the command from a clean checkout.

| Dimension | Claim | Verify with one command |
|---|---|---|
| Composition protocol (CACP v0.1) | The reference MCP server passes its own conformance suite, 14/14 (L1/L2/L3). | `python -m conformance.cacp` |
| `escolib` reusable library | Standalone ESCO/ISCO reconciliation; 100% recall, 0 false positives on committed fixtures. | `python -m escolib Krankenschwester` |
| `biasprobe` bias harness | Reproduces the comparative per-persona bias report offline from committed caches. | `python -m biasprobe` |
| Tamper-evident audit anchor | A record edit / deletion / non-v2 injection is detected offline against a committed fixture. | `python -m unittest tests.test_audit_anchor` |
| Reproducible build | Deterministic, HEAD-commit-bound source tarball (same SHA-256 on any machine). | `./scripts/verify_reproducibility.sh` |
| Release signing | Offline `cosign` sign→verify dry-run over the reproducible tarball. | `./scripts/sign_release_local.sh` |
| Multi-agent planner | Golden-trace replay; per-step trust receipts are HMAC-chained + anchorable. | `python -m unittest tests.test_civic_agents` |
| Compliance starter kit | Every AI Act / GDPR article cites an artefact that exists; build breaks if one disappears. | `python -m unittest tests.test_compliance_traceability` |
| Supply chain | CycloneDX SBOM + cosign public key + sigstore bundle ship as hard requirements. | `python -m unittest tests.test_release_supply_chain` |

## Human track — NOT buildable by code (operator-owned, dated Phase-2)

72 hours of coding can build the technical ceiling above; it **cannot** produce
the human dimensions below, which need other people and elapsed time. They are
never claimed as done — the ledger's gate fails if any is flipped to "built".

| Item | Status | Why code cannot produce it |
|---|---|---|
| Real users with measured outcomes | not built | The seven personas are **synthetic fixtures**. |
| External security audit | not built | Needs a paid third party; internal review ≠ external audit. |
| Co-maintainers / contributor community | not built | Code cannot manufacture a community. |
| Signed institutional partners (MOUs) | not built | Outreach drafted but unsent. |
| Third-party adoption of CACP | not built | Buildable proxy shipped: the in-repo reference agents pass conformance. |

This split — and the runnable one-commands above — is the project's integrity
spine: claims are verifiable, and the limits are stated honestly.
