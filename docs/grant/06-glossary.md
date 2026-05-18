# Glossary

Short reference for German bureaucratic, EU policy, and project-specific terms used throughout `docs/grant/`. Keep this file concise — link to authoritative sources rather than duplicating their content.

---

## German employment and welfare terminology

- **Agentur für Arbeit** — Federal Employment Agency local office. Handles short-term unemployment, job placement, vocational guidance, and Arbeitslosengeld I (unemployment insurance, contribution-based).
- **Anerkennung** — Formal recognition of foreign professional qualifications. Required to practice many regulated professions in Germany (nursing, medicine, engineering, teaching, trades). Process varies by profession and Bundesland.
- **Anerkennung-in-Deutschland.de** — Federal portal for credential-recognition information; run by BIBB (Bundesinstitut für Berufsbildung).
- **Arbeitsagentur** — Common short form for Agentur für Arbeit.
- **Arbeitsamt** — Older colloquial term, often used by migrants; technically the predecessor of Agentur für Arbeit.
- **Aufenthaltstitel** — Residence permit. Different titles grant different work rights.
- **Aufenthaltsgestattung** — Temporary residence permission for asylum seekers.
- **Ausbildung** — Formal vocational training (typically 2–3.5 years, dual-system combining school and on-the-job training).
- **BA / Bundesagentur für Arbeit** — German Federal Employment Agency; the federal-level body.
- **BAMF / Bundesamt für Migration und Flüchtlinge** — Federal Office for Migration and Refugees. Funds migrant-advice services.
- **Berufssprachkurs** — Profession-specific German language course, BAMF-funded.
- **Beratungsstelle** — Advice centre. Generic term for any institutional advice service; often refers to migrant-advice centres (MBE, JMD).
- **Bürgergeld** — Citizens' allowance. The basic welfare payment for long-term unemployed and low-income households. Replaced Arbeitslosengeld II / Hartz IV in January 2023. Administered by Jobcenter.
- **Eingetragener Verein (e.V.)** — Registered non-profit association under German law. Common legal form for civic organisations.
- **EURES** — European Employment Services. EU-wide job-mobility network for EEA + Switzerland.
- **Fachkräfteeinwanderungsgesetz** — Skilled Immigration Act. Legal framework for non-EU skilled-worker immigration, revised in 2023.
- **Fachkräftemangel** — Shortage of skilled workers. The umbrella political and economic term for the labor gap.
- **Familienzusammenführung** — Family reunification (immigration-law procedure).
- **Gesetzliche Krankenversicherung** — Statutory health insurance (the public option; ~90% of residents).
- **Hartz IV** — Colloquial old name for Arbeitslosengeld II; replaced by Bürgergeld in 2023.
- **Impressum** — Mandatory legal-disclosure section required on all German websites under §5 TMG.
- **Integrationskurs** — BAMF-funded integration course (German language + life-in-Germany).
- **IQ Netzwerk / Förderprogramm Integration durch Qualifizierung** — Federal programme supporting recognition and qualification of migrants. ~16 regional networks. Federally funded by BMAS + ESF.
- **JMD / Jugendmigrationsdienst** — Youth Migration Service. Counselling for migrants aged 12–27. BAMF-funded; operated by Caritas, Diakonie, etc.
- **Jobcenter** — Local-level body administering Bürgergeld and long-term unemployment support under SGB II. Exists as either gemeinsame Einrichtung (joint BA + municipality) or zugelassener kommunaler Träger / Optionskommune (municipality only).
- **Lebenslauf** — CV / résumé in German format. Specific structural conventions (chronological, photo optional, no objective statement).
- **MBE / Migrationsberatung für Erwachsene Zuwanderer** — Migration Advice for Adult Immigrants. ~700 service points across Germany. BAMF-funded; operated by Caritas, Diakonie, AWO, Paritätischer, DRK, ZdJ.
- **Optionskommune** — One of 104 municipalities authorised to run their own Jobcenter independently of BA. More procurement autonomy than gemeinsame Einrichtungen.
- **Paritätischer Gesamtverband** — Umbrella organisation of welfare NGOs in Germany.
- **Pflege** — Care / nursing sector. The term covers both Krankenpflege (medical nursing) and Altenpflege (elderly care).
- **Probezeit** — Probation period in a job contract; typically 6 months.
- **SGB II** — Social Code Book II. Governs Bürgergeld and Jobcenter activities.
- **Sozialdaten** — Social data. Personal data held by social-security and welfare agencies; protected under §35 SGB I, a regime stricter than GDPR.
- **TMG / Telemediengesetz** — Telemedia Act. Governs online services in Germany; §5 mandates the Impressum.
- **Triple Win** — Bilateral programme of GIZ + BA recruiting healthcare workers from Bosnia, Philippines, Vietnam, Tunisia, Indonesia, Mexico, India.

---

## EU policy and regulatory terminology

