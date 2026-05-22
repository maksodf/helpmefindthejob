# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Provider-neutral company discovery from explicit sources.

This module is the **discovery side** counterpart to ``ats_adapters``:
it surfaces *new* companies the user might want to watch from a
configured provider. The product policy is unchanged — we never crawl
search engines directly. Allowed sources are:

- ``MockSearchProvider`` — synthetic results, used by tests and as a
  fully-offline default for pilots.
- ``CuratedSearchProvider`` — re-uses ``curated_companies`` to surface
  the curated healthcare taxonomy as discovery results.
- ``GreenhouseFeedProvider`` — given a Greenhouse board token, fetches
  the public Job Board API. The fetch is left to the caller (we
  receive the JSON body) so the same path is used in tests with
  fixtures and in production with a real HTTP client.
- ``LeverFeedProvider`` — same pattern for Lever public postings.

External vendors that require keys (e.g. Brave Search, Tavily) are
expressed as their own provider classes in user code; those credentials
remain BLOCKED until the operator chooses one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Iterable, Protocol
from urllib.parse import urlparse

from .curated_companies import suggest_curated_companies


@dataclass
class DiscoveryResult:
    name: str
    website_url: str
    career_page_url: str | None = None
    sector: str | None = None
    location_hint: str | None = None
    relevance_score: float = 0.5
    relevance_reason: str = ""
    source: str = "unknown"
    raw: dict[str, object] = field(default_factory=dict)


class DiscoveryProvider(Protocol):
    name: str

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]: ...


@dataclass
class MockSearchProvider:
    """Deterministic in-memory provider for tests."""

    name: str = "mock"
    fixture_companies: list[DiscoveryResult] = field(default_factory=list)

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        roles_text = " ".join(target_roles).casefold()
        results: list[DiscoveryResult] = []
        for item in self.fixture_companies:
            score = item.relevance_score
            haystack = f"{item.name} {item.sector or ''} {item.relevance_reason or ''}".casefold()
            if any(token for token in roles_text.split() if token and token in haystack):
                score = min(1.0, score + 0.15)
            if industry and industry.casefold() in haystack:
                score = min(1.0, score + 0.05)
            if (
                location
                and item.location_hint
                and location.casefold() in item.location_hint.casefold()
            ):
                score = min(1.0, score + 0.05)
            results.append(
                DiscoveryResult(
                    name=item.name,
                    website_url=item.website_url,
                    career_page_url=item.career_page_url,
                    sector=item.sector,
                    location_hint=item.location_hint,
                    relevance_score=round(score, 3),
                    relevance_reason=item.relevance_reason or "",
                    source="mock",
                    raw=dict(item.raw),
                )
            )
        results.sort(key=lambda item: item.relevance_score, reverse=True)
        return results[:limit]


@dataclass
class CuratedSearchProvider:
    name: str = "curated"

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        seeds = suggest_curated_companies(
            target_roles,
            industry,
            location,
            limit=limit,
            persona_id=persona_id,
        )
        results: list[DiscoveryResult] = []
        for entry in seeds:
            results.append(
                DiscoveryResult(
                    name=str(entry.get("name") or ""),
                    website_url=str(entry.get("website_url") or ""),
                    career_page_url=entry.get("career_page_url"),
                    sector=entry.get("sector"),
                    location_hint=entry.get("location_hint") or entry.get("locationHint"),
                    relevance_score=float(entry.get("relevanceScore") or 0.5),
                    relevance_reason=str(entry.get("relevanceReason") or ""),
                    source="curated",
                    raw=dict(entry),
                )
            )
        return results


def _safe_json(body: str) -> object | None:
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


@dataclass
class GreenhouseFeedProvider:
    """Parses a Greenhouse Job Board response body into companies.

    Each posting on a Greenhouse board belongs to one company, so this
    provider returns a single result per board with the embedded jobs
    counted in ``raw['jobs']``.
    """

    name: str = "greenhouse_feed"
    company_name: str = ""
    board_url: str = ""

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        body: str = "",
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        payload = _safe_json(body)
        jobs: list[dict[str, object]] = []
        if isinstance(payload, dict) and isinstance(payload.get("jobs"), list):
            jobs = [item for item in payload["jobs"] if isinstance(item, dict)]
        if not jobs:
            return []
        roles_text = " ".join(target_roles).casefold()
        match_count = 0
        for job in jobs:
            title = str(job.get("title") or "")
            if any(token in title.casefold() for token in roles_text.split() if token):
                match_count += 1
        score = 0.55 + min(0.4, match_count * 0.05)
        sample_titles = ", ".join(
            str(job.get("title") or "")[:60] for job in jobs[:3] if job.get("title")
        )
        return [
            DiscoveryResult(
                name=self.company_name or "Greenhouse board",
                website_url=self.board_url,
                career_page_url=self.board_url,
                sector=None,
                location_hint=location,
                relevance_score=round(score, 2),
                relevance_reason=f"{len(jobs)} public roles via Greenhouse"
                + (f" — e.g. {sample_titles}" if sample_titles else ""),
                source="greenhouse_feed",
                raw={"jobs": jobs, "match_count": match_count},
            )
        ][:limit]


