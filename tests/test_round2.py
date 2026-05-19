# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-2 tests: B2 alerts, B5 tracker depth, A4 regional templates,
B1 (DOCX) CV upload."""

from __future__ import annotations

import base64
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.cv_extract import CvExtractError, extract_text
from company_discovery.models import (
    INTERVIEW_STAGES,
    Company,
    DiscoveredJob,
    SavedSearch,
    now_utc,
)
from company_discovery.repository import InMemoryCompanyDiscoveryRepository
from company_discovery.saved_search_alerts import (
    alert_summary_for_search,
    matches_for_search,
    saved_search_matches_job,
    unseen_matches_for_search,
)
from company_discovery.watchlist_templates import list_templates


def _build_minimal_docx(text: str) -> bytes:
    """Build the smallest valid .docx archive that contains ``text``."""

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<placeholder/>")
        zf.writestr("word/document.xml", document_xml)
    return buf.getvalue()


class CvExtractTests(unittest.TestCase):
    def test_extract_docx_text(self) -> None:
        blob = _build_minimal_docx("Senior Backend Engineer at Acme")
        out = extract_text("cv.docx", blob)
        self.assertIn("Senior Backend Engineer", out)

    def test_extract_txt(self) -> None:
        out = extract_text("cv.txt", b"Plain CV body")
        self.assertEqual(out, "Plain CV body")

    def test_unsupported_extension_raises(self) -> None:
        with self.assertRaises(CvExtractError):
            extract_text("cv.pdf", b"%PDF-1.4...")

    def test_corrupt_docx_raises(self) -> None:
        with self.assertRaises(CvExtractError):
            extract_text("cv.docx", b"not a real zip")


class SavedSearchAlertsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryCompanyDiscoveryRepository()
        self.user_id = "alerts-user"
        self.company = Company(
            user_id=self.user_id,
            name="Acme Corp",
            website_url="https://acme.example.com",
            sector="B2B SaaS",
        )
        self.repo.save_company(self.company)

    def _add_job(
        self, title: str, location: str = "Berlin", offset: timedelta | None = None
    ) -> DiscoveredJob:
        job = DiscoveredJob(
            user_id=self.user_id,
            company_id=self.company.id,
            source_url=f"https://acme.example.com/job/{title}",
            title=title,
            location=location,
        )
        if offset is not None:
            job.discovered_at = now_utc() + offset
        return self.repo.save_discovered_job(job)

    def test_role_token_match(self) -> None:
        search = SavedSearch(
            user_id=self.user_id, name="Backend", target_roles=["backend engineer"]
        )
        good = self._add_job("Senior Backend Engineer")
        bad = self._add_job("Marketing Coordinator")
        self.assertTrue(saved_search_matches_job(search, good, self.company.sector))
        self.assertFalse(saved_search_matches_job(search, bad, self.company.sector))

    def test_location_filter(self) -> None:
        search = SavedSearch(
            user_id=self.user_id,
            name="Berlin only",
            target_roles=["engineer"],
            location="Berlin",
        )
        in_berlin = self._add_job("Backend Engineer", location="Berlin")
        in_paris = self._add_job("Backend Engineer", location="Paris")
        self.assertTrue(saved_search_matches_job(search, in_berlin))
        self.assertFalse(saved_search_matches_job(search, in_paris))

    def test_unseen_excludes_old_matches(self) -> None:
        old = self._add_job("Backend Engineer", offset=timedelta(days=-7))
        new = self._add_job("Backend Architect", offset=timedelta(seconds=5))
        search = SavedSearch(
            user_id=self.user_id,
            name="Backend",
            target_roles=["backend"],
            last_seen_at=now_utc() - timedelta(days=1),
        )
        jobs = self.repo.list_discovered_jobs(self.user_id)
        unseen = unseen_matches_for_search(search, jobs, {self.company.id: self.company})
        unseen_ids = {j.id for j in unseen}
        self.assertIn(new.id, unseen_ids)
        self.assertNotIn(old.id, unseen_ids)

    def test_alert_summary_counts(self) -> None:
        self._add_job("Backend Engineer")
        self._add_job("Frontend Engineer")
        self._add_job("Marketing Coordinator")
        search = SavedSearch(
            user_id=self.user_id,
            name="Engineering",
            target_roles=["engineer"],
        )
        summary = alert_summary_for_search(
            search,
            self.repo.list_discovered_jobs(self.user_id),
            {self.company.id: self.company},
        )
        self.assertEqual(summary["matchCount"], 2)
        self.assertEqual(summary["unseenCount"], 2)
        self.assertIsNotNone(summary["latestMatchAt"])


class RegionalTemplatesTests(unittest.TestCase):
    def test_paris_amsterdam_milan_london_zurich_present(self) -> None:
        ids = {item["id"] for item in list_templates()}
        for expected in (
            "paris_tech_fr",
            "amsterdam_tech_nl",
            "milan_tech_it",
            "london_finance_uk",
            "zurich_tech_ch",
        ):
            self.assertIn(expected, ids)

    def test_london_finance_filters_by_finance_persona(self) -> None:
        finance_ids = {item["id"] for item in list_templates("finance")}
        self.assertIn("london_finance_uk", finance_ids)
        self.assertIn("zurich_tech_ch", finance_ids)
        # Also ensure tech-only templates aren't shown to finance personas
        # unless they're cross-listed (zurich is cross-listed; paris isn't).
        self.assertNotIn("paris_tech_fr", finance_ids)


class TrackerDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round2-tracker-"))
        os.environ["HELPMEFINDTHEJOB_DATA_DIR"] = str(cls.tmpdir)
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app

        cls.state = app.STATE

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _seed_imported_job(self, user_id: str = "tracker-user"):
        company = self.state.service.create_company(
            user_id=user_id,
            name="Acme",
            website_url="https://acme.example.com",
        )
        from company_discovery.models import DiscoveredJob, ImportedJob

        discovered = DiscoveredJob(
            user_id=user_id,
            company_id=company.id,
            source_url="https://acme.example.com/job/1",
            title="Engineer",
        )
        self.state.repository.save_discovered_job(discovered)
        imported = ImportedJob(
            user_id=user_id,
            company_id=company.id,
            discovered_job_id=discovered.id,
            source_url="https://acme.example.com/job/1",
            title="Engineer",
            company_name="Acme",
        )
        self.state.repository.save_imported_job(imported)
        return user_id, imported.id

    def test_status_change_appends_history(self) -> None:
        user_id, job_id = self._seed_imported_job()
        # First call seeds the history with "applied"; we don't bind
        # the return because the assertion below targets the SECOND
        # call's outcome + the cumulative history shape.
        self.state.update_application_state(
            user_id,
            job_id,
            {"applicationStatus": "applied"},
        )
        second = self.state.update_application_state(
            user_id,
            job_id,
            {"applicationStatus": "interview", "historyNote": "phone screen Thurs"},
        )
        self.assertEqual(len(second.application_history), 2)
        self.assertEqual(second.application_history[-1]["status"], "interview")
        self.assertEqual(second.application_history[-1]["note"], "phone screen Thurs")

    def test_invalid_interview_stage_rejected(self) -> None:
        user_id, job_id = self._seed_imported_job(user_id="tracker-stage-user")
        with self.assertRaises(ValueError):
            self.state.update_application_state(
                user_id,
                job_id,
                {"interviewStage": "not-a-real-stage"},
            )

    def test_valid_interview_stage_persists(self) -> None:
        user_id, job_id = self._seed_imported_job(user_id="tracker-valid-stage")
        for stage in INTERVIEW_STAGES:
            updated = self.state.update_application_state(
                user_id,
                job_id,
                {"interviewStage": stage},
            )
            self.assertEqual(updated.interview_stage, stage)

    def test_reminder_at_round_trip(self) -> None:
        user_id, job_id = self._seed_imported_job(user_id="tracker-reminder")
        updated = self.state.update_application_state(
            user_id,
            job_id,
            {"reminderAt": "2026-06-01T09:30:00"},
        )
        self.assertIsNotNone(updated.reminder_at)


if __name__ == "__main__":
    unittest.main()
