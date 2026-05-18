# Personas

The DirectJob Scout panel of personas. Used in proposal narrative, demos, screenshots, public materials, and design conversations. **Every public-facing artifact references at least one of these personas concretely.**

The panel is split into two groups:
- **The most acute use case (five personas)**: migrants and EU-mobile workers facing the densest concentration of friction. These remain the strongest specific narrative evidence and the primary persona-anchors in proposals and demos.
- **The wider friction class (two personas)**: non-migrant users facing structurally similar friction in different forms. Their presence demonstrates that the tool's architecture is friction-driven rather than demographic-driven, per Decision 21 in `04-research-and-decisions.md`.

When real anonymized testers become available, their stories replace or augment the fictional panel. Until then, the fictional panel carries the narrative.

---

## Why a panel — and why a wider panel

A single anchor persona risks reading as tokenism — "the migrant" as a singular figure. A panel proves the system serves a *category of human situations*, not a single demographic. The panel forces the design to handle edge cases (RTL languages, regulated professions, EU vs non-EU work rights, refugee-status nuances) rather than optimising for one happy path.

Extending the panel beyond the migrant use case proves the architectural claim that the tool addresses structural labor-market friction, not migration status as such. The wider personas (Käthe, Tobias) demonstrate that the same features serving the most-acute group — CV-format scaffolding, language-aware system navigation, structured conversational journey, fit-scoring, motivation-letter drafting — are equally relevant to other friction classes the European labor market produces.

The migrant five remain the most acute and the most concrete evidence. They are not the only users. They are the strongest example users.

---

## The five most-acute-use-case personas (migrants and EU-mobile workers)

Each persona is rendered with: name + origin, current age and family situation, professional background, current residence status in Germany, German-language level, primary frustration the agent solves, secondary frustrations the agent acknowledges but does not solve.

### 1. Aïcha — Tunisia → Berlin

**Age**: 31, partnered (husband works in IT in Tunis, planning to follow), no children yet.

**Professional background**: Registered nurse in Tunisia, 7 years of hospital experience including 2 in geriatric care. Speaks French and Arabic professionally; English conversational; German B1 (working toward B2).

**Residence status**: Holds a visa to seek Anerkennung (Aufenthaltserlaubnis nach §16d AufenthG — "for the purpose of recognition of a foreign professional qualification"). Anerkennung process is underway through BIBB / Anabin database; the recognition decision letter is expected in approximately 4 more months.

**Primary frustration the agent solves**: Aïcha can practice nursing legally once the recognition lands, but the German job market does not wait for the letter. She needs to identify employers willing to begin the application process, line up a probationary nursing contract for the moment the letter arrives, and prepare a German-format Lebenslauf that translates her Tunisian credentials in a way German HR understands. **The agent walks her through identifying recognition-friendly employers, generates a CV that aligns Tunisian role descriptions to German equivalents using ESCO mappings, drafts a motivation letter in clinical German, and tracks which applications acknowledge the in-progress recognition status positively.**

**Secondary frustrations the agent acknowledges but does not solve**: housing in Berlin (referred to the housing-agent composition partner); childcare planning for when her husband joins; navigating Krankenversicherung enrolment as a §16d holder. Each is acknowledged at the appropriate journey phase with a referral, not silence.

**What makes her credible as a persona**: Tunisia is one of the seven Triple Win countries from which the BA actively recruits nurses; her situation is statistically common; the language-level mismatch is the same problem the Bundesagentur publicly identifies; her recognition timeline mirrors the average duration in the Pflege sector.

### 2. Yusuf — Turkey → Munich

**Age**: 38, married, two children (ages 9 and 6) currently in Turkish school in Istanbul.

**Professional background**: Mechanical engineer with 13 years of experience in automotive supplier work (Bursa-based Tier 2 supplier to VW/Mercedes German plants). Bachelor's from ITÜ Istanbul; ISO 9001 lead auditor certification. Speaks Turkish, English (B2-business), German A2 (learning).

**Residence status**: EU Blue Card application in progress, supported by an employer offer at a Munich engineering firm. Will arrive once the Blue Card is issued; family reunification follows once a school place for the older child is secured.

