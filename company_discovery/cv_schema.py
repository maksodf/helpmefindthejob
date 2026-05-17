"""Strict CV data schema (R24.4).

The chat-first vision (R23) demands that AI never invents CV layout
or design — only EXTRACTS user facts into a fixed structure that
hand-designed templates render. This module is that fixed structure.

Why a strict schema
===================

The legacy ``UserProfile.cv_text`` was a free-form blob the LLM
rewrote on every "tailor for job" / "build" call. Result: every
download looked slightly different, hallucinations slipped in, and
aesthetic quality was bound to the LLM's mood. The fix:

  raw user input (CV upload + chat answers)
        |
        | (one-shot LLM extraction, TASK_CV_EXTRACT)
        v
  ┌────────────────────┐
  │ CvDocument         │  <-- THIS MODULE — pure data, no AI
  │  - basics          │
  │  - summary         │
  │  - experience[]    │
  │  - education[]     │
  │  - skills[]        │
  │  - languages[]     │
  │  - certifications[]│
  └────────────────────┘
        |
        | (deterministic render — no AI)
        v
  static/cv_templates/{modern|classic|tech|executive|creative|academic}.html
        |
        v
  Final HTML / PDF download — aesthetics guaranteed.

All AI calls upstream of the schema are bounded by task type;
nothing downstream is allowed to call an LLM. The schema lives in
its own module so the render path can import it without dragging
in any LLM dependency.

Field sizing
============

Every string field is length-capped so a malformed AI extraction
or pasted CV with a 20MB blob can't OOM the renderer.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field


# -------------------- Length caps --------------------

MAX_NAME = 120
MAX_TITLE = 160
MAX_HEADLINE = 220
MAX_SUMMARY = 1200
MAX_LOCATION = 120
MAX_CONTACT_VALUE = 200
MAX_DESCRIPTION = 1400
MAX_BULLET = 400
MAX_BULLETS_PER_ROLE = 8
MAX_EXPERIENCE = 15
MAX_EDUCATION = 8
MAX_CERTIFICATIONS = 12
MAX_SKILLS = 30
MAX_LANGUAGES = 10
MAX_PUBLICATIONS = 30  # academic template only

VALID_TEMPLATES = ("modern", "classic", "tech",
                    "executive", "creative", "academic")

VALID_ACCENT_COLORS = ("indigo", "teal", "slate")


# -------------------- Sanitisation --------------------


def _clean(text: str | None, *, max_len: int) -> str:
    """Single-line cap + strip control chars. Used for every
    user-controlled string before it lands in the schema."""
    if not text:
        return ""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(text))
    s = " ".join(s.split())  # collapse whitespace
    return s[:max_len].strip()


def _clean_block(text: str | None, *, max_len: int) -> str:
    """Multi-line variant that preserves paragraph breaks. Used for
    summary + experience descriptions."""
    if not text:
        return ""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(text))
    # Cap consecutive newlines at 2 (one blank line).
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s[:max_len].strip()


# -------------------- Schema dataclasses --------------------


@dataclass
class CvContact:
    """One contact channel (email / phone / website / LinkedIn).

    ``label`` is what the template shows (e.g. "Email"); ``value`` is
    the text. Renderer escapes both before inserting.
    """
    label: str = ""
    value: str = ""

    def sanitised(self) -> "CvContact":
        return CvContact(
            label=_clean(self.label, max_len=40),
            value=_clean(self.value, max_len=MAX_CONTACT_VALUE),
        )


@dataclass
class CvExperience:
    """One job entry."""
    title: str = ""
    company: str = ""
    location: str = ""
    start: str = ""  # free-form "2020-01" / "Jan 2020" / "since 2020"
    end: str = ""    # free-form "present" / "2024-12"
    description: str = ""  # 1-3 sentences
    bullets: list[str] = field(default_factory=list)

    def sanitised(self) -> "CvExperience":
        return CvExperience(
            title=_clean(self.title, max_len=MAX_TITLE),
            company=_clean(self.company, max_len=MAX_TITLE),
            location=_clean(self.location, max_len=MAX_LOCATION),
            start=_clean(self.start, max_len=40),
            end=_clean(self.end, max_len=40),
            description=_clean_block(self.description, max_len=MAX_DESCRIPTION),
            bullets=[
                _clean(b, max_len=MAX_BULLET)
                for b in (self.bullets or [])[:MAX_BULLETS_PER_ROLE]
                if (b or "").strip()
            ],
        )


@dataclass
class CvEducation:
    """One education entry."""
    degree: str = ""
    institution: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    notes: str = ""

    def sanitised(self) -> "CvEducation":
        return CvEducation(
            degree=_clean(self.degree, max_len=MAX_TITLE),
            institution=_clean(self.institution, max_len=MAX_TITLE),
            location=_clean(self.location, max_len=MAX_LOCATION),
            start=_clean(self.start, max_len=40),
            end=_clean(self.end, max_len=40),
            notes=_clean(self.notes, max_len=MAX_DESCRIPTION),
        )


@dataclass
class CvLanguage:
    """One language proficiency (template renders as "German — C1")."""
    language: str = ""
    level: str = ""

    def sanitised(self) -> "CvLanguage":
        return CvLanguage(
            language=_clean(self.language, max_len=40),
            level=_clean(self.level, max_len=40),
        )


@dataclass
class CvCertification:
    """One certification (template renders as "AWS — 2024")."""
    name: str = ""
    issuer: str = ""
    year: str = ""

    def sanitised(self) -> "CvCertification":
        return CvCertification(
            name=_clean(self.name, max_len=MAX_TITLE),
            issuer=_clean(self.issuer, max_len=MAX_TITLE),
            year=_clean(self.year, max_len=10),
        )


@dataclass
class CvPublication:
    """Academic template only — one publication."""
    title: str = ""
    venue: str = ""
    year: str = ""
    co_authors: str = ""

    def sanitised(self) -> "CvPublication":
        return CvPublication(
            title=_clean(self.title, max_len=MAX_DESCRIPTION),
            venue=_clean(self.venue, max_len=MAX_TITLE),
            year=_clean(self.year, max_len=10),
            co_authors=_clean(self.co_authors, max_len=MAX_DESCRIPTION),
        )


@dataclass
class CvDocument:
    """The full CV. Pass to ``render_cv()`` along with a template id."""

    # ── Basics ────────────────────────────────────────────
    full_name: str = ""
    headline: str = ""     # tagline under the name; user-overridable
    location: str = ""
    photo_data_uri: str = ""  # base64 data:image/...;base64,... or ""

    # ── Customisation ─────────────────────────────────────
    # See R24.6 — moderate flexibility per the product decision.
    template_id: str = "modern"     # one of VALID_TEMPLATES
    accent_color: str = "indigo"    # one of VALID_ACCENT_COLORS
    photo_on: bool = True

    # ── Content sections ──────────────────────────────────
    contacts: list[CvContact] = field(default_factory=list)
    summary: str = ""
    experience: list[CvExperience] = field(default_factory=list)
    education: list[CvEducation] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    languages: list[CvLanguage] = field(default_factory=list)
    certifications: list[CvCertification] = field(default_factory=list)
    publications: list[CvPublication] = field(default_factory=list)

    # ── Free-form notes the user can add ──────────────────
    notes: str = ""

    def sanitised(self) -> "CvDocument":
        """Return a fully-clamped copy safe for the renderer. EVERY
        string is length-capped and stripped of control chars; lists
        are length-capped to their per-section maximums; template /
        accent are validated against the allow-list."""
        tpl = self.template_id if self.template_id in VALID_TEMPLATES else "modern"
        accent = self.accent_color if self.accent_color in VALID_ACCENT_COLORS else "indigo"
        return CvDocument(
            full_name=_clean(self.full_name, max_len=MAX_NAME),
            headline=_clean(self.headline, max_len=MAX_HEADLINE),
            location=_clean(self.location, max_len=MAX_LOCATION),
            photo_data_uri=(self.photo_data_uri or "")[:1024 * 1024],
            template_id=tpl,
            accent_color=accent,
            photo_on=bool(self.photo_on),
            contacts=[c.sanitised() for c in (self.contacts or [])[:8]],
            summary=_clean_block(self.summary, max_len=MAX_SUMMARY),
            experience=[
                e.sanitised() for e in (self.experience or [])[:MAX_EXPERIENCE]
            ],
            education=[
                e.sanitised() for e in (self.education or [])[:MAX_EDUCATION]
            ],
            skills=[
                _clean(s, max_len=80)
                for s in (self.skills or [])[:MAX_SKILLS]
                if (s or "").strip()
            ],
            languages=[
                l.sanitised() for l in (self.languages or [])[:MAX_LANGUAGES]
            ],
            certifications=[
                c.sanitised() for c in (self.certifications or [])[:MAX_CERTIFICATIONS]
            ],
            publications=[
                p.sanitised() for p in (self.publications or [])[:MAX_PUBLICATIONS]
            ],
            notes=_clean_block(self.notes, max_len=MAX_DESCRIPTION),
        )

    # ── Serialisation ─────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to a dict ready for JSON. Note: this does NOT
        sanitise — caller should ``self.sanitised().to_dict()`` for
        renderer input."""
        return asdict(self)

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: dict) -> "CvDocument":
        """Build a CvDocument from a dict (likely from AI extraction
        or persisted state). Missing fields default to empty / safe
        values; unknown extra keys are ignored."""
        if not isinstance(payload, dict):
            return cls()

        def _list(key: str, builder):
            raw = payload.get(key)
            if not isinstance(raw, list):
                return []
            out = []
            for item in raw:
                try:
                    out.append(builder(item))
                except Exception:  # noqa: BLE001
                    continue
            return out

        return cls(
            full_name=str(payload.get("full_name") or ""),
            headline=str(payload.get("headline") or ""),
            location=str(payload.get("location") or ""),
            photo_data_uri=str(payload.get("photo_data_uri") or ""),
            template_id=str(payload.get("template_id") or "modern"),
            accent_color=str(payload.get("accent_color") or "indigo"),
            photo_on=bool(payload.get("photo_on", True)),
            contacts=_list(
                "contacts",
                lambda i: CvContact(
                    label=str((i or {}).get("label") or ""),
                    value=str((i or {}).get("value") or ""),
                ),
            ),
            summary=str(payload.get("summary") or ""),
            experience=_list(
                "experience",
                lambda i: CvExperience(
                    title=str((i or {}).get("title") or ""),
                    company=str((i or {}).get("company") or ""),
                    location=str((i or {}).get("location") or ""),
                    start=str((i or {}).get("start") or ""),
                    end=str((i or {}).get("end") or ""),
                    description=str((i or {}).get("description") or ""),
                    bullets=list((i or {}).get("bullets") or []),
                ),
            ),
            education=_list(
                "education",
                lambda i: CvEducation(
                    degree=str((i or {}).get("degree") or ""),
                    institution=str((i or {}).get("institution") or ""),
                    location=str((i or {}).get("location") or ""),
                    start=str((i or {}).get("start") or ""),
                    end=str((i or {}).get("end") or ""),
                    notes=str((i or {}).get("notes") or ""),
                ),
            ),
            skills=[str(s) for s in (payload.get("skills") or [])
                     if isinstance(s, (str, int, float))],
            languages=_list(
                "languages",
                lambda i: CvLanguage(
                    language=str((i or {}).get("language") or ""),
                    level=str((i or {}).get("level") or ""),
                ),
            ),
            certifications=_list(
                "certifications",
                lambda i: CvCertification(
                    name=str((i or {}).get("name") or ""),
                    issuer=str((i or {}).get("issuer") or ""),
                    year=str((i or {}).get("year") or ""),
                ),
            ),
            publications=_list(
                "publications",
                lambda i: CvPublication(
                    title=str((i or {}).get("title") or ""),
                    venue=str((i or {}).get("venue") or ""),
                    year=str((i or {}).get("year") or ""),
                    co_authors=str((i or {}).get("co_authors") or ""),
                ),
            ),
            notes=str(payload.get("notes") or ""),
        )
