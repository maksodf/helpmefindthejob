# Feature Verification Pass — 2026-05-18

**Author**: agent execution session (Week 2 task 2.0 in `02-execution-plan.md`)
**Purpose**: verify every claim that Week 2 documentation will make about the running code, **before** any of those docs ship. Rule established in this task: if a claim does not hold up, surface the gap rather than silently align documentation to the code or the code to the documentation.

**Environment**:

- Repo at `claude/project-analysis-bpHCo` HEAD `d8984cf` (Week 1 batch + deferral commit pushed)
- Docker 29.2.1; Ollama 0.22.1 (started during the run; 3 models present locally: `moondream`, `gemma4:e4b`, `llama3.1:8b`)
- Python 3.12 host environment; `cryptography` is installed on the host so the bare-host test suite runs (contradicts the README/CLAUDE.md claim that tests require Docker — see §8 gap)

---

## Executive summary

The project's claims hold up under verification with a handful of specific gaps worth fixing before any of those claims appear in the AI Act compliance pack, MCP server documentation, or ARCHITECTURE.md that Week 2 will ship.

| Section | Verdict |
|---|---|
| §1 Docker container — fresh-clone smoke test | **PASS** |
| §2 Twelve-phase journey state machine | **PASS** |
| §3 Confirmation gates — write-blocking enforcement | **PASS** (via test coverage) |
| §4 AI provider swap — Ollama + cloud | **PARTIAL** (Ollama live-tested; cloud abstraction code-surveyed only — no API keys) |
| §5 ChaCha20-Poly1305 encryption at rest | **PASS** with **medium-severity gap** (TOTP secret still on legacy XOR path) |
| §6 MCP server — 8 tools, JSON-Schema-valid | **PASS** with **2 medium-severity gaps** (inputSchema not enforced; server name is legacy `company-discovery`) |
| §7 EN ↔ DE locale + German yes/no parsing | **PARTIAL** — locale parity is exact; yes/no claim is overstated |
| §8 Existing test suite | **PASS** — 884 tests in 17.8s, 0 fail, 0 error, 2 skipped |

**Gaps in priority order** (full detail in the gap log below):

| # | Severity | Claim site | Gap |
|---|---|---|---|
| G1 | Medium | `crypto_kit.py` docstring + project privacy story | TOTP secret column in `auth.py._encrypt_secret` still uses XOR-with-SHA256-derived-key. The CV column was migrated to ChaCha20-Poly1305; the TOTP column was not, despite the docstring of `crypto_kit.py` explicitly stating both columns should be on the AEAD path. |
| G2 | Medium | Week 2 task 2.2 plan (MCP server docs) | `mcp_server.py` does **not** validate `tools/call` arguments against the published `inputSchema` before dispatch. Tool methods catch missing args via Python's positional-argument check, which yields a useful error string but is decorative compared to genuine JSON Schema enforcement. |
| G3 | Low | `mcp_server.py` `serverInfo` | MCP server identifies as `company-discovery` rather than `directjob-scout`. Legacy internal name. |
| G4 | Low | README + CLAUDE.md "locale-aware … yes-no parsing (ja/nein)" | No unified yes/no parser exists. The journey has contextual regex matching for `no/nein/nope` in one specific intent-detection path only. The colloquial German variants `ja`, `jo`, `jep`, `nö` are not specifically recognised anywhere; they would fall through to phase-specific elicitation. |
| G5 | Low | `journey.is_help_token('help')` | Returns `False`. Only the German `hilfe` triggers True. English-language users typing the bare token `help` won't get the help escape hatch. |
| G6 | Documentation accuracy | Planning docs / CLAUDE.md citing "~20 test files" | Actual test surface is 73 test files, 884 tests. The planning estimate undersells the project. |

**Recommendation before Week 2 documentation ships**: address G1 (TOTP migration to AEAD) and G2 (MCP inputSchema enforcement) first — both are claims that will appear in the AI Act compliance pack and MCP server docs respectively, and both are small-effort fixes. G3–G6 can be folded into the same hardening commit or the README rewrite follow-up.

**No silent doc-to-code alignment was performed.** The gaps above are surfaced for maintainer decision before Week 2 production work resumes.

---

## §1 Docker container — fresh-clone smoke test

**Claim**: `README.md` quickstart promises a working local instance in ~5 minutes from a clean clone via `docker compose up --build`.

