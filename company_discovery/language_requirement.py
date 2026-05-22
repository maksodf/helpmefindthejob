# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Post-fetch language-requirement detection (phase2-backlog #72).

Upgrades the basic ``classify_language(description) -> "de"|"en"|""``
heuristic in ``job_index.py`` (which classifies *the language the JD
itself is written in*) into a richer detector that surfaces the
**language LEVEL the role requires of the candidate** — the signal
the user actually needs to decide whether a posting is reachable.

The doctrinal constraint from #72 is evidence-backed detection: the
output carries the matched phrases ("matched: 'B1-Deutsch
erforderlich'") so a user can verify the inference rather than
trust a black-box label.

Powers the ``loosen_language`` widening affordance documented in
PART 6 Bug C piece 3 (empty-state widening): when a search comes
up empty and the user's profile says they have B1 German, we can
offer to widen the search to include B1+ / native-friendly roles
instead of only matching exact-level postings.

The detector is deterministic + offline (regex + curated phrase
lists). No AI dependency. The output is a structured
``LanguageRequirement`` dataclass; the post-fetch annotator stamps
the result onto each ``AggregatedJob`` via its ``raw`` field so
downstream filters can read it without re-running detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Language-level ladder, ordered low → high. The Goethe / CEFR
# scale: A1 (beginner) → A2 → B1 → B2 → C1 → C2 → native.
# Used by the loosen_language widening affordance to decide which
# level steps to relax (e.g., user is B2, posting is C1 → offer
# the widening; user is A2, posting is C1 → no widening, too far).
LEVEL_ORDER: tuple[str, ...] = (
    "",  # unspecified / no requirement detected
    "A1+",
    "A2+",
    "B1+",
    "B2+",
    "C1+",
    "C2+",
    "native",
)


@dataclass(frozen=True)
class LanguageRequirement:
    """Detected language requirement on a job posting.

    ``language`` is the ISO 639-1 code ("de" / "en" / "") of the
    required language. ``level`` is the CEFR ladder rung.
    ``evidence`` carries the matched phrases verbatim so a user
    can verify the inference. ``confidence`` is a coarse
    high/medium/low signal driven by evidence count + signal
    strength.

    Empty fields = "no signal" (do not display, do not filter
    against). Detector is allowed to be silent — false negatives
    are safer than false positives in this surface (the user can
    always read the JD themselves).
    """

    language: str = ""
    level: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: str = ""  # "high" / "medium" / "low" / ""

    def is_silent(self) -> bool:
        """True when the detector found no usable signal."""

        return not self.language and not self.level

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "level": self.level,
            "evidence": list(self.evidence),
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Phrase patterns — German requirements
# ---------------------------------------------------------------------------

# Native-speaker patterns. Highest level; rare in modern JDs (legally
# suspect under anti-discrimination law in DE — see ADGG / GG Art. 3)
# but still present in legacy or niche postings.
_DE_NATIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bmuttersprachler?\b", re.IGNORECASE),
    re.compile(r"\bauf muttersprachlichem niveau\b", re.IGNORECASE),
    re.compile(r"\bnative german (?:speaker|level)\b", re.IGNORECASE),
    # English-language JD asking for native German (very common in
    # DACH-international postings). Anchored to a required-context
    # keyword to avoid matching "native German cuisine" etc.
    re.compile(
        r"\bnative german\s+(?:required|needed|essential|necessary|preferred|speaker|level)\b",
        re.IGNORECASE,
    ),
)

# C1+/C2 patterns — "verhandlungssicher" / "fließend" / explicit C1/C2.
_DE_C1_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "verhandlungssicher Deutsch" OR "verhandlungssicher
    # Deutschkenntnisse" — extended to match either noun form so a
    # JD writing "verhandlungssichere Deutschkenntnisse" doesn't
    # slip through.
    re.compile(
        r"\bverhandlungssicher(?:e|es|en|er)?\s+deutsch(?:kenntnisse)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfließend(?:e|es|en|er)?\s+deutsch(?:kenntnisse)?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bdeutsch\s+(?:auf\s+)?(?:c1|c2)\b", re.IGNORECASE),
    re.compile(r"\bc[12]\s*-?\s*deutsch\b", re.IGNORECASE),
    re.compile(r"\bdeutsch\s+fließend\b", re.IGNORECASE),
    re.compile(r"\bsehr\s+gute?\s+deutschkenntnisse\b", re.IGNORECASE),
)

# B2 patterns — explicit B2 mention.
_DE_B2_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bb2\s*-?\s*deutsch\b", re.IGNORECASE),
    re.compile(r"\bdeutsch\s+(?:auf\s+)?b2\b", re.IGNORECASE),
    re.compile(r"\bgute?\s+deutschkenntnisse\b", re.IGNORECASE),
    re.compile(r"\bdeutsch\s+gut\b", re.IGNORECASE),
)

