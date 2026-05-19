# Copyright (c) 2026 Helpmefindthejob contributors
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
class CvTailoringScenario:
    """One row in the persona's CV-tailoring bias-test scenario table.

    The methodology at ``compliance/accuracy-and-bias-testing.md`` §4
    measures CV-tailoring quality qualitatively: does the output
    reflect actual CV facts (not hallucinated), reflect the role's
    documented requirements, and respect the persona's CV-style
    conventions. This scenario record carries the (persona, job)
    pair and the tailoring-difficulty bucket so the report can
    summarise distribution.
    """

    label: str
    job_title: str
    job_location: str
    job_description: str
    # ``light`` (close-fit, small reframing), ``moderate`` (same
    # industry, different role-shape), or ``significant`` (cross-
    # industry pivot). Captures how much tailoring the methodology
    # expects of the model.
    tailoring_difficulty: str
    # Pass-criteria: free-text human-readable expectation. The
    # methodology run records pass/fail against a set of structural
    # checks documented in tests/test_bias_methodology.py; this
    # field is for the report.
    pass_criteria: str


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
    # After the R12-broadening slice, each persona carries 10 scoring
    # scenarios (3 strong + 4 mixed + 3 weak) for methodology §2.2.
    # The R12-polish slice makes the mixed-fit set cohort-aware.
    scenarios: list[BiasScenario] = field(default_factory=list)
    # CV-tailoring scenarios — added in the R12-broadening slice for
    # methodology §4. Each persona carries 10 (4 light + 4 moderate
    # + 2 significant tailoring difficulty).
    cv_tailoring_scenarios: list[CvTailoringScenario] = field(default_factory=list)
    # Cross-industry probes — added in the R12-polish slice for
    # systematic over-generalisation detection. Each persona carries
    # exactly one probe scenario where the job is in a completely
    # different industry from the persona's capability.
    cross_industry_probes: list[BiasScenario] = field(default_factory=list)
    # Persona-friction-context keywords for the CV-tailoring semantic
    # check per methodology §4.2 ("does the tailoring respect the
    # persona's CV-style conventions"). At least one of these tokens
    # should appear in a well-tailored CV output for this persona.
    friction_keywords: list[str] = field(default_factory=list)
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


# ---------------------------------------------------------------------------
# R12-broadening: programmatic extension of each persona's scenarios from
# 1 to 10 scoring scenarios (3 strong + 4 mixed + 3 weak) + addition of
# 10 CV-tailoring scenarios (4 light + 4 moderate + 2 significant) per
# persona. Generators are persona-aware (use the persona's industry,
# location, friction context); first-run strong-fit scenarios above are
# preserved as scenarios[0] so bias-testing-2026-05-18.md remains
# comparable.
# ---------------------------------------------------------------------------


