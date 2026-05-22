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
from typing import Any


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
# Ausländerbehörde / Migrationsberatungsstelle. See
# docs/grant/14-source-class-hierarchy.md class A (legal/regulatory):
# class-A claims are never AI-generated; this caveat is the bound.

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

# Bug C piece 6 (2026-05-20): static labels for the final-state
# summary block. These are the past-tense user-facing names used
# when enumerating which widenings the user has already applied
# in the exhausted-recovery summary. Kept here (not in journey.py)
# so widening.py owns all widening-affordance UX strings — same
# pattern as the present-tense labels in WideningAffordance.label
# (e.g. "Widen location" -> "Widened location"). DE-bundle wiring
# captured in Phase 2 backlog #75 for the whole affordance label
# set; current rendering is EN-only consistent with pieces 1-5.
WIDENING_LABEL: dict[str, str] = {
    WIDEN_LOCATION: "Widened location",
    DROP_SENIORITY: "Dropped seniority qualifier",
    TRY_LATERALS: "Tried lateral roles",
}


def widening_label(affordance: str, locale: str | None = "en") -> str:
    """Locale-aware accessor for a widening affordance's user-facing
    label. Closes phase2-backlog #75 for this surface: the
    English defaults remain in ``WIDENING_LABEL`` (used as the
    fallback when a translation is missing); DE / future-locale
    strings live in ``static/i18n/<locale>.json`` under the
    ``backend.widening.<affordance>`` key.

    Existing call sites that don't yet pass a locale receive the
    English label (no behaviour change for un-migrated callers).
    """

    from company_discovery.i18n_bundle import translate

    key = f"backend.widening.{affordance}"
    default = WIDENING_LABEL.get(affordance, affordance)
    return translate(key, locale=locale, default=default)

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
    also_exclude: set[str] | None = None,
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
    # Piece 4 (2026-05-20): auto-relax mode passes the declined set
    # so a widening user said "no/skip" to in auto-mode doesn't get
    # re-suggested. Manual menu mode passes None (or set()) — declined
    # affordances stay menu-pickable per operator decision 2026-05-20
    # ("declining is a soft signal").
    if also_exclude:
        applied = applied | set(also_exclude)
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

# ----------------------------------------------------------------------
# CROSS-SUB-STATE TOKEN COLLISIONS — DOCUMENTED AND TESTED (2026-05-20)
# ----------------------------------------------------------------------
# Three tokens carry DIFFERENT meanings depending on which sub-state
# the user is in when they type them. The parser is sub-state-scoped
# so the dispatch is unambiguous, but the cross-sub-state correctness
# is easy to violate accidentally if a future agent reorders the parse
# routing. Three regression tests at the bottom of
# tests/test_widening.py pin the invariant:
#
#   test_weiter_in_auto_relax_advances_not_widens_location
#   test_skip_in_auto_relax_declines_not_lateral_cancels
#   test_cancel_in_auto_relax_returns_to_menu_not_lateral_cancel
#
#   token       sub-state                                meaning
#   ----------  ---------------------------------------  -----------------
#   weiter      menu (review_substate="empty")          widen-location token
#   weiter      auto_relax_offering                     advance/confirm
#   skip        laterals_offered                        cancel laterals
#   skip        auto_relax_offering                     decline this suggestion
#   next        auto_relax_offering                     decline this suggestion
#   cancel      laterals_offered                        cancel laterals
#   cancel      auto_relax_offering                     exit auto-mode -> menu
#   back        laterals_offered                        cancel laterals
#   back        auto_relax_offering                     exit auto-mode -> menu
#
# Routing order (in _advance_review and the handlers):
#   1. Check review_substate; route to the substate-specific handler
#   2. WITHIN that handler, parse against the substate-specific token
#      sets only. NEVER fall through to a sibling-substate token set.
#
# If a future change makes a substate handler accidentally consult
# another substate's token set, the three pinned tests fail loudly.
# ----------------------------------------------------------------------

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


# Auto-relax tokens (sub-state-scoped to review_substate ==
# "auto_relax_offering"). See cross-sub-state collision comment above.

_AUTO_RELAX_ADVANCE_TOKENS = frozenset(
    {
        "yes", "y", "ja", "j", "ok", "okay", "go", "weiter",
        "confirm", "do it", "apply", "sure",
    }
)
_AUTO_RELAX_DECLINE_TOKENS = frozenset(
    {
        "no", "n", "nein", "skip", "next", "nächste", "nachste",
        "weiter zu", "decline",
    }
)
_AUTO_RELAX_CANCEL_TOKENS = frozenset(
    {
        "cancel", "back", "back to menu", "back-to-menu",
        "stop", "abbrechen", "menu", "manual",
    }
)
_AUTO_RELAX_GIVE_UP_TOKENS = frozenset(
    {
        "give up", "done", "fertig", "exit", "quit", "end", "ende",
    }
)

# Tokens that route INTO auto-mode from the empty-state menu. The
# menu-level parser checks these AFTER the numbered-affordance
# parser; if a token matches an auto-relax-enter token, the handler
# enters auto-mode.

