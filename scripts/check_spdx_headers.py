#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Verify SPDX-License-Identifier headers on Python files.

Used as a pre-commit hook (see .pre-commit-config.yaml). Exits non-zero if
any inspected file is missing the SPDX line within the first 15 lines.

Files to check can be passed as positional arguments (pre-commit passes the
staged file list this way); if none are passed, the script scans the
whole tree under --root.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

SPDX_MARKER = "SPDX-License-Identifier"

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    ".dev-data",
    ".obsidian",
    ".claude",
    "node_modules",
    "backups",
    "data",
    "private",
}


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        yield path


def has_spdx(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    head = "\n".join(text.splitlines()[:15])
    return SPDX_MARKER in head


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files to check. If empty, scan the whole tree under --root.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root for full-tree mode (default: current directory).",
    )
    args = parser.parse_args()

    if args.paths:
        candidates = [Path(p) for p in args.paths if p.endswith(".py")]
    else:
        root = Path(args.root).resolve()
        candidates = list(iter_python_files(root))

    missing: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if not has_spdx(path):
            missing.append(path)

    if missing:
        print(
            "ERROR: SPDX-License-Identifier header missing in:",
            file=sys.stderr,
        )
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        print(
            "Fix: prepend the header from .license-header-template.txt, or "
            "run python3 scripts/add_spdx_headers.py to add it automatically.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
