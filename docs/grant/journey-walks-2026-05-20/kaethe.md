<!-- SPDX-License-Identifier: Apache-2.0 -->

# Journey walk — Käthe (German, nursing re-entrant)

> Raw test transcript: this document is a verbatim capture from an internal QA walk (local test server, Ollama provider). It is kept as evidence of a live end-to-end run; internal loop/debug bookkeeping has been removed from the narrative.

**Walked**: 2026-05-20 (UTC)  |  **Persona**: Käthe (German, nursing re-entrant) (kaethe)  |  **Cohort**: wider-friction
**Provider**: Ollama llama3.1:8b (local test server)
**Residency status**: German citizen (Freizügigkeit not applicable)
**Friction notes**: 12-year clinical absence: digital patient-record systems, electronic medication management, infection-control protocols, mandatory CE hours all changed since 2013. Hospitals expect a Wiedereinstiegsprogramm or Auffrischung course; her old CV reads as obsolete for 2026 conventions.

## Purpose

A live end-to-end walk of the guided job-search journey for the
Käthe persona, with the persona profile resolved from a real
classification of the pasted CV (rather than a hard-coded fixture).
The walk records each turn, the journey phase, and the assistant
reply so the empty-state and widening behaviour can be reviewed.

## Empty-state behaviour summary

| Signal | Observed |
|---|---|
| Diagnostic text on empty-state | YES |
| Ausländerbehörde caveat on widen-location | no |
| Adjacent-criterion count parenthetical | no |
| Auto-relax slot offered | YES |
| Final-state summary block | YES |
| Start-fresh bridge → DISCOVER_ASK_ROLE | YES |

## Per-turn transcript

| # | Phase | User input | Elapsed | Notes |
|---|---|---|---|---|
| 1 | `discover` | `/start` | 8 ms | exec=`start_job_journey` |
| 2 | `discover` | `Krankenschwester (Wiedereinstieg)` | 77 ms | — |
| 3 | `discover` | `Berlin` | 2 ms | — |
| 4 | `discover` | `14` | 2 ms | — |
| 5 | `cv_check` | `DE: native, EN: B1-clinical` | 1 ms | — |
| 6 | `inspire` | `Käthe (German, nursing re-entrant) / Email: kaethe.walk@example.test / Phone: +49 30…` | 3 ms | — |
| 7 | `preferences` | `no` | 1 ms | — |
| 8 | `review` | `none` | 2886 ms | — |
| 9 | `review` | `1` | 2513 ms | — |
| 10 | `review` | `1` | 3 ms | — |
| 11 | `review` | `yes` | 2047 ms | — |
| 12 | `discover` | `start fresh` | 2 ms | — |

## Latency summary

- **Turns**: 12
- **Total**: 7.5 s wall-clock
- **p50**: 3 ms
- **p95**: 2513 ms
- **max**: 2886 ms

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

### Turn 2 — phase `discover` (77 ms)

**User input**:
```
Krankenschwester (Wiedereinstieg)
```

**Assistant reply** (verbatim):
```
Got it: **Krankenschwester (Wiedereinstieg)**.

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
Berlin
```

**Assistant reply** (verbatim):
```
Noted: **Berlin**.

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

### Turn 4 — phase `discover` (2 ms)

**User input**:
```
14
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
DE: native, EN: B1-clinical
```

**Assistant reply** (verbatim):
```
Thanks. Quick summary:
  - Role: **Krankenschwester (Wiedereinstieg)**
  - Where: **Berlin**
  - Experience: **14**
  - Languages: **DE: native, EN: B1-clinical**

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
Käthe (German, nursing re-entrant)
Email: kaethe.walk@example.test
Phone: +49 30 1234-5678
Location: Berlin
Residency status: German citizen (Freizügigkeit not applicable)

Profile / Summary:
Krankenschwester certified 1998. Clinical nursing on a cardiology ward at a Berlin hospital from 1999 to 2013 (14 years), then 12 years out of the workforce for child-rearing (three children, ages 14/11/8 now in school). German-native; reads English clinical literature. Looking for a Wiedereinstieg programme.

Experience:
  - 2019 - 2026 — Healthcare role, Berlin
  - 2016 - 2019 — Prior Healthcare role

Skills:
  - Clinical nursing (cardiology speciality, 1999-2013)
  - Patient-facing communication in German
  - Re-entrant-aware CV reframing needed
  - Adaptable to digital patient-record systems with re-orientation

