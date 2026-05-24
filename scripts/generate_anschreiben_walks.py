# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""PART 5 inspection-grade Anschreiben evidence generator.

Runs after the bias-methodology re-run completes (same Ollama
session). Generates one Anschreiben per persona against their
canonical strong-fit scenario, writes each to
``docs/grant/anschreiben-quality-walks-2026-05-20/<persona>.md``
with persona metadata + scenario metadata + full Anschreiben +
automated gate-check.

Gate 4.3 + 4.7 require inspection-grade evidence the bias-test does
not produce (the bias-test exercises fit-scoring + CV-tailoring; it
does not exercise the motivation-letter / Anschreiben prompts).

Usage:
    python3 scripts/generate_anschreiben_walks.py

Estimated runtime: ~120 s for 7 personas (×17 s per Ollama call).
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from company_discovery.ai_providers import AIProviderConfig  # noqa: E402
from company_discovery.analysis import _dispatch_provider  # noqa: E402
from company_discovery.motivation_letter import draft_with_ai  # noqa: E402
from company_discovery.persona_fixtures import PERSONAS  # noqa: E402

FORBIDDEN_FILLER = (
    "Hiermit bewerbe ich mich",
    "I am writing to express my interest",
    "I would like to apply for the position",
    "In conclusion",
    "Overall, this is",
    "It is important to note that",
    "Here are some key points",
    "I would recommend",
)


def _make_ai_caller(provider: AIProviderConfig):
    def caller(system: str, user: str) -> str | None:
        # The motivation-letter helper passes a (system, user) tuple
        # but _dispatch_provider takes a single prompt string. Concatenate
        # with explicit role markers so the model treats them distinctly.
        full = f"<<<SYSTEM>>>\n{system}\n\n<<<USER>>>\n{user}"
        result = _dispatch_provider(full, provider, runtime_credential="", purpose="cover_letter")
        return result.output

    return caller


def _context_tokens_from_jd(jd: str, limit: int = 8) -> list[str]:
    """Extract simple noun-ish tokens from the JD for 4.7 fact-grounding
    inspection. Heuristic only — picks capitalised words + a few
    domain-specific markers. Not a substitute for human inspection."""

    tokens: list[str] = []
    seen: set[str] = set()
    # Capitalised words longer than 3 chars (excludes line-start common words)
    for m in re.finditer(r"\b[A-ZÄÖÜ][\wäöüß-]{3,}\b", jd or ""):
        t = m.group(0)
        if t.lower() in {"sehr", "geehrte", "damen", "herren", "this", "that"}:
            continue
        if t not in seen:
            seen.add(t)
            tokens.append(t)
        if len(tokens) >= limit:
            break
    return tokens


def _generate_walk(persona, scenario, ai_caller) -> dict:
    """Generate one persona's Anschreiben + return walk metadata."""

    company_name = f"Beispielarbeitgeber ({scenario.job_location})"
    t0 = time.monotonic()
    letter = draft_with_ai(
        job={
            "title": scenario.job_title,
            "company": company_name,
            "location": scenario.job_location,
            "url": "https://demo.helpmefindthejob.org/walk",
            "description": scenario.job_description,
        },
        cv_text=persona.cv_summary,
        user_name=persona.display_name,
        user_location=persona.location,
        ai_caller=ai_caller,
        residency_status=persona.residency_status,
        friction_notes=persona.friction_notes,
    )
    elapsed = time.monotonic() - t0
    letter_text = letter or ""
    letter_lower = letter_text.lower()

    # Gate 4.2: forbidden filler
    filler_hits = [p for p in FORBIDDEN_FILLER if p.lower() in letter_lower]

    # Gate 4.3: no markdown bullets in body. Heuristic: lines starting
    # with bullet markers (-, *, •) anywhere in the letter.
    body_bullets = re.findall(r"(?m)^\s*[-*•]\s", letter_text)

    # Gate 4.7: role token + at least one JD-context token
    role_tokens = list(persona.target_roles[:3])
    role_hits = [t for t in role_tokens if t.lower() in letter_lower]
    jd_context_tokens = _context_tokens_from_jd(scenario.job_description)
    context_hits = [t for t in jd_context_tokens if t.lower() in letter_lower]

    return {
        "persona": persona,
        "scenario": scenario,
        "company_name": company_name,
        "letter": letter_text,
        "elapsed_s": elapsed,
        "filler_hits": filler_hits,
        "body_bullets": body_bullets,
        "role_tokens": role_tokens,
        "role_hits": role_hits,
        "jd_context_tokens": jd_context_tokens,
        "context_hits": context_hits,
    }


