# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PART 6 Bug C piece 3 — persona-aware manual widening affordances.

Sibling to ``diagnostic_engine.py``: the diagnostic engine is the
read-side honesty layer (cache-only counts → strict-fact prose);
this module is the write-side, deterministic affordance generator
+ applier (offers widenings, applies them to journey state, emits
``run_search_with`` for the aggregator dispatch).

DOCTRINE (operator spec 2026-05-20):
  - 3 honest affordances shipped: widen location, drop seniority,
    try lateral roles. Each maps to a real change in the
    aggregator query (verified against provider .search()
    signatures + AggregatedJob fields).
  - 2 theatrical affordances OMITTED: loosen language requirement,
    loosen visa-status preference. The aggregator layer has no
    language or visa-status filter at any provider. Shipping them
    would be theatrical — selecting them would change nothing in
    the actual search. Phase 2 backlog #72 (post-fetch language
    detection) + #73 (post-fetch visa-flag annotation) capture the
    real work.
  - Persona-aware ordering: visa-constrained personas (Aïcha §16d
    / Olga §24 / Mahmoud §4 AsylG) see safer widenings first +
    explicit Ausländerbehörde caveat on the location-widening
    affordance. Unconstrained personas (Yusuf Blue Card, Maria EU
    citizen, Käthe + Tobias native German) see neutral ordering.
  - Cumulative-shrink invariant: each applied widening is removed
    from subsequent offers; eligibility checks (has-seniority,
    has-new-laterals, has-location) further hide affordances that
    would do nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Visa-constraint classifier — pattern-match against the
# persona_fixtures.residency_status string. The Yusuf carve-out
# (EU Blue Card is portable across EU employers → not constrained)
# is handled by matching "Blue Card" / "Blaue Karte" specifically
# in the unconstrained-pattern set rather than gating on "non-EU
# nationality" alone.

_CONSTRAINED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"§\s*16\s*[a-z]", re.IGNORECASE),  # §16a/b/c/d/e/f AufenthG
    re.compile(r"§\s*24", re.IGNORECASE),
    re.compile(r"\bAsylG\b", re.IGNORECASE),
    re.compile(r"\bAsylgesetz\b", re.IGNORECASE),
    re.compile(r"subsidiary\s+protection", re.IGNORECASE),
    re.compile(r"temporary\s+protection", re.IGNORECASE),
    re.compile(r"\bAufenthaltsgestattung\b", re.IGNORECASE),
    re.compile(r"\bDuldung\b", re.IGNORECASE),
)
_UNCONSTRAINED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bBlue\s*Card\b", re.IGNORECASE),
    re.compile(r"\bBlaue\s*Karte\b", re.IGNORECASE),
    re.compile(r"\bEU\s+citizen\b", re.IGNORECASE),
    re.compile(r"\bFreiz[üu]gigkeits", re.IGNORECASE),
    re.compile(r"\bGerman\s+citizen\b", re.IGNORECASE),
    re.compile(r"\bNiederlassungserlaubnis\b", re.IGNORECASE),
    re.compile(r"\bpermanent\s+residence\b", re.IGNORECASE),
)


def classify_visa_constraint(residency_status: str | None) -> bool:
    """Return True iff the residency_status indicates a permit class
    where relocation may require coordination with the Ausländerbehörde.

    Order: constrained-patterns checked first; unconstrained-patterns
    can override only if no constrained-pattern matched. Empty /
    unknown defaults to unconstrained (don't add an unnecessary
    caveat).
    """
    if not residency_status:
        return False
    for pat in _CONSTRAINED_PATTERNS:
        if pat.search(residency_status):
            return True
    # If no constrained-pattern matched, no need to check unconstrained —
    # the default is unconstrained.
    return False


# Seniority qualifiers we recognise in role_text — mirrors the
# diagnostic_engine's _STRIPPABLE_SENIORITY_PREFIXES so the two
# layers agree on what counts as a strippable qualifier.

