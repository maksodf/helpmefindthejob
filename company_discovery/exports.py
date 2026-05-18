# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Export imported jobs and discovered jobs to CSV / Markdown.

Pure-Python; no external libraries. The CSV variant uses the stdlib
``csv`` module; Markdown is hand-built. Both shapes match what a user
would paste into Notion/Google Docs.

PDF export is intentionally deferred — every Python PDF library brings
real dependency weight, and the current pilot only asked for "CSV +
Markdown at minimum".
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Iterable

from .models import DiscoveredJob, ImportedJob

_IMPORTED_FIELDS = (
    ("id", "ID"),
    ("title", "Title"),
    ("company_name", "Company"),
    ("location", "Location"),
    ("source_url", "Source URL"),
    ("source_type", "Source type"),
    ("application_status", "Application status"),
    ("fit_score", "Fit score"),
    ("recommendation", "Recommendation"),
    ("analysis_status", "Analysis status"),
    ("analyzed_at", "Analyzed at"),
    ("created_at", "Imported at"),
)


_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return ", ".join(_stringify(item) for item in value)
    return str(value)


def _csv_safe(value: object) -> str:
    """Return a string that cannot trigger formula execution in spreadsheets.

    Excel, LibreOffice Calc, and Google Sheets execute strings that begin
    with ``= + - @`` (plus tab and CR). Prefixing the value with a single
    quote disables the formula without changing the displayed text in
    reasonable viewers.
    """
    text = _stringify(value)
    if text and text[0] in _CSV_INJECTION_PREFIXES:
        return "'" + text
    return text


def imported_jobs_to_csv(jobs: Iterable[ImportedJob]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([label for _, label in _IMPORTED_FIELDS])
    for job in jobs:
        writer.writerow([_csv_safe(getattr(job, attr, "")) for attr, _ in _IMPORTED_FIELDS])
    return buffer.getvalue()


def imported_jobs_to_markdown(jobs: Iterable[ImportedJob]) -> str:
    rows = list(jobs)
    if not rows:
        return "_No imported jobs._\n"
    out: list[str] = ["# Imported jobs", ""]
    out.append("| Title | Company | Location | Status | Fit | Source |")
    out.append("|---|---|---|---|---|---|")
    for job in rows:
        title = (job.title or "").replace("|", "/")
        company = (job.company_name or "").replace("|", "/")
        loc = (job.location or "").replace("|", "/")
        status = job.application_status or "saved"
        fit = "" if job.fit_score is None else f"{int(job.fit_score * 100)}%"
        url = job.source_url or ""
        out.append(f"| {title} | {company} | {loc} | {status} | {fit} | <{url}> |")
    return "\n".join(out) + "\n"


def discovered_jobs_to_csv(jobs: Iterable[DiscoveredJob]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "ID",
            "Title",
            "Company ID",
            "Location",
            "Confidence",
            "Source URL",
            "Discovered at",
            "Imported",
        ]
    )
    for job in jobs:
        writer.writerow(
            [
                _csv_safe(job.id),
                _csv_safe(job.title),
                _csv_safe(job.company_id),
                _csv_safe(job.location),
                f"{int((job.confidence_score or 0) * 100)}%",
                _csv_safe(job.source_url),
                _csv_safe(job.discovered_at),
                "yes" if job.imported_job_id else "no",
            ]
        )
    return buffer.getvalue()


def discovered_jobs_to_markdown(jobs: Iterable[DiscoveredJob]) -> str:
    rows = list(jobs)
    if not rows:
        return "_No discovered jobs._\n"
    out: list[str] = ["# Discovered jobs", ""]
    out.append("| Title | Location | Confidence | Source URL |")
    out.append("|---|---|---|---|")
    for job in rows:
        title = (job.title or "").replace("|", "/")
        location = (job.location or "").replace("|", "/")
        confidence = f"{int((job.confidence_score or 0) * 100)}%"
        url = job.source_url or ""
        out.append(f"| {title} | {location} | {confidence} | <{url}> |")
    return "\n".join(out) + "\n"
