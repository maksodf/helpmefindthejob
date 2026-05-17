# HANDOFF — emergency session restart

**Saved at:** 2026-05-16 (session compacted from earlier work + Phase 1 sprint)
**Project:** DirectJob Scout (chat-first DACH job-search SaaS, app.khalo.org)
**Not a git repo** — no commit was possible. State is preserved on disk only.

---

## ⚠ Mid-flight when interrupted

**`app.py:APP_VERSION` is bumped to `"0.91.0"` BUT NOT DEPLOYED.**
Production is still running `0.90.0`. Local code contains three bug fixes
that need to ship.

### Exact next step (resume here):

```
TAG=0.91.0 /Users/fouad./Desktop/NasserMCPserver/scripts/deploy-with-backup.sh
```

Then verify live: `curl -s https://app.khalo.org/api/health` should show
`"version": "0.91.0"`.

---

## What 0.91.0 fixes (uncommitted local work)

Three real bugs found in self-audit after the user challenged me to stop
hiding behind "honest gaps":

### Bug A — system prompt's destructive-tool list was stale
- **File:** `company_discovery/tool_use_router.py:255–275`
- **Cause:** Hard-coded list of 6 destructive tools in
  `build_system_prompt`. Missed `delete_saved_search` when added.
- **Fix:** Derive list dynamically from `_DESTRUCTIVE_COMMANDS`.
- **Test:** Strengthened `test_prompt_warns_about_destructive_tools` in
  `tests/test_tool_use_router.py` to iterate the set so future additions
  can't silently go stale.

### Bug B — idempotency cache returned stale `reversalToken` after undo
- **Files:**
  - `company_discovery/tool_actions_store.py` — added
    `invalidate_user_idempotency(user_id, tool_name=None)`
  - `company_discovery/tools/undo_last_action.py` — call invalidate
    before dispatching the inverse
- **Cause:** 60s idempotency cache returned the original `reversalToken`
  on a repeat call EVEN if undo had already consumed it; chat would tell
  user "switched to data" but DB row was still 'tech'.
- **Fix:** On undo, clear cache entries for both the original tool and
  the inverse tool for that user.
- **Test:** Extended `scripts/probe_idempotency_keys.py` with section
  6 (stale-token regression).