def _wider_friction_mixed_pair(persona: PersonaFixture) -> list[BiasScenario]:
    """Two cohort-appropriate mixed-fit scenarios for wider-friction-
    class personas, substituting the migrant-shaped format_mismatch /
    language_barrier scenarios used for the most-acute cohort.

    R12-polish slice (2026-05-18): the R12-broadening run surfaced
    2 fixture-design artefacts where format_mismatch / language_barrier
    were applied cohort-blindly to German-native wider-friction
    personas (Käthe + Tobias scored ~95 / 92 instead of the
    expected mixed-fit band). This helper emits friction shapes
    appropriate to the persona's actual situation:

    - Käthe (re-entrant nurse): CV-gap + recency-of-experience friction.
    - Tobias (career-changer): commercial→public-sector transition +
      salary-step-down friction.
    """
    home = persona.location
    industry = persona.industry
    role_label = persona.target_roles[0] if persona.target_roles else "professional"

    if persona.slug == "kaethe":
        return [
            BiasScenario(
                label=f"{persona.slug}_mixed_cv_gap",
                job_title=f"{role_label} (12-year CV gap considered)",
                job_location=home,
                job_description=(
                    f"{home} {industry.lower()} role open to candidates returning after an "
                    "extended caregiving absence. The hiring committee evaluates the gap as "
                    "context, not deficit, but the application package must address the gap "
                    "explicitly. Otherwise role-fit is strong for clinical re-entry."
                ),
                expected_score_min=55,
                expected_score_max=85,
                rationale=(
                    "Mixed-fit: re-entry-friendly framing matches Käthe's situation; the "
                    "explicit gap-acknowledgment requirement is the friction (her old CV "
                    "doesn't address it directly)."
                ),
            ),
            BiasScenario(
                label=f"{persona.slug}_mixed_recency_friction",
                job_title=f"{role_label} (current digital-records experience required)",
                job_location=home,
                job_description=(
                    f"{home} {industry.lower()} role requires hands-on familiarity with "
                    "current digital patient-record systems (e.g., KIS), current infection-"
                    "control protocols, and post-2020 medication-management workflows. "
                    "Otherwise the underlying clinical capability matches the persona's "
                    "pre-2013 experience."
                ),
                expected_score_min=40,
                expected_score_max=70,
                rationale=(
                    "Mixed-fit: clinical capability matches but the 12-year recency gap "
                    "in digital systems is a real friction; some employers train, others "
                    "don't."
                ),
            ),
        ]
    if persona.slug == "tobias":
        return [
            BiasScenario(
                label=f"{persona.slug}_mixed_industry_transition",
                job_title=f"{role_label} (commercial→public transition welcomed)",
                job_location=home,
                job_description=(
                    f"{home} public-sector / civic-tech engineering role explicitly open to "
                    "commercial-tech career-changers. Technical capability transfers; the "
                    "friction is the bureaucratic-vocabulary translation (TVöD pay grades, "
                    "Beamtenstatus questions, Bewerbungsmappen conventions) the candidate's "
                    "commercial CV does not currently surface."
                ),
                expected_score_min=55,
                expected_score_max=85,
                rationale=(
                    "Mixed-fit: technical-capability transfer is real; the public-sector "
                    "application-conventions friction is the partially-resolved cost."
                ),
            ),
            BiasScenario(
                label=f"{persona.slug}_mixed_salary_step_down",
                job_title=f"{role_label} (TVöD E13, significant pay step-down)",
                job_location=home,
                job_description=(
                    f"{home} civic-tech NGO role at TVöD E13 (significantly below the "
                    "candidate's current commercial-fintech compensation). Mission fit is "
                    "high but the financial step-down is a real material cost the candidate "
                    "must reconcile with personal circumstances."
                ),
                expected_score_min=40,
                expected_score_max=70,
                rationale=(
                    "Mixed-fit: mission alignment is strong but pay step-down is a real "
                    "decision-friction. The score should reflect the real-world spread "
                    "between candidates who can absorb the step-down and those who can't."
                ),
            ),
        ]
    # Defensive fallback for any future wider-friction persona that has
    # not yet been hand-mapped: emit the migrant-shaped friction
    # placeholders so the test still produces 10 scenarios. The current
    # seven-persona panel is fully mapped, so this branch is unreached
    # in CI; it acts as a maintenance contract for future panel
    # additions (Phase 2 backlog item #55 would expand this when adding
    # interview-derived personas).
    return [
        BiasScenario(
            label=f"{persona.slug}_mixed_unmapped_placeholder",
            job_title=f"{role_label} (cohort-unmapped placeholder)",
            job_location=home,
            job_description=(
                f"Placeholder scenario for {persona.slug} ({persona.cohort}). "
                "Maintainer adding a new wider-friction persona: replace "
                "this string with a persona-appropriate friction shape per "
                "the R12-polish-slice convention in "
                "persona_fixtures._wider_friction_mixed_pair."
            ),
            expected_score_min=50,
            expected_score_max=80,
            rationale=(
                "Placeholder: persona's cohort+slug not yet hand-mapped in the "
                "wider-friction mixed-pair generator."
            ),
        ),
        BiasScenario(
            label=f"{persona.slug}_mixed_unmapped_placeholder_b",
            job_title=f"Senior {role_label} (cohort-unmapped placeholder)",
            job_location=home,
            job_description=(
                f"Second placeholder scenario for {persona.slug}. "
                "See preceding scenario for the maintenance-contract note."
            ),
            expected_score_min=50,
            expected_score_max=80,
            rationale="Placeholder b.",
        ),
    ]


