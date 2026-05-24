# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Curated city-adjacency graph for DACH commute-range job search.

Phase 2 backlog item #74 (and #71 Phase D) requires a city↔city
adjacency graph so the diagnostic engine can answer questions like
"47 postings exist in Berlin AND Halle (within commute range)."
This module is the substrate: a hand-curated dataset of city pairs
where one-way commute time is approximately ≤90 minutes on
regional rail (S-Bahn / RE / IC). The hand curation is deliberate
— OSM-derived edges would include impractical 4-hour drives, and
Verkehrsverbund APIs are not consistent enough across DACH to
trust as a build-time data source for a v0.1 feature.

Edges are symmetric and undirected. Keys are normalised location
strings (lowercase, accent-stripped, single-segment) matching the
``_norm_location`` output in :mod:`company_discovery.job_index`,
so an aggregator query for "berlin" matches adjacency entries
keyed "berlin".

Sources for the curation (operator notes, 2026-05-21):
- Deutsche Bahn Reiseauskunft for actual transit times
- Verkehrsverbund coverage maps (BVG/MVV/KVV/VVS/VRS/RMV/HVV/MDV)
- Bayerisches Tarifsystem for München-area S-Bahn endpoints
- Mitteldeutscher Verkehrsverbund for Leipzig–Halle S-Bahn link
- Hamburg / Kiel / Lübeck S-Bahn extension projects (2025)

Each pair carries a ``minutes`` field (one-way regional-rail time)
as an honesty marker. If we ever surface this data to users, the
minutes field lets the UI say "≈45 min by S-Bahn" rather than a
naïve "within commute range" which would over-promise on pairs
like Berlin↔Brandenburg.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class AdjacencyEdge:
    """A symmetric commute-range edge between two cities. ``minutes``
    is the typical one-way regional-rail time at peak; assume ±10
    minutes off-peak variance. ``mode`` is the dominant transit
    label ("S-Bahn" / "RE/IC" / "ICE" / "mixed") used in user-
    facing copy.
    """

    a: str
    b: str
    minutes: int
    mode: str


