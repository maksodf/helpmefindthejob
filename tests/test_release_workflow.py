# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for `.github/workflows/release.yml`.

PlanTowardPerfection boxes 2.14.8 (cosign signing automated in CI
on tag-push) + 2.14.9 (SLSA Level 2 build provenance). The
workflow itself runs only on tag-push (operator-gated cadence);
these tests verify its structural invariants so a future agent
that edits the workflow can't silently break (a) the trigger
contract, (b) the permission-minimisation discipline, (c) the
SHA-pin discipline, or (d) the cosign + SLSA attestation steps.
"""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

# PyYAML lives in requirements-dev.txt (not the runtime
# requirements.txt that the test.yml CI installs). When the dev
# deps aren't present the tests that need yaml skip cleanly
# rather than failing the entire module import. The same pattern
# is used by test_docs_site_quality.py for mkdocs.
_YAML_AVAILABLE = importlib.util.find_spec("yaml") is not None
if _YAML_AVAILABLE:
    import yaml  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"


def _skip_if_no_yaml(test_case: unittest.TestCase) -> None:
    if not _YAML_AVAILABLE:
        test_case.skipTest(
            "PyYAML not installed (test.yml installs requirements.txt "
            "only; PyYAML lives in requirements-dev.txt). YAML-parsing "
            "tests skip cleanly under that constraint."
        )


class ReleaseWorkflowExists(unittest.TestCase):
    def test_file_exists(self) -> None:
        self.assertTrue(
            WORKFLOW_PATH.is_file(),
            f"release workflow missing at {WORKFLOW_PATH}",
        )

    def test_file_is_valid_yaml(self) -> None:
        _skip_if_no_yaml(self)
        data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict, "workflow root must be a mapping")
        self.assertEqual(data.get("name"), "release")


@unittest.skipUnless(_YAML_AVAILABLE, "PyYAML not installed (requirements-dev.txt only)")
class ReleaseWorkflowTriggers(unittest.TestCase):
    def setUp(self) -> None:
        # PyYAML resolves the bare `on:` key as boolean True per
        # the YAML 1.1 spec. Recent PyYAML versions sometimes leave
        # it as the string "on" depending on loader; handle both.
        data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.on = data.get("on") or data.get(True) or data.get("on:")

    def test_triggers_on_v_prefixed_tag_push(self) -> None:
        # Triggers must include `push: tags: ['v*']` so the workflow
        # fires automatically when the maintainer pushes a release
        # tag — the box's automation contract.
        push = self.on.get("push", {})
        tags = push.get("tags", [])
        self.assertIn(
            "v*",
            tags,
            f"workflow must trigger on `push: tags: [v*]`; got {tags!r}",
        )

    def test_supports_manual_dispatch(self) -> None:
        # Manual dispatch is the operator's safety valve for
        # re-signing an existing tag.
        self.assertIn(
            "workflow_dispatch",
            self.on,
            "workflow must support workflow_dispatch for ad-hoc re-signing",
        )


@unittest.skipUnless(_YAML_AVAILABLE, "PyYAML not installed (requirements-dev.txt only)")
class ReleaseWorkflowPermissions(unittest.TestCase):
    def setUp(self) -> None:
        self.data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.jobs = self.data.get("jobs", {})

    def test_top_level_permissions_are_read_only(self) -> None:
        # Default to read-all; jobs that need more elevate explicitly.
        # This matches the OpenSSF Scorecard "permissions" check.
        self.assertEqual(
            self.data.get("permissions"),
            "read-all",
            "top-level permissions must be read-all; jobs elevate per-step",
        )

    def test_sign_and_publish_has_id_token_write(self) -> None:
        # Keyless cosign OIDC needs id-token: write. Without this,
        # the cosign sign-blob step would 401.
        sign_job = self.jobs.get("sign-and-publish", {})
        perms = sign_job.get("permissions", {})
        self.assertEqual(
            perms.get("id-token"),
            "write",
            "sign-and-publish job MUST have id-token: write for cosign OIDC",
        )

    def test_sign_and_publish_has_contents_write(self) -> None:
        # gh release create / upload needs contents: write.
        sign_job = self.jobs.get("sign-and-publish", {})
        perms = sign_job.get("permissions", {})
        self.assertEqual(
            perms.get("contents"),
            "write",
            "sign-and-publish job MUST have contents: write for gh release",
        )

    def test_build_and_sbom_jobs_are_contents_read_only(self) -> None:
        # The earlier jobs do NOT need write access; if they did,
        # any compromised dep in pip install could ride those
        # permissions to write to the repo.
        for job_name in ("build-source-tarball", "generate-sbom"):
            job = self.jobs.get(job_name, {})
            perms = job.get("permissions", {})
            self.assertEqual(
                perms,
                {"contents": "read"},
                f"{job_name} permissions must be exactly {{contents: read}}",
            )


class ReleaseWorkflowActionsArePinned(unittest.TestCase):
    """Every `uses:` reference must be a SHA-pinned action ref with
    a version-tag comment for human readability. This matches the
    OpenSSF Scorecard 'pinned-dependencies' check that the existing
    workflows already enforce."""

    PIN_RE = re.compile(r"uses:\s*([^@\s]+)@([0-9a-f]{40})\s*#\s*v[0-9]+\.[0-9]+(\.[0-9]+)?")

    def test_every_uses_is_sha_pinned(self) -> None:
        src = WORKFLOW_PATH.read_text(encoding="utf-8")
        uses_lines = [ln.strip() for ln in src.splitlines() if ln.strip().startswith("uses:")]
        self.assertGreater(
            len(uses_lines),
            0,
            "workflow has no `uses:` lines — either it stopped using "
            "actions, or the test no longer parses correctly",
        )
        for line in uses_lines:
            with self.subTest(line=line):
                self.assertRegex(
                    line,
                    self.PIN_RE,
                    f"uses line {line!r} is not SHA-pinned with a version "
                    "comment per the OpenSSF Scorecard discipline",
                )


class ReleaseWorkflowSecuritySigning(unittest.TestCase):
    """The cosign sign + SLSA-attest contract: both must be present
    in the sign-and-publish job + the verification step must run as
    a sanity check before the release goes live."""

    def setUp(self) -> None:
        self.src = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_cosign_sign_blob_present(self) -> None:
        self.assertIn(
            "cosign sign-blob",
            self.src,
            "release workflow must run `cosign sign-blob` to satisfy box 2.14.8",
        )

    def test_cosign_attest_blob_present(self) -> None:
        self.assertIn(
            "cosign attest-blob",
            self.src,
            "release workflow must run `cosign attest-blob` to satisfy box 2.14.9 (SLSA L2)",
        )

    def test_slsa_provenance_predicate_type(self) -> None:
        # The attestation must declare slsaprovenance as the type,
        # otherwise downstream tooling doesn't recognise it as SLSA.
        self.assertIn(
            "--type slsaprovenance",
            self.src,
            "cosign attest-blob must use --type slsaprovenance for SLSA L2 compliance",
        )

    def test_post_sign_verify_runs(self) -> None:
        # Sanity-check that the signature round-trips BEFORE the
        # release goes live. Without this we'd discover broken
        # cosign config only when a downstream verifier complains.
        self.assertIn(
            "cosign verify-blob",
            self.src,
            "release workflow must verify the signature before publishing",
        )

    def test_keyless_oidc_certificate_identity(self) -> None:
        # The verify step pins both the OIDC issuer + the
        # certificate-identity-regex so a malicious workflow in a
        # different repo can't produce a valid signature.
        self.assertIn(
            "--certificate-oidc-issuer 'https://token.actions.githubusercontent.com'",
            self.src,
            "verify step must pin the GitHub Actions OIDC issuer",
        )
        self.assertIn(
            "--certificate-identity-regexp",
            self.src,
            "verify step must pin a certificate-identity regex",
        )


class ReleaseWorkflowSecurityInjection(unittest.TestCase):
    """Defence against command-injection via untrusted GitHub
    payload fields. Every github.* field that could carry attacker-
    controlled bytes (actor, ref-name, event payload bodies) must
    flow through an `env:` block rather than direct $ {{ }}
    interpolation inside a `run:` script."""

    def setUp(self) -> None:
        self.src = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_no_direct_actor_interpolation_in_run(self) -> None:
        # Walk every line; if a `run:` block somewhere shell-
        # interpolates github.actor or other untrusted fields
        # directly via $ {{ ... }}, that's a known command-injection
        # vector. We require env: indirection.
        risky_patterns = (
            "${{ github.actor }}",
            "${{ github.event.head_commit.message }}",
            "${{ github.event.commits",
            "${{ github.event.pull_request.title }}",
            "${{ github.event.pull_request.body }}",
            "${{ github.event.issue.title }}",
            "${{ github.event.issue.body }}",
            "${{ github.head_ref }}",
        )
        # These are allowed in `env:` blocks; flag only if they
        # appear inside a `run:` script body. The simplest proxy:
        # ensure they appear ONLY as right-hand sides of env entries,
        # never as bare interpolations on `run:` lines.
        lines = self.src.splitlines()
        in_run_block = False
        run_block_indent = -1
        for i, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if stripped.startswith("run:"):
                in_run_block = True
                run_block_indent = indent
                continue
            if in_run_block and indent <= run_block_indent and stripped:
                in_run_block = False
            if not in_run_block:
                continue
            for pat in risky_patterns:
                if pat in line:
                    self.fail(
                        f"line {i} of release.yml uses risky direct "
                        f"interpolation {pat!r} inside a run: block; "
                        "wrap it in an env: block per the security comment"
                    )


if __name__ == "__main__":
    unittest.main()
