# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard: every path in static/sw.js SHELL_PATHS must point
at a real file under static/.

AUDIT-45 (2026-05-22): the service worker precaches a list of paths
during install (offline-shell hydration). If any precache path 404s,
the install fails silently — the SW activates but the offline shell
is incomplete. Users navigating offline get partial-broken UI.

The audit was a false-alarm on the live deploy (all paths return 200),
but the gap is: nothing prevents a developer from removing a static
file without updating sw.js. This test pins both directions:
- Every SHELL_PATHS entry exists on disk under static/
- Adding a new core static file without considering SW caching is a
  conscious tradeoff (not enforced — could grow noisy)
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "static"
SW_JS = STATIC / "sw.js"


class ServiceWorkerPrecachePathsResolve(unittest.TestCase):
    def test_every_shell_path_exists_on_disk(self) -> None:
        sw = SW_JS.read_text(encoding="utf-8")
        # Extract SHELL_PATHS array body
        match = re.search(r"const SHELL_PATHS\s*=\s*\[([^\]]+)\]", sw, re.DOTALL)
        self.assertIsNotNone(match, "SHELL_PATHS not found in sw.js")
        body = match.group(1)
        paths = re.findall(r'"([^"]+)"', body)
        self.assertGreater(len(paths), 0, "SHELL_PATHS is empty")

        missing = []
        for url_path in paths:
            # Skip the bare "/" — that resolves to index.html, not a
            # literal "/" file.
            if url_path == "/":
                if not (STATIC / "index.html").exists():
                    missing.append((url_path, "→ static/index.html"))
                continue
            # Strip the leading slash to map to a static file
            rel = url_path.lstrip("/")
            disk_path = STATIC / rel
            if not disk_path.exists():
                missing.append((url_path, str(disk_path)))

        if missing:
            details = "\n".join(f"  {url} → {disk} (does not exist)" for url, disk in missing)
            self.fail(
                "Service-worker SHELL_PATHS entries that 404 — the SW "
                "install will fail silently for these:\n" + details
            )


if __name__ == "__main__":
    unittest.main()
