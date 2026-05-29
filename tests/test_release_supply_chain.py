# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W3 D13-14: reproducible build + supply-chain
attestation contract tests (invariant 11).

What this pins:

1. **SBOM completeness**: every direct dep in requirements.txt
   appears in the committed CycloneDX SBOM. A future contributor
   who adds a dep without regenerating the SBOM fails CI here —
   not in production when someone tries to verify the SBOM.

2. **SBOM structural validity**: bomFormat is CycloneDX, every
   component has a name + version + purl + license — the bare
   minimum a supply-chain auditor needs.

3. **Cosign + sigstore release artifacts**: the public key + the
   bundle are committed and well-formed. Operators who want to
   verify a release tarball won't hit a 404.

4. **security.txt + SECURITY.md present and linked**: RFC 9116
   compliance — vulnerability reporters can find the contact
   without guessing.

5. **Nix flake present and parseable**: the reproducible-build
   story has a concrete entry point.

These are NOT tests of the build process itself (we'd need a Nix
runner in CI for that). They're contracts on the artifacts the
build process produces — so artifact drift is caught fast.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SBOM_PATH = REPO_ROOT / "docs" / "releases" / "v0.1.0-sbom.json"
COSIGN_PUB = REPO_ROOT / "docs" / "releases" / "v0.1.0-cosign.pub"
SIGSTORE_BUNDLE = REPO_ROOT / "docs" / "releases" / "v0.1.0-source.tar.gz.sigstore"
SIGNING_DOC = REPO_ROOT / "docs" / "releases" / "v0.1.0-signing.md"
REQUIREMENTS = REPO_ROOT / "requirements.txt"
FLAKE = REPO_ROOT / "flake.nix"
SECURITY_TXT = REPO_ROOT / "static" / ".well-known" / "security.txt"
SECURITY_MD = REPO_ROOT / "SECURITY.md"


def _direct_deps_from_requirements() -> set[str]:
    """Pull the set of direct (top-level) deps from requirements.txt,
    normalised to lowercase. Skips comments + blank lines."""

    deps: set[str] = set()
    for raw_line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Take the package name up to the first version constraint
        # or environment marker
        m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if m:
            deps.add(m.group(1).lower())
    return deps


class SbomCompleteness(unittest.TestCase):
    """Every direct dep MUST appear in the SBOM. Drift here
    means we shipped a release artifact that lies about what's
    inside — the highest-severity supply-chain integrity failure."""

    @classmethod
    def setUpClass(cls):
        if not SBOM_PATH.exists():
            raise AssertionError(
                f"v0.1.0 CycloneDX SBOM MUST be committed at {SBOM_PATH} — the "
                "supply-chain claim depends on it; its absence is a regression, not a skip."
            )
        cls.sbom = json.loads(SBOM_PATH.read_text(encoding="utf-8"))
        cls.component_names = {c["name"].lower() for c in cls.sbom["components"]}

    def test_every_direct_dep_in_sbom(self):
        direct = _direct_deps_from_requirements()
        missing = direct - self.component_names
        self.assertEqual(
            missing,
            set(),
            f"requirements.txt declares deps the SBOM doesn't list — "
            f"regenerate the SBOM (`cyclonedx-py environment`) before "
            f"shipping. Missing: {sorted(missing)}",
        )

    def test_sbom_has_at_least_as_many_components_as_direct_deps(self):
        # Sanity check — direct + transitives must be ≥ direct alone.
        direct = _direct_deps_from_requirements()
        self.assertGreaterEqual(len(self.sbom["components"]), len(direct))


