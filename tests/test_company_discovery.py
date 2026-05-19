# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import AppState, jsonable
from company_discovery.ai_providers import AIProviderConfig, validate_provider_config
from company_discovery.analysis import build_job_decision_brief_prompt, execute_job_decision_brief
from company_discovery.auth import AuthStore
from company_discovery.http_fetcher import validate_public_http_url
from company_discovery.mcp_tools import TOOL_SCHEMAS, CompanyDiscoveryMCPTools
from company_discovery.models import (
    CareerPageScan,
    Company,
    CompanyDiscoveryRun,
    DiscoveredJob,
    ImportedJob,
)
from company_discovery.repository import InMemoryCompanyDiscoveryRepository
from company_discovery.service import (
    CompanyDiscoveryService,
    FetchResult,
    ScanConfig,
    StaticFetcher,
    robots_allows,
)
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository
from mcp_server import handle_request

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class CompanyDiscoveryTests(unittest.TestCase):
    def build_service(
        self, routes: dict[str, str | tuple[int, str]], max_pages: int = 5
    ) -> CompanyDiscoveryService:
        return CompanyDiscoveryService(
            InMemoryCompanyDiscoveryRepository(),
            StaticFetcher(routes),
            ScanConfig(max_pages_per_scan=max_pages),
        )

    def test_company_relevance_suggestion_prefers_digital_health(self) -> None:
        service = self.build_service({})
        suggestions = service.suggest_relevant_companies(
            target_roles=["Digital Health Project Management"],
            industry="Healthcare",
            location="Berlin",
        )
        self.assertEqual(suggestions[0]["type"], "company")
        self.assertIn("career_page_url", suggestions[0])
        self.assertTrue(
            any(item.get("category") == "Digital Health startups" for item in suggestions)
        )
        self.assertGreaterEqual(suggestions[0]["relevanceScore"], 0.65)

    def test_find_company_career_page_from_homepage_link(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example": fixture("home_with_career_link.html"),
            }
        )
        company = service.create_company(
            user_id="u1", name="Demo", website_url="https://demo.example"
        )
        result = service.find_company_career_page("u1", company.id)
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["careerPageUrl"], "https://demo.example/karriere")

    def test_robots_allow_and_disallow_handling(self) -> None:
        robots = fixture("robots_disallow.txt")
        self.assertFalse(
            robots_allows(robots, "https://demo.example/karriere", "CompanyDiscoveryBot")
        )
        self.assertFalse(
            robots_allows(robots, "https://demo.example/jobs/123", "CompanyDiscoveryBot")
        )
        self.assertTrue(robots_allows(robots, "https://demo.example/about", "CompanyDiscoveryBot"))

    def test_jobposting_json_ld_extraction_and_scan(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("career_jobposting.html"),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo Klinikgruppe",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        jobs = service.repository.list_discovered_jobs("u1")
        self.assertEqual(scan.status, "completed")
        self.assertEqual(scan.jobs_found, 1)
        self.assertEqual(jobs[0].title, "Junior Healthcare Project Manager")
        self.assertEqual(jobs[0].location, "Berlin, DE")
        self.assertGreaterEqual(jobs[0].confidence_score, 0.9)

    def test_html_fallback_job_link_extraction(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("career_plain_cards.html"),
                "https://demo.example/jobs/digital-health-project-coordinator": fixture(
                    "detail_plain_job.html"
                ),
                "https://demo.example/jobs/market-access-analyst": fixture("detail_plain_job.html"),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        titles = {job.title for job in service.repository.list_discovered_jobs("u1")}
        self.assertEqual(scan.jobs_found, 2)
        self.assertIn("Junior Projektkoordinator Digital Health", titles)
        self.assertIn("Market Access Analyst Healthcare", titles)

    def test_direct_job_deduplication_same_url(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("duplicate_jobs.html"),
                "https://demo.example/jobs/project-manager-healthcare": fixture(
                    "detail_plain_job.html"
                ),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.jobs_found, 1)
        self.assertEqual(len(service.repository.list_discovered_jobs("u1")), 1)

    def test_import_discovered_job_into_pipeline_placeholder(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("career_jobposting.html"),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo Klinikgruppe",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        service.scan_company_career_page("u1", company.id)
        discovered = service.repository.list_discovered_jobs("u1")[0]
        imported = service.import_discovered_job("u1", discovered.id)
        self.assertEqual(imported.source_type, "direct_company")
        self.assertEqual(imported.analysis_status, "pending")
        self.assertEqual(
            service.repository.discovered_jobs[discovered.id].imported_job_id, imported.id
        )

    def test_safe_failure_when_page_blocked(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("blocked_page.html"),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.status, "blocked_or_captcha")
        self.assertEqual(scan.jobs_found, 0)

    def test_scan_stops_when_robots_disallow(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_disallow.txt"),
                "https://demo.example/karriere": fixture("career_jobposting.html"),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.status, "blocked_by_robots")
        self.assertFalse(scan.robots_allowed)
        self.assertEqual(scan.pages_checked, 0)

    def test_redirect_target_requires_its_own_robots_allowance(self) -> None:
        class RedirectFetcher:
            def fetch(self, url: str, user_agent: str) -> FetchResult:
                if url == "https://demo.example/robots.txt":
                    return FetchResult(url=url, status_code=200, text="User-agent: *\nAllow: /\n")
                if url == "https://other.example/robots.txt":
                    return FetchResult(
                        url=url, status_code=200, text="User-agent: *\nDisallow: /jobs\n"
                    )
                return FetchResult(url=url, status_code=404, text="")

            def fetch_no_redirect(self, url: str, user_agent: str) -> FetchResult:
                if url == "https://demo.example/robots.txt":
                    return FetchResult(url=url, status_code=200, text="User-agent: *\nAllow: /\n")
                if url == "https://other.example/robots.txt":
                    return FetchResult(
                        url=url, status_code=200, text="User-agent: *\nDisallow: /jobs\n"
                    )
                if url == "https://demo.example/karriere":
                    return FetchResult(
                        url=url,
                        status_code=302,
                        text="",
                        headers={"Location": "https://other.example/jobs"},
                    )
                if url == "https://other.example/jobs":
                    return FetchResult(
                        url=url, status_code=200, text=fixture("career_jobposting.html")
                    )
                return FetchResult(url=url, status_code=404, text="")

        service = CompanyDiscoveryService(
            InMemoryCompanyDiscoveryRepository(),
            RedirectFetcher(),  # type: ignore[arg-type]
            ScanConfig(max_pages_per_scan=5),
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.status, "blocked_by_robots")
        self.assertEqual(scan.jobs_found, 0)
        self.assertTrue(any(error["code"] == "robots_disallowed" for error in scan.errors))

    def test_robots_txt_redirect_is_not_followed(self) -> None:
        class RedirectingRobotsFetcher:
            def fetch(self, url: str, user_agent: str) -> FetchResult:
                return self.fetch_no_redirect(url, user_agent)

            def fetch_no_redirect(self, url: str, user_agent: str) -> FetchResult:
                if url == "https://demo.example/robots.txt":
                    return FetchResult(
                        url=url,
                        status_code=302,
                        text="",
                        headers={"Location": "https://other.example/robots.txt"},
                    )
                return FetchResult(url=url, status_code=200, text=fixture("career_jobposting.html"))

        service = CompanyDiscoveryService(
            InMemoryCompanyDiscoveryRepository(),
            RedirectingRobotsFetcher(),  # type: ignore[arg-type]
            ScanConfig(max_pages_per_scan=5),
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.status, "blocked_or_unavailable")
        self.assertTrue(
            any(error["code"] == "robots_redirect_not_followed" for error in scan.errors)
        )

    def test_rate_limit_max_page_guard(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("career_plain_cards.html"),
                "https://demo.example/jobs/digital-health-project-coordinator": fixture(
                    "detail_plain_job.html"
                ),
                "https://demo.example/jobs/market-access-analyst": fixture("detail_plain_job.html"),
            },
            max_pages=2,
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.pages_checked, 2)
        self.assertTrue(any(error["code"] == "max_pages_reached" for error in scan.errors))

    def test_no_jobs_page_completes_empty(self) -> None:
        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("no_jobs.html"),
            }
        )
        company = service.create_company(
            user_id="u1",
            name="Demo",
            website_url="https://demo.example",
            career_page_url="https://demo.example/karriere",
        )
        scan = service.scan_company_career_page("u1", company.id)
        self.assertEqual(scan.status, "completed")
        self.assertEqual(scan.jobs_found, 0)

    def test_mcp_tool_schemas_and_scan_wrapper(self) -> None:
        names = {schema["name"] for schema in TOOL_SCHEMAS}
        self.assertIn("scan_company_career_page", names)
        self.assertIn("import_discovered_job", names)

        service = self.build_service(
            {
                "https://demo.example/robots.txt": fixture("robots_allow.txt"),
                "https://demo.example/karriere": fixture("career_jobposting.html"),
            }
        )
        tools = CompanyDiscoveryMCPTools(service)
        created = tools.add_company_to_watchlist(
            userId="u1",
            name="Demo",
            websiteUrl="https://demo.example",
            careerPageUrl="https://demo.example/karriere",
        )
        result = tools.scan_company_career_page("u1", created["company"]["id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["scan"]["jobs_found"], 1)

    def test_mcp_stdio_bridge_lists_and_calls_tools(self) -> None:
        service = self.build_service({})
        tools = CompanyDiscoveryMCPTools(service)
        listed = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, tools)
        self.assertEqual(listed["result"]["tools"][0]["name"], "suggest_relevant_companies")

        called = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "suggest_relevant_companies",
                    "arguments": {
                        "targetRoles": ["Digital Health"],
                        "industry": "Healthcare",
                        "location": "Berlin",
                    },
                },
            },
            tools,
        )
        self.assertFalse(called["result"]["isError"])
        self.assertIn("Vivantes", called["result"]["content"][0]["text"])

    def test_fetcher_blocks_private_and_local_hosts(self) -> None:
        self.assertEqual(validate_public_http_url("http://127.0.0.1:8000")[0], False)
        self.assertEqual(validate_public_http_url("http://localhost:8000")[0], False)
        self.assertEqual(validate_public_http_url("file:///tmp/jobs.html")[0], False)

    def test_provider_config_is_provider_neutral_and_rejects_raw_secrets(self) -> None:
        valid = AIProviderConfig(provider_id="codex_cli", invocation_mode="cli", command="codex")
        self.assertEqual(validate_provider_config(valid), [])
        invalid = AIProviderConfig(
            provider_id="openai", invocation_mode="api", credential_reference="sk-secret"
        )
        self.assertEqual(validate_provider_config(invalid)[0]["code"], "raw_secret_not_allowed")

    def test_job_decision_brief_prompt_is_provider_neutral(self) -> None:
        job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://demo.example/jobs/1",
            title="Junior Digital Health Project Manager",
            company_name="Demo Klinikgruppe",
            location="Berlin",
            description="Coordinate digital health implementation projects.",
        )
        brief = build_job_decision_brief_prompt(
            job,
            AIProviderConfig(provider_id="gemini", invocation_mode="api", model="user-selected"),
        )
        self.assertIn("Job Decision Brief", brief["title"])
        self.assertIn("Junior Digital Health Project Manager", brief["prompt"])
        self.assertIn("user's selected AI subscription", brief["handoffInstruction"])

    def test_analysis_execution_falls_back_without_provider_credentials(self) -> None:
        job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://demo.example/jobs/1",
            title="Junior Role",
            company_name="Demo",
        )
        manual = execute_job_decision_brief(job, AIProviderConfig())
        self.assertEqual(manual.status, "handoff_required")
        missing_key = execute_job_decision_brief(
            job,
            AIProviderConfig(
                provider_id="openai", invocation_mode="api", credential_reference="MISSING_TEST_KEY"
            ),
        )
        self.assertEqual(missing_key.status, "configuration_error")

    def test_analysis_accepts_session_only_provider_key_without_persisting_it(self) -> None:
        job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://demo.example/jobs/1",
            title="Junior Role",
            company_name="Demo",
        )
        seen: dict[str, str | None] = {}

        class FakeResponse:
            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "Fit score: 82"}}]}).encode(
                    "utf-8"
                )

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            seen["authorization"] = request.get_header("Authorization")  # type: ignore[attr-defined]
            return FakeResponse()

        with patch("company_discovery.analysis.urlopen", fake_urlopen):
            result = execute_job_decision_brief(
                job,
                AIProviderConfig(provider_id="openai", invocation_mode="api"),
                runtime_credential="sk-session-test",
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(seen["authorization"], "Bearer sk-session-test")

    def test_delete_company_cascades_related_records(self) -> None:
        repo = InMemoryCompanyDiscoveryRepository()
        company = repo.save_company(
            Company(user_id="u1", name="Demo", website_url="https://demo.example")
        )
        repo.save_discovery_run(
            CompanyDiscoveryRun(user_id="u1", company_id=company.id, source_type="career_page_scan")
        )
        repo.save_scan(
            CareerPageScan(
                user_id="u1",
                company_id=company.id,
                career_page_url="https://demo.example/jobs",
                status="completed",
                checked_robots=True,
                robots_allowed=True,
            )
        )
        discovered = repo.save_discovered_job(
            DiscoveredJob(
                user_id="u1",
                company_id=company.id,
                source_url="https://demo.example/jobs/1",
                title="Role",
            )
        )
        repo.save_imported_job(
            ImportedJob(
                user_id="u1",
                company_id=company.id,
                discovered_job_id=discovered.id,
                source_url=discovered.source_url,
                title=discovered.title,
                company_name=company.name,
            )
        )
        repo.delete_company("u1", company.id)
        self.assertEqual(repo.list_companies("u1"), [])
        self.assertEqual(repo.list_discovery_runs("u1"), [])
        self.assertEqual(repo.list_scans("u1"), [])
        self.assertEqual(repo.list_discovered_jobs("u1"), [])
        self.assertEqual(repo.list_imported_jobs("u1"), [])

    def test_sqlite_repository_persists_and_reloads_state(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "pilot.sqlite3"
            repo = SqliteCompanyDiscoveryRepository(db_path)
            company = repo.save_company(
                Company(user_id="u1", name="Demo", website_url="https://demo.example")
            )
            discovered = repo.save_discovered_job(
                DiscoveredJob(
                    user_id="u1",
                    company_id=company.id,
                    source_url="https://demo.example/jobs/1",
                    title="Junior Role",
                )
            )
            repo.save_imported_job(
                ImportedJob(
                    user_id="u1",
                    company_id=company.id,
                    discovered_job_id=discovered.id,
                    source_url=discovered.source_url,
                    title=discovered.title,
                    company_name=company.name,
                )
            )
            repo.close()

            reloaded = SqliteCompanyDiscoveryRepository(db_path)
            self.assertEqual(reloaded.list_companies("u1")[0].name, "Demo")
            self.assertEqual(reloaded.list_discovered_jobs("u1")[0].title, "Junior Role")
            self.assertEqual(reloaded.list_imported_jobs("u1")[0].company_name, "Demo")
            reloaded.close()

    def test_app_state_exports_imports_and_reports_health(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = AppState(
                root / "source.sqlite3",
                root / "source_auth.sqlite3",
                root / "source_ai.json",
                root / "source_schedule.json",
                start_scheduler=False,
            )
            user = state.auth_store.create_user("tester@example.com", "very-secure-password")
            state.seed_demo(user.id)
            exported = json.loads(json.dumps(jsonable(state.export_data(user.id))))
            self.assertEqual(exported["schemaVersion"], 1)
            self.assertEqual(state.health(user.id)["status"], "ok")

            restored = AppState(
                root / "restored.sqlite3",
                root / "restored_auth.sqlite3",
                root / "restored_ai.json",
                root / "restored_schedule.json",
                start_scheduler=False,
            )
            restored_user = restored.auth_store.create_user(
                "restored@example.com", "very-secure-password"
            )
            result = restored.import_data(restored_user.id, exported)
            self.assertEqual(result["counts"]["companies"], 1)
            self.assertEqual(restored.health(restored_user.id)["counts"]["discoveredJobs"], 1)
            state.auth_store.close()
            state.repository.close()
            restored.auth_store.close()
            restored.repository.close()

    def test_auth_store_hashes_passwords_and_sessions(self) -> None:
        with TemporaryDirectory() as tmp:
            store = AuthStore(Path(tmp) / "auth.sqlite3", "test-secret-key-with-enough-entropy-123")
            user = store.create_user("Tester@Example.com", "very-secure-password")
            self.assertEqual(user.email, "tester@example.com")
            self.assertEqual(user.role, "member")
            self.assertIsNotNone(store.authenticate("tester@example.com", "very-secure-password"))
            self.assertIsNone(store.authenticate("tester@example.com", "wrong-password"))
            session = store.create_session(user)
            restored = store.get_session(session.token)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.user.id, user.id)
            self.assertEqual(restored.csrf_token, session.csrf_token)
            store.delete_session(session.token)
            self.assertIsNone(store.get_session(session.token))
            store.close()

    def test_auth_store_admin_user_management_controls_access(self) -> None:
        with TemporaryDirectory() as tmp:
            store = AuthStore(Path(tmp) / "auth.sqlite3", "test-secret-key-with-enough-entropy-123")
            admin = store.create_user("admin@example.com", "very-secure-password", role="admin")
            tester = store.create_user("tester@example.com", "very-secure-password")
            self.assertTrue(admin.is_admin)
            self.assertFalse(tester.is_admin)
            self.assertEqual(store.count_active_admins(), 1)

            session = store.create_session(tester)
            store.update_user(tester.id, active=False)
            self.assertIsNone(store.authenticate("tester@example.com", "very-secure-password"))
            self.assertIsNone(store.get_session(session.token))

            store.update_user(tester.id, active=True, password="new-secure-password")
            self.assertIsNone(store.authenticate("tester@example.com", "very-secure-password"))
            self.assertIsNotNone(store.authenticate("tester@example.com", "new-secure-password"))
            session = store.create_session(
                store.authenticate("tester@example.com", "new-secure-password")
            )
            store.update_user(tester.id, password="newer-secure-password")
            self.assertIsNone(store.get_session(session.token))

            with self.assertRaises(ValueError):
                store.update_user(admin.id, role="member")
            store.update_user(tester.id, role="admin")
            store.update_user(admin.id, role="member")
            self.assertEqual(store.count_active_admins(), 1)
            store.close()

    def test_app_state_login_rate_limit_tracks_failures(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = AppState(
                root / "source.sqlite3",
                root / "source_auth.sqlite3",
                root / "source_ai.json",
                root / "source_schedule.json",
                start_scheduler=False,
            )
            for _ in range(10):
                self.assertTrue(state.login_allowed("127.0.0.1"))
                state.record_login_failure("127.0.0.1")
            self.assertFalse(state.login_allowed("127.0.0.1"))
            state.clear_login_failures("127.0.0.1")
            self.assertTrue(state.login_allowed("127.0.0.1"))
            state.auth_store.close()
            state.repository.close()


if __name__ == "__main__":
    unittest.main()
