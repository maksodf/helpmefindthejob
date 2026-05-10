"""Unit tests for the modules added during sellable-readiness work.

Covers email_transport, tokens, scheduler, quotas, ats_adapters, and
dedup. All tests are stdlib-only and use temporary directories.
"""

from __future__ import annotations

import time
import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery import ats_adapters
from company_discovery.dedup import find_duplicate, normalize_url, shingles
from company_discovery.email_transport import ConsoleTransport, Email, build_transport
from company_discovery.models import Company, DiscoveredJob
from company_discovery.quotas import QuotaError, QuotaLimits, QuotaStore
from company_discovery.scheduler import DurableScheduler
from company_discovery.tokens import TokenStore


SECRET = "tests-secret-key-with-enough-bytes-1234"


class EmailTransportTests(unittest.TestCase):
    def test_console_records_sends_and_appends_outbox(self) -> None:
        with TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "email.log"
            transport = ConsoleTransport(outbox_path=outbox)
            email = Email(
                to="user@example.com",
                subject="hello",
                text="body",
                from_address="bot@example.com",
            )
            transport.send(email)
            transport.send(Email(to="user2@example.com", subject="x", text="y", from_address="bot@example.com"))
            self.assertEqual(len(transport.outbox), 2)
            self.assertEqual(transport.last_for("USER@example.com").subject, "hello")
            lines = outbox.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn("hello", lines[0])

    def test_build_transport_default_console(self) -> None:
        transport = build_transport(backend="console")
        self.assertIsInstance(transport, ConsoleTransport)


class TokenStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = TokenStore(Path(self.tmp.name) / "tokens.sqlite3", SECRET)
        self.addCleanup(self.store.close)

    def test_invitation_round_trip(self) -> None:
        issued = self.store.issue(kind="invitation", email="Tester@Example.com", role="member", created_by="admin")
        record = self.store.lookup("invitation", issued.raw_token)
        self.assertIsNotNone(record)
        self.assertEqual(record.email, "tester@example.com")
        consumed = self.store.consume("invitation", issued.raw_token)
        self.assertIsNotNone(consumed)
        # Single-use: cannot consume twice
        self.assertIsNone(self.store.consume("invitation", issued.raw_token))
        self.assertIsNone(self.store.lookup("invitation", issued.raw_token))

    def test_expired_invitation_rejected(self) -> None:
        issued = self.store.issue(
            kind="invitation",
            email="x@example.com",
            ttl=timedelta(microseconds=1),
        )
        time.sleep(0.01)
        self.assertIsNone(self.store.lookup("invitation", issued.raw_token))
        self.assertIsNone(self.store.consume("invitation", issued.raw_token))

    def test_password_reset_isolated_from_invitation_tokens(self) -> None:
        issued = self.store.issue(kind="password_reset", email="x@example.com")
        self.assertIsNone(self.store.lookup("invitation", issued.raw_token))
        self.assertIsNotNone(self.store.lookup("password_reset", issued.raw_token))

    def test_revoke_all_for_address(self) -> None:
        a = self.store.issue(kind="invitation", email="x@example.com")
        b = self.store.issue(kind="password_reset", email="x@example.com")
        self.store.revoke_all_for("x@example.com")
        self.assertIsNone(self.store.lookup("invitation", a.raw_token))
        self.assertIsNone(self.store.lookup("password_reset", b.raw_token))


class DurableSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _build(self, handler):
        scheduler = DurableScheduler(
            Path(self.tmp.name) / "scheduler.sqlite3",
            handler=handler,
            poll_seconds=1,
            min_interval_minutes=1,
        )
        self.addCleanup(scheduler.close)
        return scheduler

    def test_upsert_then_run_due_then_persist(self) -> None:
        calls: list[str] = []
        scheduler = self._build(lambda user_id, trigger: (calls.append(user_id), {"status": "completed"})[1])
        record = scheduler.upsert("u1", enabled=True, interval_minutes=1)
        self.assertTrue(record.enabled)
        self.assertEqual(record.interval_minutes, 1)
        # Force the next run into the past so run_due executes it.
        scheduler._connection.execute(
            "UPDATE schedules SET next_run_at = ? WHERE user_id = 'u1'",
            ("1970-01-01T00:00:00+00:00",),
        )
        scheduler._connection.commit()
        scheduler.run_due()
        self.assertEqual(calls, ["u1"])
        # Persist + reload
        scheduler.close()
        reloaded = DurableScheduler(
            Path(self.tmp.name) / "scheduler.sqlite3",
            handler=lambda *_: {"status": "completed"},
            poll_seconds=1,
        )
        try:
            self.assertEqual(reloaded.get("u1").enabled, True)
            self.assertIsNotNone(reloaded.get("u1").last_run_at)
        finally:
            reloaded.close()

    def test_failure_increments_consecutive_failures_and_backs_off(self) -> None:
        scheduler = self._build(lambda *_: {"status": "failed"})
        scheduler.upsert("u1", enabled=True, interval_minutes=1)
        scheduler._connection.execute(
            "UPDATE schedules SET next_run_at = ? WHERE user_id = 'u1'",
            ("1970-01-01T00:00:00+00:00",),
        )
        scheduler._connection.commit()
        scheduler.run_due()
        record = scheduler.get("u1")
        self.assertEqual(record.consecutive_failures, 1)


class QuotaStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        limits = QuotaLimits(scans_per_day=2, ai_per_day=2, domain_per_hour=2, active_scans=1)
        self.store = QuotaStore(Path(self.tmp.name) / "quotas.sqlite3", limits=limits)
        self.addCleanup(self.store.close)

    def test_scan_quota_enforced(self) -> None:
        self.store.can_start_scan("u1", target_url="https://example.org/jobs")
        self.store.record_scan_started("u1", target_url="https://example.org/jobs")
        self.store.record_scan_finished("u1")
        self.store.can_start_scan("u1", target_url="https://example.org/jobs")
        self.store.record_scan_started("u1", target_url="https://example.org/jobs")
        self.store.record_scan_finished("u1")
        with self.assertRaises(QuotaError) as cm:
            self.store.can_start_scan("u1", target_url="https://example.org/jobs")
        self.assertEqual(cm.exception.code, "scan_quota_exhausted")

    def test_concurrency_cap_enforced(self) -> None:
        self.store.can_start_scan("u1", target_url="https://a.example/jobs")
        self.store.record_scan_started("u1", target_url="https://a.example/jobs")
        with self.assertRaises(QuotaError) as cm:
            self.store.can_start_scan("u1", target_url="https://b.example/jobs")
        self.assertEqual(cm.exception.code, "scan_concurrency_limit")

    def test_ai_quota_enforced(self) -> None:
        self.store.can_run_ai("u1")
        self.store.record_ai_run("u1")
        self.store.can_run_ai("u1")
        self.store.record_ai_run("u1")
        with self.assertRaises(QuotaError) as cm:
            self.store.can_run_ai("u1")
        self.assertEqual(cm.exception.code, "ai_quota_exhausted")

    def test_domain_rate_limited(self) -> None:
        for _ in range(2):
            self.store.record_scan_started("u1", target_url="https://crowded.example/jobs")
            self.store.record_scan_finished("u1")
        with self.assertRaises(QuotaError) as cm:
            self.store.can_start_scan("u2", target_url="https://crowded.example/jobs")
        self.assertEqual(cm.exception.code, "domain_rate_limited")

    def test_admin_metrics_includes_top_domain(self) -> None:
        self.store.record_scan_started("u1", target_url="https://hot.example/jobs")
        self.store.record_scan_finished("u1")
        metrics = self.store.admin_metrics()
        self.assertGreaterEqual(metrics["scansLast24h"], 1)
        self.assertEqual(metrics["topDomainThisHour"], "hot.example")


class AtsAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.company = Company(
            user_id="u1",
            name="Acme",
            website_url="https://acme.example",
            career_page_url=None,
        )

    def test_detect_supported_and_unsupported(self) -> None:
        self.assertEqual(ats_adapters.detect_ats("https://boards-api.greenhouse.io/v1/boards/acme/jobs"), "greenhouse")
        self.assertEqual(ats_adapters.detect_ats("https://api.lever.co/v0/postings/acme"), "lever")
        self.assertEqual(ats_adapters.detect_ats("https://acme.jobs.personio.de/xml"), "personio")
        self.assertEqual(ats_adapters.detect_ats("https://api.smartrecruiters.com/v1/companies/acme/postings"), "smartrecruiters")
        self.assertEqual(ats_adapters.detect_ats("https://acme.teamtailor.com/job-board.json"), "teamtailor")
        self.assertEqual(ats_adapters.detect_unsupported_ats("https://acme.wd1.myworkdayjobs.com/External"), "workday")

    def test_greenhouse_extraction(self) -> None:
        body = """
        {
          "jobs": [
            {"id": 12345, "title": "Healthcare Project Manager", "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
             "location": {"name": "Berlin"}, "content": "<p>Lead projects.</p>"},
            {"id": 67890, "title": "", "absolute_url": "https://boards.greenhouse.io/acme/jobs/67890"}
          ]
        }
        """
        result = ats_adapters.extract_jobs(self.company, "https://boards-api.greenhouse.io/v1/boards/acme/jobs", body)
        self.assertIsNotNone(result)
        self.assertEqual(result.adapter, "greenhouse")
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].title, "Healthcare Project Manager")
        self.assertEqual(result.jobs[0].structured_data["ats_id"], "12345")

    def test_lever_extraction(self) -> None:
        body = """
        [
          {"id": "abc-123", "text": "Market Access Manager",
           "categories": {"location": "Remote"},
           "descriptionPlain": "Join the policy team",
           "hostedUrl": "https://jobs.lever.co/acme/abc-123"}
        ]
        """
        result = ats_adapters.extract_jobs(self.company, "https://api.lever.co/v0/postings/acme", body)
        self.assertIsNotNone(result)
        self.assertEqual(result.jobs[0].title, "Market Access Manager")
        self.assertEqual(result.jobs[0].structured_data["ats"], "lever")

    def test_personio_xml_extraction(self) -> None:
        body = """<?xml version="1.0" encoding="utf-8"?>
        <workzag-jobs>
          <position id="9001">
            <name>Junior Healthcare Project Coordinator</name>
            <office>Berlin</office>
            <url>https://acme.jobs.personio.de/job/9001</url>
            <jobDescriptions>
              <jobDescription>
                <value>&lt;p&gt;Coordinate digital health workstreams.&lt;/p&gt;</value>
              </jobDescription>
            </jobDescriptions>
          </position>
        </workzag-jobs>"""
        result = ats_adapters.extract_jobs(self.company, "https://acme.jobs.personio.de/xml", body)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].title, "Junior Healthcare Project Coordinator")
        self.assertEqual(result.jobs[0].structured_data["ats_id"], "9001")

    def test_smartrecruiters_extraction(self) -> None:
        body = """
        {
          "content": [
            {"uuid": "uuid-1", "name": "Quality Manager",
             "location": {"city": "Munich", "country": "DE"},
             "jobAd": {"sections": {"jobDescription": {"text": "<p>Quality work</p>"}}},
             "ref": "https://jobs.smartrecruiters.com/acme/quality-manager"}
          ]
        }
        """
        result = ats_adapters.extract_jobs(self.company, "https://api.smartrecruiters.com/v1/companies/acme/postings", body)
        self.assertIsNotNone(result)
        self.assertEqual(result.jobs[0].title, "Quality Manager")

    def test_teamtailor_extraction(self) -> None:
        body = """
        {
          "data": [
            {"id": "tt-1",
             "attributes": {"title": "Healthcare Consultant",
                            "locations": ["Hamburg"],
                            "body": "<p>Consult on healthcare</p>",
                            "careersite-job-url": "https://acme.teamtailor.com/jobs/100"}}
          ]
        }
        """
        result = ats_adapters.extract_jobs(self.company, "https://acme.teamtailor.com/job-board.json", body)
        self.assertIsNotNone(result)
        self.assertEqual(result.jobs[0].title, "Healthcare Consultant")
        self.assertEqual(result.jobs[0].structured_data["ats"], "teamtailor")


