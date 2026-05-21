# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Friction-class classifier — Phase 1 best-guess.

Maps a candidate's CV text to one of the seven persona-fixture
slugs (``aicha``, ``yusuf``, ``olga``, ``mahmoud``, ``maria``,
``kaethe``, ``tobias``) or to the empty string when no
classification is confident enough. Output drives:

- Bug C piece-3's persona-aware widening order + Ausländerbehörde
  caveat (via journey.visa_constrained, set by app.py from the
  resolved fixture's residency_status)
- analysis.py's AI-prompt friction context (residency status,
  friction notes, fixture scenarios)

Patterns are seeded from ``persona_fixtures.friction_keywords_for``
plus a small set of regulatory / institutional citations drawn
from the German labor-market context the personas inhabit. The two
sources serve different purposes — the friction_keywords bank was
designed for "what should appear in a well-tailored CV OUTPUT",
not "what signals classify a real-user CV INPUT" — so the
classifier defines its own pattern set, drawing from but not
literally importing the bank.

REAL USERS MAY NOT WRITE PRECISE REGULATORY CITATIONS. A real
Aïcha-class user might just type "nursing degree from Tunisia,
recognition process underway" without ever writing "§16d" or
"Anerkennungsgesetz." That is why scored-fallback exists: strong-
markers catch the obvious / explicit cases (where the user IS
fluent in the institutional vocabulary), and scored handles
muddier multi-signal cases ("Anerkennung" + "Krankenpflege" +
"Tunisia" → aicha-soft).

Classification accuracy in production depends on how closely
real-user CV vocabulary aligns with the seeded patterns. Phase 2
refines patterns based on telemetry (Phase 2 backlog #76 — user-
confirmation flow + advanced edge-case handling).

Public API:

    classify(cv_text: str) -> str
        Returns the fixture slug or "" when unclassified.

    classify_with_telemetry(cv_text: str) -> ClassificationResult
        Returns slug + confidence-class + match-count for logging.
        Loop 10.2 hook calls this; the caller writes one analytics
        log line per classification call (see OQ-2 verdict).

