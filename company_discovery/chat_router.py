# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

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
from typing import Any, Callable

# ---------------- Command schema ----------------


@dataclass
class CommandParam:
    """One typed parameter of a command."""

    name: str
    prompt: str  # what the user sees when we elicit this field
    required: bool = True
    type: str = "string"  # "string" | "url" | "list" | "bool"
    hint: str | None = None
    # Optional validator — returns (ok, error_message_or_canonical_value)
    validator: Callable[[str], tuple[bool, Any]] | None = None


@dataclass
class Command:
    """A typed function-call the chat router can execute."""

    name: str
    label: str  # human-readable
    description: str  # used by AI / keyword matchers
    params: list[CommandParam] = field(default_factory=list)
    # Keyword triggers — regex patterns, in priority order. Used by the
    # keyword router before AI is invoked. Each pattern is case-insensitive.
    keywords: list[str] = field(default_factory=list)
    slash_aliases: list[str] = field(default_factory=list)
    # Confirmation template — Python str.format with kwargs from params.
    confirmation_template: str = ""
    # When False, the dispatcher skips the "Confirm?" prompt and
    # executes immediately once all required params are present. Use
    # for read-only / non-destructive commands (find_jobs, show_view,
    # help, suggest_*, draft_*) where asking permission to think is
    # friction. Destructive commands (add_company, mark_applied,
    # delete_company, etc.) keep the gate.
    requires_confirmation: bool = True

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
    valid = {"saved", "interested", "applied", "interview", "rejected", "archived"}
    if v in valid:
        return True, v
    return False, f"Status must be one of: {', '.join(sorted(valid))}."


# ---------------- Built-in command registry ----------------