def _write_walk_md(out_dir: Path, walk: dict) -> Path:
    persona = walk["persona"]
    scenario = walk["scenario"]
    letter = walk["letter"]
    filler_hits = walk["filler_hits"]
    body_bullets = walk["body_bullets"]
    role_hits = walk["role_hits"]
    context_hits = walk["context_hits"]

    md = f"""<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — {persona.display_name}

**Persona slug**: `{persona.slug}`  |  **Cohort**: `{persona.cohort}`  |  **Location**: {persona.location}
**Residency status**: {persona.residency_status}
**Friction notes**: {persona.friction_notes}

## Fixture JD

**Scenario label**: `{scenario.label}`
**Job title**: {scenario.job_title}
**Job location**: {scenario.job_location}
**Company**: {walk["company_name"]} (synthetic for this walk)

**Job description**:

> {scenario.job_description}

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: {walk["elapsed_s"]:.1f} s
- Output length: {len(letter)} chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
{letter}
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | {len(filler_hits)} {"PASS" if not filler_hits else "FAIL — " + repr(filler_hits)} |
| 4.3 | Markdown-bullet lines in body | {len(body_bullets)} {"PASS" if not body_bullets else "FAIL"} |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | {role_hits if role_hits else "MISSING — FAIL"} |
| 4.7 (context) | JD-derived context tokens found (heuristic) | {context_hits[:4] if context_hits else "NONE"} ({len(context_hits)} / {len(walk["jd_context_tokens"])} candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. {"PASS" if (role_hits and context_hits) else "FAIL"}

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
"""
    out_path = out_dir / f"{persona.slug}.md"
    out_path.write_text(md, encoding="utf-8")
    return out_path


def main() -> int:
    out_dir = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "grant"
        / "anschreiben-quality-walks-2026-05-20"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    provider = AIProviderConfig(
        provider_id="ollama",
        invocation_mode="local_http",
        model="llama3.1:8b",
        credential_reference="",
        base_url="http://127.0.0.1:11434",
        command="",
        notes="anschreiben-quality-walks",
    )
    ai_caller = _make_ai_caller(provider)

    walks = []
    overall_t0 = time.monotonic()
    for persona in PERSONAS:
        scenario = persona.scenarios[0]  # canonical first scoring scenario
        print(f"=== {persona.slug} / {scenario.label} ===", flush=True)
        walk = _generate_walk(persona, scenario, ai_caller)
        out_path = _write_walk_md(out_dir, walk)
        print(
            f"  elapsed={walk['elapsed_s']:.1f}s  "
            f"length={len(walk['letter'])}  "
            f"filler={len(walk['filler_hits'])}  "
            f"bullets={len(walk['body_bullets'])}  "
            f"role={len(walk['role_hits'])}  "
            f"context={len(walk['context_hits'])}",
            flush=True,
        )
        print(f"  -> {out_path.relative_to(Path.cwd())}", flush=True)
        walks.append(walk)
    overall_elapsed = time.monotonic() - overall_t0

    # Aggregate summary
    print()
    print("=" * 60)
    print(f"=== AGGREGATE — 7 personas, {overall_elapsed:.1f}s total ===")
    print("=" * 60)
    n_filler_fail = sum(1 for w in walks if w["filler_hits"])
    n_bullet_fail = sum(1 for w in walks if w["body_bullets"])
    n_role_fail = sum(1 for w in walks if not w["role_hits"])
    n_context_fail = sum(1 for w in walks if not w["context_hits"])
    n_4_7_fail = sum(1 for w in walks if not (w["role_hits"] and w["context_hits"]))
    print(f"4.2 forbidden-filler fails:     {n_filler_fail}/7")
    print(f"4.3 markdown-bullet fails:      {n_bullet_fail}/7")
    print(f"4.7 role-token-missing fails:   {n_role_fail}/7")
    print(f"4.7 context-token-missing:      {n_context_fail}/7")
    print(f"4.7 combined PASS rate:         {7 - n_4_7_fail}/7")
    print()
    if any([n_filler_fail, n_bullet_fail, n_4_7_fail]):
        print("STATUS: gate failures present. Inspect the per-persona .md files.")
        return 1
    print(
        "STATUS: 7/7 personas pass automated gates. Operator review for inspection-grade points still required."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