# B1 patterns — explicit B1 mention, or "basic"/"Grundkenntnisse".
_DE_B1_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bb1\s*-?\s*deutsch\b", re.IGNORECASE),
    re.compile(r"\bdeutsch\s+(?:auf\s+)?b1\b", re.IGNORECASE),
    re.compile(r"\bdeutschkenntnisse\s+vorteilhaft\b", re.IGNORECASE),
    # Conservative: only count "Grundkenntnisse" if "Deutsch" appears nearby.
    re.compile(r"\bgrundkenntnisse\s+deutsch\b", re.IGNORECASE),
    re.compile(r"\bdeutsch\s+grundkenntnisse\b", re.IGNORECASE),
)

# Generic "German required" without level — implicit B2+ by convention
# in DACH labour-market patterns (Bundesagentur für Arbeit guidance).
_DE_REQUIRED_NO_LEVEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdeutsch\s+erforderlich\b", re.IGNORECASE),
    re.compile(r"\bdeutsch\s+ist\s+(?:eine\s+)?voraussetzung\b", re.IGNORECASE),
    re.compile(r"\bdeutschkenntnisse\s+erforderlich\b", re.IGNORECASE),
)


# ---------------------------------------------------------------------------
# Phrase patterns — English requirements
# ---------------------------------------------------------------------------

_EN_NATIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bnative english (?:speaker|level)\b", re.IGNORECASE),
    re.compile(r"\benglish (?:as a )?mother tongue\b", re.IGNORECASE),
    # "Native English required/needed" without explicit speaker/level
    re.compile(
        r"\bnative english\s+(?:required|needed|essential|necessary|preferred)\b",
        re.IGNORECASE,
    ),
)

_EN_C1_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfluent\s+(?:in\s+)?english\b", re.IGNORECASE),
    re.compile(r"\benglish\s+(?:proficiency|fluency)\b", re.IGNORECASE),
    re.compile(r"\benglish\s+c[12]\b", re.IGNORECASE),
    re.compile(r"\bc[12]\s*-?\s*english\b", re.IGNORECASE),
)

_EN_B2_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bb2\s*-?\s*english\b", re.IGNORECASE),
    re.compile(r"\benglish\s+b2\b", re.IGNORECASE),
    re.compile(r"\bgood\s+english\b", re.IGNORECASE),
    re.compile(r"\bstrong\s+english\b", re.IGNORECASE),
)

_EN_B1_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bb1\s*-?\s*english\b", re.IGNORECASE),
    re.compile(r"\benglish\s+b1\b", re.IGNORECASE),
    re.compile(r"\bbasic\s+english\b", re.IGNORECASE),
    re.compile(r"\bworking\s+(?:knowledge\s+of\s+)?english\b", re.IGNORECASE),
)


def _scan(patterns: tuple[re.Pattern[str], ...], text: str) -> list[str]:
    """Run patterns against text; return list of matched substrings
    (verbatim from the text) for the evidence field."""

    matches: list[str] = []
    for pat in patterns:
        for m in pat.finditer(text):
            snippet = m.group(0).strip()
            if snippet and snippet not in matches:
                matches.append(snippet)
    return matches


def _detect_language(
    text: str,
    *,
    native_patterns: tuple[re.Pattern[str], ...],
    c1_patterns: tuple[re.Pattern[str], ...],
    b2_patterns: tuple[re.Pattern[str], ...],
    b1_patterns: tuple[re.Pattern[str], ...],
    required_no_level_patterns: tuple[re.Pattern[str], ...] = (),
) -> tuple[str, list[str]]:
    """Internal helper: walk the pattern ladder from highest level
    down to lowest, returning the first level matched + its
    evidence. Higher-level matches win — a JD that says
    "verhandlungssicher (C1+) but at least B1" requires C1+, not
    B1."""

    native_ev = _scan(native_patterns, text)
    if native_ev:
        return "native", native_ev
    c1_ev = _scan(c1_patterns, text)
    if c1_ev:
        return "C1+", c1_ev
    b2_ev = _scan(b2_patterns, text)
    if b2_ev:
        return "B2+", b2_ev
    b1_ev = _scan(b1_patterns, text)
    if b1_ev:
        return "B1+", b1_ev
    if required_no_level_patterns:
        req_ev = _scan(required_no_level_patterns, text)
        if req_ev:
            # No level specified — DACH market convention is B2+
            # for unscoped "Deutsch erforderlich". Documented in
            # company_discovery/language_requirement.py docstring.
            return "B2+", req_ev
    return "", []


