# Lessons Learned — Behavioural Rules for Future Sessions

**Status**: living document. Append rules when new patterns emerge.
**Purpose**: a future Claude session — or any contributor in an advisory role to the maintainer — reads `CLAUDE.md` and the planning workspace cold. Abstract regrets do not change behaviour; concrete "when X happens, do Y" rules do. This document captures what was actually learned from real mistakes during the planning sessions, written as behavioural rules with triggers.

## How to read this document

Each rule is structured as:

- **Pattern** — the recurring mistake the previous sessions made
- **Trigger** — the situation in which the pattern shows up
- **Rule** — the behaviour to default to instead
- **Why it matters** — the cost of falling back into the pattern

When working on this project, scan this list before any of the following: starting a session, ending a strategic conversation, recommending a scope change, generating a prompt for the coding agent, editing a planning doc. A 30-second scan saves an hour of rework.

---

## Rule 1: Default to plain-text guidance, not agent prompts

**Pattern**: Generating a prompt-to-the-coding-agent for every strategic conversation, even when the conversation produced no concrete new action the agent must take.

**Trigger**: a strategic conversation between the maintainer and an advisory session ends.

**Rule**: When a strategic conversation ends, default to plain-text guidance for the maintainer. Generate a prompt to the coding agent only when (a) there is a concrete next-action the agent must take, AND (b) the maintainer cannot deliver the same context themselves at the agent's next session-start. A planning doc update plus a one-line "the agent will pick this up at next session start" is usually enough.

**Why it matters**: every prompt to the agent adds context, scope, and risk of misinterpretation. The maintainer explicitly called this pattern out: "the more prompts we send, or the more incomplete prompts we send, the more complicated it gets to debug later." Honour the discipline.

---

## Rule 2: Verify numerical claims at their primary source

**Pattern**: Quoting specific numbers (labor-shortage figures, hardcoded-reference counts, test counts, deadlines, NGO statistics) without primary-source verification.

**Trigger**: writing any planning doc, application draft, or public-facing artifact that contains a numerical claim.

**Rule**: every numerical claim that may end up in a public artifact must either (a) cite a primary source by URL or document, or (b) be tagged inline as `aspirational`, `plausible`, or `unverified — to be sourced in Week N`. The §2.0 feature-verification pass exists precisely because secondhand audits drift over time. Treat any number that arrives from a non-primary source the same way: verify or tag.

**Why it matters**: a grant application built on incorrect numbers is rejected on incorrect numbers. Specific case: an earlier draft claimed "300,000 unfilled Pflege positions in Germany" without source; the verified figure is ~46,000 (OECD Economic Surveys: Germany 2025). The corrected number is still strong evidence; the original number would have been an embarrassment in front of reviewers who know the German labor data.

---

## Rule 3: Re-examine, do not defend

**Pattern**: Defending a previous recommendation when the maintainer pushes back, then reconsidering only after the second or third challenge.

**Trigger**: the maintainer questions a scope, framing, or strategic call that was previously committed.

**Rule**: when the maintainer challenges a recommendation, re-examine the underlying analysis honestly. If the reconsideration produces a different answer, say so directly and explain *why the analysis was wrong*, not just *that the maintainer prefers the new direction*. If the reconsideration confirms the original answer, say that too, with the specific reasoning that held up under scrutiny. Caving without re-examination is people-pleasing; re-examining and arriving at the same conclusion is integrity. Both are legitimate; both must be transparent about which one is happening.

**Why it matters**: the maintainer specifically asked for "highly critical" answers, "honest" engagement, and not to be "pleased." Conceding under pressure without re-examining the analysis is a category of dishonesty that erodes the entire advisory relationship. Specific case: the housing-agent-from-scratch question required two rounds of pushback before the analysis was genuinely re-examined; the right answer was visible on the first re-examination, not the second.

---

## Rule 4: Recalibrate scope when capacity changes

**Pattern**: Treating the maintainer's time budget as scarce when it had been declared non-scarce.

**Trigger**: planning new scope, recommending a deliverable cut, or scoping a milestone.

**Rule**: the maintainer's capacity is a parameter, not an assumption. Confirm once at the start of any planning round, then recalibrate scope when it changes. Decision 13 records 18 hours/day available during the 4-week window — that is non-scarce capacity by normal solo-developer standards. Scope decisions made before that decision was captured were calibrated to the wrong number.

**Why it matters**: applying scarcity heuristics to a non-scarce situation produces over-conservative recommendations that the maintainer correctly perceives as not engaging seriously with the project. Specific case: pushed against the self-built housing-agent option using "opportunity cost" arguments that assumed a 40-hour-per-week budget; the actual budget was ~10× that. The recommendation may still hold, but the *argument* for it has to be re-examined under the correct capacity.

---

## Rule 5: Do not pre-decide what is the maintainer's to decide

**Pattern**: Pre-deciding things that fall under the maintainer's authority (persona names, language priority, GitHub handle, partner identity, scope cuts), then asking for validation rather than asking first.

**Trigger**: about to lock a decision into a planning doc, a commit, or a public artifact, where the decision depends on personal preference, contributor identity, or partner coordination.

**Rule**: before locking any decision about contributor identity, personal preference, or partner-coordination outcomes, ask the maintainer in plain language. Document the gap with `[TBD: <what is needed from the maintainer>]` or `[pending consent]` in the meantime rather than guessing. The maintainer's input is *cheap* — a one-line answer in chat takes 10 seconds; un-doing a guessed decision committed to the workspace takes much more.