_AUTO_RELAX_ENTER_TOKENS = frozenset(
    {
        "auto", "auto-relax", "auto relax", "autorelax",
        "suggest", "system suggest", "guide me", "help me decide",
        "relax", "auto mode", "auto-mode", "automatic",
    }
)


def parse_auto_relax_response(msg: str) -> str:
    """Sub-state-scoped parser for review_substate="auto_relax_offering".

    Returns one of:
      - "advance"  — confirm the current suggestion
      - "decline"  — decline this one, hear the next
      - "cancel"   — exit auto-mode, return to the menu
      - "give_up"  — end the journey (PHASE_DONE)
      - "unknown"  — caller re-asks the current suggestion

    Order of resolution matters when tokens overlap across action
    sets: give-up checked first (longest-multiword wins), then
    cancel, then decline, then advance. "weiter" specifically lands
    in "advance" here even though it's in piece-3's
    _WIDEN_LOCATION_TOKENS (menu-mode meaning); the sub-state
    scoping prevents the menu-token parser from ever firing while
    we're in this sub-state.
    """
    if not msg or not msg.strip():
        return "unknown"
    lc = " ".join(msg.strip().lower().split())
    if lc in _AUTO_RELAX_GIVE_UP_TOKENS:
        return "give_up"
    if lc in _AUTO_RELAX_CANCEL_TOKENS:
        return "cancel"
    if lc in _AUTO_RELAX_DECLINE_TOKENS:
        return "decline"
    if lc in _AUTO_RELAX_ADVANCE_TOKENS:
        return "advance"
    return "unknown"


def parse_menu_auto_relax_entry(msg: str) -> bool:
    """True iff the menu-mode input is a request to enter auto-mode.

    Scoped to review_substate="empty" (menu mode). The caller
    checks the numbered-affordance parser first; if no number /
    widening-token matched, it falls through to this check and
    enters auto-mode on a hit.
    """
    if not msg or not msg.strip():
        return False
    lc = " ".join(msg.strip().lower().split())
    return lc in _AUTO_RELAX_ENTER_TOKENS


def next_auto_relax_suggestion(
    journey,  # type: ignore[no-untyped-def]
    *,
    new_laterals_count: int = 0,
) -> WideningAffordance | None:
    """Pick the next affordance auto-relax should propose, considering:
      - applied_widenings (cumulative-shrink from piece 3)
      - auto_relax_declined (user said no/skip in auto-mode)
      - persona-aware ordering (already enforced by available_affordances)
      - eligibility gates (already enforced)

    Returns the first eligible affordance per the persona-ordered
    list, or None when auto-relax has exhausted options. In the None
    case the caller exits auto-mode and routes back to the menu
    (which will show only retry + give-up since all widenings are
    either applied or declined).
    """
    declined = set(journey.auto_relax_declined or [])
    offered = available_affordances(
        journey,
        new_laterals_count=new_laterals_count,
        also_exclude=declined,
    )
    return offered[0] if offered else None


def format_count_text(n: int | None) -> str:
    """Render a cache-probed count for menu / auto-relax surface text.

    Piece 5 (2026-05-20):
      - ``None``  -> ""              (cold cache or no engine — omit)
      - ``0``     -> "(0 postings)"  (exact zero shown WITHOUT tilde
                                       per operator Q3: stale-cache-
                                       plus-new-postings is a real
                                       scenario; honesty > UX-protective
                                       omission. The tilde-prefix is
                                       reserved for approximate counts.)
      - ``N > 0`` -> "(~N postings)" (approximate, cache snapshot)

    Caller is responsible for any leading separator (space, comma).
    """
    if n is None:
        return ""
    if n == 0:
        return "(0 postings)"
    return f"(~{n} postings)"


def probe_count_for_affordance(
    journey,  # type: ignore[no-untyped-def]
    affordance: WideningAffordance,
    *,
    lateral_options: list[str] | None = None,
    engine: Any = None,  # type: ignore[name-defined]  # noqa: F821 - lazy import
) -> int | None:
    """Compute a single representative count for a widening affordance.

    Piece 5 (2026-05-20): replaces piece-4's per-affordance probe
    logic that lived in journey._probe_auto_relax_count for
    WIDEN_LOCATION + DROP_SENIORITY. Extends with TRY_LATERALS
    AGGREGATE: sum of per-lateral counts iff EVERY lateral has a
    cache count; otherwise None (operator Q2 — strict honesty about
    partial data).

    Per-lateral granular counts are surfaced separately via
    ``probe_lateral_counts`` (used in the auto-relax suggestion text).

    Returns None when no engine OR cold cache OR (for TRY_LATERALS)
    when at least one lateral is cold.
    """
    if engine is None or affordance is None:
        return None
    primary = (
        journey.target_roles[0]
        if journey.target_roles
        else (journey.role_text or "")
    )
    try:
        if affordance.id == WIDEN_LOCATION:
            # Probe: same role, no location filter (what widen-location
            # would search).
            return engine.probe_cached_count(query=primary, location=None)
        if affordance.id == DROP_SENIORITY:
            stripped = strip_seniority_prefix(primary)
            return engine.probe_cached_count(
                query=stripped, location=journey.location or None
            )
        if affordance.id == TRY_LATERALS:
            if not lateral_options:
                return None
            counts: list[int | None] = []
            for lat in lateral_options:
                # Operator Q4 (2026-05-20): probe with
                # journey.location INTACT. The TRY_LATERALS
                # affordance widens ROLE, not LOCATION; counting
                # against the user's stated location reflects what
                # they would actually search. Do NOT probe with
                # location=None here — that would conflate two
                # different widening affordances.
                counts.append(
                    engine.probe_cached_count(
                        query=lat, location=journey.location or None
                    )
                )
            # Aggregate iff ALL laterals warm (operator Q2):
            # partial-data sum would be decision-misleading.
            if any(c is None for c in counts):
                return None
            return sum(counts)
    except Exception:  # noqa: BLE001 - count surface is optional; never fail the caller
        return None
    return None


