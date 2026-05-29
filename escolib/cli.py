# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for escolib: reconcile free text to ESCO/ISCO codes."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from escolib.reconcile import EscoReconciler


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="escolib",
        description="Reconcile free text to ESCO/ISCO occupation + skill concepts.",
    )
    parser.add_argument("query", help="free-text term to reconcile, e.g. 'Krankenschwester'")
    parser.add_argument(
        "--type",
        dest="kind",
        choices=["occupation", "skill", "any"],
        default=None,
        help="restrict to occupations or skills (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="maximum number of matches to return",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="path to a directory of {occupations,skills}.json (default: packaged data)",
    )
    args = parser.parse_args(argv)

    reconciler = EscoReconciler(base=args.data)
    result = reconciler.query(args.query, kind=args.kind, limit=args.limit)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0