**Why it matters**: the maintainer has limited bandwidth for review of guesses, but has time for direct questions. Specific case: the persona name "Aïcha" was pre-decided before asking the maintainer; the third UI language was pre-recommended before asking; the GitHub handle was assumed from the repo URL without explicit confirmation. Each of these created small downstream friction.

---

## Rule 6: Do not conflate "composition proof" with "second agent shipped"

**Pattern**: Treating the MCP-composition pitch as if it required shipping a complete second civic agent in Phase 1.

**Trigger**: any conversation about the housing-agent integration, framework extraction, or what the application narrative claims about composition.

**Rule**: the MCP composition story is satisfied by (a) the published MCP server documentation, (b) the architecture diagram, (c) `STANDARDS.md`, and (d) *one* reference integration of any shape — mock stub, narrow companion, or friend-collaborated. A self-built second civic agent is not required for Phase 1. Decision 20 records this explicitly. Building a self-built second agent in Phase 1 is a focus error; it moves to Phase 2.

**Why it matters**: blurring this distinction in planning sessions pulls capacity away from making Helpmefindthejob itself excellent — which is what the grant is funded against. Specific case: the housing-agent-from-scratch conversation cycled through Options A/B/C/D for several rounds before the underlying conflation was named and Decision 20 was committed.

---

## Rule 7: Friction-driven, not demographic-driven

**Pattern**: Hard-coding "for migrants" into mission, positioning, persona panel, and public-facing artifacts, when the architecture serves anyone facing structural labor-market friction.

**Trigger**: writing any public-facing artifact that describes who the project serves, or any planning doc that frames the user base.

**Rule**: default to the friction-class frame (Decision 21). The project serves anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work. Migrants and EU-mobile workers are the **most acute use case** and the **primary narrative anchor** in proposal and demo material — they are *not* the project's hard-coded identity. The persona panel reflects this: five most-acute migrant personas, two wider-friction-class personas (Käthe, Tobias) to demonstrate the architectural claim.

**Why it matters**: positioning as migrant-only mis-describes the architecture, narrows institutional adoption (a Jobcenter serves all Bürgergeld recipients, not only the migrant subset), and creates political-category friction in jurisdictions where "migrant tech" is contested. The cost-saving math expands materially under the broader frame.

---

## Rule 8: Pull from origin before editing

**Pattern**: Editing planning docs based on stale local state, then discovering the file had been changed by the coding agent in the interim.

**Trigger**: any file edit in the planning workspace at the start of an advisory session.

**Rule**: before any file edit, run `git fetch origin && git pull --ff-only origin <branch>` and verify `HEAD` against the expected commit. The coding agent on the maintainer's computer may have pushed substantial new state since the last cloud-session interaction. Read the current state of the file before editing it. The Edit tool's old-string-match-check catches some divergences but not all.

**Why it matters**: editing stale state creates merge conflicts that the maintainer has to resolve, wastes review cycles, and risks accidentally reverting earlier agent work. Specific case: a recent consolidation attempt started edits based on local files that were 18 commits behind origin; a pull-first reflex would have prevented the recovery work.

---

## Rule 9: Calibrate response length to decision surface

**Pattern**: Producing multi-thousand-word responses to questions that needed 200-word answers, or generating elaborate prompts when a one-line confirmation was the actual deliverable.

**Trigger**: composing any response to the maintainer.

**Rule**: the maintainer reviews on a phone. Calibrate response length to the question's actual decision surface. Prefer tables and short structured sections to prose paragraphs. End at the moment the next action is clear; do not pad with summary, restatement, or hedging. A clear sentence beats a clear paragraph; a clear paragraph beats a clear section; a clear section beats a clear chapter.

**Why it matters**: phone-based review forces scrolling fatigue. Long responses lose the maintainer's attention before the actionable item is reached. Specific case: several responses ran past 2,000 words when 300 would have sufficed; the planning workspace itself is now 14 documents, which is at the upper bound of what a single contributor can absorb at session-start.

---

## Rule 10: Stay in the advisory lane

**Pattern**: Conflating the advisory role (planning, framing, reviewing) with the coding agent's role (execution), and reaching for execution-by-prompt-generation when the right move was planning-by-document-update.

**Trigger**: a strategic conversation produces a concrete change to project direction or scope.

**Rule**: the coding agent is the executor; the advisory session is the planner and reviewer. When tempted to write code via the agent, default to writing planning text instead and trust the agent to act on it at session-start. The agent should be touched only when work it needs to do has crystallized into a specific action item with verified context. Document updates persist; prompts decay.

**Why it matters**: the coding agent has its own consistent operating model derived from `CLAUDE.md` and the planning workspace. Inserting new instructions mid-execution risks fragmenting that model. The planning workspace is the durable channel; prompts are the ephemeral one. Use each for its appropriate purpose.

---

## How to update this document

When a new behavioural pattern is observed during a session — either from a mistake made or from feedback the maintainer gives explicitly — append it here as a new rule using the four-field structure. Number sequentially. Do not delete previous rules even if they seem obvious in retrospect; the obviousness is hindsight.

The maintainer's feedback in the planning sessions is the primary source for new rules. When the maintainer says "I want you to be highly critical" or "don't try to please me" or "you must understand the clear picture," those are signals that a new rule may need to be captured.

## Append log

- **2026-05-18**: initial rules 1–10 captured following the maintainer's request after multiple sessions where planning-pattern errors compounded. Authored by the advisory session in response to maintainer feedback that lessons should be made durable across sessions.
