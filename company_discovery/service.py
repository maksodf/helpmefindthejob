from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from . import ats_adapters
from .curated_companies import suggest_curated_companies
from .models import CareerPageScan, Company, CompanyDiscoveryRun, DiscoveredJob, ImportedJob, now_utc
from .personas import DEFAULT_PERSONA_ID, get_persona
from .repository import InMemoryCompanyDiscoveryRepository


CAREER_LINK_TERMS = (
    # English
    "career",
    "careers",
    "jobs",
    "vacancies",
    "work with us",
    "join us",
    "join our team",
    "open positions",
    # German
    "karriere",
    "stellenangebote",
    "stellen",
    "stellenmarkt",
    # French
    "carrieres",
    "carrières",
    "emplois",
    "rejoignez-nous",
    "nous rejoindre",
    "offres d'emploi",
    # Dutch
    "vacatures",
    "werken bij",
    "carriere",  # also Italian
    "carrière",
    # Spanish
    "empleos",
    "carreras",
    "trabaja con nosotros",
    "unete",
    "únete",
    "oportunidades",
    # Italian
    "lavoro",
    "carriere",
    "candidati",
    "opportunita",
    "opportunità",
    # Polish
    "kariera",
    "praca",
    "dolacz-do-nas",
    "dołącz-do-nas",
    # Portuguese
    "carreiras",
    "trabalhe-conosco",
    "vagas",
)

JOB_TITLE_TERMS = (
    # Healthcare-management originals
    "manager",
    "projekt",
    "project",
    "consultant",
    "referent",
    "koordinator",
    "coordinator",
    "analyst",
    "quality",
    "prozess",
    "process",
    "health",
    "healthcare",
    "digital",
    "market access",
    "public affairs",
    "policy",
    "research",
    "klinikum",
    "klinik",
    # Tech / product persona
    "engineer",
    "developer",
    "developpeur",
    "ingenieur",
    "ingénieur",
    "frontend",
    "backend",
    "platform",
    "devops",
    "sre",
    "data",
    "ml",
    "scientist",
    "security",
    "qa",
    "product",
    "pm",
    "designer",
    # Marketing persona
    "marketing",
    "brand",
    "growth",
    "performance",
    "content",
    "seo",
    "crm",
    "communication",
    "social",
    # Finance persona
    "finance",
    "controller",
    "controlling",
    "accountant",
    "treasurer",
    "treasury",
    "audit",
    "auditor",
    "risk",
    "compliance",
    "actuarial",
    "actuary",
    "tax",
)

RESTRICTED_PLATFORM_DOMAINS = (
    "linkedin.com",
    "xing.com",
    "stepstone.",
    "indeed.",
)

CAPTCHA_OR_BLOCK_MARKERS = (
    "captcha",
    "access denied",
    "bot detection",
    "unusual traffic",
    "enable javascript and cookies",
)


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict[str, str] | None = None


@dataclass
class ScanConfig:
    user_agent: str = "CompanyDiscoveryBot"
    max_pages_per_scan: int = 5
    max_redirects_per_fetch: int = 5
    request_delay_seconds: float = 0.0
    max_response_chars: int = 1_000_000
    fetch_same_host_job_details: bool = True


class StaticFetcher:
    """Fixture-backed fetcher for tests and local demos.

    This intentionally avoids live network access. Production code should supply
    an HTTP fetcher with timeout, redirect, size, and retry limits.
    """

    def __init__(self, routes: dict[str, str | tuple[int, str]]) -> None:
        self.routes = routes
        self.requests: list[str] = []

    def fetch(self, url: str, user_agent: str) -> FetchResult:
        self.requests.append(url)
        if url not in self.routes:
            return FetchResult(url=url, status_code=404, text="")
        value = self.routes[url]
        if isinstance(value, tuple):
            status_code, text = value
        else:
            status_code, text = 200, value
        return FetchResult(url=url, status_code=status_code, text=text)


class _ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_ld_json = False
        self._buffer: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if "ld+json" in attr_map.get("type", "").lower():
            self._in_ld_json = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_ld_json:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_ld_json:
            self.scripts.append("".join(self._buffer).strip())
            self._in_ld_json = False
            self._buffer = []


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current: dict[str, Any] | None = None
        self.anchors: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {name.lower(): value or "" for name, value in attrs}
        self._current = {"href": attr_map.get("href", ""), "attrs": attr_map, "text": []}

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current is not None:
            self._current["text"] = clean_text(" ".join(self._current["text"]))
            self.anchors.append(self._current)
            self._current = None


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)

    @property
    def text(self) -> str:
        return clean_text(" ".join(self.parts))


