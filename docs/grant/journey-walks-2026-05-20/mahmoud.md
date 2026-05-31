<!-- SPDX-License-Identifier: Apache-2.0 -->

# Journey walk — Mahmoud (Syria → Hamburg)

> Raw test transcript: this document is a verbatim capture from an internal QA walk (local test server, Ollama provider). It is kept as evidence of a live end-to-end run; internal loop/debug bookkeeping has been removed from the narrative.

**Walked**: 2026-05-20 (UTC)  |  **Persona**: Mahmoud (Syria → Hamburg) (mahmoud)  |  **Cohort**: most-acute
**Provider**: Ollama llama3.1:8b (local test server)
**Residency status**: §4 AsylG subsidiary protection
**Friction notes**: Ausbildung openings are scattered across IHK/HwK portals and informal Handwerkskammer noticeboards. CV format expected for Ausbildung (Bewerbungsmappe convention) differs from Festanstellung. Vorstellungsgespräch with a Handwerksmeister is the typical interview format.

## Purpose

A live end-to-end walk of the guided job-search journey for the
Mahmoud persona, with the persona profile resolved from a real
classification of the pasted CV (rather than a hard-coded fixture).
The walk records each turn, the journey phase, and the assistant
reply so the empty-state and widening behaviour can be reviewed.

## Empty-state behaviour summary

| Signal | Observed |
|---|---|
| Diagnostic text on empty-state | YES |
| Ausländerbehörde caveat on widen-location | YES |
| Adjacent-criterion count parenthetical | no |
| Auto-relax slot offered | YES |
| Final-state summary block | YES |
| Start-fresh bridge → DISCOVER_ASK_ROLE | YES |

## Per-turn transcript

| # | Phase | User input | Elapsed | Notes |
|---|---|---|---|---|
| 1 | `discover` | `/start` | 7 ms | exec=`start_job_journey` |
| 2 | `discover` | `Auszubildender Anlagenmechaniker SHK` | 60 ms | — |
| 3 | `discover` | `Hamburg` | 2 ms | — |
| 4 | `discover` | `2` | 1 ms | — |
| 5 | `cv_check` | `AR: native, DE: B2 (trades)` | 1 ms | — |
| 6 | `inspire` | `Mahmoud (Syria → Hamburg) / Email: mahmoud.walk@example.test / Phone: +49 30 1234-56…` | 2 ms | — |
| 7 | `preferences` | `no` | 1 ms | — |
| 8 | `review` | `none` | 2664 ms | — |
| 9 | `review` | `1` | 2 ms | — |
| 10 | `review` | `yes` | 1940 ms | — |
| 11 | `review` | `1` | 2353 ms | — |
| 12 | `discover` | `start fresh` | 4 ms | — |

## Latency summary

- **Turns**: 12
- **Total**: 7.0 s wall-clock
- **p50**: 4 ms
- **p95**: 2353 ms
- **max**: 2664 ms

## Per-turn detail (verbatim)

### Turn 1 — phase `discover` (7 ms)

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
Auszubildender Anlagenmechaniker SHK
```

**Assistant reply** (verbatim):
```
Got it: **Auszubildender Anlagenmechaniker SHK**.

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
2
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
AR: native, DE: B2 (trades)
```

**Assistant reply** (verbatim):
```
Thanks. Quick summary:
  - Role: **Auszubildender Anlagenmechaniker SHK**
  - Where: **Hamburg**
  - Experience: **2**
  - Languages: **AR: native, DE: B2 (trades)**

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

### Turn 6 — phase `inspire` (2 ms)

