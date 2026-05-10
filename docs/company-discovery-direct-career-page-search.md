# Company Discovery and Direct Career Page Search

Date: 2026-05-08

## Implementability Research

### Feasibility Decision

This feature is implementable, but the safe first build should be a controlled Level 1 MVP, not autonomous broad crawling.

Recommended first build:

1. A user manually adds a company name and website, optionally with a career page URL.
2. The system finds an obvious career page from public homepage links when possible.
3. The system checks robots.txt before fetching public pages.
4. The system fetches only the known career page and a small bounded number of same-site job detail pages.
5. The system extracts schema.org `JobPosting` JSON-LD first and uses HTML job-link fallback second.
6. The system stores discovered jobs in a review queue before importing them into the normal job pipeline.

The current pilot implements Level 1, a local Level 2-style watchlist scan control with explicit scheduling, and a curated Level 3-style suggestion seed. It does not implement broad search-result crawling or unattended production-scale discovery.

### Safe Discovery Methods

Allowed methods for the product:

- Manual company watchlists supplied by the user.
- Public company homepages and public career pages.
- Public homepage links with obvious labels: Karriere, Jobs, Stellenangebote, Career, Careers, Work with us, Join us, Vacancies.
- Public robots.txt and Sitemap references. RFC 9309 defines robots.txt as the standard way service owners communicate crawler access rules, and sitemap.org documents XML sitemap format and sitemap references in robots.txt.
- Structured data in public HTML, especially schema.org `JobPosting` JSON-LD.
- Public RSS/job feeds when clearly offered by the company or ATS.
- Public ATS APIs/feeds where documented, such as Greenhouse Job Board API GET endpoints that expose public job-board data without authentication.
- Search-provider APIs only behind explicit configuration and their own terms. Google Custom Search JSON API is closed to new customers and existing customers must transition by January 1, 2027. Microsoft Bing Search APIs were retired on August 11, 2025, so Bing cannot be assumed as a normal API option.

Do not build a default workflow around scraping search-result HTML pages.

### Compliance Constraints

The implementation must enforce:

- Check robots.txt before career-page fetches and job-detail fetches.
- Stop on disallow, authentication walls, 401/403/429 blocks, CAPTCHA markers, or bot-block pages.
- Do not bypass login, CAPTCHA, paywalls, hidden APIs, or platform restrictions.
- Do not scrape restricted platforms such as LinkedIn, XING, StepStone, Indeed, or other job boards through automation.
- Do not run broad recursive crawling. MVP scans one known company/career page at a time.
- Limit pages per scan, request rate, response size, redirects, and retry behavior.
- Collect only job-posting content needed for the user's workflow.
- Show source URL, source company, discovery date, confidence, and errors before import.
- Provide manual paste/import fallback when a page cannot be scanned safely.

### Technical Feasibility

Company identification:

- Level 1 uses manual user input.
- Level 2 stores watchlists and reuses known career pages.
- Level 3 can rank suggested companies from a curated healthcare taxonomy plus configured search-provider results.
- Level 4 can add provider adapters for documented ATS APIs.

Career page detection:

- Prefer user-provided careerPageUrl.
- Otherwise fetch the homepage if robots.txt allows it.
- Parse public links and rank by label/path terms: karriere, jobs, stellenangebote, career, careers, work-with-us, join-us, vacancies.
- Do not follow more than a small number of candidate links during detection.

Job detection:

- First parse `application/ld+json` blocks and recursively find schema.org `JobPosting`.
- Accept `title` or `name`, `hiringOrganization`, `jobLocation`, `employmentType`, `validThrough`, and `description` when present.
- Use HTML fallback only for visible links/cards that look like jobs.
- If detail-page fetching is enabled, fetch only same-host or explicitly allowed ATS links, with max-page limits.

Deduplication:

- Same source URL.
- Same company plus normalized title.
- Similar title plus similar description.
- Same external ATS link.
- Same deadline/location when available.

Scheduling:

- Level 2 should run scans in a background queue, not in UI request handlers.
- Store CompanyDiscoveryRun and CareerPageScan records with pagesChecked, jobsFound, errors, and finish status.
- Use per-user and per-domain rate limits.

False positive controls:

- Confidence is higher when JobPosting structured data exists, title/company/url are clear, and description/location/deadline are present.
- Confidence is lower for generic links, sparse cards, or external redirects.
- Queue all discoveries for human-visible review before import.

### MVP Level Classification

Level 1 MVP: Safe and realistic now.

- Manual company creation.
- Career page URL storage or homepage career-link detection.
- Public allowed-page scan.
- JSON-LD JobPosting extraction.
- HTML fallback job-link extraction.
- DiscoveredJob review queue.
- Import discovered job into the normal Job entity/pipeline.

Level 2: Partially implemented for the local pilot.

- Watchlists.
- User-triggered scan-all-watched-company runs.
- Explicit local-process periodic checks with rate limits.
- Notifications remain a follow-up.
- Per-domain rate limits and scan history.