_SENIORITY_PREFIXES: tuple[str, ...] = (
    "senior",
    "junior",
    "lead",
    "principal",
    "staff",
    "head of",
    "chief",
)


def has_seniority_qualifier(role_text: str | None) -> bool:
    """True iff role_text starts with a strippable seniority prefix.

    Used by the widening engine to gate the "drop seniority qualifier"
    affordance — if no qualifier is present, the affordance is hidden
    (no widening would result).
    """
    if not role_text:
        return False
    lc = role_text.casefold().lstrip()
    for prefix in _SENIORITY_PREFIXES:
        if lc.startswith(prefix + " "):
            return True
    return False


def strip_seniority_prefix(role_text: str) -> str:
    """Return role_text with the leading seniority prefix removed
    (case-preserving on the remainder). Idempotent: returns input
    unchanged when no qualifier present.
    """
    if not role_text:
        return ""
    lc = role_text.casefold().lstrip()
    for prefix in _SENIORITY_PREFIXES:
        if lc.startswith(prefix + " "):
            # Preserve the leading whitespace cap'd at the prefix,
            # then re-trim
            stripped = role_text.lstrip()[len(prefix) :].lstrip()
            return stripped
    return role_text


# Ausländerbehörde caveat text — operator-verbatim (2026-05-20).
# Doctrine: refuse to invent legal advice; always direct to BAMF /
# Ausländerbehörde / Migrationsberatungsstelle.

LOCATION_CAVEAT_TEXT = (
    "Note: changing your search location may not be compatible with "
    "your current residence-permit ties. We recommend checking with "
    "your local Ausländerbehörde or Migrationsberatungsstelle before "
    "relocating."
)


@dataclass(frozen=True)
class WideningAffordance:
    """One widening option offered in the empty-state recovery.

    ``id`` is the stable identifier (used by ``apply_widening`` +
    by the cumulative-shrink ``applied_widenings`` set on journey
    state). ``label`` is the user-facing title. ``description`` is
    the one-line explanation shown in the menu. ``caveat`` is the
    persona-aware footer (empty for unconstrained personas;
    populated with Ausländerbehörde caveat for constrained personas
    on the widen-location affordance).
    """

    id: str
    label: str
    description: str
    caveat: str = ""


# Affordance IDs — stable strings used in journey.applied_widenings.
WIDEN_LOCATION = "widen_location"
DROP_SENIORITY = "drop_seniority"
TRY_LATERALS = "try_laterals"

# Affordance order for unconstrained personas (Yusuf / Maria /
# Käthe / Tobias). Neutral: widen first, then seniority, then
# laterals.
_UNCONSTRAINED_ORDER: tuple[str, ...] = (
    WIDEN_LOCATION,
    DROP_SENIORITY,
    TRY_LATERALS,
)

# Affordance order for visa-constrained personas (Aïcha / Olga /
# Mahmoud). Safer widenings first: laterals (no friction with
# visa), drop seniority (within same role family), location LAST
# (with caveat).
_CONSTRAINED_ORDER: tuple[str, ...] = (
    TRY_LATERALS,
    DROP_SENIORITY,
    WIDEN_LOCATION,
)


