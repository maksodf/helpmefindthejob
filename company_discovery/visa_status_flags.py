# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Post-fetch visa-status flag detection (phase2-backlog #73).

Complements ``language_requirement.py`` (#72): #72 detects what
language LEVEL a JD requires; this module detects which
visa-status / migration-pathway flags the JD carries. Together
they power the empty-state widening affordances in PART 6 Bug C
piece 3 (``loosen_language`` + ``loosen_visa_status``) — both
currently theatrical because the aggregator layer has no
structured field for either signal.

The flag taxonomy mirrors the friction-class system from
``friction_classifier.py`` (which classifies the USER'S CV into
one of seven friction classes) — this module classifies the
JOB POSTING'S accommodations along the same axes. The two
pair up:

- User has friction class `aicha` (§16d Anerkennung) AND
  JD carries `anerkennung_friendly` flag → strong match
- User has friction class `yusuf` (Blue Card) AND
  JD carries `eu_citizens_only` flag → hard mismatch

The doctrine constraint from #73: evidence-backed detection.
Every detected flag carries the matched substring verbatim so a
user can verify. Silent (no flags) is the default — better than
guessing.

Deterministic, regex-based, offline. No AI dependency. Resilient
to malformed input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Flag identifiers. These are the canonical machine-readable
# slugs; UI labels live in FLAG_LABELS below. Stable strings —
# downstream consumers (loosen_visa_status affordance, JobIndex
# facets) depend on these.

FLAG_ANERKENNUNG_FRIENDLY = "anerkennung_friendly"
FLAG_BLUE_CARD_OK = "blue_card_ok"
FLAG_WIEDEREINSTIEG_FRIENDLY = "wiedereinstieg_friendly"
FLAG_AUSBILDUNG_CLASS = "ausbildung_class"
FLAG_PARAGRAPH_16D = "paragraph_16d_recognised"
FLAG_HUMANITARIAN_PATHWAY = "humanitarian_pathway_recognised"
FLAG_EU_CITIZENS_ONLY = "eu_citizens_only"
FLAG_PERMANENT_RESIDENCE_REQUIRED = "permanent_residence_required"

# All known flags. Drift guard: if you add a new flag, also add
# its label below + a pattern set + extend the test suite.
ALL_FLAGS: tuple[str, ...] = (
    FLAG_ANERKENNUNG_FRIENDLY,
    FLAG_BLUE_CARD_OK,
    FLAG_WIEDEREINSTIEG_FRIENDLY,
    FLAG_AUSBILDUNG_CLASS,
    FLAG_PARAGRAPH_16D,
    FLAG_HUMANITARIAN_PATHWAY,
    FLAG_EU_CITIZENS_ONLY,
    FLAG_PERMANENT_RESIDENCE_REQUIRED,
)

# Positive flags signal accommodation (good for migrant users).
# Negative flags signal barrier (bad for migrant users; useful
# input to the loosen_visa_status widening logic — these are the
# flags the user might want to ignore if they're under-qualified).
POSITIVE_FLAGS: frozenset[str] = frozenset({
    FLAG_ANERKENNUNG_FRIENDLY,
    FLAG_BLUE_CARD_OK,
    FLAG_WIEDEREINSTIEG_FRIENDLY,
    FLAG_AUSBILDUNG_CLASS,
    FLAG_PARAGRAPH_16D,
    FLAG_HUMANITARIAN_PATHWAY,
})
NEGATIVE_FLAGS: frozenset[str] = frozenset({
    FLAG_EU_CITIZENS_ONLY,
    FLAG_PERMANENT_RESIDENCE_REQUIRED,
})

# Human-readable labels for UI rendering. EN-first; DE versions
# live in the i18n bundles per project convention.
FLAG_LABELS: dict[str, str] = {
    FLAG_ANERKENNUNG_FRIENDLY: "Anerkennung-friendly",
    FLAG_BLUE_CARD_OK: "EU Blue Card eligible",
    FLAG_WIEDEREINSTIEG_FRIENDLY: "Wiedereinstieg-welcoming",
    FLAG_AUSBILDUNG_CLASS: "Ausbildung (trainee position)",
    FLAG_PARAGRAPH_16D: "§16d AufenthG recognised",
    FLAG_HUMANITARIAN_PATHWAY: "Humanitarian-pathway recognised (§24/§4)",
    FLAG_EU_CITIZENS_ONLY: "EU citizens only",
    FLAG_PERMANENT_RESIDENCE_REQUIRED: "Permanent residence required",
}


@dataclass(frozen=True)
class VisaStatusFlag:
    """One detected flag with the substring(s) that triggered it.

    ``slug`` is one of ALL_FLAGS. ``evidence`` carries the matched
    phrases verbatim from the source description so a user can
    verify the inference (doctrine constraint).
    """

    slug: str
    evidence: list[str] = field(default_factory=list)

    def is_positive(self) -> bool:
        return self.slug in POSITIVE_FLAGS

    def is_negative(self) -> bool:
        return self.slug in NEGATIVE_FLAGS

    def label(self) -> str:
        return FLAG_LABELS.get(self.slug, self.slug)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "label": self.label(),
            "evidence": list(self.evidence),
            "polarity": "positive" if self.is_positive() else (
                "negative" if self.is_negative() else "neutral"
            ),
        }