def probe_lateral_counts(
    journey,  # type: ignore[no-untyped-def]
    lateral_options: list[str],
    *,
    engine: Any = None,  # type: ignore[name-defined]  # noqa: F821 - lazy import
) -> list[int | None]:
    """Per-lateral cache counts, list aligned with ``lateral_options``.

    Piece 5 (2026-05-20): powers the auto-relax suggestion text's
    per-lateral granular display (operator Q1 — per-lateral in auto-
    relax, aggregate in menu). Returns a list of ``int | None`` of
    the same length as ``lateral_options``; each entry is the cache
    count for that specific lateral or None if cold.

    Operator Q4: probe with journey.location intact (same as
    probe_count_for_affordance — TRY_LATERALS widens role, not
    location).
    """
    if not lateral_options:
        return []
    if engine is None:
        return [None] * len(lateral_options)
    out: list[int | None] = []
    for lat in lateral_options:
        try:
            out.append(
                engine.probe_cached_count(
                    query=lat, location=journey.location or None
                )
            )
        except Exception:  # noqa: BLE001 - Case E best-effort: count is decorative on the menu (None renders as "—"); never fail the lateral list assembly
            out.append(None)
    return out


def format_auto_relax_suggestion(
    affordance: WideningAffordance,
    *,
    lateral_options: list[str] | None = None,
    lateral_counts: list[int | None] | None = None,
    count: int | None = None,
) -> str:
    """Compose the user-facing suggestion text for a single
    auto-relax step. Piece 4 (2026-05-20) + piece 5 (per-lateral
    mixed-state rendering, 2026-05-20).

    Cold cache: no count surfacing. Warm cache:
      - WIDEN_LOCATION / DROP_SENIORITY: trailing "Recent searches
        show **(~N postings)**" (or "(0 postings)" for exact zero).
      - TRY_LATERALS: per-lateral counts INLINE with each role name
        (mixed warm/cold state handled — laterals without a cache
        hit render without a count parenthetical, no fabricated
        placeholder).
    """
    if affordance.id == WIDEN_LOCATION:
        suggestion = (
            "Try widening to **search without the location filter**?"
        )
    elif affordance.id == DROP_SENIORITY:
        suggestion = (
            f"Try widening to **{affordance.description}**?"
        )
    elif affordance.id == TRY_LATERALS:
        if lateral_options:
            # Render per-lateral inline; mixed-state handled by
            # format_count_text returning "" for None entries.
            counts = lateral_counts or [None] * len(lateral_options)
            parts: list[str] = []
            for i, role in enumerate(lateral_options[:5]):
                lc = counts[i] if i < len(counts) else None
                cnt_text = format_count_text(lc)
                if cnt_text:
                    parts.append(f"**{role}** {cnt_text}")
                else:
                    parts.append(f"**{role}**")
            roles_list = ", ".join(parts)
            suggestion = (
                f"Try widening to **lateral roles**? Would search "
                f"these too: {roles_list}."
            )
        else:
            suggestion = "Try widening to **lateral roles**?"
    else:
        suggestion = f"Try **{affordance.label}**?"

    # Count tail — applies to WIDEN_LOCATION + DROP_SENIORITY (where
    # ``count`` is the single relevant probe). Skipped for
    # TRY_LATERALS because the per-lateral counts already surface
    # inline above; appending an aggregate tail here would either
    # be redundant (all warm) or hide partial-data state (operator
    # Q1 — aggregate not surfaced in auto-relax).
    if affordance.id != TRY_LATERALS:
        cnt_text = format_count_text(count)
        if cnt_text:
            suggestion += f" Recent searches show **{cnt_text}**."

    if affordance.caveat:
        suggestion += f"\n\n{affordance.caveat}"

    suggestion += (
        "\n\nReply **yes** to apply, **no** / **skip** to try the next "
        "widening, **cancel** to return to the menu, or **give up** "
        "to end this journey."
    )
    return suggestion


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
    # Number-pick. Restrict to ASCII digits — ``str.isdigit()``
    # returns True for Unicode digits like '²' which ``int()``
    # rejects. Same fix applied in journey.py:_advance_review_empty.
    if raw.isascii() and raw.isdigit():
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