- **AI Act / Verordnung (EU) 2024/1689** — EU regulation on artificial intelligence. Entered into force 1 August 2024; high-risk AI obligations applicable from **2 August 2026**.
- **AI Act Annex III §4** — Employment-related AI systems classified as high-risk: recruitment, candidate filtering, fit scoring, work-relationship decisions, performance monitoring.
- **DPIA / Data Protection Impact Assessment** — Required under GDPR Article 35 for high-risk processing. Required under AI Act for high-risk AI systems.
- **EDC / European Digital Credentials** — EU framework for digitally-signed academic and professional credentials.
- **eIDAS** — EU regulation on electronic identification, authentication, and trust services.
- **ESCO** — European Skills, Competences, Qualifications and Occupations. EU's open taxonomy (3,000+ occupations, 13,000+ skills). https://esco.ec.europa.eu
- **EURES schema** — Data formats used by EURES for cross-border job exchange.
- **EU AI Act high-risk AI obligations** — risk management, data governance, technical documentation, record-keeping, transparency to users, human oversight, accuracy + robustness + cybersecurity. Article 6 + Annex III.
- **GDPR** — General Data Protection Regulation, EU 2016/679.
- **NGI / Next Generation Internet** — EU initiative for human-centric internet, run by DG CONNECT.
- **NGI0 / NGI Zero** — The umbrella of NLnet-administered funds under NGI.
- **PES Network / European Network of Public Employment Services** — Coordination body for PES across EU member states.
- **Sovereign Tech Fund (STF)** — German federal fund for critical open-source infrastructure. Run by SPRIND.

---

## Project-specific and technical terminology

- **BYO-AI** — Bring Your Own AI provider. User-supplied API key or local model.
- **CLA / Contributor License Agreement** — Legal document signed by contributors granting the project rights to incorporate their contributions.
- **Civic Agent** — A conversational AI agent serving a civic-life domain (employment, housing, healthcare, residency).
- **Civic Commons** — Open-source infrastructure built and maintained for public benefit, distinct from commercial SaaS.
- **Commons Conservancy / The Commons Conservancy** — Dutch stichting hosting open-source projects as multi-tenant legal infrastructure. https://commonsconservancy.org
- **Cost-saving doctrine** — Project design principle: every feature must reduce institutional operational costs while improving outcomes. See `08-cost-saving-doctrine.md`.
- **DirectJob Scout** — The project. The first reference implementation of the civic-employment-agent pattern.
- **Journey state machine** — The 12-phase deterministic conversation flow that drives a job-search session from discovery to drafted application.
- **MCP / Model Context Protocol** — Open protocol for AI applications to expose tools, resources, and prompts to AI clients. https://modelcontextprotocol.io
- **MCP tool** — A callable function exposed by an MCP server with a JSON Schema for its inputs and outputs.
- **NGO** — Non-Governmental Organisation. In Germany, often "Verein" or "gemeinnütziger Verein" (charitable association).
- **Persona panel** — The set of seven fictional users used in proposal narrative, demos, and documentation: the five most-acute migrant personas (Aïcha, Yusuf, Olga, Mahmoud, Maria) plus the two wider-friction-class personas (Käthe, Tobias) added per Decision 21. See `07-personas.md`.

---

## Acronyms quick reference

| Acronym | Expansion | Domain |
|---|---|---|
| AGG | Allgemeines Gleichbehandlungsgesetz | DE / anti-discrimination |
| BA | Bundesagentur für Arbeit | DE / federal employment |
| BAMF | Bundesamt für Migration und Flüchtlinge | DE / federal migration |
| BMAS | Bundesministerium für Arbeit und Soziales | DE / federal labor ministry |
| BMG | Bundesministerium für Gesundheit | DE / federal health ministry |
| BSI | Bundesamt für Sicherheit in der Informationstechnik | DE / federal cybersecurity |
| CLA | Contributor License Agreement | OSS governance |
| DPIA | Data Protection Impact Assessment | EU / GDPR |
| EAA | European Accessibility Act | EU / accessibility |
| ESCO | European Skills, Competences, Qualifications and Occupations | EU / taxonomy |
| EURES | European Employment Services | EU / job mobility |
| GDPR | General Data Protection Regulation (EU 2016/679) | EU / data protection |
| IQ | Integration durch Qualifizierung | DE / federal programme |
| JMD | Jugendmigrationsdienst | DE / youth migration service |
| MBE | Migrationsberatung für Erwachsene Zuwanderer | DE / adult migrant advice |
| MCP | Model Context Protocol | OSS / AI protocol |
| NGI | Next Generation Internet | EU programme |
| NGI0 | NGI Zero family of funds | EU / NLnet |
| PES | Public Employment Service | EU / employment policy |
| SCOP | Société coopérative et participative | FR / co-op legal form |
| SGB | Sozialgesetzbuch | DE / social code |
| STF | Sovereign Tech Fund | DE / federal OSS funding |
| TMG | Telemediengesetz | DE / telemedia law |
| WCAG | Web Content Accessibility Guidelines | W3C / accessibility |