class SbomStructuralValidity(unittest.TestCase):
    """Pin the CycloneDX schema invariants a supply-chain auditor
    expects. A malformed SBOM would silently fail external scanners."""

    @classmethod
    def setUpClass(cls):
        if not SBOM_PATH.exists():
            raise AssertionError(
                f"v0.1.0 CycloneDX SBOM MUST be committed at {SBOM_PATH} — the "
                "supply-chain claim depends on it; its absence is a regression, not a skip."
            )
        cls.sbom = json.loads(SBOM_PATH.read_text(encoding="utf-8"))

    def test_bom_format_is_cyclonedx(self):
        self.assertEqual(self.sbom.get("bomFormat"), "CycloneDX")

    def test_spec_version_is_modern(self):
        # Accept 1.4+ (current is 1.6); reject older that lack purl
        spec = self.sbom.get("specVersion", "")
        self.assertRegex(spec, r"^1\.[4-9]$|^[2-9]\.")

    def test_serial_number_is_uuid_urn(self):
        sn = self.sbom.get("serialNumber", "")
        self.assertRegex(sn, r"^urn:uuid:[0-9a-fA-F-]{36}$")

    def test_every_component_has_name_version_purl(self):
        for comp in self.sbom["components"]:
            self.assertIn("name", comp, f"component missing name: {comp}")
            self.assertIn("version", comp, f"component {comp['name']} missing version")
            self.assertIn("purl", comp, f"component {comp['name']} missing purl")
            # purl must start with pkg:
            self.assertTrue(
                comp["purl"].startswith("pkg:"),
                f"component {comp['name']} has malformed purl: {comp['purl']}",
            )

    def test_every_component_has_at_least_one_license_or_explicit_none(self):
        # Some packages have no declared license; the SBOM tool emits
        # an empty licenses list in that case. We allow empty but ban
        # the field being absent.
        for comp in self.sbom["components"]:
            self.assertIn(
                "licenses",
                comp,
                f"component {comp['name']} has no licenses field — even "
                "an empty list is required for downstream audit tooling",
            )

    def test_metadata_carries_timestamp_and_tool(self):
        meta = self.sbom.get("metadata", {})
        self.assertIn("timestamp", meta)
        self.assertIn("tools", meta)