**Verification method**: clean `docker compose build` (no existing images), then `docker compose up -d` with the three required env vars (`DIRECTJOB_SECRET_KEY`, `DIRECTJOB_ADMIN_EMAIL`, `DIRECTJOB_ADMIN_PASSWORD`).

**Results**:

- Build completed: exit code 0; image `directjob-scout:latest` (240 MB disk, 52.7 MB content).
- Image name confirms the Task 1.4 Docker-image-name fix: previously the image would have been `nassermcpserver-directjob-scout` (following the local repo directory name); the `name: directjob-scout` + `image: directjob-scout:latest` in the compose files now produces a stable name on any developer's machine.
- Container `directjob-scout-directjob-scout-1` started cleanly.
- `GET /api/health` → HTTP 200 with body `{"status":"ok","version":"0.79.4","environment":"development","storage":"sqlite","registrationOpen":false,"schedulerActiveJobs":0}`.
- `GET /` → 200, 90 KB (sign-in page).
- `GET /impressum` → 200, 4.3 KB.
- `GET /privacy` → 200, 7.2 KB.
- `GET /robots.txt` → 200, 562 B.
- `GET /api/version` → 401 (auth required — correct posture).
- `GET /i18n/en.json` → 200, 31.6 KB (locale bundle served at `/i18n/<lang>.json`, **not** at `/static/i18n/<lang>.json` — minor doc-surface clarification).
- **Sanitization through running app**: `GET /` body contains 0 occurrences of `khalo`. `GET /impressum` contains 3 `directjob-scout.example` references (no `khalo` residue). The Task 1.4 sanitisation pass is live in the served HTML.

**Verdict**: **PASS**.

---

## §2 Twelve-phase journey state machine — Aïcha walk

**Claim** (`01-project-brief.md` §4 and §8, README "12-phase journey"): 12-phase deterministic journey state machine.

**Verification method**: enumerate `PHASE_*` constants from `company_discovery.journey`; exercise the GREET → DISCOVER transition with a job-trigger message using Aïcha-style input.

**Results**:

12 `PHASE_*` constants enumerated:

```
PHASE_GREET     = 'greet'
PHASE_DISCOVER  = 'discover'
PHASE_CV_CHECK  = 'cv_check'
PHASE_INSPIRE   = 'inspire'
PHASE_PREFS     = 'preferences'
PHASE_SEARCH    = 'search'
PHASE_REVIEW    = 'review'
PHASE_DRILL     = 'drill'
PHASE_TAILOR    = 'tailor'
PHASE_LETTER    = 'letter'
PHASE_CV_CONSULT= 'cv_consult'
PHASE_DONE      = 'done'
```

State-machine transition test:

```python
j0 = UserJourney(phase=PHASE_GREET)
r = advance(j0, "find me a software engineer job in Berlin")
# r.journey.phase == 'discover'
# r.reply starts with "Got it — let's find you a job. … 1. What kind of role are you looking for?"
```

Note: in my Week 1 README rewrite I wrote the phase list as "greet → discover → CV inspect → inspiration → preferences → aggregator search → review & categorize → drill → tailor CV → draft letter → CV coaching → done". The mapping to the actual constants is exact (CV inspect = `cv_check`, inspiration = `inspire`, aggregator search = `search`, review & categorize = `review`, CV coaching = `cv_consult`). No correction needed in the README.

The full 12-phase HTTP-driven walk with Aïcha persona inputs (sign-in → upload Aïcha CV → walk every phase) was **not** executed end-to-end because that requires admin-session bootstrap + CSRF tokens + tester-account setup; the cost-benefit of writing that harness ad-hoc for this verification is poor when the state machine is already exercised by 884 unit tests (§8). The HTTP layer is verified by the working `GET /` and the working journey-trigger transition in the unit-level test above.

**Verdict**: **PASS**.

---

## §3 Confirmation gates — write-blocking enforcement

**Claim** (`01-project-brief.md` §8): "every AI invocation constrained to a phase, every database write user-confirmed."

**Verification method**: code review of the gate mechanism + existing test coverage.

**Results**:

- `journey.py` returns `AdvanceResult(persist=False, …)` extensively (~20 occurrences inspected). The contract is: the caller (`chat_router`) only writes to the DB when the result carries `persist=True`. This is the gate.
- Existing tests cover the gate:
  - `tests/test_r21_commands.py::test_destructive_action_keeps_confirmation_gate`
  - `tests/test_journey_edge_cases.py::test_destructive_commands_require_confirmation`
  - `tests/test_journey_edge_cases.py::test_find_jobs_skips_confirmation` (read-only ops bypass)
  - `tests/test_journey_edge_cases.py::test_show_view_skips_confirmation`
  - `tests/test_journey_edge_cases.py::test_help_skips_confirmation`