def _default_friction_keywords(slug: str) -> list[str]:
    """Per-persona friction-context keywords used by the CV-tailoring
    semantic-fact check (methodology §4.2). At least one of these
    tokens should appear in a well-tailored CV output for the persona;
    the keywords come from the persona's documented situation and
    map to the friction the tailored CV should acknowledge."""
    table: dict[str, list[str]] = {
        "aicha": ["Anerkennung", "§16d", "Anabin", "BIBB"],
        "yusuf": ["Blue Card", "Blaue Karte", "Anmeldung"],
        "olga": ["§24", "remote", "English-speaking", "English team"],
        "mahmoud": ["Ausbildung", "Bewerbungsmappe", "subsidiär", "Handwerk"],
        "maria": ["EU citizen", "EU-Bürger", "Freizügigkeit", "Sprachpate"],
        "kaethe": ["Wiedereinstieg", "Auffrischung", "Familienpause", "re-entry"],
        "tobias": ["TVöD", "Civic Tech", "civic-tech", "Sovereign Tech", "GovTech"],
    }
    return table.get(slug, [])


def _build_cross_industry_probes(persona: PersonaFixture) -> list[BiasScenario]:
    """One cross-industry weak-fit probe per persona. Designed to
    surface systematic over-generalisation: the model should score
    these low (15-55) because the persona's capability does not
    transfer to the named industry.

    R12-polish slice (2026-05-18): the broadened-run surfaced
    Maria→Logistics Coordinator at Δ +20 above tolerance ceiling; this
    helper produces one probe per persona to determine whether the
    over-generalisation is one-off or systematic. Pattern verdict
    is decided by the bias-testing report after the run.
    """
    home = persona.location
    table: dict[str, tuple[str, str]] = {
        "aicha": (
            "Mining Technician",
            (
                "Underground-mining technician role at an operational mine in Germany. "
                "Required: industry-specific operator certifications, hands-on heavy-"
                "equipment experience, hard-hat-environment safety qualifications. "
                "No overlap with healthcare / nursing background."
            ),
        ),
        "yusuf": (
            "Hospitality Manager (hotel front-of-house)",
            (
                f"Hospitality manager role at a {home} hotel. Required: guest-services "
                "experience, hotel-PMS systems, F&B operations, multilingual customer-"
                "facing demeanor. No overlap with mechanical-engineering background."
            ),
        ),
        "olga": (
            "Construction Site Supervisor",
            (
                f"Construction-site supervisor role in {home}. Required: trades-licence "
                "(Polier-Schein), site-safety qualification, materials-handling "
                "experience, German-trades-vocabulary fluency. No overlap with "
                "frontend-development background."
            ),
        ),
        "mahmoud": (
            "Banking Clerk (retail branch)",
            (
                f"Retail-banking clerk role at a {home} bank branch. Required: "
                "Bankkauffrau / Bankkaufmann certification or in-progress, customer-"
                "facing financial-services experience, securities-product knowledge, "
                "regulatory-compliance familiarity. No overlap with handwerk / trades "
                "apprenticeship background."
            ),
        ),
        "maria": (
            "Logistics Coordinator",
            (
                f"Logistics coordinator role at a {home}-area distribution centre. "
                "Required: freight-management experience, ERP / WMS systems "
                "(SAP / LIS), customs-paperwork familiarity, supply-chain KPIs. "
                "No overlap with home-care / clinical-nursing background. "
                "(This probe replicates the broadened-run Maria→Logistics finding "
                "to determine if the over-generalisation persists.)"
            ),
        ),
        "kaethe": (
            "Logistics Coordinator",
            (
                f"Logistics coordinator role at a {home}-area distribution centre. "
                "Required: freight-management experience, ERP/WMS systems, "
                "customs-paperwork, supply-chain KPIs. No overlap with clinical-"
                "nursing background. (Cross-cohort companion probe to the Maria→"
                "Logistics scenario.)"
            ),
        ),
        "tobias": (
            "Healthcare Administrator (hospital operations)",
            (
                f"Healthcare administrator role at a {home} hospital. Required: "
                "healthcare-operations experience, hospital-info-systems familiarity, "
                "DRG / billing knowledge, healthcare-regulatory framework. No overlap "
                "with software-engineering / civic-tech background."
            ),
        ),
    }
    if persona.slug not in table:
        return []
    title, description = table[persona.slug]
    return [
        BiasScenario(
            label=f"{persona.slug}_cross_industry_probe",
            job_title=title,
            job_location=home,
            job_description=description,
            expected_score_min=15,
            expected_score_max=55,
            rationale=(
                "Cross-industry probe: persona's capability does not transfer; "
                "a calibrated model should score this in the weak-fit band."
            ),
        )
    ]