# ---------------------------------------------------------------------------
# Pattern catalogues
# ---------------------------------------------------------------------------

# Anerkennung-friendly: JD explicitly supports the recognition
# process for non-EU professional qualifications (§16d AufenthG /
# Berufsanerkennung etc.).
_ANERKENNUNG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\banerkennung(?:s)?\s*[-\s]?(?:freundlich|friendly|partner)\b", re.IGNORECASE),
    re.compile(r"\bsupports?\s+anerkennung\b", re.IGNORECASE),
    re.compile(r"\bberufsanerkennung\s+(?:unterstützt|wird unterstützt|gefördert)\b", re.IGNORECASE),
    re.compile(r"\banerkennung\s+läuft\b", re.IGNORECASE),
    re.compile(r"\bin\s+anerkennung(?:sverfahren)?\b", re.IGNORECASE),
    re.compile(r"\banpassungslehrgang\b", re.IGNORECASE),
    re.compile(r"\bkenntnisprüfung\s+(?:unterstützt|gefördert)\b", re.IGNORECASE),
)

# EU Blue Card patterns
_BLUE_CARD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bblue[\s-]card\b", re.IGNORECASE),
    # German "Blaue/Blauen/Blauer Karte" — German adjective endings
    # ("Blauen Karte EU" appears in dative case).
    re.compile(r"\bblaue[rn]?\s+karte\b", re.IGNORECASE),
    # §18b AufenthG — section symbol is not a word character, so
    # \b before § doesn't anchor. Use lookahead+lookbehind for
    # whitespace/start instead.
    re.compile(r"(?:^|\s)§\s*18b(?:\s+aufenthG?)?\b", re.IGNORECASE),
    re.compile(r"\beu[\s-]?blue[\s-]?card\b", re.IGNORECASE),
)

# Wiedereinstieg (returning to work after career break)
_WIEDEREINSTIEG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwiedereinstieg\b", re.IGNORECASE),
    re.compile(r"\bwiedereinsteiger(?:in(?:nen)?)?\b", re.IGNORECASE),
    re.compile(r"\bberufliche?r?\s+wiedereinstieg\b", re.IGNORECASE),
    re.compile(r"\bcareer[\s-]?return(?:er|ers|ing)\b", re.IGNORECASE),
    re.compile(r"\bafter\s+(?:a\s+)?career\s+break\b", re.IGNORECASE),
    re.compile(r"\bnach\s+der\s+(?:eltern|familien)zeit\b", re.IGNORECASE),
    re.compile(r"\breturning\s+(?:after|to)\s+(?:parental|career|family)\b", re.IGNORECASE),
)

# Ausbildung (trainee position)
_AUSBILDUNG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bausbildung\s+(?:zum|zur)\b", re.IGNORECASE),
    re.compile(r"\bauszubildende(?:r|n)?\b", re.IGNORECASE),
    re.compile(r"\bausbildungsplatz\b", re.IGNORECASE),
    re.compile(r"\bduale?\s+ausbildung\b", re.IGNORECASE),
    # English equivalents
    re.compile(r"\bapprenticeship\b", re.IGNORECASE),
    re.compile(r"\btrainee(?:ship)?\s+(?:program(?:me)?|position)\b", re.IGNORECASE),
)

# §16d AufenthG (specific German residence-permit class for
# recognition-process residents)
_PARAGRAPH_16D_PATTERNS: tuple[re.Pattern[str], ...] = (
    # §16d / § 16d — anchor on whitespace/start instead of \b
    # because § isn't a word character.
    re.compile(r"(?:^|\s)§\s*16d\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)§\s*16d\s+aufenthG?\b", re.IGNORECASE),
    re.compile(r"\bsixteen[\s-]d\s+aufenthG?\b", re.IGNORECASE),
)

