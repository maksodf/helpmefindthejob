# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

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
    "software_engineer": TaxonomyBucket(
        label_en="Software engineer",
        label_de="Softwareentwickler/in",
        synonyms=(
            "software engineer", "software developer", "software dev",
            "backend engineer", "backend developer",
            "frontend engineer", "frontend developer",
            "fullstack engineer", "fullstack developer",
            "full stack", "fullstack",
            "platform engineer", "infrastructure engineer",
            "devops engineer", "site reliability engineer", "sre",
            "engineering manager",
            "softwareentwickler", "softwareentwicklerin",
            "softwareingenieur", "softwareingenieurin",
            "anwendungsentwickler", "anwendungsentwicklerin",
            "programmierer", "programmiererin",
        ),
    ),
    "data_engineer": TaxonomyBucket(
        label_en="Data engineer / scientist",
        label_de="Data Engineer / Data Scientist",
        synonyms=(
            "data engineer", "data scientist", "data analyst",
            "ml engineer", "machine learning engineer",
            "ai engineer", "ml scientist",
            "analytics engineer", "bi analyst",
            "datenanalyst", "datenanalystin",
            "data engineer:in", "dateningenieur", "dateningenieurin",
        ),
    ),
    "product_manager": TaxonomyBucket(
        label_en="Product manager",
        label_de="Product Manager / Produktmanager",
        synonyms=(
            "product manager", "product owner", "product lead",
            "senior product manager", "group product manager",
            "principal product manager",
            "produktmanager", "produktmanagerin",
            "produktentwickler", "produktentwicklerin",
        ),
    ),
    "designer": TaxonomyBucket(
        label_en="Designer",
        label_de="Designer/in",
        synonyms=(
            "designer", "ux designer", "ui designer", "ux/ui designer",
            "product designer", "graphic designer",
            "visual designer", "interaction designer",
            "designerin", "grafikdesigner", "grafikdesignerin",
            "gestalter", "gestalterin", "mediengestalter",
            "mediengestalterin",
        ),
    ),
    "marketing": TaxonomyBucket(
        label_en="Marketing",
        label_de="Marketing",
        synonyms=(
            "marketing manager", "marketing lead", "marketing specialist",
            "performance marketing", "growth marketing", "growth lead",
            "growth hacker",
            "content marketing", "content manager", "content strategist",
            "social media manager", "social media specialist",
            "seo specialist", "seo manager", "seo lead",
            "brand manager", "brand strategist",
            "crm manager", "crm specialist",
            "marketingmanager", "marketingmanagerin",
            "marketingreferent", "marketingreferentin",
            "marketingbeauftragter", "marketingbeauftragte",
        ),
    ),
    "sales": TaxonomyBucket(
        label_en="Sales",
        label_de="Vertrieb",
        synonyms=(
            "sales representative", "sales rep", "sales manager",
            "sales executive", "account executive", "account manager",
            "business development", "bdr", "sdr",
            "sales engineer",
            "vertriebsmitarbeiter", "vertriebsmitarbeiterin",
            "vertriebsleiter", "vertriebsleiterin",
            "verkäufer", "verkäuferin",
            "kundenberater", "kundenberaterin",
        ),
    ),
    "finance": TaxonomyBucket(
        label_en="Finance",
        label_de="Finance / Controlling",
        synonyms=(
            "finance manager", "financial analyst", "controller",
            "fp&a", "fpa", "treasury", "treasurer",
            "accountant", "senior accountant", "bookkeeper",
            "audit", "auditor", "internal audit",
            "tax manager", "tax accountant",
            "buchhalter", "buchhalterin",
            "finanzbuchhalter", "finanzbuchhalterin",
            "finanzmanager", "finanzmanagerin",
            "controlling", "controller/in",
        ),
    ),
    "consulting": TaxonomyBucket(
        label_en="Consultant",
        label_de="Berater/in",
        synonyms=(
            "consultant", "senior consultant", "principal consultant",
            "management consultant", "strategy consultant",
            "business consultant", "it consultant", "tech consultant",
            "associate consultant",
            "berater", "beraterin", "unternehmensberater",
            "unternehmensberaterin", "strategieberater",
            "strategieberaterin",
        ),
    ),
    "customer_success": TaxonomyBucket(
        label_en="Customer success / support",
        label_de="Customer Success / Support",
        synonyms=(
            "customer success", "customer success manager",
            "customer support", "support engineer", "support specialist",
            "technical support", "client success",
            "kundenservice", "kundensupport",
            "kundenbetreuer", "kundenbetreuerin",
            "kundenservicemitarbeiter", "kundenservicemitarbeiterin",
        ),
    ),
    "healthcare_management": TaxonomyBucket(
        label_en="Healthcare management",
        label_de="Healthcare-Management",
        synonyms=(
            "healthcare manager", "clinic manager", "hospital manager",
            "klinikleiter", "klinikleiterin",
            "klinikmanager", "klinikmanagerin",
            "krankenhausmanager", "krankenhausmanagerin",
            "stationsleiter", "stationsleiterin",
            "pflegedienstleitung", "pflegedienstleiter",
            "pflegedienstleiterin",
            "healthcare project manager", "clinical project manager",
            "digital health", "health tech",
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
    key, _ = identify_bucket_with_match(text)
    return key


def identify_bucket_with_match(text: str | None) -> tuple[str | None, str | None]:
    """Like :func:`identify_bucket` but also returns the literal token
    from the user's message that triggered the match.

    Used by the chat router to preserve the user's language when
    sending a query to the aggregator. The user typed "Pflegehelfer"
    in German — we want the aggregator to search for "Pflegehelfer"
    (which matches German job-board postings), NOT the canonical
    English label "Nursing assistant" (which only matches the small
    English-titled subset on DE job boards).

    The returned token preserves the case of the user's message so
    the confirmation prompt also feels right.
    """
    if not text:
        return None, None
    haystack = text.casefold()
    best_key: str | None = None
    best_matched_text: str | None = None
    best_len = 0
    for key, bucket in TAXONOMY.items():
        for synonym in bucket.synonyms:
            m = _word_boundary_re(synonym).search(haystack)
            if m and len(synonym) > best_len:
                start, end = m.span()
                # Slice the ORIGINAL text — preserves case + diacritics.
                best_matched_text = text[start:end]
                best_key = key
                best_len = len(synonym)
    return best_key, best_matched_text


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
    - job_location empty AND requested set → True (trust upstream)
      The aggregator search already received the location parameter
      and filtered server-side. If it returned a job with no
      explicit location field, rejecting it would shrink the result
      set to almost nothing — especially for DACH-native postings
      where the aggregator's location-tagged subset is sparse.
    - requested='germany' → match if job location contains a known DE
      city OR ends with ', germany' / ', deutschland'
    - other → match if requested is a substring of the job location
      (case-insensitive)
    """
    if requested is None:
        return True
    if not job_location:
        return True
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


# R21.2: when a search resolves to a known role bucket we also flip
# the user's persona so the aggregator's ranking + the watchlist
# scan don't bias toward a default they never chose. Keys map a
# taxonomy bucket → an existing persona id from
# company_discovery.personas.PERSONAS. Missing entries mean "don't
# touch the persona" — keep what the user already had.
BUCKET_TO_PERSONA: dict[str, str] = {
    "software_engineer": "tech",
    "data_engineer": "data",
    "product_manager": "product-management",
    "designer": "design",
    "marketing": "marketing",
    "sales": "sales",
    "finance": "finance",
    "consulting": "operations",
    "customer_success": "support",
    "healthcare_management": "healthcare-management",
    "pflegehelfer": "healthcare-clinical",
    # Hospitality buckets have no dedicated persona — leave the
    # user's existing persona alone rather than forcing a wrong
    # one. The strict bucket filter does the actual narrowing.
}


def persona_for_bucket(bucket_key: str | None) -> str | None:
    """Look up the persona id matching a taxonomy bucket. Returns
    None when the bucket has no mapped persona or the key is
    unknown — callers should leave the user's existing persona
    in place in that case."""
    if not bucket_key:
        return None
    return BUCKET_TO_PERSONA.get(bucket_key)


# R21.3: aggregator job-field sanity check.
#
# Real-world aggregator parsers occasionally swap title↔location
# fields (we saw "title=Bangalore, India" + "location=Senior/Lead
# Devops Engineer..." on prod). Rendering those raw on the search-
# results canvas looks broken. This validator drops jobs that fail
# basic field-shape checks.
#
# We're intentionally LENIENT — only the obviously-malformed cases
# get dropped. Borderline rows pass through and the user can decide
# whether they're useful.

_LIKELY_TITLE_VERBS = (
    "lead", "senior", "junior", "principal", "manager", "engineer",
    "developer", "scientist", "analyst", "designer", "specialist",
    "consultant", "executive", "coordinator", "assistant", "agent",
    "officer", "associate", "intern",
    "leiter", "leiterin", "entwickler", "entwicklerin",
    "berater", "beraterin", "ingenieur", "ingenieurin",
    "manager:in", "spezialist", "spezialistin",
)

_OBVIOUS_LOCATION_TOKENS = (
    # Just a few — we don't need full DE city list; we just need
    # enough that a string with NOTHING but place names is flagged
    # as "looks like a location, not a title".
    "berlin", "münchen", "muenchen", "munich", "hamburg",
    "stuttgart", "frankfurt", "köln", "koeln", "düsseldorf",
    "duesseldorf", "vienna", "wien", "zurich", "zürich",
    "london", "paris", "amsterdam", "dublin",
    "san francisco", "new york", "ny", "sf", "bangalore",
    "remote", "anywhere", "germany", "deutschland", "uk", "usa",
)


def _looks_like_only_a_location(text: str) -> bool:
    """True when ``text`` reads as a place name + nothing else.
    Used to drop jobs whose 'title' is actually a location."""
    if not text:
        return False
    lc = text.casefold().strip().strip(",.;:!?")
    if len(lc) > 50:
        return False  # too long to be a bare location
    # If the string is a comma-separated list of place tokens, it's
    # a location dressed up as a title.
    bits = [b.strip() for b in lc.replace(";", ",").split(",")
              if b.strip()]
    if not bits:
        return False
    return all(b in _OBVIOUS_LOCATION_TOKENS for b in bits)


def _looks_like_a_title_not_location(text: str) -> bool:
    """True when ``text`` contains role-noun keywords — i.e. it's a
    title that landed in the location field by mistake."""
    if not text:
        return False
    lc = text.casefold()
    return any(verb in lc for verb in _LIKELY_TITLE_VERBS)


def looks_malformed(job: dict[str, Any]) -> bool:
    """True iff the job's fields look swapped or otherwise unfit for
    the user. Drops:

    - title that's actually a location ("Bangalore, India")
    - location that's actually a title ("Senior Devops Engineer...")
    - URL that's not http(s) (could be a relative path, broken
      reference, or scheme-less garbage)
    """
    title = (job.get("title") or "").strip()
    location = (job.get("location") or "").strip()
    url = (job.get("url") or "").strip()

    if _looks_like_only_a_location(title):
        return True
    if _looks_like_a_title_not_location(location):
        return True
    if url and not url.lower().startswith(("http://", "https://")):
        return True
    if not title:
        return True  # nothing to render
    return False


def filter_malformed_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop obviously-malformed jobs from a list. Preserves order."""
    return [j for j in jobs if not looks_malformed(j)]
