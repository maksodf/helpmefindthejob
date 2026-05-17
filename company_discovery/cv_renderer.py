"""Deterministic CV renderer (R24.6 + R24.7).

Takes a sanitised ``CvDocument`` and returns full HTML for one of
six hand-designed templates. **No LLM calls** anywhere in this
module — the AI's only job is upstream extraction into ``CvDocument``.

Six templates
=============

  modern    — clean two-column with accent header; default for most users
  classic   — traditional one-column ATS-friendly layout
  tech      — sidebar with skills/pills + main content on the right
  executive — serif typography, conservative spacing, no sidebar
  creative  — wide accent header, larger name, looser whitespace
  academic  — publications + teaching prominent, narrow margins

Three accent colors per template (indigo / teal / slate) controlled
by ``cv_base.css`` CSS variables. Photo on/off via the data
attribute on the root element.

Security
========

Every user-controlled string is HTML-escaped via ``html.escape``
before insertion. URLs are NOT auto-linked here — we never embed
``<a href="...">`` from user input because a malicious extracted
"website" could carry ``javascript:``. The renderer treats all
strings as text.

Photo data URIs are validated at the schema level (capped at
~1MB). If the user supplies something other than ``data:image/...``
the renderer drops the photo block.
"""

from __future__ import annotations

import html
import re

from company_discovery.cv_schema import (
    CvCertification, CvContact, CvDocument, CvEducation,
    CvExperience, CvLanguage, CvPublication, VALID_ACCENT_COLORS,
    VALID_TEMPLATES,
)


# CSS path is served by the existing static file route.
_CSS_HREF = "/static/cv_templates/cv_base.css"

# Photo guard — only ``data:image/(png|jpeg|webp|gif);base64,`` is
# allowed. Everything else is dropped so a crafted ``photo_data_uri``
# can't carry ``javascript:`` or ``data:text/html``.
_PHOTO_RE = re.compile(
    r"^data:image/(?:png|jpeg|jpg|webp|gif);base64,[A-Za-z0-9+/=]+$",
    re.IGNORECASE,
)