# Humanitarian pathway (§24 — Ukrainian temp protection; §4 AsylG
# — asylum)
_HUMANITARIAN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|\s)§\s*24\s+(?:aufenthG?|aufenthaltsgesetz)\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)§\s*4\s+(?:asylG?|asylgesetz)\b", re.IGNORECASE),
    re.compile(r"\btemporary\s+protection\b", re.IGNORECASE),
    re.compile(r"\bvorübergehender\s+schutz\b", re.IGNORECASE),
    re.compile(r"\basyl(?:bewerber|berechtigte|suchende)\b", re.IGNORECASE),
    re.compile(r"\bgeflüchtete\b", re.IGNORECASE),
    re.compile(r"\bukrainian\s+(?:refugees?|protection)\b", re.IGNORECASE),
)

# Negative flag — EU citizens only
_EU_CITIZENS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\beu\s+citizens?\s+only\b", re.IGNORECASE),
    re.compile(r"\bonly\s+eu\s+citizens?\b", re.IGNORECASE),
    re.compile(r"\beu\s+nationals?\s+only\b", re.IGNORECASE),
    re.compile(r"\bnur\s+für\s+eu[-\s]bürger\b", re.IGNORECASE),
    re.compile(r"\beu[-\s]staatsangehörigkeit\s+(?:erforderlich|required)\b", re.IGNORECASE),
)

# Negative flag — permanent residence required
_PERMANENT_RESIDENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # The stem is "residen" — branches: "resident" (no suffix) /
    # "residency" / "residence" / "residentship". A naive
    # `resident(?:cy)?` fails on "residency" because the literal
    # `t` isn't in that word ("residency" = r-e-s-i-d-e-n-c-y).
    re.compile(
        r"\bpermanent\s+residen(?:t|tship|cy|ce)\s+(?:required|necessary|essential)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bniederlassungserlaubnis\s+(?:erforderlich|required|vorausgesetzt)\b", re.IGNORECASE),
    re.compile(r"\bunbefristeter?\s+aufenthaltstitel\s+(?:erforderlich|notwendig)\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)§\s*9\s+(?:aufenthG?|aufenthaltsgesetz)\s+(?:erforderlich|required)\b", re.IGNORECASE),
)


# Map each flag slug to its pattern catalogue + the polarity-aware
# minimum signal threshold (positive flags require 1+ match;
# negative flags also require 1+ but the user impact is different).
_FLAG_TO_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    FLAG_ANERKENNUNG_FRIENDLY: _ANERKENNUNG_PATTERNS,
    FLAG_BLUE_CARD_OK: _BLUE_CARD_PATTERNS,
    FLAG_WIEDEREINSTIEG_FRIENDLY: _WIEDEREINSTIEG_PATTERNS,
    FLAG_AUSBILDUNG_CLASS: _AUSBILDUNG_PATTERNS,
    FLAG_PARAGRAPH_16D: _PARAGRAPH_16D_PATTERNS,
    FLAG_HUMANITARIAN_PATHWAY: _HUMANITARIAN_PATTERNS,
    FLAG_EU_CITIZENS_ONLY: _EU_CITIZENS_PATTERNS,
    FLAG_PERMANENT_RESIDENCE_REQUIRED: _PERMANENT_RESIDENCE_PATTERNS,
}


def _scan(patterns: tuple[re.Pattern[str], ...], text: str) -> list[str]:
    matches: list[str] = []
    for pat in patterns:
        for m in pat.finditer(text):
            snippet = m.group(0).strip()
            if snippet and snippet not in matches:
                matches.append(snippet)
    return matches


def detect_visa_status_flags(description: str | None) -> list[VisaStatusFlag]:
    """Inspect a job description and return all detected
    visa-status flags. Each result carries the evidence (matched
    substring) per the doctrine constraint.

    Returns an empty list when the description is empty / silent.
    Multiple flags can coexist on one posting (e.g., a JD might
    be both `anerkennung_friendly` AND `paragraph_16d_recognised`)
    — both surface. The ordering of the returned list follows
    ALL_FLAGS for determinism.
    """

    if not description:
        return []

    flags: list[VisaStatusFlag] = []
    for slug in ALL_FLAGS:
        evidence = _scan(_FLAG_TO_PATTERNS[slug], description)
        if evidence:
            flags.append(VisaStatusFlag(slug=slug, evidence=evidence))
    return flags


# ---------------------------------------------------------------------------
# Post-fetch annotator
# ---------------------------------------------------------------------------