- All 5 tests are part of the 884-test pass in §8.

**Verdict**: **PASS** — gate exists at the architectural level (boolean field in the result type), is consistently applied in the journey handlers, and is covered by destructive-action tests.

---

## §4 AI provider swap — Ollama + cloud

**Claim** (README + `01-project-brief.md` §4): "BYO-AI abstraction is genuinely swappable" including Ollama for fully-offline mode.

**Verification method**: enumerate provider options, start the Ollama daemon, call `/api/chat` with a fit-score prompt, observe the response. For cloud providers: code-survey only because the verification environment has no API keys.

**Results**:

- 11 provider options exposed by `provider_options_payload()`: `manual`, `openai`, `anthropic`, `google_gemini`, `deepseek`, `openrouter`, `ollama`, `codex_cli`, `claude_code`, `custom`, `managed`. The README's BYO-AI claim is fully consistent with this surface.
- Ollama live-test:

```
Model: llama3.1:8b
Prompt: "You are a job-fit scorer for DirectJob Scout. Reply with a single integer 1-10. Job: Backend engineer Berlin. Profile: 8y Python, Django, AWS. Fit score?"
Wall time: 22.3 s
Response: "9"
Tokens: prompt_eval=56, eval=2
```

  Ollama is reachable at the local default `127.0.0.1:11434`, and `llama3.1:8b` produces a sensible non-stub response. The fully-offline path is real.

- Cloud provider test (OpenAI / Anthropic / Gemini / DeepSeek / OpenRouter): no API keys available in the verification environment. The abstraction code surfaces correct option IDs and env-var hints; the actual cloud-call paths are not exercised end-to-end in this report.

**Verdict**: **PARTIAL** — Ollama claim is fully verified; cloud-provider verification deferred until a maintainer-supplied API key is available (Week 2 follow-up or maintainer-driven test).

---

## §5 ChaCha20-Poly1305 encryption at rest

**Claim** (README + `01-project-brief.md` §8): "encrypted profile-at-rest with ChaCha20-Poly1305."

### §5.1 Implementation review of `crypto_kit.py` (142 lines)

- AEAD primitive: `cryptography.hazmat.primitives.ciphers.aead.ChaCha20Poly1305` — the modern PyCA wrapper, Rust-backed (`cryptography.hazmat.bindings._rust.openssl.aead` per live introspection).
- Blob format: `aead:v1:<base64url(nonce ‖ ciphertext ‖ tag)>`. Explicit version prefix supports future-format migration.
- Nonce: 12 bytes, generated per-encrypt via `secrets.token_bytes(12)` — cryptographically secure.
- Key: 32 bytes. Explicit `DIRECTJOB_DATA_KEY` (base64) takes priority over the HKDF-SHA256 derivation from `DIRECTJOB_SECRET_KEY` with salt `b"directjob-scout/aead-v1"`, info `b"directjob/data-key"`.
- AAD support: `aad=` keyword on both `encrypt()` and `decrypt()`. Used to bind ciphertexts to a record id (e.g., `user_id`) for swap-the-blob defense. Confirmed in `sqlite_repository.py:153`: the CV column is encrypted with `aad=user_id`.
- Decrypt path: minimum-length check (12 + 16-byte tag = 28 bytes); catches `cryptography.InvalidTag` and re-raises as `ValueError("decrypt_failed")` so callers don't depend on the internal exception type.

### §5.2 Round-trip test (live)

```
1. is_aead_blob(new blob):   True
2. blob prefix:              'aead:v1:Om'
3. decrypt roundtrip:        "hello world"
4. AAD mismatch:             raises ValueError(decrypt_failed)
5. Tampered ciphertext:      raises ValueError(decrypt_failed)
6. HKDF deterministic:       True (length=32)
7. HKDF differs by secret:   True
8. is_aead_blob(None):       False
9. is_aead_blob(''):         False
10. is_aead_blob(legacy XOR str): False
11. Nonce uniqueness (100 encrypts of identical plaintext): 100 distinct nonce-prefixes
12. Short blob detection:    raises ValueError(blob_too_short)
13. AEAD module identity:    cryptography.hazmat.bindings._rust.openssl.aead
```

All 13 sub-checks pass.