Languages: DE: native, EN: B1-clinical

Friction context: 12-year clinical absence: digital patient-record systems, electronic medication management, infection-control protocols, mandatory CE hours all changed since 2013. Hospitals expect a Wiedereinstiegsprogramm or Auffrischung course; her old CV reads as obsolete for 2026 conventions.

```

**Assistant reply** (verbatim):
```
Got it — captured **1155 chars** of CV. Moving on to suggestions.

_(I'm working without an AI right now — these are templated from your persona defaults.)_

Based on what you've told me, you'd also be competitive for:
  - Senior Krankenschwester (Wiedereinstieg)
  - Lead Krankenschwester (Wiedereinstieg)
  - Assistant Krankenschwester (Wiedereinstieg)

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
Locked in: searching for **Krankenschwester (Wiedereinstieg)**.

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

### Turn 8 — phase `review` (2886 ms)

**User input**:
```
none
```

**Assistant reply** (verbatim):
```
Searching for **Krankenschwester (Wiedereinstieg)** in **Berlin**…

No matches found for **Krankenschwester (Wiedereinstieg)** in **Berlin** with these preferences.

What next?
  1. **Widen location** — search without the location filter
  2. **Try lateral roles** — search 3 related role name(s) too
  3. **Auto-relax** — let the system suggest the next widening step (or type `auto` / `suggest` / `guide me`)
  4. **Retry** the same search (or type `retry` / `nochmal` / `search again`)
  5. **Give up** — end this journey (or type `give up` / `done` / `fertig`)
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": 0,
  "jobs": [],
  "categories": [],
  "navigateTo": null
}
```

### Turn 9 — phase `review` (2513 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
OK — re-running search with **Widen location** applied: searching for **Krankenschwester (Wiedereinstieg)** in **anywhere**…

No matches found for **Krankenschwester (Wiedereinstieg)** in **Berlin** with these preferences.

What next?
  1. **Try lateral roles** — search 3 related role name(s) too
  2. **Auto-relax** — let the system suggest the next widening step (or type `auto` / `suggest` / `guide me`)
  3. **Retry** the same search (or type `retry` / `nochmal` / `search again`)
  4. **Give up** — end this journey (or type `give up` / `done` / `fertig`)
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": 0,
  "jobs": [],
  "categories": [],
  "navigateTo": null
}
```

### Turn 10 — phase `review` (3 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
I can also search these related role names:

  1. **Senior Krankenschwester (Wiedereinstieg)**
  2. **Lead Krankenschwester (Wiedereinstieg)**
  3. **Assistant Krankenschwester (Wiedereinstieg)**

Reply **yes** to include all of them, **no** to skip, or pick by number (e.g. `1` or `1, 3`).
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

### Turn 11 — phase `review` (2047 ms)

**User input**:
```
yes
```

**Assistant reply** (verbatim):
```
OK — added 3 lateral role(s). Re-running search for **Krankenschwester (Wiedereinstieg), Senior Krankenschwester (Wiedereinstieg), Lead Krankenschwester (Wiedereinstieg), Assistant Krankenschwester (Wiedereinstieg)** in **Berlin**…

No matches found for **Krankenschwester (Wiedereinstieg), Senior Krankenschwester (Wiedereinstieg), Lead Krankenschwester (Wiedereinstieg), Assistant Krankenschwester (Wiedereinstieg)** in **Berlin** with these preferences.

You've tried these widenings:
  - **Widened location** — searched without the location filter
  - **Tried lateral roles** — Senior Krankenschwester (Wiedereinstieg), Lead Krankenschwester (Wiedereinstieg), Assistant Krankenschwester (Wiedereinstieg)

All returned 0 matches.

What next?
  1. **Start fresh** — clear this search and try with different criteria (or type `start fresh` / `neu starten` / `restart`)
  2. **Retry** the same search (or type `retry` / `nochmal` / `search again`)
  3. **Give up** — end this journey (or type `give up` / `done` / `fertig`)
```

**Extra response fields** (beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": 0,
  "jobs": [],
  "categories": [],
  "navigateTo": null
}
```

### Turn 12 — phase `discover` (2 ms)

**User input**:
```
start fresh
```

**Assistant reply** (verbatim):
```
OK — clearing your old search. Let's try with different criteria.

**1. What kind of role this time?** (e.g., "Pflegehelfer", "bartender", "backend engineer")
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

Walk this transcript to verify the journey smoothness live for Käthe:

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

