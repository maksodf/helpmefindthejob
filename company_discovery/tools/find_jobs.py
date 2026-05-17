"""find_jobs — one-off job search.

Tier R (read-only). Migrated from ``chat_router.REGISTRY`` to the new
Pydantic-backed tool registry per the portfolio chat-architecture
reference at ``~/Desktop/personal Projects/_portfolio-architecture/
chat-tool-invocation.md``.

The handler is a thin wrapper around the existing
``AppState.chat_handler_find_jobs`` method — the business logic is
unchanged in this migration step. The wrapper:

1. Accepts validated Pydantic input (replaces legacy
   ``_validate_string`` callable).
2. Calls the existing handler with a dict of validated args.
3. Wraps the dict return value in a ``ToolResult`` envelope.

The legacy handler key names (``totalJobs``, ``jobType``, ``navigateTo``)
are normalised to snake_case here so the wire payload matches the
Pydantic ``FindJobsOutput`` schema. When the handler is fully migrated
later, the snake_case names will become canonical.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool,
    ToolError,
    ToolResult,
    register_tool,
)


class FindJobsInput(BaseModel):
    """find_jobs input schema."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        description=(
            "What role do you want? E.g. 'Pflegehelfer', 'bartender', "
            "'data engineer'. Single role, in the user's preferred "
            "language."
        ),
        min_length=1,
        max_length=200,
    )

    location: str | None = Field(
        default=None,
        description=(
            "Where? A city, 'remote', or 'anywhere'. If omitted, the "
            "user's profile location is used."
        ),
        max_length=120,
    )


class FindJobsJob(BaseModel):
    """One job in the find_jobs response. Mirrors the dict shape
    produced by the legacy handler. ``extra='allow'`` for forward
    compatibility — the legacy handler may add optional fields the
    schema doesn't yet enumerate."""

    model_config = ConfigDict(extra="allow")

    title: str
    company: str
    location: str
    url: str
    source: str


class FindJobsOutput(BaseModel):
    """find_jobs output schema.

    Field names match the wire format expected by the chat frontend
    (camelCase), so downstream consumers (``_enrich_message``,
    ``_tool_outputs`` copy-through) work without translation.
    """

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        description="User-facing chat reply summarising the result.",
    )
    jobs: list[FindJobsJob] = Field(
        description=(
            "The ranked + filtered job results. Empty list if no "
            "matches."
        ),
    )
    totalJobs: int = Field(
        description="Number of jobs in the result set.",
        ge=0,
    )
    jobType: str | None = Field(
        default=None,
        description=(
            "The supported bucket the query mapped to (e.g. "
            "'bartender', 'pflegehelfer') or None if no match."
        ),
    )
    categories: list[str] = Field(
        default_factory=list,
        description=(
            "Cluster labels (e.g. by city / company size) the user "
            "can drill into in the search-results view."
        ),
    )
    navigateTo: str | None = Field(
        default=None,
        description=(
            "Optional view ID the frontend should switch to. Only "
            "set when results are non-empty."
        ),
    )


def find_jobs_handler(
    input: FindJobsInput, ctx: dict[str, Any]
) -> ToolResult:
    """find_jobs handler — wraps the legacy
    ``AppState.chat_handler_find_jobs``.

    The context dict must carry:
      - ``state``: the AppState instance
      - ``user_id``: str
    """
    state = ctx["state"]
    user_id = ctx["user_id"]
    legacy_result = state.chat_handler_find_jobs(
        user_id, input.model_dump(exclude_none=True)
    )
    if not legacy_result.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="search_failed",
                message=legacy_result.get(
                    "message", "Job search failed."
                ),
                retryable=False,
            ),
        )
    # Preserve the legacy camelCase wire shape so downstream consumers
    # (``_enrich_message``, ``_tool_outputs`` copy-through in
    # ``app.py``) work without translation.
    return ToolResult(
        ok=True,
        data={
            "message": legacy_result.get("message", ""),
            "jobs": legacy_result.get("jobs", []),
            "totalJobs": legacy_result.get("totalJobs", 0),
            "jobType": legacy_result.get("jobType"),
            "categories": legacy_result.get("categories", []),
            "navigateTo": legacy_result.get("navigateTo"),
        },
    )


register_tool(Tool(
    name="find_jobs",
    label="Run a one-off job search",
    description=(
        "Search job aggregators now for a role + location. When the "
        "role matches a supported job type (bartender, barista, "
        "café worker, waiter, Pflegehelfer) results are strictly "
        "filtered to that role. Read-only — runs immediately, no "
        "confirmation gate. Returns a summary message + ranked job "
        "cards + cluster categories the user can drill into."
    ),
    tier="R",
    input_schema=FindJobsInput,
    output_schema=FindJobsOutput,
    handler=find_jobs_handler,
    keywords=[
        r"\bfind (?:me )?(?:a )?(?:\w+ )?(?:job|jobs|role|roles|position|positions)\b",
        r"\bsearch (?:for )?(?:\w+ )?(?:job|jobs|role|roles|position|positions)\b",
        r"\bshow (?:me )?(?:\w+ )?(?:jobs|roles)\b",
        r"\b(?:suche|finde)\b.*\b(?:job|stelle|arbeit|stellen)\b",
        r"\b(?:bartender|barkeeper|barista|kellner|pflegehelfer|pflegeassistent)\b",
    ],
    slash_aliases=["/find", "/find-jobs"],
    confirmation_template="Searching for **{query}** in **{location}**.",
))
