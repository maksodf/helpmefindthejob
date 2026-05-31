# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week-plan Week 1 Day 1 — civic-services mesh contract tests.

Three per-agent unit suites + one end-to-end mesh integration
test that boots all 3 agents in-process and runs Aïcha's walk.

These tests prove:
- The protocol envelope round-trips correctly
- Each agent's 3 demo cohorts produce realistic decisions
- The end-to-end mesh walk doesn't crash and every step
  produces a structured payload
- Each agent's audit log captures every event
"""

from __future__ import annotations

import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from mesh.anerkennung_agent import (
    _make_verification_decision,
)
from mesh.anerkennung_agent import (
    make_handler as make_anerkennung_handler,
)
from mesh.common import (
    REFERRAL_SCHEMA_VERSION,
    AgentAuditLog,
    new_referral_id,
    now_iso,
    serve_until_stopped,
    validate_referral,
)
from mesh.housing_agent import (
    _make_intake_decision,
)
from mesh.housing_agent import (
    _match_cohort as _housing_match_cohort,
)
from mesh.housing_agent import (
    make_handler as make_housing_handler,
)
from mesh.social_services_agent import (
    _make_recommendation,
)
from mesh.social_services_agent import (
    make_handler as make_social_handler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _aicha_referral(target: str, reason: str, ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "referralId": new_referral_id(),
        "schemaVersion": REFERRAL_SCHEMA_VERSION,
        "issuedAt": now_iso(),
        "sourceAgent": "helpmefindthejob",
        "targetAgent": target,
        "userId": "test-aicha",
        "intent": "proposed",
        "priority": "routine",
        "reasonCode": reason,
        "supportingInfo": ctx,
        "userConsentRequired": True,
        "userConsentReceivedAt": now_iso(),
    }


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 4xx responses carry structured JSON we want to inspect
        return json.loads(exc.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Referral envelope contract
# ---------------------------------------------------------------------------


class ReferralEnvelope(unittest.TestCase):
    def test_valid_referral_passes(self):
        ref = _aicha_referral("housing-agent", "needs_housing", {"city": "berlin"})
        ok, err = validate_referral(ref)
        self.assertTrue(ok, err)

    def test_missing_field_rejected(self):
        ref = _aicha_referral("housing-agent", "needs_housing", {})
        del ref["userId"]
        ok, err = validate_referral(ref)
        self.assertFalse(ok)
        self.assertIn("userId", err)

    def test_schema_version_mismatch_rejected(self):
        ref = _aicha_referral("housing-agent", "needs_housing", {})
        ref["schemaVersion"] = "9.9.9-fake"
        ok, err = validate_referral(ref)
        self.assertFalse(ok)
        self.assertEqual(err, "schema_version_mismatch")

    def test_consent_must_be_required(self):
        ref = _aicha_referral("housing-agent", "needs_housing", {})
        ref["userConsentRequired"] = False
        ok, err = validate_referral(ref)
        self.assertFalse(ok)
        self.assertEqual(err, "consent_must_be_required")


# ---------------------------------------------------------------------------
# Housing-agent cohort matching
# ---------------------------------------------------------------------------


class HousingCohorts(unittest.TestCase):
    def test_berlin_16d_matches(self):
        ref = _aicha_referral(
            "housing-agent",
            "needs_housing_berlin",
            {"city": "berlin", "residency_status": "§16d"},
        )
        cohort = _housing_match_cohort(ref)
        self.assertEqual(cohort["cohort_id"], "berlin_aufenthaltsgesetz_16d")

    def test_munich_blue_card_matches(self):
        ref = _aicha_referral(
            "housing-agent",
            "needs_housing_munich",
            {"city": "munich", "residency_status": "Blue Card"},
        )
        cohort = _housing_match_cohort(ref)
        self.assertEqual(cohort["cohort_id"], "munich_blue_card")

    def test_leipzig_paragraph_24_matches(self):
        ref = _aicha_referral(
            "housing-agent",
            "needs_housing_leipzig",
            {"city": "leipzig", "residency_status": "§24"},
        )
        cohort = _housing_match_cohort(ref)
        self.assertEqual(cohort["cohort_id"], "leipzig_paragraph_24_ukraine")
        # Leipzig is markedly cheaper than the larger cities.
        self.assertLess(cohort["monthly_rent_band_eur"][1], 1000)

    def test_unmatched_falls_through_to_default(self):
        ref = _aicha_referral(
            "housing-agent",
            "needs_housing_other",
            {"city": "rome", "residency_status": "EU"},
        )
        cohort = _housing_match_cohort(ref)
        self.assertEqual(cohort["cohort_id"], "default_unmatched")

    def test_decision_shape_includes_required_fields(self):
        ref = _aicha_referral(
            "housing-agent", "needs_housing", {"city": "berlin", "residency_status": "§16d"}
        )
        decision = _make_intake_decision(ref)
        for required in (
            "intakeId",
            "sourceReferralId",
            "cohort",
            "decision",
            "estimatedWaitWeeksMin",
            "estimatedWaitWeeksMax",
            "monthlyRentBandEur",
            "nextSteps",
            "userConsentReceivedAt",
        ):
            self.assertIn(required, decision)
        self.assertEqual(decision["decision"], "accepted")


# ---------------------------------------------------------------------------
# Anerkennung-agent pathway matching
# ---------------------------------------------------------------------------


class AnerkennungPathways(unittest.TestCase):
    def test_tunisia_nursing_pflege_pathway(self):
        decision = _make_verification_decision(
            {
                "userId": "u",
                "qualificationField": "Nursing (Krankenpflege)",
                "countryOfOrigin": "Tunisia",
            }
        )
        self.assertEqual(decision["pathway"], "pflege_drittstaaten")
        self.assertEqual(decision["decision"], "partial_recognition")
        self.assertIn("Anpassungslehrgang", " ".join(decision["missingRequirements"]))

    def test_turkey_engineering_bluecard_pathway(self):
        # Yusuf came DIRECTLY on an EU Blue Card and was never an asylum
        # seeker, so recognition runs the BQFG Blue-Card engineering route,
        # not §4 AsylG.
        decision = _make_verification_decision(
            {
                "userId": "u",
                "qualificationField": "Mechanical Engineering",
                "countryOfOrigin": "Turkey",
                "residencyStatus": "EU Blue Card",
            }
        )
        self.assertEqual(decision["pathway"], "engineering_bluecard_bqfg")
        self.assertEqual(decision["decision"], "comparability_statement_blue_card")
        self.assertIn("BQFG", decision["legalBasis"])
        self.assertNotIn("AsylG", decision["legalBasis"])

    def test_ukraine_software_unregulated_no_recognition_pathway(self):
        # IT / software is an UNREGULATED profession in Germany: no formal
        # recognition (Anerkennung) is required and the candidate may start
        # work immediately. This is correct German law.
        decision = _make_verification_decision(
            {
                "userId": "u",
                "qualificationField": "Software engineering (senior frontend / React)",
                "countryOfOrigin": "Ukraine",
                "residencyStatus": "§24 Ukraine",
            }
        )
        self.assertEqual(decision["pathway"], "it_unregulated_no_recognition")
        self.assertEqual(decision["decision"], "no_recognition_required_unregulated_profession")
        self.assertIn("No Anerkennung required", decision["legalBasis"])
        self.assertIn("unregulated", decision["issuingAuthority"].lower())
        self.assertEqual(decision["estimatedCompletionMonths"], 0)
        self.assertEqual(decision["missingRequirements"], [])

    def test_pii_fields_only_appear_as_opaque_hashes(self):
        """Quality bar: the decision payload must NOT carry plaintext
        of qualification + country_of_origin (those are minor PII).
        Only short hash fingerprints survive into the response."""
        decision = _make_verification_decision(
            {
                "userId": "u",
                "qualificationField": "Nursing",
                "countryOfOrigin": "Tunisia",
            }
        )
        flat = json.dumps(decision)
        self.assertNotIn("Tunisia", flat)
        self.assertNotIn("Nursing", flat)
        self.assertEqual(len(decision["qualificationFieldOpaque"]), 16)


# ---------------------------------------------------------------------------
# Social-services-agent recommendations
# ---------------------------------------------------------------------------


class SocialServicesRecommendations(unittest.TestCase):
    def test_aicha_16d_recommendation(self):
        rec = _make_recommendation(
            {
                "userId": "u",
                "frictionClass": "aicha",
                "residencyStatus": "§16d",
                "hasChildren": False,
            }
        )
        self.assertEqual(rec["cohort"], "aicha_paragraph_16d_anerkennung")
        self.assertIn("Aufstockung", rec["primaryBenefit"])

    def test_olga_24_family_recommendation(self):
        rec = _make_recommendation(
            {
                "userId": "u",
                "frictionClass": "olga",
                "residencyStatus": "§24 Ukraine",
                "hasChildren": True,
            }
        )
        self.assertEqual(rec["cohort"], "olga_paragraph_24_family")
        self.assertIn("Kinderzuschlag", rec["primaryBenefit"])

    def test_tobias_quereinstieg_recommendation(self):
        rec = _make_recommendation(
            {
                "userId": "u",
                "frictionClass": "tobias",
                "careerIntent": "career change bootcamp",
            }
        )
        self.assertEqual(rec["cohort"], "tobias_quereinstieg_bildungsgutschein")
        self.assertIn("Bildungsgutschein", rec["primaryBenefit"])

    def test_consent_expiry_is_set(self):
        rec = _make_recommendation(
            {"userId": "u", "frictionClass": "aicha", "residencyStatus": "§16d"}
        )
        self.assertIn("consentExpiresAt", rec)


# ---------------------------------------------------------------------------
# End-to-end mesh integration (all 3 agents live in-process)
# ---------------------------------------------------------------------------


class EndToEndMeshWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.tmp_path = Path(cls.tmp.name)
        cls.housing_port = _free_port()
        cls.anerkennung_port = _free_port()
        cls.social_port = _free_port()
        cls.housing_audit = AgentAuditLog(cls.tmp_path / "housing.log")
        cls.anerkennung_audit = AgentAuditLog(cls.tmp_path / "anerkennung.log")
        cls.social_audit = AgentAuditLog(cls.tmp_path / "social.log")
        cls.housing_server = serve_until_stopped(
            make_housing_handler(cls.housing_audit), "127.0.0.1", cls.housing_port
        )
        cls.anerkennung_server = serve_until_stopped(
            make_anerkennung_handler(cls.anerkennung_audit),
            "127.0.0.1",
            cls.anerkennung_port,
        )
        cls.social_server = serve_until_stopped(
            make_social_handler(cls.social_audit), "127.0.0.1", cls.social_port
        )
        # Wait for all 3 to answer /v1/health
        for label, port in (
            ("housing", cls.housing_port),
            ("anerkennung", cls.anerkennung_port),
            ("social", cls.social_port),
        ):
            for _ in range(30):
                try:
                    out = _get_json(f"http://127.0.0.1:{port}/v1/health")
                    if out.get("status") == "ok":
                        break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.1)
            else:
                raise RuntimeError(f"{label} agent never became healthy")

    @classmethod
    def tearDownClass(cls):
        cls.housing_server.shutdown()
        cls.housing_server.server_close()
        cls.anerkennung_server.shutdown()
        cls.anerkennung_server.server_close()
        cls.social_server.shutdown()
        cls.social_server.server_close()
        cls.tmp.cleanup()

    def test_aicha_walks_full_mesh(self):
        # Step 1 — verify credential
        decision = _post_json(
            f"http://127.0.0.1:{self.anerkennung_port}/v1/verify-credential",
            {
                "userId": "test-aicha",
                "qualificationField": "Nursing (Krankenpflege)",
                "countryOfOrigin": "Tunisia",
                "residencyStatus": "§16d",
            },
        )
        self.assertEqual(decision["status"], "ok")
        self.assertEqual(decision["decision"]["pathway"], "pflege_drittstaaten")
        decision_id = decision["decision"]["decisionId"]

        # Step 2 — issue VC
        vc_resp = _post_json(
            f"http://127.0.0.1:{self.anerkennung_port}/v1/issue-vc",
            {"decisionId": decision_id, "userId": "test-aicha"},
        )
        self.assertEqual(vc_resp["status"], "ok")
        self.assertIn("VerifiableCredential", vc_resp["verifiableCredential"]["type"])

        # Step 3 — housing referral
        housing_resp = _post_json(
            f"http://127.0.0.1:{self.housing_port}/v1/intake",
            {
                "referral": _aicha_referral(
                    "housing-agent",
                    "needs_housing_berlin_anerkennung_track",
                    {"city": "berlin", "residency_status": "§16d", "single_occupant": True},
                )
            },
        )
        self.assertEqual(housing_resp["status"], "ok")
        self.assertEqual(housing_resp["intake"]["cohort"], "berlin_aufenthaltsgesetz_16d")

        # Step 4 — social-services eligibility
        social_resp = _post_json(
            f"http://127.0.0.1:{self.social_port}/v1/eligibility-check",
            {
                "profile": {
                    "userId": "test-aicha",
                    "frictionClass": "aicha",
                    "residencyStatus": "§16d",
                    "hasChildren": False,
                }
            },
        )
        self.assertEqual(social_resp["status"], "ok")
        self.assertEqual(social_resp["recommendation"]["cohort"], "aicha_paragraph_16d_anerkennung")

        # Step 5 — every agent recorded the event in its audit log
        for label, port, expected_event in (
            ("housing", self.housing_port, "intake_accepted"),
            ("anerkennung", self.anerkennung_port, "credential_verified"),
            ("social", self.social_port, "eligibility_recommended"),
        ):
            audit = _get_json(f"http://127.0.0.1:{port}/v1/audit-trail")
            self.assertEqual(audit["status"], "ok")
            event_types = [e["event_type"] for e in audit["events"]]
            self.assertIn(
                expected_event,
                event_types,
                f"{label} agent did not record {expected_event}",
            )

    def test_yusuf_blue_card_walk(self):
        """Yusuf scenario: Turkish mechanical engineer on a direct EU Blue
        Card → BQFG engineering recognition pathway + Munich Blue Card
        housing + social-services NOT matched (above Bürgergeld
        threshold). §4 AsylG never applied to him."""
        # Anerkennung — BQFG Blue-Card engineering route
        decision = _post_json(
            f"http://127.0.0.1:{self.anerkennung_port}/v1/verify-credential",
            {
                "userId": "test-yusuf",
                "qualificationField": "Mechanical Engineering",
                "countryOfOrigin": "Turkey",
                "residencyStatus": "EU Blue Card",
            },
        )["decision"]
        self.assertEqual(decision["pathway"], "engineering_bluecard_bqfg")
        self.assertNotIn("AsylG", decision["legalBasis"])
        # Housing — Munich Blue Card cohort
        intake = _post_json(
            f"http://127.0.0.1:{self.housing_port}/v1/intake",
            {
                "referral": _aicha_referral(
                    "housing-agent",
                    "needs_housing_munich",
                    {"city": "munich", "residency_status": "Blue Card"},
                )
            },
        )["intake"]
        self.assertEqual(intake["cohort"], "munich_blue_card")
        # Social — must NOT match the §16d cohort (Yusuf is yusuf, not aicha)
        rec = _post_json(
            f"http://127.0.0.1:{self.social_port}/v1/eligibility-check",
            {
                "profile": {
                    "userId": "test-yusuf",
                    "frictionClass": "yusuf",
                    "residencyStatus": "Blue Card",
                    "hasChildren": False,
                }
            },
        )["recommendation"]
        # Falls through to default — that's the correct civic-tech outcome
        self.assertEqual(rec["cohort"], "default_unmatched")

    def test_olga_family_walk(self):
        """Olga scenario: §24 Ukraine software developer in Leipzig →
        IT-unregulated (no formal recognition) + Leipzig family housing
        + Bürgergeld + Kinderzuschlag."""
        # Anerkennung — IT/software is unregulated, no Anerkennung required
        decision = _post_json(
            f"http://127.0.0.1:{self.anerkennung_port}/v1/verify-credential",
            {
                "userId": "test-olga",
                "qualificationField": "Software engineering (senior frontend / React)",
                "countryOfOrigin": "Ukraine",
                "residencyStatus": "§24 Ukraine",
            },
        )["decision"]
        self.assertEqual(decision["pathway"], "it_unregulated_no_recognition")
        self.assertIn("No Anerkennung required", decision["legalBasis"])
        # Housing
        intake = _post_json(
            f"http://127.0.0.1:{self.housing_port}/v1/intake",
            {
                "referral": _aicha_referral(
                    "housing-agent",
                    "needs_housing_leipzig_family",
                    {"city": "leipzig", "residency_status": "§24", "family_size": 3},
                )
            },
        )["intake"]
        self.assertEqual(intake["cohort"], "leipzig_paragraph_24_ukraine")
        # Social with family
        rec = _post_json(
            f"http://127.0.0.1:{self.social_port}/v1/eligibility-check",
            {
                "profile": {
                    "userId": "test-olga",
                    "frictionClass": "olga",
                    "residencyStatus": "§24 Ukraine",
                    "hasChildren": True,
                }
            },
        )["recommendation"]
        self.assertEqual(rec["cohort"], "olga_paragraph_24_family")
        # Family-bracket recommendation includes Kinderzuschlag
        self.assertIn("Kinderzuschlag", rec["primaryBenefit"])

    def test_invalid_referral_is_rejected_by_housing_agent(self):
        bad_ref = _aicha_referral("housing-agent", "x", {})
        del bad_ref["userId"]
        resp = _post_json(f"http://127.0.0.1:{self.housing_port}/v1/intake", {"referral": bad_ref})
        self.assertEqual(resp["status"], "rejected")
        self.assertEqual(resp["code"], "invalid_referral")


# ---------------------------------------------------------------------------
# Persona-spine consistency: the mesh demo walks must match the canonical
# persona spine in company_discovery/persona_fixtures.py. This guard would
# have caught the "Spine-B" scramble (Yusuf modelled as a Syrian §4-AsylG
# electrical engineer; Olga as a Ukrainian MD in Hamburg) at commit time.
# ---------------------------------------------------------------------------


class DemoWalkPersonaSpine(unittest.TestCase):
    def _fixtures_by_first_name(self):
        from company_discovery.persona_fixtures import PERSONAS

        # Fixture display_name is e.g. "Yusuf (Turkey → Munich)"; key on the
        # leading first name so we can match the walk PROFILE name.
        return {p.display_name.split(" ")[0]: p for p in PERSONAS}

    def test_yusuf_walk_matches_canonical_spine(self):
        from mesh import demo_yusuf_walk

        profile = demo_yusuf_walk.YUSUF_PROFILE
        fixture = self._fixtures_by_first_name()["Yusuf"]
        self.assertEqual(profile["countryOfOrigin"], "Turkey")
        self.assertEqual(profile["city"], fixture.location)  # Munich
        self.assertEqual(fixture.industry, "Engineering")
        self.assertIn("Mechanical", profile["qualificationField"])
        self.assertEqual(profile["residencyStatus"], "EU Blue Card")
        # The old scramble must never return.
        blob = json.dumps(profile).lower()
        for stale in ("syria", "syrian", "electrical", "asylg", "subsidiary"):
            self.assertNotIn(stale, blob)

    def test_olga_walk_matches_canonical_spine(self):
        from mesh import demo_olga_walk

        profile = demo_olga_walk.OLGA_PROFILE
        fixture = self._fixtures_by_first_name()["Olga"]
        self.assertEqual(profile["countryOfOrigin"], "Ukraine")
        self.assertEqual(profile["city"], fixture.location)  # Leipzig
        self.assertEqual(fixture.industry, "Software")
        self.assertIn("software", profile["qualificationField"].lower())
        self.assertIn("§24", profile["residencyStatus"])
        # The old scramble must never return.
        blob = json.dumps(profile).lower()
        for stale in ("hamburg", "medicine", "physician", "approbation"):
            self.assertNotIn(stale, blob)

    def test_aicha_walk_matches_canonical_spine(self):
        from mesh import demo_aicha_walk

        profile = demo_aicha_walk.AICHA_PROFILE
        fixture = self._fixtures_by_first_name()["Aïcha"]
        self.assertEqual(profile["countryOfOrigin"], "Tunisia")
        self.assertEqual(profile["city"], fixture.location)  # Berlin
        self.assertEqual(fixture.industry, "Healthcare")
        self.assertIn("§16d", profile["residencyStatus"])


# ---------------------------------------------------------------------------
# Demo-walk smoke test: actually run each walk's main() end-to-end against
# live in-process agents. The per-agent integration tests above call the
# agents directly and therefore never execute the walk scripts' own
# payload-construction code — which is exactly where a stale PROFILE-key
# reference (e.g. PROFILE["residency"] vs PROFILE["residencyStatus"]) can
# hide and crash the operator-facing demo while every other test stays
# green. This class closes that gap: it asserts each walk's main() exits 0.
# ---------------------------------------------------------------------------


class DemoWalkSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        tmp_path = Path(cls.tmp.name)
        cls.housing_port = _free_port()
        cls.anerkennung_port = _free_port()
        cls.social_port = _free_port()
        cls.housing_server = serve_until_stopped(
            make_housing_handler(AgentAuditLog(tmp_path / "h.log")),
            "127.0.0.1",
            cls.housing_port,
        )
        cls.anerkennung_server = serve_until_stopped(
            make_anerkennung_handler(AgentAuditLog(tmp_path / "a.log")),
            "127.0.0.1",
            cls.anerkennung_port,
        )
        cls.social_server = serve_until_stopped(
            make_social_handler(AgentAuditLog(tmp_path / "s.log")),
            "127.0.0.1",
            cls.social_port,
        )
        for port in (cls.housing_port, cls.anerkennung_port, cls.social_port):
            for _ in range(30):
                try:
                    if _get_json(f"http://127.0.0.1:{port}/v1/health").get("status") == "ok":
                        break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.1)
            else:
                raise RuntimeError(f"agent on port {port} never became healthy")

    @classmethod
    def tearDownClass(cls):
        for server in (cls.housing_server, cls.anerkennung_server, cls.social_server):
            server.shutdown()
            server.server_close()
        cls.tmp.cleanup()

    def _run_walk(self, module):
        """Point a walk module at this class's in-process agents and run
        its ``main()`` with ``--skip-health``; assert a clean exit. This
        executes the walk's own payload construction, so a stale PROFILE
        key crashes the test rather than only the operator."""
        orig_urls = (module.HOUSING_URL, module.ANERKENNUNG_URL, module.SOCIAL_URL)
        orig_argv = sys.argv
        module.HOUSING_URL = f"http://127.0.0.1:{self.housing_port}"
        module.ANERKENNUNG_URL = f"http://127.0.0.1:{self.anerkennung_port}"
        module.SOCIAL_URL = f"http://127.0.0.1:{self.social_port}"
        sys.argv = [module.__name__, "--skip-health"]
        try:
            rc = module.main()
        finally:
            module.HOUSING_URL, module.ANERKENNUNG_URL, module.SOCIAL_URL = orig_urls
            sys.argv = orig_argv
        self.assertEqual(rc, 0, f"{module.__name__}.main() returned {rc}, expected 0")

    def test_aicha_walk_main_runs_clean(self):
        from mesh import demo_aicha_walk

        self._run_walk(demo_aicha_walk)

    def test_yusuf_walk_main_runs_clean(self):
        from mesh import demo_yusuf_walk

        self._run_walk(demo_yusuf_walk)

    def test_olga_walk_main_runs_clean(self):
        from mesh import demo_olga_walk

        self._run_walk(demo_olga_walk)


if __name__ == "__main__":
    unittest.main()
