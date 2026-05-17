# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Safe company-discovery reference slice."""

from .models import Company, CompanyDiscoveryRun, CareerPageScan, DiscoveredJob, ImportedJob
from .repository import InMemoryCompanyDiscoveryRepository
from .service import CompanyDiscoveryService, ScanConfig, StaticFetcher
from .sqlite_repository import SqliteCompanyDiscoveryRepository

__all__ = [
    "CareerPageScan",
    "Company",
    "CompanyDiscoveryRun",
    "CompanyDiscoveryService",
    "DiscoveredJob",
    "ImportedJob",
    "InMemoryCompanyDiscoveryRepository",
    "ScanConfig",
    "SqliteCompanyDiscoveryRepository",
    "StaticFetcher",
]
