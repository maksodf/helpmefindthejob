# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic source tarball for reproducible-build verification.

Builds a byte-identical tar of the source **as committed at HEAD** on every
machine: the file list, modes, AND content all come from the HEAD commit's git
objects (``git ls-tree`` + ``git cat-file``), never the working tree — so an
uncommitted or unstaged local edit cannot change the digest (the tarball is
bound to the commit, not to the checkout's dirty state). Every varying field is
normalised: sorted paths, a fixed mtime, uid/gid 0, empty owner names, GNU
format (so any path length is handled without atime/ctime pax headers). There is
no wall-clock read, no host path, and no environment input, so two builds — here
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


def tracked_entries(root: Path = REPO_ROOT) -> list[tuple[str, str, str]]:
    """``(mode, oid, path)`` for every blob in the HEAD commit, sorted by path.

    Reads the committed tree via ``git ls-tree -r -z HEAD`` (``-z`` so paths with
    spaces / odd bytes are NUL-delimited and unquoted), so the result is bound to
    the commit — identical on every clone and unaffected by working-tree edits or
    the staging area. Submodule (``commit``) entries are skipped.
    """
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    entries: list[tuple[str, str, str]] = []
    for record in proc.stdout.split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode, obj_type, oid = meta.split()
        if obj_type != "blob":  # skip submodule (commit) / tree entries
            continue
        entries.append((mode, oid, path))
    entries.sort(key=lambda e: e[2])
    return entries


def _read_blobs(root: Path, oids: list[str]) -> list[bytes]:
    """Blob content for each oid (in input order) via one ``git cat-file --batch``
    process. Reading committed objects — not the working tree — is what binds the
    tarball to the commit."""
    if not oids:
        return []
    proc = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=str(root),
        input=("\n".join(oids) + "\n").encode("ascii"),
        capture_output=True,
        check=True,
    )
    out = proc.stdout
    blobs: list[bytes] = []
    pos = 0
    for _oid in oids:
        newline = out.index(b"\n", pos)
        # header is "<oid> <type> <size>"
        size = int(out[pos:newline].split()[2])
        start = newline + 1
        blobs.append(out[start : start + size])
        pos = start + size + 1  # skip the blob content + its trailing newline
    return blobs


def build_source_tar(root: Path = REPO_ROOT) -> bytes:
    """Canonical, deterministic uncompressed tar of the HEAD commit's source."""
    entries = tracked_entries(root)
    blobs = _read_blobs(root, [oid for _mode, oid, _path in entries])
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for (mode, _oid, rel), data in zip(entries, blobs):
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mtime = FIXED_MTIME
            info.mode = 0o755 if mode == "100755" else 0o644
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
