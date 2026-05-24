# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 gate 6.1 — drive one persona's journey via the live HTTP API.

Logs every (input, reply, phase) tuple to a per-persona walk markdown
file under docs/grant/journey-walks-2026-05-20/.

Usage:
    python3 scripts/journey_walk.py <persona-slug> <session-jar> <csrf>
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from company_discovery.persona_fixtures import PERSONAS  # noqa: E402

BASE = "http://127.0.0.1:8765"


def load_cookies(jar_path: Path) -> str:
    """Read a Netscape cookie jar and return a Cookie header.

    The Netscape cookie format uses lines starting with ``#HttpOnly_``
    as real cookie entries (NOT comments) — only lines starting with
    ``#`` that are NOT ``#HttpOnly_`` are comments. Earlier versions of
    this helper incorrectly skipped every ``#``-prefixed line, which
    silently dropped the session cookie and produced 401s on every
    chat call.
    """
    cookies = []
    for line in jar_path.read_text().splitlines():
        if not line:
            continue
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name, value = parts[5], parts[6]
            cookies.append(f"{name}={value}")
    return "; ".join(cookies)


def send_message(message: str, cookie_header: str, csrf: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}/api/chat/message",
        data=json.dumps({"message": message}).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie_header,
            "X-CSRF-Token": csrf,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": {"code": e.code, "body": e.read().decode("utf-8")}}


