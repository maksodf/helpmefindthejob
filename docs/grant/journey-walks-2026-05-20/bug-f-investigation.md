<!-- SPDX-License-Identifier: Apache-2.0 -->

# Bug F investigation — persona-classification flow (Loop 9.2)

**Investigation date**: 2026-05-20
**Loop**: 9.2 (read-only investigation; NO fix in this loop)
**Time-box**: ~1-2 h
**Verdict**: **OUTCOME B confirmed** — the 7-persona fixture panel is **research/test infrastructure**, NOT wired to production user-facing classification.

---

## TL;DR

Two parallel persona systems exist in the codebase. They have **disjoint** ID namespaces and serve different purposes.

| System | File | IDs | Wired to production? |
|---|---|---|---|
| **Industry registry** | `company_discovery/personas.py` | 15 IDs: `healthcare-management`, `tech`, `data`, `design`, `marketing`, `finance`, `product-management`, `education`, `legal`, `sales`, `operations`, `healthcare-clinical`, `hr`, `support`, `media` | **YES** — drives all production persona logic |
| **Fixture panel** | `company_discovery/persona_fixtures.py` | 7 slugs: `aicha`, `yusuf`, `olga`, `mahmoud`, `maria`, `kaethe`, `tobias` | **NO** — never lands in `UserProfile.persona_id` for any real user |

`UserProfile.persona_id` (default `"healthcare-management"` per `models.py:274`) only ever takes values from the **industry registry**. The 7 fixture slugs never appear in production `persona_id` values. Every code path that updates `persona_id` (registration, find-jobs auto-mapping, settings dropdown, persona-suggest, onboarding wizard) sources its value from the registry.

The Bug C piece-3 persona-aware behavior (Ausländerbehörde caveat + constrained ordering) is gated by `journey.visa_constrained`, which is computed by looking up `profile.persona_id` against the fixture panel via `_persona_fixture_for(persona_id)` (`app.py:3869`). Because `persona_id` is always a registry ID and never a fixture slug, the fixture lookup ALWAYS returns `None` → `residency_status = ""` → `classify_visa_constraint("")` → `False`. **`visa_constrained` is silently always `False` in production.**

Decision 21 positions the 7-persona panel as the project's core architecture. The piece-3 doctrine (constrained ordering + Ausländerbehörde caveat for §16d / §24 / §4 AsylG personas) cannot fire in production until the persona-classification flow is rewired.

---

## Q1 — Default value of `persona_id` on a fresh `UserProfile`

**Fact**: `"healthcare-management"` (a registry ID; NOT a fixture slug).

**Code reference**: `company_discovery/models.py:274`

```python
@dataclass
class UserProfile:
    ...
    persona_id: str = "healthcare-management"
```

**Fresh-user constructor sites in app.py**:
- `app.py:728` — `return UserProfile(user_id=user_id, persona_id=DEFAULT_PERSONA_ID)` (also `"healthcare-management"`)
- `app.py:731-733` — `UserProfile(user_id=user_id, persona_id=DEFAULT_PERSONA_ID)` in `update_profile` fallback path

**The default has no relationship to the 7 fixture panel.** It biases brand-new users toward healthcare-management AI prompts, ranking weights, and watchlist templates — which is fine for users who actually are in that vertical and wrong for the migrant-class personas the project positions itself around.

---

## Q2 — Production code paths that update `persona_id`

Three paths. All source values from the 15-industry **registry**, not the fixture panel.

### Path A — Auto-mapping from search bucket (`app.py:3354`)

```python
mapped_persona = persona_for_bucket(bucket_key)
if mapped_persona and profile.persona_id != mapped_persona:
    profile.persona_id = mapped_persona
```

Triggered: every time `chat_handler_find_jobs` runs (user types a search query, slash command `/find`, natural-language intent classifier, etc.). The role text → bucket → registry-persona mapping lives at `company_discovery/job_type_filter.py:659-674`:

```python
BUCKET_TO_PERSONA: dict[str, str] = {
    "software_engineer": "tech",
    "data_engineer": "data",
    "product_manager": "product-management",
    "designer": "design",
    "marketing": "marketing",
    "sales": "sales",
    "finance": "finance",
    "consulting": "operations",
    "customer_success": "support",
    "healthcare_management": "healthcare-management",
    "pflegehelfer": "healthcare-clinical",
    # Hospitality buckets have no dedicated persona ...
}
```