def detect_language_requirement(description: str | None) -> LanguageRequirement:
    """Inspect a job description and return the detected language
    requirement (language + level + evidence + confidence).

    Deterministic, regex-based, offline. Returns a silent
    ``LanguageRequirement`` when no signal is found — better to be
    silent than to guess.

    Algorithm:
    - Run DE patterns top-down (native → C1+ → B2+ → B1+ → unscoped)
    - Run EN patterns top-down (native → C1+ → B2+ → B1+)
    - If both DE and EN match, surface BOTH (some JDs require both
      languages — common in DACH international roles). The "primary"
      language is the higher-level one.
    """

    if not description:
        return LanguageRequirement()

    text = description

    de_level, de_evidence = _detect_language(
        text,
        native_patterns=_DE_NATIVE_PATTERNS,
        c1_patterns=_DE_C1_PATTERNS,
        b2_patterns=_DE_B2_PATTERNS,
        b1_patterns=_DE_B1_PATTERNS,
        required_no_level_patterns=_DE_REQUIRED_NO_LEVEL_PATTERNS,
    )
    en_level, en_evidence = _detect_language(
        text,
        native_patterns=_EN_NATIVE_PATTERNS,
        c1_patterns=_EN_C1_PATTERNS,
        b2_patterns=_EN_B2_PATTERNS,
        b1_patterns=_EN_B1_PATTERNS,
    )

    # Decide primary language: the one with the highest level. Ties
    # are broken by preferring DE when the description has a DACH
    # focus (which we approximate by "more DE evidence than EN
    # evidence"); otherwise EN.
    if not de_level and not en_level:
        return LanguageRequirement()

    if de_level and not en_level:
        primary_language = "de"
        primary_level = de_level
        evidence = list(de_evidence)
    elif en_level and not de_level:
        primary_language = "en"
        primary_level = en_level
        evidence = list(en_evidence)
    else:
        # Both languages have a level — surface as bilingual. The
        # primary is the higher-level one; the secondary is
        # captured in evidence with a "+ EN: ..." prefix so the
        # user sees both signals.
        de_rank = LEVEL_ORDER.index(de_level)
        en_rank = LEVEL_ORDER.index(en_level)
        if de_rank >= en_rank:
            primary_language = "de"
            primary_level = de_level
            evidence = list(de_evidence) + [
                f"+ EN: {ev}" for ev in en_evidence
            ]
        else:
            primary_language = "en"
            primary_level = en_level
            evidence = list(en_evidence) + [
                f"+ DE: {ev}" for ev in de_evidence
            ]

    # Confidence: "high" if 2+ pieces of evidence at the matched
    # level; "medium" if 1 piece + the level is C1+ or higher (more
    # specific signals); "low" otherwise.
    high_levels = {"native", "C1+", "C2+"}
    if len(evidence) >= 2:
        confidence = "high"
    elif primary_level in high_levels:
        confidence = "medium"
    else:
        confidence = "low"

    return LanguageRequirement(
        language=primary_language,
        level=primary_level,
        evidence=evidence,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Post-fetch annotator
# ---------------------------------------------------------------------------


def annotate_jobs_with_language_requirement(
    jobs: list[Any],
) -> list[Any]:
    """Loop through aggregator jobs, detect each one's language
    requirement, and stamp the structured result onto
    ``job.raw["languageRequirement"]``.

    Mutates jobs in place AND returns the same list for fluent
    chaining. Resilient: a malformed job (missing description /
    missing raw) is left unchanged rather than raising.

    Caller responsibility: this annotator does not filter — it
    annotates. The journey's ``loosen_language`` widening
    affordance reads ``raw["languageRequirement"]`` to decide
    whether to include / exclude a posting.
    """

    for job in jobs:
        try:
            description = getattr(job, "description", None) or ""
            requirement = detect_language_requirement(description)
            if requirement.is_silent():
                continue
            # Ensure job.raw exists; some aggregators leave it None.
            raw = getattr(job, "raw", None)
            if raw is None:
                # Skip jobs we can't annotate (no place to store the
                # result). Better than re-shaping the aggregator's
                # job type.
                continue
            if not isinstance(raw, dict):
                continue
            raw["languageRequirement"] = requirement.to_dict()
        except Exception:  # noqa: BLE001 - annotation must never break the pipeline
            continue
    return jobs


# ---------------------------------------------------------------------------
# Filter helpers — power the loosen_language widening affordance
# ---------------------------------------------------------------------------


def level_at_or_above(detected_level: str, user_level: str) -> bool:
    """True iff ``detected_level`` is achievable by a user with
    ``user_level``. Both arguments use the LEVEL_ORDER ladder.

    Example: user has "B2+", detected is "B1+" → True (user
    over-qualified). User has "B1+", detected is "C1+" → False
    (user under-qualified).

    Unscoped ("") detected requirement always returns True (no
    barrier). Unscoped user level returns False (cannot prove
    capability)."""

    if not user_level:
        return False
    if not detected_level:
        return True
    if detected_level not in LEVEL_ORDER or user_level not in LEVEL_ORDER:
        return False
    return LEVEL_ORDER.index(user_level) >= LEVEL_ORDER.index(detected_level)