def clean_text(value: str | None) -> str:
    return " ".join(unescape(value or "").split())


def strip_html(value: str | None) -> str:
    parser = _TextCollector()
    parser.feed(value or "")
    return parser.text


def origin_for(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def robots_url_for(url: str) -> str:
    return f"{origin_for(url)}/robots.txt"


def same_host(left: str, right: str) -> bool:
    return urlparse(left).netloc.casefold() == urlparse(right).netloc.casefold()


def is_restricted_platform(url: str) -> bool:
    host = urlparse(url).netloc.casefold()
    return any(domain in host for domain in RESTRICTED_PLATFORM_DOMAINS)


def looks_blocked(html: str) -> bool:
    lower = html.casefold()
    return any(marker in lower for marker in CAPTCHA_OR_BLOCK_MARKERS)


def _pattern_matches(path: str, pattern: str) -> bool:
    if not pattern:
        return False
    escaped = re.escape(pattern).replace(r"\*", ".*")
    if escaped.endswith(r"\$"):
        escaped = escaped[:-2] + "$"
    else:
        escaped += ".*"
    return re.match(escaped, path) is not None


def robots_allows(robots_txt: str, target_url: str, user_agent: str) -> bool:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().casefold()
        value = value.strip()
        if key == "user-agent":
            if agents and rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.casefold())
        elif key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    if agents or rules:
        groups.append((agents, rules))

    user_agent_lc = user_agent.casefold()
    exact_rules: list[tuple[str, str]] = []
    wildcard_rules: list[tuple[str, str]] = []
    for group_agents, group_rules in groups:
        if any(agent != "*" and agent and agent in user_agent_lc for agent in group_agents):
            exact_rules.extend(group_rules)
        elif "*" in group_agents:
            wildcard_rules.extend(group_rules)
    applicable_rules = exact_rules or wildcard_rules
    if not applicable_rules:
        return True

    parsed = urlparse(target_url)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    best: tuple[int, str] | None = None
    for directive, pattern in applicable_rules:
        if directive == "disallow" and pattern == "":
            continue
        if _pattern_matches(path, pattern):
            specificity = len(pattern.replace("*", "").replace("$", ""))
            if best is None or specificity > best[0] or (specificity == best[0] and directive == "allow"):
                best = (specificity, directive)
    if best is None:
        return True
    return best[1] == "allow"


def parse_json_ld_job_postings(html: str) -> list[dict[str, Any]]:
    collector = _ScriptCollector()
    collector.feed(html)
    postings: list[dict[str, Any]] = []
    for script in collector.scripts:
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue
        postings.extend(_find_job_postings(payload))
    return postings


def _find_job_postings(payload: Any) -> list[dict[str, Any]]:
    postings: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            postings.extend(_find_job_postings(item))
    elif isinstance(payload, dict):
        raw_type = payload.get("@type") or payload.get("type")
        types = raw_type if isinstance(raw_type, list) else [raw_type]
        if any(str(item).casefold() == "jobposting" for item in types):
            postings.append(payload)
        for key in ("@graph", "graph", "itemListElement"):
            if key in payload:
                postings.extend(_find_job_postings(payload[key]))
    return postings


def extract_location_from_structured_data(data: dict[str, Any]) -> str | None:
    if data.get("jobLocationType"):
        return str(data["jobLocationType"])
    location = data.get("jobLocation") or data.get("applicantLocationRequirements")
    if isinstance(location, list):
        return ", ".join(filter(None, (extract_location_from_structured_data({"jobLocation": item}) for item in location)))
    if isinstance(location, dict):
        address = location.get("address")
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            return ", ".join(str(part) for part in parts if part)
        return str(location.get("name") or location.get("address") or "") or None
    if isinstance(location, str):
        return location
    return None


