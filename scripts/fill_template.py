# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Fill a compliance template from a JSON config — the forkable starter-kit tool.

The compliance pack carries two kinds of fill markers:

* ``{{TOKEN}}`` — a named, machine-fillable slot. Substituted from the config.
* ``[TBD: deployer to fill — …]`` — a descriptive, judgement-requiring prompt.
  NEVER auto-filled (it needs a human deployer's deployment-specific answer); it
  is surfaced as a manual-fill TODO so a forker sees exactly what is left.

A deployer forks the pack, writes a small JSON config of their deployment values,
runs this tool to fill every ``{{TOKEN}}`` mechanically, then works the reported
``[TBD]`` list by hand. ``--strict`` makes an unfilled ``{{TOKEN}}`` a hard error
(for CI gates that must not ship a half-filled template).

    python -m scripts.fill_template TEMPLATE.md --config cfg.json --output OUT.md
    python -m scripts.fill_template TEMPLATE.md --config cfg.json --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: A machine-fillable placeholder: ANY ``{{...}}`` (spaces, hyphens, even a line
#: wrap inside the braces), so no real slot is ever silently skipped. The body
#: is normalised to a config key by ``_normalise_key``.
TOKEN_RE = re.compile(r"\{\{([^{}]+?)\}\}", re.DOTALL)
#: A descriptive human-fill prompt, e.g. [TBD: deployer to fill — organisation name].
TBD_RE = re.compile(r"\[TBD:[^\]]*\]")


def _normalise_key(raw: str) -> str:
    """Canonical config key for a slot body: collapse runs of whitespace,
    hyphens, and slashes to single underscores, strip, uppercase. So
    ``{{DEPLOYER\\nNAME}}``, ``{{DEPLOYER NAME}}`` and ``{{deployer-name}}`` all
    map to ``DEPLOYER_NAME`` — a line-wrapped or oddly-cased placeholder is still
    seen, and ``--strict`` cannot be fooled into passing over it."""
    return re.sub(r"[\s\-/]+", "_", raw.strip()).upper()


def fill(template_text: str, config: dict[str, object]) -> tuple[str, list[str], list[str]]:
    """Return ``(filled_text, unfilled_keys, tbd_prompts)``.

    EVERY ``{{...}}`` placeholder is detected (whatever its spacing/case); its
    body is normalised to a config key and substituted when present.
    ``unfilled_keys`` lists the distinct normalised keys still unsubstituted
    (sorted) — so ``--strict`` cannot pass over a placeholder it failed to fill.
    ``tbd_prompts`` lists the verbatim ``[TBD: …]`` human-fill markers.
    """

    def _sub(match: re.Match[str]) -> str:
        key = _normalise_key(match.group(1))
        return str(config[key]) if key in config else match.group(0)

    filled = TOKEN_RE.sub(_sub, template_text)
    unfilled = sorted({_normalise_key(body) for body in TOKEN_RE.findall(filled)})
    tbd = TBD_RE.findall(filled)
    return filled, unfilled, tbd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fill_template", description=__doc__)
    parser.add_argument("template", type=Path, help="the template .md to fill")
    parser.add_argument("--config", type=Path, required=True, help="JSON config of TOKEN→value")
    parser.add_argument("--output", type=Path, default=None, help="write the filled doc here")
    parser.add_argument(
        "--strict", action="store_true", help="exit non-zero if any {{TOKEN}} is left unfilled"
    )
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        print("ERROR: config must be a JSON object of TOKEN→value", file=sys.stderr)
        return 2

    filled, unfilled, tbd = fill(args.template.read_text(encoding="utf-8"), config)

    if args.output:
        args.output.write_text(filled, encoding="utf-8")
        print(f"wrote {args.output}")

    print(f"unfilled {{TOKEN}} slots: {unfilled or 'none'}")
    print(f"manual [TBD] prompts a deployer must still answer: {len(tbd)}")
    for prompt in tbd[:50]:
        print(f"  TODO {prompt}")

    if args.strict and unfilled:
        print(f"ERROR (--strict): unfilled placeholders remain: {unfilled}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