def available_affordances(
    journey,  # type: ignore[no-untyped-def]  # circular import avoidance
    *,
    new_laterals_count: int = 0,
) -> list[WideningAffordance]:
    """Return the ordered, persona-aware, cumulatively-shrunk list of
    widening affordances available at the current empty-state turn.

    Filters applied (in order):
      1. ``journey.applied_widenings`` — affordances already used drop
         out (cumulative-shrink).
      2. Eligibility:
         - ``WIDEN_LOCATION`` requires journey.location truthy.
         - ``DROP_SENIORITY`` requires has_seniority_qualifier(role_text).
         - ``TRY_LATERALS`` requires new_laterals_count > 0 (caller
           computes via _suggest_lateral_roles minus already-in-
           target_roles).
      3. Persona ordering: constrained vs unconstrained per
         journey.visa_constrained.

    The 2 theatrical affordances spec'd by the operator (loosen
    language, loosen visa-status) are never offered — they would be
    theatrical against the current aggregator architecture. Phase 2
    backlog #72 + #73 capture the work to make them real.

    Retry + give-up are NOT included in the returned list — they
    are always-available routing tokens handled separately in the
    empty-state reply.
    """
    applied = set(journey.applied_widenings or [])
    pool: list[WideningAffordance] = []

    if WIDEN_LOCATION not in applied and journey.location:
        caveat = LOCATION_CAVEAT_TEXT if journey.visa_constrained else ""
        pool.append(
            WideningAffordance(
                id=WIDEN_LOCATION,
                label="Widen location",
                description="search without the location filter",
                caveat=caveat,
            )
        )

    # Drop seniority is eligible only when the aggregator's primary
    # query (target_roles[0]) still carries a seniority prefix.
    # The taxonomy match (fix #3, 2026-05-20) may have already
    # neutralized the qualifier — e.g., Olga's "Senior frontend
    # developer" matched to "frontend developer" as target_roles[0],
    # in which case dropping seniority would be a no-op for the
    # actual search. Doctrine: don't offer no-op affordances.
    if DROP_SENIORITY not in applied:
        primary_query = (
            journey.target_roles[0]
            if journey.target_roles
            else journey.role_text or ""
        )
        if has_seniority_qualifier(primary_query):
            stripped = strip_seniority_prefix(primary_query)
            pool.append(
                WideningAffordance(
                    id=DROP_SENIORITY,
                    label="Drop seniority qualifier",
                    description=f'search for "{stripped}" without the seniority prefix',
                )
            )

    if TRY_LATERALS not in applied and new_laterals_count > 0:
        pool.append(
            WideningAffordance(
                id=TRY_LATERALS,
                label="Try lateral roles",
                description=f"search {new_laterals_count} related role name(s) too",
            )
        )

    # Persona-aware ordering
    order = (
        _CONSTRAINED_ORDER if journey.visa_constrained else _UNCONSTRAINED_ORDER
    )

    def _order_key(a: WideningAffordance) -> int:
        try:
            return order.index(a.id)
        except ValueError:
            return 99

    pool.sort(key=_order_key)
    return pool


# Token vocabulary for user input parsing. Mirrors the inspire-phase
# decline / preferences-phase advance token sets that the rest of
# PART 6 fixes have settled on.

_WIDEN_LOCATION_TOKENS = frozenset(
    {
        "widen location", "widen", "location", "anywhere", "wider location",
        "broader location", "wider area", "weiter",
    }
)
_DROP_SENIORITY_TOKENS = frozenset(
    {
        "drop seniority", "drop seniority qualifier", "drop senior",
        "without seniority", "any seniority", "any level",
    }
)
_TRY_LATERALS_TOKENS = frozenset(
    {
        "try laterals", "try lateral roles", "laterals", "lateral roles",
        "related roles", "similar roles", "related",
    }
)


@dataclass(frozen=True)
class WideningOutcome:
    """Result of applying a widening affordance.

    ``action`` is one of:
      - ``"fire_search"`` — caller emits an AdvanceResult with
        ``run_search_with=outcome.search_criteria``. The journey
        state is mutated in place (location cleared / role_text
        rewritten / applied_widenings appended).
      - ``"ask_confirm_laterals"`` — caller emits an AdvanceResult
        with reply=outcome.reply asking the user to confirm
        which lateral roles to include. The journey state is
        mutated to ``review_substate="laterals_offered"`` with
        ``proposed_laterals`` populated.
      - ``"noop"`` — affordance not applicable (defensive fallback).

    The widening module never imports ``AdvanceResult`` or
    ``UserJourney`` from journey.py (avoids circular imports);
    the caller bridges via ``WideningOutcome``.
    """

    action: str
    reply: str = ""
    search_criteria: dict | None = None