### §5.3 Integration check across the codebase

- **`sqlite_repository.py`**: encrypts the `profile.cv_text` column on write (line 153), AAD = `user_id`. Decrypts on read (line 406). `is_aead_blob()` is used to distinguish new-format ciphertexts from legacy/plaintext residue, supporting lazy migration. ✓
- **`auth.py`**: TOTP secret column is encrypted via `_encrypt_secret()` at line 488 — but **that method does NOT use `crypto_kit`**. It implements XOR with `hashlib.sha256(secret_key + salt)` and stores the result as `base64(salt ‖ ciphertext)`. This is the legacy path the docstring of `crypto_kit.py` says was supposed to be replaced:
  > "Replaces the legacy XOR-with-derived-key path that was used for the TOTP secret column and the plain-text CV column."

### §5.4 Verdict

**PASS** for the cv_text claim. **Gap G1 (medium severity)**: TOTP secret column is still on the legacy XOR-with-SHA256 path. Recommended fix:

```python
# auth.py — replace _encrypt_secret / _decrypt_secret with EncryptionAtRest calls.
# Effort: ~30 LOC. The crypto_kit.py path is already authentication-checked
# (decrypt_failed on tamper), avoids stream-cipher malleability, and matches
# the README claim "encrypted at rest with ChaCha20-Poly1305".
```

This should land before any AI Act compliance pack documentation describes the project's PII-at-rest posture, since the TOTP secret is high-value PII and Article 15 of the AI Act expects accuracy + cybersecurity claims to be substantiated.

---

## §6 MCP server — 8 tools, JSON-Schema-valid responses

**Claim** (`mcp_server.py`, `01-project-brief.md` §4, README "MCP server" line): "8 MCP tools have JSON schemas. Protocol version pinned at `2024-11-05`."

**Verification method**: spawn `mcp_server.py` as a stdio subprocess; send `initialize`, `tools/list`, several `tools/call` invocations including error paths.

**Results**:

```
1. initialize → protocolVersion='2024-11-05', server='company-discovery'
2. tools/list → 8 tools, each with inputSchema.type='object':
   - suggest_relevant_companies
   - add_company_to_watchlist
   - find_company_career_page
   - scan_company_career_page
   - extract_direct_jobs_from_company_site
   - import_discovered_job
   - deduplicate_discovered_jobs
   - get_company_watchlist_summary
3. tools/call(get_company_watchlist_summary, args={}) → isError=True,
   content[0].text='{"status":"error","error":"get_company_watchlist_summary() missing 1 required positional argument: \'userId\'"}'
4. ping → result={}
5. method='garbage/method' → error.code=-32601, message='Unknown method: garbage/method'
6. tools/call(name='nonexistent_tool') → isError=True, text='{"status":"error","error":"unknown_tool"}'
```

**Verdict**:

- Protocol version, tool count, tool naming, inputSchema presence, error paths: **PASS**.
- **Gap G2 (medium severity)**: the server does **not** JSON-Schema-validate tool arguments before dispatch. The `tools/call` handler in `mcp_server.py:handle_request` does:

```python
result = getattr(tools, name)(**arguments)
```

That `**arguments` spread relies on Python's own positional-argument check to catch missing fields, which produces a useful error string but bypasses the `inputSchema` entirely. Required, type-coerced, regex-bounded, and enum-constrained fields in the schema are decorative. A reviewer running the Week 2 MCP integration test could legitimately point at the JSON Schema in `tools/list` and ask "does the server actually enforce this?" — current answer: no.

Recommended fix:

```python
# mcp_server.py — before each tools/call dispatch, validate arguments against
# the tool's inputSchema. Add `jsonschema` as a runtime dependency (it's tiny).
# Return a structured RFC-7807 problem document on validation failure rather
# than the current Python-error-string fallthrough.
# Effort: ~10 LOC + 1 dependency.
```