**Primary frustration the agent solves**: Yusuf has the offer; the friction is in the *adjacent* labor-market navigation. He needs to compare equivalent-or-better opportunities (the Blue Card is portable but switching employers in the first months has rules), evaluate which German cities have schooling that will work for his children, prepare for the Anmeldung / Steuer-ID / Krankenkasse cascade his employer expects him to navigate in his first two weeks. **The agent gives him a structured timeline of "what happens in months 1-3 after arrival," a personalised checklist tied to his Blue Card start date, and a comparison of automotive-sector roles in Munich vs. Stuttgart vs. Ingolstadt.**

**Secondary frustrations the agent acknowledges but does not solve**: ITÜ degree certification, school enrolment for children, family-reunification paperwork. Each is referred.

**What makes him credible as a persona**: EU Blue Card holders are the largest growing category of skilled non-EU migration to Germany; Turkish engineers are a numerically significant cohort; the family-reunification timing puzzle is the actual lived experience.

### 3. Olga — Ukraine → Leipzig

**Age**: 34, single mother with one child (age 7) attending a German Grundschule.

**Professional background**: Senior frontend developer (React, TypeScript) at a Kyiv startup, 9 years' experience. Speaks Ukrainian and Russian as first languages; English B2-business; German A2-conversational.

**Residence status**: Holds residence permission under §24 AufenthG (temporary protection directive for displaced persons from Ukraine), which grants immediate work authorisation without separate work-permit application. Status renewed automatically for the directive period.

**Primary frustration the agent solves**: Olga can work today without permit paperwork — but the labor market reads "Ukrainian refugee" as a category before reading her CV. Tech employers either over-index on the protected-status framing or assume she does not speak enough German for collaboration. She wants to be evaluated as a senior frontend developer with proven shipping record. **The agent presents her CV in a way that foregrounds shipping history (GitHub commits, portfolio projects, public talks), provides employers with a clear residence-status explainer that pre-answers HR's "can she work here without sponsorship" question, and matches her to remote-friendly or English-speaking-team roles where her German level is not a blocker for the first 12 months.**

**Secondary frustrations the agent acknowledges but does not solve**: child's school progress, mental-health support for trauma, Ukrainian academic-credential equivalency for any future career-change. Each is referred.

**What makes her credible as a persona**: Ukrainian refugees specifically face low job-finding rates due to language mismatch (this is the actual policy problem the Bundesagentur and OECD have identified); tech is one of the strongest matching sectors because English-led teams reduce the German requirement; single-parent constraints shape commute and remote-work preferences.

### 4. Mahmoud — Syria → Hamburg

**Age**: 22, unmarried, no children. Arrived in Germany as an unaccompanied minor in 2018; reunited with mother and younger sister in 2020.

**Professional background**: Did not complete the Syrian Abitur due to displacement. Apprenticeship-level skills as a plumber's helper (informally trained at the family workshop in Aleppo). Has completed an Integrationskurs (B1) and a Berufssprachkurs (B2 for trades). Wants to enter the German dual system as an Auszubildender (apprentice) in Anlagenmechaniker für Sanitär-, Heizungs- und Klimatechnik.

**Residence status**: Subsidiärer Schutz (subsidiary protection) under §4 AsylG; permanent residence pathway via integration + work.

**Primary frustration the agent solves**: Mahmoud is in the labor-market segment with the strongest shortage (handwerkliche Berufe / skilled trades) but the weakest digital infrastructure. Most Ausbildung listings are scattered across IHK / HwK portals, individual employer websites, and informal Handwerkskammer noticeboards. The Lebenslauf format expected for an Ausbildung application is different from a Festanstellung application. **The agent aggregates Ausbildung openings across the IHK/HwK/employer sources, generates the right CV format for Ausbildung (Bewerbungsmappe convention, simpler structure, weights given to motivation and Praktikumserfahrungen), and prepares him for the typical Vorstellungsgespräch with a Handwerksmeister.**

**Secondary frustrations the agent acknowledges but does not solve**: BAföG eligibility for during the Ausbildung, family-finance coordination, certificate authentication. Each is referred.

**What makes him credible as a persona**: subsidiary-protection holders are the second-largest refugee-status group in Germany after Ukrainians; trades shortages are documented and acute; the digital gap in the Ausbildung-discovery pipeline is real and rarely addressed by existing tools.

### 5. Maria — Romania → Stuttgart

**Age**: 52, widowed, two adult children in Romania (one in Bucharest, one returned to Cluj for study).