### Bug C — `capture_inverse` empty-dict case wrote useless reversals
- **File:** `company_discovery/tool_registry.py:407`
- **Cause:** Check was `inverse_args is not None`; an empty dict
  (capture function couldn't find target) passed the check and wrote a
  reversal that later undo dispatch couldn't satisfy.
- **Fix:** Changed to truthy check `inverse_args and tool.inverse_tool`.

### Bonus — silent import-failure rationalization removed
- **File:** `company_discovery/tool_registry.py:_ensure_loaded`
- **Before:** `except Exception: pass` with comforting comment. If the
  tools package failed to import in production, EVERY Phase 1
  enhancement (Pydantic validation, tier-based undo, idempotency, tool
  spans) silently disabled — operators would never know.
- **After:** Logs at ERROR with full traceback + explicit "this is a
  silent degradation, investigate immediately" message.

---

## Phase 1 progress (Step 7 wrap-batches done)

**Live at 0.90.0:** 25 chat tools registered, 17 probes + 1090 unit tests.

| Step | Status |
|---|---|
| 1 — Pydantic registry, all 14 tools migrated | ✅ shipped 0.88.0 |
| 2 — `cache_control` on last tool | ✅ shipped 0.88.0 |
| 3 — `<untrusted_data>` tag wrap | ✅ shipped 0.88.0 |
| 4 — CRUD-parity undo (5 of 5 Tier I tools wired) | ✅ shipped 0.88.0 |
| 5 — Atomic-release slot on LLM failure | ✅ shipped 0.88.0 |
| 6 — Idempotency keys per non-read tool | ✅ shipped 0.88.0 |
| 7 Batch 1 — saved-search + company CRUD (3 new tools) | ✅ shipped 0.89.0 |
| 7 Batch 2 — settings reads (3 new tools) | ✅ shipped 0.89.0 |
| 7 Batch 3 — account/billing/export/slack (4 new tools) | ✅ shipped 0.90.0 |
| 8 — OTel-shaped tool-call spans (data layer; exporter deferred) | ✅ shipped 0.88.0 |
| 9 — ADR-001 loop-driver migration to Pydantic AI | ✅ written |
| **Bug A/B/C fixes** | **❌ awaiting 0.91.0 deploy** |

### Still TODO in Phase 1

- **Wrappable next batch (~4 tools):** `start_2fa_enrollment`,
  `disable_2fa` (openUrl-bridge to TOTP flow), `subscribe_push_notifications`
  (openUrl-bridge to browser dance), maybe a couple extended profile fields.
- **Needs real backend (~10 items)** — DO NOT speed-wrap into stubs:
  1. `archive_discovered_job` + `mark_not_interested` — need
     `review_state` column on `DiscoveredJob` + migration + filter
     changes in `list_discovered_jobs`.
  2. `dismiss_captured_job` — same shape.
  3. CV section-level edit verbs (`edit_summary`,
     `add_experience_bullet`, `quantify_bullet`) — needs new
     CV-mutation primitives.
  4. CV photo upload via chat — base64-in-tool support.
  5. CV variant management — variant model exists on
     `ImportedJob.cv_variants`, no primitives.
  6. Workspace invite via chat.
  7. Bookmarklet installer.

### Explicitly NOT wrapping (with reasoning)
- `update_ai_provider_config` — contradicts canonical product vision
  ("no AI knobs for user").
- `change_password` — putting a new password in chat history is a
  security regression.

---

## Architecture snapshot

### Tool registry
- `company_discovery/tool_registry.py` — Pydantic-backed `Tool` /
  `ToolResult` / `ToolError`. Pre-capture (`capture_inverse`) +
  post-capture (`capture_inverse_after`) for inverse args. Lazy-loaded
  by `_ensure_loaded`.
- `company_discovery/tools/` — one file per tool, 25 modules.
- `company_discovery/tool_actions_store.py` — SQLite at
  `<data_dir>/tool_actions.sqlite` with three tables:
  `reversal_tokens`, `pending_actions`, `idempotency_cache`,
  `tool_call_spans`.

### CRUD tiers (portfolio policy)
- **R (read):** 12 tools — no friction, no undo, no idempotency
- **I (idempotent write):** 7 tools — issue `reversalToken`, undo via
  `undo_last_action`. Idempotency cache 60s. All have working
  `capture_inverse` or `capture_inverse_after`.
- **N (non-idempotent destructive):** 3 tools (`delete_company`,
  `delete_account`, `delete_saved_search`) — pre-confirm via legacy
  `_DESTRUCTIVE_COMMANDS` gate. Step 4b (pending-actions
  preview/commit) deferred.
- **R-meta:** 1 (`undo_last_action`)

### Portfolio reference doc
`/Users/fouad./Desktop/personal Projects/_portfolio-architecture/chat-tool-invocation.md`
— canonical chat-architecture decisions across DJS + xboard + future
projects. **Read this before any chat-related work in any portfolio
project** (also captured in memory: `reference_portfolio_chat_architecture.md`).

### Memory
Files in `/Users/fouad./.claude/projects/-Users-fouad--Desktop-NasserMCPserver/memory/`:
- `project_canonical_vision.md`
- `feedback_demand_runtime_proof.md`
- `feedback_top_tier_only.md`
- `feedback_dont_please_disagree.md` (added this session)
- `feedback_cross_project_feature_eval.md` (added this session)
- `feedback_no_project_bias.md` (added this session)
- `reference_deploy_paths.md`
- `reference_portfolio_chat_architecture.md` (added this session)

Global `~/.claude/CLAUDE.md` extended with the "no project deference"
section (committed before this restart trigger).

---

## Spawned background tasks / subagents

**None currently active.** Two ran earlier in this session and
completed:
- `aca4d15cbea66f033` — web research on chat tool-calling state of the
  art. **Completed.** Output integrated into the portfolio doc.
- `a1709ceb7721d75bf` — xboard chat-surface inventory. **Completed.**
  Output integrated into the portfolio doc.

No pending child processes, schedules, or external runs.

---

## Live URLs / probes for quick health check

```
curl -s https://app.khalo.org/api/health
# expect: "version": "0.90.0" until 0.91.0 deploys

curl -s "https://app.khalo.org/api/cv/template-thumbnail?id=modern&accent=indigo&photo=0" -o /dev/null -w "%{http_code}\n"
# expect: 200
```

Local probe battery (all should be ALL CHECKS PASS):

```
python -m pytest -q  # expect 1090 passed
for p in probe_lazy_cv_extract probe_template_thumbnail probe_tool_use_chat \
         probe_new_registry_dispatch probe_undo_last_action \
         probe_slot_release_on_failure probe_idempotency_keys \
         probe_tool_spans probe_phase1_batch1 probe_phase1_batch2 \
         probe_phase1_batch3; do
  python scripts/${p}.py 2>&1 | tail -2
done
```

---

## Open observational items (not bugs)

1. **Throughput drift baseline 135 → 75-97 req/s** after Phase 1.
   Cumulative SQLite-write cost. Each Tier I dispatch now writes
   reversal token + idempotency cache + span. Not a blocker (1M/year ≈
   31 req/s peak, still 2-3x headroom) but not load-tested against
   real production traffic.
2. **`strict: true` on Anthropic tool spec — deferred.** EmailStr in
   `delete_account` emits `format: "email"` which some Anthropic strict
   variants may reject. Needs live API verification, not a unit test.

---

## Deploy script

```
TAG=0.91.0 /Users/fouad./Desktop/NasserMCPserver/scripts/deploy-with-backup.sh
```

Uses SSH ControlMaster to `app.khalo.org`. Per deploy memory:
`/Users/fouad./.claude/projects/-Users-fouad--Desktop-NasserMCPserver/memory/reference_deploy_paths.md`.
