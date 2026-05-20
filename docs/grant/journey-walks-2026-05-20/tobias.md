<!-- SPDX-License-Identifier: Apache-2.0 -->

# Aïcha Loop 10.3 re-walk — Bug F Option B substrate live-validation (NO env-hook workaround)

**Walked**: 2026-05-20T20:49:47+00:00 (UTC)  |  **Persona**: Tobias (German, commercial → civic-tech) (tobias)  |  **Cohort**: wider-friction
**Server**: http://127.0.0.1:55578  |  **Provider**: Ollama llama3.1:8b
**Residency status**: German citizen
**Friction notes**: Public-sector hiring is structurally different from commercial: TVöD pay grades (E13/E14/E15), formal tariff-bound positions, application packages with specific German bureaucratic conventions (Beamtenstatus questions, Bewerbungsmappen, tariff-aware CV framing). Doesn't know which agencies and NGOs are actively hiring developers.

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
| 2 | `discover` | `Senior Backend Developer (Public Sector / Civic Tech)` | 62 ms | — |
| 3 | `discover` | `Hamburg` | 2 ms | — |
| 4 | `discover` | `11` | 1 ms | — |
| 5 | `cv_check` | `DE: native, EN: C1-business` | 2 ms | — |
| 6 | `inspire` | `Tobias (German, commercial → civic-tech) / Email: tobias.walk@example.test / Phone: …` | 3 ms | — |
| 7 | `preferences` | `no` | 1 ms | — |
| 8 | `review` | `none` | 2596 ms | — |
| 9 | `review` | `1` | 2 ms | — |
| 10 | `drill` | `Tech / Engineering` | 2 ms | — |
| 11 | `tailor` | `1` | 2 ms | — |
| 12 | `letter` | `/letter` | 2 ms | — |
| 13 | `cv_consult` | `/consult` | 3 ms | — |
| 14 | `done` | `save` | 2 ms | — |

## Latency summary

- **Turns**: 14
- **Total**: 2.7 s wall-clock
- **p50**: 2 ms
- **p95**: 62 ms
- **max**: 2596 ms

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

### Turn 2 — phase `discover` (62 ms)

**User input**:
```
Senior Backend Developer (Public Sector / Civic Tech)
```

**Assistant reply** (verbatim):
```
Got it: **Senior Backend Developer (Public Sector / Civic Tech)**.

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
Hamburg
```

**Assistant reply** (verbatim):
```
Noted: **Hamburg**.

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
11
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

### Turn 5 — phase `cv_check` (2 ms)

**User input**:
```
DE: native, EN: C1-business
```

**Assistant reply** (verbatim):
```
Thanks. Quick summary:
  - Role: **Senior Backend Developer (Public Sector / Civic Tech)**
  - Where: **Hamburg**
  - Experience: **11**
  - Languages: **DE: native, EN: C1-business**

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
Tobias (German, commercial → civic-tech)
Email: tobias.walk@example.test
Phone: +49 30 1234-5678
Location: Hamburg
Residency status: German citizen

Profile / Summary:
Senior backend developer with eleven years at a Hamburg-based fintech startup. Strong portfolio of shipped commercial software (Python, Go, distributed systems); led a team of four in last role. German-native; English C1-business. Wants to leave commercial fintech and work on civic-tech / public-sector digital infrastructure.

Experience:
  - 2019 - 2026 — Software role, Hamburg
  - 2016 - 2019 — Prior Software role

Skills:
  - Backend systems (Python, Go)
  - Distributed systems / API design
  - Team lead / mentoring
  - Commercial-impact framing (needs TVöD-translation help)

Languages: DE: native, EN: C1-business

Friction context: Public-sector hiring is structurally different from commercial: TVöD pay grades (E13/E14/E15), formal tariff-bound positions, application packages with specific German bureaucratic conventions (Beamtenstatus questions, Bewerbungsmappen, tariff-aware CV framing). Doesn't know which agencies and NGOs are actively hiring developers.

```

**Assistant reply** (verbatim):
```
Got it — captured **1143 chars** of CV. Moving on to suggestions.