**For an Aïcha-class user typing "Registered nurse" or "Krankenpfleger" → bucket detection** (`pflegehelfer` if matched) → `persona_id = "healthcare-clinical"`. Still a registry ID. The fixture slug `aicha` is never assigned by this path.

### Path B — Explicit user pick via UI (`app.py:730-755`, `app.py:6451+`)

`POST /api/profile` with `personaId` payload:

```python
def update_profile(self, user_id: str, payload: dict[str, Any]) -> UserProfile:
    ...
    persona_id = str(
        payload.get("personaId")
        or payload.get("persona_id")
        or existing.persona_id
    )
```

UI surfaces that hit this endpoint:

- **Onboarding wizard step 2** ("Confirm your persona") — `static/index.html:1426-1438`. Populates `<select id="wizardPersona">` from `state.personas` (= bootstrap `personas`).
- **Settings dropdown** ("Persona & profile") — `static/index.html:824-862`. Populates `<input id="profilePersona" list="personaDatalist">` from the same `state.personas` source.

The `state.personas` array is sourced from server bootstrap at `app.py:588`:

```python
"personas": list_personas_summary(),
```

`list_personas_summary()` is defined at `company_discovery/personas.py:1034-1046`:

```python
def list_personas_summary() -> list[dict[str, object]]:
    return [
        {"id": persona.id, "label": persona.label, ...}
        for persona in PERSONAS.values()
    ]
```

This iterates the **15-industry registry**, never the fixture panel. **Therefore: the dropdown UI offers only 15 industry IDs; the user cannot select "aicha" / "yusuf" / etc. through any UI surface.**

### Path C — AI-suggested persona via CV text (`app.py:6566`, `app.py:6586`)

Endpoint `POST /api/profile/persona-suggest`:

```python
from company_discovery.personas import PERSONAS, suggest_persona_from_text
ranked = suggest_persona_from_text(cv_text, top_k=5)
```

`suggest_persona_from_text` at `company_discovery/personas.py:1009-1032`:

```python
def suggest_persona_from_text(text, *, top_k=3):
    ...
    for pid, persona in PERSONAS.items():
        terms = _persona_search_terms(persona)
        ...
```

Again iterates the **registry**, never the fixture panel. CV-text ranking returns industry IDs (`tech`, `healthcare-clinical`, etc.) — never `aicha` / `yusuf` / etc.

The onboarding wizard calls this endpoint when the user pastes a CV (`static/app.js:1927`) and pre-selects the top suggestion in step 2's dropdown.

### What I did NOT find

- **No registration-time persona-classification flow.** `POST /api/auth/register` (`app.py:5961+`) does not touch `persona_id`. A fresh user is created with `persona_id = DEFAULT_PERSONA_ID = "healthcare-management"`.
- **No chat-router heuristic** that detects persona-class signals (Anerkennung, §16d, residency status, etc.) and updates `persona_id` accordingly.
- **No persona-fixture-aware UI** anywhere. `grep -rE '"(aicha|yusuf|olga|mahmoud|maria|kaethe|tobias)"' --include="*.py" company_discovery/ app.py` returns hits only in `persona_fixtures.py` (definitions) and `tests/`. Production-side: zero references.

---

## Q3 — User-facing surface, trigger, likelihood

There ARE user-facing persona surfaces (onboarding wizard + settings dropdown + CV-suggest). They are **wired to the registry, not the fixture panel**. So:

- A real user CAN explicitly choose their persona (between the 15 industry IDs).
- A real user CANNOT choose `aicha` / `yusuf` / etc. through any UI surface.
- The CV-suggest engine ranks against the 15 registry personas; it can't propose a fixture slug.
- Path A auto-set during chat_handler_find_jobs maps role buckets to registry IDs only.

**Likelihood a real Aïcha-class user ends up with `persona_id="aicha"` in production**: **zero.** No code path produces that value.

---

## Q4 — If not wired: confirm gap + scope size

**Gap confirmed.** The fixture panel is consumed by exactly two production code paths, both of which always fail to resolve a fixture for any real user:

