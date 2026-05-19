# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

from dataclasses import asdict, dataclass

from .personas import DEFAULT_PERSONA_ID, get_persona


@dataclass(frozen=True)
class CuratedCompany:
    name: str
    website_url: str
    career_page_url: str
    sector: str
    location_hint: str
    role_families: tuple[str, ...]
    relevance_reason: str
    personas: tuple[str, ...] = ("healthcare-management",)


CURATED_COMPANIES: tuple[CuratedCompany, ...] = (
    # Healthcare management seeds
    CuratedCompany(
        name="Charite - Universitaetsmedizin Berlin",
        website_url="https://www.charite.de",
        career_page_url="https://karriere.charite.de",
        sector="University hospital",
        location_hint="Berlin",
        role_families=(
            "public health",
            "health services research",
            "quality/process management",
            "project management",
        ),
        relevance_reason="Large university hospital with management, research, quality, and public-sector healthcare roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="Vivantes",
        website_url="https://www.vivantes.de",
        career_page_url="https://karriere.vivantes.de",
        sector="Hospital / clinic group",
        location_hint="Berlin",
        role_families=("project management", "quality/process management", "digital health"),
        relevance_reason="Large Berlin healthcare network with hospital operations, project, administration, and digital transformation roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="Helios",
        website_url="https://www.helios-gesundheit.de",
        career_page_url="https://www.helios-gesundheit.de/karriere/alle-jobs/",
        sector="Hospital / clinic group",
        location_hint="Germany",
        role_families=(
            "project management",
            "quality/process management",
            "controlling",
            "management trainee",
        ),
        relevance_reason="Major private hospital group with management, controlling, trainee, and operational healthcare roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="Techniker Krankenkasse",
        website_url="https://www.tk.de",
        career_page_url="https://www.tk.de/karriere",
        sector="Statutory health insurer",
        location_hint="Germany",
        role_families=("digital health", "public health", "project management", "health insurance"),
        relevance_reason="Large statutory health insurer with digital health, prevention, product, and policy-adjacent roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="BARMER",
        website_url="https://www.barmer.de",
        career_page_url="https://jobs.barmer.de/",
        sector="Statutory health insurer",
        location_hint="Germany",
        role_families=("digital health", "public health", "health insurance", "project management"),
        relevance_reason="Large statutory health insurer with digital care, prevention, and healthcare administration roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="GKV-Spitzenverband",
        website_url="https://www.gkv-spitzenverband.de",
        career_page_url="https://www.gkv-spitzenverband.de/gkv_spitzenverband/karriere/karriere.jsp",
        sector="Health policy organization",
        location_hint="Berlin / Bonn",
        role_families=("health policy", "public health", "digital health", "project management"),
        relevance_reason="Central statutory health-insurance association with policy, digitalization, prevention, and project roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="Siemens Healthineers",
        website_url="https://www.siemens-healthineers.com",
        career_page_url="https://www.siemens-healthineers.com/de/careers",
        sector="MedTech",
        location_hint="Germany / global",
        role_families=("medtech", "digital health", "healthcare IT", "project management"),
        relevance_reason="Major MedTech company with healthcare technology, project, product, and implementation roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="Roche Deutschland",
        website_url="https://www.roche.de",
        career_page_url="https://careers.roche.com/de/de",
        sector="Pharma / diagnostics",
        location_hint="Germany",
        role_families=("market access", "public affairs", "digital health", "pharma"),
        relevance_reason="Pharma and diagnostics employer with market access, healthcare system, digital, and commercial roles.",
        personas=("healthcare-management",),
    ),
    CuratedCompany(
        name="IQVIA Germany",
        website_url="https://www.iqvia.com/de-de",
        career_page_url="https://www.iqvia.com/de-de/locations/germany/career-opportunities",
        sector="Healthcare consulting / data",
        location_hint="Germany",
        role_families=(
            "healthcare consulting",
            "market access",
            "health services research",
            "analytics",
        ),
        relevance_reason="Healthcare data and consulting employer with analyst, consulting, market access, and real-world evidence roles.",
        personas=("healthcare-management",),
    ),
    # Tech persona seeds
    CuratedCompany(
        name="Datadog",
        website_url="https://www.datadoghq.com",
        career_page_url="https://www.datadoghq.com/careers/",
        sector="SaaS / Cloud infrastructure",
        location_hint="Paris / Dublin / Berlin / remote",
        role_families=("backend", "frontend", "platform", "sre", "observability"),
        relevance_reason="Observability platform with platform, backend, frontend, and SRE engineering roles across Europe.",
        personas=("tech", "product-management"),
    ),
    CuratedCompany(
        name="GitHub",
        website_url="https://github.com",
        career_page_url="https://github.com/about/careers",
        sector="Developer tools",
        location_hint="Remote (EMEA)",
        role_families=("backend", "frontend", "platform", "developer experience"),
        relevance_reason="Developer-tools company with strong remote-EMEA hiring for engineering and product.",
        personas=("tech", "product-management"),
    ),
    CuratedCompany(
        name="Vercel",
        website_url="https://vercel.com",
        career_page_url="https://vercel.com/careers",
        sector="Developer tools / Cloud",
        location_hint="Remote (EU) / Berlin",
        role_families=("frontend", "platform", "developer experience"),
        relevance_reason="Frontend cloud platform with remote engineering and product roles in the EU.",
        personas=("tech", "product-management"),
    ),
    CuratedCompany(
        name="Hugging Face",
        website_url="https://huggingface.co",
        career_page_url="https://apply.workable.com/huggingface/",
        sector="AI / ML",
        location_hint="Paris / remote",
        role_families=("ml engineering", "research engineer", "platform"),
        relevance_reason="AI/ML platform with ML engineering, applied research, and platform roles, mostly Paris and remote.",
        personas=("tech", "product-management"),
    ),
    CuratedCompany(
        name="Mistral AI",
        website_url="https://mistral.ai",
        career_page_url="https://mistral.ai/careers/",
        sector="AI / ML",
        location_hint="Paris",
        role_families=("ml engineering", "research", "infra"),
        relevance_reason="European LLM lab with research, ML engineering, and infra roles in Paris.",
        personas=("tech", "product-management"),
    ),
    CuratedCompany(
        name="Celonis",
        website_url="https://www.celonis.com",
        career_page_url="https://www.celonis.com/careers/",
        sector="B2B SaaS / process mining",
        location_hint="Munich / Berlin",
        role_families=("backend", "data engineering", "ml engineering", "platform"),
        relevance_reason="German process-mining unicorn with engineering, data, and ML roles in Munich and Berlin.",
        personas=("tech", "product-management"),
    ),
    CuratedCompany(
        name="N26",
        website_url="https://n26.com",
        career_page_url="https://n26.com/en/careers",
        sector="Fintech / neobank",
        location_hint="Berlin / Barcelona",
        role_families=("backend", "mobile", "data", "product"),
        relevance_reason="Berlin-based neobank with backend, mobile, data, and product roles.",
        personas=("tech", "product-management", "finance"),
    ),
    CuratedCompany(
        name="Personio",
        website_url="https://www.personio.com",
        career_page_url="https://www.personio.com/careers/",
        sector="B2B SaaS / HR-tech",
        location_hint="Munich / Madrid / Dublin",
        role_families=("backend", "frontend", "product", "platform"),
        relevance_reason="European HR-tech SaaS with engineering, platform, and product roles.",
        personas=("tech", "product-management", "marketing"),
    ),
    CuratedCompany(
        name="GetYourGuide",
        website_url="https://www.getyourguide.com",
        career_page_url="https://careers.getyourguide.com",
        sector="Marketplace / travel",
        location_hint="Berlin",
        role_families=("backend", "data", "product", "growth"),
        relevance_reason="Berlin travel marketplace with engineering, data, product, and growth roles.",
        personas=("tech", "product-management", "marketing"),
    ),
    # Marketing persona seeds
    CuratedCompany(
        name="Zalando",
        website_url="https://corporate.zalando.com",
        career_page_url="https://jobs.zalando.com",
        sector="E-commerce / marketplace",
        location_hint="Berlin",
        role_families=("brand", "performance marketing", "crm", "content", "merchandising"),
        relevance_reason="Europe's largest fashion marketplace with brand, performance, CRM, and content marketing roles.",
        personas=("marketing", "tech", "product-management"),
    ),
    CuratedCompany(
        name="HelloFresh",
        website_url="https://www.hellofreshgroup.com",
        career_page_url="https://careers.hellofresh.com",
        sector="DTC / food",
        location_hint="Berlin",
        role_families=("performance marketing", "crm", "growth", "brand"),
        relevance_reason="Berlin-based DTC food brand with strong performance marketing, growth, and CRM functions.",
        personas=("marketing", "product-management"),
    ),
    CuratedCompany(
        name="About You",
        website_url="https://corporate.aboutyou.de",
        career_page_url="https://corporate.aboutyou.de/de/career",
        sector="E-commerce / fashion",
        location_hint="Hamburg",
        role_families=("brand", "performance marketing", "crm", "content"),
        relevance_reason="Hamburg-based fashion e-commerce with brand, performance, content, and CRM roles.",
        personas=("marketing", "tech"),
    ),
    CuratedCompany(
        name="HubSpot",
        website_url="https://www.hubspot.com",
        career_page_url="https://www.hubspot.com/careers",
        sector="B2B SaaS / marketing",
        location_hint="Dublin / Berlin / remote",
        role_families=("product marketing", "demand gen", "content", "seo"),
        relevance_reason="Inbound marketing SaaS with product marketing, content, demand-gen, and SEO roles in EMEA.",
        personas=("marketing", "tech", "product-management"),
    ),
    CuratedCompany(
        name="Spotify",
        website_url="https://www.lifeatspotify.com",
        career_page_url="https://www.lifeatspotify.com/jobs",
        sector="Media / streaming",
        location_hint="Stockholm / London / Berlin",
        role_families=("brand", "growth", "product marketing", "partnerships"),
        relevance_reason="European media platform with brand, growth, product marketing, and partnership roles.",
        personas=("marketing", "tech", "product-management"),
    ),
    CuratedCompany(
        name="Klarna",
        website_url="https://www.klarna.com",
        career_page_url="https://www.klarna.com/careers/",
        sector="Fintech / payments",
        location_hint="Stockholm / Berlin",
        role_families=("brand", "performance marketing", "growth", "product marketing"),
        relevance_reason="Fintech with brand, growth, performance, and product-marketing roles across Europe.",
        personas=("marketing", "finance", "tech", "product-management"),
    ),
    # Finance persona seeds
    CuratedCompany(
        name="Deutsche Bank",
        website_url="https://www.db.com",
        career_page_url="https://careers.db.com",
        sector="Universal bank",
        location_hint="Frankfurt / Germany",
        role_families=("analyst", "fp&a", "risk", "audit", "treasury", "m&a"),
        relevance_reason="Germany's largest bank with analyst, FP&A, risk, audit, treasury, and M&A roles.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="Commerzbank",
        website_url="https://www.commerzbank.de",
        career_page_url="https://www.commerzbank.de/karriere",
        sector="Universal bank",
        location_hint="Frankfurt / Germany",
        role_families=("analyst", "fp&a", "risk", "audit", "treasury"),
        relevance_reason="German universal bank with analyst, controlling, risk, and corporate-finance roles.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="Allianz",
        website_url="https://www.allianz.com",
        career_page_url="https://careers.allianz.com",
        sector="Insurance",
        location_hint="Munich / global",
        role_families=("actuarial", "risk", "controlling", "audit", "fp&a"),
        relevance_reason="Largest European insurer with actuarial, risk, controlling, and audit roles.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="Munich Re",
        website_url="https://www.munichre.com",
        career_page_url="https://www.munichre.com/en/company/career.html",
        sector="Reinsurance",
        location_hint="Munich",
        role_families=("actuarial", "risk", "underwriting", "fp&a"),
        relevance_reason="Reinsurer with actuarial, risk, underwriting, and finance roles in Munich.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="KPMG Germany",
        website_url="https://kpmg.com/de",
        career_page_url="https://kpmg.com/de/de/home/karriere.html",
        sector="Audit / advisory",
        location_hint="Germany",
        role_families=("audit", "tax", "transaction services", "advisory"),
        relevance_reason="Big-4 firm with audit, tax, transaction-services, and advisory roles across Germany.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="EY Germany",
        website_url="https://www.ey.com/de_de",
        career_page_url="https://www.ey.com/de_de/careers",
        sector="Audit / advisory",
        location_hint="Germany",
        role_families=("audit", "tax", "transaction services", "advisory"),
        relevance_reason="Big-4 firm with audit, tax, transaction-services, and consulting roles across Germany.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="DWS",
        website_url="https://www.dws.com",
        career_page_url="https://careers.dws.com",
        sector="Asset management",
        location_hint="Frankfurt / global",
        role_families=("investment analyst", "portfolio operations", "risk", "fp&a"),
        relevance_reason="Asset manager with investment, portfolio, risk, and finance roles.",
        personas=("finance",),
    ),
    CuratedCompany(
        name="Trade Republic",
        website_url="https://traderepublic.com",
        career_page_url="https://traderepublic.com/careers",
        sector="Fintech / brokerage",
        location_hint="Berlin",
        role_families=("treasury", "risk", "compliance", "controlling", "product"),
        relevance_reason="Berlin neobroker with treasury, risk, compliance, and finance roles, plus product/engineering.",
        personas=("finance", "tech", "product-management"),
    ),
    # Product-management persona seeds (additional ones beyond cross-listed)
    CuratedCompany(
        name="Stripe",
        website_url="https://stripe.com",
        career_page_url="https://stripe.com/jobs",
        sector="Fintech / payments",
        location_hint="Dublin / London / remote",
        role_families=("backend", "platform", "product", "data"),
        relevance_reason="Payments platform with engineering, platform, and product roles in EMEA.",
        personas=("tech", "product-management", "finance"),
    ),
    CuratedCompany(
        name="Doctolib",
        website_url="https://www.doctolib.de",
        career_page_url="https://careers.doctolib.de/",
        sector="Digital Health",
        location_hint="Berlin / Paris",
        role_families=("backend", "frontend", "product", "growth"),
        relevance_reason="European e-health platform with engineering and product roles in Berlin, Paris, and remote.",
        personas=("tech", "product-management", "healthcare-management"),
    ),
    # Education persona seeds
    CuratedCompany(
        name="Coursera",
        website_url="https://www.coursera.org",
        career_page_url="https://about.coursera.org/careers",
        sector="EdTech",
        location_hint="Remote / global",
        role_families=("curriculum", "content design", "product", "engineering"),
        relevance_reason="EdTech platform with curriculum, content-design, product, and engineering roles.",
        personas=("education", "tech", "product-management"),
    ),
    CuratedCompany(
        name="Babbel",
        website_url="https://www.babbel.com",
        career_page_url="https://careers.babbel.com",
        sector="EdTech",
        location_hint="Berlin",
        role_families=("curriculum", "content design", "language teacher", "product"),
        relevance_reason="Berlin-based language-learning EdTech with curriculum, content, and product roles.",
        personas=("education", "tech", "product-management"),
    ),
    CuratedCompany(
        name="GoStudent",
        website_url="https://www.gostudent.org",
        career_page_url="https://www.gostudent.org/careers",
        sector="EdTech",
        location_hint="Vienna / DACH",
        role_families=("tutoring", "curriculum", "operations", "engineering"),
        relevance_reason="DACH tutoring platform with curriculum, ops, and tutor-facing roles.",
        personas=("education", "operations"),
    ),
    CuratedCompany(
        name="Max-Planck-Gesellschaft",
        website_url="https://www.mpg.de",
        career_page_url="https://www.mpg.de/jobboard",
        sector="Research institute",
        location_hint="Germany",
        role_families=("research associate", "postdoc", "wissenschaftlicher mitarbeiter"),
        relevance_reason="German research network with postdoc, research-associate, and academic-coordinator roles.",
        personas=("education",),
    ),
    # Legal persona seeds
    CuratedCompany(
        name="Freshfields Bruckhaus Deringer",
        website_url="https://www.freshfields.com",
        career_page_url="https://careers.freshfields.com",
        sector="Law firm",
        location_hint="Frankfurt / global",
        role_families=("associate", "paralegal", "of counsel", "trainee"),
        relevance_reason="Magic-circle law firm with associate, trainee, and counsel-track roles across DE / EU.",
        personas=("legal",),
    ),
    CuratedCompany(
        name="Hengeler Mueller",
        website_url="https://www.hengeler.com",
        career_page_url="https://www.hengeler.com/de/karriere",
        sector="Law firm",
        location_hint="Germany",
        role_families=("associate", "trainee", "rechtsanwalt"),
        relevance_reason="Top-tier German law firm with associate, referendar, and trainee roles.",
        personas=("legal",),
    ),
    CuratedCompany(
        name="Lawhive",
        website_url="https://lawhive.co.uk",
        career_page_url="https://lawhive.co.uk/careers",
        sector="Legal tech",
        location_hint="London / remote",
        role_families=("legal ops", "contracts", "engineering", "product"),
        relevance_reason="UK legal-tech with legal-ops, contracts, engineering, and product roles.",
        personas=("legal", "tech", "product-management"),
    ),
    # Sales persona seeds
    CuratedCompany(
        name="Salesforce",
        website_url="https://www.salesforce.com",
        career_page_url="https://www.salesforce.com/company/careers/",
        sector="Enterprise software",
        location_hint="Global / EMEA",
        role_families=("account executive", "sdr", "sales engineer", "partnerships"),
        relevance_reason="Global enterprise SaaS with AE, SDR, sales-engineer, and partner roles.",
        personas=("sales", "tech", "product-management"),
    ),
    CuratedCompany(
        name="HubSpot Sales",
        website_url="https://www.hubspot.com",
        career_page_url="https://www.hubspot.com/careers",
        sector="B2B SaaS",
        location_hint="Dublin / Berlin / remote",
        role_families=("account executive", "sdr", "partnerships", "ae"),
        relevance_reason="Inbound CRM SaaS with EMEA AE, SDR, and partnerships hiring.",
        personas=("sales", "marketing", "product-management"),
    ),
    CuratedCompany(
        name="Personio Sales",
        website_url="https://www.personio.com",
        career_page_url="https://www.personio.com/careers/?team=Sales",
        sector="B2B SaaS / HR-tech",
        location_hint="Munich / Madrid / Dublin",
        role_families=("account executive", "sdr", "key account manager"),
        relevance_reason="HR-tech SaaS with strong sales hiring across DACH and EU.",
        personas=("sales", "tech"),
    ),
    # Design persona seeds
    CuratedCompany(
        name="Figma",
        website_url="https://www.figma.com",
        career_page_url="https://www.figma.com/careers/",
        sector="Design / B2B SaaS",
        location_hint="Remote / global",
        role_families=("product designer", "design system", "ux", "research"),
        relevance_reason="Design-tool company with strong product-designer + design-system hiring.",
        personas=("design", "tech", "product-management"),
    ),
    CuratedCompany(
        name="Edenspiekermann",
        website_url="https://www.edenspiekermann.com",
        career_page_url="https://www.edenspiekermann.com/jobs",
        sector="Design agency",
        location_hint="Berlin",
        role_families=("art direction", "senior designer", "creative"),
        relevance_reason="Berlin design agency with senior-designer + art-direction + creative-lead roles.",
        personas=("design",),
    ),
    CuratedCompany(
        name="IDEO",
        website_url="https://www.ideo.com",
        career_page_url="https://www.ideo.com/careers",
        sector="Design consultancy",
        location_hint="Global",
        role_families=("designer", "research", "innovation strategy"),
        relevance_reason="Global design consultancy with designer, research, and innovation roles.",
        personas=("design",),
    ),
    # Operations persona seeds
    CuratedCompany(
        name="DHL",
        website_url="https://www.dhl.com",
        career_page_url="https://careers.dhl.com",
        sector="Logistics / freight",
        location_hint="Bonn / global",
        role_families=("logistics", "supply chain", "fleet", "warehouse"),
        relevance_reason="Global logistics network with logistics, supply-chain, and warehouse roles.",
        personas=("operations",),
    ),
    CuratedCompany(
        name="Flink",
        website_url="https://www.goflink.com",
        career_page_url="https://www.goflink.com/de-de/careers/",
        sector="Q-commerce / grocery",
        location_hint="Berlin",
        role_families=("operations manager", "fulfillment", "supply chain"),
        relevance_reason="Berlin q-commerce operator with operations, fulfillment, and supply-chain roles.",
        personas=("operations", "marketing"),
    ),
    CuratedCompany(
        name="Gorillas / Getir",
        website_url="https://getir.com",
        career_page_url="https://getir.com/careers",
        sector="Q-commerce / delivery",
        location_hint="Berlin / Istanbul",
        role_families=("operations", "logistics", "fleet"),
        relevance_reason="Q-commerce delivery network with operations, fleet, and logistics roles.",
        personas=("operations",),
    ),
    CuratedCompany(
        name="Maersk",
        website_url="https://www.maersk.com",
        career_page_url="https://www.maersk.com/careers",
        sector="Shipping / logistics",
        location_hint="Copenhagen / global",
        role_families=("supply chain", "logistics", "shipping ops"),
        relevance_reason="Global shipping line with supply-chain, ops, and logistics roles.",
        personas=("operations",),
    ),
    # Healthcare-clinical persona seeds (extends healthcare-management roster)
    CuratedCompany(
        name="Vivantes (clinical)",
        website_url="https://www.vivantes.de",
        career_page_url="https://karriere.vivantes.de/pflege",
        sector="Hospital / clinic group",
        location_hint="Berlin",
        role_families=("krankenpfleger", "pflegefachkraft", "physiotherapist", "facharzt"),
        relevance_reason="Berlin hospital network with nursing, physician, and therapist roles.",
        personas=("healthcare-clinical",),
    ),
    CuratedCompany(
        name="Helios Kliniken (clinical)",
        website_url="https://www.helios-gesundheit.de",
        career_page_url="https://www.helios-gesundheit.de/karriere/medizinisches-personal/",
        sector="Hospital / clinic group",
        location_hint="Germany",
        role_families=("krankenpfleger", "pflegefachkraft", "facharzt", "anästhesist"),
        relevance_reason="National hospital chain with nursing, physician, and clinical-leadership roles.",
        personas=("healthcare-clinical",),
    ),
    CuratedCompany(
        name="Asklepios (clinical)",
        website_url="https://www.asklepios.com",
        career_page_url="https://karriere.asklepios.com/pflege",
        sector="Hospital / clinic group",
        location_hint="Germany",
        role_families=("krankenpfleger", "altenpfleger", "physiotherapist"),
        relevance_reason="Major German clinic group with nursing, eldercare, and therapist roles.",
        personas=("healthcare-clinical",),
    ),
    CuratedCompany(
        name="Charité (clinical)",
        website_url="https://www.charite.de",
        career_page_url="https://karriere.charite.de/pflege",
        sector="University hospital",
        location_hint="Berlin",
        role_families=("krankenpfleger", "pflegefachkraft", "facharzt", "research nurse"),
        relevance_reason="Berlin's flagship university hospital with all clinical professions.",
        personas=("healthcare-clinical",),
    ),
    # Data persona seeds
    CuratedCompany(
        name="DeepL",
        website_url="https://www.deepl.com",
        career_page_url="https://www.deepl.com/careers",
        sector="Applied AI / ML",
        location_hint="Cologne / Berlin",
        role_families=("ml engineer", "research engineer", "data scientist"),
        relevance_reason="ML / NLP scale-up with data-science, MLOps, and applied-research roles.",
        personas=("data", "tech"),
    ),
    CuratedCompany(
        name="Aleph Alpha",
        website_url="https://aleph-alpha.com",
        career_page_url="https://aleph-alpha.com/careers/",
        sector="Applied AI / ML",
        location_hint="Heidelberg",
        role_families=("research scientist", "ml engineer", "applied scientist"),
        relevance_reason="Foundation-model lab building European LLMs; broad applied-science roster.",
        personas=("data",),
    ),
    CuratedCompany(
        name="Hugging Face",
        website_url="https://huggingface.co",
        career_page_url="https://apply.workable.com/huggingface/",
        sector="Applied AI / ML",
        location_hint="Remote",
        role_families=("ml engineer", "research engineer", "open-source"),
        relevance_reason="Open-source ML hub with research, ML-engineering, and platform-engineering roles.",
        personas=("data", "tech"),
    ),
    CuratedCompany(
        name="N26 Data",
        website_url="https://n26.com",
        career_page_url="https://n26.com/en/careers",
        sector="Fintech",
        location_hint="Berlin",
        role_families=("data analyst", "data scientist", "analytics engineer"),
        relevance_reason="Mobile-banking scale-up with sizable data + analytics teams.",
        personas=("data", "finance"),
    ),
    # HR / people-ops persona seeds
    CuratedCompany(
        name="Personio (People)",
        website_url="https://www.personio.com",
        career_page_url="https://www.personio.com/about/jobs/",
        sector="HR SaaS",
        location_hint="Munich",
        role_families=("recruiter", "people partner", "people ops"),
        relevance_reason="HR-tech vendor that hires aggressively for its own people-ops + TA functions.",
        personas=("hr",),
    ),
    CuratedCompany(
        name="HeyJobs",
        website_url="https://www.heyjobs.co",
        career_page_url="https://www.heyjobs.co/de-de/about/karriere",
        sector="HR / recruitment marketplace",
        location_hint="Berlin",
        role_families=("recruiter", "talent acquisition", "people ops"),
        relevance_reason="Recruitment-marketplace headquarters in Berlin with broad TA + people-ops roles.",
        personas=("hr",),
    ),
    CuratedCompany(
        name="Workday EMEA",
        website_url="https://www.workday.com",
        career_page_url="https://www.workday.com/en-us/company/careers.html",
        sector="HR SaaS",
        location_hint="EMEA",
        role_families=("hrbp", "compensation", "talent partner"),
        relevance_reason="Enterprise HR-platform vendor; large EMEA HR + TA roster.",
        personas=("hr",),
    ),
    CuratedCompany(
        name="SAP People",
        website_url="https://www.sap.com",
        career_page_url="https://jobs.sap.com",
        sector="Enterprise SaaS",
        location_hint="Walldorf / EMEA",
        role_families=("hrbp", "talent acquisition", "learning & development"),
        relevance_reason="Largest German employer for HR / people-ops careers in tech.",
        personas=("hr", "tech"),
    ),
    # Customer support / success persona seeds
    CuratedCompany(
        name="Zendesk EMEA",
        website_url="https://www.zendesk.com",
        career_page_url="https://jobs.zendesk.com",
        sector="B2B SaaS (CX)",
        location_hint="Dublin / Berlin",
        role_families=("customer success", "support engineer", "csm"),
        relevance_reason="Customer-experience SaaS with first-party CSM, onboarding, and support roles.",
        personas=("support",),
    ),
    CuratedCompany(
        name="Stripe Support",
        website_url="https://stripe.com",
        career_page_url="https://stripe.com/jobs/search?teams=Customer+Operations",
        sector="Fintech",
        location_hint="Dublin / Berlin / Remote",
        role_families=("technical support", "customer ops", "trust & safety"),
        relevance_reason="Payments platform with technical-support, dispute-ops, and trust-and-safety teams.",
        personas=("support", "finance"),
    ),
    CuratedCompany(
        name="HubSpot Customer Success",
        website_url="https://www.hubspot.com",
        career_page_url="https://www.hubspot.com/careers",
        sector="B2B SaaS",
        location_hint="Dublin / Berlin",
        role_families=("customer success", "onboarding specialist", "csm"),
        relevance_reason="CRM SaaS with explicit CSM, onboarding, and education-services roles in EMEA.",
        personas=("support", "marketing"),
    ),
    CuratedCompany(
        name="GetYourGuide Support",
        website_url="https://careers.getyourguide.com",
        career_page_url="https://careers.getyourguide.com",
        sector="Travel / marketplace",
        location_hint="Berlin",
        role_families=("customer care", "trust & safety", "support ops"),
        relevance_reason="Travel marketplace with multilingual customer-care + trust-and-safety roles.",
        personas=("support",),
    ),
    # Media / journalism persona seeds
    CuratedCompany(
        name="Der Spiegel",
        website_url="https://www.spiegel.de",
        career_page_url="https://www.spiegel-jobs.de",
        sector="Publisher / newsroom",
        location_hint="Hamburg / Berlin",
        role_families=("journalist", "editor", "video producer"),
        relevance_reason="Major German news magazine with reporters, editors, and video-newsroom roles.",
        personas=("media",),
    ),
    CuratedCompany(
        name="Axel Springer",
        website_url="https://www.axelspringer.com",
        career_page_url="https://www.axelspringer.com/en/career",
        sector="Publisher / newsroom",
        location_hint="Berlin",
        role_families=("journalist", "editor", "digital editor"),
        relevance_reason="Pan-European publisher group covering BILD, Welt, Politico, and Insider.",
        personas=("media",),
    ),
    CuratedCompany(
        name="Deutsche Welle",
        website_url="https://www.dw.com",
        career_page_url="https://www.dw.com/en/jobs-and-traineeships/s-31373",
        sector="Broadcaster",
        location_hint="Bonn / Berlin",
        role_families=("journalist", "editor", "audio producer"),
        relevance_reason="International broadcaster with multilingual journalism + production roles.",
        personas=("media",),
    ),
    CuratedCompany(
        name="Edition F",
        website_url="https://editionf.com",
        career_page_url="https://editionf.com/jobs/",
        sector="Digital media",
        location_hint="Berlin",
        role_families=("editor", "content producer", "social editor"),
        relevance_reason="Digital-media outlet with newsroom + community-led content roles.",
        personas=("media",),
    ),
)


