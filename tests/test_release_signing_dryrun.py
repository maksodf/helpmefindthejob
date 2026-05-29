# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 5c (trustworthiness) — local cosign signing dry-run.

``scripts/sign_release_local.sh`` proves the release signing flow end-to-end
(build the reproducible tarball → ephemeral ECDSA key → cosign sign-blob →
cosign verify-blob) fully offline. The real release is signed by the operator
with the long-lived key per docs/releases/v0.80.0-signing.md; this dry-run lets
any contributor confirm the mechanics on their own machine without OIDC, a
transparency-log upload, or an operator tag-push.

The live-signing test skips where cosign is absent (it is operator/CI tooling,
not a runtime dependency); the script-shape test always runs.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = REPO_ROOT / "scripts" / "sign_release_local.sh"


class SigningDryRunScriptShape(unittest.TestCase):
    def test_script_present(self):
        self.assertTrue(_SCRIPT.is_file(), "scripts/sign_release_local.sh is missing")

    def test_script_is_tracked_executable(self):
        if not (REPO_ROOT / ".git").exists():
            self.skipTest("not a git checkout — cannot verify the index mode")
        out = subprocess.run(
            ["git", "ls-files", "-s", "scripts/sign_release_local.sh"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertTrue(
            out.startswith("100755"),
            f"sign_release_local.sh must be tracked executable, got: {out!r}",
        )


@unittest.skipUnless(
    shutil.which("cosign"),
    "cosign not installed — the signing dry-run is operator/CI tooling, not a runtime dep",
)
class SigningDryRunVerifiesOffline(unittest.TestCase):
    def test_sign_and_verify_flow(self):
        proc = subprocess.run(
            ["bash", str(_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, f"dry-run failed:\n{proc.stdout}\n{proc.stderr}")
        self.assertIn("SIGNING DRY-RUN OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
