"""CV-vs-JD enhancement consultation.

Unlike :mod:`analysis.execute_cv_tailoring` (which auto-rewrites the
CV), this module helps the user STRENGTHEN their CV by asking
targeted questions. Output is a list of gap-questions:

    - "The JD asks for X. Your CV doesn't mention it — do you have
      experience with X? Yes → I'll add a one-sentence story."

Two paths:

1. AI-backed — model compares CV + JD and emits a JSON list of
   ``{"gap": "...", "question": "..."}`` items.

2. Heuristic fallback — extracts terms from the JD that don't appear
   in the CV and prompts the user about them.

We never auto-add anything to the CV. The user has to confirm each
addition; the caller (chat handler) wires that confirmation flow.
"""

from __future__ import annotations

import json
import re
from typing import Callable


def build_consult_prompt(*, job: dict, cv_text: str) -> tuple[str, str]:
    system = (
        "You are a CV consultant. Given a job posting and an "
        "applicant's CV, identify 3-5 GAPS — specific things the "
        "JD asks for that are not present in the CV.\n\n"
        "For each gap, write a short user-facing QUESTION the "
        "applicant could answer to fill that gap.\n\n"
        "OUTPUT — ONLY a JSON list of objects on one line:\n"
        '  [{"gap": "<JD requirement>", "question": '
        '"<one-sentence question to the applicant>"}, ...]\n\n'
        "RULES:\n"
        "- Never invent CV facts. Only point at what's missing.\n"
        "- Questions should be short, concrete, and answerable in "
        "one sentence.\n"
        "- If the CV already covers everything, return an empty list."
    )
    user = (
        f"Job title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Job description / posting:\n"
        f"{job.get('description') or job.get('rawDescription') or '(no description; consult by title only)'}\n\n"
        f"Applicant CV:\n{cv_text}"
    )
    return system, user


def parse_consult_response(raw: str | None) -> list[dict[str, str]]:
    """Pull the gap list from the AI's JSON-output response."""
    if not raw:
        return []
    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        return []
    try:
        parsed = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    out: list[dict[str, str]] = []
    for item in parsed[:6]:
        if not isinstance(item, dict):
            continue
        gap = str(item.get("gap") or "").strip()
        question = str(item.get("question") or "").strip()
        if gap and question:
            out.append({"gap": gap[:160], "question": question[:200]})
    return out


# Heuristic stopwords for the fallback path — we don't want to surface
# generic JD boilerplate as "gaps".
_STOP = {
    "the", "and", "or", "for", "with", "you", "your", "we", "our",
    "are", "you'll", "will", "have", "has", "this", "that", "team",
    "experience", "year", "years", "english", "deutsch", "german",
    "job", "role", "position", "company", "candidate", "applicant",
    "ideal", "looking", "based", "ability", "able", "must", "should",
    "ein", "eine", "und", "oder", "für", "der", "die", "das",
    "wir", "sie", "ihr", "stelle",
}


def heuristic_consult(*, job: dict, cv_text: str) -> list[dict[str, str]]:
    """Fallback when no AI is configured. Pulls capitalised /
    technical-looking terms from the JD that don't appear in the CV
    and surfaces them as gap-questions. Conservative — produces 0-3
    items so the user isn't drowned in noise."""
    description = (
        job.get("description")
        or job.get("rawDescription")
        or job.get("raw_description")
        or ""
    )
    if not description:
        return []
    cv_lower = (cv_text or "").lower()
    # Tokens: alpha tokens longer than 4 chars, with at least one
    # capital letter (signals a proper noun / tech term) — drops generic
    # filler words.
    candidates: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9.+/\-]{4,}", description):
        cleaned = token.strip(".,;:()/+-")
        low = cleaned.lower()
        if low in _STOP or low in seen:
            continue
        if not any(c.isupper() for c in cleaned[1:]) and not cleaned[0].isupper():
            continue
        if low in cv_lower:
            continue
        seen.add(low)
        candidates.append(cleaned)
        if len(candidates) >= 3:
            break
    return [
        {"gap": c,
          "question": f"Do you have hands-on experience with **{c}**? "
                       "If yes, give me a one-sentence story I can add."}
        for c in candidates
    ]


def consult(
    *, job: dict, cv_text: str,
    ai_caller: Callable[[str, str], str | None] | None,
) -> tuple[list[dict[str, str]], bool]:
    """Top-level consultation. Returns ``(gaps, used_ai)`` where
    ``gaps`` is a list of ``{gap, question}`` dicts and ``used_ai``
    is True iff the AI path produced the output (so the caller can
    decide whether to show the "running without AI" banner)."""
    if ai_caller is not None:
        system, user = build_consult_prompt(job=job, cv_text=cv_text)
        try:
            raw = ai_caller(system, user)
            ai_gaps = parse_consult_response(raw)
            if ai_gaps:
                return ai_gaps, True
        except Exception:  # noqa: BLE001
            pass
    return heuristic_consult(job=job, cv_text=cv_text), False