def _build_search_criteria(journey) -> dict:  # type: ignore[no-untyped-def]
    """Mirror of the run_search_with dict shape used everywhere in
    journey.py + app.py. Centralised here so widening doesn't drift
    from the schema."""
    return {
        "target_roles": list(journey.target_roles),
        "location": journey.location or None,
        "remote_required": journey.remote_required,
        "salary_floor": journey.salary_floor,
        "company_size": journey.company_size or None,
    }


def apply_widening(
    journey,  # type: ignore[no-untyped-def]
    affordance_id: str,
    *,
    new_laterals: list[str] | None = None,
) -> WideningOutcome:
    """Apply the chosen widening to journey state. Mutates journey
    in place; returns a ``WideningOutcome`` describing what the
    caller should emit next.

    Idempotency: applying the same affordance twice is a no-op (the
    second call sees the affordance already in ``applied_widenings``
    and returns action="noop").

    For TRY_LATERALS, ``new_laterals`` MUST be supplied (computed
    by the caller via ``_suggest_lateral_roles`` then deduplicated
    against ``journey.target_roles``). Empty list → noop.
    """
    if affordance_id in journey.applied_widenings:
        return WideningOutcome(action="noop")

    if affordance_id == WIDEN_LOCATION:
        journey.location = ""
        journey.applied_widenings.append(WIDEN_LOCATION)
        return WideningOutcome(
            action="fire_search", search_criteria=_build_search_criteria(journey)
        )

    if affordance_id == DROP_SENIORITY:
        # Strip the qualifier from BOTH role_text (for display
        # consistency in subsequent re-renders) AND target_roles[0]
        # (the actual aggregator query). Fix-#3 semantics: role_text
        # is the user-verbatim narrative; target_roles[0] drives the
        # search. Both need to lose the qualifier here.
        if journey.target_roles:
            journey.target_roles = [
                strip_seniority_prefix(journey.target_roles[0]),
                *journey.target_roles[1:],
            ]
        journey.role_text = strip_seniority_prefix(journey.role_text or "")
        # matched_token stays as-is — it's already the canonical form
        journey.applied_widenings.append(DROP_SENIORITY)
        return WideningOutcome(
            action="fire_search", search_criteria=_build_search_criteria(journey)
        )

    if affordance_id == TRY_LATERALS:
        new_laterals = [r for r in (new_laterals or []) if r]
        if not new_laterals:
            return WideningOutcome(action="noop")
        journey.proposed_laterals = list(new_laterals)
        journey.review_substate = "laterals_offered"
        # The caller emits this reply. We compose it here so widening.py
        # owns the per-affordance UX strings.
        lines = [
            "I can also search these related role names:",
            "",
        ]
        for i, role in enumerate(new_laterals, start=1):
            lines.append(f"  {i}. **{role}**")
        lines.append("")
        lines.append(
            "Reply **yes** to include all of them, **no** to skip, or "
            "pick by number (e.g. `1` or `1, 3`)."
        )
        return WideningOutcome(action="ask_confirm_laterals", reply="\n".join(lines))

    return WideningOutcome(action="noop")


def parse_affordance_choice(
    msg: str, offered: list[WideningAffordance]
) -> WideningAffordance | None:
    """Parse the user's empty-state input against the offered
    affordance list. Accepts a 1-based number ("1") OR a token
    ("widen location"). Returns the matched affordance or None
    (caller re-asks).

    Number parsing tolerates leading / trailing whitespace + the
    "#" prefix users sometimes type. Token parsing is lowercased,
    whitespace-collapsed.
    """
    if not msg or not msg.strip():
        return None
    raw = msg.strip().lstrip("#").strip()
    # Number-pick
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(offered):
            return offered[idx]
        return None
    # Token-match — search per-affordance to keep order stable
    lc = " ".join(raw.lower().split())
    for a in offered:
        if a.id == WIDEN_LOCATION and lc in _WIDEN_LOCATION_TOKENS:
            return a
        if a.id == DROP_SENIORITY and lc in _DROP_SENIORITY_TOKENS:
            return a
        if a.id == TRY_LATERALS and lc in _TRY_LATERALS_TOKENS:
            return a
    return None
