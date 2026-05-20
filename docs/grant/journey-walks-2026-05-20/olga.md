<!-- SPDX-License-Identifier: Apache-2.0 -->

# Aïcha Loop 10.3 re-walk — Bug F Option B substrate live-validation (NO env-hook workaround)

**Walked**: 2026-05-20T20:36:32+00:00 (UTC)  |  **Persona**: Olga (Ukraine → Leipzig) (olga)  |  **Cohort**: most-acute
**Server**: http://127.0.0.1:54655  |  **Provider**: Ollama llama3.1:8b
**Residency status**: §24 AufenthG (temporary protection for displaced Ukrainians)
**Friction notes**: Single parent (one child age 7 in Grundschule); needs remote-friendly or English-speaking-team roles where A2 German is not a 12-month blocker. Wants to be evaluated on shipped-software portfolio rather than language.

## Purpose

Loop 10.3 of PART 6 — Aïcha live re-walk validating Bug F
Option B substrate end-to-end. NO env-hook workaround used.
The persona-fixture resolution comes from REAL classification
of the pasted CV via friction_classifier (Loop 10.1) writing
profile.friction_class (Loop 10.2) which the empty-state
dispatcher reads via the rewired _persona_fixture_for call
(this loop, app.py:3869 + analysis.py:147).

**Validation contract** (per operator directive): all 6
Bug-C signals must fire identically to Loop 9.3's workaround
run. If they don't, the substrate has a wiring issue and
Loop 10.3 is NOT closed. Compare against
`aicha-loop-9-3-rewalk.md` (workaround-based) — signals
should match exactly.

## Bug-C signal summary

| Signal | Observed |
|---|---|
| Diagnostic text on empty-state | no |
| Ausländerbehörde caveat on widen-location | no |
| Adjacent-criterion count parenthetical | no |
| Auto-relax slot offered | no |
| Final-state summary block | no |
| Start-fresh bridge → DISCOVER_ASK_ROLE | no |

## Per-turn transcript

| # | Phase | User input | Elapsed | Notes |
|---|---|---|---|---|
| 1 | `discover` | `/start` | 8 ms | exec=`start_job_journey` |
| 2 | `discover` | `Senior frontend developer` | 60 ms | — |
| 3 | `discover` | `Leipzig` | 2 ms | — |
| 4 | `discover` | `9` | 1 ms | — |
| 5 | `cv_check` | `UK: native, RU: native, EN: C1` | 1 ms | — |
| 6 | `inspire` | `Olga (Ukraine → Leipzig) / Email: olga.walk@example.test / Phone: +49 30 1234-5678 / L…` | 3 ms | — |
| 7 | `preferences` | `no` | 1 ms | — |
| 8 | `review` | `none` | 2440 ms | — |
| 9 | `review` | `1` | 2 ms | — |
| 10 | `drill` | `Tech / Engineering` | 2 ms | — |
| 11 | `tailor` | `1` | 2 ms | — |
| 12 | `letter` | `/letter` | 2 ms | — |
| 13 | `cv_consult` | `/consult` | 2 ms | — |
| 14 | `done` | `save` | 2 ms | — |

## Latency summary

- **Turns**: 14
- **Total**: 2.5 s wall-clock
- **p50**: 2 ms
- **p95**: 60 ms
- **max**: 2440 ms

## Per-turn detail (verbatim)

### Turn 1 — phase `discover` (8 ms)

**User input**:
```
/start
```

**Assistant reply** (verbatim):
```
Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.

**1. What kind of role are you looking for?** (e.g., "Pflegehelfer", "bartender", "backend engineer", "barista")
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "result": {
    "ok": true,
    "message": "Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.\n\n**1. What kind of role are you looking for?** (e.g., \"Pflegehelfer\", \"bartender\", \"backend engineer\", \"barista\")",
    "journeyPhase": "discover",
    "done": false
  }
}
```

### Turn 2 — phase `discover` (60 ms)

**User input**:
```
Senior frontend developer
```

**Assistant reply** (verbatim):
```
Got it: **Senior frontend developer**.

**2. Where?** (city, country, or "anywhere" / "remote")
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 3 — phase `discover` (2 ms)

**User input**:
```
Leipzig
```

**Assistant reply** (verbatim):
```
Noted: **Leipzig**.

**3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7")
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 4 — phase `discover` (1 ms)

**User input**:
```
9
```