def suggest_curated_companies(
    target_roles: list[str],
    industry: str,
    location: str | None,
    limit: int = 8,
    *,
    persona_id: str | None = None,
) -> list[dict[str, object]]:
    persona = get_persona(persona_id or DEFAULT_PERSONA_ID)
    role_text = " ".join(target_roles).casefold()
    industry_text = industry.casefold()
    location_text = (location or "").casefold()
    suggestions: list[dict[str, object]] = []

    matching = [c for c in CURATED_COMPANIES if persona.id in c.personas]
    # Fall back to all curated entries if a persona has no seeds yet —
    # rare, but avoids returning an empty list mid-rollout.
    if not matching:
        matching = list(CURATED_COMPANIES)

    for company in matching:
        score = 0.45
        sector_text = company.sector.casefold()
        family_text = " ".join(company.role_families).casefold()
        if any(term in industry_text for term in persona.industry_match_terms):
            score += 0.10
        # Generic role-keyword bonus across personas.
        for term in (
            "digital health",
            "public health",
            "market access",
            "public affairs",
            "project",
            "quality",
            "process",
            "consulting",
            "analytics",
            "policy",
            "backend",
            "frontend",
            "platform",
            "sre",
            "ml",
            "data",
            "security",
            "product",
            "growth",
            "brand",
            "performance",
            "content",
            "seo",
            "crm",
            "audit",
            "risk",
            "actuarial",
            "controlling",
            "treasury",
            "fp&a",
        ):
            if term in role_text and term in family_text:
                score += 0.12
        if location_text and location_text in company.location_hint.casefold():
            score += 0.10
        # Persona-specific role-to-sector boosts.
        for role_terms, sector_terms, boost in persona.role_to_sector_boosts:
            if any(term in role_text for term in role_terms) and any(
                term in sector_text for term in sector_terms
            ):
                score += boost
        # Legacy healthcare-specific boosts retained for back-compat.
        if (
            any(term in role_text for term in ("insurance", "krankenkasse", "payer"))
            and "insurer" in sector_text
        ):
            score += 0.15
        if "medtech" in role_text and "medtech" in sector_text:
            score += 0.15
        if "pharma" in role_text and "pharma" in sector_text:
            score += 0.15

        payload = asdict(company)
        payload.pop("personas", None)
        payload.update(
            {
                "type": "company",
                "relevanceScore": min(round(score, 2), 1.0),
                "relevanceReason": company.relevance_reason,
                "watchEnabled": True,
            }
        )
        suggestions.append(payload)

    return sorted(suggestions, key=lambda item: item["relevanceScore"], reverse=True)[:limit]
