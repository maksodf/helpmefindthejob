"""Operator-package regression tests."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OperatorPackageTests(unittest.TestCase):
    def test_production_env_template_is_sourceable_by_readiness_check(self) -> None:
        env = os.environ.copy()
        env["ENV_FILE"] = "deploy/production.env.template"
        result = subprocess.run(
            ["./scripts/production-readiness-check.sh"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn('"overallStatus": "missing"', result.stdout)
        self.assertNotIn("syntax error", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
