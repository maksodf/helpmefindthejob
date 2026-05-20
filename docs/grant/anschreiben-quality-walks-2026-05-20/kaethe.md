<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Käthe (German, nursing re-entrant)

**Persona slug**: `kaethe`  |  **Cohort**: `wider-friction`  |  **Location**: Berlin
**Residency status**: German citizen (Freizügigkeit not applicable)
**Friction notes**: 12-year clinical absence: digital patient-record systems, electronic medication management, infection-control protocols, mandatory CE hours all changed since 2013. Hospitals expect a Wiedereinstiegsprogramm or Auffrischung course; her old CV reads as obsolete for 2026 conventions.

## Fixture JD

**Scenario label**: `wiedereinstieg_clinical`
**Job title**: Krankenschwester (Wiedereinstieg-Programm)
**Job location**: Berlin
**Company**: Beispielarbeitgeber (Berlin) (synthetic for this walk)

**Job description**:

> Klinikum Berlin bietet Wiedereinstiegsprogramm für Pflegekräfte nach Familienpause. Auffrischungskurs inklusive. 3-stufige Wiedereinstiegs-Timeline: Auffrischung → Schattenpraktikum → Wiederaufnahme. Familienfreundliche Arbeitszeiten.

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 20.0 s
- Output length: 1906 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile:
Käthe
Berlin

Empfängeradresse:
Beispielarbeitgeber
Berlin

Date: 15.03.2023

Betreff: Bewerbung als Krankenschwester (Wiedereinstieg-Programm)

Sehr geehrte Damen und Herren,

Als erfahrene Krankenschwester mit langjähriger Erfahrung in der Klinik und dem Wunsch, sich wieder auf die Pflege zurückzuziehen, bin ich von der Möglichkeit, mich bei Ihrem Unternehmen für das Wiedereinstieg-Programm zu bewerben, sehr angetan. Ich habe mich entschieden, mich um diese Stelle zu bewerben, weil ich wissen möchte, wie ich mit den modernen Pflegekonzepten und Technologien Schritt halten kann.

In meiner über 14-jährigen Laufbahn als Krankenschwester war ich auf einer Kardiologie-Station tätig und habe mich in der Betreuung von Patienten mit kardiovaskulären Erkrankungen und in der Erfassung von medizinischen Daten ausgebildet. Ich besitze die erforderliche Zertifizierung als Krankenschwester, die ich 1998 erworben habe. Da ich mich über zwölf Jahre aus dem Beruf zurückgezogen habe, um meine Kinder aufzuziehen, muss ich mich nun wieder in den modernen Pflegebereich einarbeiten.

Ich bin mir bewusst, dass sich das Krankenhauswesen in diesem Zeitraum stark verändert hat. Die Umstellung von Papierdokumentation zu digitalen Patientenakten sowie die Einführung elektronischer Medikationsmanagement-Systeme und neue Infektionskontrollprotokolle erfordern ein hohes Maß an Flexibilität und Wissensverfügbarkeit. Ich bin jedoch überzeugt, dass ich mit meiner Erfahrung, Flexibilität und Neugier schnell in den neuen Anforderungen Schritt halten kann.

Ich freue mich darauf, in einem persönlichen Gespräch meine Qualifikationen im Detail zu besprechen und zu erfahren, wie ich mein Wiedereinstieg-Programm bei Ihrem Unternehmen fortsetzen kann. Ich bitte darum, mir die Möglichkeit zu geben, mich am 22. März um 10 Uhr in Ihrem Büro vorzustellen.

Mit freundlichen Grüßen,
Käthe

Unterschrift:
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | MISSING — FAIL |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['Berlin'] (1 / 8 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. FAIL

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
