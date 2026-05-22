# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Concrete :class:`JobAggregatorProvider` implementations.

Each provider here is **no-auth**: no API key, no signup, no card. They
ship default-on. Free-signup providers (Adzuna, EURES, Bundesagentur)
live in :mod:`company_discovery.aggregator_providers_signup` and are
gated behind env-var keys.

Pattern shared by every provider:
- ``fetcher`` kwarg in ``__init__`` — testable fake with
  ``.get(url, headers, params) -> (status, body)``.
- Production fetcher uses stdlib ``urllib.request``; default User-Agent
  identifies us so feed maintainers can opt out.
- All HTTP errors swallowed → return ``[]``. Never raise.
- ``query`` is whatever the user typed; providers don't try to be
  clever about it. Persona/CV expansion happens upstream.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .aggregators import (
    AggregatedJob,
    ProviderAttribution,
    location_matches,
    seniority_conflicts,
    title_matches_query_family,
)

_USER_AGENT = "Helpmefindthejob/0.1 (+https://app.helpmefindthejob.com/about)"


def _strip_html(html_text: str) -> str:
    if not html_text:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_text)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _query_tokens(query: str) -> list[str]:
    return [tok for tok in re.findall(r"\w+", (query or "").casefold()) if tok]


def _matches(haystack_parts: list[str], tokens: list[str]) -> bool:
    """Loose OR-match: any token present in any haystack part qualifies.

    Keeping this lenient is deliberate — providers that lack server-side
    search (Arbeitnow, Muse, WWR, HN) would otherwise return zero results
    for any multi-word query, since our caller passes the raw user
    phrase (e.g. "healthcare policy consulting") rather than running
    keyword expansion. Phase 2 adds CV-driven token reduction; until
    then, OR-match is the safer default.
    """

    if not tokens:
        return True
    haystack = " ".join(part.casefold() for part in haystack_parts if part)
    return any(tok in haystack for tok in tokens)


# ---------- shared transport ----------------------------------------------


class _StdlibFetcher:
    def get(
        self, url: str, headers: dict[str, str] | None = None, params: dict[str, str] | None = None
    ) -> tuple[int, str]:
        merged = {"User-Agent": _USER_AGENT, "Accept": "application/json,*/*;q=0.5"}
        if headers:
            merged.update(headers)
        full_url = url if not params else f"{url}?{urlencode(params)}"
        request = Request(full_url, headers=merged)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            return exc.code, ""
        except (URLError, OSError):
            return 0, ""


# ---------- Arbeitnow ------------------------------------------------------


@dataclass
class ArbeitnowProvider:
    """Arbeitnow public job-board API. Tech-heavy, EU + remote."""

    name: str = "arbeitnow"
    base_url: str = "https://www.arbeitnow.com/api/job-board-api"
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="arbeitnow",
            label="Arbeitnow",
            url="https://www.arbeitnow.com/",
        ),
    )
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        status, body = self.fetcher.get(self.base_url)  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        items = payload.get("data") or []
        tokens = _query_tokens(query)
        out: list[AggregatedJob] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "")
            company = str(item.get("company_name") or "")
            description = _strip_html(str(item.get("description") or ""))
            loc = str(item.get("location") or "")
            tag_list = item.get("tags") or []
            tags = " ".join(tag_list) if isinstance(tag_list, list) else ""
            if not _matches([title, company, description, tags], tokens):
                continue
            if location and not location_matches(location, loc):
                # Strict substring + diacritic-fold + DE/EU alias match.
                # The previous "or remote in text" escape hatch leaked
                # remote-anywhere jobs into specific-location searches
                # (a Berlin search returned remote-EU roles); see also
                # JobAggregationEngine's remote-only-provider skip.
                continue
            if seniority_conflicts(query, title):
                # Caller asked for senior; this is a junior/intern role
                # (or vice versa). OR-token matching alone would let
                # 'Junior Backend Engineer' pass a 'senior backend
                # engineer' search.
                continue
            if not title_matches_query_family(query, title):
                # 'marketing manager' query was passing 'HR Manager'
                # because OR-token treats 'manager' as a hit. Require
                # at least one distinctive (non-generic) token from
                # the query to appear in the title.
                continue
            posted_iso = item.get("created_at")
            posted = None
            if isinstance(posted_iso, (int, float)):
                posted = datetime.fromtimestamp(int(posted_iso), tz=timezone.utc)
            elif isinstance(posted_iso, str):
                posted = _parse_iso(posted_iso)
            out.append(
                AggregatedJob(
                    title=title,
                    company_name=company,
                    source=self.name,
                    source_url=str(item.get("url") or ""),
                    location=loc or None,
                    description=description or None,
                    posted_at=posted,
                    raw={"slug": item.get("slug"), "tags": tag_list},
                )
            )
            if len(out) >= limit:
                break
        return out


