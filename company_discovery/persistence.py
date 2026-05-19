# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, TypeVar

from .models import CareerPageScan, Company, CompanyDiscoveryRun, DiscoveredJob, ImportedJob
from .repository import InMemoryCompanyDiscoveryRepository

T = TypeVar("T")


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


class JsonCompanyDiscoveryRepository(InMemoryCompanyDiscoveryRepository):
    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def save_company(self, company: Company) -> Company:
        with self._lock:
            result = super().save_company(company)
            self._persist()
            return result

    def delete_company(self, user_id: str, company_id: str) -> None:
        with self._lock:
            super().delete_company(user_id, company_id)
            self._persist()

    def get_company(self, user_id: str, company_id: str) -> Company:
        with self._lock:
            return super().get_company(user_id, company_id)

    def save_discovery_run(self, run: CompanyDiscoveryRun) -> CompanyDiscoveryRun:
        with self._lock:
            result = super().save_discovery_run(run)
            self._persist()
            return result

    def save_scan(self, scan: CareerPageScan) -> CareerPageScan:
        with self._lock:
            result = super().save_scan(scan)
            self._persist()
            return result

    def save_discovered_job(self, job: DiscoveredJob) -> DiscoveredJob:
        with self._lock:
            result = super().save_discovered_job(job)
            self._persist()
            return result

    def save_imported_job(self, job: ImportedJob) -> ImportedJob:
        with self._lock:
            result = super().save_imported_job(job)
            self._persist()
            return result

    def list_companies(self, user_id: str) -> list[Company]:
        with self._lock:
            return list(super().list_companies(user_id))

    def list_discovered_jobs(
        self, user_id: str, company_id: str | None = None
    ) -> list[DiscoveredJob]:
        with self._lock:
            return list(super().list_discovered_jobs(user_id, company_id))

    def list_discovery_runs(self, user_id: str) -> list[CompanyDiscoveryRun]:
        with self._lock:
            return list(super().list_discovery_runs(user_id))

    def list_scans(self, user_id: str) -> list[CareerPageScan]:
        with self._lock:
            return list(super().list_scans(user_id))

    def list_imported_jobs(self, user_id: str) -> list[ImportedJob]:
        with self._lock:
            return list(super().list_imported_jobs(user_id))

    def watchlist_summary(self, user_id: str) -> dict[str, object]:
        with self._lock:
            return super().watchlist_summary(user_id)

    def find_duplicate_discovered_job(self, candidate: DiscoveredJob) -> DiscoveredJob | None:
        with self._lock:
            return super().find_duplicate_discovered_job(candidate)

    def _persist(self) -> None:
        payload = {
            "companies": [asdict(item) for item in self.companies.values()],
            "discoveryRuns": [asdict(item) for item in self.discovery_runs.values()],
            "scans": [asdict(item) for item in self.scans.values()],
            "discoveredJobs": [asdict(item) for item in self.discovered_jobs.values()],
            "importedJobs": [asdict(item) for item in self.imported_jobs.values()],
        }
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, default=_json_default, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))

        for data in payload.get("companies", []):
            item = Company(
                **_drop_none(
                    {
                        **data,
                        "created_at": _parse_datetime(data.get("created_at")),
                        "updated_at": _parse_datetime(data.get("updated_at")),
                    }
                )
            )
            self.companies[item.id] = item

        for data in payload.get("discoveryRuns", []):
            item = CompanyDiscoveryRun(
                **_drop_none(
                    {
                        **data,
                        "started_at": _parse_datetime(data.get("started_at")),
                        "finished_at": _parse_datetime(data.get("finished_at")),
                        "created_at": _parse_datetime(data.get("created_at")),
                    }
                )
            )
            self.discovery_runs[item.id] = item

        for data in payload.get("scans", []):
            item = CareerPageScan(
                **_drop_none(
                    {
                        **data,
                        "last_checked_at": _parse_datetime(data.get("last_checked_at")),
                        "created_at": _parse_datetime(data.get("created_at")),
                    }
                )
            )
            self.scans[item.id] = item

        for data in payload.get("discoveredJobs", []):
            item = DiscoveredJob(
                **_drop_none(
                    {
                        **data,
                        "discovered_at": _parse_datetime(data.get("discovered_at")),
                        "created_at": _parse_datetime(data.get("created_at")),
                        "updated_at": _parse_datetime(data.get("updated_at")),
                    }
                )
            )
            self.discovered_jobs[item.id] = item

        for data in payload.get("importedJobs", []):
            item = ImportedJob(
                **_drop_none(
                    {
                        **data,
                        "analyzed_at": _parse_datetime(data.get("analyzed_at")),
                        "created_at": _parse_datetime(data.get("created_at")),
                    }
                )
            )
            self.imported_jobs[item.id] = item
