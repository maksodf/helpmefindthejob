"""Stronger deduplication for discovered jobs.

The matcher is purely Python — no external libraries. It returns a
``DuplicateMatch`` with a reason code so callers can explain *why* a
job was treated as a duplicate.

Match strategies (any one match → duplicate):

- ``url``: normalised source URL equality.
- ``ats_id``: same vendor + same external ATS id.
- ``title_company``: identical normalised title + same company.
- ``title_location``: identical normalised title + identical location.
- ``description_shingle``: ≥80% Jaccard overlap on 3-word shingles
  (only triggers when both descriptions have ≥120 chars to avoid
  matching short snippets).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import DiscoveredJob


_DESCRIPTION_SHINGLE_MIN_CHARS = 300
_DESCRIPTION_SHINGLE_THRESHOLD = 0.80
_DESCRIPTION_TITLE_THRESHOLD = 0.55


_TRACKING_KEYS = {
    # UTM family — campaign attribution.
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_name",
    # Greenhouse referrer params.
    "gh_src",
    "gh_jid",
    # Generic referrer / source query params.
    "ref",
    "source",
    "src",
    "referrer",
    "referer",
    # Ad-click identifiers — Google + Facebook + Microsoft + Bing + LinkedIn.
    "gclid",
    "gclsrc",
    "fbclid",
    "msclkid",
    "li_fat_id",
    "trk",
    "trkinfo",
    # Aggregator click-through identifiers.
    "vjk",     # Indeed view-job key (changes per session)
    "from",    # Indeed / StepStone share-from
    "tk",      # Indeed token
    "promoted",
}


@dataclass(frozen=True)
class DuplicateMatch:
    duplicate_id: str
    reason: str
    explanation: str


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").casefold()
    netloc = parsed.netloc.casefold()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/").casefold()
    keep_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key.casefold() not in _TRACKING_KEYS
    ]
    keep_query.sort()
    return urlunparse((scheme, netloc, path or "/", "", urlencode(keep_query), ""))


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    cleaned = re.sub(r"\s+", " ", title.strip().casefold())
    cleaned = re.sub(r"\s*\((m/w/d|m/f/d|f/m/d|all genders|all-gender|d/f/m)\)\s*", " ", cleaned)
    cleaned = re.sub(r"\s*[-–—|/]+\s*$", "", cleaned)
    cleaned = re.sub(r"[^\w\säöüß]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


# Cross-locale title alignment: the German and English forms of the
# same job rarely share enough word-tokens for a shingle match (e.g.
# "Senior Software Engineer" vs "Senior Softwareentwickler"), but
# stripping the de↔en glossary terms below back to a common token set
# gives us a reliable signal that they're the same role.
_DE_EN_ROLE_GLOSSARY: dict[str, str] = {
    # left = lemma we want to keep; right = synonym to fold into it.
    # Both directions are added at runtime.
    "softwareentwickler": "software engineer",
    "softwareentwicklerin": "software engineer",
    "entwickler": "developer",
    "entwicklerin": "developer",
    "ingenieur": "engineer",
    "ingenieurin": "engineer",
    "fachkraft": "specialist",
    "mitarbeiter": "associate",
    "mitarbeiterin": "associate",
    "leiter": "lead",
    "leiterin": "lead",
    "leitung": "lead",
    "manager": "manager",
    "managerin": "manager",
    "berater": "consultant",
    "beraterin": "consultant",
    "vertrieb": "sales",
    "marketing": "marketing",
    "datenanalyst": "data analyst",
    "datenanalystin": "data analyst",
    "datenwissenschaftler": "data scientist",
    "datenwissenschaftlerin": "data scientist",
    "ingenieur datenverarbeitung": "data engineer",
    "personalreferent": "hr business partner",
    "personalreferentin": "hr business partner",
    "personalmanagement": "hr",
    "rechtsanwalt": "lawyer",
    "rechtsanwältin": "lawyer",
    "krankenpfleger": "nurse",
    "krankenpflegerin": "nurse",
    "pflegefachkraft": "nurse",
    "facharzt": "specialist physician",
    "ärztin": "physician",
    "arzt": "physician",
    "lehrer": "teacher",
    "lehrerin": "teacher",
    "redakteur": "editor",
    "redakteurin": "editor",
    "journalist": "journalist",
    "journalistin": "journalist",
}


def normalize_title_cross_locale(title: str | None) -> str:
    """Normalize a title and fold de/en role synonyms.

    Returns a *token-sorted* canonical string so two titles that mean
    the same thing in different languages collapse to the same key.
    """

    base = normalize_title(title)
    if not base:
        return ""
    tokens = base.split()
    folded: list[str] = []
    for tok in tokens:
        # Apply both directions of the glossary.
        replacement = _DE_EN_ROLE_GLOSSARY.get(tok, tok)
        # Strip common suffixes (-in feminine form) before matching.
        if tok.endswith("in") and tok[:-2] in _DE_EN_ROLE_GLOSSARY:
            replacement = _DE_EN_ROLE_GLOSSARY[tok[:-2]]
        folded.extend(replacement.split())
    folded = [t for t in folded if t]
    folded.sort()
    return " ".join(folded)


def normalize_location(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value.strip().casefold())
    return re.sub(r"[^\w\säöüß]+", " ", cleaned).strip()


def shingles(text: str | None, *, n: int = 3) -> set[tuple[str, ...]]:
    if not text:
        return set()
    tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
    if len(tokens) < n:
        return set()
    return {tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def jaccard(a: set[tuple[str, ...]], b: set[tuple[str, ...]]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def ats_pair(job: DiscoveredJob) -> tuple[str, str] | None:
    structured = job.structured_data or {}
    ats = structured.get("ats")
    ats_id = structured.get("ats_id")
    if isinstance(ats, str) and isinstance(ats_id, str) and ats_id.strip():
        return ats.casefold(), ats_id.strip().casefold()
    return None


def effective_freshness_at(job: DiscoveredJob):
    """Return the freshest signal we have about this job.

    A job that was first seen 3 weeks ago on the company's career page
    but re-found yesterday on Indeed should rank as "yesterday-fresh,"
    not "3-weeks-stale." We pick the max of ``discovered_at`` and any
    ``also_seen_at[*].seen_at`` timestamps.
    """
    from datetime import datetime, timezone  # local import to keep top-of-file lean

    candidates = []
    if job.discovered_at is not None:
        candidates.append(job.discovered_at)
    for entry in (job.also_seen_at or {}).values():
        if not isinstance(entry, dict):
            continue
        seen = entry.get("seen_at") or entry.get("found_at") or entry.get("at")
        if isinstance(seen, datetime):
            candidates.append(seen)
        elif isinstance(seen, str):
            try:
                candidates.append(datetime.fromisoformat(seen.replace("Z", "+00:00")))
            except ValueError:
                continue
    if not candidates:
        return None
    # Coerce naive datetimes to UTC so max() doesn't mix offsets.
    norm = [c if c.tzinfo else c.replace(tzinfo=timezone.utc) for c in candidates]
    return max(norm)


def find_duplicate(candidate: DiscoveredJob, existing: Iterable[DiscoveredJob]) -> DuplicateMatch | None:
    candidate_url = normalize_url(candidate.source_url)
    candidate_title = normalize_title(candidate.title)
    candidate_title_cross = normalize_title_cross_locale(candidate.title)
    candidate_location = normalize_location(candidate.location or "")
    candidate_ats = ats_pair(candidate)
    candidate_description = (candidate.raw_description or "").strip()
    candidate_shingles = (
        shingles(candidate_description)
        if len(candidate_description) >= _DESCRIPTION_SHINGLE_MIN_CHARS
        else set()
    )

    for other in existing:
        if other.id == candidate.id and other.user_id == candidate.user_id:
            continue
        if other.user_id != candidate.user_id:
            continue
        if candidate_url and normalize_url(other.source_url) == candidate_url:
            return DuplicateMatch(
                duplicate_id=other.id,
                reason="url",
                explanation="Same source URL.",
            )
        other_ats = ats_pair(other)
        if candidate_ats and other_ats and candidate_ats == other_ats:
            return DuplicateMatch(
                duplicate_id=other.id,
                reason="ats_id",
                explanation=f"Same {candidate_ats[0]} job id ({candidate_ats[1]}).",
            )
        other_title = normalize_title(other.title)
        if (
            candidate_title
            and candidate_title == other_title
            and other.company_id == candidate.company_id
        ):
            return DuplicateMatch(
                duplicate_id=other.id,
                reason="title_company",
                explanation="Same title at the same company.",
            )
        other_location = normalize_location(other.location or "")
        if (
            candidate_title
            and candidate_title == other_title
            and candidate_location
            and candidate_location == other_location
        ):
            return DuplicateMatch(
                duplicate_id=other.id,
                reason="title_location",
                explanation="Same title and location.",
            )
        # Cross-locale title alignment: same role posted in DE + EN
        # collapses if the folded-glossary canonical strings match AND
        # the location matches (so we don't accidentally merge two
        # genuinely different roles that happen to share keywords).
        other_title_cross = normalize_title_cross_locale(other.title)
        if (
            candidate_title_cross
            and other_title_cross
            and candidate_title_cross == other_title_cross
            and candidate_location
            and candidate_location == other_location
            and candidate_title_cross != candidate_title  # only fire when folding actually changed something
        ):
            return DuplicateMatch(
                duplicate_id=other.id,
                reason="title_cross_locale",
                explanation="Same role across DE/EN at same location.",
            )
        if candidate_shingles:
            other_description = (other.raw_description or "").strip()
            if len(other_description) >= _DESCRIPTION_SHINGLE_MIN_CHARS:
                similarity = jaccard(candidate_shingles, shingles(other_description))
                title_similarity = SequenceMatcher(
                    None, candidate_title, other_title or normalize_title(other.title)
                ).ratio() if candidate_title else 0.0
                if (
                    similarity >= _DESCRIPTION_SHINGLE_THRESHOLD
                    and title_similarity >= _DESCRIPTION_TITLE_THRESHOLD
                ):
                    return DuplicateMatch(
                        duplicate_id=other.id,
                        reason="description_shingle",
                        explanation=f"Description {int(similarity * 100)}% identical and titles align.",
                    )
    return None
