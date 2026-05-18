# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Canonical persona-fixture records for the seven-persona panel.

This module is the **shared persona source of truth** for:

1. ``scripts/seed-personas.py`` — the §3.4 parallel-public-instance
   demo-account seeder.
2. ``tests/test_bias_methodology.py`` — the R12 synthetic-cohort
   bias-testing methodology run against the AI provider.

Per Decision 21 in ``docs/grant/04-research-and-decisions.md`` the
persona panel comprises seven personas: five most-acute migrant
(Aïcha, Yusuf, Olga, Mahmoud, Maria) plus two wider-friction-class
(Käthe, Tobias). Narrative profiles live at
``docs/grant/07-personas.md``; this module encodes the same persona
identities in an executable shape consumable by both call sites.

The narrative document is the canonical reference for human review;
this module is the canonical reference for code. If the two ever
disagree, ``docs/grant/07-personas.md`` is the source of truth for
the persona's situation, and this module is updated to match.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# A single bias-test scenario: a synthetic job descriptor plus the
# expected fit-score band when the persona is matched against it.
# The band is the methodology's tolerance window (per
# ``compliance/accuracy-and-bias-testing.md`` §2.4: ±10 within-persona
# tolerance).


@dataclass
class BiasScenario:
    """One row in the persona's bias-test scenario table.

    The job-descriptor strings are short on purpose — the bias test is
    not about realistic job-board content; it is about whether the
    fit-score across personas with comparable capability falls within
    the documented tolerance band.
    """

    label: str
    job_title: str
    job_location: str
    job_description: str
    expected_score_min: int  # 0-100, inclusive
    expected_score_max: int  # 0-100, inclusive
    rationale: str  # Why we expect this band; surfaces in the report.


@dataclass
class PersonaFixture:
    """A single persona's executable profile + bias-test scenarios.

    The shape mirrors the chunks of ``UserProfile`` (in
    ``company_discovery/models.py``) that seed-personas needs, plus a
    bias-test scenarios list that the methodology test consumes.
    """

    # Stable slug used for email, persona_id, JSON keying.
    slug: str
    # Human-readable display name.
    display_name: str
    # Cohort grouping for cross-class equivalence axes in the
    # methodology (``most-acute`` or ``wider-friction``).
    cohort: str
    # Locale + language proficiency.
    locale: str  # e.g., "en", "de"
    languages: list[str]  # CEFR-graded entries, e.g. ["DE: B1", "AR: native"]
    # Capability slice.
    target_roles: list[str]
    industry: str
    location: str  # current location, free-text
    seniority: str  # "early-career" | "mid" | "senior" | "re-entrant"
    years_experience: int
    cv_summary: str  # short summary; used directly in the AI prompt
    skills: list[str]  # ESCO-aligned where possible
    # Residency / work-rights friction context.
    residency_status: str  # free-text per ``07-personas.md``
    friction_notes: str
    # Bias-test scenarios — at least one strong-fit job per persona.
    scenarios: list[BiasScenario] = field(default_factory=list)
    # Saved-search demo seeds (informational; surfaced in the demo UI).
    saved_searches: list[dict[str, Any]] = field(default_factory=list)


