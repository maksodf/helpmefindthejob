<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Mahmoud (Syria → Hamburg)

**Persona slug**: `mahmoud`  |  **Cohort**: `most-acute`  |  **Location**: Hamburg
**Residency status**: §4 AsylG subsidiary protection
**Friction notes**: Ausbildung openings are scattered across IHK/HwK portals and informal Handwerkskammer noticeboards. CV format expected for Ausbildung (Bewerbungsmappe convention) differs from Festanstellung. Vorstellungsgespräch with a Handwerksmeister is the typical interview format.

## Fixture JD

**Scenario label**: `ausbildung_shk_hamburg`
**Job title**: Auszubildender Anlagenmechaniker SHK
**Job location**: Hamburg
**Company**: Beispielarbeitgeber (Hamburg) (synthetic for this walk)

**Job description**:

> Handwerksbetrieb in Hamburg sucht Auszubildenden im Bereich Anlagenmechanik Sanitär, Heizung, Klima. Ausbildungsbeginn September. Berufssprachkurs B2 ausreichend. Subsidiärer Schutz / Aufenthaltsgestattung kein Hindernis.

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 12.7 s
- Output length: 1273 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile:
Mahmoud 
Hamburg 

Empfängeradresse:
Beispielarbeitgeber
Hamburg

Date: 01.02.2023

Betreff:
Bewerbung als Auszubildender Anlagenmechaniker SHK

Anrede:
Sehr geehrte Damen und Herren,

In der Bewerberschaft für eine Ausbildung als Anlagenmechaniker für Sanitär, Heizung, Klima bei Beispielarbeitgeber in Hamburg bin ich von dem Unternehmen überzeugt worden, weil es sich auf eine wichtige Branche spezialisiert hat. Als jemand, der sich immer für die technische Seite von Bauwerken interessiert hat, würde ich mich sehr freuen, meine Fähigkeiten und mein Wissen weiter zu entwickeln.

Ich habe bereits Erfahrungen als Hilfsarbeiter in meiner Familie gesammelt und bin aufgrund meines Integrationskurses (B1) und Berufssprachkurs (B2 für Handwerk) gut vorbereitet. Ich verfüge über die notwendigen Sprachkenntnisse, um erfolgreich meine Ausbildung zu absolvieren.

Mein Einstieg in die deutsche Bildungssysteme gestaltete sich schwierig aufgrund meines unaccompanied status als Flüchtling. Dennoch bin ich entschlossen, mich in der Gesellschaft zu integrieren und eine erfolgreiche Zukunft zu bauen. Meine Ausbildungswünsche basieren auf meinen Interessen an der Branche und meiner Fähigkeit, die Herausforderungen anzugehen.

Mit freundlichen Grüßen,
Mahmoud
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | ['Auszubildender Anlagenmechaniker SHK'] |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['Hamburg', 'Anlagenmechanik', 'Sanitär', 'Heizung'] (5 / 8 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. PASS

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