# ---------- The Muse -------------------------------------------------------


@dataclass
class MuseProvider:
    """The Muse public jobs API. Global tech + media + consumer."""

    name: str = "muse"
    base_url: str = "https://www.themuse.com/api/public/jobs"
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="muse",
            label="The Muse",
            url="https://www.themuse.com/",
        ),
    )
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        params = {"page": "0", "descending": "true"}
        if location:
            params["location"] = location
        status, body = self.fetcher.get(self.base_url, params=params)  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        results = payload.get("results") or []
        tokens = _query_tokens(query)
        out: list[AggregatedJob] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("name") or "")
            company_obj = item.get("company") or {}
            company = str(company_obj.get("name") or "") if isinstance(company_obj, dict) else ""
            description = _strip_html(str(item.get("contents") or ""))
            loc_list = item.get("locations") or []
            loc = ", ".join(str(l.get("name", "")) for l in loc_list if isinstance(l, dict)) or None
            if not _matches([title, company, description], tokens):
                continue
            # The Muse API loosely matches the ``location`` param, so we
            # re-check client-side. Without this, a Berlin search would
            # accept "Berlin, GA" or worse "anywhere" results.
            if location and not location_matches(location, loc or ""):
                continue
            if seniority_conflicts(query, title):
                continue
            if not title_matches_query_family(query, title):
                continue
            posted = _parse_iso(item.get("publication_date"))
            out.append(
                AggregatedJob(
                    title=title,
                    company_name=company,
                    source=self.name,
                    source_url=str(item.get("refs", {}).get("landing_page") or ""),
                    location=loc,
                    description=description or None,
                    posted_at=posted,
                    raw={"id": item.get("id"), "categories": item.get("categories")},
                )
            )
            if len(out) >= limit:
                break
        return out


# ---------- Remotive -------------------------------------------------------


@dataclass
class RemotiveProvider:
    """Remotive remote-only job feed."""

    name: str = "remotive"
    base_url: str = "https://remotive.com/api/remote-jobs"
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="remotive",
            label="Remotive",
            url="https://remotive.com/",
        ),
    )
    # Engine skips this provider when the user's saved search names
    # a specific (non-remote) location.
    remote_only: bool = True
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        params = {}
        if query:
            params["search"] = query
        status, body = self.fetcher.get(self.base_url, params=params)  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        jobs = payload.get("jobs") or []
        out: list[AggregatedJob] = []
        for item in jobs:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "")
            if not title:
                continue
            # Remotive's server-side ``search=`` is fairly permissive —
            # it matches keywords against the full posting body, so a
            # query like 'senior data scientist' returns Copywriter and
            # Customer Support Manager listings whose description
            # happens to mention 'data' or 'senior'. Apply our standard
            # client-side filters as defense in depth.
            if seniority_conflicts(query, title):
                continue
            if not title_matches_query_family(query, title):
                continue
            posted = _parse_iso(item.get("publication_date"))
            out.append(
                AggregatedJob(
                    title=title,
                    company_name=str(item.get("company_name") or ""),
                    source=self.name,
                    source_url=str(item.get("url") or ""),
                    location=str(item.get("candidate_required_location") or "Remote"),
                    description=_strip_html(str(item.get("description") or "")),
                    posted_at=posted,
                    salary_hint=str(item.get("salary") or "") or None,
                    raw={"id": item.get("id"), "category": item.get("category")},
                )
            )
            if len(out) >= limit:
                break
        return out


# ---------- WeWorkRemotely (RSS) -------------------------------------------