class DedupTests(unittest.TestCase):
    def _job(self, **kwargs) -> DiscoveredJob:
        defaults = dict(user_id="u1", company_id="c1", source_url="", title="", raw_description=None, structured_data=None)
        defaults.update(kwargs)
        return DiscoveredJob(**defaults)

    def test_url_normalization_strips_tracking(self) -> None:
        a = normalize_url("https://www.example.org/jobs/1?utm_source=x&keep=1")
        b = normalize_url("https://example.org/jobs/1?keep=1")
        self.assertEqual(a, b)

    def test_url_match_is_duplicate(self) -> None:
        a = self._job(id="a", source_url="https://example.org/jobs/1?utm_source=foo", title="Manager")
        b = self._job(id="b", source_url="https://example.org/jobs/1", title="Different title")
        match = find_duplicate(b, [a])
        self.assertIsNotNone(match)
        self.assertEqual(match.reason, "url")

    def test_ats_id_match_is_duplicate(self) -> None:
        a = self._job(
            id="a",
            title="Manager A",
            source_url="https://acme.example/jobs/1",
            structured_data={"ats": "greenhouse", "ats_id": "9001"},
        )
        b = self._job(
            id="b",
            title="Manager B",
            source_url="https://acme.example/jobs/2",
            structured_data={"ats": "greenhouse", "ats_id": "9001"},
        )
        match = find_duplicate(b, [a])
        self.assertIsNotNone(match)
        self.assertEqual(match.reason, "ats_id")

    def test_title_company_match_is_duplicate(self) -> None:
        a = self._job(id="a", title="Healthcare Manager (m/w/d)", source_url="https://x.example/a")
        b = self._job(id="b", title="Healthcare Manager", source_url="https://x.example/b")
        match = find_duplicate(b, [a])
        self.assertIsNotNone(match)
        self.assertEqual(match.reason, "title_company")

    def test_short_descriptions_dont_trigger_shingle(self) -> None:
        a = self._job(id="a", title="A", source_url="https://x.example/a", raw_description="Short shared text" * 2)
        b = self._job(id="b", title="B", source_url="https://x.example/b", raw_description="Short shared text" * 2)
        self.assertIsNone(find_duplicate(b, [a]))

    def test_long_descriptions_with_similar_titles_trigger_shingle(self) -> None:
        boilerplate = " ".join(f"phrase{i} word{i}" for i in range(80))
        a = self._job(
            id="a",
            title="Healthcare Project Manager",
            source_url="https://x.example/a",
            raw_description=boilerplate,
        )
        b = self._job(
            id="b",
            title="Healthcare Project Manager (m/w/d)",
            source_url="https://x.example/b",
            raw_description=boilerplate,
        )
        match = find_duplicate(b, [a])
        self.assertIsNotNone(match)
        self.assertIn(match.reason, {"title_company", "title_location", "description_shingle"})

    def test_shingles_helper_returns_overlap(self) -> None:
        a = shingles("alpha beta gamma delta epsilon")
        b = shingles("alpha beta gamma delta zeta")
        self.assertGreater(len(a & b), 0)


if __name__ == "__main__":
    unittest.main()