# Curated commute-range edges across DACH metropolitan areas.
# Pairs are stored in canonical order (alphabetical) but lookups
# are direction-agnostic via :func:`adjacent_cities`.
_EDGES: tuple[AdjacencyEdge, ...] = (
    # Berlin metro + commuter belt
    AdjacencyEdge("berlin", "potsdam", 30, "S-Bahn"),
    AdjacencyEdge("berlin", "brandenburg", 65, "RE/IC"),
    AdjacencyEdge("berlin", "frankfurt (oder)", 70, "RE/IC"),
    AdjacencyEdge("berlin", "oranienburg", 35, "S-Bahn"),
    AdjacencyEdge("berlin", "konigs wusterhausen", 35, "S-Bahn"),
    # Hamburg metro + Schleswig-Holstein corridor
    AdjacencyEdge("hamburg", "lubeck", 45, "RE/IC"),
    AdjacencyEdge("hamburg", "luneburg", 40, "RE/IC"),
    AdjacencyEdge("hamburg", "buxtehude", 35, "S-Bahn"),
    AdjacencyEdge("hamburg", "norderstedt", 30, "U-Bahn"),
    AdjacencyEdge("hamburg", "ahrensburg", 25, "S-Bahn"),
    AdjacencyEdge("kiel", "lubeck", 80, "RE/IC"),
    # München metro + Oberbayern
    AdjacencyEdge("munchen", "augsburg", 40, "RE/IC"),
    AdjacencyEdge("munchen", "ingolstadt", 40, "RE/IC"),
    AdjacencyEdge("munchen", "freising", 25, "S-Bahn"),
    AdjacencyEdge("munchen", "rosenheim", 50, "RE/IC"),
    AdjacencyEdge("munchen", "starnberg", 25, "S-Bahn"),
    AdjacencyEdge("munchen", "erding", 45, "S-Bahn"),
    # Rhein-Ruhr-Köln cluster (heavily interconnected)
    AdjacencyEdge("koln", "bonn", 20, "RE/IC"),
    AdjacencyEdge("koln", "dusseldorf", 25, "RE/IC"),
    AdjacencyEdge("koln", "leverkusen", 15, "S-Bahn"),
    AdjacencyEdge("koln", "aachen", 50, "RE/IC"),
    AdjacencyEdge("dusseldorf", "duisburg", 10, "S-Bahn"),
    AdjacencyEdge("dusseldorf", "essen", 15, "RE/IC"),
    AdjacencyEdge("dusseldorf", "wuppertal", 25, "S-Bahn"),
    AdjacencyEdge("dusseldorf", "krefeld", 20, "RE/IC"),
    AdjacencyEdge("essen", "bochum", 10, "S-Bahn"),
    AdjacencyEdge("essen", "duisburg", 15, "S-Bahn"),
    AdjacencyEdge("bochum", "dortmund", 15, "S-Bahn"),
    AdjacencyEdge("dortmund", "essen", 25, "S-Bahn"),
    # Rhein-Main cluster
    AdjacencyEdge("frankfurt", "wiesbaden", 40, "RE/IC"),
    AdjacencyEdge("frankfurt", "mainz", 30, "RE/IC"),
    AdjacencyEdge("frankfurt", "darmstadt", 15, "RE/IC"),
    AdjacencyEdge("frankfurt", "hanau", 15, "S-Bahn"),
    AdjacencyEdge("frankfurt", "offenbach", 10, "S-Bahn"),
    AdjacencyEdge("wiesbaden", "mainz", 15, "S-Bahn"),
    # Stuttgart cluster
    AdjacencyEdge("stuttgart", "esslingen", 15, "S-Bahn"),
    AdjacencyEdge("stuttgart", "ludwigsburg", 15, "S-Bahn"),
    AdjacencyEdge("stuttgart", "heilbronn", 40, "RE/IC"),
    AdjacencyEdge("stuttgart", "boblingen", 20, "S-Bahn"),
    AdjacencyEdge("stuttgart", "reutlingen", 45, "RE/IC"),
    # Sachsen / Sachsen-Anhalt (the spec example)
    AdjacencyEdge("leipzig", "halle", 25, "S-Bahn"),
    AdjacencyEdge("leipzig", "chemnitz", 60, "RE/IC"),
    AdjacencyEdge("dresden", "freital", 15, "S-Bahn"),
    AdjacencyEdge("dresden", "meissen", 35, "S-Bahn"),
    # Niedersachsen
    AdjacencyEdge("hannover", "hildesheim", 30, "RE/IC"),
    AdjacencyEdge("hannover", "braunschweig", 40, "ICE"),
    AdjacencyEdge("hannover", "celle", 25, "RE/IC"),
    # Nordbayern
    AdjacencyEdge("nurnberg", "erlangen", 15, "S-Bahn"),
    AdjacencyEdge("nurnberg", "furth", 10, "S-Bahn"),
    AdjacencyEdge("nurnberg", "bamberg", 40, "RE/IC"),
    # Bremen / Niedersachsen NW
    AdjacencyEdge("bremen", "oldenburg", 45, "RE/IC"),
    AdjacencyEdge("bremen", "delmenhorst", 15, "S-Bahn"),
    # Baden / Pfalz
    AdjacencyEdge("karlsruhe", "pforzheim", 25, "RE/IC"),
    AdjacencyEdge("mannheim", "heidelberg", 15, "S-Bahn"),
    AdjacencyEdge("mannheim", "ludwigshafen", 5, "RE/IC"),
    AdjacencyEdge("freiburg", "offenburg", 30, "RE/IC"),
    # Münster / OWL
    AdjacencyEdge("munster", "osnabruck", 45, "RE/IC"),
    AdjacencyEdge("bielefeld", "paderborn", 50, "RE/IC"),
    # AT (Wien commuter belt — useful for EU-wide composition;
    # operator may scope out for Germany-only deploy but the
    # data is here)
    AdjacencyEdge("wien", "wiener neustadt", 45, "RE/IC"),
    AdjacencyEdge("wien", "st polten", 35, "RE/IC"),
    # CH (Zürich + Bern + Basel — same caveat as AT)
    AdjacencyEdge("zurich", "winterthur", 25, "S-Bahn"),
    AdjacencyEdge("zurich", "zug", 30, "RE/IC"),
    AdjacencyEdge("basel", "liestal", 15, "S-Bahn"),
)


