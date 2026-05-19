# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 DirectJob Scout contributors

"""mkdocs build hook — mirror user-facing compliance/*.md into docs/.

The two user-facing compliance artefacts (transparency-notice +
deployer-operating-manual) live canonically at the repo root under
``compliance/`` so they're discoverable from GitHub UI. The mkdocs
site wants them as native pages so the §3.6 WCAG 2.2 AA audit can
exercise them. This hook copies them into ``docs/compliance/`` at
the ``on_pre_build`` event so the rendered site has up-to-date
content without any file-system symlinks (which behave inconsistently
across platforms).

The mirror directory is in ``.gitignore`` — the canonical source of
truth remains ``compliance/`` at the repo root.

Mirror list expands as more compliance/*.md files become user-facing.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Source path (relative to repo root) → destination path inside docs/.
#
# Only the two user-facing files (transparency-notice + deployer-
# operating-manual) are mirrored. Their sibling cross-tree links
# (../SECURITY.md, ../docs/grant/*, human-oversight-guide.md, etc.)
# are rewritten to absolute GitHub URLs in the source so they
# resolve in both the GitHub UI and the mkdocs build without
# polluting docs/ with the full compliance/ tree.
MIRROR: dict[str, str] = {
    "compliance/transparency-notice.md": "compliance/transparency-notice.md",
    "compliance/deployer-operating-manual.md": "compliance/deployer-operating-manual.md",
}


def on_pre_build(config, **kwargs):
    """Copy the mirror list into ``docs/<dest>`` before mkdocs scans
    the docs tree. Idempotent; overwrites stale mirrors."""
    docs_dir = Path(config["docs_dir"])
    repo_root = docs_dir.parent
    for src_rel, dest_rel in MIRROR.items():
        src = repo_root / src_rel
        dest = docs_dir / dest_rel
        if not src.exists():
            # Surface the missing file via a clear print rather than
            # silently mirroring nothing; mkdocs --strict will still
            # surface a broken nav reference downstream if the dest
            # doesn't exist.
            print(f"compliance_mirror: source missing — {src}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