_(I'm working without an AI right now — these are templated from your persona defaults.)_

Based on what you've told me, you'd also be competitive for:
  - Senior Senior Backend Developer (Public Sector / Civic Tech)
  - Lead Senior Backend Developer (Public Sector / Civic Tech)
  - Assistant Senior Backend Developer (Public Sector / Civic Tech)

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
Locked in: searching for **Backend Developer**.

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

### Turn 8 — phase `review` (2596 ms)

**User input**:
```
none
```

**Assistant reply** (verbatim):
```
Searching for **Backend Developer** in **Hamburg**…

**Found 4 job(s) total.**
  - **Tech / Engineering**: 4 job(s)

Reply with a **category name** to see the jobs in it.
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": 4,
  "jobs": [
    {
      "title": "Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte",
      "company": "plusYou GmbH",
      "location": "Hamburg, 20095, Hamburg, Deutschland",
      "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/14068-k18924.2331-S",
      "source": "bundesagentur"
    },
    {
      "title": "Java Backend Developer (gn)",
      "company": "workidentity GmbH",
      "location": "Hamburg, 20097, Hamburg, Deutschland",
      "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/13635-8fc9aa51_JB5134547-S",
      "source": "bundesagentur"
    },
    {
      "title": "B122-C01 Software Engineer / Cloud Backend Developer (m/w/d)",
      "company": "Jan Schreiner Private Arbeitsvermittlung Arbitex",
      "location": "Hamburg, Hamburg, Deutschland",
      "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002955851-S",
      "source": "bundesagentur"
    },
    {
      "title": "Backend Developer – C# & ASP.NET Core (m/w/d)",
      "company": "VinciFi GmbH",
      "location": "Hamburg, 20146, Hamburg, Deutschland",
      "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002943743-S",
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
**Tech / Engineering** — top 4 job(s):
  1. **Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte** — plusYou GmbH · Hamburg, 20095, Hamburg, Deutschland
     https://www.arbeitsagentur.de/jobsuche/jobdetail/14068-k18924.2331-S
  2. **Java Backend Developer (gn)** — workidentity GmbH · Hamburg, 20097, Hamburg, Deutschland
     https://www.arbeitsagentur.de/jobsuche/jobdetail/13635-8fc9aa51_JB5134547-S
  3. **B122-C01 Software Engineer / Cloud Backend Developer (m/w/d)** — Jan Schreiner Private Arbeitsvermittlung Arbitex · Hamburg, Hamburg, Deutschland
     https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002955851-S
  4. **Backend Developer – C# & ASP.NET Core (m/w/d)** — VinciFi GmbH · Hamburg, 20146, Hamburg, Deutschland
     https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1002943743-S

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
**Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte**
Company: plusYou GmbH
Location: Hamburg, 20095, Hamburg, Deutschland
Apply / view: https://www.arbeitsagentur.de/jobsuche/jobdetail/14068-k18924.2331-S

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
Here's the draft for **Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte** at **plusYou GmbH**:

---

_(I'm running without an AI right now — this is a template you can fill in. Configure a provider in /profile to get a personalised draft.)_

<Ihr Name>, Hamburg

plusYou GmbH
Hamburg, 20095, Hamburg, Deutschland

20.05.2026

Betreff: Bewerbung als Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte

Sehr geehrte Damen und Herren,

hiermit bewerbe ich mich um die ausgeschriebene Position als Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte bei plusYou GmbH. <Erkläre kurz, warum diese Rolle und dieses Unternehmen dich interessieren.>

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
  "letter": "_(I'm running without an AI right now — this is a template you can fill in. Configure a provider in /profile to get a personalised draft.)_\n\n<Ihr Name>, Hamburg\n\nplusYou GmbH\nHamburg, 20095, Hamburg, Deutschland\n\n20.05.2026\n\nBetreff: Bewerbung als Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte\n\nSehr geehrte Damen und Herren,\n\nhiermit bewerbe ich mich um die ausgeschriebene Position als Cloud Backend Developer (m/w/d) für zukunftsweisende Medienprojekte bei plusYou GmbH. <Erkläre kurz, warum diese Rolle und dieses Unternehmen dich interessieren.>\n\n<2. Absatz: Welche Qualifikationen aus deinem Lebenslauf passen zu der Stelle? Nenne konkrete Beispiele aus deiner bisherigen Erfahrung.>\n\n<3. Absatz: Welche persönlichen Eigenschaften und Soft-Skills machen dich für genau dieses Team und diese Aufgabe geeignet?>\n\nÜber die Gelegenheit zu einem persönlichen Gespräch würde ich mich sehr freuen.\n\nMit freundlichen Grüßen,\n\n<Ihr Name>",
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 13 — phase `cv_consult` (3 ms)

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

