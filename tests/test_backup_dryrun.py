# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Shell-level smoke for scripts/backup-production.sh dry-run paths.

Exercises the dry-run branches without touching docker or production
data. Skips when bash is not available.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "backup-production.sh"


def _run(env_extra: dict[str, str]) -> tuple[int, str, str]:
    env = {**os.environ, **env_extra, "HELPMEFINDTHEJOB_BACKUP_DRY_RUN": "1"}
    res = subprocess.run(
        ["sh", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return res.returncode, res.stdout, res.stderr


class BackupDryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not shutil.which("sh"):
            raise unittest.SkipTest("/bin/sh not available")
        if not SCRIPT.exists():
            raise unittest.SkipTest("backup script not present")

    def test_local_dryrun_succeeds(self) -> None:
        code, stdout, stderr = _run({"HELPMEFINDTHEJOB_BACKUP_BACKEND": "local"})
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", stdout)
        self.assertIn("would write tarball", stdout)

    def test_unknown_backend_exits_2(self) -> None:
        code, _, stderr = _run({"HELPMEFINDTHEJOB_BACKUP_BACKEND": "mystery"})
        self.assertEqual(code, 2)
        self.assertIn("unknown HELPMEFINDTHEJOB_BACKUP_BACKEND", stderr)

    def test_offhost_without_cli_or_remote_exits_2(self) -> None:
        # rclone is not installed in CI; this should bail with a helpful message
        code, _, stderr = _run({"HELPMEFINDTHEJOB_BACKUP_BACKEND": "rclone"})
        self.assertEqual(code, 2)
        self.assertTrue(
            "rclone not installed" in stderr or "HELPMEFINDTHEJOB_BACKUP_REMOTE missing" in stderr,
            stderr,
        )


if __name__ == "__main__":
    unittest.main()
