from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .service import CompanyDiscoveryService


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "suggest_relevant_companies",
        "description": "Suggest curated healthcare-management companies and fallback categories from role, industry, and location preferences.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "targetRoles": {"type": "array", "items": {"type": "string"}},
                "industry": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["targetRoles", "industry"],
        },
    },
    {
        "name": "add_company_to_watchlist",
        "description": "Create a company watchlist entry without scanning external pages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "name": {"type": "string"},
                "websiteUrl": {"type": "string"},
                "careerPageUrl": {"type": "string"},
                "sector": {"type": "string"},
                "notes": {"type": "string"},
                "watchEnabled": {"type": "boolean"},
            },
            "required": ["userId", "name", "websiteUrl"],
        },
    },
    {
        "name": "find_company_career_page",
        "description": "Find an obvious public career page from a company homepage, respecting robots.txt.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}, "companyId": {"type": "string"}},
            "required": ["userId", "companyId"],
        },
    },
    {
        "name": "scan_company_career_page",
        "description": "Scan one known public career page with robots.txt and max-page guards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "companyId": {"type": "string"},
                "careerPageUrl": {"type": "string"},
            },
            "required": ["userId", "companyId"],
        },
    },
    {
        "name": "extract_direct_jobs_from_company_site",
        "description": "Extract JobPosting JSON-LD and visible job links from supplied HTML without fetching.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "companyId": {"type": "string"},
                "pageUrl": {"type": "string"},
                "html": {"type": "string"},
            },
            "required": ["userId", "companyId", "pageUrl", "html"],
        },
    },
    {
        "name": "import_discovered_job",
        "description": "Import a reviewed discovered job into the normal job pipeline.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}, "discoveredJobId": {"type": "string"}},
            "required": ["userId", "discoveredJobId"],
        },
    },
    {
        "name": "deduplicate_discovered_jobs",
        "description": "Report likely duplicates among discovered direct-company jobs.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}},
            "required": ["userId"],
        },
    },
    {
        "name": "get_company_watchlist_summary",
        "description": "Return dashboard metrics for company watchlist and direct-company discoveries.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}},
            "required": ["userId"],
        },
    },
]


class CompanyDiscoveryMCPTools:
    def __init__(self, service: CompanyDiscoveryService) -> None:
        self.service = service

    def suggest_relevant_companies(self, targetRoles: list[str], industry: str, location: str | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "suggestions": self.service.suggest_relevant_companies(
                target_roles=targetRoles,
                industry=industry,
                location=location,
            ),
        }

    def add_company_to_watchlist(self, **payload: Any) -> dict[str, Any]:
        company = self.service.create_company(
            user_id=payload["userId"],
            name=payload["name"],
            website_url=payload["websiteUrl"],
            career_page_url=payload.get("careerPageUrl"),
            sector=payload.get("sector"),
            notes=payload.get("notes"),
            watch_enabled=payload.get("watchEnabled", True),
        )
        return {"status": "ok", "company": asdict(company)}

    def find_company_career_page(self, userId: str, companyId: str) -> dict[str, Any]:
        return self.service.find_company_career_page(userId, companyId)

    def scan_company_career_page(self, userId: str, companyId: str, careerPageUrl: str | None = None) -> dict[str, Any]:
        scan = self.service.scan_company_career_page(userId, companyId, careerPageUrl)
        return {"status": scan.status, "scan": asdict(scan)}

    def extract_direct_jobs_from_company_site(self, userId: str, companyId: str, pageUrl: str, html: str) -> dict[str, Any]:
        company = self.service.repository.get_company(userId, companyId)
        jobs = self.service.extract_direct_jobs_from_company_site(company, pageUrl, html)
        return {"status": "ok", "jobs": [asdict(job) for job in jobs]}

    def import_discovered_job(self, userId: str, discoveredJobId: str) -> dict[str, Any]:
        imported = self.service.import_discovered_job(userId, discoveredJobId)
        return {"status": "ok", "job": asdict(imported)}

    def deduplicate_discovered_jobs(self, userId: str) -> dict[str, Any]:
        return {"status": "ok", **self.service.deduplicate_discovered_jobs(userId)}

    def get_company_watchlist_summary(self, userId: str) -> dict[str, Any]:
        return {"status": "ok", "summary": self.service.get_company_watchlist_summary(userId)}