**Professional background**: Trained as Krankenschwester (registered nurse) in Romania in 1991. Worked for 28 years in a Romanian hospital, then moved to elderly home-care work after the death of her husband. Speaks Romanian and Hungarian as first languages; conversational Italian (worked one year in Italy in 2015); German A2.

**Residence status**: EU citizen (Freizügigkeitsrecht under §2 FreizügG/EU). No permit needed.

**Primary frustration the agent solves**: Maria's biggest barrier is *not* a residence-status problem — she has full work rights. It is the persistent language barrier despite her legal access. Most home-care employers want B1 minimum, formally. Maria's care quality is excellent but she cannot demonstrate it through a German-language interview. **The agent connects her to the subset of Pflegedienst employers who actively integrate non-fluent care workers, generates a CV that documents her 28 years of clinical experience in terms an Altenpflegedienst Pflegedienstleiter will understand, and provides interview prep using audio prompts she can rehearse with.**

**Secondary frustrations the agent acknowledges but does not solve**: B1 certificate preparation, Anerkennung of her Romanian nursing diploma for full Krankenpflege practice (vs. the easier Altenpflegehelferin track), pension coordination between Romania and Germany. Each is referred.

**What makes her credible as a persona**: EU citizens with language barriers are the *forgotten* population of EU labor mobility — they have legal access but practical exclusion; older workers in Pflege are an under-served demographic with the most acute employer demand; Romania is the largest single source of EU migration to Germany.

---

## How the personas are used

### In the public README and project site

The README opens with: *"Aïcha, a Tunisian-trained nurse working through Anerkennung in Berlin, opens DirectJob Scout."* Then one sentence per other persona to show breadth. No long backstories on the README; the panel exists in this document for everyone who wants depth.

### In the application proposal

The proposal's introductory narrative uses two personas (typically Aïcha + Olga) to ground the problem statement in specific human situations. The rest of the panel is referenced in an annex.

### In demos and screenshots

Each demo screenshot is captioned with the persona it represents. The persona shapes the example queries, the CV content shown, the journey path. Demos are not generic — they are persona-specific.

### In design discussions

When considering whether a feature is worth building, the test is: does this help at least two personas in the panel, or is it overfit to one demographic? Features that fail this test are deferred.

### In the multilingual roadmap

The personas' linguistic profiles drive language priority:
- EN + DE already shipped — serves Käthe, Tobias, Aïcha, Yusuf, Olga, Mahmoud, Maria at the comprehension level they have or are reaching (Käthe and Tobias are German-native; the others are at A2–C1 German and benefit from English as well)
- Arabic (RTL work) — serves Aïcha and Mahmoud at first-language fluency
- Ukrainian / Russian — serves Olga at first-language fluency
- Turkish — serves Yusuf at first-language fluency
- Romanian — serves Maria at first-language fluency

The wider-friction-class personas (Käthe, Tobias) do not generate additional language demand because they are German-native. Their inclusion adds *no* language-roadmap cost — only architectural-validation evidence.

### Inclusion of real testers

If real testers from comparable backgrounds become available before submission, their anonymized stories *replace* the fictional panel in public materials. Real beats fictional every time. The fictional panel exists as scaffolding until then; we may end up with a panel that is part-fictional and part-real, and that is acceptable.

---

## The two wider-friction-class personas (non-migrant)

These personas demonstrate that the same friction the migrant five face takes structurally similar forms for non-migrant users. The architecture serves them equally. Per Decision 21, the friction class is the design target; the migrant subset is the most acute case within it.

### 6. Käthe — German, returning to nursing after twelve years out for childcare

**Age**: 47, married, three children (ages 14, 11, 8) now all in school for the first time.

**Professional background**: Registered Krankenschwester. Trained and certified in Germany in 1998. Practiced clinical nursing on a cardiology ward in a Berlin hospital from 1999 to 2013, then left the workforce to raise her children. Speaks German natively; reads English clinical literature.

**Residence status**: German citizen, no permit needed, lived in Berlin her whole working life.