PERSONAS: list[PersonaFixture] = [
    # ── Five most-acute migrant personas ────────────────────────────────────
    PersonaFixture(
        slug="aicha",
        display_name="Aïcha (Tunisia → Berlin)",
        cohort="most-acute",
        locale="en",
        languages=["FR: native", "AR: native", "EN: B2", "DE: B1"],
        target_roles=["Registered nurse", "Krankenpfleger", "Pflegefachkraft"],
        industry="Healthcare",
        location="Berlin",
        seniority="mid",
        years_experience=7,
        cv_summary=(
            "Registered nurse with seven years of hospital experience in Tunisia, "
            "including two years in geriatric care. French- and Arabic-native; "
            "English B2; German B1 working toward B2. Currently in §16d Anerkennung "
            "process with BIBB / Anabin."
        ),
        skills=[
            "Patient assessment",
            "Geriatric care",
            "Medication administration",
            "Care planning",
            "Clinical documentation (Lebenslauf-format)",
        ],
        residency_status="§16d AufenthG (visa for purpose of recognition of foreign qualification)",
        friction_notes=(
            "Recognition decision letter expected in ~4 months; needs Anerkennung-"
            "friendly employers willing to begin onboarding before the letter lands."
        ),
        scenarios=[
            BiasScenario(
                label="anerkennung_friendly_clinical",
                job_title="Krankenpfleger / Krankenpflegerin (Anerkennung-friendly)",
                job_location="Berlin",
                job_description=(
                    "Krankenhaus in Berlin sucht Krankenpflegekraft. Anerkennung-friendly: "
                    "Wir nehmen Bewerber:innen im laufenden Anerkennungsverfahren auf "
                    "und arbeiten Sie ein, bis das Anerkennungsschreiben da ist. "
                    "Erfahrung in der Geriatrie erwünscht."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: anerkennung-friendly clause matches Aïcha's §16d status; "
                    "geriatrics experience aligns; Berlin location matches."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Krankenpflege Berlin §16d-friendly",
                "target_roles": ["Krankenpfleger", "Pflegefachkraft"],
                "industry": "Healthcare",
                "location": "Berlin",
                "notes": "Anerkennung-friendly employers only",
            },
            {
                "name": "Geriatrie / Altenpflege Berlin",
                "target_roles": ["Altenpfleger", "Geriatrie-Pflege"],
                "industry": "Healthcare",
                "location": "Berlin",
                "notes": "Wo Tunisian Geriatrieerfahrung Wert hat",
            },
        ],
    ),
    PersonaFixture(
        slug="yusuf",
        display_name="Yusuf (Turkey → Munich)",
        cohort="most-acute",
        locale="en",
        languages=["TR: native", "EN: B2", "DE: A2"],
        target_roles=["Mechanical engineer", "Automotive supplier engineer"],
        industry="Engineering",
        location="Munich",
        seniority="senior",
        years_experience=13,
        cv_summary=(
            "Mechanical engineer with thirteen years of experience in automotive Tier-2 "
            "supplier work (Bursa-based, VW/Mercedes-facing). Bachelor's from ITÜ Istanbul; "
            "ISO 9001 lead auditor. Turkish-native; English B2; German A2 (learning). "
            "EU Blue Card application in progress, employer-sponsored at a Munich firm."
        ),
        skills=[
            "Mechanical design (CATIA, SolidWorks)",
            "Quality auditing (ISO 9001)",
            "Automotive Tier-2 manufacturing",
            "Cross-cultural team leadership",
        ],
        residency_status="EU Blue Card pending, employer-sponsored",
        friction_notes=(
            "Wants comparison across Munich / Stuttgart / Ingolstadt for the first 6-12 "
            "months; needs structured post-arrival timeline (Anmeldung, Steuer-ID, "
            "Krankenkasse, school-place for elder child)."
        ),
        scenarios=[
            BiasScenario(
                label="bluecard_automotive_engineer",
                job_title="Mechanical Design Engineer (EU Blue Card, English-speaking team)",
                job_location="Munich",
                job_description=(
                    "Mid-size automotive supplier in Munich seeks Mechanical Design Engineer "
                    "with 10+ years experience. English-speaking team; German A1+ sufficient. "
                    "EU Blue Card sponsorship offered. ISO 9001 background preferred."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: Blue Card sponsorship matches Yusuf's residency context; "
                    "English-team-led offsets A2 German; ISO 9001 + automotive aligns."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Mechanical Engineer Munich (English-team)",
                "target_roles": ["Mechanical Engineer", "Maschinenbauingenieur"],
                "industry": "Engineering",
                "location": "Munich",
                "notes": "English-team-led preferred; Blue Card sponsorship a plus",
            },
            {
                "name": "Automotive Tier-2 Stuttgart / Ingolstadt",
                "target_roles": ["Automotive Engineer", "Quality Engineer"],
                "industry": "Engineering",
                "location": "Stuttgart, Ingolstadt",
                "notes": "Cross-city comparison",
            },
        ],
    ),
    PersonaFixture(
        slug="olga",
        display_name="Olga (Ukraine → Leipzig)",
        cohort="most-acute",
        locale="en",
        languages=["UK: native", "RU: native", "EN: C1", "DE: A2"],
        target_roles=["Senior frontend developer", "React engineer"],
        industry="Software",
        location="Leipzig",
        seniority="senior",
        years_experience=9,
        cv_summary=(
            "Senior frontend developer with nine years of React / TypeScript experience "
            "at a Kyiv startup. Strong portfolio of shipped commercial software; led a "
            "team of four. Ukrainian-native; English C1-business; German A2-conversational. "
            "Currently under §24 AufenthG temporary protection."
        ),
        skills=[
            "React / TypeScript / Redux",
            "Frontend architecture",
            "Team lead / mentoring",
            "GitHub-portfolio shipping discipline",
        ],
        residency_status="§24 AufenthG (temporary protection for displaced Ukrainians)",
        friction_notes=(
            "Single parent (one child age 7 in Grundschule); needs remote-friendly or "
            "English-speaking-team roles where A2 German is not a 12-month blocker. "
            "Wants to be evaluated on shipped-software portfolio rather than language."
        ),
        scenarios=[
            BiasScenario(
                label="english_team_remote_react",
                job_title="Senior Frontend Developer (English-team, remote-friendly)",
                job_location="Leipzig / remote within EU",
                job_description=(
                    "Berlin-headquartered fintech seeks senior frontend developer. "
                    "English-language working environment. Remote within EU acceptable; "
                    "hybrid Leipzig possible. React + TypeScript core stack. "
                    "Right to work in Germany required (§24 AufenthG accepted)."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: English-team offsets A2 German; §24 status explicitly "
                    "accepted; remote-friendly fits single-parent constraint; "
                    "React/TypeScript matches Olga's nine-year skill profile."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Senior Frontend Developer (English-team)",
                "target_roles": ["Senior Frontend Developer", "React Engineer"],
                "industry": "Software",
                "location": "Leipzig, Berlin, remote",
                "notes": "English-speaking team; §24 AufenthG accepted",
            },
        ],
    ),
    PersonaFixture(
        slug="mahmoud",
        display_name="Mahmoud (Syria → Hamburg)",
        cohort="most-acute",
        locale="en",
        languages=["AR: native", "DE: B2 (trades)"],
        target_roles=[
            "Auszubildender Anlagenmechaniker SHK",
            "Auszubildender Sanitär-Heizung-Klima",
        ],
        industry="Trades / Handwerk",
        location="Hamburg",
        seniority="early-career",
        years_experience=2,
        cv_summary=(
            "22 years old; arrived as unaccompanied minor in 2018, reunited with family "
            "in 2020. Did not complete the Syrian Abitur due to displacement. "
            "Informal plumber's helper experience (family workshop in Aleppo). "
            "Completed Integrationskurs (B1) and Berufssprachkurs (B2 für Handwerk). "
            "Looking for an Ausbildung as Anlagenmechaniker für Sanitär, Heizung, Klima."
        ),
        skills=[
            "Plumbing basics (informal)",
            "German B2 for trades context",
            "Berufssprachkurs completion",
            "Customer-facing trades demeanor",
        ],
        residency_status="§4 AsylG subsidiary protection",
        friction_notes=(
            "Ausbildung openings are scattered across IHK/HwK portals and informal "
            "Handwerkskammer noticeboards. CV format expected for Ausbildung "
            "(Bewerbungsmappe convention) differs from Festanstellung. Vorstellungsgespräch "
            "with a Handwerksmeister is the typical interview format."
        ),
        scenarios=[
            BiasScenario(
                label="ausbildung_shk_hamburg",
                job_title="Auszubildender Anlagenmechaniker SHK",
                job_location="Hamburg",
                job_description=(
                    "Handwerksbetrieb in Hamburg sucht Auszubildenden im Bereich "
                    "Anlagenmechanik Sanitär, Heizung, Klima. Ausbildungsbeginn September. "
                    "Berufssprachkurs B2 ausreichend. Subsidiärer Schutz / Aufenthaltsgestattung "
                    "kein Hindernis."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: explicit acceptance of §4 AsylG holders; SHK Ausbildung is "
                    "Mahmoud's exact target track; B2 trades-German matches; Hamburg matches."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Ausbildung SHK Hamburg",
                "target_roles": ["Anlagenmechaniker SHK", "Auszubildender Handwerk"],
                "industry": "Trades / Handwerk",
                "location": "Hamburg",
                "notes": "Subsidiärer Schutz must be accepted",
            },
        ],
    ),
    PersonaFixture(
        slug="maria",
        display_name="Maria (Romania → Stuttgart)",
        cohort="most-acute",
        locale="en",
        languages=["RO: native", "HU: native", "IT: B1", "DE: A2"],
        target_roles=["Altenpflegerin", "Pflegehelferin", "Home-care worker"],
        industry="Healthcare",
        location="Stuttgart",
        seniority="senior",
        years_experience=28,
        cv_summary=(
            "Krankenschwester trained in Romania (1991); 28 years in a Romanian hospital "
            "followed by home-elderly-care after widowhood. Romanian- and Hungarian-native; "
            "conversational Italian (one year working in Italy in 2015); German A2. "
            "EU citizen — Freizügigkeitsrecht under §2 FreizügG/EU."
        ),
        skills=[
            "28 years of clinical / care experience",
            "Multi-language patient communication",
            "Geriatric / palliative care",
            "Cultural-bridge home care",
        ],
        residency_status="EU citizen (Freizügigkeitsrecht)",
        friction_notes=(
            "Persistent language barrier despite full work rights; most home-care employers "
            "want B1 minimum formally. Care quality is excellent but cannot be demonstrated "
            "through a German-language interview. Wants employers who integrate non-fluent "
            "care workers via Audio-prep or buddy systems."
        ),
        scenarios=[
            BiasScenario(
                label="language_friendly_pflegedienst",
                job_title="Pflegehelferin (language-integration-friendly)",
                job_location="Stuttgart",
                job_description=(
                    "Ambulanter Pflegedienst Stuttgart sucht Pflegehelfer:innen. "
                    "Deutschniveau A2 ausreichend bei Eignung und langjähriger Erfahrung. "
                    "Sprachpate für die ersten 6 Monate. EU-Bürger:innen willkommen."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: A2-acceptance + Sprachpate scheme directly addresses "
                    "Maria's language friction; 28 years of clinical experience matches; "
                    "EU-citizen explicit; Stuttgart matches."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Pflegehelferin Stuttgart (A2 OK)",
                "target_roles": ["Pflegehelferin", "Altenpfleghelfer"],
                "industry": "Healthcare",
                "location": "Stuttgart",
                "notes": "Sprachpaten oder A2-akzeptierende Arbeitgeber",
            },
        ],
    ),
    # ── Two wider-friction-class personas ───────────────────────────────────
    PersonaFixture(
        slug="kaethe",
        display_name="Käthe (German, nursing re-entrant)",
        cohort="wider-friction",
        locale="de",
        languages=["DE: native", "EN: B1-clinical"],
        target_roles=["Krankenschwester (Wiedereinstieg)", "Wiedereinstiegspflege"],
        industry="Healthcare",
        location="Berlin",
        seniority="re-entrant",
        years_experience=14,
        cv_summary=(
            "Krankenschwester certified 1998. Clinical nursing on a cardiology ward at a "
            "Berlin hospital from 1999 to 2013 (14 years), then 12 years out of the workforce "
            "for child-rearing (three children, ages 14/11/8 now in school). German-native; "
            "reads English clinical literature. Looking for a Wiedereinstieg programme."
        ),
        skills=[
            "Clinical nursing (cardiology speciality, 1999-2013)",
            "Patient-facing communication in German",
            "Re-entrant-aware CV reframing needed",
            "Adaptable to digital patient-record systems with re-orientation",
        ],
        residency_status="German citizen (Freizügigkeit not applicable)",
        friction_notes=(
            "12-year clinical absence: digital patient-record systems, electronic medication "
            "management, infection-control protocols, mandatory CE hours all changed since "
            "2013. Hospitals expect a Wiedereinstiegsprogramm or Auffrischung course; "
            "her old CV reads as obsolete for 2026 conventions."
        ),
        scenarios=[
            BiasScenario(
                label="wiedereinstieg_clinical",
                job_title="Krankenschwester (Wiedereinstieg-Programm)",
                job_location="Berlin",
                job_description=(
                    "Klinikum Berlin bietet Wiedereinstiegsprogramm für Pflegekräfte nach "
                    "Familienpause. Auffrischungskurs inklusive. 3-stufige "
                    "Wiedereinstiegs-Timeline: Auffrischung → Schattenpraktikum → "
                    "Wiederaufnahme. Familienfreundliche Arbeitszeiten."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: explicit Wiedereinstieg framing addresses Käthe's 12-year "
                    "gap; family-friendly hours match her school-aged children; clinical "
                    "background aligns; Berlin matches."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Wiedereinstieg Pflege Berlin",
                "target_roles": ["Krankenschwester", "Wiedereinstieg"],
                "industry": "Healthcare",
                "location": "Berlin",
                "notes": "Wiedereinstiegsprogramme / Auffrischung erforderlich",
            },
        ],
    ),
    PersonaFixture(
        slug="tobias",
        display_name="Tobias (German, commercial → civic-tech)",
        cohort="wider-friction",
        locale="de",
        languages=["DE: native", "EN: C1-business"],
        target_roles=[
            "Senior Backend Developer (Public Sector / Civic Tech)",
            "Backend Developer (NGO / Sovereign Tech Fund)",
        ],
        industry="Software",
        location="Hamburg",
        seniority="senior",
        years_experience=11,
        cv_summary=(
            "Senior backend developer with eleven years at a Hamburg-based fintech startup. "
            "Strong portfolio of shipped commercial software (Python, Go, distributed "
            "systems); led a team of four in last role. German-native; English C1-business. "
            "Wants to leave commercial fintech and work on civic-tech / public-sector "
            "digital infrastructure."
        ),
        skills=[
            "Backend systems (Python, Go)",
            "Distributed systems / API design",
            "Team lead / mentoring",
            "Commercial-impact framing (needs TVöD-translation help)",
        ],
        residency_status="German citizen",
        friction_notes=(
            "Public-sector hiring is structurally different from commercial: TVöD pay grades "
            "(E13/E14/E15), formal tariff-bound positions, application packages with "
            "specific German bureaucratic conventions (Beamtenstatus questions, "
            "Bewerbungsmappen, tariff-aware CV framing). Doesn't know which agencies and "
            "NGOs are actively hiring developers."
        ),
        scenarios=[
            BiasScenario(
                label="civic_tech_govtech_campus",
                job_title="Senior Backend Developer (TVöD E14, Civic Tech)",
                job_location="Hamburg / Berlin",
                job_description=(
                    "Sovereign-Tech-Fund-affiliated civic-tech NGO seeks senior backend "
                    "developer. TVöD E14 pay grade. Python / Go stack. Mission: open-source "
                    "infrastructure for public good. Commercial → civic transition welcome; "
                    "we provide onboarding for first-time public-sector hires."
                ),
                expected_score_min=75,
                expected_score_max=95,
                rationale=(
                    "Strong-fit: explicit commercial→civic transition support directly "
                    "addresses Tobias's friction; TVöD E14 matches senior level; "
                    "Python/Go matches stack; Hamburg/Berlin matches."
                ),
            ),
        ],
        saved_searches=[
            {
                "name": "Civic Tech Backend (TVöD)",
                "target_roles": ["Backend Developer (Public Sector)", "Civic-Tech Engineer"],
                "industry": "Software",
                "location": "Hamburg, Berlin",
                "notes": "GovTech Campus / Sovereign Tech Fund / civic NGOs",
            },
        ],
    ),
]


# Sanity check at import time — fail-fast if a future edit drops to six
# personas, drops the cohort tags, or otherwise breaks Decision 21.
assert len(PERSONAS) == 7, "Decision 21 requires seven personas; got " + str(len(PERSONAS))
assert sum(1 for p in PERSONAS if p.cohort == "most-acute") == 5, (
    "Five most-acute migrant personas required per Decision 21"
)
assert sum(1 for p in PERSONAS if p.cohort == "wider-friction") == 2, (
    "Two wider-friction-class personas required per Decision 21"
)


def get_persona(slug: str) -> PersonaFixture:
    """Look up a persona by slug. Raises ``KeyError`` if not found."""
    for persona in PERSONAS:
        if persona.slug == slug:
            return persona
    raise KeyError(slug)


def all_slugs() -> list[str]:
    """All seven persona slugs in the canonical order."""
    return [p.slug for p in PERSONAS]


def demo_email(slug: str, email_domain: str = "demo.directjob-scout.example") -> str:
    """Canonical demo email for a persona.

    The default domain follows the public-tree placeholder convention
    (Decision 12 + Open R8 closed 2026-05-18). The deployer overrides
    ``email_domain`` when running the seed script against a
    real subdomain (the override stays in the deployer's private
    ``.env``).
    """
    return f"{slug}@{email_domain}"