Determinism: pure function, deterministic substring match, tie-
break by alphabetical persona slug. Pinned by a regression test.
"""
from __future__ import annotations

from dataclasses import dataclass


# ─── Phase 1 pattern tables ──────────────────────────────────────

# Strong markers — single hit wins for the matching persona.
# Tie-break (CV contains markers from multiple personas) is by
# alphabetical persona slug (operator Q-D verdict).
STRONG_MARKERS: dict[str, tuple[str, ...]] = {
    # Aïcha (Tunisia → Berlin, §16d Anerkennung path)
    "aicha": (
        "§16d",
        "Anerkennungsgesetz",
        "BIBB",
        "Anabin",
    ),
    # Yusuf (Turkey → Munich, EU Blue Card / §18b)
    "yusuf": (
        "Blue Card",
        "Blaue Karte",
        "EU Blue Card",
        "§18b",
    ),
    # Olga (Ukraine → Berlin, §24 mass-influx temporary protection)
    "olga": (
        "§24",
        "Sonderaufenthalt",
    ),
    # Mahmoud (Syria → Frankfurt, §4 AsylG subsidiary protection)
    "mahmoud": (
        "§4 AsylG",
        "subsidiärer Schutz",
        "subsidiary protection",
        "Asylanerkennung",
        "Ausbildungsduldung",
    ),
    # Maria (Spain → Hamburg, EU citizen Freizügigkeitsrecht)
    "maria": (
        "EU-Bürger",
        "EU citizen",
        "Freizügigkeitsrecht",
    ),
    # Käthe (Germany → Leipzig, Wiedereinstieg / re-entry)
    "kaethe": (
        "Wiedereinstieg",
        "Berufsrückkehr",
        "Familienpause",
    ),
    # Tobias (Germany → Frankfurt, Quereinstieg / former banker)
    "tobias": (
        "TVöD",
        "Civic Tech",
        "Sovereign Tech",
        "GovTech",
        "Quereinsteiger",
        "Quereinstieg",
    ),
}

# Scored patterns — multi-signal soft markers; require ≥ 2 hits
# from this persona's list to fire. Lower confidence than strong-
# match. Ties broken by alphabetical persona slug.
SCORED_PATTERNS: dict[str, tuple[str, ...]] = {
    "aicha": (
        "Anerkennung",
        "Krankenpflege",
        "Krankenpfleger",
        "Krankenschwester",
        "Pflegefachkraft",
        "Tunisia",
        "Tunis",
        "geriatric",
        "Geriatrie",
        "Altenpflege",
    ),
    "yusuf": (
        "Bursa",
        "automotive",
        "Tier-2",
        "ITÜ",
        "ISO 9001",
        "CATIA",
        "SolidWorks",
        "Anmeldung",
    ),
    "olga": (
        "DevOps",
        "Kubernetes",
        "remote",
        "English-speaking",
        "English team",
        "Ukraine",
        "Kyiv",
    ),
    "mahmoud": (
        "Ausbildung",
        "Bewerbungsmappe",
        "Handwerk",
        "Syria",
        "Lagerhelfer",
        "Lagerarbeit",
    ),
    "maria": (
        "Spain",
        "Spanish",
        "Bartender",
        "hospitality",
        "Sprachpate",
    ),
    "kaethe": (
        "Auffrischung",
        "returning",
        "re-entry",
        "Krankenschwester",
        "Krankenpflege",
    ),
    "tobias": (
        # NOTE: Quereinstieg / Quereinsteiger live in STRONG_MARKERS;
        # don't duplicate here -- the strong path short-circuits
        # before scored.
        "banker",
        "banking",
        "Former banker",
        "career change",
    ),
}

# Minimum scored-match count required to emit a scored
# classification. Below this threshold, classify returns "".
SCORED_MIN_HITS = 2


# ─── Public slug → human-readable label map ─────────────────────
#
# Used by the chat UX (Phase 2 #76 sub-piece a — user-confirmation
# flow at classification time) and the Settings page (#76 sub-piece d
# — read-only display). The labels are operator-curated and follow
# the project's translation convention: German bureaucratic terms
# (§16d AufenthG, EU Blue Card, Anerkennungsweg, Wiedereinstieg,
# Quereinstieg) stay verbatim regardless of UI locale.

FRICTION_CLASS_LABELS: dict[str, str] = {
    "aicha": "§16d Anerkennungsweg (regulated profession, migrant)",
    "yusuf": "EU Blue Card (high-skilled migrant, portable across EU)",
    "olga": "§24 humanitarian protection (Ukrainian temp protection)",
    "mahmoud": "§4 AsylG (asylum, work permit)",
    "maria": "EU citizen (no visa constraint)",
    "kaethe": "Wiedereinstieg (returning after career break)",
    "tobias": "Quereinstieg (career changer, native-DACH)",
}


def label_for(slug: str) -> str:
    """Return a human-readable label for a friction-class slug, or
    an empty string for unknown / empty slugs."""

    return FRICTION_CLASS_LABELS.get(slug, "")


def all_labels() -> list[tuple[str, str]]:
    """Return the (slug, label) pairs for all known friction classes.
    Useful for rendering the 7-option pick list in the chat confirmation
    flow + the Settings card. Order is stable (alphabetical by slug,
    matching the classifier's tie-break order)."""

    return [(slug, FRICTION_CLASS_LABELS[slug]) for slug in sorted(FRICTION_CLASS_LABELS)]


# Phase 2 #76 sub-piece (b): persona-vs-friction-class mismatch
# reconciliation. Each friction-class slug carries a typical
# industry profile derived from the persona-fixture context
# (Aïcha + Maria are healthcare; Yusuf + Olga + Tobias are
# engineering / tech; Mahmoud is trade / construction; Käthe
# is broad because Wiedereinsteigerinnen come from many sectors).
# When a user's persona_id implies a different industry than their
# friction-class, the chat / Settings surface a soft hint inviting
# reconciliation. The tokens here match the persona registry's
# industry_match_terms convention.

_FRICTION_CLASS_INDUSTRY_TOKENS: dict[str, tuple[str, ...]] = {
    "aicha": ("health", "gesund", "klinik", "pflege", "krankenhaus", "med"),
    "maria": ("pflege", "altenpflege", "betreuung", "care", "health", "gesund"),
    "yusuf": ("engineering", "mechanical", "industrial", "manufacturing", "auto"),
    "olga": ("tech", "software", "saas", "frontend", "developer", "engineer"),
    "tobias": ("trade", "handwerk", "shk", "anlagen", "tech", "engineer", "construction"),
    "mahmoud": ("trade", "handwerk", "shk", "anlagen", "construction", "bau"),
    # Käthe = Wiedereinstieg returner. Sector is whatever she was in
    # before the break — too broad to constrain. Empty tokens =
    # never flagged as a mismatch.
    "kaethe": (),
}


def expected_industry_tokens_for(slug: str) -> tuple[str, ...]:
    """Return the typical-industry tokens for a friction-class slug.
    Empty tuple when the class is industry-broad (Käthe Wiedereinstieg)
    or unknown — callers treat that as "no constraint" rather than
    "no industry"."""

    return _FRICTION_CLASS_INDUSTRY_TOKENS.get(slug, ())


def reconcile_persona_and_friction_class(
    *, persona_industry_terms: tuple[str, ...] | list[str], friction_slug: str
) -> str:
    """Soft reconciliation hint: returns a user-facing message when
    the persona's typical industry doesn't overlap with the
    friction-class's typical industry, otherwise "".

    Empty when:
    - friction_slug is "" or unknown
    - friction-class has no industry constraint (Käthe Wiedereinstieg)
    - persona_industry_terms is empty (no persona industry signal)
    - persona_industry_terms overlaps with friction-class expected
      tokens (full or partial token-set overlap = aligned)

    The hint is *soft* (suggests reconciliation, doesn't block) because
    a user genuinely can be a Wiedereinsteigerin moving from healthcare
    to tech, or an Aïcha-pattern nurse seeking a marketing role — both
    are legitimate trajectories. The system surfaces the mismatch so
    the user can confirm, override, or update their persona/CV.
    """

    if not friction_slug:
        return ""
    expected = expected_industry_tokens_for(friction_slug)
    if not expected:
        return ""  # industry-broad class — no constraint
    persona_terms = tuple(t.casefold() for t in persona_industry_terms or ())
    if not persona_terms:
        return ""  # no persona signal — can't reconcile
    expected_cf = {t.casefold() for t in expected}
    persona_cf = set(persona_terms)
    if expected_cf & persona_cf:
        return ""  # aligned
    # Mismatch — return a hint.
    label = label_for(friction_slug) or friction_slug
    expected_summary = ", ".join(expected[:4])
    persona_summary = ", ".join(persona_terms[:3])
    return (
        f"Your friction-class is **{label}** (typically: "
        f"{expected_summary}), but your persona is tuned for "
        f"**{persona_summary}**. These are legitimate trajectories "
        f"(e.g. Wiedereinstieg into a different sector) — but if "
        f"this is unexpected, re-classify from your latest CV "
        f"(Settings → Friction-class) or change your persona "
        f"(Settings → Persona & profile)."
    )


# ─── Output dataclass ────────────────────────────────────────────


@dataclass(frozen=True)
class ClassificationResult:
    """Return shape of classify_with_telemetry.

    ``slug``        — fixture slug ("aicha" / ... / "tobias") or "".
    ``confidence``  — "strong" / "scored" / "none".
    ``match_count`` — count of pattern hits that drove the result.
                       For "strong" always 1 (single-marker wins);
                       for "scored" the actual hit count; for
                       "none" always 0.
    ``tied_slugs``  — Phase 2 #76 sub-piece (b): other slugs that
                       scored equally to the winner. Empty tuple
                       when there's a unique winner (the common
                       case). Non-empty when the scored fallback
                       had multiple slugs at the same max count;
                       the algorithm picks alphabetically first
                       (operator-spec deterministic), but the
                       chat UX surfaces the alternatives so the
                       user can override via the change flow.
                       Always empty for "strong" + "none" results.
    """

    slug: str
    confidence: str
    match_count: int
    tied_slugs: tuple[str, ...] = ()


# ─── Public API ──────────────────────────────────────────────────


def classify(cv_text: str) -> str:
    """Map CV text to a fixture slug or "" (no confident match).

    Public-facing convenience wrapper around
    ``classify_with_telemetry`` — drops the telemetry payload."""
    return classify_with_telemetry(cv_text).slug


def classify_with_telemetry(cv_text: str) -> ClassificationResult:
    """Map CV text to a fixture slug + confidence + match count.

    The Loop 10.2 cv_check classification hook calls this and
    writes a single ``log.info("friction_class_classified", ...)``
    line per call (OQ-2 verdict).

    Algorithm (deterministic):
      1. Case-fold both text and patterns.
      2. STRONG_MARKERS: iterate sorted-by-slug. First slug whose
         any marker substring-matches → return slug + "strong" +
         match_count=1.
      3. SCORED_PATTERNS: count substring hits per slug. Slugs
         with count >= SCORED_MIN_HITS qualify. Highest count
         wins; ties broken alphabetically. Return slug + "scored"
         + match_count.
      4. Otherwise: return "" + "none" + 0.
    """
    if not cv_text or not cv_text.strip():
        return ClassificationResult(slug="", confidence="none", match_count=0)

    text_lower = cv_text.casefold()

    # Strong markers — single hit wins; alphabetical-slug tie-break
    # via sorted iteration.
    for slug in sorted(STRONG_MARKERS.keys()):
        for marker in STRONG_MARKERS[slug]:
            if marker.casefold() in text_lower:
                return ClassificationResult(
                    slug=slug, confidence="strong", match_count=1,
                )

    # Scored fallback — multi-signal soft match.
    scored: dict[str, int] = {}
    for slug in sorted(SCORED_PATTERNS.keys()):
        count = sum(
            1 for p in SCORED_PATTERNS[slug] if p.casefold() in text_lower
        )
        if count >= SCORED_MIN_HITS:
            scored[slug] = count

    if not scored:
        return ClassificationResult(slug="", confidence="none", match_count=0)

    # Highest count wins; alphabetical tie-break.
    max_count = max(scored.values())
    winners = sorted(
        slug for slug, count in scored.items() if count == max_count
    )
    # Phase 2 #76 sub-piece (b): surface the tied alternatives so the
    # chat UX can mention them ("you might also be in Y") and let the
    # user override via the change flow. Tied list excludes the
    # winning slug itself.
    tied = tuple(winners[1:])
    return ClassificationResult(
        slug=winners[0],
        confidence="scored",
        match_count=max_count,
        tied_slugs=tied,
    )