**Primary frustration the agent solves**: Käthe is legally a nurse — the Berufsbezeichnung still applies. But everything about practising nursing in Germany has changed since 2013: digital patient-record systems, electronic medication management, new infection-control protocols, COVID-era staffing-model changes, mandatory continuing-education hours she missed, and a shifted hiring landscape where hospitals expect re-entrants to attest to specific re-orientation programmes (Wiedereinstiegsprogramme). She does not know where to start, her old contacts have moved on, and her CV from 2013 is structurally wrong for 2026 conventions. **The agent walks her through identifying Berlin hospitals with formal Wiedereinstieg programmes, generates an updated CV that frames her twelve-year absence as caregiving rather than a gap to apologise for, drafts a motivation letter aligned with current Pflege-sector hiring conventions, and proposes a three-step re-entry timeline (formal Auffrischung course → Wiedereinstieg interview prep → first ward shadowing).**

**Secondary frustrations the agent acknowledges but does not solve**: continuing-education credit recovery, schedule-flexibility negotiation (school-aged kids), pension-credit catch-up. Each is referred.

**What makes her credible as a persona**: returning workers after extended caregiving absence are a numerically significant, structurally under-served demographic across the EU. The Bundesagentur publicly identifies this as one of the labor-supply levers Germany pulls hardest. The 46,000-position healthcare shortage is the same shortage Aïcha addresses, from a different friction angle: Käthe has legal access and German fluency but needs system re-orientation; Aïcha has clinical capability but needs language and recognition support. Same shortage, different friction shape.

### 7. Tobias — German, software developer pivoting from commercial tech to public-sector civic-tech

**Age**: 35, single, no children. Lives in Hamburg.

**Professional background**: Senior backend developer (Python, Go, distributed systems) with eleven years at a Hamburg-based fintech startup. Strong portfolio of shipped commercial software; led a team of four in his last role. Speaks German natively; English C1-business.

**Residence status**: German citizen, no permit needed.

**Primary frustration the agent solves**: Tobias wants to leave commercial fintech and work on civic-tech or public-sector digital infrastructure — applications that serve the public good rather than maximising returns. He has no idea how to get hired in the public-sector or NGO context. The hiring process is entirely different from commercial tech: TVöD pay grades (E13 / E14 / E15), formal tariff-bound positions, application packages that demand specific German bureaucratic conventions (Beamtenstatus questions, formal Bewerbungsmappen, tariff-aware CV framing) rather than the casual CV+cover-letter pattern commercial tech uses. He doesn't know which agencies and NGOs are actively hiring developers, doesn't know how to translate his commercial impact ("led the migration of our payment-processing layer") into the language public-sector hiring committees actually evaluate. **The agent walks him through the public-sector digital-employer landscape (GovTech Campus, Sovereign Tech Fund-affiliated projects, Code for Germany, Prototype Fund-adjacent organisations, federal IT roles, civic-NGO digital teams), generates a CV reformatted for public-sector conventions with TVöD-pay-grade-aligned framing, drafts a motivation letter that translates commercial impact into civic-service language, and prepares him for the structurally different interview format.**

**Secondary frustrations the agent acknowledges but does not solve**: pay-cut financial planning, navigating Beamtenstatus eligibility, family pension implications. Each is referred.

**What makes him credible as a persona**: career-changers from commercial tech to civic-tech / public-sector are a small but growing cohort across the EU. The friction they face — translating commercial-vocabulary capability into public-sector-vocabulary credentials — is identical in *shape* to what Aïcha faces translating Tunisian-vocabulary credentials into German-vocabulary credentials. Same architectural friction, different surface vocabulary. His presence in the panel directly demonstrates the friction-class claim.

---

## What the personas are not

- **Not stereotypes**: each persona has a specific profession, life situation, and goal. None is "the migrant" generically and none is "the German" generically.
- **Not interchangeable**: the agent's response to each differs concretely — Aïcha gets Anerkennung-aware employer matching; Olga gets remote-friendly-tech matching; Mahmoud gets Ausbildung-format CV scaffolding; Käthe gets Wiedereinstieg-programme matching; Tobias gets TVöD-aware public-sector framing.
- **Not used to claim universal applicability beyond the friction class**: the agent serves *humans with structural labor-market friction in the EU*. People who already navigate the system fluently and have the social capital to do so are not the design target.

---

## What if a real partner NGO objects to the panel?

Likely: an MBE or IQ-Netzwerk advisor reviewing the panel will say something like "Aïcha is too senior" or "Mahmoud is the wrong age" or "you missed the Western Balkan apprenticeship category." That feedback is welcomed and folded in. The panel is a living document, not a fixed reference.