@dataclass
class WeWorkRemotelyProvider:
    """WeWorkRemotely category RSS feeds (no auth)."""

    name: str = "weworkremotely"
    feeds: tuple[str, ...] = (
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-product-jobs.rss",
        "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
        "https://weworkremotely.com/categories/remote-business-jobs.rss",
    )
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="weworkremotely",
            label="We Work Remotely",
            url="https://weworkremotely.com/",
        ),
    )
    # Remote-only feed; engine skips this provider on specific-location
    # searches — see JobAggregationEngine.search.
    remote_only: bool = True
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        tokens = _query_tokens(query)
        out: list[AggregatedJob] = []
        for feed in self.feeds:
            status, body = self.fetcher.get(feed)  # type: ignore[attr-defined]
            if status != 200 or not body:
                continue
            try:
                root = ET.fromstring(body)
            except ET.ParseError:
                continue
            # Standard RSS — every <item>
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = item.findtext("pubDate")
                description_html = item.findtext("description") or ""
                description = _strip_html(description_html)
                # Title in WWR is "Company: Role"
                company = ""
                role = title
                if ": " in title:
                    company, _, role = title.partition(": ")
                if not _matches([role, company, description], tokens):
                    continue
                if seniority_conflicts(query, role):
                    continue
                if not title_matches_query_family(query, role):
                    continue
                posted = None
                if pub:
                    try:
                        # RSS pubDate format: "Sat, 09 May 2026 17:30:00 +0000"
                        from email.utils import parsedate_to_datetime

                        posted = parsedate_to_datetime(pub)
                    except (TypeError, ValueError):
                        posted = None
                out.append(
                    AggregatedJob(
                        title=role,
                        company_name=company,
                        source=self.name,
                        source_url=link,
                        location="Remote",
                        description=description or None,
                        posted_at=posted,
                        raw={"feed": feed},
                    )
                )
                if len(out) >= limit:
                    return out
        return out


# ---------- Hacker News "Who is hiring?" -----------------------------------


@dataclass
class HackerNewsHiringProvider:
    """Latest 'Who is hiring?' thread parsed via the Algolia HN API.

    Each top-level comment in the monthly hiring thread is one
    company's job ad. Format is loose (`<companyish> | <role> | …`)
    but we extract enough to surface a useful row.
    """

    name: str = "hn_hiring"
    search_url: str = "https://hn.algolia.com/api/v1/search"
    item_url: str = "https://hn.algolia.com/api/v1/items"
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="hn_hiring",
            label="Hacker News “Who is hiring?”",
            url="https://news.ycombinator.com/",
        ),
    )
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        # Find the latest "Ask HN: Who is hiring?" thread.
        status, body = self.fetcher.get(
            self.search_url,
            params={  # type: ignore[attr-defined]
                "query": "Ask HN: Who is hiring?",
                "tags": "story,author_whoishiring",
                "hitsPerPage": "1",
            },
        )
        if status != 200 or not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        hits = payload.get("hits") or []
        if not hits:
            return []
        story_id = hits[0].get("objectID")
        if not story_id:
            return []
        status, body = self.fetcher.get(f"{self.item_url}/{story_id}")  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        try:
            thread = json.loads(body)
        except (TypeError, ValueError):
            return []
        comments = thread.get("children") or []
        tokens = _query_tokens(query)
        out: list[AggregatedJob] = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            text = _strip_html(str(comment.get("text") or ""))
            if not text:
                continue
            if not _matches([text], tokens):
                continue
            if location and not location_matches(location, text):
                # Strict substring + diacritic-fold + DE/EU alias match.
                # Same fix as ArbeitnowProvider. The previous "remote in
                # text" OR-clause leaked remote-anywhere listings into
                # specific-location searches.
                continue
            # First line is usually "<Company> | <Role> | <Location>" pipe-delimited
            # but real posters use other shapes: "<Co> | <Role> | <Full-Time> | <Loc>"
            # or "<Co> | <Role> | <Remote>" or just "<Co> | <Role>". When the
            # third part is a work-type / arrangement word (Full-Time, Contract,
            # Onsite, Remote, Hybrid, etc.), skip past it to the next part.
            first_line = text.split("\n", 1)[0]
            parts = [p.strip() for p in re.split(r"\s*\|\s*", first_line) if p.strip()]
            company = parts[0] if parts else "Hacker News listing"
            role = parts[1] if len(parts) > 1 else first_line[:120]
            non_location_words = {
                "full-time",
                "full time",
                "fulltime",
                "part-time",
                "part time",
                "parttime",
                "contract",
                "contractor",
                "freelance",
                "permanent",
                "temporary",
                "intern",
                "internship",
                "h1b",
                "visa",
                "onsite",
                "on-site",
                "on site",
                "hybrid",
                "remote",
            }
            loc_str: str | None = None
            for candidate in parts[2:]:
                if candidate.casefold() not in non_location_words:
                    loc_str = candidate
                    break
            if seniority_conflicts(query, role):
                continue
            if not title_matches_query_family(query, role):
                continue
            posted = None
            created_iso = comment.get("created_at")
            if isinstance(created_iso, str):
                posted = _parse_iso(created_iso)
            out.append(
                AggregatedJob(
                    title=role[:160],
                    company_name=company[:120],
                    source=self.name,
                    source_url=f"https://news.ycombinator.com/item?id={comment.get('id', story_id)}",
                    location=loc_str,
                    description=text[:1500],
                    posted_at=posted,
                    raw={"thread_id": story_id, "comment_id": comment.get("id")},
                )
            )
            if len(out) >= limit:
                break
        return out