# Common cross-language aliases for DACH cities. A user might
# enter "Munich" (EN) while the canonical graph key is "munchen"
# (de-accented). Same for "Cologne" → "koln", "Vienna" → "wien",
# "Zurich" → "zurich" (no alias needed), "Hanover" → "hannover",
# "Nuremberg" → "nurnberg", "Brunswick" → "braunschweig", etc.
# The alias table maps the de-accented form of the foreign-language
# name to the canonical key.
# Public alias table — consumed by job_index._norm_location so the
# index storage uses canonical keys regardless of which spelling
# (English exonym, German oe/ue/ae alternate, ISO short form) the
# job posting carried. Quality-audit (2026-05-21): promoted from
# the original leading-underscore `_CITY_ALIASES` to a public name
# because cross-module consumers shouldn't reach into private
# symbols. The old name remains as an alias for backward
# compatibility with any external code reading the dataset.
CITY_ALIASES: dict[str, str] = {
    # English exonyms
    "munich": "munchen",
    "cologne": "koln",
    "hanover": "hannover",
    "nuremberg": "nurnberg",
    "brunswick": "braunschweig",
    "vienna": "wien",
    # Common German alternate spellings (oe / ue / ae for umlauts)
    "muenchen": "munchen",
    "koeln": "koln",
    "duesseldorf": "dusseldorf",
    "luebeck": "lubeck",
    "lueneburg": "luneburg",
    "nuernberg": "nurnberg",
    "fuerth": "furth",
    "wuerzburg": "wurzburg",
    "ingolstadt": "ingolstadt",
    "muenster": "munster",
    "osnabrueck": "osnabruck",
    "saarbruecken": "saarbrucken",
    "tuebingen": "tubingen",
    "goettingen": "gottingen",
    "stadtkroenung": "stadtkronung",
    # Common short forms / abbreviations
    "ffm": "frankfurt",
    "muc": "munchen",
    "hh": "hamburg",
    "bln": "berlin",
}

# Backward-compatible alias for the original private name. Kept
# so any external tests / tooling that imported the old symbol
# still resolves. New consumers should use ``CITY_ALIASES``.
_CITY_ALIASES = CITY_ALIASES


def normalise_city(text: str | None) -> str:
    """Public city-key normaliser. Quality-audit (2026-05-21):
    promoted from ``_norm_city`` so cross-module consumers don't
    reach into private symbols. The private name remains as a
    backward-compat alias."""

    if not text:
        return ""
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.casefold().strip()
    first = folded.split(",")[0].strip()
    normalised = re.sub(r"\s+", " ", first)
    return CITY_ALIASES.get(normalised, normalised)


def _norm_city(text: str | None) -> str:
    """Backward-compat alias for :func:`normalise_city`. New
    consumers should use the public name."""

    return normalise_city(text)


def _build_adjacency_map() -> dict[str, tuple[AdjacencyEdge, ...]]:
    """Pre-compute a city → tuple-of-edges lookup table. Each edge
    appears under both endpoints (the graph is undirected)."""

    out: dict[str, list[AdjacencyEdge]] = {}
    for edge in _EDGES:
        out.setdefault(edge.a, []).append(edge)
        out.setdefault(edge.b, []).append(edge)
    return {k: tuple(v) for k, v in out.items()}


_ADJACENCY: dict[str, tuple[AdjacencyEdge, ...]] = _build_adjacency_map()


def adjacent_cities(
    city: str | None, *, max_minutes: int | None = None
) -> tuple[AdjacencyEdge, ...]:
    """Return the commute-range neighbours of ``city`` as a tuple of
    :class:`AdjacencyEdge`. Direction-agnostic — for an edge ``(a,
    b)``, ``adjacent_cities("a")`` returns the edge with ``b`` as
    the neighbour endpoint, and vice versa. If ``max_minutes`` is
    given, edges with ``minutes > max_minutes`` are filtered out.

    Returns an empty tuple for unknown / empty input.
    """

    key = _norm_city(city)
    if not key:
        return ()
    edges = _ADJACENCY.get(key, ())
    if max_minutes is not None:
        edges = tuple(e for e in edges if e.minutes <= max_minutes)
    return edges


def neighbour_keys(city: str | None, *, max_minutes: int | None = None) -> tuple[str, ...]:
    """Convenience: just the normalised keys of the neighbour
    endpoints, with ``city`` itself excluded."""

    key = _norm_city(city)
    if not key:
        return ()
    edges = adjacent_cities(city, max_minutes=max_minutes)
    out: list[str] = []
    seen: set[str] = set()
    for edge in edges:
        other = edge.b if edge.a == key else edge.a
        if other == key or other in seen:
            continue
        seen.add(other)
        out.append(other)
    return tuple(out)


def all_known_cities() -> tuple[str, ...]:
    """All city keys that appear in the adjacency graph, sorted."""

    return tuple(sorted(_ADJACENCY.keys()))


def edge_count() -> int:
    """Number of curated symmetric edges. Useful for sanity checks."""

    return len(_EDGES)
