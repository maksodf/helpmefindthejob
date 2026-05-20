<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Tobias (German, commercial → civic-tech)

**Persona slug**: `tobias`  |  **Cohort**: `wider-friction`  |  **Location**: Hamburg
**Residency status**: German citizen
**Friction notes**: Public-sector hiring is structurally different from commercial: TVöD pay grades (E13/E14/E15), formal tariff-bound positions, application packages with specific German bureaucratic conventions (Beamtenstatus questions, Bewerbungsmappen, tariff-aware CV framing). Doesn't know which agencies and NGOs are actively hiring developers.

## Fixture JD

**Scenario label**: `civic_tech_govtech_campus`
**Job title**: Senior Backend Developer (TVöD E14, Civic Tech)
**Job location**: Hamburg / Berlin
**Company**: Beispielarbeitgeber (Hamburg / Berlin) (synthetic for this walk)

**Job description**:

> Sovereign-Tech-Fund-affiliated civic-tech NGO seeks senior backend developer. TVöD E14 pay grade. Python / Go stack. Mission: open-source infrastructure for public good. Commercial → civic transition welcome; we provide onboarding for first-time public-sector hires.

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 12.4 s
- Output length: 1274 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile:
Tobias
Hamburg

Empfängeradresse:
Beispielarbeitgeber
Hamburg / Berlin

Date: 15.02.2023

Betreff:
Bewerbung als Senior Backend Developer (TVöD E14, Civic Tech)

Sehr geehrte Damen und Herren,

Mein Interesse an der Stelle als Senior Backend Developer bei Beispielarbeitgeber in Hamburg entstand durch die Chance, meine Fähigkeiten für zivilgesellschaftliche und öffentliche Zwecke einzusetzen. Ich bin beeindruckt von den Aktivitäten des Unternehmens im Bereich Civic Tech und glaube, dass ich mich mit meinen 11 Jahren Erfahrung als Senior Backend Entwickler im FinTech-Sektor in Hamburg einsetzen kann, um einen wertvollen Beitrag zu leisten.

In meiner letzten Position führte ich eine Mannschaft von vier Entwicklern an und baute ein starkes Portfolio an gelieferten Software-Produkten mit Python, Go und verteilten Systemen. Meine Sprachkenntnisse in Englisch auf C1-Business-Niveau ermöglichen mir eine effektive Kommunikation mit internationalen Teams.

Ich bin überzeugt, dass meine Fähigkeiten und Erfahrungen mich gut auf die Herausforderungen im Bereich Civic Tech vorbereiten. Ich bin gespannt darauf, mein Know-how in einem neuen Umfeld einzubringen und zu lernen, wie ich mich in diesem Bereich einsetzen kann.

Mit freundlichen Grüßen,

Tobias
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | MISSING — FAIL |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['TVöD', 'Python'] (2 / 5 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. FAIL

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