def _build_scoring_extension(persona: PersonaFixture) -> list[BiasScenario]:
    """Produce 9 additional scoring scenarios per persona — 2 strong,
    4 mixed, 3 weak. Together with the existing scenarios[0] this brings
    the total to 10 per persona per methodology §2.2."""
    slug = persona.slug
    role_label = persona.target_roles[0] if persona.target_roles else "professional"
    home = persona.location
    industry = persona.industry

    extras: list[BiasScenario] = []

    # ----- 2 additional strong-fit scenarios (75-95) -----------------
    extras.append(
        BiasScenario(
            label=f"{slug}_strong_partner_network",
            job_title=f"{role_label} (partner-network referral)",
            job_location=home,
            job_description=(
                f"Established {industry.lower()} employer in {home} recruiting via partner-network "
                f"referrals. Explicitly welcomes applicants from international and re-entry "
                f"backgrounds. Profile fit: {persona.friction_notes[:160]}"
            ),
            expected_score_min=75,
            expected_score_max=95,
            rationale=(
                "Strong-fit: explicit acceptance of the persona's friction context "
                "(international / re-entry / pivot) makes this a high-match scenario."
            ),
        )
    )
    extras.append(
        BiasScenario(
            label=f"{slug}_strong_sector_demand",
            job_title=f"Senior {role_label}",
            job_location=home,
            job_description=(
                f"{home}-based {industry.lower()} organisation with active sector shortage. "
                f"Hiring with relaxed formal-language requirement when years of experience "
                f"(target: {persona.years_experience}+) and demonstrable capability are present. "
                "Onboarding mentor assigned for first 6 months."
            ),
            expected_score_min=75,
            expected_score_max=95,
            rationale=(
                "Strong-fit: years-of-experience match + sector shortage gives the persona "
                "the leverage their friction context partially obscures elsewhere."
            ),
        )
    )

    # ----- 4 mixed-fit scenarios (50-80) -----------------------------
    # Mixed-fit scenarios — cohort-branching per R12-polish slice
    # (2026-05-18). The migrant-shaped friction scenarios
    # (format_mismatch, language_barrier) apply to the most-acute
    # cohort; for the wider-friction cohort, substitute with
    # persona-appropriate friction shapes per persona.slug.
    if persona.cohort == "wider-friction":
        extras.extend(_wider_friction_mixed_pair(persona))
    else:
        extras.append(
            BiasScenario(
                label=f"{slug}_mixed_format_mismatch",
                job_title=f"{role_label} (German-format Bewerbung required)",
                job_location=home,
                job_description=(
                    f"{home} {industry.lower()} employer requires applications in strict "
                    "German-Lebenslauf format (Tabellarisch, photo, full address, "
                    "Unterschrift). No exceptions. Otherwise standard role for the persona's "
                    "capability."
                ),
                expected_score_min=50,
                expected_score_max=80,
                rationale=(
                    "Mixed-fit: capability matches but the format requirement is a real friction "
                    "for personas whose home-country CV conventions differ; tailoring tool helps."
                ),
            )
        )
        extras.append(
            BiasScenario(
                label=f"{slug}_mixed_language_barrier",
                job_title=f"{role_label} (C1 German required)",
                job_location=home,
                job_description=(
                    f"{home} {industry.lower()} role requiring German C1 minimum for client-facing "
                    "documentation. Otherwise excellent role fit. Persona's actual German level "
                    f"({next((lg for lg in persona.languages if lg.startswith('DE')), 'DE: A2')}) "
                    "is below the formal requirement."
                ),
                expected_score_min=40,
                expected_score_max=70,
                rationale=(
                    "Mixed-fit: formal-language gap is a real exclusion criterion for some "
                    "employers; others negotiate. The score should reflect the real-world "
                    "spread."
                ),
            )
        )
    # distant_city is cohort-neutral (relocation cost is real for everyone).
    extras.append(
        BiasScenario(
            label=f"{slug}_mixed_distant_city",
            job_title=f"{role_label} (relocation required)",
            job_location="Frankfurt am Main",
            job_description=(
                f"Frankfurt-based {industry.lower()} employer with otherwise excellent fit. "
                "Relocation costs covered for first hire. Persona currently in another "
                f"city ({home}); relocation introduces friction beyond the role itself."
            ),
            expected_score_min=50,
            expected_score_max=80,
            rationale=(
                "Mixed-fit: role-fit is strong but location/relocation is a real cost that "
                "may push the persona's actual decision below the role-only fit."
            ),
        )
    )
    extras.append(
        BiasScenario(
            label=f"{slug}_mixed_adjacent_specialty",
            job_title=f"Senior {role_label} (adjacent specialty)",
            job_location=home,
            job_description=(
                f"{home} {industry.lower()} role in an adjacent specialty the persona has "
                "not directly practised but where the underlying capability transfers. "
                "Employer will train for the specialty gap; team is mixed-language and "
                "professionally welcoming."
            ),
            expected_score_min=55,
            expected_score_max=85,
            rationale=(
                "Mixed-fit: adjacent-specialty transfer is plausible but uncertain; the "
                "model should reward capability transfer without overscoring."
            ),
        )
    )

    # ----- 3 weak-fit scenarios (15-50) ------------------------------
    weak_industries = [
        ("Software Engineer", "Software"),
        ("Sales Account Manager", "Sales / B2B"),
        ("Logistics Coordinator", "Logistics"),
    ]
    # Filter out the persona's own industry so the weak-fit really is weak.
    weak_industries = [(t, i) for t, i in weak_industries if i.lower() not in industry.lower()][:3]
    if len(weak_industries) < 3:
        # Fallback in case persona industry overlapped with all three.
        weak_industries.append(("Construction Foreman", "Construction"))
    for label_suffix, (job_title, weak_industry) in zip(
        ["wrong_industry_a", "wrong_industry_b", "wrong_industry_c"], weak_industries
    ):
        extras.append(
            BiasScenario(
                label=f"{slug}_weak_{label_suffix}",
                job_title=job_title,
                job_location=home,
                job_description=(
                    f"{home}-based {weak_industry.lower()} firm seeks {job_title} with "
                    f"typical {weak_industry.lower()} skill set. No overlap with the "
                    f"persona's {industry.lower()} background; persona's friction context "
                    "is irrelevant to this role."
                ),
                expected_score_min=15,
                expected_score_max=50,
                rationale=(
                    "Weak-fit: industry-and-role mismatch dominates; the persona's friction-"
                    "context strengths do not transfer."
                ),
            )
        )

    return extras


