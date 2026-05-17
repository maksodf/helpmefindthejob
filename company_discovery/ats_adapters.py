# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""ATS-specific extractors.

Each adapter takes a URL + HTML/JSON body and returns a list of
``DiscoveredJob`` candidates with provenance, an external id when one
is exposed, and a confidence score that reflects how trustworthy the
adapter's extraction is.

Supported (HTML + JSON fixtures only — no live calls in this module):

- Greenhouse (boards.greenhouse.io / public boards-api JSON)
- Lever (jobs.lever.co / api.lever.co JSON)
- Personio (jobs.personio.de XML feed and HTML listing)
- SmartRecruiters (jobs.smartrecruiters.com / api.smartrecruiters.com)
- Teamtailor (career.<company>.com / teamtailor.com JSON)

Workday / SAP SuccessFactors are deliberately excluded: their public
HTML is variable and JS-heavy. ``detect_unsupported_ats`` recognises
them so the UI can show a clear "paste jobs manually" hint.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from .models import Company, DiscoveredJob


@dataclass
class AdapterResult:
    adapter: str
    jobs: list[DiscoveredJob]
    notes: list[dict[str, str]]


_ATS_HOST_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("greenhouse", re.compile(r"(boards|boards-api)\.greenhouse\.io", re.I)),
    ("lever", re.compile(r"(jobs|api)\.lever\.co", re.I)),
    ("personio", re.compile(r"\.jobs\.personio\.(de|com)", re.I)),
    ("smartrecruiters", re.compile(r"jobs\.smartrecruiters\.com|api\.smartrecruiters\.com", re.I)),
    ("teamtailor", re.compile(r"\.teamtailor\.com|career\.[^/]+\.teamtailor\.com", re.I)),
    ("recruitee", re.compile(r"\.recruitee\.com", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com|api\.ashbyhq\.com", re.I)),
    ("bamboohr", re.compile(r"\.bamboohr\.com", re.I)),
]

_UNSUPPORTED_HOST_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("workday", re.compile(r"\.myworkdayjobs\.com|wd[1-9]\.myworkdaysite\.com", re.I)),
    ("successfactors", re.compile(r"successfactors\.|sapsf\.com", re.I)),
]


def detect_ats(url: str | None) -> str | None:
    """Best-effort name of the ATS hosting ``url`` (or ``None``)."""
    if not url:
        return None
    host = (urlparse(url).hostname or "").casefold()
    for name, pattern in _ATS_HOST_PATTERNS:
        if pattern.search(host):
            return name
    return None


def detect_unsupported_ats(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlparse(url).hostname or "").casefold()
    for name, pattern in _UNSUPPORTED_HOST_PATTERNS:
        if pattern.search(host):
            return name
    return None


def extract_jobs(company: Company, page_url: str, body: str) -> AdapterResult | None:
    """Run the matching adapter, if any, against the response body."""
    name = detect_ats(page_url)
    if name == "greenhouse":
        return _extract_greenhouse(company, page_url, body)
    if name == "lever":
        return _extract_lever(company, page_url, body)
    if name == "personio":
        return _extract_personio(company, page_url, body)
    if name == "smartrecruiters":
        return _extract_smartrecruiters(company, page_url, body)
    if name == "teamtailor":
        return _extract_teamtailor(company, page_url, body)
    if name == "recruitee":
        return _extract_recruitee(company, page_url, body)
    if name == "ashby":
        return _extract_ashby(company, page_url, body)
    if name == "bamboohr":
        return _extract_bamboohr(company, page_url, body)
    return None


def _safe_json(body: str) -> object | None:
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", unescape(value))
    return " ".join(text.split())


def _location_string(location: object) -> str | None:
    if isinstance(location, dict):
        for key in ("name", "city", "addressLocality"):
            value = location.get(key)
            if value:
                return str(value)
    if isinstance(location, str):
        return location
    return None