**User input**:
```
Mahmoud (Syria → Hamburg)
Email: mahmoud.walk@example.test
Phone: +49 30 1234-5678
Location: Hamburg
Residency status: §4 AsylG subsidiary protection

Profile / Summary:
22 years old; arrived as unaccompanied minor in 2018, reunited with family in 2020. Did not complete the Syrian Abitur due to displacement. Informal plumber's helper experience (family workshop in Aleppo). Completed Integrationskurs (B1) and Berufssprachkurs (B2 für Handwerk). Looking for an Ausbildung as Anlagenmechaniker für Sanitär, Heizung, Klima.

Experience:
  - 2019 - 2026 — Trades / Handwerk role, Hamburg
  - 2016 - 2019 — Prior Trades / Handwerk role

Skills:
  - Plumbing basics (informal)
  - German B2 for trades context
  - Berufssprachkurs completion
  - Customer-facing trades demeanor

Languages: AR: native, DE: B2 (trades)

Friction context: Ausbildung openings are scattered across IHK/HwK portals and informal Handwerkskammer noticeboards. CV format expected for Ausbildung (Bewerbungsmappe convention) differs from Festanstellung. Vorstellungsgespräch with a Handwerksmeister is the typical interview format.

```

**Assistant reply** (verbatim):
```
Got it — captured **1103 chars** of CV. Moving on to suggestions.

_(I'm working without an AI right now — these are templated from your persona defaults.)_

Based on what you've told me, you'd also be competitive for:
  - Senior Auszubildender Anlagenmechaniker SHK
  - Lead Auszubildender Anlagenmechaniker SHK
  - Assistant Auszubildender Anlagenmechaniker SHK

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
Locked in: searching for **Auszubildender Anlagenmechaniker SHK**.

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

### Turn 8 — phase `review` (2664 ms)

**User input**:
```
none
```

**Assistant reply** (verbatim):
```
Searching for **Auszubildender Anlagenmechaniker SHK** in **Hamburg**…

No matches found for **Auszubildender Anlagenmechaniker SHK** in **Hamburg** with these preferences.

What next?
  1. **Try lateral roles** — search 3 related role name(s) too
  2. **Widen location** — search without the location filter
     Note: changing your search location may not be compatible with your current residence-permit ties. We recommend checking with your local Ausländerbehörde or Migrationsberatungsstelle before relocating.
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

### Turn 9 — phase `review` (2 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
I can also search these related role names:

  1. **Senior Auszubildender Anlagenmechaniker SHK**
  2. **Lead Auszubildender Anlagenmechaniker SHK**
  3. **Assistant Auszubildender Anlagenmechaniker SHK**

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

### Turn 10 — phase `review` (1940 ms)

**User input**:
```
yes
```

**Assistant reply** (verbatim):
```
OK — added 3 lateral role(s). Re-running search for **Auszubildender Anlagenmechaniker SHK, Senior Auszubildender Anlagenmechaniker SHK, Lead Auszubildender Anlagenmechaniker SHK, Assistant Auszubildender Anlagenmechaniker SHK** in **Hamburg**…

No matches found for **Auszubildender Anlagenmechaniker SHK, Senior Auszubildender Anlagenmechaniker SHK, Lead Auszubildender Anlagenmechaniker SHK, Assistant Auszubildender Anlagenmechaniker SHK** in **Hamburg** with these preferences.

What next?
  1. **Widen location** — search without the location filter
     Note: changing your search location may not be compatible with your current residence-permit ties. We recommend checking with your local Ausländerbehörde or Migrationsberatungsstelle before relocating.
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

### Turn 11 — phase `review` (2353 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
OK — re-running search with **Widen location** applied: searching for **Auszubildender Anlagenmechaniker SHK, Senior Auszubildender Anlagenmechaniker SHK, Lead Auszubildender Anlagenmechaniker SHK, Assistant Auszubildender Anlagenmechaniker SHK** in **anywhere**…

No matches found for **Auszubildender Anlagenmechaniker SHK, Senior Auszubildender Anlagenmechaniker SHK, Lead Auszubildender Anlagenmechaniker SHK, Assistant Auszubildender Anlagenmechaniker SHK** in **Hamburg** with these preferences.

You've tried these widenings:
  - **Tried lateral roles** — Senior Auszubildender Anlagenmechaniker SHK, Lead Auszubildender Anlagenmechaniker SHK, Assistant Auszubildender Anlagenmechaniker SHK
  - **Widened location** — searched without the location filter

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

### Turn 12 — phase `discover` (4 ms)

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

Walk this transcript to verify the journey smoothness live for Mahmoud:

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

