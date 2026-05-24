# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Parse an uploaded CV's extracted text into structured sections
(phase2-backlog #3, sectional-parsing portion).

The project already supports PDF / DOCX / TXT extraction
(``cv_extract.py``) which produces a plain-text CV blob. This
module takes that blob and structures it into named sections
(summary / experience / education / skills / languages /
certifications / projects). The sectional view powers:

- The SPA's per-section CV editor (richer than a single textarea)
- Per-section keyword extraction for fit-score / search
- Persona auto-routing (skills + experience inform the suggestion)
- Tailored-CV generation (the AI prompts know which bullets are
  experience vs. skills)

Algorithm — deterministic header detection:

1. Walk the text line-by-line.
2. A line is a "section header" if it matches one of the
   canonical-header patterns (EN + DE, case-insensitive, with
   reasonable variants like "WORK EXPERIENCE" / "Berufserfahrung"
   / "Skills & Tools").
3. Everything between two headers belongs to the first one's
   section.
4. Lines before the first detected header land in a synthetic
   ``preamble`` section (often the name + contact info).
5. Empty / very-short lines are preserved as paragraph breaks.

No AI. No external dependencies. Resilient: unparseable input
returns a single ``preamble`` section with the full text — never
raises.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Canonical section IDs. UI labels live separately (per-locale).
SECTION_PREAMBLE = "preamble"
SECTION_SUMMARY = "summary"
SECTION_EXPERIENCE = "experience"
SECTION_EDUCATION = "education"
SECTION_SKILLS = "skills"
SECTION_LANGUAGES = "languages"
SECTION_CERTIFICATIONS = "certifications"
SECTION_PROJECTS = "projects"
SECTION_OTHER = "other"

ALL_SECTIONS: tuple[str, ...] = (
    SECTION_PREAMBLE,
    SECTION_SUMMARY,
    SECTION_EXPERIENCE,
    SECTION_EDUCATION,
    SECTION_SKILLS,
    SECTION_LANGUAGES,
    SECTION_CERTIFICATIONS,
    SECTION_PROJECTS,
    SECTION_OTHER,
)


# Header pattern catalogues. Each section maps to a tuple of
# regex patterns; ANY match assigns the following content to
# that section. Patterns are case-insensitive, anchored to the
# start of a stripped line, and tolerate trailing colons /
# punctuation that often appear in CV headers.
#
# DE + EN coverage matters because the project's primary
# deployment market is DACH; mixed-language CVs (German
# Berufserfahrung headers + English bullets) are common.

_HEADER_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    SECTION_SUMMARY: (
        re.compile(r"^(?:professional\s+)?summary\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^profile\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^about\s+me\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^objective\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^zusammenfassung\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^kurzprofil\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^über\s+mich\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^profil\s*[:.]?\s*$", re.IGNORECASE),
    ),
    SECTION_EXPERIENCE: (
        re.compile(r"^(?:work\s+)?experience\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^professional\s+experience\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^employment(?:\s+history)?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^work\s+history\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^career\s+history\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^berufserfahrung\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^berufliche?r?\s+werdegang\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^praktische\s+erfahrungen?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^anstellungs?historie\s*[:.]?\s*$", re.IGNORECASE),
    ),
    SECTION_EDUCATION: (
        re.compile(r"^education\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^academic\s+background\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^qualifications?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^ausbildung\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^schulbildung\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^studium\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^bildungsweg\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^akademischer?\s+werdegang\s*[:.]?\s*$", re.IGNORECASE),
    ),
    SECTION_SKILLS: (
        re.compile(r"^skills?(?:\s+(?:&|and)\s+tools)?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^(?:core\s+)?competenc(?:y|ies)\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^technical\s+skills?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^expertise\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^kompetenzen\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^fähigkeiten\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^kenntnisse\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^fertigkeiten\s*[:.]?\s*$", re.IGNORECASE),
    ),
    SECTION_LANGUAGES: (
        re.compile(r"^languages?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^language\s+skills?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^sprachen\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^sprachkenntnisse\s*[:.]?\s*$", re.IGNORECASE),
    ),
    SECTION_CERTIFICATIONS: (
        re.compile(r"^certifications?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^certificates?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^licenses?\s*(?:&|and)?\s*certifications?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^zertifikate?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^zertifizierungen\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^weiterbildungen\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^fortbildungen\s*[:.]?\s*$", re.IGNORECASE),
    ),
    SECTION_PROJECTS: (
        re.compile(r"^projects?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^selected\s+projects?\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^portfolio\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^projekte\s*[:.]?\s*$", re.IGNORECASE),
        re.compile(r"^ausgewählte\s+projekte\s*[:.]?\s*$", re.IGNORECASE),
    ),
}


@dataclass
class ParsedCv:
    """Structured view of a CV's text.

    ``sections`` maps a section ID to the list of non-empty
    paragraph blocks belonging to it (preserving paragraph
    structure so the UI can render bullet lists / dates / etc.
    The UI is responsible for line-wrapping; this layer just
    preserves the original block grouping).

    ``detected_headers`` carries the literal header strings that
    triggered each section — useful for showing the user how
    their CV was understood and letting them correct it.
    """

    sections: dict[str, list[str]] = field(default_factory=dict)
    detected_headers: dict[str, str] = field(default_factory=dict)

    def get(self, section_id: str) -> list[str]:
        return self.sections.get(section_id, [])

    def is_empty(self) -> bool:
        return not any(blocks for blocks in self.sections.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "sections": {sid: list(blocks) for sid, blocks in self.sections.items()},
            "detectedHeaders": dict(self.detected_headers),
        }


def _classify_header(line: str) -> str | None:
    """Match ``line`` against the header catalogue. Returns the
    section_id for a positive match, or None if the line isn't a
    recognised header."""

    stripped = line.strip()
    if not stripped:
        return None
    if len(stripped) > 60:
        # Real headers are short. A 60+-char line is body text.
        return None
    for section_id, patterns in _HEADER_PATTERNS.items():
        for pattern in patterns:
            if pattern.match(stripped):
                return section_id
    return None


def parse_sections(text: str | None) -> ParsedCv:
    """Parse a CV's plain text into structured sections.

    Returns a ParsedCv with non-empty sections only — empty
    sections are omitted so the SPA can iterate without
    rendering empty cards. Lines before the first detected
    header land in ``preamble`` (typically name + contact).

    Empty / None input returns an empty ParsedCv (is_empty()
    returns True).
    """

    if not text or not text.strip():
        return ParsedCv()

    lines = text.splitlines()
    current_section = SECTION_PREAMBLE
    sections: dict[str, list[str]] = {}
    detected_headers: dict[str, str] = {}
    current_block: list[str] = []

    def flush_block() -> None:
        if current_block:
            block_text = "\n".join(current_block).strip()
            if block_text:
                sections.setdefault(current_section, []).append(block_text)
        current_block.clear()

    for raw_line in lines:
        section_id = _classify_header(raw_line)
        if section_id is not None:
            # Flush the in-progress block into the prior section
            flush_block()
            # Move to the new section
            current_section = section_id
            detected_headers[section_id] = raw_line.strip()
            continue
        # Empty line = paragraph break
        if not raw_line.strip():
            flush_block()
            continue
        current_block.append(raw_line)

    # Flush the final block
    flush_block()

    return ParsedCv(sections=sections, detected_headers=detected_headers)