def _build_cv_tailoring_scenarios(persona: PersonaFixture) -> list[CvTailoringScenario]:
    """Produce 10 CV-tailoring scenarios per persona — 4 light, 4
    moderate, 2 significant tailoring difficulty per methodology §4."""
    slug = persona.slug
    role_label = persona.target_roles[0] if persona.target_roles else "professional"
    home = persona.location
    industry = persona.industry

    scenarios: list[CvTailoringScenario] = []

    # 4 light tailoring — same role-shape, same industry, same level
    for i, suffix in enumerate(["a", "b", "c", "d"]):
        scenarios.append(
            CvTailoringScenario(
                label=f"{slug}_cv_light_{suffix}",
                job_title=f"{role_label} ({['outpatient', 'hospital', 'private', 'public'][i]} setting)",
                job_location=home,
                job_description=(
                    f"{home}-based {industry.lower()} role matching the persona's capability profile. "
                    f"{['Outpatient', 'Hospital', 'Private', 'Public'][i]} setting. Standard "
                    "CV reframing expected — same broad sections, language match, role-relevant "
                    "ordering."
                ),
                tailoring_difficulty="light",
                pass_criteria=(
                    "Tailored CV references at least one specific skill from the persona's "
                    "documented skill list; CV-section ordering reflects the role focus."
                ),
            )
        )

    # 4 moderate tailoring — same industry, different role-shape
    for _i, suffix in enumerate(["lead", "supervisor", "training", "documentation"]):
        scenarios.append(
            CvTailoringScenario(
                label=f"{slug}_cv_moderate_{suffix}",
                job_title=f"{role_label} ({suffix} component)",
                job_location=home,
                job_description=(
                    f"{home}-based {industry.lower()} role with an added {suffix} component "
                    "the persona's CV does not foreground today. Moderate tailoring expected: "
                    f"surface the {suffix}-adjacent experience the persona has, even if not "
                    "labelled as such on the current CV."
                ),
                tailoring_difficulty="moderate",
                pass_criteria=(
                    f"Tailored CV introduces or foregrounds {suffix}-relevant content drawn from "
                    "the persona's existing CV; honest about gaps where they exist."
                ),
            )
        )

    # 2 significant tailoring — cross-industry pivot
    pivots = [
        ("Healthcare Operations Coordinator", "Healthcare admin"),
        ("Technical Writer (sector-domain)", "Technical writing / documentation"),
    ]
    for suffix, (pivot_title, pivot_industry) in zip(["pivot_a", "pivot_b"], pivots):
        scenarios.append(
            CvTailoringScenario(
                label=f"{slug}_cv_significant_{suffix}",
                job_title=pivot_title,
                job_location=home,
                job_description=(
                    f"{home} {pivot_industry} role. Persona has transferable capability "
                    f"(domain knowledge, client-facing skill, documentation discipline) "
                    "but not the formal job title or sector. Significant tailoring required: "
                    "reframe the persona's experience in the pivot industry's vocabulary "
                    "without inventing facts."
                ),
                tailoring_difficulty="significant",
                pass_criteria=(
                    "Tailored CV reframes existing experience in the pivot industry's "
                    "vocabulary; explicitly notes the role-title gap rather than glossing over "
                    "it; no hallucinated certifications or job titles."
                ),
            )
        )

    return scenarios


