<!-- SPDX-License-Identifier: Apache-2.0 -->

# Aïcha Loop 10.3 re-walk — Bug F Option B substrate live-validation (NO env-hook workaround)

**Walked**: 2026-05-20T20:43:07+00:00 (UTC)  |  **Persona**: Maria (Romania → Stuttgart) (maria)  |  **Cohort**: most-acute
**Server**: http://127.0.0.1:55032  |  **Provider**: Ollama llama3.1:8b
**Residency status**: EU citizen (Freizügigkeitsrecht)
**Friction notes**: Persistent language barrier despite full work rights; most home-care employers want B1 minimum formally. Care quality is excellent but cannot be demonstrated through a German-language interview. Wants employers who integrate non-fluent care workers via Audio-prep or buddy systems.

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
| Diagnostic text on empty-state | YES |
| Ausländerbehörde caveat on widen-location | no |
| Adjacent-criterion count parenthetical | no |
| Auto-relax slot offered | YES |
| Final-state summary block | YES |
| Start-fresh bridge → DISCOVER_ASK_ROLE | YES |

## Per-turn transcript

| # | Phase | User input | Elapsed | Notes |
|---|---|---|---|---|
| 1 | `discover` | `/start` | 7 ms | exec=`start_job_journey` |
| 2 | `discover` | `Altenpflegerin` | 61 ms | — |
| 3 | `discover` | `Stuttgart` | 2 ms | — |
| 4 | `discover` | `28` | 1 ms | — |
| 5 | `cv_check` | `RO: native, HU: native, IT: B1` | 1 ms | — |
| 6 | `inspire` | `Maria (Romania → Stuttgart) / Email: maria.walk@example.test / Phone: +49 30 1234-56…` | 2 ms | — |
| 7 | `preferences` | `no` | 1 ms | — |
| 8 | `review` | `none` | 2203 ms | — |
| 9 | `review` | `1` | 2522 ms | — |
| 10 | `review` | `1` | 3 ms | — |
| 11 | `review` | `yes` | 2072 ms | — |
| 12 | `discover` | `start fresh` | 4 ms | — |

## Latency summary

- **Turns**: 12
- **Total**: 6.9 s wall-clock
- **p50**: 4 ms
- **p95**: 2203 ms
- **max**: 2522 ms

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

### Turn 2 — phase `discover` (61 ms)

**User input**:
```
Altenpflegerin
```

**Assistant reply** (verbatim):
```
Got it: **Altenpflegerin**.

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
Stuttgart
```

**Assistant reply** (verbatim):
```
Noted: **Stuttgart**.

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
28
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
RO: native, HU: native, IT: B1
```

**Assistant reply** (verbatim):
```
Thanks. Quick summary:
  - Role: **Altenpflegerin**
  - Where: **Stuttgart**
  - Experience: **28**
  - Languages: **RO: native, HU: native, IT: B1**

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
Maria (Romania → Stuttgart)
Email: maria.walk@example.test
Phone: +49 30 1234-5678
Location: Stuttgart
Residency status: EU citizen (Freizügigkeitsrecht)

Profile / Summary:
Krankenschwester trained in Romania (1991); 28 years in a Romanian hospital followed by home-elderly-care after widowhood. Romanian- and Hungarian-native; conversational Italian (one year working in Italy in 2015); German A2. EU citizen — Freizügigkeitsrecht under §2 FreizügG/EU.

Experience:
  - 2019 - 2026 — Healthcare role, Stuttgart
  - 2016 - 2019 — Prior Healthcare role

Skills:
  - 28 years of clinical / care experience
  - Multi-language patient communication
  - Geriatric / palliative care
  - Cultural-bridge home care

Languages: RO: native, HU: native, IT: B1, DE: A2

Friction context: Persistent language barrier despite full work rights; most home-care employers want B1 minimum formally. Care quality is excellent but cannot be demonstrated through a German-language interview. Wants employers who integrate non-fluent care workers via Audio-prep or buddy systems.

```

**Assistant reply** (verbatim):
```
Got it — captured **1059 chars** of CV. Moving on to suggestions.

_(I'm working without an AI right now — these are templated from your persona defaults.)_

Based on what you've told me, you'd also be competitive for:
  - Senior Altenpflegerin
  - Lead Altenpflegerin
  - Assistant Altenpflegerin

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
Locked in: searching for **Altenpflegerin**.

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

### Turn 8 — phase `review` (2203 ms)

**User input**:
```
none
```

**Assistant reply** (verbatim):
```
Searching for **Altenpflegerin** in **Stuttgart**…

No matches found for **Altenpflegerin** in **Stuttgart** with these preferences.

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

### Turn 9 — phase `review` (2522 ms)

**User input**:
```
1
```

**Assistant reply** (verbatim):
```
OK — re-running search with **Widen location** applied: searching for **Altenpflegerin** in **anywhere**…

No matches found for **Altenpflegerin** in **Stuttgart** with these preferences.

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

  1. **Senior Altenpflegerin**
  2. **Lead Altenpflegerin**
  3. **Assistant Altenpflegerin**

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

### Turn 11 — phase `review` (2072 ms)

**User input**:
```
yes
```

**Assistant reply** (verbatim):
```
OK — added 3 lateral role(s). Re-running search for **Altenpflegerin, Senior Altenpflegerin, Lead Altenpflegerin, Assistant Altenpflegerin** in **Stuttgart**…

No matches found for **Altenpflegerin, Senior Altenpflegerin, Lead Altenpflegerin, Assistant Altenpflegerin** in **Stuttgart** with these preferences.

You've tried these widenings:
  - **Widened location** — searched without the location filter
  - **Tried lateral roles** — Senior Altenpflegerin, Lead Altenpflegerin, Assistant Altenpflegerin

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