def annotate_jobs_with_visa_status_flags(jobs: list[Any]) -> list[Any]:
    """Loop through aggregator jobs, detect flags, and stamp the
    structured list onto ``job.raw["visaStatusFlags"]``.

    Mutates jobs in place AND returns the same list for fluent
    chaining. Resilient: a malformed job (no description / no raw
    dict) is left unchanged.

    Caller responsibility: the journey's ``loosen_visa_status``
    widening affordance reads this list to decide which postings
    to include / exclude when widening for the user.
    """

    for job in jobs:
        try:
            description = getattr(job, "description", None) or ""
            flags = detect_visa_status_flags(description)
            if not flags:
                continue
            raw = getattr(job, "raw", None)
            if raw is None or not isinstance(raw, dict):
                continue
            raw["visaStatusFlags"] = [f.to_dict() for f in flags]
        except Exception:  # noqa: BLE001 - annotation must never break the pipeline
            continue
    return jobs


# ---------------------------------------------------------------------------
# Friction-class compatibility — pairs with friction_classifier
# ---------------------------------------------------------------------------


# Which JD flags are STRONG MATCHES for each user friction class.
# Drives the future loosen_visa_status widening affordance: when
# searching for user X, prefer postings carrying the flags in
# their row; allow widening to postings without those flags.
FRICTION_CLASS_PREFERRED_FLAGS: dict[str, frozenset[str]] = {
    # Aïcha — §16d Anerkennungsweg
    "aicha": frozenset({
        FLAG_ANERKENNUNG_FRIENDLY,
        FLAG_PARAGRAPH_16D,
    }),
    # Yusuf — EU Blue Card
    "yusuf": frozenset({
        FLAG_BLUE_CARD_OK,
    }),
    # Olga — §24 Ukrainian temporary protection
    "olga": frozenset({
        FLAG_HUMANITARIAN_PATHWAY,
        FLAG_ANERKENNUNG_FRIENDLY,
    }),
    # Mahmoud — §4 AsylG
    "mahmoud": frozenset({
        FLAG_HUMANITARIAN_PATHWAY,
        FLAG_AUSBILDUNG_CLASS,
    }),
    # Maria — EU citizen (no visa constraint; broad)
    "maria": frozenset(),  # no preferred flags — Maria has no visa friction
    # Käthe — Wiedereinstieg
    "kaethe": frozenset({
        FLAG_WIEDEREINSTIEG_FRIENDLY,
    }),
    # Tobias — Quereinstieg (native-DACH career changer; no visa)
    "tobias": frozenset({
        FLAG_AUSBILDUNG_CLASS,  # career-change roles often Ausbildung-class
    }),
}


# Which JD flags are HARD BARRIERS for each user friction class.
FRICTION_CLASS_BARRIER_FLAGS: dict[str, frozenset[str]] = {
    "aicha": frozenset({FLAG_EU_CITIZENS_ONLY, FLAG_PERMANENT_RESIDENCE_REQUIRED}),
    "yusuf": frozenset({FLAG_EU_CITIZENS_ONLY}),
    "olga": frozenset({FLAG_EU_CITIZENS_ONLY, FLAG_PERMANENT_RESIDENCE_REQUIRED}),
    "mahmoud": frozenset({FLAG_EU_CITIZENS_ONLY, FLAG_PERMANENT_RESIDENCE_REQUIRED}),
    "maria": frozenset(),  # Maria's an EU citizen
    "kaethe": frozenset(),  # German citizen
    "tobias": frozenset(),  # German citizen
}


def has_barrier_for_class(
    flags: list[VisaStatusFlag], friction_class_slug: str
) -> bool:
    """True iff the detected flags include any HARD BARRIER for
    the given friction class. Used by the journey's widening
    logic: if `has_barrier_for_class(flags, user.class) == True`,
    the posting is excluded from default results and only
    surfaces when the user opts in to widening."""

    barriers = FRICTION_CLASS_BARRIER_FLAGS.get(friction_class_slug, frozenset())
    if not barriers:
        return False
    detected_slugs = {f.slug for f in flags}
    return bool(detected_slugs & barriers)


def matches_preferred_for_class(
    flags: list[VisaStatusFlag], friction_class_slug: str
) -> bool:
    """True iff the detected flags include any PREFERRED match
    for the friction class. Used by the journey's ranking logic
    to surface stronger matches first."""

    preferred = FRICTION_CLASS_PREFERRED_FLAGS.get(friction_class_slug, frozenset())
    if not preferred:
        return False
    detected_slugs = {f.slug for f in flags}
    return bool(detected_slugs & preferred)
