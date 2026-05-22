# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Backend i18n bundle loader (phase2-backlog #75 substrate).

The frontend SPA reads ``static/i18n/<locale>.json`` directly. The
backend (Python) needs the same strings for chat replies + UI
labels rendered server-side (e.g. the widening affordance labels
in ``widening.py`` and the journey bridge messages in
``journey.py``). Before this module these strings were hardcoded
EN regardless of the user's locale; #75 closes the gap.

Design:
- One-time module load: read every ``static/i18n/<code>.json`` file
  into memory at first ``translate()`` call.
- ``translate(key, locale, default)`` — flat dot-namespaced lookup.
  Falls back to EN if the locale doesn't have the key (degrades
  gracefully); falls back to ``default`` if neither locale has it.
- Thread-safe lazy load via a single lock.
- Read-only: this module never writes the bundles. Translations
  are authored by hand in the JSON files; contract tests pin the
  parity invariants.
- No new dependencies — stdlib `json` + `pathlib` only.

Keys for #75 live under the ``backend.`` namespace to keep them
separate from the existing SPA-only keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


# The i18n directory lives under static/. Resolved relative to this
# file so the module is path-independent (tests + production both
# work). Override via env var for test isolation if ever needed.
_DEFAULT_I18N_DIR = Path(__file__).resolve().parent.parent / "static" / "i18n"


_BUNDLES: dict[str, dict[str, Any]] = {}
_BUNDLES_LOAD_LOCK = Lock()
_BUNDLES_LOADED = False


def _normalise_locale(locale: str | None) -> str:
    """Return a normalised locale code. Lowercase, trimmed. Falls
    back to ``"en"`` for unknown / empty / unsupported locales."""

    if not locale:
        return "en"
    norm = locale.strip().lower()
    # Take the language portion of language-region codes (en-US -> en)
    norm = norm.split("-")[0].split("_")[0]
    return norm or "en"


def _load_bundles(directory: Path = _DEFAULT_I18N_DIR) -> None:
    """Load every JSON bundle in the i18n directory into memory.
    Idempotent: subsequent calls are no-ops."""

    global _BUNDLES_LOADED
    if _BUNDLES_LOADED:
        return
    with _BUNDLES_LOAD_LOCK:
        if _BUNDLES_LOADED:
            return
        if not directory.is_dir():
            _BUNDLES_LOADED = True
            return
        for path in directory.glob("*.json"):
            code = path.stem.lower()
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    _BUNDLES[code] = payload
            except (OSError, json.JSONDecodeError):
                # Malformed bundle - skip silently. Frontend has the
                # same defensive behaviour; tests pin valid JSON.
                continue
        _BUNDLES_LOADED = True


def translate(key: str, locale: str | None = None, default: str | None = None) -> str:
    """Resolve a flat dot-namespaced ``key`` against the locale
    bundle. Falls back to EN if the key is missing in the
    requested locale; falls back to ``default`` (or the key
    itself when ``default`` is None) when even EN doesn't carry
    it.

    Never raises. The caller is expected to render the result
    directly — if a backend handler is taking user-supplied data
    that flows into translation lookup, the caller validates the
    locale first."""

    _load_bundles()
    code = _normalise_locale(locale)
    # Lookup in target locale first
    if code in _BUNDLES and key in _BUNDLES[code]:
        value = _BUNDLES[code][key]
        if isinstance(value, str):
            return value
    # Fallback to EN
    if "en" in _BUNDLES and key in _BUNDLES["en"]:
        value = _BUNDLES["en"][key]
        if isinstance(value, str):
            return value
    if default is not None:
        return default
    return key


def available_translation_locales() -> list[str]:
    """List the loaded locale codes (lowercased). Useful for
    contract tests that assert parity across bundles."""

    _load_bundles()
    return sorted(_BUNDLES.keys())


def _reset_for_test() -> None:
    """Test-only: clear the module-level cache so tests can
    isolate from each other. Never called in production."""

    global _BUNDLES_LOADED
    with _BUNDLES_LOAD_LOCK:
        _BUNDLES.clear()
        _BUNDLES_LOADED = False