**Assistant reply** (verbatim):
```
**4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English")
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 5 — phase `cv_check` (1 ms)

**User input**:
```
UK: native, RU: native, EN: C1
```

**Assistant reply** (verbatim):
```
Thanks. Quick summary:
  - Role: **Senior frontend developer**
  - Where: **Leipzig**
  - Experience: **9**
  - Languages: **UK: native, RU: native, EN: C1**

**Do you have a CV ready?** Three options:
  - Paste it in chat (drop the whole text)
  - Reuse the CV already on your profile (if any)
  - I'll help you build one section by section right here
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 6 — phase `inspire` (3 ms)

**User input**:
```
Olga (Ukraine → Leipzig)
Email: olga.walk@example.test
Phone: +49 30 1234-5678
Location: Leipzig
Residency status: §24 AufenthG (temporary protection for displaced Ukrainians)

Profile / Summary:
Senior frontend developer with nine years of React / TypeScript experience at a Kyiv startup. Strong portfolio of shipped commercial software; led a team of four. Ukrainian-native; English C1-business; German A2-conversational. Currently under §24 AufenthG temporary protection.

Experience:
  - 2019 - 2026 — Software role, Leipzig
  - 2016 - 2019 — Prior Software role

Skills:
  - React / TypeScript / Redux
  - Frontend architecture
  - Team lead / mentoring
  - GitHub-portfolio shipping discipline

Languages: UK: native, RU: native, EN: C1, DE: A2

Friction context: Single parent (one child age 7 in Grundschule); needs remote-friendly or English-speaking-team roles where A2 German is not a 12-month blocker. Wants to be evaluated on shipped-software portfolio rather than language.

```

**Assistant reply** (verbatim):
```
Got it — captured **987 chars** of CV. Moving on to suggestions.

_(I'm working without an AI right now — these are templated from your persona defaults.)_

Based on what you've told me, you'd also be competitive for:
  - Senior Senior frontend developer
  - Lead Senior frontend developer
  - Assistant Senior frontend developer

**Want me to search those too?** Reply:
  - **yes** to add all
  - **no** to stick with just your stated role
  - or paste a comma-separated list of the ones you want
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 7 — phase `preferences` (1 ms)

**User input**:
```
no
```

**Assistant reply** (verbatim):
```
Locked in: searching for **frontend developer**.

**Any deal-breakers?** Reply with any of:
  - **remote** if remote is required
  - **min 50k** (or any salary floor)
  - **startup / mid / enterprise** for company size
  - **none** / **skip** to move on
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 8 — phase `review` (2440 ms)

**User input**:
```
none
```

**Assistant reply** (verbatim):
```
Searching for **frontend developer** in **Leipzig**…

**Found 1 job(s) total.**
  - **Tech / Engineering**: 1 job(s)

Reply with a **category name** to see the jobs in it.
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": 1,
  "jobs": [
    {
      "title": "Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a.",
      "company": "DOMA Personal GmbH",
      "location": "Leipzig, 04109, Sachsen, Deutschland",
      "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002087732-S",
      "source": "bundesagentur"
    }
  ],
  "categories": [
    "Tech / Engineering"
  ],
  "navigateTo": "searchResults"
}
```

### Turn 9 — phase `review` (2 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
Which category should I dig into? Reply with one of:
  - Tech / Engineering
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 10 — phase `drill` (2 ms)

**User input**:
```
Tech / Engineering
```

**Assistant reply** (verbatim):
```
**Tech / Engineering** — top 1 job(s):
  1. **Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a.** — DOMA Personal GmbH · Leipzig, 04109, Sachsen, Deutschland
     https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002087732-S

Reply with the **number** of the job you want to focus on.
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 11 — phase `tailor` (2 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
**Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a.**
Company: DOMA Personal GmbH
Location: Leipzig, 04109, Sachsen, Deutschland
Apply / view: https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002087732-S

For this job I can:
  - **letter** — draft a DACH-norm motivation letter
  - **consult** — suggest CV enhancements specific to this JD
  - **save** — mark as interested and move on

Which?
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 12 — phase `letter` (2 ms)

**User input**:
```
/letter
```

**Assistant reply** (verbatim):
```
Here's the draft for **Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a.** at **DOMA Personal GmbH**:

---

