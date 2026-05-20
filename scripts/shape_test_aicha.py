# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Aïcha shape-test — drive the full 12-phase journey via the
live HTTP API, capture every turn verbatim, and surface anything
UNEXPECTED.

Per operator (2026-05-20):
  > capture per-phase but explicitly call out anything UNEXPECTED —
  > every place where the walk surfaced a phase behaviour you didn't
  > predict from reading journey.py.

The output lands at docs/grant/journey-walks-2026-05-20/aicha-shape-
test.md. Annotations between turns flag predicted-vs-actual.
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
    cookies = []
    for line in jar_path.read_text().splitlines():
        if not line:
            continue
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies.append(f"{parts[5]}={parts[6]}")
    return "; ".join(cookies)


def send(message: str, cookies: str, csrf: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}/api/chat/message",
        data=json.dumps({"message": message}).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookies,
            "X-CSRF-Token": csrf,
        },
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {
            "error": {
                "code": e.code,
                "body": e.read().decode("utf-8", errors="replace"),
            }
        }
    return body, int((time.monotonic() - started) * 1000)


def reset(cookies: str, csrf: str) -> None:
    req = urllib.request.Request(
        f"{BASE}/api/chat/reset",
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookies,
            "X-CSRF-Token": csrf,
        },
    )
    urllib.request.urlopen(req, timeout=10).read()


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <session-jar> <csrf-token>")
        return 2
    jar = Path(sys.argv[1])
    csrf = sys.argv[2]
    cookies = load_cookies(jar)

    aicha = next(p for p in PERSONAS if p.slug == "aicha")
    # Use her CV summary as the "paste" path in cv_check.
    paste_cv = (
        f"{aicha.display_name}\n"
        f"Email: aicha.shape-test@example.test\n"
        f"Phone: +49 30 0000-000\n"
        f"Location: {aicha.location}\n"
        f"Residency status: {aicha.residency_status}\n\n"
        f"Profile: {aicha.cv_summary}\n\n"
        f"Skills: {', '.join(aicha.skills)}\n\n"
        f"Languages: {', '.join(aicha.languages)}\n\n"
        f"Friction context: {aicha.friction_notes}\n"
    )

    # Predicted turn sequence — based on reading journey.py. Each
    # tuple is (label, expected_phase_after, input). We capture actual
    # phase + reply + AI calls + latency; surprises get flagged in
    # the markdown.
    turns = [
        ("Begin guided journey", "discover", "/start"),
        ("Answer role", "discover", aicha.target_roles[0]),
        ("Answer location", "discover", aicha.location),
        ("Answer years", "discover", str(aicha.years_experience)),
        (
            "Answer languages — should transition to cv_check",
            "cv_check",
            ", ".join(aicha.languages[:3]),
        ),
        (
            "cv_check: paste her CV — should chain into inspire",
            "preferences",  # PREDICTED: inspire chains immediately
            paste_cv,
        ),
        (
            "preferences: 'none' (no deal-breakers)",
            "search",
            "none",
        ),
        # search returns the results synchronously per
        # _advance_prefs returning run_search_with — but I'm not sure
        # if the HTTP layer auto-fires the search or whether the user
        # needs another input. We'll see.
        (
            "After search: pick first category",
            "drill",
            "1",
        ),
        (
            "After drill: pick first job for tailor/letter offer",
            "tailor",
            "1",
        ),
        (
            "Tailor: /tailor command for the picked job",
            "tailor",
            "/tailor",
        ),
        (
            "Letter: /letter command",
            "letter",
            "/letter",
        ),
        (
            "CV consult: /consult command",
            "cv_consult",
            "/consult",
        ),
    ]

    reset(cookies, csrf)
    print("Shape-test reset; beginning Aïcha walk...", flush=True)
    captured = []
    for label, predicted_phase, user_input in turns:
        body, elapsed_ms = send(user_input, cookies, csrf)
        actual_phase = body.get("journeyPhase")
        reply = body.get("reply", "")
        executed = body.get("executed")
        error = body.get("error")
        captured.append(
            {
                "label": label,
                "predicted_phase": predicted_phase,
                "actual_phase": actual_phase,
                "input": user_input,
                "reply": reply,
                "executed": executed,
                "elapsed_ms": elapsed_ms,
                "error": error,
                "extras": {
                    k: v
                    for k, v in body.items()
                    if k not in {"reply", "journeyPhase", "session", "executed"}
                },
            }
        )
        print(
            f"  turn {len(captured):2d}: {predicted_phase:11s}→{actual_phase or '?':12s} "
            f"{elapsed_ms:5d}ms  input={user_input[:40]!r}",
            flush=True,
        )
        if error:
            print(f"    ERROR: {error}", flush=True)
            print(f"    Stopping early to inspect.", flush=True)
            break

    # Write the shape-test markdown
    out_path = (
        ROOT
        / "docs"
        / "grant"
        / "journey-walks-2026-05-20"
        / "aicha-shape-test.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        "",
        "# Aïcha shape-test — full 12-phase journey via live HTTP API",
        "",
        "Per operator directive 2026-05-20: drive Aïcha turn-by-turn,",
        "capture verbatim, flag every PREDICTED-vs-ACTUAL divergence.",
        "Shape-test informs the refactor of `scripts/journey_walk.py`",
        "to capture exactly what the live system surfaces (not what",
        "the code-read predicted).",
        "",
        f"**Persona**: {aicha.display_name} ({aicha.slug}, {aicha.cohort})",
        f"**Provider**: Ollama llama3.1:8b at http://127.0.0.1:11434",
        "",
        "## Per-turn capture",
        "",
        "| # | Predicted phase | Actual phase | Surprise? | Input (truncated) | Elapsed |",
        "|---|---|---|---|---|---|",
    ]
    for i, t in enumerate(captured, start=1):
        surprise = "**YES**" if t["actual_phase"] != t["predicted_phase"] else "no"
        inp = t["input"][:60].replace("\n", "  ").replace("|", "\\|")
        if len(t["input"]) > 60:
            inp += "…"
        lines.append(
            f"| {i} | `{t['predicted_phase']}` | `{t['actual_phase']}` | {surprise} | `{inp}` | {t['elapsed_ms']} ms |"
        )
    lines.append("")
    lines.append("## Per-turn detail")
    lines.append("")
    for i, t in enumerate(captured, start=1):
        lines.append(f"### Turn {i} — {t['label']}")
        lines.append("")
        surprise = "**YES**" if t["actual_phase"] != t["predicted_phase"] else "no"
        lines.append(
            f"**Predicted phase**: `{t['predicted_phase']}`  |  **Actual phase**: `{t['actual_phase']}`  |  **Surprise?**: {surprise}"
        )
        lines.append(
            f"**Executed**: `{t.get('executed')}`  |  **Elapsed**: {t['elapsed_ms']} ms"
        )
        if t.get("error"):
            lines.append(f"**ERROR**: `{t['error']}`")
        lines.append("")
        lines.append("**Input**:")
        lines.append("```")
        lines.append(t["input"])
        lines.append("```")
        lines.append("")
        lines.append("**Reply** (verbatim):")
        lines.append("```")
        lines.append(t["reply"] or "(empty)")
        lines.append("```")
        if t.get("extras"):
            lines.append("")
            lines.append("**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):")
            lines.append("```json")
            lines.append(json.dumps(t["extras"], indent=2, ensure_ascii=False))
            lines.append("```")
        lines.append("")
    lines.append("")
    lines.append("## Surprise summary (PART 6 directive — feeds the refactor)")
    lines.append("")
    surprises = [
        (i, t)
        for i, t in enumerate(captured, start=1)
        if t["actual_phase"] != t["predicted_phase"]
    ]
    if not surprises:
        lines.append(
            "No predicted-vs-actual divergences. The code-read of journey.py "
            "matched the live behaviour exactly. (This is useful evidence "
            "in itself — phase inventory accurate.)"
        )
    else:
        lines.append(f"**{len(surprises)} divergences** observed:")
        lines.append("")
        for i, t in surprises:
            lines.append(
                f"- **Turn {i}** ({t['label']}): predicted "
                f"`{t['predicted_phase']}`, actual `{t['actual_phase']}`."
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path.relative_to(ROOT)}", flush=True)
    print(f"Surprises: {len(surprises)} of {len(captured)} turns", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