def confidence_for_job(job: DiscoveredJob) -> float:
    score = 0.15
    if job.structured_data:
        score += 0.35
    if clean_text(job.title):
        score += 0.15
    if job.source_url:
        score += 0.10
    if job.raw_description:
        score += 0.10
    if job.location:
        score += 0.05
    if job.structured_data and job.structured_data.get("hiringOrganization"):
        score += 0.05
    if job.structured_data and job.structured_data.get("validThrough"):
        score += 0.05
    return min(score, 1.0)


class CompanyDiscoveryService:
    def __init__(
        self,
        repository: InMemoryCompanyDiscoveryRepository,
        fetcher: StaticFetcher,
        config: ScanConfig | None = None,
    ) -> None:
        self.repository = repository
        self.fetcher = fetcher
        self.config = config or ScanConfig()

    def create_company(
        self,
        *,
        user_id: str,
        name: str,
        website_url: str,
        career_page_url: str | None = None,
        sector: str | None = None,
        notes: str | None = None,
        watch_enabled: bool = False,
    ) -> Company:
        company = Company(
            user_id=user_id,
            name=name,
            website_url=website_url,
            career_page_url=career_page_url,
            sector=sector,
            notes=notes,
            watch_enabled=watch_enabled,
        )
        return self.repository.save_company(company)

    def update_company(self, user_id: str, company_id: str, **changes: object) -> Company:
        company = self.repository.get_company(user_id, company_id)
        for key, value in changes.items():
            if hasattr(company, key):
                setattr(company, key, value)
        return self.repository.save_company(company)

    def suggest_relevant_companies(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None = None,
        persona_id: str | None = None,
    ) -> list[dict[str, object]]:
        persona = get_persona(persona_id or DEFAULT_PERSONA_ID)
        role_text = " ".join(target_roles).casefold()
        industry_text = industry.casefold()
        concrete = suggest_curated_companies(
            target_roles, industry, location, limit=8, persona_id=persona.id,
        )
        suggestions: list[dict[str, object]] = []
        for category in persona.category_suggestions:
            score = category.base_score
            for role_terms, boost in category.role_keyword_boosts:
                if any(term in role_text for term in role_terms):
                    score += boost
            if any(term in industry_text for term in persona.industry_match_terms):
                score += 0.05
            suggestions.append(
                {
                    "type": "category",
                    "category": category.label,
                    "name": category.label,
                    "relevanceScore": min(round(score, 2), 1.0),
                    "relevanceReason": category.reason,
                    "locationHint": location,
                    "confidence": "category_suggestion",
                }
            )
        ranked_categories = sorted(
            suggestions, key=lambda item: item["relevanceScore"], reverse=True,
        )
        return concrete + ranked_categories

    def find_company_career_page(self, user_id: str, company_id: str) -> dict[str, object]:
        company = self.repository.get_company(user_id, company_id)
        if is_restricted_platform(company.website_url):
            return {"status": "blocked", "careerPageUrl": None, "errors": [{"code": "restricted_platform"}]}
        response, errors = self._fetch_allowed_page(company.website_url)
        if response is None:
            return {"status": "blocked", "careerPageUrl": None, "errors": errors}
        if response.status_code >= 400:
            return {
                "status": "unavailable",
                "careerPageUrl": None,
                "errors": [{"code": "homepage_unavailable", "statusCode": response.status_code}],
            }
        if looks_blocked(response.text):
            return {"status": "blocked", "careerPageUrl": None, "errors": [{"code": "blocked_or_captcha"}]}
        anchors = self._extract_anchors(response.text, company.website_url)
        candidates = [
            anchor
            for anchor in anchors
            if any(term in f"{anchor['text']} {anchor['href']}".casefold() for term in CAREER_LINK_TERMS)
            and not is_restricted_platform(anchor["absolute_url"])
        ]
        if not candidates:
            return {"status": "not_found", "careerPageUrl": None, "errors": []}
        best = sorted(candidates, key=lambda anchor: self._career_link_score(anchor), reverse=True)[0]
        company.career_page_url = best["absolute_url"]
        self.repository.save_company(company)
        return {
            "status": "found",
            "careerPageUrl": company.career_page_url,
            "confidence": best["score"],
            "errors": [],
        }

    def scan_company_career_page(
        self,
        user_id: str,
        company_id: str,
        career_page_url: str | None = None,
        discovery_run: CompanyDiscoveryRun | None = None,
    ) -> CareerPageScan:
        company = self.repository.get_company(user_id, company_id)
        scan_url = career_page_url or company.career_page_url
        run = discovery_run
        if not scan_url:
            errors = [{"code": "missing_career_page"}]
            if run:
                run.status = "missing_career_page"
                run.errors = errors
                run.finished_at = now_utc()
                self.repository.save_discovery_run(run)
            scan = CareerPageScan(
                user_id=user_id,
                company_id=company.id,
                career_page_url="",
                status="missing_career_page",
                checked_robots=False,
                robots_allowed=False,
                errors=errors,
            )
            return self.repository.save_scan(scan)
        if is_restricted_platform(scan_url):
            errors = [{"code": "restricted_platform"}]
            if run:
                run.status = "restricted_platform"
                run.errors = errors
                run.finished_at = now_utc()
                self.repository.save_discovery_run(run)
            scan = CareerPageScan(
                user_id=user_id,
                company_id=company.id,
                career_page_url=scan_url,
                status="restricted_platform",
                checked_robots=False,
                robots_allowed=False,
                errors=errors,
            )
            return self.repository.save_scan(scan)

        if run is None:
            run = CompanyDiscoveryRun(user_id=user_id, company_id=company.id, source_type="career_page_scan")
        run.status = "running"
        self.repository.save_discovery_run(run)
        errors: list[dict[str, Any]] = []
        pages_checked = 0
        source_urls: list[str] = []
        response, fetch_errors = self._fetch_allowed_page(scan_url)
        if response is None:
            status = "blocked_by_robots" if any(error.get("code") == "robots_disallowed" for error in fetch_errors) else "blocked_or_unavailable"
            scan = CareerPageScan(
                user_id=user_id,
                company_id=company.id,
                career_page_url=scan_url,
                status=status,
                checked_robots=True,
                robots_allowed=False,
                errors=fetch_errors,
            )
            run.status = status
            run.errors = fetch_errors
            run.finished_at = now_utc()
            self.repository.save_discovery_run(run)
            return self.repository.save_scan(scan)

        errors.extend(fetch_errors)
        pages_checked += 1
        source_urls.append(response.url)
        if response.status_code in {401, 403, 429} or response.status_code >= 500:
            errors.append({"code": "page_unavailable_or_blocked", "statusCode": response.status_code, "url": scan_url})
            return self._finish_scan(company, run, scan_url, "blocked_or_unavailable", True, True, pages_checked, 0, errors, source_urls)
        if looks_blocked(response.text):
            errors.append({"code": "blocked_or_captcha", "url": scan_url})
            return self._finish_scan(company, run, scan_url, "blocked_or_captcha", True, True, pages_checked, 0, errors, source_urls)

        discovered = self.extract_direct_jobs_from_company_site(company, scan_url, response.text)
        if self.config.fetch_same_host_job_details:
            discovered, detail_pages_checked, detail_urls, detail_errors = self._enrich_with_detail_pages(company, discovered, scan_url)
            pages_checked += detail_pages_checked
            source_urls.extend(detail_urls)
            errors.extend(detail_errors)

        # Strict job-type filter: if the user has set a job_type_filter
        # (via /find on a known role bucket), drop scan results that
        # don't match the role + location. The user opted into a focused
        # queue; surfacing off-topic jobs would defeat that.
        profile = self.repository.get_user_profile(user_id)
        if profile is not None and getattr(profile, "job_type_filter", ""):
            from company_discovery.job_type_filter import filter_jobs as _filter_jobs_by_type
            discovered = _filter_jobs_by_type(
                discovered,
                job_type=profile.job_type_filter,
                location=getattr(profile, "job_type_location_filter", "") or None,
            )

        saved_jobs = []
        merged_sources: list[dict[str, str]] = []
        for job in discovered:
            duplicate = self.repository.find_duplicate_discovered_job(job)
            if duplicate:
                # Merge-semantics: instead of dropping the candidate silently,
                # record this re-sighting on the existing job's also_seen_at map
                # so the user can see "found again on N source(s) since last
                # scan" rather than the misleading "0 new jobs."
                source_host = (urlparse(job.source_url).hostname or "direct").casefold()
                existing_map = dict(duplicate.also_seen_at or {})
                existing_map[source_host] = {
                    "url": job.source_url,
                    "found_at": now_utc().isoformat(),
                    "source_label": "career_page_scan",
                }
                duplicate.also_seen_at = existing_map
                self.repository.save_discovered_job(duplicate)
                merged_sources.append({
                    "duplicateId": duplicate.id,
                    "sourceUrl": job.source_url,
                    "sourceHost": source_host,
                })
                continue
            saved_jobs.append(self.repository.save_discovered_job(job))

        status = "completed" if (saved_jobs or merged_sources or not errors) else "completed_with_errors"
        scan = self._finish_scan(
            company,
            run,
            scan_url,
            status,
            True,
            True,
            pages_checked,
            len(saved_jobs),
            errors,
            source_urls,
        )
        # Surface merge information through the scan record so the UI can
        # render a useful summary even when no new jobs landed.
        scan.errors = list(scan.errors)
        scan.errors.extend(
            {"code": "source_merged", **entry} for entry in merged_sources
        )
        if merged_sources:
            scan.errors.append({"code": "merged_sources_total", "count": len(merged_sources)})
        return scan

    def extract_direct_jobs_from_company_site(self, company: Company, page_url: str, html: str) -> list[DiscoveredJob]:
        ats_result = ats_adapters.extract_jobs(company, page_url, html)
        if ats_result and ats_result.jobs:
            return ats_result.jobs
        jobs: list[DiscoveredJob] = []
        for item in parse_json_ld_job_postings(html):
            title = clean_text(str(item.get("title") or item.get("name") or ""))
            if not title:
                continue
            source_url = str(item.get("url") or page_url)
            if is_restricted_platform(source_url):
                continue
            job = DiscoveredJob(
                user_id=company.user_id,
                company_id=company.id,
                source_url=urljoin(page_url, source_url),
                title=title,
                location=extract_location_from_structured_data(item),
                raw_snippet=title,
                raw_description=strip_html(str(item.get("description") or "")) or None,
                structured_data=item,
            )
            job.confidence_score = confidence_for_job(job)
            jobs.append(job)

        seen_urls = {job.source_url for job in jobs}
        for anchor in self._extract_anchors(html, page_url):
            source_url = anchor["absolute_url"]
            if source_url in seen_urls or is_restricted_platform(source_url):
                continue
            title = clean_text(anchor["text"])
            searchable = f"{title} {source_url}".casefold()
            if not title or not self._looks_like_job_link(searchable):
                continue
            job = DiscoveredJob(
                user_id=company.user_id,
                company_id=company.id,
                source_url=source_url,
                title=title,
                location=anchor["attrs"].get("data-location") or None,
                raw_snippet=title,
                confidence_score=0.45 if anchor["attrs"].get("data-location") else 0.35,
            )
            jobs.append(job)
            seen_urls.add(source_url)
        return jobs

    def import_discovered_job(self, user_id: str, discovered_job_id: str) -> ImportedJob:
        discovered = self.repository.discovered_jobs[discovered_job_id]
        if discovered.user_id != user_id:
            raise KeyError(discovered_job_id)
        if discovered.imported_job_id:
            return self.repository.imported_jobs[discovered.imported_job_id]
        # Aggregator-sourced discovered jobs (saved-search runs, bookmarklet
        # captures) have company_id=None because they don't map to a
        # watched company. Auto-create a placeholder company from the URL
        # host so the import path always has a company_id to bind. This
        # unblocks the entire post-search import → fit → tailor → apply
        # flow for queue-side jobs.
        if discovered.company_id is None:
            placeholder_company = self._placeholder_company_for(user_id, discovered)
            discovered.company_id = placeholder_company.id
            self.repository.save_discovered_job(discovered)
            company = placeholder_company
        else:
            company = self.repository.get_company(user_id, discovered.company_id)
        imported = ImportedJob(
            user_id=user_id,
            company_id=company.id,
            discovered_job_id=discovered.id,
            source_url=discovered.source_url,
            title=discovered.title,
            company_name=company.name,
            location=discovered.location,
            description=discovered.raw_description,
            gaps=list(discovered.gaps or []),
        )
        self.repository.save_imported_job(imported)
        discovered.imported_job_id = imported.id
        self.repository.save_discovered_job(discovered)
        return imported

    def _placeholder_company_for(
        self, user_id: str, discovered: "DiscoveredJob",
    ) -> "Company":
        """Derive a company from a discovered job's metadata and persist it.

        Order of preference for the company name:
        1. ``structured_data.company_name`` if the aggregator captured one
        2. URL host (``careers.acme.com`` → ``acme.com``)
        3. ``"Unknown employer"`` as a last resort

        If a placeholder company with the same name already exists for
        this user, reuse it — otherwise queue rows from the same host
        would each spawn a new company."""

        from urllib.parse import urlparse

        from .models import Company

        sd = discovered.structured_data or {}
        name = ""
        if isinstance(sd, dict):
            name = str(sd.get("company_name") or "").strip()
        if not name:
            host = (urlparse(discovered.source_url).hostname or "").lower()
            # Strip leading 'www.' and 'careers.' / 'jobs.' subdomain noise.
            for prefix in ("www.", "careers.", "career.", "jobs."):
                if host.startswith(prefix):
                    host = host[len(prefix):]
                    break
            name = host or "Unknown employer"
        for existing in self.repository.list_companies(user_id):
            if existing.name == name:
                return existing
        company = Company(
            user_id=user_id,
            name=name,
            website_url=discovered.source_url,
            notes="Auto-created from aggregator import.",
        )
        return self.repository.save_company(company)

    def deduplicate_discovered_jobs(self, user_id: str) -> dict[str, object]:
        duplicates: list[dict[str, str]] = []
        unique: list[DiscoveredJob] = []
        for job in self.repository.list_discovered_jobs(user_id):
            duplicate = None
            for existing in unique:
                if self.repository.find_duplicate_discovered_job_pair(existing, job):
                    duplicate = existing
                    break
            if duplicate:
                duplicates.append({"duplicateId": job.id, "keptId": duplicate.id})
            else:
                unique.append(job)
        return {"duplicates": duplicates, "uniqueCount": len(unique)}

    def get_company_watchlist_summary(self, user_id: str) -> dict[str, object]:
        return self.repository.watchlist_summary(user_id)

    def _enrich_with_detail_pages(
        self,
        company: Company,
        jobs: list[DiscoveredJob],
        career_page_url: str,
    ) -> tuple[list[DiscoveredJob], int, list[str], list[dict[str, Any]]]:
        pages_checked = 0
        source_urls: list[str] = []
        errors: list[dict[str, Any]] = []
        enriched: list[DiscoveredJob] = []

        for job in jobs:
            if pages_checked + 1 >= self.config.max_pages_per_scan:
                errors.append({"code": "max_pages_reached", "limit": self.config.max_pages_per_scan})
                enriched.append(job)
                continue
            if job.structured_data or not same_host(career_page_url, job.source_url):
                enriched.append(job)
                continue
            if self.config.request_delay_seconds:
                time.sleep(self.config.request_delay_seconds)
            response, fetch_errors = self._fetch_allowed_page(job.source_url)
            errors.extend(fetch_errors)
            if response is None:
                enriched.append(job)
                continue
            pages_checked += 1
            source_urls.append(response.url)
            if response.status_code >= 400 or looks_blocked(response.text):
                errors.append({"code": "job_detail_unavailable", "statusCode": response.status_code, "url": job.source_url})
                enriched.append(job)
                continue
            structured = self.extract_direct_jobs_from_company_site(company, job.source_url, response.text)
            structured = [item for item in structured if item.structured_data]
            if structured:
                enriched.extend(structured)
            else:
                job.raw_description = strip_html(response.text)[:4000] or job.raw_description
                job.confidence_score = max(job.confidence_score, confidence_for_job(job))
                enriched.append(job)
        return enriched, pages_checked, source_urls, errors

    def _finish_scan(
        self,
        company: Company,
        run: CompanyDiscoveryRun,
        scan_url: str,
        status: str,
        checked_robots: bool,
        robots_allowed_value: bool,
        pages_checked: int,
        jobs_found: int,
        errors: list[dict[str, Any]],
        source_urls: list[str],
    ) -> CareerPageScan:
        run.status = status
        run.pages_checked = pages_checked
        run.jobs_found = jobs_found
        run.errors = errors
        run.finished_at = now_utc()
        self.repository.save_discovery_run(run)
        scan = CareerPageScan(
            user_id=company.user_id,
            company_id=company.id,
            career_page_url=scan_url,
            status=status,
            checked_robots=checked_robots,
            robots_allowed=robots_allowed_value,
            pages_checked=pages_checked,
            jobs_found=jobs_found,
            errors=errors,
            source_urls=source_urls,
        )
        return self.repository.save_scan(scan)

    def _fetch(self, url: str) -> FetchResult:
        response = self.fetcher.fetch(url, self.config.user_agent)
        if len(response.text) > self.config.max_response_chars:
            response.text = response.text[: self.config.max_response_chars]
        return response

    def _fetch_no_redirect(self, url: str) -> FetchResult:
        fetch_no_redirect = getattr(self.fetcher, "fetch_no_redirect", None)
        if fetch_no_redirect is None:
            response = self.fetcher.fetch(url, self.config.user_agent)
        else:
            response = fetch_no_redirect(url, self.config.user_agent)
        if len(response.text) > self.config.max_response_chars:
            response.text = response.text[: self.config.max_response_chars]
        return response

    def _fetch_allowed_page(self, target_url: str) -> tuple[FetchResult | None, list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        current_url = target_url
        for redirect_count in range(self.config.max_redirects_per_fetch + 1):
            if is_restricted_platform(current_url):
                return None, [{"code": "restricted_platform", "url": current_url}]
            allowed, error = self._robots_allowed(current_url)
            if not allowed:
                return None, [error]
            response = self._fetch_no_redirect(current_url)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = (response.headers or {}).get("Location") or (response.headers or {}).get("location")
                if not location:
                    return response, errors
                if redirect_count >= self.config.max_redirects_per_fetch:
                    return None, [{"code": "redirect_limit_exceeded", "url": current_url}]
                next_url = urljoin(current_url, location)
                errors.append({"code": "redirect_followed", "from": current_url, "to": next_url})
                current_url = next_url
                continue
            return response, errors
        return None, [{"code": "redirect_limit_exceeded", "url": current_url}]

    def _robots_allowed(self, target_url: str) -> tuple[bool, dict[str, Any]]:
        robots_url = robots_url_for(target_url)
        response = self._fetch_no_redirect(robots_url)
        if response.status_code == 404:
            return True, {}
        if response.status_code in {301, 302, 303, 307, 308}:
            return False, {"code": "robots_redirect_not_followed", "statusCode": response.status_code, "url": robots_url}
        if response.status_code != 200:
            return False, {"code": "robots_unavailable_or_blocked", "statusCode": response.status_code, "url": robots_url}
        allowed = robots_allows(response.text, target_url, self.config.user_agent)
        if allowed:
            return True, {}
        return False, {"code": "robots_disallowed", "url": target_url}

    def _extract_anchors(self, html: str, base_url: str) -> list[dict[str, Any]]:
        parser = _AnchorCollector()
        parser.feed(html)
        anchors = []
        for anchor in parser.anchors:
            href = anchor.get("href") or ""
            if not href or href.startswith(("mailto:", "tel:", "#")):
                continue
            absolute_url = urljoin(base_url, href)
            anchors.append({**anchor, "absolute_url": absolute_url})
        return anchors

    def _career_link_score(self, anchor: dict[str, Any]) -> float:
        text = str(anchor["text"]).casefold()
        href = str(anchor["href"]).casefold()
        score = 0.4
        text_terms = (
            "karriere", "career", "careers", "jobs",
            "carrieres", "carrières", "carriere", "carreras",
            "vacatures", "vacancies", "empleos", "lavoro",
            "kariera", "praca", "carreiras",
        )
        href_terms = (
            "karriere", "career", "careers", "jobs", "stellen",
            "carrieres", "carrieres", "vacatures", "empleos",
            "lavoro", "kariera", "carreiras",
        )
        if any(term in text for term in text_terms):
            score += 0.35
        if any(term in href for term in href_terms):
            score += 0.20
        anchor["score"] = min(score, 1.0)
        return anchor["score"]

    def _looks_like_job_link(self, searchable: str) -> bool:
        return any(term in searchable for term in JOB_TITLE_TERMS) and any(
            path_term in searchable
            for path_term in (
                "job", "jobs", "stellen", "career", "careers", "karriere",
                "position", "vacancy", "vacancies", "vacatures", "carrieres",
                "carriere", "empleos", "lavoro", "kariera", "praca", "carreiras",
            )
        )