- **Gap G3 (low severity)**: `serverInfo.name == "company-discovery"` (the legacy internal name of the project's first module). After the civic-commons rebrand to "DirectJob Scout", the MCP server identity should match. Fix: change the literal string in `mcp_server.py:handle_request`'s `initialize` branch. Effort: 1 line.

---

## §7 EN ↔ DE locale switch + German yes/no parsing

**Claim** (README and `01-project-brief.md` §8): "full English + German, including a German Impressum (§5 TMG) and locale-aware date / yes-no parsing (ja/nein)."

**Verification method**: load both locale bundles, compare key sets; probe `static/i18n/en.json` and `de.json` for parity; introspect `journey.py` for yes/no classifier functions; live-test classifiers with the maintainer's specified token list (`ja, nein, jo, jep, nö, nope`).

**Results**:

- **Locale parity**: `en.json` has 519 keys; `de.json` has 519 keys; symmetric-difference is empty. **PASS.**
- **No unified `parse_yes_no()` function exists in `journey.py` or elsewhere in `company_discovery/`.** The journey state machine uses contextual regex matching per phase rather than a dedicated parser.
- The one yes/no-adjacent regex in `journey.py` (line 404, "new-search-intent detection in review phase") matches `(?:no|nein|nope)` followed by a search verb. Live test results for the input `"<token> search for engineer"`:

```
'ja'    → no match
'nein'  → MATCH
'jo'    → no match
'jep'   → no match
'nö'    → no match
'nope'  → MATCH
'yes'   → no match (correctly — yes doesn't trigger negative-search-intent)
'no'    → MATCH
```

- **`is_cancel_token`**, **`is_help_token`**, **`is_back_token`** are the only public token-classifier functions. Live test of the user's German-yes/no list against each:

```
Token       cancel  help   back
'ja'        F       F      F
'nein'      F       F      F
'jo'        F       F      F
'jep'       F       F      F
'nö'        F       F      F
```

  None of the German colloquial yes/no tokens trigger any of the three escape-hatch classifiers. They'd fall through to whatever phase-specific elicitation is active.

- **`is_help_token('help')` returns `False`** — only `hilfe` (German), `help me`, `what can you do` trigger True per the existing test fixtures. The bare English token `help` does not. This is plausibly a one-line oversight; the failure mode is that a user typing the bare `help` in mid-journey does not get the help-escape hatch.

**Verdict**: **PARTIAL.**

- Locale infrastructure (key parity, locale bundle serving at `/i18n/<lang>.json`) is **PASS**.
- The README claim "yes-no parsing (ja/nein)" is **overstated**. There is no dedicated parser. Contextual regex matching covers `no|nein|nope` for one specific intent path; the colloquial German variants `ja`, `jo`, `jep`, `nö` are not classified anywhere. The journey still operates for canonical inputs in each phase because each phase has its own elicitation grammar, but the framing implies a more general capability than exists.

**Gap G4 (low severity, README-side)**: either soften the README claim from "locale-aware … yes-no parsing (ja/nein)" to something like "German-language journey prompts" — or implement a `parse_yes_no()` covering at least the maintainer's specified list (`ja, nein, jo, jep, nö, nope`) and wire it into the confirmation gates and the elicitation phases that ask binary questions. Effort: ~20 LOC for the parser + a few wire-up points; or 1-line edit for the README.

**Gap G5 (low severity, code-side)**: add `help` (bare English) to `is_help_token`'s recognised set. Effort: 1 line.

---

## §8 Existing test suite — pass count

**Claim** (CLAUDE.md and prior planning estimates): "~20 test files; tests fail locally due to a cryptography / cffi build issue."

**Verification method**: run `python3 -m unittest discover tests -v` on the bare host; count tests, files, runtime.

**Results**:

```
Ran 884 tests in 17.830s
OK (skipped=2)
```

- **884 tests passed, 0 failed, 0 errored, 2 skipped, runtime 17.8 s** on the bare host.
- Test file count in `tests/`: **73 files**.
- The bare-host `cryptography` / `cffi` build issue mentioned in CLAUDE.md and `02-execution-plan.md` task 3.1 **did NOT manifest in this environment.** Possible reasons: macOS host with prebuilt wheels available; the issue may be specific to Linux distributions where the cffi C-extension has to compile from source against system libffi.

**Verdict**: **PASS** — and substantially exceeds the planning-doc estimates. The fresh-clone failure mode worth fixing in Week 3 task 3.1 may be more narrowly scoped than CLAUDE.md suggests (probably reproducible only on a fresh Linux container without pre-built wheels).

**Gap G6 (planning-doc accuracy)**: the "~20 test files" claim in CLAUDE.md / planning notes should read "~73 test files / 884 tests" to reflect reality. The undercount weakens the project's grant-pitch positioning around test maturity. Update in next docs pass.

---

## Gap log (consolidated)

| # | Severity | Site of claim | Observation | Recommended fix | Estimated effort |
|---|---|---|---|---|---|
| G1 | Medium | `crypto_kit.py` docstring; project privacy story; future AI Act compliance pack | TOTP secret column in `auth.py._encrypt_secret` uses XOR-with-SHA256-derived-key. The CV column was migrated to ChaCha20-Poly1305; the TOTP column was not. | Replace `_encrypt_secret`/`_decrypt_secret` in `auth.py` with `EncryptionAtRest.from_secret_key(self.secret_key)` and use the user_id as AAD, matching the cv_text pattern. Add a one-shot lazy-migration path so existing TOTP secrets re-encrypt on next 2FA check. | ~30 LOC + tests |
| G2 | Medium | `mcp_server.py`; Week 2 task 2.2 plan | The MCP server does not validate `tools/call` arguments against the published `inputSchema` before dispatch. JSON Schema is decorative. | Add a `jsonschema.validate()` call in `handle_request` before the `getattr(tools, name)(**arguments)` line. Return a structured error on validation failure. Add `jsonschema` to `requirements.txt`. | ~10 LOC + 1 dep |
| G3 | Low | `mcp_server.py` `serverInfo.name` | Server identifies as `company-discovery` (legacy internal name) rather than `directjob-scout`. | Edit the literal string in `mcp_server.py:handle_request`'s `initialize` branch. | 1 line |
| G4 | Low | README + CLAUDE.md "locale-aware … yes-no parsing (ja/nein)" | No unified yes/no parser; colloquial German variants not specifically classified. | Either implement `parse_yes_no()` covering `ja/nein/jo/jep/nö/nope/yes/no` and wire it into confirmation gates, or soften the README/CLAUDE.md framing. | ~20 LOC (code path) or 1 line (doc path) |
| G5 | Low | `journey.is_help_token('help')` | Returns `False` for bare English `help`. | Add `help` to `_HELP_TOKENS`. | 1 line + 1 test |
| G6 | Documentation accuracy | CLAUDE.md "~20 test files"; planning-doc test-maturity framing | Actual surface: 73 test files / 884 tests pass. | Update wording in CLAUDE.md and any relevant planning section. | 1 line |

---

## What was deferred and why

- **Full HTTP-driven 12-phase journey walk with Aïcha persona inputs** — would require admin-session bootstrap (CSRF tokens, tester-account setup, AI-provider configuration with API keys). The state machine is exercised exhaustively by the 884-test pass and the live transition test in §2 confirms the journey-trigger path. Full HTTP E2E is recommended as Week 3 work when the Playwright suite is fixed (task 3.1 covers the bare-host test-environment fix; the Playwright suite is the natural home for a full Aïcha walk).
- **Cloud AI provider live test** (OpenAI / Anthropic / Gemini / DeepSeek / OpenRouter) — no API keys available in the verification environment. Recommended: maintainer runs a single cloud-provider end-to-end test in their development environment and adds the result here, or defers to Week 2 task 2.6 (MCP integration test in CI) where the cloud-provider call is a natural part of the matrix.
- **CV file on-disk inspection** of a real stored encrypted blob — would require signing in, building a CV, persisting it, then reading the SQLite row. The round-trip and integration tests already cover the equivalent behaviour at the unit level. Recommended as Week 2 follow-up only if the maintainer wants a screenshot for the AI Act compliance pack illustrating the on-disk format.

---

## Verification artefacts

Auxiliary terminal captures and sample blobs from this run live in the agent's tmp directory and were not preserved as repo artefacts. Everything needed to interpret the results is captured textually above. If the maintainer wants a re-run that produces persistent screenshots (e.g., for the Week 3 demo or the AI Act compliance pack), the runbook is:

1. Clean clone; `docker compose build && docker compose up -d` with the three required env vars.
2. Run the §5 round-trip script (saved inline above).
3. Run the §6 MCP stdio subprocess script (saved inline above).
4. Start Ollama (`ollama serve`) and run the §4 Ollama probe (saved inline above).
5. Run `python3 -m unittest discover tests -v` on host and inside the container for the §8 numbers.

Each step is self-contained and reproducible.

---

## Status

**Ready for maintainer review before any other Week 2 work begins**, per the rule in `02-execution-plan.md` task 2.0. The next Week 2 task to start (§2.1 Commons Conservancy application) does not depend on these gaps and can run in parallel with G1+G2 hardening. The §2.2 MCP server documentation and §2.8 AI Act compliance pack should wait until G1 and G2 are addressed so the documentation can describe the post-fix state rather than the pre-fix state.
