# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class AIProviderOption:
    id: str
    label: str
    invocation_modes: list[str]
    secret_hint: str
    notes: str


@dataclass
class AIProviderConfig:
    provider_id: str = "manual"
    invocation_mode: str = "manual"
    model: str = ""
    credential_reference: str = ""
    base_url: str = ""
    command: str = ""
    notes: str = ""

    def public_dict(self) -> dict[str, str]:
        return asdict(self)


PROVIDER_OPTIONS: list[AIProviderOption] = [
    AIProviderOption(
        id="manual",
        label="Manual / no AI",
        invocation_modes=["manual"],
        secret_hint="No credential needed.",
        notes="Keeps analysis disabled until the user chooses an AI provider.",
    ),
    AIProviderOption(
        id="openai",
        label="OpenAI / ChatGPT",
        invocation_modes=["api"],
        secret_hint="Reference an environment variable such as OPENAI_API_KEY.",
        notes="Use with the user's own OpenAI API key or compatible ChatGPT plan integration.",
    ),
    AIProviderOption(
        id="anthropic",
        label="Anthropic / Claude",
        invocation_modes=["api", "cli"],
        secret_hint="Reference an environment variable or Claude Code local command.",
        notes="Supports future Claude API or Claude Code style local execution.",
    ),
    AIProviderOption(
        id="google_gemini",
        label="Google Gemini",
        invocation_modes=["api"],
        secret_hint="Reference an environment variable such as GEMINI_API_KEY.",
        notes="Use with the user's own Google AI Studio or Vertex subscription.",
    ),
    AIProviderOption(
        id="deepseek",
        label="DeepSeek",
        invocation_modes=["api"],
        secret_hint="Reference an environment variable such as DEEPSEEK_API_KEY.",
        notes="Use with the user's own DeepSeek-compatible API subscription.",
    ),
    AIProviderOption(
        id="openrouter",
        label="OpenRouter / compatible gateway",
        invocation_modes=["api"],
        secret_hint="Reference an environment variable such as OPENROUTER_API_KEY.",
        notes="Lets the user bring access to many compatible hosted models.",
    ),
    AIProviderOption(
        id="ollama",
        label="Ollama / local model",
        invocation_modes=["local_http"],
        secret_hint="No cloud key required for default local use.",
        notes="Use a local model endpoint such as http://127.0.0.1:11434.",
    ),
    AIProviderOption(
        id="codex_cli",
        label="Codex CLI",
        invocation_modes=["cli"],
        secret_hint="Uses the user's local Codex authentication.",
        notes="Future adapter can call the user's authenticated local Codex CLI.",
    ),
    AIProviderOption(
        id="claude_code",
        label="Claude Code",
        invocation_modes=["cli"],
        secret_hint="Uses the user's local Claude Code authentication.",
        notes="Future adapter can call the user's authenticated local Claude Code setup.",
    ),
    AIProviderOption(
        id="custom",
        label="Custom provider",
        invocation_modes=["api", "cli", "local_http"],
        secret_hint="Reference a user-controlled env var or local command.",
        notes="Escape hatch for future or organization-specific AI providers.",
    ),
    AIProviderOption(
        id="managed",
        label="Managed AI (operator-provided)",
        invocation_modes=["api"],
        secret_hint="No credential needed — uses the operator's server-side key.",
        notes=(
            "Server-side dispatch via the operator's DIRECTJOB_MANAGED_AI_KEY. "
            "Plan-gated (Pro+ only). Operator chooses the upstream provider via "
            "DIRECTJOB_MANAGED_AI_PROVIDER (openai / anthropic / google_gemini / etc)."
        ),
    ),
]


def provider_options_payload() -> list[dict[str, object]]:
    return [asdict(option) for option in PROVIDER_OPTIONS]


def validate_provider_config(config: AIProviderConfig) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    provider = next(
        (option for option in PROVIDER_OPTIONS if option.id == config.provider_id), None
    )
    if provider is None:
        errors.append({"code": "unknown_provider", "field": "provider_id"})
        return errors
    if config.invocation_mode not in provider.invocation_modes:
        errors.append({"code": "unsupported_invocation_mode", "field": "invocation_mode"})
    if config.credential_reference and any(
        secret in config.credential_reference.casefold() for secret in ("sk-", "key=", "token=")
    ):
        errors.append({"code": "raw_secret_not_allowed", "field": "credential_reference"})
    return errors