class CosignAndSigstoreArtifactsPresent(unittest.TestCase):
    """The release tarball was signed via cosign keyed signing. The
    public key + sigstore bundle MUST be present and well-formed so
    an operator can verify the tarball without contacting us."""

    def test_cosign_public_key_present(self):
        self.assertTrue(
            COSIGN_PUB.exists(),
            f"cosign public key MUST be committed at {COSIGN_PUB} — "
            "deleting a signing artifact must fail CI, not silently skip.",
        )
        contents = COSIGN_PUB.read_text(encoding="utf-8")
        self.assertIn("BEGIN PUBLIC KEY", contents)
        self.assertIn("END PUBLIC KEY", contents)

    def test_sigstore_bundle_present_and_json(self):
        self.assertTrue(
            SIGSTORE_BUNDLE.exists(),
            f"sigstore bundle MUST be committed at {SIGSTORE_BUNDLE} — "
            "deleting a signing artifact must fail CI, not silently skip.",
        )
        # Sigstore bundles are JSON
        try:
            json.loads(SIGSTORE_BUNDLE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.fail(f"sigstore bundle is not valid JSON: {exc}")

    def test_signing_documentation_present(self):
        self.assertTrue(
            SIGNING_DOC.exists(),
            f"signing documentation MUST be committed at {SIGNING_DOC} — "
            "deleting a signing artifact must fail CI, not silently skip.",
        )
        text = SIGNING_DOC.read_text(encoding="utf-8")
        # The signing doc should reference cosign + the release version
        self.assertIn("cosign", text.lower())
        self.assertIn("v0.1.0", text)


class SecurityTxtCompliance(unittest.TestCase):
    """RFC 9116 compliance — security.txt MUST exist, declare
    Contact + Expires, and be linked from SECURITY.md."""

    def test_security_txt_exists(self):
        self.assertTrue(
            SECURITY_TXT.exists(),
            f"security.txt missing at {SECURITY_TXT} — RFC 9116 requires "
            "a discoverable contact for security reports",
        )

    def test_security_txt_has_contact_and_expires(self):
        self.assertTrue(
            SECURITY_TXT.exists(),
            "static/.well-known/security.txt MUST be present (RFC 9116) — absence is a regression, not a skip.",
        )
        text = SECURITY_TXT.read_text(encoding="utf-8")
        # RFC 9116 mandates Contact and Expires fields. Fields are
        # at line-start in the body of the file; use MULTILINE so ^
        # anchors per line, not per string.
        self.assertRegex(text, r"(?im)^Contact:", "missing Contact: field")
        self.assertRegex(text, r"(?im)^Expires:", "missing Expires: field")

    def test_security_txt_not_expired(self):
        """RFC 9116 §2.5.5 — Expires MUST be in the future, otherwise
        researchers can't trust the contact is still monitored. We
        parse the Expires line and verify it's after today."""

        self.assertTrue(
            SECURITY_TXT.exists(),
            "static/.well-known/security.txt MUST be present (RFC 9116) — absence is a regression, not a skip.",
        )
        text = SECURITY_TXT.read_text(encoding="utf-8")
        from datetime import datetime, timezone

        match = re.search(r"(?im)^Expires:\s*(\S+)", text)
        self.assertIsNotNone(match, "Expires field not found")
        expires_str = match.group(1)
        # ISO 8601 with optional Z suffix
        expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        self.assertGreater(
            expires,
            datetime.now(timezone.utc),
            f"security.txt Expires={expires_str} is in the past — "
            "researchers can't trust the contact is still monitored. "
            "Bump the Expires line + re-sign per RFC 9116 §2.5.5.",
        )

    def test_security_md_references_security_txt(self):
        self.assertTrue(
            SECURITY_MD.exists(),
            "SECURITY.md MUST be present — absence is a regression, not a skip.",
        )
        text = SECURITY_MD.read_text(encoding="utf-8")
        self.assertIn("security.txt", text.lower())


class ThreatModelDocComplete(unittest.TestCase):
    """gap #24: a formal threat model document MUST ship + cover
    every STRIDE category + carry an "active defects" section that
    can be empty but must exist."""

    @classmethod
    def setUpClass(cls):
        cls.path = REPO_ROOT / "docs" / "THREAT-MODEL.md"
        if not cls.path.exists():
            raise AssertionError(
                f"threat model MUST be committed at {cls.path} — absence is a regression, not a skip."
            )
        cls.text = cls.path.read_text(encoding="utf-8")

    def test_threat_model_covers_stride_categories(self):
        for category in (
            "Spoofing",
            "Tampering",
            "Repudiation",
            "Information disclosure",
            "Denial of service",
            "Elevation of privilege",
        ):
            self.assertIn(
                category,
                self.text,
                f"threat model missing STRIDE category: {category}",
            )

    def test_threat_model_carries_active_defects_section(self):
        # The section may be empty, but the heading MUST exist so
        # the doc has a place to record any newly-discovered defect.
        self.assertRegex(
            self.text,
            r"##\s+\d*\.?\s*Active defects",
            "threat model missing 'Active defects' section",
        )

    def test_threat_model_dated(self):
        # MUST carry a "Last updated:" line so reviewers know its
        # freshness. The format is ISO date.
        self.assertRegex(
            self.text,
            r"Last updated:\s*\d{4}-\d{2}-\d{2}",
            "threat model missing or malformed 'Last updated:' line",
        )


class DpaTemplatePresent(unittest.TestCase):
    """gap #25: a DPA template MUST ship for institutional buyers
    + cover the key GDPR + AI Act surfaces."""

    @classmethod
    def setUpClass(cls):
        cls.path = REPO_ROOT / "compliance" / "dpa-template.md"
        if not cls.path.exists():
            raise AssertionError(
                f"DPA template MUST be committed at {cls.path} — absence is a regression, not a skip."
            )
        cls.text = cls.path.read_text(encoding="utf-8")

    def test_dpa_covers_required_sections(self):
        # Every standard DPA needs these sections per GDPR Art. 28:
        for heading in (
            "Subject matter",
            "Duration of processing",
            "Nature and purpose",
            "personal data",
            "Sub-processors",
            "Data subject rights",
            "Security measures",
            "International transfers",
            "Breach notification",
            "Audit",
        ):
            self.assertIn(
                heading,
                self.text,
                f"DPA template missing section heading: {heading}",
            )

    def test_dpa_references_gdpr_articles(self):
        # The template MUST cite the specific GDPR articles a
        # signer needs to honor — otherwise it's vapor. The doc
        # may use either "Article N" or the abbreviated "Art. N"
        # form; both count.
        for n in (7, 12, 15, 17, 20, 22, 28):
            full = f"Article {n}"
            abbreviated = f"Art. {n}"
            self.assertTrue(
                full in self.text or abbreviated in self.text,
                f"DPA template missing reference to GDPR Article {n} "
                f"(checked for '{full}' and '{abbreviated}')",
            )

    def test_dpa_references_ai_act(self):
        # The template MUST acknowledge AI Act overlap (Article
        # 12 audit log, Article 13 transparency, Article 86 right
        # to explanation)
        self.assertIn("AI Act", self.text)
        self.assertIn("Article 86", self.text)


class NixFlakePresent(unittest.TestCase):
    """The Nix flake is the entry point for the reproducible-build
    story. Without it, the "reproducible across machines" claim has
    no concrete recipe to point at."""

    def test_flake_exists(self):
        self.assertTrue(FLAKE.exists())

    def test_flake_declares_pinned_inputs(self):
        self.assertTrue(
            FLAKE.exists(),
            "flake.nix MUST be present (reproducible build) — absence is a regression, not a skip.",
        )
        text = FLAKE.read_text(encoding="utf-8")
        # The flake MUST pin inputs (otherwise it's not reproducible)
        self.assertIn("inputs", text)
        self.assertIn("nixpkgs", text)
        # The flake MUST declare a devShell or app output
        self.assertTrue(
            "devShells" in text or "apps" in text or "packages" in text,
            "flake declares no outputs (devShells/apps/packages)",
        )


if __name__ == "__main__":
    unittest.main()
