# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Loop 9 — Aïcha post-Bug-C re-walk (live HTTP API + Ollama).

Drives Aïcha through the full 12-phase journey against the post-Bug-C
journey machine. Captures verbatim turn-by-turn evidence and writes
docs/grant/journey-walks-2026-05-20/aicha-post-bug-c.md.

The walk is DYNAMIC — it inspects each response (journeyPhase + reply
shape) and picks the next input from a per-phase decision tree. This
covers the Bug-C empty-state branches (diagnostic, widening menu,
auto-relax, final-state, start-fresh) when they trigger AND the
populated-results review path when results come back.

Usage:
    python3 scripts/post_bug_c_aicha_walk.py --base http://127.0.0.1:8765

The script assumes a server is already running with:
  - DIRECTJOB_ALLOW_REGISTRATION=true (or equivalent)
  - Ollama llama3.1:8b reachable at OLLAMA_HOST (env or default
    http://127.0.0.1:11434)
  - Fresh data dir (cold cache so Bug C path is more likely)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from company_discovery.persona_fixtures import PERSONAS  # noqa: E402

DEFAULT_BASE = "http://127.0.0.1:8765"
MAX_TURNS = 60  # hard cap; Aïcha should finish in ~25-35


# ───────────────────────── HTTP client ────────────────────────────


class _Client:
    """Cookie-jar + CSRF-aware HTTP client matching the e2e test
    pattern (tests/e2e/journey_ux_expert.py)."""

    def __init__(self, base: str) -> None:
        self.base = base
        self.cookie = ""
        self.csrf = ""

    def request(
        self, method: str, path: str, body: dict | None = None,
        timeout: float = 120.0,
    ) -> tuple[int, Any]:
        data = None
        headers: dict[str, str] = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf and method != "GET":
            headers["X-CSRF-Token"] = self.csrf
        req = urllib.request.Request(
            self.base + path, data=data, method=method, headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                sc = resp.headers.get("Set-Cookie", "")
                if sc:
                    self.cookie = sc.split(";", 1)[0]
                raw = resp.read().decode("utf-8", errors="replace")
                payload: Any = {}
                if raw:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = raw
                if isinstance(payload, dict):
                    for k in ("csrfToken", "csrf_token"):
                        if isinstance(payload.get(k), str) and payload[k]:
                            self.csrf = payload[k]
                            break
                    u = payload.get("user") or {}
                    if isinstance(u, dict):
                        for k in ("csrfToken", "csrf_token"):
                            if isinstance(u.get(k), str) and u[k]:
                                self.csrf = u[k]
                                break
                return resp.status, payload
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            try:
                return e.code, (json.loads(raw) if raw else {})
            except json.JSONDecodeError:
                return e.code, raw


def _register(client: _Client) -> str:
    email = f"aicha-post-bug-c+{secrets.token_hex(4)}@example.test"
    client.request("GET", "/")
    s, p = client.request(
        "POST", "/api/auth/register",
        {
            "email": email,
            "password": "post-bug-c-99-X",
            "tosAccepted": True,
            "privacyAccepted": True,
        },
    )
    if s not in (200, 201):
        raise RuntimeError(f"register failed status={s} payload={p!r}")
    return email


def _send(client: _Client, msg: str, timeout: float = 120.0) -> tuple[dict, int]:
    started = time.monotonic()
    s, p = client.request("POST", "/api/chat/message", {"message": msg}, timeout=timeout)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    if not isinstance(p, dict):
        p = {"error": f"non-dict body status={s}: {p!r}"}
    if s != 200:
        p.setdefault("error", {"status": s, "body_excerpt": str(p)[:200]})
    return p, elapsed_ms


# ───────────────────────── Walk driver ────────────────────────────


def _aicha_cv_paste() -> str:
    """Build a CV-shaped paste from Aïcha's persona fixture. Includes
    enough markers (email, phone, date range, section header,
    bullets) to pass looks_like_pasted_cv (>= 80 chars + at least one
    marker + no complaint tells)."""
    aicha = next(p for p in PERSONAS if p.slug == "aicha")
    return (
        f"{aicha.display_name}\n"
        f"Email: aicha.post-bug-c@example.test\n"
        f"Phone: +49 30 1234-5678\n"
        f"Location: {aicha.location}\n"
        f"Residency status: {aicha.residency_status}\n\n"
        f"Profile / Summary:\n"
        f"{aicha.cv_summary}\n\n"
        f"Experience:\n"
        f"  - 2019 - 2026 — Geriatric ward, regional hospital, Tunis (registered nurse)\n"
        f"  - 2016 - 2019 — General medical ward, Tunis (registered nurse)\n\n"
        f"Skills:\n"
        + "\n".join(f"  - {s}" for s in aicha.skills)
        + "\n\n"
        f"Languages: {', '.join(aicha.languages)}\n\n"
        f"Friction context: {aicha.friction_notes}\n"
    )


def _next_input(reply: str, phase: str | None, prior: list[dict]) -> str | None:
    """Decide the next user input given the current response shape.

    Returns None when the walk should stop (terminal state reached or
    explicit dead-end).

    The decision tree mirrors what an alert-but-honest persona would
    type in chat. Bug-C branches (empty-state, auto-relax, laterals-
    confirmation, final-state) are recognised by reply substring +
    journeyPhase.
    """
    aicha = next(p for p in PERSONAS if p.slug == "aicha")
    rlow = (reply or "").lower()

    # Terminal / done
    if phase == "done":
        return None

    # ─── Discover phase ───
    if phase == "discover":
        # Multi-step within discover; pick by what the prompt is asking.
        # The discover handler emits a numbered question each time.
        if any(k in rlow for k in ("what kind of role", "kind of role this time")):
            return aicha.target_roles[0]
        if "where" in rlow:
            return aicha.location
        if "years" in rlow and "experience" in rlow:
            return str(aicha.years_experience)
        if "languages" in rlow or "language" in rlow:
            return ", ".join(aicha.languages[:3])
        # Fallback: re-emit the role (sometimes /start lands here)
        return aicha.target_roles[0]

    # ─── CV check ───
    if phase == "cv_check":
        # Bug-C piece-2 clarification: the cv_check phase emits a
        # prompt asking the user to paste their CV (or pick reuse /
        # build via chat). The simplest path is paste — Aïcha's
        # fixture has cv_summary content that gets shaped into a
        # CV-marker-passing paste.
        if "paste" in rlow or "drop the whole text" in rlow or "lebenslauf" in rlow:
            return _aicha_cv_paste()
        # If we're past the paste and the handler is acknowledging:
        if "thanks" in rlow or "got your cv" in rlow or "saved" in rlow:
            return "ok"
        return _aicha_cv_paste()

    # ─── Inspire ───
    if phase == "inspire":
        # Bug-A fix: decline tokens widened. Aïcha already has the
        # canonical Krankenpfleger role — decline laterals to keep
        # the test deterministic.
        return "no"

    # ─── Preferences ───
    if phase == "preferences":
        # Bug-B fix: empty + advance guard. Choose "none" to skip
        # all soft prefs and move to search.
        return "none"

    # ─── Search / Review ───
    if phase == "search" or phase == "review":
        # Review with results: the reply lists categories. Pick #1.
        # Review empty: Bug-C path.
        if "no live postings" in rlow or "no matches found" in rlow:
            # Bug-C piece 1-5: empty-state menu. We've now seen the
            # diagnostic_text + the affordances. Probe each Bug-C
            # piece by exercising the menu.
            # Decision: if final-state ("you've tried these
            # widenings"), pick start-fresh.
            if "you've tried these widenings" in rlow:
                # Final-state — operator's expected exhaustion path.
                return "start fresh"
            # Mid-empty-state — try widening 1 (constrained ordering
            # puts try_laterals first for Aïcha §16d).
            return "1"
        # Populated review: pick a category
        if "good fit" in rlow or "strong fit" in rlow or "1." in reply:
            return "1"
        return "1"

    # ─── Drill ───
    if phase == "drill":
        return "1"

    # ─── Tailor / Letter / Consult ───
    if phase == "tailor":
        # Two tracks: tailor produces CV, then offer letter.
        if "letter" in rlow or "anschreiben" in rlow or "/letter" in rlow:
            return "/letter"
        return "/tailor"

    if phase == "letter":
        return "/consult"

    if phase == "cv_consult":
        # Offer a brief answer to whatever the consult asks.
        return "I have geriatric experience from Tunis and §16d residency."

    # Greet or unknown: kick off /start
    if phase in (None, "greet"):
        return "/start"

    # Unknown phase: try /start as a safe re-kick (probably won't help
    # but won't crash).
    return "/start"


def walk_aicha(client: _Client, max_turns: int = MAX_TURNS) -> list[dict]:
    """Drive the walk. Returns the full captured turn log."""
    captured: list[dict] = []

    # Turn 0 is implicit (greet — the server's initial state). We
    # kick off with /start.
    next_input: str | None = "/start"
    last_phase: str | None = None
    saw_diagnostic = False
    saw_caveat = False
    saw_count_text = False
    saw_auto_relax = False
    saw_final_state = False
    saw_start_fresh = False

    for turn_idx in range(1, max_turns + 1):
        if next_input is None:
            break

        body, elapsed_ms = _send(client, next_input)
        actual_phase = body.get("journeyPhase")
        reply = body.get("reply") or ""
        executed = body.get("executed")
        error = body.get("error")

        # Bug-C signal detection
        rlow = reply.lower()
        if not saw_diagnostic and (
            "no live postings" in rlow or "across the 8 connected providers" in rlow
            or "no matches found for" in rlow
        ):
            saw_diagnostic = True
        if not saw_caveat and (
            "ausländerbehörde" in reply or "auslanderbehorde" in rlow
            or "migrationsberatungsstelle" in reply.lower()
        ):
            saw_caveat = True
        if not saw_count_text and "postings)" in reply:
            saw_count_text = True
        if not saw_auto_relax and (
            "auto-relax" in rlow or "let the system suggest" in rlow
        ):
            saw_auto_relax = True
        if not saw_final_state and "you've tried these widenings" in rlow:
            saw_final_state = True
        if not saw_start_fresh and (
            "clearing your old search" in rlow
            or "**start fresh**" in rlow
        ):
            saw_start_fresh = True

        captured.append({
            "turn": turn_idx,
            "input": next_input,
            "input_truncated_for_log": next_input[:80]
                + ("…" if len(next_input) > 80 else ""),
            "reply": reply,
            "journey_phase_before": last_phase,
            "journey_phase_after": actual_phase,
            "executed": executed,
            "elapsed_ms": elapsed_ms,
            "error": error,
            "extras": {
                k: v for k, v in body.items()
                if k not in {"reply", "journeyPhase", "session", "executed",
                             "csrfToken", "csrf_token", "user"}
            },
        })

        print(
            f"  turn {turn_idx:2d}: phase={actual_phase!s:13s} "
            f"{elapsed_ms:5d}ms  input={next_input[:38]!r:42s} "
            f"reply={reply[:50]!r}",
            flush=True,
        )

        if error:
            print(f"    ERROR (stopping walk for inspection): {error}", flush=True)
            break

        last_phase = actual_phase

        # Decide next input
        next_input = _next_input(reply, actual_phase, captured)

        if actual_phase == "done":
            print("    journey reached PHASE_DONE; stopping walk", flush=True)
            break

    signals = {
        "saw_diagnostic": saw_diagnostic,
        "saw_caveat_for_auslanderbehoerde": saw_caveat,
        "saw_count_text": saw_count_text,
        "saw_auto_relax_offered": saw_auto_relax,
        "saw_final_state": saw_final_state,
        "saw_start_fresh_bridge": saw_start_fresh,
    }
    return captured, signals


# ───────────────────────── Markdown writer ────────────────────────


def write_walk_md(out_dir: Path, captured: list[dict], signals: dict, base: str) -> Path:
    aicha = next(p for p in PERSONAS if p.slug == "aicha")
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    lines: list[str] = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        "",
        "# Aïcha post-Bug-C re-walk — full 12-phase journey via live HTTP API",
        "",
        f"**Walked**: {now} (UTC)  |  **Persona**: {aicha.display_name} ({aicha.slug})  |  **Cohort**: {aicha.cohort}",
        f"**Server**: {base}  |  **Provider**: Ollama llama3.1:8b",
        f"**Residency status**: {aicha.residency_status}",
        f"**Friction notes**: {aicha.friction_notes}",
        "",
        "## Purpose",
        "",
        "Loop 9 of PART 6 — EVIDENCE LAYER for Bug C closure.",
        "Pre/post comparison against the original Aïcha shape-test that",
        "surfaced Bugs A, B, and C (`aicha-shape-test.md`, 2026-05-20).",
        "",
        "This walk drives the full 12-phase journey against the post-",
        "Bug-C journey machine and captures verbatim turn-by-turn output.",
        "Whether Aïcha exercises the Bug-C empty-state branches or the",
        "populated-results review path depends on aggregator response;",
        "both outcomes are valid evidence (operator directive).",
        "",
        "## Bug-C signal summary",
        "",
        "| Signal | Observed |",
        "|---|---|",
        f"| Diagnostic text on empty-state | {'YES' if signals['saw_diagnostic'] else 'no'} |",
        f"| Ausländerbehörde caveat on widen-location | {'YES' if signals['saw_caveat_for_auslanderbehoerde'] else 'no'} |",
        f"| Adjacent-criterion count parenthetical | {'YES' if signals['saw_count_text'] else 'no'} |",
        f"| Auto-relax slot offered | {'YES' if signals['saw_auto_relax_offered'] else 'no'} |",
        f"| Final-state summary block | {'YES' if signals['saw_final_state'] else 'no'} |",
        f"| Start-fresh bridge → DISCOVER_ASK_ROLE | {'YES' if signals['saw_start_fresh_bridge'] else 'no'} |",
        "",
        "## Per-turn transcript",
        "",
        "| # | Phase | User input | Elapsed | Notes |",
        "|---|---|---|---|---|",
    ]
    for t in captured:
        inp = t["input_truncated_for_log"].replace("|", "\\|").replace("\n", " / ")
        notes = []
        if t.get("error"):
            notes.append("**ERROR**")
        if (t.get("executed") or "").strip():
            notes.append(f"exec=`{t['executed']}`")
        lines.append(
            f"| {t['turn']} | `{t['journey_phase_after']}` | `{inp}` | "
            f"{t['elapsed_ms']} ms | {' '.join(notes) or '—'} |"
        )

    # Latency summary
    durations = [t["elapsed_ms"] for t in captured if not t.get("error")]
    if durations:
        sorted_d = sorted(durations)
        p50 = sorted_d[len(sorted_d) // 2]
        p95 = sorted_d[max(0, int(len(sorted_d) * 0.95) - 1)]
        max_d = max(durations)
        total = sum(durations)
        lines += [
            "",
            "## Latency summary",
            "",
            f"- **Turns**: {len(durations)}",
            f"- **Total**: {total/1000:.1f} s wall-clock",
            f"- **p50**: {p50} ms",
            f"- **p95**: {p95} ms",
            f"- **max**: {max_d} ms",
        ]

    # Per-turn detail
    lines += ["", "## Per-turn detail (verbatim)", ""]
    for t in captured:
        lines.append(f"### Turn {t['turn']} — phase `{t['journey_phase_after']}` ({t['elapsed_ms']} ms)")
        lines.append("")
        if t.get("error"):
            lines.append(f"**ERROR**: `{json.dumps(t['error'])[:400]}`")
            lines.append("")
        lines.append("**User input**:")
        lines.append("```")
        lines.append(t["input"])
        lines.append("```")
        lines.append("")
        lines.append("**Assistant reply** (verbatim):")
        lines.append("```")
        lines.append(t["reply"] or "(empty)")
        lines.append("```")
        if t.get("extras"):
            lines.append("")
            lines.append(
                "**Extra response fields** "
                "(beyond `reply` / `journeyPhase` / `session` / `executed`):"
            )
            lines.append("```json")
            lines.append(json.dumps(t["extras"], ensure_ascii=False, indent=2)[:2000])
            lines.append("```")
        lines.append("")

    lines += [
        "## Pre/post comparison (vs aicha-shape-test.md)",
        "",
        "The original shape-test surfaced 7 surprises that became Bugs A/B/C:",
        "",
        "1. **Inspire phase decline tokens too narrow** — fix Bug A (`da682ad`)",
        "2. **Preferences advance guard missing** — fix Bug B (`a66c778`)",
        "3. **Empty-state review phase silent advance** — fix Bug C piece 1 (`c89632f`)",
        "4. **No cache-only diagnostic on 0-results** — fix Bug C piece 2 (`d639af8`)",
        "5. **No persona-aware widening affordances** — fix Bug C piece 3 (`4fc71e1`)",
        "6. **No consented auto-relax** — fix Bug C piece 4 (`d951045`)",
        "7. **No adjacent-criterion counts / no final-state exit** — fix Bug C pieces 5 + 6 (`bdcf38f` + `1af9de8`)",
        "",
        "Walk this transcript to verify the smoothness improvements live for Aïcha:",
        "",
        "- Did the inspire phase accept her decline cleanly?",
        "- Did the preferences phase guard against empty input?",
        "- If empty-state was reached: diagnostic, persona-aware ordering (try_laterals first for §16d), Ausländerbehörde caveat on widen-location, adjacent-criterion counts on warm-cache affordances?",
        "- If auto-relax exercised: did suggestions match constrained ordering?",
        "- If final-state reached: did start-fresh route back to DISCOVER_ASK_ROLE?",
        "",
        "## Operator review notes",
        "",
        "Walk for anything that surfaces UNEXPECTED behaviour against the code-read.",
        "Immediate-sync triggers (per operator directive):",
        "- New root-cause bug (Bug E candidate)",
        "- A persona genuinely dead-ended outside Bug C scope",
        "- AI output wrong-class for Aïcha (e.g., non-Anerkennung-friendly Anschreiben)",
        "- Per-turn latency over 30s",
        "",
    ]
    out_path = out_dir / "aicha-post-bug-c.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# ───────────────────────── Main ────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    args = parser.parse_args()

    client = _Client(args.base)
    print(f"[walk] base={args.base}", flush=True)

    # Register fresh user
    started = time.monotonic()
    email = _register(client)
    print(f"[walk] registered {email} ({int((time.monotonic()-started)*1000)} ms)", flush=True)

    # Drive walk
    captured, signals = walk_aicha(client, max_turns=args.max_turns)
    print(f"[walk] walked {len(captured)} turns; Bug-C signals: {signals}", flush=True)

    out_dir = ROOT / "docs" / "grant" / "journey-walks-2026-05-20"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = write_walk_md(out_dir, captured, signals, args.base)
    print(f"[walk] wrote {out_path.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
