"""Strict job-type + location filter for chat search and discovery scans.

When the user says "find me bartender jobs in Berlin" or
"Pflegehelfer in Deutschland", we have two requirements that the
existing aggregator search can't meet on its own:

1. Strict role matching. Aggregator results are ranked by keyword
   overlap, but a low-overlap match still surfaces. If the user asked
   for "bartender" we must NOT return "Backend engineer". This module
   provides a hard allow-list: a job's title (and optionally
   description) must contain at least one synonym from the chosen
   taxonomy bucket.

2. EN + DE synonyms in one bucket. A German user types "Pflegehelfer";
   an English user types "nursing assistant". Both must produce the
   same hits. Each bucket holds both vocabularies plus the role's
   common variants.

The taxonomy is intentionally small (the roles the user actually
asked for, plus a handful of obvious neighbours). Adding a new bucket
is a single dict entry; no logic changes.

Public surface
==============

- ``TAXONOMY`` — dict[str, TaxonomyBucket] keyed by canonical key
- ``identify_bucket(text)`` — text → taxonomy key or None
- ``job_matches_bucket(title, description, key)`` — strict allow-list
- ``filter_jobs(jobs, job_type, location)`` — sequence in, sequence out
- ``normalize_location(text)`` — "Berlin, DE", "Deutschland", "anywhere", …
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class TaxonomyBucket:
    """One role bucket. ``label_en``/``label_de`` are user-facing names;
    ``synonyms`` is the strict allow-list — case-insensitive,
    word-boundary matched against the title + description."""

    label_en: str
    label_de: str
    synonyms: tuple[str, ...]


# Canonical keys are lowercase ASCII. Add buckets as the operator
# expands the supported roles. Each synonym is a substring that, if
# present in a job's title/description (case-insensitive, on word
# boundaries), counts as a match.
TAXONOMY: dict[str, TaxonomyBucket] = {
    "bartender": TaxonomyBucket(
        label_en="Bartender",
        label_de="Barkeeper",
        synonyms=(
            "bartender", "bartenders",
            "barkeeper", "barkeeperin", "barkeeperinnen",
            "bar staff", "bar back", "barback",
            "barperson", "bar person",
            "mixologist",
            "schankkellner", "schankkellnerin",
            "thekenkraft",
            "barfrau", "barmann",
            "cocktail server",
            "bar attendant",
        ),
    ),
    "barista": TaxonomyBucket(
        label_en="Barista",
        label_de="Barista",
        synonyms=(
            "barista", "baristas",
            "café staff", "cafe staff",
            "coffee bar attendant",
            "espresso server", "coffee server",
            "kaffeebar", "kaffeebar-mitarbeiter",
            "coffee shop assistant",
        ),
    ),
    "cafe_worker": TaxonomyBucket(
        label_en="Café worker",
        label_de="Café-Mitarbeiter/in",
        synonyms=(
            "café worker", "cafe worker",
            "café assistant", "cafe assistant",
            "café team", "cafe team",
            "café-mitarbeiter", "cafe-mitarbeiter",
            "cafémitarbeiter", "cafemitarbeiter",
            "service crew café", "service crew cafe",
        ),
    ),
    "pflegehelfer": TaxonomyBucket(
        label_en="Nursing assistant",
        label_de="Pflegehelfer/in",
        synonyms=(
            "pflegehelfer", "pflegehelferin", "pflegehelfer/in",
            "pflegeassistent", "pflegeassistentin", "pflegeassistent/in",
            "pflegekraft",
            "altenpflegehelfer", "altenpflegehelferin",
            "krankenpflegehelfer", "krankenpflegehelferin",
            "pflegehilfskraft",
            "nursing assistant", "nursing aide",
            "care assistant", "healthcare assistant",
            "hca",
            "auxiliary nurse",
        ),
    ),
    "waiter": TaxonomyBucket(
        label_en="Waiter / waitress",
        label_de="Kellner/in",
        synonyms=(
            "waiter", "waitress", "wait staff", "server",
            "kellner", "kellnerin", "kellner/in",
            "servicekraft", "servicemitarbeiter", "servicemitarbeiterin",
            "restaurant server", "restaurant staff",
        ),
    ),
}


# Words / phrases that mean "no location filter".
_ANY_LOCATION_TOKENS = (
    "anywhere", "any location", "any city",
    "remote", "remote-only", "remote only",
    "überall", "ueberall", "egal wo", "egal", "any",
)

# Known German cities — used to expand "Germany" / "Deutschland" so
# results that say "Berlin" or "München" without the country still match.
_GERMAN_CITIES = (
    "berlin", "münchen", "muenchen", "munich",
    "hamburg", "köln", "koeln", "cologne",
    "frankfurt", "stuttgart", "düsseldorf", "duesseldorf",
    "dortmund", "essen", "leipzig", "dresden",
    "hannover", "hanover", "nürnberg", "nuernberg", "nuremberg",
    "bremen", "bonn", "münster", "muenster", "karlsruhe",
    "mannheim", "augsburg", "wiesbaden", "kiel", "freiburg",
)


def _word_boundary_re(needle: str) -> re.Pattern[str]:
    """Compile a case-insensitive regex that matches ``needle`` on
    word boundaries. We treat ``/`` and ``-`` as word characters for
    this purpose so ``Pflegehelfer/in`` matches as one token.
    """
    escaped = re.escape(needle.casefold())
    return re.compile(rf"(?<![A-Za-zÄÖÜäöüß]){escaped}(?![A-Za-zÄÖÜäöüß])",
                       flags=re.IGNORECASE)


def identify_bucket(text: str | None) -> str | None:
    """Return the canonical taxonomy key whose synonyms best match the
    user's free-text role. None if no bucket matches.

    Matching is case-insensitive, word-boundary, longest-synonym wins
    so "barback" doesn't accidentally trigger the "back-end" intuition
    and "altenpflegehelfer" doesn't ambiguously match both the
    pflegehelfer bucket and itself.
    """
    if not text:
        return None
    haystack = text.casefold()
    best_key: str | None = None
    best_len = 0
    for key, bucket in TAXONOMY.items():
        for synonym in bucket.synonyms:
            if _word_boundary_re(synonym).search(haystack):
                if len(synonym) > best_len:
                    best_key = key
                    best_len = len(synonym)
    return best_key


def job_matches_bucket(title: str, description: str | None, key: str) -> bool:
    """True iff the job's title or description matches any synonym in
    the requested bucket. Strict allow-list — used to filter out jobs
    that surface from aggregator search but aren't actually in the
    role the user asked for.
    """
    bucket = TAXONOMY.get(key)
    if bucket is None:
        return False
    haystack = " ".join(p for p in (title or "", description or "") if p).casefold()
    if not haystack.strip():
        return False
    for synonym in bucket.synonyms:
        if _word_boundary_re(synonym).search(haystack):
            return True
    return False


def normalize_location(text: str | None) -> str | None:
    """Return a canonical location string (lowercased, trimmed) or
    None if the user meant "no filter".

    - empty / 'anywhere' / 'remote' / 'überall' → None (no filter)
    - 'Germany' / 'Deutschland' / 'DE' → 'germany' (expanded to all
      known DE cities at match time)
    - everything else → casefolded raw input
    """
    if not text:
        return None
    cleaned = text.strip().casefold()
    if not cleaned:
        return None
    if cleaned in _ANY_LOCATION_TOKENS:
        return None
    if cleaned in ("germany", "deutschland", "de", "ger"):
        return "germany"
    return cleaned


def job_matches_location(job_location: str | None, requested: str | None) -> bool:
    """True iff the job's location satisfies the requested location.

    - requested=None → always True (no filter)
    - requested='germany' → match if job location contains a known DE
      city OR ends with ', germany' / ', deutschland'
    - other → match if requested is a substring of the job location
      (case-insensitive)
    """
    if requested is None:
        return True
    if not job_location:
        return False
    location = job_location.casefold()
    if requested == "germany":
        if "germany" in location or "deutschland" in location:
            return True
        for city in _GERMAN_CITIES:
            if _word_boundary_re(city).search(location):
                return True
        return False
    return requested in location


def filter_jobs(
    jobs: Iterable[Any],
    *,
    job_type: str | None,
    location: str | None,
) -> list[Any]:
    """Apply the strict job-type + location filter to a sequence.

    ``jobs`` is any iterable of objects with ``title``, optional
    ``raw_description`` (or ``description``), and optional
    ``location`` attributes. Returns a list (preserving order) of
    items that pass both filters.

    When ``job_type`` is None, the role check is skipped (any role).
    When ``location`` is None (or "anywhere"), the location check is
    skipped (any location).
    """
    norm_location = normalize_location(location)
    kept: list[Any] = []
    for job in jobs:
        title = getattr(job, "title", "") or ""
        # Aggregator and discovery payloads use different attribute names.
        description = (
            getattr(job, "raw_description", None)
            or getattr(job, "description", None)
            or getattr(job, "raw_snippet", None)
            or ""
        )
        job_location = getattr(job, "location", None)
        if job_type and not job_matches_bucket(title, description, job_type):
            continue
        if not job_matches_location(job_location, norm_location):
            continue
        kept.append(job)
    return kept


def filter_dict_jobs(
    jobs: Iterable[dict[str, Any]],
    *,
    job_type: str | None,
    location: str | None,
) -> list[dict[str, Any]]:
    """Same as ``filter_jobs`` but for dicts (HTTP-payload shape).
    Looks at ``title``, ``description``/``rawDescription``/``raw_snippet``,
    and ``location`` keys."""
    norm_location = normalize_location(location)
    kept: list[dict[str, Any]] = []
    for job in jobs:
        title = job.get("title") or ""
        description = (
            job.get("rawDescription")
            or job.get("raw_description")
            or job.get("description")
            or job.get("rawSnippet")
            or job.get("raw_snippet")
            or ""
        )
        job_location = job.get("location")
        if job_type and not job_matches_bucket(title, description, job_type):
            continue
        if not job_matches_location(job_location, norm_location):
            continue
        kept.append(job)
    return kept


def list_supported_roles() -> list[dict[str, str]]:
    """Return the labels of every taxonomy bucket so the chat router can
    surface "I support these roles" to the user when they ask for an
    unrecognised one."""
    return [
        {"key": key, "label_en": b.label_en, "label_de": b.label_de}
        for key, b in TAXONOMY.items()
    ]