@dataclass
class LeverFeedProvider:
    name: str = "lever_feed"
    company_name: str = ""
    board_url: str = ""

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        body: str = "",
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        payload = _safe_json(body)
        if not isinstance(payload, list):
            return []
        roles_text = " ".join(target_roles).casefold()
        match_count = sum(
            1
            for entry in payload
            if isinstance(entry, dict)
            and any(
                token in str(entry.get("text") or "").casefold()
                for token in roles_text.split()
                if token
            )
        )
        score = 0.55 + min(0.4, match_count * 0.05)
        return [
            DiscoveryResult(
                name=self.company_name or "Lever board",
                website_url=self.board_url,
                career_page_url=self.board_url,
                sector=None,
                location_hint=location,
                relevance_score=round(score, 2),
                relevance_reason=f"{len(payload)} public Lever roles, {match_count} match the target",
                source="lever_feed",
                raw={"jobs": payload, "match_count": match_count},
            )
        ][:limit]


@dataclass
class DuckDuckGoSearchProvider:
    """Free, no-key alternative to Brave/Tavily.

    Hits ``https://html.duckduckgo.com/html/`` (the legacy lite HTML
    endpoint, which DDG officially permits for personal/aggregator use).
    Parses the response with stdlib ``html.parser`` and emits one
    ``DiscoveryResult`` per non-restricted result link.

    Strengths:
    - Zero cost, zero signup, no card on file.
    - DDG meta-searches multiple sources, so quality is reasonable.

    Limits:
    - No semantic ranking — we just take the first ``limit`` results.
    - HTML can change. The parser is conservative (depends on
      ``a.result__a`` and the snippet sibling); if DDG changes, the
      provider returns ``[]`` rather than crashing.
    """

    name: str = "duckduckgo"
    base_url: str = "https://html.duckduckgo.com/html/"
    fetcher: object | None = None  # injectable for tests
    timeout_seconds: int = 10

    _RESTRICTED_HOSTS: tuple[str, ...] = (
        "linkedin.com",
        "indeed.com",
        "stepstone.",
        "xing.com",
        "monster.com",
        "glassdoor.com",
        "ziprecruiter.com",
        "duckduckgo.com",
    )

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        query = self._build_query(target_roles, industry, location)
        body = self._fetch(query)
        if not body:
            return []
        return self._parse(body, location=location, query=query, limit=limit)

    def _build_query(self, target_roles: list[str], industry: str, location: str | None) -> str:
        parts = [r for r in target_roles if r] + [
            industry,
            location or "",
            "careers OR jobs site:com",
        ]
        return " ".join(p for p in parts if p)

    def _fetch(self, query: str) -> str:
        if self.fetcher is not None:
            try:
                _, body = self.fetcher.get(  # type: ignore[attr-defined]
                    self.base_url,
                    {},
                    {"q": query, "kl": "wt-wt"},
                )
                return body
            except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
                return ""
        from urllib.error import HTTPError, URLError
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        url = f"{self.base_url}?{urlencode({'q': query, 'kl': 'wt-wt'})}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Helpmefindthejob/0.14; +https://app.helpmefindthejob.com/about)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, OSError):
            return ""

    def _parse(
        self, body: str, *, location: str | None, query: str, limit: int
    ) -> list[DiscoveryResult]:
        # DDG HTML wraps each hit in <a class="result__a" href="...">title</a>
        # plus a sibling <a class="result__snippet">…</a>. Capture both.
        link_pattern = re.compile(
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        from html import unescape

        def _strip(html: str) -> str:
            return unescape(re.sub(r"<[^>]+>", "", html)).strip()

        links = list(link_pattern.finditer(body))
        snippets = list(snippet_pattern.finditer(body))
        out: list[DiscoveryResult] = []
        seen_hosts: set[str] = set()
        for idx, match in enumerate(links):
            href = match.group(1)
            # DDG sometimes wraps URLs in /l/?uddg=<urlencoded>; unwrap.
            if href.startswith("//duckduckgo.com/l/?") or href.startswith("/l/?"):
                from urllib.parse import parse_qs
                from urllib.parse import unquote as _unquote
                from urllib.parse import urlparse as _urlparse

                try:
                    qs = parse_qs(_urlparse(href).query)
                    real = qs.get("uddg", [""])[0]
                    if real:
                        href = _unquote(real)
                except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
                    continue
            if href.startswith("//"):
                href = "https:" + href
            if not href.startswith(("http://", "https://")):
                continue
            host = (urlparse(href).hostname or "").lower()
            if not host or host in seen_hosts:
                continue
            if any(restricted in host for restricted in self._RESTRICTED_HOSTS):
                continue
            seen_hosts.add(host)
            title = _strip(match.group(2))
            description = _strip(snippets[idx].group(1)) if idx < len(snippets) else ""
            out.append(
                DiscoveryResult(
                    name=self._extract_company_name(title, host),
                    website_url=f"https://{host}",
                    career_page_url=href,
                    sector=None,
                    location_hint=location,
                    relevance_score=0.6,
                    relevance_reason=description[:280] or f"Found via DuckDuckGo for: {query}",
                    source="duckduckgo",
                    raw={"url": href, "host": host},
                )
            )
            if len(out) >= limit:
                break
        return out

    def _extract_company_name(self, title: str, host: str) -> str:
        for sep in (" - ", " | ", " — ", "—"):
            if sep in title:
                first = title.split(sep)[0].strip()
                if first:
                    return first
        if host:
            return host.split(".")[0].title()
        return title


@dataclass
class BraveSearchProvider:
    """Brave Search (https://api.search.brave.com) backed company-discovery.

    Activated by setting ``HELPMEFINDTHEJOB_BRAVE_API_KEY`` in the environment.
    Uses the Brave Web Search API to find career pages matching the
    user's target roles + location, then filters to direct-employer
    domains (i.e. excludes LinkedIn / Indeed / StepStone, which are
    already on our restricted-platform list elsewhere).

    Free tier (as of 2026-05): 2,000 queries/month, 1 query/second.
    The provider caps itself to ``max_calls_per_run`` to avoid eating
    the quota on a single discover call.
    """

    name: str = "brave_search"
    api_key: str = ""
    base_url: str = "https://api.search.brave.com/res/v1"
    fetcher: object | None = (
        None  # injectable for tests; expects .get(url, headers) -> (status, body_str)
    )
    max_calls_per_run: int = 1
    timeout_seconds: int = 10

    _RESTRICTED_HOSTS: tuple[str, ...] = (
        "linkedin.com",
        "indeed.com",
        "stepstone.",
        "xing.com",
        "monster.com",
        "glassdoor.com",
        "ziprecruiter.com",
    )

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int,
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        if not self.api_key.strip():
            return []
        query = self._build_query(target_roles, industry, location)
        body = self._fetch(query)
        if not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []
        web = payload.get("web") or {}
        results = web.get("results") or []
        out: list[DiscoveryResult] = []
        for entry in results:
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("url") or "")
            if not url:
                continue
            host = urlparse(url).hostname or ""
            if any(restricted in host for restricted in self._RESTRICTED_HOSTS):
                continue
            title = str(entry.get("title") or host)
            description = str(entry.get("description") or "")
            out.append(
                DiscoveryResult(
                    name=self._extract_company_name(title, host),
                    website_url=f"https://{host}" if host else url,
                    career_page_url=url,
                    sector=None,
                    location_hint=location,
                    relevance_score=0.6,  # neutral; rank_candidates re-scores by persona
                    relevance_reason=description[:280] or f"Found via Brave Search for: {query}",
                    source="brave_search",
                    raw={"url": url, "host": host},
                )
            )
            if len(out) >= limit:
                break
        return out

    def _build_query(self, target_roles: list[str], industry: str, location: str | None) -> str:
        parts = [r for r in target_roles if r] + [industry, location, "careers OR jobs"]
        return " ".join(p for p in parts if p)

    def _fetch(self, query: str) -> str:
        if self.fetcher is not None:
            try:
                _, body = self.fetcher.get(  # type: ignore[attr-defined]
                    f"{self.base_url}/web/search",
                    {"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                    {"q": query, "count": "10"},
                )
                return body
            except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
                return ""
        from urllib.error import HTTPError, URLError
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        url = f"{self.base_url}/web/search?{urlencode({'q': query, 'count': '10'})}"
        request = Request(
            url,
            headers={
                "X-Subscription-Token": self.api_key,
                "Accept": "application/json",
                "User-Agent": "Helpmefindthejob/0.10",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, OSError):
            return ""

    def _extract_company_name(self, title: str, host: str) -> str:
        # Title looks like "Careers - Acme" or "Acme Careers". Trim the noise.
        for separator in (" - ", " | ", "—"):
            if separator in title:
                first = title.split(separator)[0].strip()
                if first:
                    return first
        if host:
            return host.split(".")[0].title()
        return title


class DiscoveryEngine:
    """Aggregates results across configured providers, dedupes by host."""

    def __init__(self, providers: Iterable[DiscoveryProvider] | None = None) -> None:
        self.providers: list[DiscoveryProvider] = list(providers or [])

    def discover(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None = None,
        limit: int = 12,
        persona_id: str | None = None,
    ) -> list[DiscoveryResult]:
        seen: set[str] = set()
        merged: list[DiscoveryResult] = []
        for provider in self.providers:
            try:
                items = provider.discover(
                    target_roles=target_roles,
                    industry=industry,
                    location=location,
                    limit=limit,
                    persona_id=persona_id,
                )
            except Exception:  # noqa: BLE001 - never let a single provider sink the call
                continue
            for item in items:
                host = (urlparse(item.website_url).hostname or item.name).casefold()
                if host in seen:
                    continue
                seen.add(host)
                merged.append(item)
        merged.sort(key=lambda item: item.relevance_score, reverse=True)
        return merged[:limit]
