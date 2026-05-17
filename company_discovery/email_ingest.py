# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Email-forward ingest — parse inbound platform alert emails into jobs.

When a user forwards a LinkedIn / Indeed / StepStone alert email to
their personal DirectJob inbox (e.g. ``u-{token}@inbox.khalo.org``),
the inbound webhook (Resend, Postmark, Mailgun — any of them works)
POSTs the parsed message to ``/api/inbound/email`` on this server. The
handler resolves the user via the per-user token, runs the parser
below, and persists each extracted job as a :class:`DiscoveredJob`
with ``source="email-forward:{platform}"``.

The parser is intentionally generous: alert-email DOMs change, so we
fall back from structured heuristics to plain-text URL extraction.
Anything that yields a URL + title is good enough to land in the
queue with proper dedup against existing rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse


@dataclass(frozen=True)
class IngestedJob:
    title: str
    url: str
    company: str | None
    location: str | None
    source: str  # email-forward:linkedin / email-forward:indeed / etc.


_PLATFORMS: tuple[tuple[str, str, str], ...] = (
    # (regex on host, source label, optional brand-name guard)
    (r"linkedin\.com", "email-forward:linkedin", "LinkedIn"),
    (r"indeed\.", "email-forward:indeed", "Indeed"),
    (r"stepstone\.", "email-forward:stepstone", "StepStone"),
    (r"xing\.com", "email-forward:xing", "Xing"),
)

_URL_RE = re.compile(
    r'https?://[^\s"\'<>]+',
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", text))


def _platform_for_url(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for pattern, label, _ in _PLATFORMS:
        if re.search(pattern, host):
            return label
    return None


def parse_email_to_jobs(
    *,
    sender: str | None,
    subject: str | None,
    text_body: str | None,
    html_body: str | None,
) -> list[IngestedJob]:
    """Extract platform jobs from a forwarded alert email.

    Strategy:
    1. Concatenate text + stripped-HTML body.
    2. Run a URL regex; keep only URLs whose host matches a known
       platform.
    3. For each URL, infer a title from a nearby anchor tag or the
       email subject; infer company from anchor sibling text or the
       title (best-effort).
    4. Dedup by canonical URL prefix.
    """

    visible_html = html_body or ""
    visible_text = (text_body or "") + "\n" + _strip_html(visible_html)
    if not visible_text.strip() and not visible_html.strip():
        return []
    seen_urls: dict[str, IngestedJob] = {}

    # First pass: anchor-tag extraction from the HTML — gives us titles.
    if visible_html:
        for match in re.finditer(
            r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            visible_html, re.DOTALL | re.IGNORECASE,
        ):
            url = match.group(1).strip()
            title = _strip_html(match.group(2)).strip()
            platform = _platform_for_url(url)
            if not platform or not url:
                continue
            url_key = _canon_for_dedup(url)
            if url_key in seen_urls:
                continue
            if not title or len(title) < 3:
                title = subject or url
            company = _infer_company(title, subject or "")
            seen_urls[url_key] = IngestedJob(
                title=title[:160],
                url=url,
                company=company,
                location=None,
                source=platform,
            )

    # Second pass: bare URLs in the text body that we missed in HTML anchors.
    for match in _URL_RE.finditer(visible_text):
        url = match.group(0).rstrip(".,);")
        platform = _platform_for_url(url)
        if not platform:
            continue
        url_key = _canon_for_dedup(url)
        if url_key in seen_urls:
            continue
        title = subject or url
        seen_urls[url_key] = IngestedJob(
            title=title[:160],
            url=url,
            company=_infer_company(title, ""),
            location=None,
            source=platform,
        )

    return list(seen_urls.values())


_ID_QUERY_KEYS = ("jk", "jobid", "stellenangebotsid", "id", "tid")


def _canon_for_dedup(url: str) -> str:
    """Build a stable dedup key keeping the platform's primary job-id query.

    Most platforms encode their primary job id in either the path
    (LinkedIn: ``/jobs/view/123``, Xing) or a single query param
    (Indeed: ``?jk=…``, StepStone: ``?stellenangebotsId=…``). Tracking
    params (utm, refId, from, trk) are stripped — those vary per
    forwarded email but point at the same job.
    """

    from urllib.parse import parse_qsl

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    keep_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        if key.casefold() in _ID_QUERY_KEYS:
            keep_pairs.append((key.casefold(), value))
    keep_pairs.sort()
    suffix = "&".join(f"{k}={v}" for k, v in keep_pairs)
    return f"{parsed.scheme}://{parsed.netloc.lower()}{path}{('?' + suffix) if suffix else ''}"


def _infer_company(title: str, subject: str) -> str | None:
    """Pull a company hint from "Role at Company" or "[Company] Role" patterns."""

    for source in (title, subject):
        if not source:
            continue
        # "Senior Engineer at Acme" / "Senior Engineer @ Acme"
        m = re.search(r"\bat\s+([A-Z][\w &.-]{1,60})", source)
        if m:
            return m.group(1).strip().rstrip(".,;:")
        m = re.search(r"@\s+([A-Z][\w &.-]{1,60})", source)
        if m:
            return m.group(1).strip().rstrip(".,;:")
        m = re.search(r"^\[([A-Z][\w &.-]{1,60})\]", source)
        if m:
            return m.group(1).strip()
    return None
