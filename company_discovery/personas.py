# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Persona registry.

The product was originally built for a single persona —
``healthcare-management`` (early-career, Germany-focused, healthcare
operations). This module holds the *data* for that persona and any
additional personas (tech, marketing, finance, product-management),
so ranking / suggestion / template logic stays generic and the
content lives in one place.

Each :class:`Persona` carries everything the rest of the system
needs to be useful for that audience:

- ``sector_weights`` for :func:`persona_ranking.rank_candidates`
- ``industry_match_terms`` for ``suggest_curated_companies`` /
  ``suggest_relevant_companies`` industry-keyword bonus
- ``default_target_roles`` / ``default_industry`` so the UI can
  prefill empty searches sensibly
- ``category_suggestions`` — abstract employer categories shown
  when curated company seeds are not enough
- ``role_to_sector_boosts`` — persona-specific lifts (e.g. boosting
  pharma for healthcare ``market access`` searches)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class CategorySuggestion:
    """One generic employer category surfaced when curated seeds are scarce."""

    label: str
    reason: str
    base_score: float = 0.55
    role_keyword_boosts: tuple[tuple[tuple[str, ...], float], ...] = ()


@dataclass(frozen=True)
class Persona:
    id: str
    label: str
    description: str
    default_target_roles: tuple[str, ...]
    default_industry: str
    industry_match_terms: tuple[str, ...]
    sector_weights: Mapping[str, float]
    category_suggestions: tuple[CategorySuggestion, ...]
    role_to_sector_boosts: tuple[
        tuple[tuple[str, ...], tuple[str, ...], float], ...
    ] = field(default_factory=tuple)