1. **`company_discovery/analysis.py:42-66`** — `_persona_fixture_for(persona_id)`:
   ```python
   def _persona_fixture_for(persona_id):
       if not persona_id:
           return None
       from company_discovery.persona_fixtures import PERSONAS
       for fixture in PERSONAS:
           if fixture.slug == persona_id:
               return fixture
       return None
   ```
   Called from `analysis.py:119` to enrich AI prompts with persona-fixture context (friction notes, cv_summary, etc.). Always returns `None` for production users.

2. **`app.py:3858-3871`** — Bug C piece 3 dispatcher, the `visa_constrained` classification:
   ```python
   from company_discovery.analysis import _persona_fixture_for
   ...
   fixture = _persona_fixture_for(pid)
   residency = getattr(fixture, "residency_status", "") or ""
   journey2.visa_constrained = classify_visa_constraint(residency)
   ```
   Always sets `visa_constrained=False` in production because `_persona_fixture_for` returns `None`.

**Effect on shipped Bug C work**:
- **Piece 3 persona-aware ordering** (constrained vs unconstrained widening order): unreachable for real users. All users see the unconstrained order (widen first, drop seniority, then try laterals).
- **Piece 3 Ausländerbehörde caveat**: never renders for real users.
- **Piece 4 auto-relax ordering** (depends on `visa_constrained` via `next_auto_relax_suggestion`): same gap.

**Effect on AI prompts**: `analysis.py`'s persona-fixture enrichment (friction_notes, cv_summary, residency_status, scenarios) never fires for real users. AI prompts get only the registry-persona's `default_target_roles` / `default_industry` / system-prompt context. The migrant-aware friction context (Aïcha's §16d / Yusuf's Blue Card / Olga's §24 / Mahmoud's §4 AsylG / Maria's EU citizen / Käthe's Wiedereinstieg / Tobias's Former banker) is never injected.

---

## Scope of the real fix (sketch — not a commitment)

The fix is non-trivial because the two persona systems serve **genuinely different functions** that the codebase hasn't disentangled:

| Function | Today | What needs reconciliation |
|---|---|---|
| Industry-segment ranking + watchlist templates | 15-registry | Keep; these are useful breadth signals |
| Friction-class-aware UX (Bug C piece 3) | Reads fixture via `_persona_fixture_for` | Needs a real classification path |
| AI-prompt persona context (`analysis.py`) | Falls back to registry when fixture lookup fails | Needs both — registry for breadth, fixture for friction context |
| Bias-methodology testing | Direct fixture references (test code) | No change needed — test-only |

Two structurally different architectures possible:

### Architecture α — Add a second profile field

`UserProfile.persona_id` stays as registry ID (15 industries, used for ranking + templates).

`UserProfile.friction_class` (NEW) is the fixture-equivalent classification (7 slugs OR a more general migrant/native + visa-class taxonomy). Drives Bug C piece 3, Ausländerbehörde caveat, friction-class AI prompt enrichment.

Pros: clean separation of concerns; doesn't break existing registry-based UX.
Cons: extra field; need to migrate existing profiles (default `friction_class=None` is fine since the gate already defaults `visa_constrained=False`).

### Architecture β — Subsume registry into a unified fixture-class

Replace the 15-industry registry with the 7-fixture panel (or a third superset that covers both axes). `UserProfile.persona_id` takes fixture slugs.

Pros: one persona system; simpler mental model.
Cons: requires deleting the existing 15-registry's ranking + templates work OR mapping each industry to a friction class which loses fidelity (most fixture personas aren't industry-specific — Aïcha is healthcare but Yusuf is engineering and Olga is tech, all "migrant most-acute" but in different industries).

**I lean Architecture α (additive field).** Less destructive; existing registry-based UX continues to work; friction-class is a parallel signal that gates piece-3 doctrine and AI-prompt friction enrichment.

---

## Five options for the real-user friction-class classification flow

Per operator directive, brief honest assessment of each.

### Option 1 — Onboarding survey ("which describes you?" with 7 persona cards)

**Mechanic**: After registration, present 7 cards each describing one persona archetype. User picks.

