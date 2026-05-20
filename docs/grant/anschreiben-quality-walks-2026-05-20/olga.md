<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Olga (Ukraine → Leipzig)

**Persona slug**: `olga`  |  **Cohort**: `most-acute`  |  **Location**: Leipzig
**Residency status**: §24 AufenthG (temporary protection for displaced Ukrainians)
**Friction notes**: Single parent (one child age 7 in Grundschule); needs remote-friendly or English-speaking-team roles where A2 German is not a 12-month blocker. Wants to be evaluated on shipped-software portfolio rather than language.

## Fixture JD

**Scenario label**: `english_team_remote_react`
**Job title**: Senior Frontend Developer (English-team, remote-friendly)
**Job location**: Leipzig / remote within EU
**Company**: Beispielarbeitgeber (Leipzig / remote within EU) (synthetic for this walk)

**Job description**:

> Berlin-headquartered fintech seeks senior frontend developer. English-language working environment. Remote within EU acceptable; hybrid Leipzig possible. React + TypeScript core stack. Right to work in Germany required (§24 AufenthG accepted).

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 13.1 s
- Output length: 1382 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile:
Olga Leipzig

Empfängeradresse:
Beispielarbeitgeber, Leipzig / remote within EU

Date: 12.05.2024

Betreff:
Bewerbung als Senior Frontend Developer

Sehr geehrte Damen und Herren,

Als erfahrene Frontend-Entwicklerin mit über neun Jahren Erfahrung in React und TypeScript bin ich von der Möglichkeit, bei Beispielarbeitgeber zu arbeiten, sehr angetan. Die Tatsache, dass Sie eine remote-freundliche Arbeitssituation bieten, entspricht meinen aktuellen Bedürfnissen als Mutter eines siebenjährigen Kindes, das noch in der Grundschule ist.

Mit einer starken Portfolio-Entwicklung mit geschäftsfähigem Software und Erfahrung im Teamleiten (ein Team von vier Personen) bin ich überzeugt, dass meine Fähigkeiten bei Ihrem Unternehmen von Nutzen sein können. Ich habe eine starke Präsenz in Englisch (C1-Business-Niveau) und ein A2-Niveau in Deutsch.

In Hinblick auf Ihre Erfordernisse als Senior Frontend Developer kann ich erwähnen, dass mein Portfolio von geschäftlich entwickelter Software mit React und TypeScript überzeugt. Darüber hinaus habe ich eine enge Kommunikation mit englischsprachigen Teams in der Vergangenheit bewiesen.

Ich bin sehr daran interessiert, mich bei Beispielarbeitgeber als Senior Frontend Developer zu bewerben. Ich bitte um die Gelegenheit, meine Fähigkeiten und mein Portfolio im Gespräch zu präsentieren.

Mit freundlichen Grüßen,

Olga
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | ['Senior frontend developer'] |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['Remote', 'Leipzig', 'React', 'TypeScript'] (4 / 8 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. PASS

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
