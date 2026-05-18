#!/usr/bin/env python3
# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Add SPDX-License-Identifier headers to Python source files.

One-shot script used during the Week 1 licensing pass of the NLnet grant
sprint. Run from the repository root:

    python3 scripts/add_spdx_headers.py

Idempotent: a file that already contains the SPDX marker is left alone.
Shebangs on line 1 are preserved (the header is inserted after the
shebang, before any other content).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

HEADER_LINES = [
    "# Copyright (c) 2026 DirectJob Scout contributors",
    "# SPDX-License-Identifier: Apache-2.0",
    "#",
    '# Licensed under the Apache License, Version 2.0 (the "License"); you may',
    "# not use this file except in compliance with the License. You may obtain",
    "# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.",
]

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

SPDX_MARKER = "SPDX-License-Identifier"


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        yield path


def already_has_header(text: str) -> bool:
    head = "\n".join(text.splitlines()[:15])
    return SPDX_MARKER in head


def build_header_block(existing_shebang: str | None) -> str:
    lines = list(HEADER_LINES)
    block = "\n".join(lines) + "\n"
    if existing_shebang is not None:
        return existing_shebang + "\n" + block
    return block


def insert_header(text: str) -> str:
    lines = text.splitlines(keepends=True)
    shebang = None
    body_start = 0
    if lines and lines[0].startswith("#!"):
        shebang = lines[0].rstrip("\n")
        body_start = 1
    body = "".join(lines[body_start:])
    header_block = build_header_block(shebang)
    if body and not body.startswith("\n"):
        return header_block + "\n" + body
    return header_block + body


def process_file(path: Path, dry_run: bool = False) -> bool:
    original = path.read_text(encoding="utf-8")
    if already_has_header(original):
        return False
    updated = insert_header(original)
    if dry_run:
        return True
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan (default: current directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    changed = 0
    scanned = 0
    for path in iter_python_files(root):
        scanned += 1
        if process_file(path, dry_run=args.dry_run):
            changed += 1
            verb = "would update" if args.dry_run else "updated"
            print(f"{verb}: {path.relative_to(root)}")

    summary = "scanned {scanned}, {changed} {action}.".format(
        scanned=scanned,
        changed=changed,
        action="would change" if args.dry_run else "changed",
    )
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
