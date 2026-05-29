# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic source tarball for reproducible-build verification.

Builds a byte-identical tar of the git-tracked source on every machine: the
file list + modes come from the git index (identical on every clone), the
content from the tracked files, and every varying field is normalised —
sorted paths, a fixed mtime, uid/gid 0, empty owner names, GNU format (so any
path length is handled without atime/ctime pax headers). There is no
wall-clock read, no host path, and no environment input, so two builds — here
or on a stranger's machine from the same commit — produce the same SHA-256.

The reproducibility digest is taken over the **uncompressed** tar: gzip headers
carry platform-variable bytes (OS field) that say nothing about the payload, so
hashing the tar payload is the robust, cross-platform commitment. ``--output``
still writes a ``.tar.gz`` (gzip mtime 0) for distribution.

    python -m scripts.build_reproducible_source_dist            # print digest + file count
    python -m scripts.build_reproducible_source_dist --print-sha
    python -m scripts.build_reproducible_source_dist --output dist/src.tar.gz
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import subprocess
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# A fixed epoch stamped on every entry — the artifact must carry no wall-clock.
FIXED_MTIME = 1735689600  # 2025-01-01T00:00:00Z


def tracked_entries(root: Path = REPO_ROOT) -> list[tuple[str, str]]:
    """``(git_mode, path)`` for every tracked file, sorted by path. Mode + set
    of paths come from the git index, so the result is identical on every clone
    regardless of working-tree mtimes or local file ordering."""
    proc = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    entries: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        meta, path = line.split("\t", 1)
        entries.append((meta.split()[0], path))  # meta = "<mode> <oid> <stage>"
    entries.sort(key=lambda e: e[1])
    return entries


def build_source_tar(root: Path = REPO_ROOT) -> bytes:
    """Canonical, deterministic uncompressed tar of the tracked source."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for git_mode, rel in tracked_entries(root):
            path = root / rel
            if not path.is_file():
                continue  # skip gitlinks / submodule entries
            data = path.read_bytes()
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mtime = FIXED_MTIME
            info.mode = 0o755 if git_mode == "100755" else 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def source_sha256(root: Path = REPO_ROOT) -> str:
    """SHA-256 of the canonical uncompressed tar — the reproducibility digest."""
    return hashlib.sha256(build_source_tar(root)).hexdigest()


def gzip_bytes(tar_bytes: bytes) -> bytes:
    """Gzip with mtime 0 (no embedded timestamp) for distribution."""
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as handle:
        handle.write(tar_bytes)
    return out.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=None, help="write the gzipped tarball to this path"
    )
    parser.add_argument(
        "--print-sha", action="store_true", help="print only the sha256 (for scripting)"
    )
    args = parser.parse_args(argv)

    tar_bytes = build_source_tar()
    digest = hashlib.sha256(tar_bytes).hexdigest()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(gzip_bytes(tar_bytes))

    if args.print_sha:
        print(digest)
    else:
        print(f"source-tar sha256: {digest}")
        print(f"tracked files:     {len(tracked_entries())}")
        if args.output:
            print(f"wrote:             {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