# ---------- EURES (EU public employment service) ----------------------------


@dataclass
class EuresProvider:
    """EU's official public employment service.

    **Status (verified 2026-05-09): EURES robots.txt currently blocks
    server-side API access. Direct calls return 403.** The provider class
    is kept here for a future operator-managed proxy (e.g. routing
    through a residential session cookie) but it is **not** wired into
    ``default_no_auth_providers()``. Activate explicitly via a custom
    boot-time provider list when you have a working transport.

    Original docstring (kept for reference)
    ----------------------------------------
    Uses the public ``searchengine`` REST endpoint that powers
    ec.europa.eu/eures. Returns job postings across all EU member
    states. Known data shape (subset of fields we use):

        {
          "jvs": [
            {
              "id": "12345",
              "title": "Senior Backend Engineer",
              "employer": {"name": "Acme Co"},
              "locations": [{"city": "Berlin", "country": "Germany"}],
              "publicationStartDate": "2026-05-01",
              "description": "<p>...</p>",
              "applicationUrl": "https://employer.example/jobs/42",
            }, ...
          ]
        }

    Falls back to JSON-LD parsing if the live shape changes.
    """

    name: str = "eures"
    base_url: str = "https://ec.europa.eu/eures/eures-apps/searchengine/page/jv-search/search"
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="eures",
            label="EURES — European Employment Services",
            url="https://ec.europa.eu/eures/",
        ),
    )
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        # EURES POST endpoint expects JSON; many integrations use the
        # GET search front-end. We use the GET HTML+JSON-LD path to keep
        # this dependency-free and resilient to API changes.
        params = {"keywords": query[:120]} if query else {}
        if location:
            params["locationCodes"] = location[:80]
        params["sortBy"] = "PUBLICATION_DATE_DESC"
        status, body = self.fetcher.get(self.base_url, params=params)  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        # The live page embeds an ld+json with each job posting. Parse
        # those out — same defensive pattern as the company-page scanner.
        jobs: list[AggregatedJob] = []
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>',
            body,
            re.DOTALL | re.IGNORECASE,
        ):
            try:
                payload = json.loads(match.group(1))
            except (TypeError, ValueError):
                continue
            entries = payload if isinstance(payload, list) else [payload]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("@type", "")).casefold() != "jobposting":
                    continue
                title = str(entry.get("title") or "").strip()
                if not title:
                    continue
                if seniority_conflicts(query, title):
                    continue
                if not title_matches_query_family(query, title):
                    continue
                org = entry.get("hiringOrganization") or {}
                company = (org.get("name") if isinstance(org, dict) else "") or ""
                loc_list = entry.get("jobLocation") or []
                if isinstance(loc_list, dict):
                    loc_list = [loc_list]
                loc_text = None
                for loc in loc_list:
                    if not isinstance(loc, dict):
                        continue
                    addr = loc.get("address") or {}
                    if isinstance(addr, dict):
                        bits = [
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("addressCountry"),
                        ]
                        loc_text = ", ".join(str(b) for b in bits if b)
                        break
                description = _strip_html(str(entry.get("description") or ""))
                posted = _parse_iso(entry.get("datePosted"))
                jobs.append(
                    AggregatedJob(
                        title=title,
                        company_name=str(company),
                        source=self.name,
                        source_url=str(
                            entry.get("url")
                            or entry.get("hiringOrganization", {}).get("sameAs", "")
                            or ""
                        ),
                        location=loc_text,
                        description=description or None,
                        posted_at=posted,
                        raw={"identifier": entry.get("identifier")},
                    )
                )
                if len(jobs) >= limit:
                    return jobs
        return jobs


