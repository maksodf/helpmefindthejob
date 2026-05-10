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
