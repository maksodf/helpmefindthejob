<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Maria (Romania → Stuttgart)

**Persona slug**: `maria`  |  **Cohort**: `most-acute`  |  **Location**: Stuttgart
**Residency status**: EU citizen (Freizügigkeitsrecht)
**Friction notes**: Persistent language barrier despite full work rights; most home-care employers want B1 minimum formally. Care quality is excellent but cannot be demonstrated through a German-language interview. Wants employers who integrate non-fluent care workers via Audio-prep or buddy systems.

## Fixture JD

**Scenario label**: `language_friendly_pflegedienst`
**Job title**: Pflegehelferin (language-integration-friendly)
**Job location**: Stuttgart
**Company**: Beispielarbeitgeber (Stuttgart) (synthetic for this walk)

**Job description**:

> Ambulanter Pflegedienst Stuttgart sucht Pflegehelfer:innen. Deutschniveau A2 ausreichend bei Eignung und langjähriger Erfahrung. Sprachpate für die ersten 6 Monate. EU-Bürger:innen willkommen.

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 15.7 s
- Output length: 1579 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile:
Maria Stuttgart

Empfängeradresse:
Beispielarbeitgeber
Stuttgart

Date: 12.05.2023

Betreff: Bewerbung als Pflegehelferin

Sehr geehrte Damen und Herren,

Ich bin mich sehr für die Stelle der Pflegehelferin bei Beispielarbeitgeber in Stuttgart beworben, da ich mich für die Möglichkeit interessiere, meine Erfahrungen im Bereich der Altenpflege einzubringen. Die Arbeit mit älteren Menschen hat mir in meiner Zeit als Krankenschwester in Rumänien viel Freude bereitet und ich bin sicher, dass meine Fähigkeiten auch bei Beispielarbeitgeber nutzbar wären.

Als ausgebildete Krankenschwester verfüge ich über 28 Jahre Erfahrung im Bereich der Gesundheitsversorgung. In Rumänien habe ich in einem Krankenhaus gearbeitet und nach meiner Heiratswitwen werden mich auf die Arbeit im Bereich der Altenpflege konzentriert habe. Ich bin auch mit dem Home-Elderly-Care-System vertraut, da ich selbst in dieser Branche tätig war.

Zusätzlich zu meinen Fähigkeiten als Pflegehelferin verfüge ich über ein gutes Sprachverständnis für Italienisch und spreche fließend Rumänisch und Ungarisch. Obwohl mein Deutsch auf A2-Level begrenzt ist, bin ich bereit, mich weiterzubilden, um meine Fähigkeiten in dieser Hinsicht zu verbessern.

Ich würde mich sehr freuen, die Gelegenheit haben, mit Ihnen zu sprechen und meine Qualifikationen und Erfahrungen persönlich vorzustellen. Bitte teilen Sie mir mit, wann ein Interview möglich ist. Ich bin überzeugt, dass ich eine wichtige Ergänzung für das Team von Beispielarbeitgeber sein kann.

Mit freundlichen Grüßen,

Maria

Unterschrift:
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | ['Pflegehelferin'] |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['Stuttgart', 'Pflegehelfer', 'Erfahrung'] (3 / 8 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. PASS

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