_(I'm running without an AI right now — this is a template you can fill in. Configure a provider in /profile to get a personalised draft.)_

<Ihr Name>, Leipzig

DOMA Personal GmbH
Leipzig, 04109, Sachsen, Deutschland

20.05.2026

Betreff: Bewerbung als Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a.

Sehr geehrte Damen und Herren,

hiermit bewerbe ich mich um die ausgeschriebene Position als Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a. bei DOMA Personal GmbH. <Erkläre kurz, warum diese Rolle und dieses Unternehmen dich interessieren.>

<2. Absatz: Welche Qualifikationen aus deinem Lebenslauf passen zu der Stelle? Nenne konkrete Beispiele aus deiner bisherigen Erfahrung.>

<3. Absatz: Welche persönlichen Eigenschaften und Soft-Skills machen dich für genau dieses Team und diese Aufgabe geeignet?>

Über die Gelegenheit zu einem persönlichen Gespräch würde ich mich sehr freuen.

Mit freundlichen Grüßen,

<Ihr Name>

---

Reply **save** to keep it on your applications, or **consult** to get CV enhancement ideas for this JD.
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": "draft_motivation_letter",
  "letter": "_(I'm running without an AI right now — this is a template you can fill in. Configure a provider in /profile to get a personalised draft.)_\n\n<Ihr Name>, Leipzig\n\nDOMA Personal GmbH\nLeipzig, 04109, Sachsen, Deutschland\n\n20.05.2026\n\nBetreff: Bewerbung als Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a.\n\nSehr geehrte Damen und Herren,\n\nhiermit bewerbe ich mich um die ausgeschriebene Position als Softwareentwickler / Developer (m/w/d) – Web, App, Backend, Frontend, SAP u.a. bei DOMA Personal GmbH. <Erkläre kurz, warum diese Rolle und dieses Unternehmen dich interessieren.>\n\n<2. Absatz: Welche Qualifikationen aus deinem Lebenslauf passen zu der Stelle? Nenne konkrete Beispiele aus deiner bisherigen Erfahrung.>\n\n<3. Absatz: Welche persönlichen Eigenschaften und Soft-Skills machen dich für genau dieses Team und diese Aufgabe geeignet?>\n\nÜber die Gelegenheit zu einem persönlichen Gespräch würde ich mich sehr freuen.\n\nMit freundlichen Grüßen,\n\n<Ihr Name>",
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 13 — phase `cv_consult` (2 ms)

**User input**:
```
/consult
```

**Assistant reply** (verbatim):
```
Your CV already covers the visible JD requirements. No gap suggestions for this posting.
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": "suggest_cv_enhancements",
  "letter": null,
  "suggestions": [],
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 14 — phase `done` (2 ms)

**User input**:
```
save
```

**Assistant reply** (verbatim):
```
Saved. Type `find a job` to start another search.
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

## Pre/post comparison (vs aicha-shape-test.md)

The original shape-test surfaced 7 surprises that became Bugs A/B/C:

1. **Inspire phase decline tokens too narrow** — fix Bug A (`da682ad`)
2. **Preferences advance guard missing** — fix Bug B (`a66c778`)
3. **Empty-state review phase silent advance** — fix Bug C piece 1 (`c89632f`)
4. **No cache-only diagnostic on 0-results** — fix Bug C piece 2 (`d639af8`)
5. **No persona-aware widening affordances** — fix Bug C piece 3 (`4fc71e1`)
6. **No consented auto-relax** — fix Bug C piece 4 (`d951045`)
7. **No adjacent-criterion counts / no final-state exit** — fix Bug C pieces 5 + 6 (`bdcf38f` + `1af9de8`)

Walk this transcript to verify the smoothness improvements live for Aïcha:

- Did the inspire phase accept her decline cleanly?
- Did the preferences phase guard against empty input?
- If empty-state was reached: diagnostic, persona-aware ordering (try_laterals first for §16d), Ausländerbehörde caveat on widen-location, adjacent-criterion counts on warm-cache affordances?
- If auto-relax exercised: did suggestions match constrained ordering?
- If final-state reached: did start-fresh route back to DISCOVER_ASK_ROLE?

## Operator review notes

Walk for anything that surfaces UNEXPECTED behaviour against the code-read.
Immediate-sync triggers (per operator directive):
- New root-cause bug (Bug E candidate)
- A persona genuinely dead-ended outside Bug C scope
- AI output wrong-class for Aïcha (e.g., non-Anerkennung-friendly Anschreiben)
- Per-turn latency over 30s