def _build_registry() -> dict[str, Command]:
    return {
        c.name: c
        for c in [
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
                    CommandParam("name", "What's the company name?", validator=_validate_string),
                    CommandParam("websiteUrl", "Website URL?", type="url", validator=_validate_url),
                    CommandParam(
                        "careerPageUrl",
                        "Career page URL (optional, just press Enter to skip)?",
                        required=False,
                        type="url",
                        validator=_validate_url,
                    ),
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
                    CommandParam(
                        "name",
                        "Give the search a short name (e.g., 'Senior Backend Berlin').",
                        validator=_validate_string,
                    ),
                    CommandParam(
                        "targetRoles",
                        "What role(s)? Comma-separated.",
                        type="list",
                        validator=_validate_list_csv,
                    ),
                    CommandParam(
                        "location", "Where? (city / 'remote' / blank for any)", required=False
                    ),
                ],
                confirmation_template=(
                    "Saved search **{name}**: roles={targetRoles}, location={location}. Confirm?"
                ),
            ),
            Command(
                name="find_jobs",
                label="Run a one-off job search",
                description=(
                    "Search aggregators now for a role + location. When the "
                    "role matches a supported job type (bartender, barista, "
                    "café worker, waiter, Pflegehelfer) the results are "
                    "strictly filtered to that role. Read-only — runs "
                    "immediately, no confirmation gate."
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
                    CommandParam("query", "What role do you want?", validator=_validate_string),
                    CommandParam(
                        "location", "Where? (city / 'remote' / 'anywhere')", required=False
                    ),
                ],
                confirmation_template=("Searching for **{query}** in **{location}**."),
                requires_confirmation=False,
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
                    CommandParam(
                        "persona",
                        "Which persona? (tech / marketing / data / "
                        "healthcare-clinical / legal / finance / etc.)",
                        required=False,
                    ),
                    CommandParam(
                        "location", "Where are you based? (city or 'remote')", required=False
                    ),
                    CommandParam(
                        "targetRoles",
                        "Target roles? (comma-separated, optional)",
                        required=False,
                        type="list",
                        validator=_validate_list_csv,
                    ),
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
                    CommandParam(
                        "importedJobId",
                        "Which imported job? (paste the id from the Jobs queue)",
                        validator=_validate_string,
                    ),
                    CommandParam(
                        "status",
                        "New status? (saved / interested / applied / "
                        "interview / rejected / archived)",
                        validator=_validate_application_status,
                    ),
                    CommandParam(
                        "replied",
                        "Did the company reply? (yes/no)",
                        required=False,
                        type="bool",
                        validator=_validate_bool,
                    ),
                ],
                confirmation_template=(
                    "Marking job **{importedJobId}** as **{status}** (replied={replied}). Confirm?"
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
                    # Loop 15 (2026-05-20): DE coverage. Both noun-
                    # first ("CV anpassen") + verb-first
                    # ("anpassen meinen Lebenslauf") forms.
                    r"\b(?:cv|lebenslauf)\s+(?:anpassen|maßschneidern|zuschneiden|aufpolieren|umarbeiten)\b",
                    r"\b(?:anpassen|maßschneidern|zuschneiden|aufpolieren|umarbeiten)\s+(?:meinen?\s+)?(?:cv|lebenslauf)\b",
                ],
                params=[
                    CommandParam(
                        "importedJobId",
                        "Which imported job? (paste the id from the Jobs queue)",
                        validator=_validate_string,
                    ),
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
                    CommandParam("searchId", "Which saved-search id?", validator=_validate_string),
                ],
                confirmation_template=("Running saved search **{searchId}** now. Confirm?"),
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
                    CommandParam(
                        "persona",
                        "Which persona? (tech / marketing / data / "
                        "healthcare-clinical / legal / finance / sales / "
                        "design / hr / operations / education / media / "
                        "support / product-management / healthcare-management)",
                        validator=_validate_string,
                    ),
                ],
                confirmation_template=("Switching persona to **{persona}**. Confirm?"),
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
                    CommandParam(
                        "companyId",
                        "Which company id? (paste from Companies tab)",
                        validator=_validate_string,
                    ),
                ],
                confirmation_template=(
                    "**Removing** company **{companyId}** from your watchlist. "
                    "This is irreversible. Confirm?"
                ),
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
                requires_confirmation=False,
            ),
            Command(
                name="show_view",
                label="Show a specific view on the canvas",
                description=(
                    "Surface one of the app's views (dashboard / "
                    "companies / jobs / briefcase / settings / cv-builder) "
                    "on the right-side canvas. Read-only navigation — "
                    "no DB writes, no confirmation gate."
                ),
                slash_aliases=["/show", "/open", "/go-to", "/view"],
                keywords=[
                    # English
                    r"\b(?:show|open|go to|switch to|take me to|view)\b.*\b(?:watchlist|companies|company list)\b",
                    r"\b(?:show|open|go to|switch to|take me to|view)\b.*\b(?:queue|imported|jobs|job list|saved jobs)\b",
                    r"\b(?:show|open|go to|switch to|take me to|view)\b.*\b(?:dashboard|today|home)\b",
                    r"\b(?:show|open|go to|switch to|take me to|view)\b.*\b(?:applications|briefcase|tracker)\b",
                    r"\b(?:show|open|go to|switch to|take me to|view)\b.*\b(?:settings|profile|preferences|config)\b",
                    r"\bmy (?:watchlist|companies|queue|jobs|applications|briefcase)\b",
                    # German
                    r"\b(?:zeig|öffne|gehe zu|geh zu|wechsle)\b.*\b(?:watchlist|firmen|unternehmen|liste)\b",
                    r"\b(?:zeig|öffne|gehe zu|geh zu|wechsle)\b.*\b(?:jobs|stellen|warteschlange)\b",
                    r"\b(?:zeig|öffne|gehe zu|geh zu|wechsle)\b.*\b(?:einstellungen|profil)\b",
                    r"\b(?:zeig|öffne|gehe zu|geh zu|wechsle)\b.*\b(?:heute|dashboard|startseite)\b",
                ],
                params=[
                    CommandParam(
                        "target",
                        "Which view? (dashboard / companies / jobs / brief / settings / cvBuilder)",
                        validator=_validate_string,
                    ),
                ],
                confirmation_template="Opening **{target}**.",
                requires_confirmation=False,
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
                    # Loop 15 (2026-05-20): DE coverage. Common DE
                    # phrasing: "CV verbessern" / "Lebenslauf
                    # optimieren" / "meinen Lebenslauf verbessern".
                    r"\b(?:cv|lebenslauf)\s+(?:verbessern|optimieren|verbessere|optimiere)\b",
                    r"\b(?:verbessern|optimieren|verbessere|optimiere)\s+(?:meinen?\s+)?(?:cv|lebenslauf)\b",
                ],
                params=[],
                confirmation_template=("Consulting CV vs. picked JD for enhancement ideas."),
                requires_confirmation=False,
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
                    'honest "no AI configured" banner.'
                ),
                slash_aliases=["/letter", "/draft-letter", "/motivation"],
                keywords=[
                    r"\bdraft\b.*\b(?:motivation|cover|application)\b.*\bletter\b",
                    # Loop 15 (2026-05-20): widen verb set so
                    # "write me a cover letter" / "compose a
                    # motivation letter" / "prepare an application
                    # letter" all match.
                    r"\b(?:write|writing|compose|prepare)\b.*\b(?:motivation|cover|application)\b.*\bletter\b",
                    r"\bmotivation(?:s)?(?:schreiben)?\b",
                    r"\bbewerbungsschreiben\b",
                    r"\banschreiben\b",
                ],
                params=[],
                confirmation_template=("Drafting a motivation letter for your picked job."),
                requires_confirmation=False,
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
                    CommandParam(
                        "cvText",
                        "Paste your CV (free text — we'll store it as-is, never invent).",
                        validator=_validate_string,
                    ),
                ],
                confirmation_template=("Saving **{cvText}** chars to your profile. Confirm?"),
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
                name="download_cv",
                label="Download your CV as a PDF",
                description=(
                    "Open the print-styled CV page so the user can "
                    "save it as PDF from their browser. Read-only — "
                    "needs an existing CV on the profile."
                ),
                slash_aliases=["/download-cv", "/cv-pdf", "/print-cv"],
                keywords=[
                    r"\bdownload (?:my )?(?:cv|resume|lebenslauf)\b",
                    r"\bsave (?:my )?(?:cv|resume|lebenslauf) (?:as )?pdf\b",
                    r"\bget (?:my )?(?:cv|resume|lebenslauf) (?:as )?pdf\b",
                    r"\b(?:lebenslauf|cv) (?:als )?pdf herunterladen\b",
                    r"\b(?:herunterladen|drucken|speichern)\b.*\b(?:lebenslauf|cv)\b",
                ],
                params=[],
                confirmation_template="Opening your CV in print view.",
                requires_confirmation=False,
            ),
            Command(
                name="delete_account",
                label="Delete your account (GDPR right-to-erasure)",
                description=(
                    "Start the account-deletion flow. The agent emails "
                    "you a confirmation link. After you click, a 7-day "
                    "grace window starts before your data is erased — "
                    "you can cancel from Settings any time in that "
                    "window. Destructive: keeps the confirmation gate."
                ),
                slash_aliases=[
                    "/delete-account",
                    "/delete-my-account",
                    "/erase-account",
                ],
                keywords=[
                    r"\bdelete (?:my )?account\b",
                    r"\berase (?:my )?account\b",
                    r"\bclose (?:my )?account\b",
                    r"\bkonto (?:löschen|loeschen)\b",
                    r"\b(?:löschen|loeschen) (?:mein|meines)? konto\b",
                    r"\bgdpr\b.*(?:delete|erase|right to erasure)",
                    r"\bdsgvo\b.*(?:löschen|loeschen|löschung|loeschung)",
                ],
                params=[
                    CommandParam(
                        "email",
                        "To confirm, type your account email exactly (the one you signed up with):",
                        validator=_validate_string,
                    ),
                ],
                confirmation_template=(
                    "I'll start deletion for **{email}** — you'll get a "
                    "confirmation email with a link. Clicking the link "
                    "starts a 7-day grace window before any data is "
                    "erased. Confirm?"
                ),
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
                    # Loop 15 (2026-05-20): DE coverage.
                    r"^\s*hilfe\s*$",
                    r"\bwas kannst du\b",
                    r"\bwas kann ich tun\b",
                ],
                params=[],
                confirmation_template="Listing the {n} commands I understand.",
                requires_confirmation=False,
            ),
            # Phase 2 #76 sub-piece (a): user-confirmation flow for the
            # friction-class classification. After a CV paste, the
            # journey reply tells the user what was inferred + invites
            # them to "change classification" or "skip classification".
            Command(
                name="friction_class_change",
                label="Change your friction-class classification",
                description="Pick a different friction-class (Aïcha / Yusuf / Olga / Mahmoud / Maria / Käthe / Tobias) than the one inferred from your CV.",
                slash_aliases=["/friction", "/friction-class"],
                keywords=[
                    r"\bchange (?:my )?classification\b",
                    r"\bchange (?:my )?friction[- ]class\b",
                    r"\bpick (?:a )?different (?:friction[- ]class|classification|process)\b",
                    # DE coverage
                    r"\bklassifikation (?:ändern|wechseln)\b",
                    r"\bfriktionsklasse (?:ändern|wechseln)\b",
                ],
                params=[
                    CommandParam(
                        "slug",
                        "Which friction class? (aicha / yusuf / olga / mahmoud / maria / kaethe / tobias, or 'list' to see all 7 with labels)",
                        validator=_validate_string,
                    ),
                ],
                confirmation_template=(
                    "Setting your friction-class classification to **{slug}**. Confirm?"
                ),
                requires_confirmation=False,
            ),
            Command(
                name="friction_class_skip",
                label="Skip the friction-class classification",
                description="Clear the auto-inferred friction-class so downstream UX treats you as no-clear-match (opts out of class-aware routing for this session).",
                slash_aliases=["/skip-friction", "/friction-skip"],
                keywords=[
                    r"\bskip (?:my )?(?:friction[- ]class|classification)\b",
                    r"\bopt out (?:of )?(?:friction[- ]class|classification)\b",
                    # DE coverage
                    r"\b(?:friktions)?klassifikation überspringen\b",
                    r"\bfriktionsklasse löschen\b",
                ],
                params=[],
                confirmation_template="Clearing your friction-class classification.",
                requires_confirmation=False,
            ),
        ]
    }


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
                {
                    "name": p.name,
                    "prompt": p.prompt,
                    "required": p.required,
                    "type": p.type,
                    "hint": p.hint,
                }
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
    re.compile(
        r"\b(?:in|at|around|near)\s+([A-Za-zÄÖÜäöüß ,.\-]+?)"
        r"(?:[.!?;:\n]|$|\bfor\b)",
        re.IGNORECASE,
    ),
    # German equivalents
    re.compile(
        r"\b(?:in|bei)\s+([A-Za-zÄÖÜäöüß ,.\-]+?)"
        r"(?:[.!?;:\n]|$|\bfür\b)",
        re.IGNORECASE,
    ),
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
                        "",
                        loc,
                        flags=re.IGNORECASE,
                    ).strip()
                    if loc and len(loc) <= 80:
                        out["location"] = loc
                    break

        # R19: last-resort city scan for users typing in a script we
        # don't know (Arabic, Chinese, Cyrillic, etc.) but who still
        # mention a German/EU city in Latin script. Without this, an
        # Arabic-speaking user typing "أريد bartender في Berlin" gets
        # no location extracted. We scan for the same DE-city list
        # job_type_filter expands "Germany" into, plus a few more
        # major EU cities the aggregator commonly returns.
        if "location" not in out:
            from company_discovery.job_type_filter import _GERMAN_CITIES

            extra_cities = (
                "vienna",
                "wien",
                "zurich",
                "zürich",
                "london",
                "paris",
                "amsterdam",
                "warsaw",
                "prague",
                "budapest",
                "lisbon",
                "madrid",
                "barcelona",
                "rome",
                "milan",
                "remote",
            )
            haystack = message.casefold()
            for city in (*_GERMAN_CITIES, *extra_cities):
                if re.search(
                    rf"(?<![A-Za-zÄÖÜäöüß]){re.escape(city)}"
                    rf"(?![A-Za-zÄÖÜäöüß])",
                    haystack,
                ):
                    # Title-case for display; preserves the user
                    # intent.
                    out["location"] = city.title()
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
    cmd_lines = "\n".join(f"- {c.name}: {c.description}" for c in REGISTRY.values())
    history_text = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history[-6:])
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
    json_block = re.search(r"\{[\s\S]*\}", text)
    if json_block:
        try:
            import json as _json

            parsed = _json.loads(json_block.group(0))
        except _json.JSONDecodeError if False else ValueError:  # type: ignore[misc]  # noqa: B030 - conditional except retained for explanation that follows
            parsed = None
        # The previous line trips when ValueError is the wrong base; use
        # a plain try/except below for portability.
        if parsed is None:
            try:
                import json as _json

                parsed = _json.loads(json_block.group(0))
            except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
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
    json_block = re.search(r"\{[\s\S]*\}", text)
    if not json_block:
        return {}
    try:
        import json as _json

        parsed = _json.loads(json_block.group(0))
    except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
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
    role: str  # "user" | "assistant"
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
            "history": [{"role": t.role, "content": t.content} for t in self.history],
            "pending": (
                {
                    "commandName": self.pending.command_name,
                    "args": dict(self.pending.args),
                    "awaiting": self.pending.awaiting,
                    "awaitingConfirmation": self.pending.awaiting_confirmation,
                }
                if self.pending
                else None
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
    """Generous yes-detector — accepts EN + DE variants, slang
    (\"ofc\", \"absolutely\"), affirmative emoji/punctuation
    (e.g. \"yes!\"). Trailing punctuation is stripped."""
    v = (message or "").strip().casefold().rstrip("!.?,")
    return v in {
        # EN
        "yes",
        "y",
        "yep",
        "yeah",
        "yup",
        "yah",
        "yess",
        "confirm",
        "confirmed",
        "ok",
        "okay",
        "k",
        "kk",
        "go",
        "go ahead",
        "do it",
        "let's go",
        "lets go",
        "sure",
        "absolutely",
        "definitely",
        "of course",
        "ofc",
        "proceed",
        "right",
        "correct",
        "true",
        # DE
        "ja",
        "jawohl",
        "klar",
        "logisch",
        "natürlich",
        "natuerlich",
        "auf jeden",
        "auf jeden fall",
        "passt",
        "stimmt",
        "richtig",
        # Common positive emoji as text
        "👍",
        "✓",
        "✔",
    }


def is_confirmation_no(message: str) -> bool:
    """Generous no-detector with similar tolerance."""
    v = (message or "").strip().casefold().rstrip("!.?,")
    return v in {
        "no",
        "n",
        "nope",
        "nah",
        "naw",
        "nay",
        "cancel",
        "canceled",
        "cancelled",
        "abort",
        "stop",
        "skip",
        "never mind",
        "nevermind",
        "nvm",
        "no thanks",
        "no thank you",
        # DE
        "nein",
        "ne",
        "nö",
        "noe",
        "nope nicht",
        "abbrechen",
        "stoppen",
        "lass es",
        # Emoji
        "👎",
        "✗",
        "✘",
    }


def render_help_text() -> str:
    """The help command's text body — kept plain (no Markdown) because
    the chat surface renders bubbles as ``textContent`` and ``**bold**``
    would show literally.

    Loop 17 (2026-05-20): Gate 6.3 — enriched output now includes
    the first sentence of each command's description so /help is a
    real discoverability surface instead of an alias dump. Falls
    back to label-only when description is empty (defensive)."""
    lines = ["Here's what I can do:\n"]
    for c in REGISTRY.values():
        aliases = ", ".join(c.slash_aliases) or "—"
        # First sentence of the description (truncate at "." followed
        # by space or EOL). Keeps the help text scannable while
        # surfacing what each command actually does.
        desc = (c.description or "").strip()
        if desc:
            first_period = desc.find(". ")
            if first_period > 0:
                desc = desc[: first_period + 1]
            lines.append(f"• {c.label} ({aliases})")
            lines.append(f"    {desc}")
        else:
            lines.append(f"• {c.label} ({aliases})")
    lines.append(
        "\nYou can describe what you want in plain language too — "
        'e.g., "watch Charité, career page karriere.charite.de" or '
        '"I need to build a CV".'
    )
    lines.append(
        "Universal escape hatches at any phase: cancel / exit / "
        "quit / stop / nevermind / abbrechen / vergiss es."
    )
    return "\n".join(lines)
