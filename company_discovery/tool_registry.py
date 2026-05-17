"""Portfolio-standard tool registry — Pydantic-backed.

Replaces the hand-rolled command-to-schema converter in
``tool_use_router._command_to_tool_schema`` and the dataclass-based
``Command`` shape in ``chat_router``. Per the portfolio chat-architecture
reference at ``~/Desktop/personal Projects/_portfolio-architecture/
chat-tool-invocation.md``.

Why the migration
=================

The legacy command-to-schema converter can only express:
  - top-level string / array<string> / boolean / url-string parameters
  - a single ``required`` bool per param

It cannot express:
  - nested objects (e.g. ``{address: {street, city, postcode}}``)
  - enums (e.g. ``status: 'applied' | 'interview' | 'rejected'``)
  - numeric types or ranges
  - oneOf / anyOf / discriminated unions
  - arrays of typed objects

Pydantic gives us all of the above for free via ``model_json_schema()``,
and the same models double as runtime input validators. The legacy
``CommandParam.validator`` callable is replaced by Pydantic field
validators.

Each Tool also carries:
  - a CRUD-parity ``tier`` (R / I / N / B) that drives confirmation,
    undo, and pending-action behavior — see the portfolio reference
    for the policy.
  - a ``ToolResult`` envelope as its return type, replacing the ad-hoc
    dicts the legacy handlers return.

Migration path: tools migrate one at a time from
``chat_router.REGISTRY`` to this module's registry. The dispatcher in
``tool_use_router`` checks this registry first, falls back to the
legacy one. When the legacy registry is empty, ``Command`` and
``CommandParam`` are deleted.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Type

from pydantic import BaseModel, ConfigDict, ValidationError


# ============================================================
# CRUD-parity tier annotation
# ============================================================

Tier = Literal["R", "I", "N", "B"]
"""CRUD-parity tier — drives confirmation, undo, and pending-action
behavior.

- ``R`` Read.            No friction. No confirmation. No undo.
- ``I`` Idempotent write. Toast + undo window. ``reversal_token``
                          returned in ToolResult; ``undo_last_action``
                          consumes it.
- ``N`` Non-idempotent write. Preview -> confirm -> commit. Tool
                              inserts a ``pending_actions`` row and
                              returns ``status: "pending"``; user
                              click triggers the actual commit.
- ``B`` Bulk destructive. Hard modal + typed confirmation required.
                          Cannot be auto-confirmed by the agent.