_HEALTHCARE_MANAGEMENT = Persona(
    id="healthcare-management",
    label="Healthcare management",
    description=(
        "Public health, hospital operations, statutory insurers, "
        "digital health, market access, and healthcare consulting "
        "roles in the German-speaking market."
    ),
    default_target_roles=(
        "project management",
        "quality management",
        "process management",
        "digital health",
        "public health",
    ),
    default_industry="Healthcare",
    industry_match_terms=("health", "gesund", "klinik", "pharma", "medtech"),
    sector_weights={
        "hospital": 0.85,
        "clinic": 0.85,
        "university hospital": 0.9,
        "statutory health insurer": 0.85,
        "private health insurer": 0.8,
        "public health institution": 0.8,
        "research institute": 0.75,
        "healthcare association": 0.7,
        "pharma": 0.7,
        "medtech": 0.7,
        "digital health": 0.85,
        "healthcare it": 0.85,
        "healthcare consulting": 0.85,
        "policy": 0.75,
        "market access": 0.85,
        "public affairs": 0.8,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Hospitals and clinic groups",
            reason="Strong fit for healthcare project, quality, and process-management roles.",
            role_keyword_boosts=(
                (("quality", "process", "projekt", "project"), 0.15),
            ),
        ),
        CategorySuggestion(
            label="University hospitals",
            reason="Strong fit for public-sector healthcare management, research coordination, and clinical operations roles.",
        ),
        CategorySuggestion(
            label="Statutory health insurers",
            reason="Strong fit for public health, digital health, care management, and policy roles.",
            role_keyword_boosts=(
                (("market access", "public affairs", "policy"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Private health insurers",
            reason="Strong fit for product, quality, process, and healthcare analytics roles.",
            role_keyword_boosts=(
                (("market access", "public affairs", "policy"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Public-health institutions",
            reason="Strong fit for public-health, prevention, population health, and policy work.",
            role_keyword_boosts=(
                (("market access", "public affairs", "policy"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Research institutes",
            reason="Strong fit for health services research and evidence-based healthcare management.",
        ),
        CategorySuggestion(
            label="Pharma and MedTech companies",
            reason="Strong fit for market access, public affairs, and healthcare project roles.",
            role_keyword_boosts=(
                (("market access", "public affairs", "policy"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Digital Health startups",
            reason="Strong fit for digital health, product operations, implementation, and customer success roles.",
            role_keyword_boosts=(
                (("digital", "it", "software"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Healthcare IT companies",
            reason="Strong fit for implementation, process management, and healthcare software roles.",
            role_keyword_boosts=(
                (("digital", "it", "software"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Consulting firms with healthcare practices",
            reason="Strong fit for junior consulting and healthcare transformation roles.",
            role_keyword_boosts=(
                (("quality", "process", "projekt", "project"), 0.15),
            ),
        ),
    ),
)


_TECH = Persona(
    id="tech",
    label="Technology",
    description=(
        "Software engineering, platform, data, ML, security, and "
        "developer-tools roles across European tech employers."
    ),
    default_target_roles=(
        "software engineer",
        "backend engineer",
        "frontend engineer",
        "data engineer",
        "site reliability engineer",
    ),
    default_industry="Technology",
    industry_match_terms=("tech", "software", "saas", "platform", "developer"),
    sector_weights={
        "saas": 0.85,
        "developer tools": 0.9,
        "open source": 0.85,
        "cloud infrastructure": 0.85,
        "fintech": 0.8,
        "ai / ml": 0.85,
        "data infrastructure": 0.85,
        "cybersecurity": 0.8,
        "consumer tech": 0.7,
        "e-commerce platform": 0.7,
        "marketplace": 0.7,
        "gaming": 0.65,
        "edtech": 0.65,
        "media / streaming": 0.65,
    },
    category_suggestions=(
        CategorySuggestion(
            label="European SaaS companies",
            reason="Strong fit for backend, frontend, full-stack, and platform engineering roles.",
            role_keyword_boosts=(
                (("backend", "frontend", "full stack", "platform"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Cloud infrastructure & DevOps",
            reason="Strong fit for SRE, platform, infra, Kubernetes, and observability roles.",
            role_keyword_boosts=(
                (("sre", "devops", "platform", "infra", "kubernetes"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="AI / ML companies",
            reason="Strong fit for ML engineering, applied research, MLOps, and data engineering roles.",
            role_keyword_boosts=(
                (("ml", "machine learning", "ai", "data"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Developer-tools companies",
            reason="Strong fit for engineers who want to build for other engineers.",
        ),
        CategorySuggestion(
            label="Cybersecurity vendors",
            reason="Strong fit for security engineering, detection, and AppSec roles.",
            role_keyword_boosts=(
                (("security", "appsec", "detection"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Fintech & neobanks",
            reason="Strong fit for payment, ledger, risk, and high-throughput backend engineers.",
            role_keyword_boosts=(
                (("payment", "ledger", "risk", "backend"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Open-source companies",
            reason="Strong fit for engineers who want their work in public.",
        ),
    ),
    role_to_sector_boosts=(
        (("ml", "machine learning", "ai"), ("ai / ml", "data infrastructure"), 0.10),
        (("payment", "ledger"), ("fintech",), 0.10),
        (("sre", "devops", "platform"), ("cloud infrastructure", "developer tools"), 0.10),
    ),
)


_MARKETING = Persona(
    id="marketing",
    label="Marketing",
    description=(
        "Brand, growth, performance marketing, content, SEO, CRM, "
        "product marketing, and demand-generation roles across "
        "consumer and B2B employers."
    ),
    default_target_roles=(
        "marketing manager",
        "growth marketing",
        "brand manager",
        "content marketing",
        "performance marketing",
    ),
    default_industry="Marketing",
    industry_match_terms=("marketing", "brand", "growth", "consumer", "retail"),
    sector_weights={
        "consumer brand": 0.85,
        "dtc": 0.85,
        "b2b saas": 0.8,
        "e-commerce": 0.8,
        "marketplace": 0.75,
        "media / streaming": 0.75,
        "agency": 0.75,
        "fintech": 0.7,
        "fmcg": 0.8,
        "food & beverage": 0.75,
        "fashion / lifestyle": 0.8,
        "travel & hospitality": 0.7,
        "entertainment": 0.7,
    },
    category_suggestions=(
        CategorySuggestion(
            label="DTC consumer brands",
            reason="Strong fit for brand, growth, content, and lifecycle marketing roles.",
            role_keyword_boosts=(
                (("brand", "growth", "content", "social"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="B2B SaaS marketing teams",
            reason="Strong fit for product marketing, demand gen, and content roles in software.",
            role_keyword_boosts=(
                (("product marketing", "demand gen", "content", "seo"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Performance / growth agencies",
            reason="Strong fit for paid acquisition, performance marketing, and analytics-heavy roles.",
            role_keyword_boosts=(
                (("performance", "paid", "growth", "acquisition"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="E-commerce & marketplaces",
            reason="Strong fit for CRM, lifecycle, retention, and merchandising roles.",
            role_keyword_boosts=(
                (("crm", "lifecycle", "retention", "ecommerce"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Media & streaming",
            reason="Strong fit for content marketing, PR, partnerships, and audience growth roles.",
        ),
        CategorySuggestion(
            label="FMCG & lifestyle brands",
            reason="Strong fit for traditional brand marketing, integrated campaigns, and trade marketing roles.",
            role_keyword_boosts=(
                (("brand", "campaign", "trade"), 0.15),
            ),
        ),
    ),
)


_FINANCE = Persona(
    id="finance",
    label="Finance",
    description=(
        "FP&A, controlling, accounting, treasury, audit, risk, "
        "compliance, investment, and corporate-finance roles "
        "across banks, insurers, asset managers, and corporates."
    ),
    default_target_roles=(
        "financial analyst",
        "fp&a",
        "controller",
        "audit",
        "risk analyst",
    ),
    default_industry="Finance",
    industry_match_terms=("finance", "bank", "insurance", "asset", "audit"),
    sector_weights={
        "bank": 0.85,
        "investment bank": 0.85,
        "private bank": 0.8,
        "asset management": 0.85,
        "private equity": 0.85,
        "venture capital": 0.8,
        "insurance": 0.8,
        "reinsurance": 0.8,
        "fintech": 0.85,
        "audit firm": 0.85,
        "management consulting": 0.85,
        "ratings": 0.75,
        "corporate finance": 0.8,
        "treasury": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Universal & investment banks",
            reason="Strong fit for analyst, FP&A, M&A, risk, treasury, and compliance roles.",
            role_keyword_boosts=(
                (("analyst", "fp&a", "risk", "treasury", "m&a"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Asset managers & private capital",
            reason="Strong fit for investment analyst, portfolio operations, and reporting roles.",
            role_keyword_boosts=(
                (("investment", "portfolio", "fund"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Insurers & reinsurers",
            reason="Strong fit for risk, actuarial, compliance, controlling, and reporting roles.",
            role_keyword_boosts=(
                (("risk", "actuarial", "compliance", "controlling"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Big-4 audit & advisory",
            reason="Strong fit for auditor, transaction services, and advisory roles.",
            role_keyword_boosts=(
                (("audit", "advisory", "transaction"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Fintech",
            reason="Strong fit for finance, ledger, treasury, and risk roles in tech-led finance.",
            role_keyword_boosts=(
                (("ledger", "treasury", "risk", "fintech"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Corporate finance teams (DAX 40 / large caps)",
            reason="Strong fit for controlling, FP&A, treasury, and internal-audit roles inside large corporates.",
            role_keyword_boosts=(
                (("controlling", "fp&a", "treasury"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Management consulting (financial-services practice)",
            reason="Strong fit for consultant and analyst roles serving banks / insurers.",
        ),
    ),
)


_PRODUCT_MANAGEMENT = Persona(
    id="product-management",
    label="Product management",
    description=(
        "Product manager, product owner, technical PM, and group "
        "PM roles across software, fintech, marketplace, and "
        "consumer-tech employers."
    ),
    default_target_roles=(
        "product manager",
        "junior product manager",
        "associate product manager",
        "product owner",
        "technical product manager",
    ),
    default_industry="Product Management",
    industry_match_terms=("product", "saas", "tech", "software", "platform"),
    sector_weights={
        "b2b saas": 0.9,
        "developer tools": 0.85,
        "fintech": 0.85,
        "consumer tech": 0.8,
        "marketplace": 0.85,
        "ai / ml": 0.85,
        "e-commerce platform": 0.8,
        "media / streaming": 0.7,
        "edtech": 0.75,
        "healthtech": 0.75,
        "mobility": 0.7,
        "logistics": 0.7,
    },
    category_suggestions=(
        CategorySuggestion(
            label="B2B SaaS product teams",
            reason="Strong fit for product managers shipping to other businesses.",
            role_keyword_boosts=(
                (("b2b", "platform", "api", "integration"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Consumer tech",
            reason="Strong fit for PMs working on growth, engagement, and consumer features.",
            role_keyword_boosts=(
                (("growth", "consumer", "mobile"), 0.20),
            ),
        ),
        CategorySuggestion(
            label="Fintech product teams",
            reason="Strong fit for PMs on payments, lending, banking, and risk products.",
            role_keyword_boosts=(
                (("payment", "lending", "banking", "risk"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Marketplaces",
            reason="Strong fit for PMs on supply, demand, search, and trust-and-safety problems.",
            role_keyword_boosts=(
                (("supply", "demand", "marketplace", "search", "trust"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="AI / ML product",
            reason="Strong fit for PMs shipping ML-powered features or AI products.",
            role_keyword_boosts=(
                (("ai", "ml", "model", "llm"), 0.25),
            ),
        ),
        CategorySuggestion(
            label="Developer tools / platform",
            reason="Strong fit for technical PMs serving an engineer audience.",
            role_keyword_boosts=(
                (("technical", "platform", "developer", "api"), 0.25),
            ),
        ),
    ),
)


_EDUCATION = Persona(
    id="education",
    label="Education & academia",
    description=(
        "Teachers, lecturers, professors, school + university administration, "
        "EdTech roles, education-policy and research-coordinator positions."
    ),
    default_target_roles=(
        "lecturer",
        "research associate",
        "wissenschaftlicher mitarbeiter",
        "school administrator",
        "edtech product",
    ),
    default_industry="Education",
    industry_match_terms=("education", "school", "university", "academic", "edtech"),
    sector_weights={
        "university": 0.9,
        "school": 0.85,
        "edtech": 0.85,
        "research institute": 0.85,
        "fachhochschule": 0.85,
        "ngo / education policy": 0.75,
        "publishing / academic": 0.7,
        "ministry of education": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Universities & research institutes",
            reason="Strong fit for lecturer, postdoc, research-associate, and academic-coordinator roles.",
            role_keyword_boosts=((("research", "postdoc", "lecturer", "professor"), 0.25),),
        ),
        CategorySuggestion(
            label="EdTech companies",
            reason="Strong fit for product, content-design, and customer-success roles in education software.",
            role_keyword_boosts=((("edtech", "curriculum", "learning", "content"), 0.20),),
        ),
        CategorySuggestion(
            label="Schools & school networks",
            reason="Strong fit for teaching, school-administration, and curriculum-coordinator roles.",
            role_keyword_boosts=((("teach", "curriculum", "principal"), 0.15),),
        ),
        CategorySuggestion(
            label="Education-policy and ministries",
            reason="Strong fit for education-policy, NGO, and public-sector education roles.",
            role_keyword_boosts=((("policy", "ministry", "ngo"), 0.20),),
        ),
    ),
)


_LEGAL = Persona(
    id="legal",
    label="Legal",
    description=(
        "Lawyer, paralegal, in-house counsel, compliance, contracts, "
        "regulatory and legal-tech roles across law firms, corporates, "
        "and public institutions."
    ),
    default_target_roles=(
        "associate lawyer",
        "in-house counsel",
        "rechtsanwalt",
        "compliance officer",
        "contracts manager",
    ),
    default_industry="Legal",
    industry_match_terms=("legal", "law", "rechts", "kanzlei", "compliance"),
    sector_weights={
        "law firm": 0.9,
        "kanzlei": 0.9,
        "in-house legal": 0.85,
        "compliance": 0.85,
        "regulatory": 0.8,
        "legal tech": 0.8,
        "patent / ip": 0.8,
        "ngo / legal aid": 0.7,
        "ministry of justice": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Law firms (Kanzleien)",
            reason="Strong fit for associate, paralegal, of-counsel, and partner-track roles.",
            role_keyword_boosts=((("associate", "partner", "paralegal", "anwalt"), 0.25),),
        ),
        CategorySuggestion(
            label="In-house legal teams (corporates)",
            reason="Strong fit for in-house counsel, contracts, compliance, and IP roles inside DAX 40 / EU corporates.",
            role_keyword_boosts=((("in-house", "counsel", "contracts", "ip"), 0.25),),
        ),
        CategorySuggestion(
            label="Compliance & regulatory",
            reason="Strong fit for compliance officer, MaRisk / GDPR / Datenschutz roles.",
            role_keyword_boosts=((("compliance", "regulatory", "datenschutz", "gdpr"), 0.20),),
        ),
        CategorySuggestion(
            label="Legal tech",
            reason="Strong fit for legal-ops, contract-automation, and legaltech-product roles.",
            role_keyword_boosts=((("legal tech", "contract", "ops"), 0.20),),
        ),
    ),
)


_SALES = Persona(
    id="sales",
    label="Sales & business development",
    description=(
        "Account executive, SDR, sales engineer, BizDev, partnerships, "
        "and account-management roles across SaaS, enterprise, and "
        "consumer brands."
    ),
    default_target_roles=(
        "account executive",
        "business development representative",
        "sales engineer",
        "key account manager",
        "partnerships manager",
    ),
    default_industry="Sales",
    industry_match_terms=("sales", "vertrieb", "business development", "account", "partnerships"),
    sector_weights={
        "b2b saas": 0.9,
        "enterprise software": 0.85,
        "fintech": 0.8,
        "advertising / adtech": 0.8,
        "consumer brand": 0.75,
        "industrial": 0.7,
        "agency": 0.7,
        "marketplace": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="B2B SaaS sales teams",
            reason="Strong fit for AE, SDR, account manager, and sales-engineer roles in software vendors.",
            role_keyword_boosts=((("ae", "sdr", "account", "saas"), 0.25),),
        ),
        CategorySuggestion(
            label="Enterprise software (mid-market & up)",
            reason="Strong fit for enterprise AE, key account, and solution-sales roles.",
            role_keyword_boosts=((("enterprise", "key account", "solution"), 0.20),),
        ),
        CategorySuggestion(
            label="Partnerships & channel",
            reason="Strong fit for partner manager, channel sales, and alliance roles.",
            role_keyword_boosts=((("partner", "channel", "alliance"), 0.25),),
        ),
        CategorySuggestion(
            label="Sales engineering",
            reason="Strong fit for sales engineer, solutions architect, technical AE roles.",
            role_keyword_boosts=((("sales engineer", "solutions"), 0.25),),
        ),
    ),
)


_DESIGN = Persona(
    id="design",
    label="Design",
    description=(
        "Product designer, UX, UI, visual designer, design-ops, content "
        "designer, and creative-direction roles across software, agencies, "
        "and consumer brands."
    ),
    default_target_roles=(
        "product designer",
        "ux designer",
        "ui designer",
        "design lead",
        "content designer",
    ),
    default_industry="Design",
    industry_match_terms=("design", "ux", "ui", "creative", "product design"),
    sector_weights={
        "b2b saas": 0.85,
        "consumer tech": 0.85,
        "design agency": 0.85,
        "media / streaming": 0.8,
        "fintech": 0.8,
        "marketplace": 0.8,
        "advertising / adtech": 0.75,
        "fashion / lifestyle": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="In-house product design teams",
            reason="Strong fit for product designer, UX, UI, and design-system roles.",
            role_keyword_boosts=((("product designer", "ux", "ui", "design system"), 0.25),),
        ),
        CategorySuggestion(
            label="Design agencies & studios",
            reason="Strong fit for senior designer, art director, and creative-lead roles.",
            role_keyword_boosts=((("art director", "creative", "senior designer"), 0.20),),
        ),
        CategorySuggestion(
            label="Content & UX writing",
            reason="Strong fit for content designer, UX writer, and information-architecture roles.",
            role_keyword_boosts=((("content designer", "ux writer", "information"), 0.25),),
        ),
        CategorySuggestion(
            label="Design ops / research",
            reason="Strong fit for design-ops, user-research, and research-ops roles.",
            role_keyword_boosts=((("research", "ops", "design ops"), 0.20),),
        ),
    ),
)


_OPERATIONS = Persona(
    id="operations",
    label="Operations & logistics",
    description=(
        "Supply chain, warehouse, fleet, customer-ops, business-ops, "
        "process-improvement, and operations-management roles in "
        "logistics, e-commerce, manufacturing, and platform companies."
    ),
    default_target_roles=(
        "operations manager",
        "supply chain analyst",
        "logistics coordinator",
        "business operations",
        "process improvement",
    ),
    default_industry="Operations",
    industry_match_terms=("operations", "logistics", "supply chain", "warehouse", "fleet"),
    sector_weights={
        "logistics / freight": 0.9,
        "e-commerce": 0.85,
        "manufacturing": 0.85,
        "marketplace": 0.8,
        "delivery / mobility": 0.85,
        "retail": 0.75,
        "consumer brand": 0.75,
        "saas business ops": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Logistics & freight operators",
            reason="Strong fit for warehouse, fleet, supply-chain, and route-planning roles.",
            role_keyword_boosts=((("warehouse", "supply chain", "fleet", "logistics"), 0.25),),
        ),
        CategorySuggestion(
            label="E-commerce & marketplace ops",
            reason="Strong fit for fulfillment, customer-ops, and platform-ops roles.",
            role_keyword_boosts=((("fulfillment", "customer ops", "marketplace"), 0.20),),
        ),
        CategorySuggestion(
            label="Manufacturing & process",
            reason="Strong fit for production planning, quality, lean / six-sigma roles.",
            role_keyword_boosts=((("production", "quality", "lean", "six sigma"), 0.20),),
        ),
        CategorySuggestion(
            label="Business operations (SaaS)",
            reason="Strong fit for biz-ops, rev-ops, and strategic-ops roles in software companies.",
            role_keyword_boosts=((("biz ops", "rev ops", "strategic"), 0.25),),
        ),
    ),
)


_HEALTHCARE_CLINICAL = Persona(
    id="healthcare-clinical",
    label="Healthcare clinical",
    description=(
        "Nurses, doctors, therapists, paramedics, midwives, and direct-care "
        "professionals — distinct from healthcare-management which covers "
        "administrative, policy, and project roles."
    ),
    default_target_roles=(
        "krankenpfleger",
        "pflegefachkraft",
        "physiotherapist",
        "registered nurse",
        "facharzt",
    ),
    default_industry="Healthcare",
    industry_match_terms=("krankenhaus", "klinik", "hospital", "pflege", "care"),
    sector_weights={
        "hospital": 0.95,
        "clinic": 0.9,
        "university hospital": 0.95,
        "elderly care": 0.85,
        "rehabilitation clinic": 0.85,
        "ambulatory practice": 0.8,
        "home care": 0.8,
        "emergency / paramedic": 0.85,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Hospitals & clinic groups",
            reason="Strong fit for nursing, doctor, therapist, and direct-care roles.",
            role_keyword_boosts=((("krankenpfleger", "nurse", "arzt", "physician", "therapist"), 0.30),),
        ),
        CategorySuggestion(
            label="Elderly & home care",
            reason="Strong fit for senior-care, nursing-home, and home-care roles.",
            role_keyword_boosts=((("altenpflege", "elderly", "home care"), 0.25),),
        ),
        CategorySuggestion(
            label="Rehabilitation & therapy",
            reason="Strong fit for physio, occupational therapy, and rehab-clinic roles.",
            role_keyword_boosts=((("physio", "rehab", "therapy", "ergotherapie"), 0.25),),
        ),
        CategorySuggestion(
            label="Emergency / ambulance",
            reason="Strong fit for paramedic, emergency-medicine, and ambulance-service roles.",
            role_keyword_boosts=((("emergency", "paramedic", "rettungsdienst"), 0.25),),
        ),
    ),
)


_DATA = Persona(
    id="data",
    label="Data & analytics",
    description=(
        "Data analyst, data scientist, ML / AI engineer, analytics "
        "engineer, data engineer, BI, and research-science roles "
        "across software, fintech, e-commerce, and applied AI."
    ),
    default_target_roles=(
        "data analyst",
        "data scientist",
        "data engineer",
        "machine learning engineer",
        "analytics engineer",
    ),
    default_industry="Data",
    industry_match_terms=("data", "analytics", "machine learning", "ai", "ml"),
    sector_weights={
        "applied ai / ml": 0.95,
        "b2b saas": 0.9,
        "fintech": 0.9,
        "e-commerce": 0.85,
        "consumer tech": 0.8,
        "research lab": 0.8,
        "marketplace": 0.8,
        "adtech": 0.7,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Applied AI / ML companies",
            reason="Strong fit for ML engineer, MLOps, and research-engineer roles.",
            role_keyword_boosts=((("ml", "machine learning", "mlops", "research"), 0.30),),
        ),
        CategorySuggestion(
            label="Data-platform & analytics tooling",
            reason="Strong fit for data engineer, analytics engineer, and data-platform roles.",
            role_keyword_boosts=((("data engineer", "analytics", "platform", "warehouse"), 0.25),),
        ),
        CategorySuggestion(
            label="In-house data science teams",
            reason="Strong fit for data scientist, BI, and product-analytics roles.",
            role_keyword_boosts=((("data scientist", "bi", "product analytics"), 0.25),),
        ),
        CategorySuggestion(
            label="AI-first product startups",
            reason="Strong fit for applied scientist, foundation-model, and AI-product roles.",
            role_keyword_boosts=((("applied scientist", "foundation", "llm", "rag"), 0.30),),
        ),
    ),
)


_HR = Persona(
    id="hr",
    label="HR & people operations",
    description=(
        "Recruiters, HR business partners, talent acquisition, "
        "compensation, learning & development, DEI, and people-ops "
        "roles across SaaS, finance, healthcare, and large enterprises."
    ),
    default_target_roles=(
        "recruiter",
        "hr business partner",
        "people operations",
        "talent acquisition",
        "compensation analyst",
    ),
    default_industry="People & HR",
    industry_match_terms=("hr", "people", "recruit", "talent", "human resources"),
    sector_weights={
        "b2b saas": 0.85,
        "consulting": 0.8,
        "fintech": 0.8,
        "healthcare provider": 0.8,
        "manufacturing": 0.75,
        "retail / consumer": 0.75,
        "public sector": 0.7,
        "law firm": 0.7,
    },
    category_suggestions=(
        CategorySuggestion(
            label="In-house TA teams (scale-ups)",
            reason="Strong fit for technical recruiter, sourcer, and TA-lead roles.",
            role_keyword_boosts=((("recruiter", "sourcer", "talent"), 0.25),),
        ),
        CategorySuggestion(
            label="HR business partners",
            reason="Strong fit for HRBP, employee-relations, and people-strategy roles.",
            role_keyword_boosts=((("hrbp", "business partner", "employee relations"), 0.25),),
        ),
        CategorySuggestion(
            label="Total rewards / comp",
            reason="Strong fit for compensation analyst and benefits-program roles.",
            role_keyword_boosts=((("compensation", "benefits", "total rewards"), 0.25),),
        ),
        CategorySuggestion(
            label="Learning & development",
            reason="Strong fit for L&D, leadership-development, and DEI roles.",
            role_keyword_boosts=((("learning", "l&d", "dei", "development"), 0.20),),
        ),
    ),
)


_SUPPORT = Persona(
    id="support",
    label="Customer support & success",
    description=(
        "Customer support agents, technical support, customer-success "
        "managers, onboarding specialists, and support-ops roles "
        "across SaaS, fintech, e-commerce, and consumer products."
    ),
    default_target_roles=(
        "customer support",
        "customer success manager",
        "technical support",
        "support engineer",
        "onboarding specialist",
    ),
    default_industry="Customer experience",
    industry_match_terms=("customer", "support", "success", "service", "onboarding"),
    sector_weights={
        "b2b saas": 0.9,
        "fintech": 0.85,
        "consumer tech": 0.8,
        "e-commerce": 0.8,
        "marketplace": 0.8,
        "telecom": 0.7,
        "travel / hospitality": 0.7,
        "healthtech": 0.75,
    },
    category_suggestions=(
        CategorySuggestion(
            label="SaaS customer success",
            reason="Strong fit for CSM, onboarding, and account-success roles.",
            role_keyword_boosts=((("customer success", "csm", "onboarding"), 0.25),),
        ),
        CategorySuggestion(
            label="Tier-2 / technical support",
            reason="Strong fit for technical support, support engineer, and integration roles.",
            role_keyword_boosts=((("support engineer", "tier 2", "integration", "technical support"), 0.25),),
        ),
        CategorySuggestion(
            label="Consumer support hubs",
            reason="Strong fit for customer-care, multi-channel support, and trust-and-safety roles.",
            role_keyword_boosts=((("customer care", "trust", "safety", "moderation"), 0.20),),
        ),
        CategorySuggestion(
            label="Support ops / quality",
            reason="Strong fit for support-ops, QA, and knowledge-base roles.",
            role_keyword_boosts=((("support ops", "qa", "knowledge"), 0.20),),
        ),
    ),
)


_MEDIA = Persona(
    id="media",
    label="Media & journalism",
    description=(
        "Journalists, editors, content producers, video / podcast "
        "producers, and communications professionals across publishers, "
        "broadcasters, in-house comms, and digital media."
    ),
    default_target_roles=(
        "journalist",
        "editor",
        "content producer",
        "communications manager",
        "podcast producer",
    ),
    default_industry="Media & communications",
    industry_match_terms=("media", "journalism", "editor", "communications", "newsroom"),
    sector_weights={
        "publisher / newsroom": 0.95,
        "broadcaster": 0.9,
        "podcast / audio": 0.85,
        "in-house comms": 0.8,
        "digital media": 0.85,
        "pr agency": 0.8,
        "consumer brand": 0.7,
        "non-profit / ngo": 0.7,
    },
    category_suggestions=(
        CategorySuggestion(
            label="Newsrooms & publishers",
            reason="Strong fit for reporter, editor, and beat-writer roles.",
            role_keyword_boosts=((("reporter", "editor", "journalist", "beat"), 0.25),),
        ),
        CategorySuggestion(
            label="Podcast & audio",
            reason="Strong fit for producer, audio-editor, and host roles.",
            role_keyword_boosts=((("producer", "podcast", "audio", "host"), 0.25),),
        ),
        CategorySuggestion(
            label="In-house communications",
            reason="Strong fit for comms manager, internal-comms, and PR roles.",
            role_keyword_boosts=((("comms", "communications", "pr", "press"), 0.25),),
        ),
        CategorySuggestion(
            label="Digital / video media",
            reason="Strong fit for video-producer, social-editor, and digital-newsroom roles.",
            role_keyword_boosts=((("video", "social", "digital", "multimedia"), 0.20),),
        ),
    ),
)


PERSONAS: dict[str, Persona] = {
    persona.id: persona
    for persona in (
        _HEALTHCARE_MANAGEMENT,
        _TECH,
        _MARKETING,
        _FINANCE,
        _PRODUCT_MANAGEMENT,
        _EDUCATION,
        _LEGAL,
        _SALES,
        _DESIGN,
        _OPERATIONS,
        _HEALTHCARE_CLINICAL,
        _DATA,
        _HR,
        _SUPPORT,
        _MEDIA,
    )
}

DEFAULT_PERSONA_ID = "healthcare-management"


def get_persona(persona_id: str | None) -> Persona:
    """Return the persona matching ``persona_id`` or the default."""

    if persona_id and persona_id in PERSONAS:
        return PERSONAS[persona_id]
    return PERSONAS[DEFAULT_PERSONA_ID]


def _persona_search_terms(persona: Persona) -> tuple[str, ...]:
    """Flatten everything we can use as a CV-keyword signal for this persona."""

    terms: list[str] = []
    terms.extend(persona.default_target_roles)
    terms.extend(persona.industry_match_terms)
    for cat in persona.category_suggestions:
        for boosts in cat.role_keyword_boosts:
            keywords, _ = boosts
            terms.extend(keywords)
    # Sector weights aren't keywords per se but their phrasing often appears
    # in CVs (e.g., "fintech", "b2b saas", "publisher / newsroom").
    terms.extend(persona.sector_weights.keys())
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        norm = term.casefold().strip()
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return tuple(unique)


def suggest_persona_from_text(text: str, *, top_k: int = 3) -> list[tuple[str, float]]:
    """Rank personas by how well their search terms hit ``text``.

    Returns up to ``top_k`` ``(persona_id, score)`` pairs, score in [0, 1].
    The score is normalized by the number of search terms in the persona,
    so personas with very long term lists don't dominate just because
    they're verbose. ``score = matched_terms / total_terms`` capped at 1.
    """

    haystack = (text or "").casefold()
    if not haystack.strip():
        return []
    scored: list[tuple[str, float]] = []
    for pid, persona in PERSONAS.items():
        terms = _persona_search_terms(persona)
        if not terms:
            continue
        hits = sum(1 for t in terms if t in haystack)
        score = round(hits / len(terms), 4)
        if score > 0:
            scored.append((pid, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[: max(1, top_k)]


def list_personas_summary() -> list[dict[str, object]]:
    """Return a UI-friendly summary list of every persona."""

    return [
        {
            "id": persona.id,
            "label": persona.label,
            "description": persona.description,
            "defaultTargetRoles": list(persona.default_target_roles),
            "defaultIndustry": persona.default_industry,
        }
        for persona in PERSONAS.values()
    ]