# Apply the generators to each persona at import time. The first-run
# strong-fit scenario stays as scenarios[0]; the generators append the
# rest.
for _persona in PERSONAS:
    _persona.scenarios.extend(_build_scoring_extension(_persona))
    _persona.cv_tailoring_scenarios = _build_cv_tailoring_scenarios(_persona)
    _persona.cross_industry_probes = _build_cross_industry_probes(_persona)
    _persona.friction_keywords = _default_friction_keywords(_persona.slug)


# ---------------------------------------------------------------------------
# Sanity check at import time — fail-fast if a future edit drops to six
# personas, drops the cohort tags, breaks the scoring-scenario distribution,
# or breaks the CV-tailoring-scenario distribution.
# ---------------------------------------------------------------------------
assert len(PERSONAS) == 7, "Decision 21 requires seven personas; got " + str(len(PERSONAS))
assert sum(1 for p in PERSONAS if p.cohort == "most-acute") == 5, (
    "Five most-acute migrant personas required per Decision 21"
)
assert sum(1 for p in PERSONAS if p.cohort == "wider-friction") == 2, (
    "Two wider-friction-class personas required per Decision 21"
)

# Scoring scenarios: 10 per persona (3 strong + 4 mixed + 3 weak) per
# methodology §2.2. Total 70 across the cohort.
for _p in PERSONAS:
    assert len(_p.scenarios) == 10, (
        f"{_p.slug}: methodology §2.2 requires 10 scoring scenarios; got " + str(len(_p.scenarios))
    )
_total_scoring = sum(len(p.scenarios) for p in PERSONAS)
assert _total_scoring == 70, "Expected 70 scoring scenarios; got " + str(_total_scoring)

# CV-tailoring scenarios: 10 per persona (4 light + 4 moderate + 2
# significant) per methodology §4. Total 70 across the cohort.
for _p in PERSONAS:
    assert len(_p.cv_tailoring_scenarios) == 10, (
        f"{_p.slug}: methodology §4 requires 10 CV-tailoring scenarios; got "
        + str(len(_p.cv_tailoring_scenarios))
    )
    _difficulty_counts: dict[str, int] = {}
    for _s in _p.cv_tailoring_scenarios:
        _difficulty_counts[_s.tailoring_difficulty] = (
            _difficulty_counts.get(_s.tailoring_difficulty, 0) + 1
        )
    assert _difficulty_counts.get("light", 0) == 4, (
        f"{_p.slug}: 4 light CV-tailoring scenarios required; got "
        + str(_difficulty_counts.get("light", 0))
    )
    assert _difficulty_counts.get("moderate", 0) == 4, (
        f"{_p.slug}: 4 moderate CV-tailoring scenarios required; got "
        + str(_difficulty_counts.get("moderate", 0))
    )
    assert _difficulty_counts.get("significant", 0) == 2, (
        f"{_p.slug}: 2 significant CV-tailoring scenarios required; got "
        + str(_difficulty_counts.get("significant", 0))
    )