def reset_chat(cookie_header: str, csrf: str) -> None:
    req = urllib.request.Request(
        f"{BASE}/api/chat/reset",
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie_header,
            "X-CSRF-Token": csrf,
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass


def walk_persona(persona_slug: str, cookie_header: str, csrf: str) -> dict:
    """Drive a persona-shaped journey. Returns the captured walk."""

    persona = next(p for p in PERSONAS if p.slug == persona_slug)
    role_answer = persona.target_roles[0]
    location_answer = persona.location
    years_answer = str(persona.years_experience)
    lang_answer = ", ".join(persona.languages[:3])

    inputs = [
        ("/start", "Begin guided journey"),
        (role_answer, "Answer: target role"),
        (location_answer, "Answer: target location"),
        (years_answer, "Answer: years of experience"),
        (lang_answer, "Answer: languages"),
    ]

    captured = []
    reset_chat(cookie_header, csrf)
    for user_input, label in inputs:
        started = time.monotonic()
        resp = send_message(user_input, cookie_header, csrf)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        result = resp.get("result") or {}
        # The top-level response carries journeyPhase on every turn
        # (post-2026-05-20 fix landed during PART 6 walk #1). The
        # `result` dict may also carry it for /start-style responses;
        # prefer top-level for consistency across all turn types.
        captured.append(
            {
                "label": label,
                "input": user_input,
                "reply": resp.get("reply", ""),
                "executed": resp.get("executed"),
                "journey_phase": resp.get("journeyPhase") or result.get("journeyPhase"),
                "done": result.get("done"),
                "elapsed_ms": elapsed_ms,
                "raw_result_keys": list(result.keys()),
                "error": resp.get("error"),
            }
        )
    return {"persona": persona, "captured": captured}


def write_walk_md(out_dir: Path, walk: dict) -> Path:
    persona = walk["persona"]
    captured = walk["captured"]

    md = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        "",
        f"# Journey walk — {persona.display_name}",
        "",
        f"**Persona slug**: `{persona.slug}`  |  **Cohort**: `{persona.cohort}`",
        f"**Residency status**: {persona.residency_status}",
        f"**Friction notes**: {persona.friction_notes}",
        "",
        "## Walk-through (live HTTP API, /api/chat/message)",
        "",
        "Each row captures one user → assistant turn with the journey-phase",
        "transition and the wall-clock latency for that turn.",
        "",
        "| # | User input | Phase after | Reply (truncated) | Elapsed |",
        "|---|---|---|---|---|",
    ]
    for i, turn in enumerate(captured, start=1):
        reply_snippet = (turn["reply"] or "").replace("\n", "  ").replace("|", "\\|")
        if len(reply_snippet) > 140:
            reply_snippet = reply_snippet[:137] + "…"
        md.append(
            f"| {i} | `{turn['input']}` | `{turn['journey_phase']}` | {reply_snippet} | {turn['elapsed_ms']} ms |"
        )

    md.append("")
    md.append("## Per-turn detail")
    md.append("")
    for i, turn in enumerate(captured, start=1):
        md.append(f"### Turn {i} — {turn['label']}")
        md.append("")
        md.append(f"**Input**: `{turn['input']}`")
        md.append("")
        md.append(
            f"**Executed**: `{turn.get('executed')}`  |  **Phase after**: `{turn['journey_phase']}`  |  **Done**: `{turn['done']}`  |  **Elapsed**: {turn['elapsed_ms']} ms"
        )
        md.append("")
        if turn.get("error"):
            md.append(f"**ERROR**: `{turn['error']}`")
            md.append("")
        md.append("**Reply**:")
        md.append("")
        md.append("```")
        md.append(turn["reply"] or "(empty)")
        md.append("```")
        md.append("")

    # Gate-6.1 assessment per turn
    md.append("## Gate 6.1 assessment (per-turn)")
    md.append("")
    md.append(
        "| Turn | Phase | Clear entry? | Clear next-step prompt? | Clear exit signal? | No dead-end? |"
    )
    md.append("|---|---|---|---|---|---|")
    for i, turn in enumerate(captured, start=1):
        reply = turn["reply"] or ""
        # Heuristic checks (operator inspection still required)
        clear_entry = len(reply) >= 30  # non-trivial message
        has_prompt = "?" in reply or any(
            kw in reply.lower() for kw in ["what", "which", "wie", "was", "welche"]
        )
        # Exit signal: phase advanced OR explicit "done" marker
        clear_exit = turn["journey_phase"] is not None or turn.get("done")
        no_deadend = not turn.get("error") and (clear_exit or has_prompt)
        md.append(
            f"| {i} | `{turn['journey_phase']}` | {'OK' if clear_entry else 'NEEDS_REVIEW'} | {'OK' if has_prompt else 'NEEDS_REVIEW'} | {'OK' if clear_exit else 'NEEDS_REVIEW'} | {'OK' if no_deadend else 'NEEDS_REVIEW'} |"
        )

    md.append("")
    md.append("## Operator inspection notes")
    md.append("")
    md.append("- Does each phase make it clear WHERE the user is in the 12-phase flow?")
    md.append(
        "- Is the next-step prompt unambiguous (one specific question, not a wall of options)?"
    )
    md.append("- Does the exit signal (phase advance) come back to the UI clearly?")
    md.append(
        "- For migrant personas: is friction context handled gracefully throughout, OR does the journey assume baseline German fluency / German-format CV?"
    )
    md.append(
        "- For wider-friction personas (Käthe / Tobias): does the same UI work without over-emphasising friction they don't have?"
    )
    md.append("")
    return out_dir, md


def main() -> int:
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <persona-slug> <session-jar> <csrf-token>")
        return 2
    slug = sys.argv[1]
    jar = Path(sys.argv[2])
    csrf = sys.argv[3]

    cookie_header = load_cookies(jar)
    out_dir = ROOT / "docs" / "grant" / "journey-walks-2026-05-20"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Walking persona: {slug} ===", flush=True)
    walk = walk_persona(slug, cookie_header, csrf)
    _, md_lines = write_walk_md(out_dir, walk)
    out_path = out_dir / f"{slug}.md"
    out_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"  -> {out_path.relative_to(ROOT)}", flush=True)
    for turn in walk["captured"]:
        print(
            f"    [{turn['journey_phase']}] {turn['input'][:30]:30s} -> {(turn['reply'] or '')[:60]}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