def _build_job(
    *,
    company: Company,
    source_url: str,
    title: str,
    location: str | None,
    description: str | None,
    structured: dict[str, object],
    confidence: float,
) -> DiscoveredJob:
    job = DiscoveredJob(
        user_id=company.user_id,
        company_id=company.id,
        source_url=source_url,
        title=title,
        location=location,
        raw_snippet=title,
        raw_description=description,
        structured_data=structured,
        confidence_score=max(0.0, min(1.0, confidence)),
    )
    return job


def _extract_greenhouse(company: Company, page_url: str, body: str) -> AdapterResult:
    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    if isinstance(payload, dict) and isinstance(payload.get("jobs"), list):
        for entry in payload["jobs"]:
            if not isinstance(entry, dict):
                continue
            ext_id = str(entry.get("id") or entry.get("internal_job_id") or "")
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            absolute = entry.get("absolute_url") or entry.get("url") or page_url
            location = entry.get("location")
            location_text = location.get("name") if isinstance(location, dict) else _location_string(location)
            description = _strip_html(entry.get("content"))
            structured = {
                "ats": "greenhouse",
                "ats_id": ext_id,
                "raw": entry,
            }
            jobs.append(
                _build_job(
                    company=company,
                    source_url=str(absolute),
                    title=title,
                    location=location_text,
                    description=description or None,
                    structured=structured,
                    confidence=0.85,
                )
            )
    if not jobs:
        # Greenhouse boards.greenhouse.io HTML pages embed JSON-LD already
        # handled by the JSON-LD path, but anchor fallback covers older boards.
        for match in re.finditer(r'<a[^>]+href="([^"]+/jobs/(\d+))"[^>]*>([^<]+)</a>', body, re.I):
            href, ext_id, title = match.group(1), match.group(2), match.group(3).strip()
            if not title:
                continue
            absolute = urljoin(page_url, href)
            jobs.append(
                _build_job(
                    company=company,
                    source_url=absolute,
                    title=title,
                    location=None,
                    description=None,
                    structured={"ats": "greenhouse", "ats_id": ext_id},
                    confidence=0.6,
                )
            )
    return AdapterResult(adapter="greenhouse", jobs=jobs, notes=[])


def _extract_lever(company: Company, page_url: str, body: str) -> AdapterResult:
    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    if isinstance(payload, list):
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            ext_id = str(entry.get("id") or entry.get("lever_id") or "")
            title = str(entry.get("text") or entry.get("title") or "").strip()
            if not title:
                continue
            categories = entry.get("categories") or {}
            location = (
                categories.get("location") if isinstance(categories, dict) else None
            ) or entry.get("location")
            description = _strip_html(entry.get("descriptionPlain") or entry.get("description"))
            url = entry.get("hostedUrl") or entry.get("applyUrl") or page_url
            structured = {
                "ats": "lever",
                "ats_id": ext_id,
                "raw": entry,
            }
            jobs.append(
                _build_job(
                    company=company,
                    source_url=str(url),
                    title=title,
                    location=str(location) if location else None,
                    description=description or None,
                    structured=structured,
                    confidence=0.85,
                )
            )
    if not jobs:
        for match in re.finditer(
            r'<a[^>]+href="([^"]+/[A-Za-z0-9-]+/([0-9a-fA-F-]{12,}))"[^>]*>([^<]+)</a>',
            body,
            re.I,
        ):
            href, ext_id, title = match.group(1), match.group(2), match.group(3).strip()
            if not title:
                continue
            absolute = urljoin(page_url, href)
            jobs.append(
                _build_job(
                    company=company,
                    source_url=absolute,
                    title=title,
                    location=None,
                    description=None,
                    structured={"ats": "lever", "ats_id": ext_id},
                    confidence=0.6,
                )
            )
    return AdapterResult(adapter="lever", jobs=jobs, notes=[])