Level 3: Partially implemented with curated data only.

- Company suggestions from curated healthcare employers and category taxonomy.
- Allowed search APIs remain extension points.
- Ranking by target roles, industry, location, healthcare-management persona, and role family.
- No default scraping of search-result pages.

Level 4: Realistic provider by provider.

- Official ATS/job APIs or feeds where available.
- Examples: Greenhouse Job Board API public GET endpoints; Lever public postings API. Each adapter needs separate terms review and tests.

## Product Behavior

### Company Discovery / Watchlist

Show:

- Search or add company.
- Company category/sector.
- Website and career page.
- Last checked.
- Jobs discovered.
- Watch status.
- Relevance to profile.
- Companies needing career-page setup.

### Company Detail

Show:

- Company summary.
- Website.
- Career page.
- Sector.
- Notes.
- Last scan status.
- Discovered jobs.
- Actions: Scan career page, Import matching jobs, Analyze discovered jobs.

### Discovered Jobs Queue

Show:

- "Discovered from company website" source label.
- Source company.
- Career-page URL and job source URL.
- Discovery date.
- Confidence level.
- Fit status after analysis.
- Actions: Analyze, Save, Skip, Add to tracker.

### Dashboard Integration

Show:

- Companies watched.
- New direct-company jobs discovered.
- Best direct-company matches.
- Companies needing career-page setup.
- Last discovery run status.

## Data Model

Use existing naming conventions in the target app, but preserve these concepts:

```text
Company
- id
- userId
- name
- websiteUrl
- careerPageUrl
- sector
- relevanceScore
- relevanceReason
- watchEnabled
- notes
- createdAt
- updatedAt

CompanyDiscoveryRun
- id
- userId
- companyId nullable
- query nullable
- sourceType
- status
- startedAt
- finishedAt
- pagesChecked
- jobsFound
- errors JSON
- createdAt

CareerPageScan
- id
- userId
- companyId
- careerPageUrl
- status
- checkedRobots
- robotsAllowed
- lastCheckedAt
- pagesChecked
- jobsFound
- errors JSON
- createdAt

DiscoveredJob
- id
- userId
- companyId
- sourceUrl
- title
- location
- rawSnippet
- rawDescription
- structuredData JSON
- confidenceScore
- importedJobId nullable
- discoveredAt
- createdAt
- updatedAt
```

## Backend Service Boundaries

Keep all fetch/scanning behavior outside UI components and route handlers.

Recommended layers:

- CompanyRepository: CRUD for companies, runs, scans, discovered jobs.
- CareerPageScanner: robots checks, bounded fetches, JSON-LD extraction, HTML fallback extraction.
- DirectJobDeduplicator: URL/title/description/ATS dedupe.
- DirectJobImporter: maps DiscoveredJob into the existing Job entity and triggers normal scoring.
- CompanySuggestionService: curated taxonomy and configured search-provider integration.
- MCP tools: thin wrappers over the service layer.

## MCP Tool Surface

Tools should expose explicit input/output schemas and return uncertainty/errors clearly:

- suggest_relevant_companies
- add_company_to_watchlist
- find_company_career_page
- scan_company_career_page
- extract_direct_jobs_from_company_site
- import_discovered_job
- deduplicate_discovered_jobs
- get_company_watchlist_summary

Tool rules:

- No restricted-platform scraping.
- No login/CAPTCHA bypass.
- No broad crawling by default.
- robots.txt must be checked for company-site scans.
- Tool output must include status, pagesChecked, jobsFound, errors, and confidence.

## Implementation Phase Update

Add this phase after the Search Strategy Module and before final UX polish:

Phase: Company Discovery and Direct Career Page Search

- Research safe implementation options.
- Add data model for companies, career-page scans, discovery runs, and discovered jobs.
- Add company watchlist UI.
- Add company detail UI.
- Add user-triggered scan flow.
- Add structured-data extraction for JobPosting where possible.
- Add safe HTML fallback extraction using fixtures.
- Add deduplication against existing jobs.
- Add import-to-job-pipeline action.
- Add dashboard metrics for watched companies and direct-company discoveries.
- Add MCP tools for company discovery.
- Add tests with local fixtures.
- Document realistic limitations.

## Sources

- RFC 9309 Robots Exclusion Protocol: https://www.rfc-editor.org/rfc/rfc9309.html
- Google robots.txt documentation: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- schema.org JobPosting: https://schema.org/JobPosting
- Google JobPosting structured data documentation: https://developers.google.com/search/docs/appearance/structured-data/job-posting
- Sitemaps protocol: https://www.sitemaps.org/protocol.html
- Google Custom Search JSON API overview: https://developers.google.com/custom-search/v1/overview
- Microsoft Bing Search API retirement notice: https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement
- Greenhouse Job Board API: https://developer.greenhouse.io/job-board.html
- Lever Postings API: https://github.com/lever/postings-api