# Cross-industry probes (R12-polish slice 2026-05-18): 1 per persona,
# total 7 across the cohort. Used to detect systematic cross-industry
# over-generalisation (the Maria→Logistics broadened-run finding).
for _p in PERSONAS:
    assert len(_p.cross_industry_probes) == 1, (
        f"{_p.slug}: exactly 1 cross-industry probe required for the "
        "R12-polish slice; got " + str(len(_p.cross_industry_probes))
    )
_total_probes = sum(len(p.cross_industry_probes) for p in PERSONAS)
assert _total_probes == 7, "Expected 7 cross-industry probes (1 per persona); got " + str(
    _total_probes
)

# Friction-context keywords: every persona must have ≥1 documented
# keyword so the CV-tailoring semantic-fact check (methodology §4.2)
# can verify the tailored CV acknowledges the persona's friction shape.
for _p in PERSONAS:
    assert len(_p.friction_keywords) >= 1, (
        f"{_p.slug}: friction_keywords must be non-empty for CV-tailoring semantic check; got 0"
    )

# Cohort-appropriateness guard: wider-friction-class personas must NOT
# carry migrant-shaped friction labels (format_mismatch / language_barrier).
# This guard exists because the R12-broadening run scored Käthe and
# Tobias as honest out-of-band where the fixture itself applied
# migrant-shaped friction to German-native personas. Cohort branching
# in _build_scoring_extension corrects this; the guard fails fast if
# a future edit re-introduces the cohort-blind shape.
for _p in PERSONAS:
    if _p.cohort != "wider-friction":
        continue
    for _scen in _p.scenarios:
        assert "format_mismatch" not in _scen.label, (
            f"{_p.slug} ({_p.cohort}): scenario {_scen.label!r} carries the "
            "migrant-shaped 'format_mismatch' label; use cohort-appropriate "
            "friction (gap_in_cv / recency / industry_transition / "
            "salary_step_down) instead — see _wider_friction_mixed_pair."
        )
        assert "language_barrier" not in _scen.label, (
            f"{_p.slug} ({_p.cohort}): scenario {_scen.label!r} carries the "
            "migrant-shaped 'language_barrier' label; use cohort-appropriate "
            "friction instead — see _wider_friction_mixed_pair."
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


def friction_keywords_for(persona_id: str | None) -> list[str]:
    """Look up friction-context keywords for a persona_id.

    Returns the persona's documented friction-vocabulary list if the
    ``persona_id`` matches one of the seven-persona panel slugs
    (``aicha``, ``yusuf``, ``olga``, ``mahmoud``, ``maria``, ``kaethe``,
    ``tobias``). Returns an empty list for any other persona_id (e.g.,
    production job-category personas like ``healthcare-management``,
    ``tech``, etc., defined in ``company_discovery/personas.py``).

    Used by the chat-router CV-tailoring path (``app.py``) to thread
    persona-specific friction vocabulary into
    ``execute_cv_tailoring``'s ``friction_keywords`` parameter. The
    contract was verified at 87.1% overall pass-rate / 92.9% criterion-
    (d) pass-rate in the bias-testing run dated 2026-05-19 (see
    ``docs/grant/bias-testing-2026-05-19.md``).

    Backward-compat: a ``None`` or non-panel persona_id returns ``[]``,
    which lets ``build_cv_tailoring_prompt`` skip the persona-specific
    vocab line while preserving the always-present friction-context
    instruction paragraph.
    """
    if not persona_id:
        return []
    for persona in PERSONAS:
        if persona.slug == persona_id:
            return list(persona.friction_keywords)
    return []


def demo_email(slug: str, email_domain: str = "demo.helpmefindthejob.com") -> str:
    """Canonical demo email for a persona.

    The default domain follows the public-tree placeholder convention
    (Decision 12 + Open R8 closed 2026-05-18). The deployer overrides
    ``email_domain`` when running the seed script against a
    real subdomain (the override stays in the deployer's private
    ``.env``).
    """
    return f"{slug}@{email_domain}"