def _extract_personio(company: Company, page_url: str, body: str) -> AdapterResult:
    jobs: list[DiscoveredJob] = []
    notes: list[dict[str, str]] = []
    body_stripped = body.strip()
    if body_stripped.startswith("<?xml") or body_stripped.startswith("<workzag-jobs") or "<position " in body_stripped:
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as error:
            notes.append({"code": "personio_parse_error", "message": str(error)})
            return AdapterResult(adapter="personio", jobs=[], notes=notes)
        for position in root.iter("position"):
            ext_id = position.get("id") or (position.findtext("id") or "")
            title = (position.findtext("name") or position.findtext("title") or "").strip()
            if not title:
                continue
            location = position.findtext("office") or position.findtext("location") or None
            description = ""
            for desc in position.iter("jobDescription"):
                value = desc.findtext("value")
                if value:
                    description += " " + _strip_html(value)
            description = description.strip() or None
            url_field = position.findtext("url") or page_url
            structured = {"ats": "personio", "ats_id": ext_id}
            jobs.append(
                _build_job(
                    company=company,
                    source_url=str(url_field),
                    title=title,
                    location=str(location) if location else None,
                    description=description,
                    structured=structured,
                    confidence=0.85,
                )
            )
        return AdapterResult(adapter="personio", jobs=jobs, notes=notes)

    # HTML listing fallback
    for match in re.finditer(
        r'<a[^>]+href="([^"]*/job(?:s)?/(\d+)[^"]*)"[^>]*>([^<]+)</a>',
        body,
        re.I,
    ):
        href, ext_id, title = match.group(1), match.group(2), match.group(3).strip()
        if not title:
            continue
        absolute = urljoin(page_url, href)
        jobs.append(
            _build_job(
                company=company,
                source_url=absolute,
                title=title,
                location=None,
                description=None,
                structured={"ats": "personio", "ats_id": ext_id},
                confidence=0.65,
            )
        )
    return AdapterResult(adapter="personio", jobs=jobs, notes=notes)


