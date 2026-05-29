# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 5b (trustworthiness) — reproducible source-dist build.

Determinism IS reproducibility: the source tarball builder reads only
git-tracked content + git-index modes and normalises every varying field, so
building twice — here or on a stranger's machine from the same commit — yields
byte-identical output. These tests pin that property so a future change that
leaks a timestamp, host path, or unstable ordering fails CI rather than
silently breaking the reproducibility claim.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
import unittest
from pathlib import Path

from scripts.build_reproducible_source_dist import (
    FIXED_MTIME,
    REPO_ROOT,
    build_source_tar,
    gzip_bytes,
    source_sha256,
    tracked_entries,
)

_IS_GIT_CHECKOUT = (REPO_ROOT / ".git").exists()


@unittest.skipUnless(_IS_GIT_CHECKOUT, "not a git checkout — builder needs the git index")
class SourceDistIsDeterministic(unittest.TestCase):
    def test_build_twice_is_byte_identical(self):
        first = build_source_tar(REPO_ROOT)
        second = build_source_tar(REPO_ROOT)
        self.assertEqual(first, second, "two builds differ — non-determinism in the builder")
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            hashlib.sha256(second).hexdigest(),
        )

    def test_source_sha256_helper_matches_manual_digest(self):
        self.assertEqual(
            source_sha256(REPO_ROOT),
            hashlib.sha256(build_source_tar(REPO_ROOT)).hexdigest(),
        )

    def test_gzip_wrapper_is_also_deterministic(self):
        tar = build_source_tar(REPO_ROOT)
        self.assertEqual(gzip_bytes(tar), gzip_bytes(tar))


@unittest.skipUnless(_IS_GIT_CHECKOUT, "not a git checkout — builder needs the git index")
class TarballCarriesNoBuildEnvironment(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.members = tarfile.open(
            fileobj=io.BytesIO(build_source_tar(REPO_ROOT)), mode="r"
        ).getmembers()

    def test_every_member_uses_the_fixed_epoch(self):
        mtimes = {m.mtime for m in self.members}
        self.assertEqual(mtimes, {FIXED_MTIME}, "a member leaked a build-time mtime")

    def test_no_owner_identity_leaks(self):
        for m in self.members:
            self.assertEqual((m.uid, m.gid), (0, 0), f"{m.name} leaked uid/gid")
            self.assertEqual((m.uname, m.gname), ("", ""), f"{m.name} leaked owner name")

    def test_members_are_sorted_by_path(self):
        names = [m.name for m in self.members]
        self.assertEqual(names, sorted(names), "tar member order is not stable")

    def test_tracked_source_is_present(self):
        names = {m.name for m in self.members}
        # representative tracked files across the packages built this sprint
        for expected in ("mcp_server.py", "biasprobe/__init__.py", "escolib/__init__.py"):
            self.assertIn(expected, names)


@unittest.skipUnless(_IS_GIT_CHECKOUT, "not a git checkout")
class TrackedEntriesContract(unittest.TestCase):
    def test_modes_are_git_canonical(self):
        for mode, _oid, _path in tracked_entries(REPO_ROOT):
            self.assertIn(mode, ("100644", "100755", "120000"))

    def test_verify_script_is_executable_in_head(self):
        modes = {path: mode for mode, _oid, path in tracked_entries(REPO_ROOT)}
        self.assertEqual(
            modes.get("scripts/verify_reproducibility.sh"),
            "100755",
            "verify_reproducibility.sh must be committed executable",
        )


@unittest.skipUnless(_IS_GIT_CHECKOUT, "not a git checkout")
class DigestIsBoundToCommitNotWorkingTree(unittest.TestCase):
    """Regression for the working-tree-vs-commit overclaim (review finding #1):
    the build reads HEAD blobs, so perturbing a tracked file's working-tree
    content must NOT change the digest. A dirty checkout that believes it is
    'on the same commit' still reproduces the commit's bytes."""

    def test_working_tree_edit_does_not_change_digest(self):
        target = REPO_ROOT / "README.md"
        if not target.is_file():
            self.skipTest("no README.md to perturb")
        original = target.read_bytes()
        baseline = source_sha256(REPO_ROOT)
        try:
            target.write_bytes(original + b"\n<!-- repro probe: working-tree perturbation -->\n")
            perturbed = source_sha256(REPO_ROOT)
        finally:
            target.write_bytes(original)
        self.assertEqual(
            baseline, perturbed, "digest changed with a dirty working tree — not commit-bound"
        )
        self.assertEqual(source_sha256(REPO_ROOT), baseline, "restore failed")


if __name__ == "__main__":
    unittest.main()