# ---------- Bundesagentur für Arbeit (German federal employment service) ----


@dataclass
class BundesagenturProvider:
    """Germany's federal employment-agency public job-search API.

    Documented at https://jobsuche.api.bund.dev/. The free API key is
    issued automatically (just paste any well-formed UUID into the
    `X-API-Key` header — the API treats it as a soft client identifier).
    To stay safe, we ship a default DEV-issued key that anyone can use,
    but operators are encouraged to override via
    ``HELPMEFINDTHEJOB_BUNDESAGENTUR_API_KEY``.
    """

    name: str = "bundesagentur"
    base_url: str = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
    api_key: str = "jobboerse-jobsuche"  # documented public token
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="bundesagentur",
            label="Bundesagentur für Arbeit",
            url="https://www.arbeitsagentur.de/jobsuche/",
        ),
    )
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        params: dict[str, str] = {"size": str(min(limit, 50))}
        if query:
            params["was"] = query[:120]
        if location:
            params["wo"] = location[:80]
        params["sort"] = "veroeffdatum"
        headers = {"X-API-Key": self.api_key, "Accept": "application/json"}
        status, body = self.fetcher.get(self.base_url, headers=headers, params=params)  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        items = payload.get("stellenangebote") or []
        out: list[AggregatedJob] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("titel") or entry.get("beruf") or "").strip()
            if not title:
                continue
            if seniority_conflicts(query, title):
                # Bundesagentur's `was=` matches keywords, not seniority,
                # so a 'senior backend' query can still return junior
                # listings. Defense in depth.
                continue
            if not title_matches_query_family(query, title):
                continue
            company = str(entry.get("arbeitgeber") or "").strip()
            ext_id = str(entry.get("hashId") or entry.get("refnr") or "")
            absolute = (
                f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ext_id}" if ext_id else ""
            )
            loc_obj = entry.get("arbeitsort") or {}
            loc_text = None
            if isinstance(loc_obj, dict):
                bits = [
                    loc_obj.get("ort"),
                    loc_obj.get("plz"),
                    loc_obj.get("region"),
                    loc_obj.get("land"),
                ]
                loc_text = ", ".join(str(b) for b in bits if b) or None
            posted = _parse_iso(entry.get("aktuelleVeroeffentlichungsdatum"))
            out.append(
                AggregatedJob(
                    title=title,
                    company_name=company,
                    source=self.name,
                    source_url=absolute,
                    location=loc_text,
                    description=str(entry.get("kundennummerHash") or "") or None,
                    posted_at=posted,
                    raw={"hashId": ext_id},
                )
            )
            if len(out) >= limit:
                break
        return out