def _extract_smartrecruiters(company: Company, page_url: str, body: str) -> AdapterResult:
    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    if isinstance(payload, dict) and isinstance(payload.get("content"), list):
        for entry in payload["content"]:
            if not isinstance(entry, dict):
                continue
            ext_id = str(entry.get("uuid") or entry.get("id") or "")
            title = str(entry.get("name") or "").strip()
            if not title:
                continue
            location = entry.get("location") or {}
            location_text = (
                f"{location.get('city', '')} {location.get('country', '')}".strip()
                if isinstance(location, dict)
                else None
            )
            description = _strip_html(entry.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text"))
            url = entry.get("ref") or entry.get("applyUrl") or page_url
            structured = {"ats": "smartrecruiters", "ats_id": ext_id, "raw": entry}
            jobs.append(
                _build_job(
                    company=company,
                    source_url=str(url),
                    title=title,
                    location=location_text or None,
                    description=description or None,
                    structured=structured,
                    confidence=0.85,
                )
            )
    if not jobs:
        for match in re.finditer(
            r'<a[^>]+href="([^"]+jobs/([A-Za-z0-9-]{20,}))"[^>]*>([^<]+)</a>',
            body,
            re.I,
        ):
            href, ext_id, title = match.group(1), match.group(2), match.group(3).strip()
            if not title:
                continue
            absolute = urljoin(page_url, href)
            jobs.append(
                _build_job(
                    company=company,
                    source_url=absolute,
                    title=title,
                    location=None,
                    description=None,
                    structured={"ats": "smartrecruiters", "ats_id": ext_id},
                    confidence=0.6,
                )
            )
    return AdapterResult(adapter="smartrecruiters", jobs=jobs, notes=[])


def _extract_teamtailor(company: Company, page_url: str, body: str) -> AdapterResult:
    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    items: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            items = [item for item in payload["data"] if isinstance(item, dict)]
        elif isinstance(payload.get("jobs"), list):
            items = [item for item in payload["jobs"] if isinstance(item, dict)]
    for entry in items:
        attributes = entry.get("attributes") if isinstance(entry.get("attributes"), dict) else entry
        if not isinstance(attributes, dict):
            continue
        ext_id = str(entry.get("id") or attributes.get("id") or "")
        title = str(attributes.get("title") or "").strip()
        if not title:
            continue
        location = attributes.get("locations") or attributes.get("location") or attributes.get("city")
        if isinstance(location, list):
            location_text = ", ".join(str(item) for item in location if item)
        elif isinstance(location, dict):
            location_text = str(location.get("name") or "")
        elif isinstance(location, str):
            location_text = location
        else:
            location_text = None
        description = _strip_html(attributes.get("body") or attributes.get("description"))
        url = attributes.get("careersite-job-url") or attributes.get("url") or page_url
        structured = {"ats": "teamtailor", "ats_id": ext_id, "raw": entry}
        jobs.append(
            _build_job(
                company=company,
                source_url=str(url),
                title=title,
                location=location_text or None,
                description=description or None,
                structured=structured,
                confidence=0.85,
            )
        )
    if not jobs:
        for match in re.finditer(
            r'<a[^>]+href="([^"]+/jobs/(\d+)[^"]*)"[^>]*>([^<]+)</a>',
            body,
            re.I,
        ):
            href, ext_id, title = match.group(1), match.group(2), match.group(3).strip()
            if not title:
                continue
            absolute = urljoin(page_url, href)
            jobs.append(
                _build_job(
                    company=company,
                    source_url=absolute,
                    title=title,
                    location=None,
                    description=None,
                    structured={"ats": "teamtailor", "ats_id": ext_id},
                    confidence=0.6,
                )
            )
    return AdapterResult(adapter="teamtailor", jobs=jobs, notes=[])


def _extract_recruitee(company: Company, page_url: str, body: str) -> AdapterResult:
    """Recruitee public offers feed: /api/offers/ returns ``{"offers": [...]}``."""

    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    if isinstance(payload, dict) and isinstance(payload.get("offers"), list):
        for entry in payload["offers"]:
            if not isinstance(entry, dict):
                continue
            ext_id = str(entry.get("id") or entry.get("slug") or "")
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            absolute = entry.get("careers_url") or entry.get("url") or page_url
            location = entry.get("location") or entry.get("city") or entry.get("country")
            location_text = _location_string(location)
            description = _strip_html(str(entry.get("description") or entry.get("requirements") or ""))
            structured = {"ats": "recruitee", "ats_id": ext_id, "raw": entry}
            jobs.append(
                _build_job(
                    company=company,
                    source_url=str(absolute),
                    title=title,
                    location=location_text,
                    description=description or None,
                    structured=structured,
                    confidence=0.85,
                )
            )
    if not jobs:
        # HTML fallback: Recruitee careers pages render `<a class="vacancy">` rows.
        for match in re.finditer(
            r'<a[^>]+href="([^"]*?/o/[^"]+)"[^>]*class="[^"]*vacancy[^"]*"[^>]*>([^<]+)</a>',
            body, re.I,
        ):
            href, title = match.group(1), match.group(2).strip()
            if not title:
                continue
            jobs.append(_build_job(
                company=company,
                source_url=urljoin(page_url, href),
                title=title,
                location=None,
                description=None,
                structured={"ats": "recruitee"},
                confidence=0.6,
            ))
    return AdapterResult(adapter="recruitee", jobs=jobs, notes=[])


def _extract_ashby(company: Company, page_url: str, body: str) -> AdapterResult:
    """Ashby HQ — public job board JSON at /api/non-user-graphql/public-jobs."""

    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    listings: list[object] = []
    # Ashby's public payload sometimes nests jobs under data.jobBoard.jobPostings.
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            board = data.get("jobBoard") or data.get("organizationJobBoard") or {}
            if isinstance(board, dict):
                postings = board.get("jobPostings") or board.get("jobs")
                if isinstance(postings, list):
                    listings = postings
        if not listings and isinstance(payload.get("jobs"), list):
            listings = payload["jobs"]
    for entry in listings:
        if not isinstance(entry, dict):
            continue
        ext_id = str(entry.get("id") or entry.get("jobId") or "")
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        # Ashby exposes a slug + organisation slug to build the absolute URL.
        slug = entry.get("slug") or entry.get("urlSlug")
        org_slug = entry.get("organizationSlug") or ""
        absolute = (
            f"https://jobs.ashbyhq.com/{org_slug}/{slug}" if slug and org_slug
            else entry.get("applicationUrl") or page_url
        )
        loc_text = entry.get("locationName") or entry.get("location")
        location_text = _location_string(loc_text)
        description = _strip_html(str(entry.get("descriptionHtml") or entry.get("description") or ""))
        structured = {"ats": "ashby", "ats_id": ext_id, "raw": entry}
        jobs.append(
            _build_job(
                company=company,
                source_url=str(absolute),
                title=title,
                location=location_text,
                description=description or None,
                structured=structured,
                confidence=0.85,
            )
        )
    if not jobs:
        for match in re.finditer(
            r'<a[^>]+href="(/[^"/]+/[^"#?]+)"[^>]*class="[^"]*JobPosting[^"]*"[^>]*>([^<]+)</a>',
            body, re.I,
        ):
            href, title = match.group(1), match.group(2).strip()
            if not title:
                continue
            jobs.append(_build_job(
                company=company,
                source_url=urljoin(page_url, href),
                title=title,
                location=None,
                description=None,
                structured={"ats": "ashby"},
                confidence=0.6,
            ))
    return AdapterResult(adapter="ashby", jobs=jobs, notes=[])


def _extract_bamboohr(company: Company, page_url: str, body: str) -> AdapterResult:
    """BambooHR /jobs/embed2.php returns an HTML fragment with anchor + meta divs.

    Some boards also expose a JSON variant at /jobs/embed2.php?json=true; we
    handle that first, then fall back to the HTML scrape.
    """

    payload = _safe_json(body)
    jobs: list[DiscoveredJob] = []
    if isinstance(payload, dict) and isinstance(payload.get("result"), list):
        for entry in payload["result"]:
            if not isinstance(entry, dict):
                continue
            ext_id = str(entry.get("id") or "")
            title = str(entry.get("jobOpeningName") or entry.get("title") or "").strip()
            if not title:
                continue
            absolute = entry.get("jobOpeningURL") or entry.get("url") or page_url
            location = entry.get("location") or entry.get("city")
            location_text = _location_string(location)
            description = _strip_html(str(entry.get("jobOpeningDescription") or ""))
            structured = {"ats": "bamboohr", "ats_id": ext_id, "raw": entry}
            jobs.append(
                _build_job(
                    company=company,
                    source_url=str(absolute),
                    title=title,
                    location=location_text,
                    description=description or None,
                    structured=structured,
                    confidence=0.85,
                )
            )
    if not jobs:
        # HTML embed: <a href="...?id=N" class="BambooHR-ATS-Jobs-Item">Title</a>
        for match in re.finditer(
            r'<a[^>]+href="([^"]*\?id=(\d+))"[^>]*class="[^"]*BambooHR[^"]*"[^>]*>([^<]+)</a>',
            body, re.I,
        ):
            href, ext_id, title = match.group(1), match.group(2), match.group(3).strip()
            if not title:
                continue
            jobs.append(_build_job(
                company=company,
                source_url=urljoin(page_url, href),
                title=title,
                location=None,
                description=None,
                structured={"ats": "bamboohr", "ats_id": ext_id},
                confidence=0.65,
            ))
    return AdapterResult(adapter="bamboohr", jobs=jobs, notes=[])