Classification rule: a tool is Tier I if its mutation is reversible
without external side-effect; Tier N if it has external side-effect
(email sent, payment captured, account deleted, file delivered to a
third party); Tier B if it affects >=10 records and is irreversible.
"""


# ============================================================
# Tool result envelope
# ============================================================

class ToolError(BaseModel):
    """Structured error returned inside a ``ToolResult``.

    Goes into ``tool_result.content`` with ``is_error: true`` so the
    model treats it as recoverable and can retry or clarify on its
    next iteration.
    """

    model_config = ConfigDict(extra="forbid")

    code: str
    """Stable machine-readable code, e.g. ``validation_failed``,
    ``rate_limited``, ``not_found``, ``permission_denied``,
    ``cap_exhausted``, ``upstream_unavailable``."""

    message: str
    """Human-readable message safe to display to the end user.
    Localised when possible."""

    retryable: bool = False
    """Whether retrying with the same input may succeed. The
    orchestrator handles backoff; the model should not immediately
    re-call on its own."""

    user_hint: str | None = None
    """Optional actionable next-step the LLM can fold into its reply,
    e.g. ``You can upgrade your plan to raise this cap.``"""


class ToolResult(BaseModel):
    """Universal envelope returned by every tool handler.

    The ``data`` field is intentionally untyped at the envelope level
    — callers introspect the tool's declared ``output_schema`` to
    know the shape. Pydantic v2 supports generic envelopes but the
    wins are minor here and the loose type keeps the dispatcher
    simple.
    """

    model_config = ConfigDict(extra="forbid")

    ok: bool

    data: dict[str, Any] | None = None
    """Success payload, schema-conformant to ``Tool.output_schema``."""

    error: ToolError | None = None
    """Set when ``ok=False``. Mutually exclusive with ``data``."""

    reversal_token: str | None = None
    """Tier I only. Opaque token consumable by ``undo_last_action``.
    Persisted server-side keyed to the originating tool_call_id."""

    pending_action_id: str | None = None
    """Tier N only. ID of the row in ``pending_actions``. The chat
    surface renders an inline confirmation card whose commit button
    POSTs to ``/api/pending-actions/<id>/commit``."""


# ============================================================
# Tool registration record
# ============================================================

# The handler receives:
#   1. validated input — instance of Tool.input_schema
#   2. context dict — user_id, request, locale, etc. (typed in Step 1c)
# and returns a ToolResult.
ToolHandler = Callable[[Any, dict[str, Any]], ToolResult]


@dataclass
class Tool:
    """A registered chat tool — the portfolio-standard shape.

    Replaces ``chat_router.Command`` as tools migrate. Each Tool owns
    its input/output Pydantic schemas, the CRUD tier, and the handler.
    Metadata fields (keywords, slash_aliases, description) carry over
    from Command for the keyword + AI intent routers.
    """

    name: str
    """Stable tool identifier. Same as the legacy ``Command.name``
    during migration so the dispatcher can find it by name regardless
    of which registry it lives in."""

    label: str
    """Human-readable name for UI / confirmation prompts."""

    description: str
    """Tool description shown to the LLM. Per Anthropic's "Writing
    effective tools" guidance: describe agent jobs-to-be-done, not
    REST endpoints. Be specific about when to use this vs alternatives.
    Tool descriptions are load-bearing — any change invalidates the
    Anthropic prompt cache for the whole tools array."""

    tier: Tier

    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    handler: ToolHandler

    # Routing metadata carried from legacy Command
    keywords: list[str] = field(default_factory=list)
    """Regex patterns matched by the keyword router before AI is
    invoked. Case-insensitive."""

    slash_aliases: list[str] = field(default_factory=list)
    """Slash-command aliases users can type, e.g. ``/find``."""

    confirmation_template: str = ""
    """For Tier N tools — the preview/confirmation string shown to
    the user. Python ``str.format`` applied with the validated input
    dict. Empty string for tiers that don't pre-confirm."""

    capture_inverse: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None
    """For Tier I tools whose inverse depends on PRE-execution state.
    Runs BEFORE the handler so it can read the previous value
    (e.g. ``set_persona`` reads ``profile.persona_id`` before the
    handler overwrites it). Mutually exclusive with
    ``capture_inverse_after``.
    """

    capture_inverse_after: Callable[[Any, dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None
    """For Tier I tools whose inverse depends on POST-execution state.
    Runs AFTER a successful handler and receives the handler's
    result data dict. Used when the inverse needs an identifier the
    handler assigns at creation time (e.g. ``add_company`` needs the
    newly minted ``companyId`` for ``delete_company`` as inverse).
    Mutually exclusive with ``capture_inverse``.
    """

    inverse_tool: str = ""
    """The tool that ``undo_last_action`` will dispatch with the
    captured inverse args. For most Tier I tools this is the same
    tool name (the action is its own inverse with previous args).
    For asymmetric pairs (``add_company`` ↔ ``delete_company``) it
    points at the partner tool. Required for Tier I.
    """

    def requires_confirmation(self) -> bool:
        """Tier N and Tier B require explicit confirmation; R and I
        flow through (I uses post-execution undo-toast, not
        pre-execution confirmation)."""
        return self.tier in ("N", "B")

    def anthropic_tool_spec(self) -> dict[str, Any]:
        """Generate the Anthropic-shaped tool spec for the ``tools``
        array in a Messages API call. Uses Pydantic's own JSON Schema
        generation rather than the hand-rolled converter in
        ``tool_use_router._command_to_tool_schema``.
        """
        schema = self.input_schema.model_json_schema()
        # Pydantic v2 omits the ``required`` key entirely when no
        # fields are required. Anthropic's tool spec wants it present
        # (empty array is fine) so downstream code can rely on its
        # existence — matches the legacy converter's invariant.
        if "required" not in schema:
            schema["required"] = []
        return {
            "name": self.name,
            "description": self.description.strip(),
            "input_schema": schema,
        }


# ============================================================
# Module-level registry
# ============================================================

_REGISTRY: dict[str, Tool] = {}
_LOADED = False


def _ensure_loaded() -> None:
    """Lazy-load the tools subpackage on first access. Each tool
    module registers itself via import side-effect. We do this here
    (rather than at ``tool_registry`` import time) to avoid the
    circular import that would occur if a tool module imported
    ``tool_registry`` while ``tool_registry`` was importing it.

    If the tools package import fails, the registry stays empty and
    the dispatcher falls back to the legacy ``chat_router.REGISTRY``
    path — the app keeps working but every Phase 1 enhancement
    (Pydantic validation, tier-based behaviour, reversal tokens,
    idempotency, tool spans) silently disappears. That is a major
    incident-class regression, so we log it loudly. Don't ``pass``
    silently — a comforting comment doesn't make a failure visible
    to operators.
    """
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        import company_discovery.tools  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger("directjob.tool_registry").error(
            "tool_registry: failed to import company_discovery.tools "
            "(%s). The new-registry features are DISABLED; "
            "dispatcher will fall back to legacy chat_router.REGISTRY. "
            "Investigate immediately — this is a silent degradation "
            "of Pydantic validation, tier-based undo, idempotency, "
            "and tool spans.", exc, exc_info=True,
        )


def register_tool(tool: Tool) -> None:
    """Register a tool. Raises ``ValueError`` if the name is taken."""
    if tool.name in _REGISTRY:
        raise ValueError(
            f"Tool '{tool.name}' already registered. "
            "Names must be unique across the new registry."
        )
    _REGISTRY[tool.name] = tool


def get_tool(name: str) -> Tool | None:
    """Look up a tool by name. Returns ``None`` if not in the new
    registry — the dispatcher then falls back to
    ``chat_router.REGISTRY`` during migration."""
    _ensure_loaded()
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    """Return all registered tools in insertion order."""
    _ensure_loaded()
    return list(_REGISTRY.values())


def clear_registry() -> None:
    """Test-only — wipe the registry and reset the lazy-load flag.
    Production code should never call this; tools register at module
    import time."""
    global _LOADED
    _REGISTRY.clear()
    _LOADED = False


def try_dispatch(
    name: str, args: dict[str, Any], ctx: dict[str, Any]
) -> dict[str, Any] | None:
    """Migration seam: if ``name`` is in the new registry, validate
    input + call handler + return a legacy-shaped dict for the
    dispatcher in ``app.py:_dispatch`` to consume. Returns ``None`` if
    the tool is not in the new registry — caller falls back to the
    legacy ``chat_execute_command`` path.

    Conversion at the seam:
      - validation failure → ``{"ok": False, "message": <details>}``
      - handler ``ToolResult.ok=False`` → ``{"ok": False, "message": <error.message>}``
      - handler ``ToolResult.ok=True`` → ``{"ok": True, **data}``

    The handler's ``data`` dict is spread to the top level so existing
    downstream consumers that do ``out["totalJobs"]`` keep working
    without modification. When the legacy ``chat_execute_command``
    path is finally removed, this seam goes with it.
    """
    tool = get_tool(name)
    if tool is None:
        return None
    span_t0 = time.perf_counter()
    user_id = ctx.get("user_id", "")
    turn_id = ctx.get("tool_call_id", "")
    store = ctx.get("tool_actions_store")

    def _emit_span(*, success: bool, error_code: str, cache_hit: bool):
        if store is None:
            return
        dur_ms = int((time.perf_counter() - span_t0) * 1000)
        store.record_tool_span(
            turn_id=turn_id, user_id=user_id, tool_name=name,
            tier=tool.tier, success=success, error_code=error_code,
            duration_ms=dur_ms, cache_hit=cache_hit,
        )

    ok, validated_or_err = validate_input(tool, args)
    if not ok:
        err = validated_or_err
        _emit_span(success=False, error_code="validation_failed",
                   cache_hit=False)
        return {"ok": False, "message": err.message}  # type: ignore[union-attr]

    # Phase 1 / Step 6 — idempotency cache for non-read tools.
    # Returns the cached result without re-running the handler when
    # the same (user, tool, args) was just executed. Window is short
    # (60s) — long enough to absorb network retries and LLM
    # re-emissions across iterations, short enough that the user can
    # intentionally repeat an action within a normal session.
    idem_key: str | None = None
    if tool.tier in ("I", "N", "B") and store is not None:
        idem_key = _idempotency_key(user_id, name, validated_or_err)
        cached = store.get_idempotent(key=idem_key, user_id=user_id)
        if cached is not None:
            _emit_span(success=True, error_code="",
                       cache_hit=True)
            return cached

    # Phase 1 / Step 4 — Tier I capture-inverse runs BEFORE the
    # handler so it sees the previous state. We capture defensively;
    # if the capture itself errors we proceed without a reversal token
    # rather than blocking the action.
    inverse_args: dict[str, Any] | None = None
    if tool.tier == "I" and tool.capture_inverse is not None:
        try:
            inverse_args = tool.capture_inverse(validated_or_err, ctx)
        except Exception:  # noqa: BLE001
            inverse_args = None

    try:
        result = tool.handler(validated_or_err, ctx)
    except Exception as exc:  # noqa: BLE001
        _emit_span(success=False, error_code="handler_exception",
                   cache_hit=False)
        return {
            "ok": False,
            "message": f"Tool '{name}' raised an exception: {exc}",
        }

    if not result.ok:
        err_code = (result.error.code
                    if result.error and result.error.code
                    else "handler_failed")
        _emit_span(success=False, error_code=err_code, cache_hit=False)
        return {
            "ok": False,
            "message": (
                result.error.message
                if result.error
                else f"Tool '{name}' failed."
            ),
        }

    # After a successful Tier I action, persist a reversal token if
    # the tool declared an inverse. The token bubbles up through
    # ``ToolResult.reversal_token`` and the chat layer surfaces it as
    # an undo toast.
    out: dict[str, Any] = {"ok": True, **(result.data or {})}

    # Post-execution capture path: read the handler's result data to
    # build the inverse args (used when the inverse needs an ID the
    # handler assigned). Pre-execution capture beat us to it; we
    # only run post-capture if pre didn't fire.
    if (tool.tier == "I"
            and inverse_args is None
            and tool.capture_inverse_after is not None):
        try:
            inverse_args = tool.capture_inverse_after(
                validated_or_err, ctx, result.data or {},
            )
        except Exception:  # noqa: BLE001
            inverse_args = None

    # Bug C fix — an empty dict from a capture function (e.g.
    # ``capture_inverse_after`` couldn't find an id in the result)
    # would previously pass the ``is not None`` check and record a
    # useless reversal that later undo dispatch can't satisfy.
    # Truthy check skips empty dicts cleanly.
    if (tool.tier == "I"
            and inverse_args
            and tool.inverse_tool
            and store is not None):
        try:
            token = store.record_reversal(
                user_id=user_id,
                tool_name=name,
                tool_call_id=turn_id,
                inverse_tool=tool.inverse_tool,
                inverse_args=inverse_args,
            )
            out["reversalToken"] = token
        except Exception:  # noqa: BLE001
            # Storage failure must not block the user's action;
            # they just won't have undo for this one.
            pass

    # Phase 1 / Step 6 — cache the successful result under the
    # idempotency key so a retry within the TTL returns the same
    # result without re-executing. We only cache successes; failures
    # are not cached so a transient error doesn't poison future
    # retries with the same args.
    if idem_key is not None and store is not None:
        try:
            store.record_idempotent(
                key=idem_key, user_id=user_id,
                tool_name=name, result=out,
            )
        except Exception:  # noqa: BLE001
            pass
    _emit_span(success=True, error_code="", cache_hit=False)
    return out


def _idempotency_key(
    user_id: str, tool_name: str, validated_input: BaseModel,
) -> str:
    """SHA-256 of ``(user_id | tool_name | canonical_args_json)``.

    Canonical = ``model_dump(mode="json")`` + ``sort_keys=True`` so
    JSON field ordering and Python representation differences (e.g.
    ``"123"`` vs ``123`` after Pydantic coercion) don't produce
    different hashes for semantically identical calls.

    SHA-256 is cryptographically unnecessary here (the keys live in
    a server-private SQLite table) but the implementation is in the
    stdlib and produces a stable, short hex string.
    """
    canonical = json.dumps(
        validated_input.model_dump(mode="json"),
        sort_keys=True, separators=(",", ":"), default=str,
    )
    payload = f"{user_id}|{tool_name}|{canonical}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_input(
    tool: Tool, raw: dict[str, Any]
) -> tuple[bool, BaseModel | ToolError]:
    """Validate raw input against the tool's ``input_schema``.

    Returns ``(True, validated_model)`` on success, ``(False,
    ToolError)`` on failure. The error message lists the specific
    Pydantic violations so the LLM can self-correct on the next
    iteration without the orchestrator having to interpret the failure.
    """
    try:
        validated = tool.input_schema.model_validate(raw)
        return True, validated
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        return False, ToolError(
            code="validation_failed",
            message=(
                "Input failed schema validation: "
                f"{details}"
            ),
            retryable=False,
            user_hint=(
                "Re-issue the tool call with the corrected arguments."
            ),
        )
