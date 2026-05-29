# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""``python -m biasprobe`` — replay the committed caches into a comparative
bias report, offline. No API keys, no network, no host-application import.

    python -m biasprobe                       # report from the bundled caches
    python -m biasprobe --cache-dir DIR        # replay a different cache dir
    python -m biasprobe --providers deepseek   # restrict to some providers
    python -m biasprobe --output report.md     # write instead of printing

Live runs (which call providers and rebuild the cache) are the job of the host
project's runner — for Helpmefindthejob, ``scripts/bias_comparative_report.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from biasprobe import (
    DEFAULT_CACHE_DIR,
    discover_providers,
    load_outcomes,
    render_markdown,
    summarize,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="biasprobe", description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Directory of <provider>.jsonl caches to replay (default: bundled).",
    )
    parser.add_argument(
        "--providers",
        default=None,
        help="Comma-separated provider ids (default: every cache found in --cache-dir).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the Markdown report to this path (default: print to stdout).",
    )
    args = parser.parse_args(argv)

    cache_dir: Path = args.cache_dir
    if args.providers:
        providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    else:
        providers = discover_providers(cache_dir)

    if not providers:
        parser.error(
            f"no caches found in {cache_dir} — pass --cache-dir at a directory of "
            "<provider>.jsonl files, or generate one with the host project's live runner."
        )

    by_provider = {}
    summaries = []
    for provider_id in providers:
        outcomes = list(load_outcomes(cache_dir, provider_id).values())
        by_provider[provider_id] = outcomes
        summaries.append(summarize(provider_id, outcomes))

    md = render_markdown(
        by_provider, summaries, generated_by="biasprobe (`python -m biasprobe`)"
    )
    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(md, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