def _h(text: str | None) -> str:
    """HTML-escape (quotes too). Used for every user-controlled
    string before it lands in the rendered HTML."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)


def _safe_photo(uri: str) -> str:
    if not uri or not _PHOTO_RE.match(uri):
        return ""
    return uri


# ---------------- Shared section builders ----------------


def _render_header(doc: CvDocument) -> str:
    photo = _safe_photo(doc.photo_data_uri) if doc.photo_on else ""
    photo_html = (
        f'<img class="cv-photo" alt="" src="{_h(photo)}" />'
        if photo else ""
    )
    contacts_html = ""
    if doc.contacts:
        items = "".join(
            f'<span><span class="cv-contact-label">{_h(c.label)}:</span>'
            f' {_h(c.value)}</span>'
            for c in doc.contacts if c.value
        )
        contacts_html = f'<div class="cv-contacts">{items}</div>'
    location_html = (
        f'<p class="cv-meta-line">{_h(doc.location)}</p>'
        if doc.location else ""
    )
    headline_html = (
        f'<p class="cv-headline">{_h(doc.headline)}</p>'
        if doc.headline else ""
    )
    return (
        '<header class="cv-header">'
        f'  <div class="cv-header-text">'
        f'    <h1 class="cv-name">{_h(doc.full_name)}</h1>'
        f'    {headline_html}'
        f'    {location_html}'
        f'    {contacts_html}'
        f'  </div>'
        f'  {photo_html}'
        '</header>'
    )


def _render_summary(doc: CvDocument) -> str:
    if not doc.summary:
        return ""
    return (
        '<section class="cv-section cv-section-summary">'
        '  <h2 class="cv-section-title">Summary</h2>'
        f'  <p class="cv-summary">{_h(doc.summary)}</p>'
        '</section>'
    )


def _render_experience(doc: CvDocument, *, title: str = "Experience") -> str:
    if not doc.experience:
        return ""
    rows = []
    for e in doc.experience:
        bullets = ""
        if e.bullets:
            bullets = (
                '<ul class="cv-entry-bullets">'
                + "".join(f"<li>{_h(b)}</li>" for b in e.bullets)
                + "</ul>"
            )
        desc = f'<p class="cv-entry-description">{_h(e.description)}</p>' if e.description else ""
        meta = " – ".join(x for x in (e.start, e.end) if x) or ""
        rows.append(
            '<article class="cv-entry">'
            f'  <div class="cv-entry-head">'
            f'    <span class="cv-entry-title">{_h(e.title)}</span>'
            f'    <span class="cv-entry-meta">{_h(meta)}</span>'
            f'  </div>'
            f'  <p class="cv-entry-company">{_h(e.company)}{(" · " + _h(e.location)) if e.location else ""}</p>'
            f'  {desc}'
            f'  {bullets}'
            '</article>'
        )
    return (
        f'<section class="cv-section cv-section-experience">'
        f'  <h2 class="cv-section-title">{_h(title)}</h2>'
        + "".join(rows)
        + '</section>'
    )


def _render_education(doc: CvDocument) -> str:
    if not doc.education:
        return ""
    rows = []
    for e in doc.education:
        meta = " – ".join(x for x in (e.start, e.end) if x) or ""
        notes = f'<p class="cv-entry-description">{_h(e.notes)}</p>' if e.notes else ""
        rows.append(
            '<article class="cv-entry">'
            f'  <div class="cv-entry-head">'
            f'    <span class="cv-entry-title">{_h(e.degree)}</span>'
            f'    <span class="cv-entry-meta">{_h(meta)}</span>'
            f'  </div>'
            f'  <p class="cv-entry-company">{_h(e.institution)}{(" · " + _h(e.location)) if e.location else ""}</p>'
            f'  {notes}'
            '</article>'
        )
    return (
        '<section class="cv-section cv-section-education">'
        '  <h2 class="cv-section-title">Education</h2>'
        + "".join(rows)
        + '</section>'
    )


def _render_skills(doc: CvDocument, *, as_pills: bool = True) -> str:
    if not doc.skills:
        return ""
    if as_pills:
        items = "".join(
            f'<li class="cv-pill">{_h(s)}</li>' for s in doc.skills
        )
        body = f'<ul class="cv-pills">{items}</ul>'
    else:
        items = " · ".join(_h(s) for s in doc.skills)
        body = f'<p>{items}</p>'
    return (
        '<section class="cv-section cv-section-skills">'
        '  <h2 class="cv-section-title">Skills</h2>'
        f'  {body}'
        '</section>'
    )


def _render_languages(doc: CvDocument) -> str:
    if not doc.languages:
        return ""
    rows = "".join(
        '<div class="cv-kv-row">'
        f'  <span class="cv-kv-key">{_h(l.language)}</span>'
        f'  <span class="cv-kv-value">{_h(l.level)}</span>'
        '</div>'
        for l in doc.languages if l.language
    )
    return (
        '<section class="cv-section cv-section-languages">'
        '  <h2 class="cv-section-title">Languages</h2>'
        f'  {rows}'
        '</section>'
    )


def _render_certifications(doc: CvDocument) -> str:
    if not doc.certifications:
        return ""
    rows = "".join(
        '<div class="cv-kv-row">'
        f'  <span class="cv-kv-key">{_h(c.name)}{(" — " + _h(c.issuer)) if c.issuer else ""}</span>'
        f'  <span class="cv-kv-value">{_h(c.year)}</span>'
        '</div>'
        for c in doc.certifications if c.name
    )
    return (
        '<section class="cv-section cv-section-certifications">'
        '  <h2 class="cv-section-title">Certifications</h2>'
        f'  {rows}'
        '</section>'
    )


def _render_publications(doc: CvDocument) -> str:
    if not doc.publications:
        return ""
    rows = []
    for p in doc.publications:
        venue = f' — <em>{_h(p.venue)}</em>' if p.venue else ""
        year = f' ({_h(p.year)})' if p.year else ""
        authors = f'<br><span class="cv-entry-meta">{_h(p.co_authors)}</span>' if p.co_authors else ""
        rows.append(
            f'<p class="cv-publication">{_h(p.title)}{venue}{year}{authors}</p>'
        )
    return (
        '<section class="cv-section cv-section-publications">'
        '  <h2 class="cv-section-title">Publications</h2>'
        + "".join(rows)
        + '</section>'
    )


# ---------------- Per-template body builders ----------------


def _body_modern(doc: CvDocument) -> str:
    return (
        _render_header(doc)
        + _render_summary(doc)
        + _render_experience(doc)
        + _render_education(doc)
        + _render_skills(doc)
        + _render_languages(doc)
        + _render_certifications(doc)
    )


def _body_classic(doc: CvDocument) -> str:
    # Single-column, more conservative spacing, skills inline.
    return (
        _render_header(doc)
        + _render_summary(doc)
        + _render_experience(doc)
        + _render_education(doc)
        + _render_skills(doc, as_pills=False)
        + _render_languages(doc)
        + _render_certifications(doc)
    )


def _body_tech(doc: CvDocument) -> str:
    # Sidebar with skills + languages + certs on the right.
    main = (
        _render_summary(doc)
        + _render_experience(doc)
        + _render_education(doc)
    )
    side = (
        _render_skills(doc)
        + _render_languages(doc)
        + _render_certifications(doc)
    )
    return (
        _render_header(doc)
        + '<div class="cv-twocol">'
        f'  <div class="cv-twocol-main">{main}</div>'
        f'  <aside class="cv-twocol-side">{side}</aside>'
        '</div>'
    )


def _body_executive(doc: CvDocument) -> str:
    return (
        _render_header(doc)
        + _render_summary(doc)
        + _render_experience(doc, title="Career history")
        + _render_education(doc)
        + _render_certifications(doc)
        + _render_languages(doc)
        + _render_skills(doc, as_pills=False)
    )


def _body_creative(doc: CvDocument) -> str:
    # Larger header, summary right after, then experience.
    return (
        _render_header(doc)
        + _render_summary(doc)
        + _render_skills(doc)
        + _render_experience(doc)
        + _render_education(doc)
        + _render_languages(doc)
        + _render_certifications(doc)
    )


def _body_academic(doc: CvDocument) -> str:
    return (
        _render_header(doc)
        + _render_summary(doc)
        + _render_education(doc)
        + _render_experience(doc, title="Research & teaching")
        + _render_publications(doc)
        + _render_certifications(doc)
        + _render_languages(doc)
        + _render_skills(doc, as_pills=False)
    )


_BODY_BUILDERS = {
    "modern": _body_modern,
    "classic": _body_classic,
    "tech": _body_tech,
    "executive": _body_executive,
    "creative": _body_creative,
    "academic": _body_academic,
}


# ---------------- Per-template style overrides ----------------

# Each template gets a small inline style block in addition to
# cv_base.css. Keeps the bundle to one shared CSS + ~50 lines of
# template-specific tweaks each. Inline so a single GET pulls the
# full document for printing.

_TEMPLATE_STYLES: dict[str, str] = {
    "modern": "",  # base styles already cover it
    "classic": """
      .cv-doc[data-template="classic"] { font-family: Georgia, "Times New Roman", serif; }
      .cv-doc[data-template="classic"] .cv-section-title { text-transform: none; letter-spacing: 0; font-size: 14pt; }
      .cv-doc[data-template="classic"] .cv-header { border-bottom-width: 1pt; }
    """,
    "tech": """
      .cv-doc[data-template="tech"] .cv-twocol {
        display: grid;
        grid-template-columns: 1fr 65mm;
        gap: 14pt;
      }
      .cv-doc[data-template="tech"] .cv-twocol-side .cv-section-title { font-size: 11pt; }
      .cv-doc[data-template="tech"] .cv-twocol-side { font-size: 10pt; }
    """,
    "executive": """
      .cv-doc[data-template="executive"] {
        font-family: "Cambria", Georgia, "Times New Roman", serif;
      }
      .cv-doc[data-template="executive"] .cv-name { letter-spacing: 0.02em; }
      .cv-doc[data-template="executive"] .cv-section-title {
        font-weight: 700;
        letter-spacing: 0.12em;
        color: var(--cv-color-text);
        border-bottom-color: var(--cv-accent);
        border-bottom-width: 2pt;
      }
      .cv-doc[data-template="executive"] .cv-pill {
        background: transparent;
        border: 1pt solid var(--cv-accent);
      }
    """,
    "creative": """
      .cv-doc[data-template="creative"] .cv-header {
        background: var(--cv-accent-soft);
        margin: calc(-1 * var(--cv-margin)) calc(-1 * var(--cv-margin)) 10pt;
        padding: 18pt var(--cv-margin) 14pt;
        border-bottom: none;
      }
      .cv-doc[data-template="creative"] .cv-name { font-size: 32pt; }
      .cv-doc[data-template="creative"] .cv-section-title {
        font-size: 11.5pt;
        border-bottom: none;
        padding-left: 8pt;
        border-left: 3pt solid var(--cv-accent);
      }
    """,
    "academic": """
      .cv-doc[data-template="academic"] { font-family: "Charter", "Georgia", serif; }
      .cv-doc[data-template="academic"] { padding: 14mm; }
      .cv-doc[data-template="academic"] .cv-section-title {
        font-size: 12pt;
        text-transform: none;
        font-weight: 700;
        border-bottom: none;
      }
      .cv-doc[data-template="academic"] .cv-publication {
        margin: 0 0 6pt;
        text-indent: -12pt;
        padding-left: 12pt;
      }
    """,
}


def _template_style_block(template_id: str) -> str:
    css = _TEMPLATE_STYLES.get(template_id, "").strip()
    return f"<style>{css}</style>" if css else ""


# ---------------- Public render API ----------------


def sample_cv_document(*, template_id: str = "modern",
                         accent_color: str = "indigo",
                         photo_on: bool = True) -> CvDocument:
    """A believable DACH sample CV used by the template-picker
    thumbnails (R29). Filling each template with the SAME sample
    data makes the visual comparison fair — the user picks based
    on layout, not content variance.

    Returned doc is NOT sanitised — caller passes through
    ``render_cv()`` which sanitises internally.
    """
    from company_discovery.cv_schema import (
        CvCertification, CvContact, CvEducation, CvExperience,
        CvLanguage, CvPublication,
    )
    return CvDocument(
        full_name="Maria Schmidt",
        headline="Pflegehelferin · 6 years at Charité Berlin",
        location="Berlin, Germany",
        photo_data_uri="",
        template_id=template_id,
        accent_color=accent_color,
        photo_on=photo_on,
        contacts=[
            CvContact(label="Email", value="maria.schmidt@example.com"),
            CvContact(label="Phone", value="+49 30 1234567"),
        ],
        summary=(
            "Hands-on care professional with six years across two "
            "Berlin clinics. Strong on documentation, first response, "
            "and handover coordination."),
        experience=[
            CvExperience(
                title="Pflegehelferin",
                company="Charité Berlin",
                location="Berlin",
                start="2020", end="present",
                description="12 residents per shift across the geriatric ward.",
                bullets=[
                    "Coordinated handovers with night-shift team",
                    "Reduced medication-cycle errors by 18%",
                    "Trained 3 new colleagues on documentation",
                ],
            ),
            CvExperience(
                title="Krankenpflegehilfe (Praktikum)",
                company="Vivantes Klinikum",
                location="Berlin",
                start="2018", end="2020",
                description="Internship rotations across surgery and geriatrics.",
                bullets=[
                    "Patient transfers and post-op care",
                    "Documented vitals into Orbis EHR",
                ],
            ),
        ],
        education=[
            CvEducation(
                degree="Ausbildung Krankenpflegehilfe",
                institution="Vivantes Berufsfachschule",
                location="Berlin",
                start="2018", end="2020",
            ),
        ],
        skills=[
            "First aid (DRK)", "Documentation (Orbis)",
            "Wound care", "Patient handover",
            "German (C1)", "English (B2)",
        ],
        languages=[
            CvLanguage(language="German", level="C1"),
            CvLanguage(language="English", level="B2"),
            CvLanguage(language="Arabic", level="Native"),
        ],
        certifications=[
            CvCertification(name="First aid", issuer="DRK", year="2024"),
        ],
        publications=(
            [CvPublication(
                title="A retrospective on shift handovers",
                venue="Pflegezeitschrift",
                year="2024",
                co_authors="A. Hoffmann, R. Bauer")]
            if template_id == "academic" else []
        ),
        notes="",
    )


def render_cv(doc: CvDocument, *,
                auto_print: bool = False,
                css_inline: str | None = None,
                thumb: bool = False) -> str:
    """Render a ``CvDocument`` to a complete HTML page.

    ``auto_print`` adds a small inline script that calls
    ``window.print()`` after the page loads — used by the
    ``/api/cv/print?autoprint=1`` flow so the browser's Save-as-PDF
    dialog pops up automatically.

    ``css_inline`` lets the caller inline the base CSS instead of
    linking to ``/static/cv_templates/cv_base.css`` — useful for
    standalone HTML downloads.

    ``thumb=True`` (R29) drops the page background, sheet margin and
    box-shadow so the rendered CV fills the iframe edge-to-edge for
    the template-picker thumbnails.
    """
    sanitised = doc.sanitised()
    template_id = sanitised.template_id
    if template_id not in VALID_TEMPLATES:
        template_id = "modern"
    accent = sanitised.accent_color
    if accent not in VALID_ACCENT_COLORS:
        accent = "indigo"

    body_html = _BODY_BUILDERS[template_id](sanitised)
    style_block = _template_style_block(template_id)
    photo_attr = "false" if sanitised.photo_on else "true"

    if css_inline is not None:
        css_block = f"<style>{css_inline}</style>"
    else:
        css_block = f'<link rel="stylesheet" href="{_CSS_HREF}">'

    autoprint_script = ""
    if auto_print:
        autoprint_script = (
            '<script>window.addEventListener("load",'
            ' function(){setTimeout(function(){window.print();}, 200);});</script>'
        )

    thumb_style = ""
    if thumb:
        thumb_style = (
            "<style>"
            "html,body{background:#fff;margin:0;padding:0;}"
            ".cv-doc{margin:0;box-shadow:none;width:210mm;min-height:297mm;}"
            "</style>"
        )

    title = sanitised.full_name or "CV"
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_h(title)} — CV</title>'
        f'{css_block}'
        f'{style_block}'
        f'{thumb_style}'
        '</head><body>'
        f'<div class="cv-doc" data-template="{template_id}"'
        f' data-accent="{accent}" data-photo-off="{photo_attr}">'
        f'{body_html}'
        '</div>'
        f'{autoprint_script}'
        '</body></html>'
    )
