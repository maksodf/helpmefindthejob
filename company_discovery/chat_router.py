"""Chat-router — the universal command surface.

The AI chat becomes the entry point for every CREATE / UPDATE action
in the app. Free-form user input is routed to one of a **fixed
whitelist of typed commands**; the AI is a constrained router, not a
free-form generator.

Architecture:

    user message
       ↓
    1. SLASH-COMMAND PARSER     ("/add-company Charité https://x")
       ↓ (no match)
    2. KEYWORD INTENT ROUTER    (regex over command synonyms)
       ↓ (no match + AI configured)
    3. AI INTENT ROUTER         (constrained: returns command-id only)
       ↓
    4. MULTI-TURN ELICITATION   (server asks for missing required params)
       ↓
    5. CONFIRMATION GATE        ("I'll <action> with <args>. Confirm?")
       ↓
    6. HANDLER                  (typed function call, audit-logged)

Design constraints (enforced by structure, not convention):
- The AI never executes anything directly — it only proposes a command
  id, the server validates params and asks for confirmation.
- Every command is typed: name, list of params with required/optional +
  validator, and a handler. The router cannot route to a non-existent
  command.
- Every successful execution is recorded in analytics_events so DSGVO
  audit + debugging are trivial.
- Slash commands are tried first so power users / accessibility users
  never depend on AI availability.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


# ---------------- Command schema ----------------


@dataclass
class CommandParam:
    """One typed parameter of a command."""
    name: str
    prompt: str           # what the user sees when we elicit this field
    required: bool = True
    type: str = "string"  # "string" | "url" | "list" | "bool"
    hint: str | None = None
    # Optional validator — returns (ok, error_message_or_canonical_value)
    validator: Callable[[str], tuple[bool, Any]] | None = None


@dataclass
class Command:
    """A typed function-call the chat router can execute."""
    name: str
    label: str            # human-readable
    description: str      # used by AI / keyword matchers
    params: list[CommandParam] = field(default_factory=list)
    # Keyword triggers — regex patterns, in priority order. Used by the
    # keyword router before AI is invoked. Each pattern is case-insensitive.
    keywords: list[str] = field(default_factory=list)
    slash_aliases: list[str] = field(default_factory=list)
    # Confirmation template — Python str.format with kwargs from params.
    confirmation_template: str = ""

    def confirmation_message(self, args: dict[str, Any]) -> str:
        try:
            return self.confirmation_template.format(**args)
        except (KeyError, IndexError):
            return f"I'll run {self.label} with {args}. Confirm?"


# ---------------- Validators ----------------


def _validate_url(value: str) -> tuple[bool, Any]:
    value = (value or "").strip()
    if not value:
        return False, "URL required."
    if not re.match(r"^https?://", value, re.IGNORECASE):
        # Be forgiving — most users type "x.com" not "https://x.com".
        if re.match(r"^[a-z0-9.\-]+\.[a-z]{2,}", value, re.IGNORECASE):
            value = "https://" + value
        else:
            return False, "That doesn't look like a URL."
    return True, value


def _validate_string(value: str) -> tuple[bool, Any]:
    value = (value or "").strip()
    if not value:
        return False, "Empty value."
    if len(value) > 5000:
        return False, "Too long (max 5000 chars)."
    return True, value


def _validate_list_csv(value: str) -> tuple[bool, Any]:
    value = (value or "").strip()
    if not value:
        return False, "Empty list."
    items = [v.strip() for v in value.split(",") if v.strip()]
    if not items:
        return False, "No items found."
    if len(items) > 50:
        return False, "Too many items (max 50)."
    return True, items


def _validate_bool(value: str) -> tuple[bool, Any]:
    v = (value or "").strip().casefold()
    if v in {"yes", "y", "true", "1", "on", "watch", "ja"}:
        return True, True
    if v in {"no", "n", "false", "0", "off", "skip", "nein"}:
        return True, False
    return False, "Reply yes or no."


def _validate_application_status(value: str) -> tuple[bool, Any]:
    v = (value or "").strip().casefold()
    valid = {"saved", "interested", "applied", "interview",
             "rejected", "archived"}
    if v in valid:
        return True, v
    return False, f"Status must be one of: {', '.join(sorted(valid))}."


# ---------------- Built-in command registry ----------------


def _build_registry() -> dict[str, Command]:
    return {c.name: c for c in [
        Command(
            name="add_company",
            label="Add a company to your watchlist",
            description="Watch a company's career page for new openings.",
            slash_aliases=["/add-company", "/add", "/watch"],
            keywords=[
                r"\badd (?:a )?company\b",
                r"\bwatch\b.*\bcompany\b",
                r"\bfollow\b.*\bcompany\b",
            ],
            params=[
                CommandParam("name", "What's the company name?",
                              validator=_validate_string),
                CommandParam("websiteUrl", "Website URL?",
                              type="url", validator=_validate_url),
                CommandParam("careerPageUrl",
                              "Career page URL (optional, just press Enter to skip)?",
                              required=False, type="url",
                              validator=_validate_url),
            ],
            confirmation_template=(
                "I'll add **{name}** ({websiteUrl}) to your watchlist. Confirm?"
            ),
        ),
        Command(
            name="create_saved_search",
            label="Create a saved search",
            description="Create a daily-watched query for a role + location.",
            slash_aliases=["/new-search", "/search"],
            keywords=[
                r"\b(?:create|new|add) (?:a )?(?:saved )?search\b",
                r"\bwatch\b.*\b(?:role|position|job)\b",
            ],
            params=[
                CommandParam("name", "Give the search a short name (e.g., 'Senior Backend Berlin').",
                              validator=_validate_string),
                CommandParam("targetRoles",
                              "What role(s)? Comma-separated.",
                              type="list", validator=_validate_list_csv),
                CommandParam("location",
                              "Where? (city / 'remote' / blank for any)",
                              required=False),
            ],
            confirmation_template=(
                "Saved search **{name}**: roles={targetRoles}, "
                "location={location}. Confirm?"
            ),
        ),
        Command(
            name="find_jobs",
            label="Run a one-off job search",
            description=(
                "Search aggregators now for a role + location. When the "
                "role matches a supported job type (bartender, barista, "
                "café worker, waiter, Pflegehelfer) the results are "
                "strictly filtered to that role."
            ),
            slash_aliases=["/find", "/find-jobs"],
            keywords=[
                r"\bfind (?:me )?(?:a )?(?:\w+ )?(?:job|jobs|role|roles|position|positions)\b",
                r"\bsearch (?:for )?(?:\w+ )?(?:job|jobs|role|roles|position|positions)\b",
                r"\bshow (?:me )?(?:\w+ )?(?:jobs|roles)\b",
                # German triggers
                r"\b(?:suche|finde)\b.*\b(?:job|stelle|arbeit|stellen)\b",
                # Common role mentions that imply "find jobs"
                r"\b(?:bartender|barkeeper|barista|kellner|pflegehelfer|pflegeassistent)\b",
            ],
            params=[
                CommandParam("query", "What role do you want?",
                              validator=_validate_string),
                CommandParam("location",
                              "Where? (city / 'remote' / 'anywhere')",
                              required=False),
            ],
            confirmation_template=(
                "Searching for **{query}** in **{location}**. Confirm?"
            ),
        ),
        Command(
            name="update_profile",
            label="Update your profile",
            description="Change persona, location, target roles, or seniority.",
            slash_aliases=["/profile", "/update-profile"],
            keywords=[
                # NOTE: "(?:set|change) (?:my )?persona" is owned by the
                # set_persona command — narrow this trigger to the
                # location/roles/seniority shapes only so the two
                # commands don't collide on routing.
                r"\bupdate (?:my )?profile\b",
                r"\bchange (?:my )?(?:location|roles|seniority)\b",
                r"\bset (?:my )?(?:location|roles|seniority)\b",
            ],
            params=[
                CommandParam("persona",
                              "Which persona? (tech / marketing / data / "
                              "healthcare-clinical / legal / finance / etc.)",
                              required=False),
                CommandParam("location",
                              "Where are you based? (city or 'remote')",
                              required=False),
                CommandParam("targetRoles",
                              "Target roles? (comma-separated, optional)",
                              required=False, type="list",
                              validator=_validate_list_csv),
            ],
            confirmation_template=(
                "Updating profile — persona={persona}, "
                "location={location}, targetRoles={targetRoles}. Confirm?"
            ),
        ),
        Command(
            name="mark_applied",
            label="Mark an application status",
            description="Update applicationStatus / replied on an imported job.",
            slash_aliases=["/applied", "/mark"],
            keywords=[
                r"\bmark (?:as )?applied\b",
                r"\bset (?:application )?status\b",
                r"\bthey replied\b",
                r"\bgot a reply\b",
            ],
            params=[
                CommandParam("importedJobId",
                              "Which imported job? (paste the id from the Jobs queue)",
                              validator=_validate_string),
                CommandParam("status",
                              "New status? (saved / interested / applied / "
                              "interview / rejected / archived)",
                              validator=_validate_application_status),
                CommandParam("replied",
                              "Did the company reply? (yes/no)",
                              required=False, type="bool",
                              validator=_validate_bool),
            ],
            confirmation_template=(
                "Marking job **{importedJobId}** as **{status}** "
                "(replied={replied}). Confirm?"
            ),
        ),
        Command(
            name="tailor_cv",
            label="Tailor your CV for a specific job",
            description="Re-emphasise the CV against a single imported job's JD (fact-grounded — never invents).",
            slash_aliases=["/tailor", "/tailor-cv"],
            keywords=[
                r"\btailor (?:my )?(?:cv|resume)\b",
                r"\bre[\-_]?write (?:my )?(?:cv|resume)\b",
                r"\bcustomi[sz]e (?:my )?(?:cv|resume)\b",
            ],
            params=[
                CommandParam("importedJobId",
                              "Which imported job? (paste the id from the Jobs queue)",
                              validator=_validate_string),
            ],
            confirmation_template=(
                "Generating a tailored CV for job **{importedJobId}**. Confirm?"
            ),
        ),
        Command(
            name="run_saved_search",
            label="Run a saved search now",
            description="Trigger one of your saved searches immediately.",
            slash_aliases=["/run-search", "/run"],
            keywords=[
                r"\brun (?:a |my |the )?(?:saved )?search\b",
                r"\bcheck (?:my )?(?:saved )?search (?:now|today)\b",
            ],
            params=[
                CommandParam("searchId",
                              "Which saved-search id?",
                              validator=_validate_string),
            ],
            confirmation_template=(
                "Running saved search **{searchId}** now. Confirm?"
            ),
        ),
        Command(
            name="set_persona",
            label="Set your persona",
            description="Switch your persona (tech / marketing / data / legal / healthcare-clinical / etc.).",
            slash_aliases=["/persona", "/set-persona"],
            keywords=[
                r"\b(?:set|change|switch) (?:my )?persona\b",
                r"\bi (?:work|am) (?:in|as|a)\b.*\b(tech|marketing|data|legal|sales|design)\b",
            ],
            params=[
                CommandParam("persona",
                              "Which persona? (tech / marketing / data / "
                              "healthcare-clinical / legal / finance / sales / "
                              "design / hr / operations / education / media / "
                              "support / product-management / healthcare-management)",
                              validator=_validate_string),
            ],
            confirmation_template=(
                "Switching persona to **{persona}**. Confirm?"
            ),
        ),
        Command(
            name="delete_company",
            label="Remove a company from your watchlist",
            description="Stop watching a company. Irreversible — the watchlist row is gone after confirm.",
            slash_aliases=["/delete-company", "/unwatch", "/remove-company"],
            keywords=[
                r"\bremove (?:a )?(?:company|employer)\b",
                r"\bunwatch\b",
                r"\bstop watching\b",
                r"\bdelete (?:a )?(?:company|employer)\b",
            ],
            params=[
                CommandParam("companyId",
                              "Which company id? (paste from Companies tab)",
                              validator=_validate_string),
            ],
            confirmation_template=(
                "**Removing** company **{companyId}** from your watchlist. "
                "This is irreversible. Confirm?"
            ),
        ),
        Command(
            name="suggest_cv_enhancements",
            label="Consult on CV enhancements specific to a JD",
            description=(
                "For the job the user picked in their journey, "
                "compare the JD against the CV and surface 3-5 gap "
                "questions. AI-backed when configured; otherwise a "
                "heuristic keyword diff with an honest banner."
            ),
            slash_aliases=["/consult", "/enhance-cv", "/cv-gaps"],
            keywords=[
                r"\b(?:consult|enhance|improve)\b.*\bcv\b",
                r"\bcv\b.*\b(?:gaps?|enhancements?|improvements?)\b",
            ],
            params=[],
            confirmation_template=(
                "Consulting CV vs. picked JD for enhancement ideas."
            ),
        ),
        Command(
            name="draft_motivation_letter",
            label="Draft a DACH-norm motivation letter",
            description=(
                "Draft a Bewerbungsschreiben in proper DACH "
                "structure (Anrede, 3-paragraph Hauptteil, Schluss) "
                "for a job the user picked in their journey. Uses "
                "the configured AI when available; otherwise emits "
                "a structured template with placeholders + an "
                "honest \"no AI configured\" banner."
            ),
            slash_aliases=["/letter", "/draft-letter", "/motivation"],
            keywords=[
                r"\bdraft\b.*\b(?:motivation|cover|application)\b.*\bletter\b",
                r"\bmotivation(?:s)?(?:schreiben)?\b",
                r"\bbewerbungsschreiben\b",
                r"\banschreiben\b",
            ],
            params=[],
            confirmation_template=(
                "Drafting a motivation letter for your picked job."
            ),
        ),
        Command(
            name="start_job_journey",
            label="Start the guided job-search journey",
            description=(
                "Walk the user end-to-end: gather role/location/CV, "
                "suggest lateral roles, run a categorized search, "
                "drill into a job, draft a motivation letter, and "
                "consult on CV enhancements specific to that JD. "
                "Triggers on explicit job-seeking intent only — bare "
                "greetings do NOT auto-start this."
            ),
            slash_aliases=["/start", "/journey", "/find-job", "/help-me-find"],
            keywords=[
                r"\b(?:i (?:want|need|wanna)|help me|can you help)"
                r"\b.*\b(?:find|look|search|get)\b.*\b(?:job|jobs|role|roles|work|position)\b",
                r"\b(?:find|look for|search for|get|need)\b.*\b(?:a |me a )?\b(?:job|role|position|work)\b",
                r"\b(?:start|begin)\b.*\b(?:job search|journey|hunt)\b",
                r"\b(?:suche|finde|brauche)\b.*\b(?:job|stelle|arbeit|position)\b",
                r"\bhilf mir\b.*\b(?:job|stelle|arbeit)\b",
                r"\bich (?:will|möchte|brauche)\b.*\b(?:job|stelle|arbeit)\b",
            ],
            params=[],
            confirmation_template="Starting your job-search journey.",
        ),
        Command(
            name="accept_cv_text",
            label="Capture pasted CV text into your profile",
            description=(
                "Save a CV the user pasted directly in chat. Skips the "
                "wizard. Only available inside the active journey."
            ),
            slash_aliases=["/paste-cv"],
            keywords=[],  # invoked by journey state machine, not freely
            params=[
                CommandParam("cvText", "Paste your CV (free text — "
                              "we'll store it as-is, never invent).",
                              validator=_validate_string),
            ],
            confirmation_template=(
                "Saving **{cvText}** chars to your profile. Confirm?"
            ),
        ),
        Command(
            name="build_cv_via_chat",
            label="Build your CV sectional via chat",
            description=(
                "Walk through DACH-CV sections (header → summary → "
                "experience → education → skills) via plain chat, no "
                "wizard UI. Each section uses the same fact-ratio "
                "gate as the visual builder."
            ),
            slash_aliases=["/build-cv-chat"],
            keywords=[],
            params=[],
            confirmation_template="Starting CV build — one section at a time.",
        ),
        Command(
            name="open_cv_builder",
            label="Open the CV Builder",
            description="Walk through guided sections to create or update your CV (DACH-style with photo + PDF export). The AI formats, it never invents.",
            slash_aliases=["/cv", "/build-cv", "/create-cv"],
            keywords=[
                r"\b(?:create|generate|build|make|write|start) (?:a |my |me )?(?:new )?(?:cv|resume|lebenslauf)\b",
                r"\bi need (?:you )?(?:to )?(?:generate|create|build|make|write)\b.*\b(?:cv|resume|lebenslauf)\b",
                r"\bhelp (?:me )?(?:write|build|create) (?:my )?(?:cv|resume)\b",
                r"\b(?:open|go to|show me) (?:the )?cv builder\b",
            ],
            params=[],
            confirmation_template="Opening the CV Builder for you.",
        ),
        Command(
            name="help",
            label="Show available commands",
            description="List every command the chat understands.",
            slash_aliases=["/help", "/?"],
            keywords=[
                r"^\s*help\s*$",
                r"\bwhat can you do\b",
                r"\bshow (?:me )?commands\b",
            ],
            params=[],
            confirmation_template="Listing the {n} commands I understand.",
        ),
    ]}


REGISTRY: dict[str, Command] = _build_registry()


def list_commands() -> list[dict[str, Any]]:
    """Public summary of every command, used by the help command and
    surfaced to the AI intent router."""
    return [
        {
            "name": c.name,
            "label": c.label,
            "description": c.description,
            "slashAliases": list(c.slash_aliases),
            "params": [
                {"name": p.name, "prompt": p.prompt,
                  "required": p.required, "type": p.type, "hint": p.hint}
                for p in c.params
            ],
        }
        for c in REGISTRY.values()
    ]


# ---------------- Intent routers ----------------


def parse_slash_command(message: str) -> tuple[str, str] | None:
    """If ``message`` starts with a slash, return (command_name, rest).
    rest is the remainder after the command word — any positional args
    the user typed inline."""
    if not message or not message.strip().startswith("/"):
        return None
    text = message.strip()
    parts = text.split(None, 1)
    head = parts[0].casefold()
    rest = parts[1] if len(parts) > 1 else ""
    for cmd in REGISTRY.values():
        for alias in cmd.slash_aliases:
            if alias.casefold() == head:
                return cmd.name, rest
    return None


def keyword_route(message: str) -> str | None:
    """Match the message against each command's keyword regexes.
    Returns the first matching command id, or None."""
    if not message:
        return None
    lc = message.lower()
    for cmd in REGISTRY.values():
        for pat in cmd.keywords:
            if re.search(pat, lc):
                return cmd.name
    return None


# Patterns that mean "in/at <location>" — covers EN + DE phrasing.
# Captures the location text up to the next punctuation / EOL / "for".
_LOCATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:in|at|around|near)\s+([A-Za-zÄÖÜäöüß ,.\-]+?)"
                r"(?:[.!?;:\n]|$|\bfor\b)",
                re.IGNORECASE),
    # German equivalents
    re.compile(r"\b(?:in|bei)\s+([A-Za-zÄÖÜäöüß ,.\-]+?)"
                r"(?:[.!?;:\n]|$|\bfür\b)",
                re.IGNORECASE),
)


def extract_keyword_args(command_name: str, message: str) -> dict[str, str]:
    """Best-effort args extraction when the keyword router fired.

    The keyword router only knows the command id; this helper digs out
    role + location from the user's natural-language message so the
    server doesn't ask "what role?" right after the user said "find me
    bartender jobs in Berlin". Used for the `find_jobs` command.

    Returns an empty dict for commands we don't recognise here, or
    when nothing could be extracted. Each value is the raw extracted
    text — validators run later.
    """
    from company_discovery.job_type_filter import identify_bucket_with_match

    if not message:
        return {}
    out: dict[str, str] = {}

    if command_name == "find_jobs":
        # Role — match against the taxonomy. We use the LITERAL synonym
        # the user typed (preserving German vs English) as the search
        # query, so aggregators searching the DACH market hit the
        # right postings. The taxonomy still pins which bucket the
        # query belongs to for the strict result filter downstream.
        bucket_key, matched_text = identify_bucket_with_match(message)
        if bucket_key and matched_text:
            out["query"] = matched_text

        # Special tokens take precedence over the generic "in X" pattern,
        # so "Pflegehelfer in Deutschland gesucht" canonicalises to
        # Germany even though the regex would have grabbed
        # "Deutschland gesucht".
        lc = message.lower()
        for tok, canonical in (
            ("in germany", "Germany"),
            ("in deutschland", "Germany"),
            ("anywhere", "anywhere"),
            ("überall", "anywhere"),
            ("ueberall", "anywhere"),
        ):
            if tok in lc:
                out["location"] = canonical
                break

        # Generic "in <city>" / "bei <city>" capture when no special
        # token fired.
        if "location" not in out:
            for pat in _LOCATION_PATTERNS:
                m = pat.search(message)
                if m:
                    loc = m.group(1).strip().rstrip(",").strip()
                    # Trim trailing German verbs that the stop-word
                    # regex didn't catch (e.g. "Berlin gesucht").
                    loc = re.sub(
                        r"\s+(?:gesucht|gesuchten|jetzt|now|m/w/d|\(m/w/d\))\b.*$",
                        "", loc, flags=re.IGNORECASE,
                    ).strip()
                    if loc and len(loc) <= 80:
                        out["location"] = loc
                    break

    return out


def build_ai_router_prompt(message: str, history: list[dict[str, str]]) -> str:
    """Build a strictly-bounded prompt the AI uses to classify intent.

    The AI's ONLY job is to return one of the known command names.
    Any other output is treated as ``unknown`` and falls back to
    ``help``.

    Backwards-compatible: callers that ignore JSON extraction get a
    bare command id (first token). New callers can pass the same
    response through ``parse_ai_router_extracted_args`` to get any
    pre-filled params the AI was able to extract from natural language.
    """
    cmd_lines = "\n".join(
        f"- {c.name}: {c.description}" for c in REGISTRY.values()
    )
    history_text = "\n".join(
        f"{turn['role']}: {turn['content']}" for turn in history[-6:]
    )
    return (
        "You are a CHAT ROUTER. Classify the user's latest message into "
        "ONE of the commands listed below.\n\n"
        "OUTPUT FORMAT — return ONLY a single JSON object on one line:\n"
        '  {"command": "<command_name>", "args": {<param>: <value>, ...}}\n\n'
        "RULES:\n"
        "1. `command` MUST be one of the listed command names, or `unknown` "
        "if no command fits.\n"
        "2. `args` MAY include values you EXTRACTED VERBATIM from the user's "
        "message — never invent values. If you're unsure, omit the param.\n"
        "3. Never invent a company name, URL, role title, or any other fact "
        "that the user did not literally state.\n"
        "4. No prose, no commentary, no markdown. Just the JSON object.\n\n"
        "Available commands:\n"
        f"{cmd_lines}\n\n"
        "Recent conversation:\n"
        f"{history_text}\n\n"
        f"Latest user message: {message}\n\n"
        "JSON output:"
    )


def parse_ai_router_response(raw: str) -> str | None:
    """Map the AI's response to a known command id, or None.

    Accepts BOTH the legacy bare-command-name format AND the new JSON
    format: ``{"command": "add_company", "args": {...}}``. Returns the
    command id; callers that want args also call
    ``parse_ai_router_extracted_args``.
    """
    if not raw:
        return None
    text = raw.strip()
    # New format: JSON object on one line (or wrapped in code fence).
    # Greedy match so the outer {command, args:{...}} wins over the
    # inner args object. The router prompt asks for one JSON object;
    # we accept code-fenced + prose-wrapped variants too.
    json_block = re.search(r'\{[\s\S]*\}', text)
    if json_block:
        try:
            import json as _json
            parsed = _json.loads(json_block.group(0))
        except (_json.JSONDecodeError if False else ValueError):  # type: ignore[misc]
            parsed = None
        # The previous line trips when ValueError is the wrong base; use
        # a plain try/except below for portability.
        if parsed is None:
            try:
                import json as _json
                parsed = _json.loads(json_block.group(0))
            except Exception:  # noqa: BLE001
                parsed = None
        if isinstance(parsed, dict):
            cand = str(parsed.get("command") or "").strip().casefold()
            for cmd in REGISTRY.values():
                if cmd.name == cand:
                    return cmd.name
            # JSON parsed but command missing/unknown → don't fall back
            # to first-token (which would be `{"command":`).
            return None
    # Legacy bare-name format: first whitespace-delimited token.
    candidate = text.split()[0] if text else ""
    candidate = candidate.strip("`'\"").casefold()
    for cmd in REGISTRY.values():
        if cmd.name == candidate:
            return cmd.name
    return None


def parse_ai_router_extracted_args(raw: str) -> dict[str, Any]:
    """Pull the ``args`` dict from the JSON router response, if any.

    Returns an empty dict for the legacy bare-name format. Values are
    NOT validated here — the caller's per-param validator does that
    (so we still reject malformed URLs, etc.)."""
    if not raw:
        return {}
    text = raw.strip()
    # Greedy match so the outer {command, args:{...}} wins over the
    # inner args object. The router prompt asks for one JSON object;
    # we accept code-fenced + prose-wrapped variants too.
    json_block = re.search(r'\{[\s\S]*\}', text)
    if not json_block:
        return {}
    try:
        import json as _json
        parsed = _json.loads(json_block.group(0))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(parsed, dict):
        return {}
    args = parsed.get("args")
    if not isinstance(args, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(k, str) and v is not None:
            out[k] = v
    return out


# ---------------- Slash-command inline-arg parser ----------------


def parse_slash_inline_args(command_name: str, rest: str) -> dict[str, str]:
    """Best-effort: split the rest of a slash command into the command's
    required positional args. Quoted strings via shlex preserve spaces.

    e.g. ``/add Charité "https://www.charite.de"`` →
        {"name": "Charité", "websiteUrl": "https://www.charite.de"}
    """
    cmd = REGISTRY.get(command_name)
    if not cmd or not rest:
        return {}
    try:
        tokens = shlex.split(rest, posix=True)
    except ValueError:
        # Fallback: simple whitespace split if shlex chokes on unbalanced quotes
        tokens = rest.split()
    out: dict[str, str] = {}
    # Map tokens onto required params in order; extras land on optional params.
    required = [p for p in cmd.params if p.required]
    optional = [p for p in cmd.params if not p.required]
    consumed = 0
    for tok, param in zip(tokens, required):
        out[param.name] = tok
        consumed += 1
    for tok, param in zip(tokens[consumed:], optional):
        out[param.name] = tok
    return out


# ---------------- Session state ----------------


@dataclass
class ChatTurn:
    role: str    # "user" | "assistant"
    content: str


@dataclass
class PendingCommand:
    """A command being assembled across multiple turns."""
    command_name: str
    args: dict[str, Any] = field(default_factory=dict)
    # The param-name currently being asked of the user.
    awaiting: str | None = None
    # True once we've shown the confirmation prompt; next user message
    # is expected to confirm/cancel rather than fill more params.
    awaiting_confirmation: bool = False


@dataclass
class ChatSession:
    """Per-user chat state. Lives in memory; resets on server restart.
    JSON-serialisable so future persistence is trivial."""
    history: list[ChatTurn] = field(default_factory=list)
    pending: PendingCommand | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "history": [{"role": t.role, "content": t.content}
                         for t in self.history],
            "pending": (
                {
                    "commandName": self.pending.command_name,
                    "args": dict(self.pending.args),
                    "awaiting": self.pending.awaiting,
                    "awaitingConfirmation": self.pending.awaiting_confirmation,
                }
                if self.pending else None
            ),
        }


# ---------------- Multi-turn elicitation engine ----------------


def next_missing_param(cmd: Command, args: dict[str, Any]) -> CommandParam | None:
    for p in cmd.params:
        if p.required and p.name not in args:
            return p
    return None


def fill_param_from_message(
    cmd: Command,
    param: CommandParam,
    message: str,
) -> tuple[bool, Any]:
    """Validate the user's reply for one specific param. Returns
    (ok, value_or_error)."""
    validator = param.validator or _validate_string
    return validator(message)


def is_confirmation_yes(message: str) -> bool:
    v = (message or "").strip().casefold()
    return v in {"yes", "y", "confirm", "ok", "go", "do it", "ja",
                 "yep", "yeah", "sure", "proceed"}


def is_confirmation_no(message: str) -> bool:
    v = (message or "").strip().casefold()
    return v in {"no", "n", "cancel", "abort", "stop", "nein",
                 "nope", "never mind", "nvm"}


def render_help_text() -> str:
    """The help command's text body — kept plain (no Markdown) because
    the chat surface renders bubbles as ``textContent`` and ``**bold**``
    would show literally."""
    lines = ["Here's what I can do:\n"]
    for c in REGISTRY.values():
        aliases = ", ".join(c.slash_aliases) or "—"
        lines.append(f"• {c.label} ({aliases})")
    lines.append(
        "\nYou can describe what you want in plain language too — "
        "e.g., \"watch Charité, career page karriere.charite.de\" or "
        "\"I need to build a CV\"."
    )
    return "\n".join(lines)