| Dimension | Assessment |
|---|---|
| Effort | ~6-10 h (UI cards + i18n + backend `friction_class` field + tests) |
| Privacy | High concern. Asking residency status explicitly is the strongest signal but also the most sensitive PII. Decision 12 says no PII in commits; runtime is different but still sensitive. Need clear consent UI ("This helps us tailor advice — you can skip.") |
| UX | Adds a step that some users will skip. Migrant users may be wary of self-classifying residency status to an app on first launch. |
| Doctrine fit | Honest if framed correctly ("we don't store this; it tailors which legal-friction guidance you see"). Civic-commons positioning compatible. |

**Subjective risk**: opt-in rate may be low for migrants (the most acute persona class) precisely because they're most cautious about residency disclosure. Could end up with a self-selected sample that under-represents the personas the project most needs to serve.

### Option 2 — CV-text inference (heuristic / keyword detection)

**Mechanic**: When the user pastes their CV in the `cv_check` phase, scan for friction-class signals (§16d, Anerkennung, Anabin, BIBB, Blue Card, EU Blue Card, §24 Sonderaufenthalt, §4 AsylG, "Wiedereinstieg", "Former <profession>", language CEFR markers indicating non-native, etc.) and set `friction_class` based on the highest-confidence match. `persona_fixtures.py:744-749` already has a curated keyword set per fixture — could be the starting point.

| Dimension | Assessment |
|---|---|
| Effort | ~4-6 h (keyword bank + classifier function + integration in cv_check + tests) |
| Privacy | Lower than Option 1 — uses data the user already pasted. No new sensitive question. |
| UX | Invisible to the user (good when classification works; opaque when it gets it wrong). |
| Doctrine fit | Strong — deterministic, no LLM call, no hallucination. Matches the cache-only diagnostic doctrine from Bug C piece 2. |