@dataclass
class AdzunaProvider:
    """Adzuna public jobs API. Free tier: 250 calls/month, 25 results/call.

    Auth: ``app_id`` + ``app_key`` query params (sign up at
    https://developer.adzuna.com — no card, instant). Country code
    selects the data set; the per-call ``country`` defaults to ``de``
    for our DACH-leaning user base but the operator can override via
    ``HELPMEFINDTHEJOB_ADZUNA_COUNTRY``.

    Attribution: required on UI surfaces — already in ProviderAttribution.
    """

    name: str = "adzuna"
    app_id: str = ""
    app_key: str = ""
    country: str = "de"
    base_url: str = "https://api.adzuna.com/v1/api/jobs"
    attribution: ProviderAttribution | None = field(
        default_factory=lambda: ProviderAttribution(
            name="adzuna",
            label="Adzuna",
            url="https://www.adzuna.com/",
        ),
    )
    fetcher: object = field(default_factory=_StdlibFetcher)

    def search(
        self, *, query: str, location: str | None, limit: int = 25, persona_id: str | None = None
    ) -> list[AggregatedJob]:
        if not self.app_id or not self.app_key:
            return []
        country = (self.country or "de").lower()
        url = f"{self.base_url}/{country}/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": str(min(50, max(5, limit))),
            "content-type": "application/json",
        }
        if query:
            params["what"] = query
        if location:
            params["where"] = location
        status, body = self.fetcher.get(url, params=params)  # type: ignore[attr-defined]
        if status != 200 or not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        results = payload.get("results") or []
        out: list[AggregatedJob] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if seniority_conflicts(query, title):
                continue
            if not title_matches_query_family(query, title):
                continue
            company_obj = item.get("company") or {}
            company = (
                str(company_obj.get("display_name") or "") if isinstance(company_obj, dict) else ""
            )
            loc_obj = item.get("location") or {}
            loc = (
                str(loc_obj.get("display_name") or "")
                if isinstance(loc_obj, dict)
                else (str(loc_obj) if loc_obj else "")
            ) or None
            description = _strip_html(str(item.get("description") or ""))
            posted = _parse_iso(item.get("created"))
            out.append(
                AggregatedJob(
                    title=title,
                    company_name=company,
                    source=self.name,
                    source_url=str(item.get("redirect_url") or ""),
                    location=loc,
                    description=description or None,
                    posted_at=posted,
                    raw={
                        "id": item.get("id"),
                        "category": (item.get("category") or {}).get("label"),
                    },
                )
            )
            if len(out) >= limit:
                break
        return out


def adzuna_from_env(env: dict[str, str] | None = None) -> AdzunaProvider | None:
    """Construct an AdzunaProvider from env vars, or return None if unset.

    ``env`` is injectable for tests; production calls without args and
    reads ``os.environ``."""

    import os
    import warnings

    src = env if env is not None else os.environ

    def _pick(new_name: str, legacy_name: str) -> str:
        # Local, dict-based equivalent of env_compat.get_env. Kept inline
        # because this builder accepts any Mapping (tests inject a dict);
        # going through os.environ would defeat the injection contract.
        value = src.get(new_name)
        if value is not None:
            return value
        legacy_value = src.get(legacy_name)
        if legacy_value is not None:
            warnings.warn(
                f"Env var {legacy_name!r} is deprecated; rename to "
                f"{new_name!r}. The legacy prefix is accepted with this "
                "DeprecationWarning through Phase 2; it is removed in "
                "Phase 3 — see docs/deployment-recipe.md migration path.",
                DeprecationWarning,
                stacklevel=2,
            )
            return legacy_value
        return ""

    app_id = _pick("HELPMEFINDTHEJOB_ADZUNA_APP_ID", "HELPMEFINDTHEJOB_ADZUNA_APP_ID").strip()
    app_key = _pick("HELPMEFINDTHEJOB_ADZUNA_APP_KEY", "HELPMEFINDTHEJOB_ADZUNA_APP_KEY").strip()
    if not app_id or not app_key:
        return None
    country = (
        _pick("HELPMEFINDTHEJOB_ADZUNA_COUNTRY", "HELPMEFINDTHEJOB_ADZUNA_COUNTRY") or "de"
    ).strip().lower() or "de"
    return AdzunaProvider(app_id=app_id, app_key=app_key, country=country)


def default_no_auth_providers() -> list:
    """The default-on aggregators wired by ``app.py`` at boot.

    Includes EURES and Bundesagentur because both are public, no-key,
    and dramatically expand EU coverage — especially for the
    healthcare-management persona (Naser's pain point) where the federal
    agency carries a long tail of public-sector + consulting roles.

    Adzuna is registered automatically when the operator sets
    ``HELPMEFINDTHEJOB_ADZUNA_APP_ID`` and ``HELPMEFINDTHEJOB_ADZUNA_APP_KEY``;
    without them it stays absent (no-op).
    """

    # NOTE: EuresProvider is intentionally absent — EURES robots.txt blocks
    # server-side calls (verified 2026-05-09, returns 403). The class is kept
    # for a future operator-managed proxy. Re-add here when transport is fixed.
    providers: list = [
        ArbeitnowProvider(),
        MuseProvider(),
        RemotiveProvider(),
        WeWorkRemotelyProvider(),
        HackerNewsHiringProvider(),
        BundesagenturProvider(),
    ]
    adzuna = adzuna_from_env()
    if adzuna is not None:
        providers.append(adzuna)
    return providers