**Subjective risk**: heuristic accuracy is unknown. Need a calibration pass (the same 7 personas' CV summaries against the classifier). Also: requires CV-paste to fire; users who skip CV-paste don't get classified.

### Option 3 — Account-settings dropdown (post-onboarding, user picks)

**Mechanic**: A second dropdown in Settings, parallel to the existing persona dropdown, labeled "Your situation" or "Friction class" with the 7 archetypes.

| Dimension | Assessment |
|---|---|
| Effort | ~3-4 h (Settings UI + backend field + tests) |
| Privacy | Medium — user opts in by visiting Settings. Most users won't. |
| UX | Most users never adjust it. Low default-coverage. |
| Doctrine fit | Compatible but yields low coverage in practice. |

**Subjective risk**: highest risk of being dead UI — most users won't open Settings. Worst-case: a setting that exists for show but doesn't actually drive behavior for anyone.

### Option 4 — Persona-selection at first search (deferred classification until search context)

**Mechanic**: When the user fires their first search and the system would have triggered the Bug C empty-state recovery flow, ask one question: "Do any of these apply to you? [§16d Anerkennung / EU Blue Card / §24 protection / §4 asylum / EU citizen / Wiedereinstieg / Former <field>]". Use the answer to set `friction_class` AND to potentially adjust the search itself.

| Dimension | Assessment |
|---|---|
| Effort | ~3-5 h (chat-router intent + journey state transition + tests) |
| Privacy | Better than Option 1 — asked in context, with clear reason ("affects which widening suggestions I'll show next"). |
| UX | Adds a turn during the journey. Some users will skip. But the question is tied to a concrete need (their search just returned 0), so motivation is higher. |
| Doctrine fit | Strong — context-tied, opt-in, deterministic. |

**Subjective risk**: only fires when the user hits an empty-state. Users who get results on the first search never get classified. May still need to combine with Option 2.

### Option 5 — Combination: CV-inference (Option 2) + user confirmation (Option 1 light)

**Mechanic**: When the user pastes their CV in `cv_check`, run the heuristic classifier. If it produces a high-confidence match, set `friction_class` and surface a confirmation: "Looks like you're in the §16d Anerkennung process — is that right? [Yes / No / Skip]". If low/no match, leave `friction_class=None`.

| Dimension | Assessment |
|---|---|
| Effort | ~7-10 h (Option 2 work + confirmation UI + tests) |
| Privacy | Lower than pure Option 1 — only ASKS when there's already strong textual evidence. Avoids cold-cold "are you a migrant?" question. |
| UX | Mostly invisible; one-step confirmation when classifier fires. |
| Doctrine fit | Strong — deterministic classifier, user has final say (honors consent doctrine), graceful degradation when heuristic can't classify. |

**Subjective risk**: most complex of the five but probably the best UX. Requires both the classifier work AND the confirmation flow.

---

## Recommended path (subjective — operator decides)

**I lean Option 5 (combination)** as the architecturally cleanest fit for the project's civic-commons positioning:

- **Deterministic** (matches Bug C piece 2 doctrine — no LLM hallucination of friction class)
- **Consent-respecting** (user confirms, can skip)
- **Privacy-aware** (uses data the user already provided; doesn't introduce a residency-status question out of context)
- **Graceful degradation** (when classifier can't classify, `friction_class=None` and Bug C piece 3 falls back to unconstrained ordering — which is the current production behavior anyway)
- **Compatible with Architecture α** (additive field, doesn't break existing registry-based UX)

**Caveat**: this is a substantive product-design slice. It's plausibly bigger than the entire PART 6 effort to date. The honest framing for the grant application is that Decision 21's 7-persona panel is **research infrastructure** that informed the design + bias testing, and that **real-user friction-class classification is on the post-grant roadmap** — to be built in Phase 2 with onboarding + UX + privacy design done properly, not as a Bug-F follow-up patch.

**Or, alternatively**: ship the workaround for Loop 9.3 validation (manually set `persona_id="aicha"` on the test user) AND surface this as a **Hard Rule 1 exception** — the persona-classification flow IS a new product feature, but it's a feature that makes the project's core positioning actually true for real users. The operator's product-design-mode doctrine (CLAUDE.md global instructions) calls for "ambitious in discovery, conservative in execution" — Bug F is discovery-mode evidence; execution comes after the grant application.

---

## Doctrine implications

The honest framing matters for the grant application + outreach drafts:

1. **What the codebase does today**: registry-based industry-segment personas, with a 7-fixture panel used for bias testing + design archetype consistency.
2. **What the project positions itself as**: a friction-class-aware civic commons that adapts UX to the 7 personas' specific needs (§16d, Blue Card, §24, §4 AsylG, EU citizen, Wiedereinstieg, Former-career).
3. **The gap**: production users land in (1); the project's narrative weight is on (2).

**Outreach implication**: descriptions like "Aïcha sees the Ausländerbehörde caveat on widen-location" are aspirational for the current production code, not actual. Phrasings should either (a) clarify that this is the doctrine the system is designed for once friction-class classification ships, or (b) limit live demos to manually-tagged fixture users until Phase 2 ships the real flow.

**Grant-application implication**: position the 7-persona panel honestly as design archetype + bias-testing infrastructure; commit to the real-user classification flow as a Phase 2 deliverable. Don't claim production-ready friction-class-aware UX.

---

## What this means for Loop 9.3

The operator-approved workaround (Loop 9.3 re-walk with `persona_id="aicha"` set manually on the test user) is the right pragmatic move. It validates that the code is CORRECT given correct inputs:

- `_persona_fixture_for("aicha")` resolves to the Aïcha fixture
- `classify_visa_constraint("§16d AufenthG (...)")` returns True
- `visa_constrained=True` activates piece-3 constrained ordering + Ausländerbehörde caveat
- Pieces 5/6 live-validate end-to-end

The workaround is **honest** because the post-9.3 status sync will document it as such: "test user manually persona-tagged because the real-user persona-classification flow is the subject of Bug F follow-up." This separates "is the code correct given correct inputs?" (yes — validated by Loop 9.3) from "are inputs correct for real users?" (no — Bug F).

---

## Status sync

Bug F investigation complete (~1.5 h, within time-box). **Outcome B confirmed.** Five options sketched with assessment. Recommendation: Option 5 (combination) as architecturally cleanest; Architecture α (additive `friction_class` field) for the structural framing. Honest framing for grant + outreach implications surfaced.

Holding for operator decision on:
1. Bug F fix path (Option 5 + Architecture α, or different combination)
2. Scope: Phase 2 deliverable vs in-grant-window slice vs Hard Rule 1 exception
3. Outreach-draft + grant-narrative honesty adjustments (do these need to be revised before submission?)
4. Loop 9.3 release with persona_id workaround
