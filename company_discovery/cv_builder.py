"""Deterministic CV builder — conversation-driven, hallucination-resistant.

The user wants a "build my CV through chat" feature. Naïve chat-with-AI
hallucinates: the model invents skills, embellishes experience, and
agrees with leading questions the user didn't really answer. Result: a
CV the user can't defend in an interview.

This module instead implements a **deterministic conversation**:

  1. **Server controls the state machine**. The conversation walks a
     fixed sequence of sections (header → summary → experience →
     education → skills → certifications → projects). The AI does NOT
     decide what to ask next; the server does.

  2. **AI is bounded to two narrow operations**:
       - ``format_section(user_text, section_type)`` — reformat the
         user's raw words into CV-ready prose with action verbs and
         parallel structure. STRICTLY transformational; no new facts.
       - ``next_clarification(section_type, partial_state)`` — choose
         the next predefined follow-up question from the section's
         schema. The schema is a list of question strings — the AI
         picks the index, it doesn't generate the question.

  3. **Fact-grounding gate**. Every AI-formatted output passes a
     fact-ratio check: % of meaningful tokens in the output that
     appear (or are reasonable transformations of) tokens in the
     user's input. Outputs below 0.6 are rejected and the user is
     shown the raw input instead — better honest than confident-wrong.

  4. **User approves each section before persist**. The user always
     sees BOTH their raw input and the AI-formatted version, and can
     edit either.

State storage: per-user CV-builder sessions live in memory + persist
to the user's `profile.cv_builder_state` JSON column. Closing the
browser is safe — reopen and resume."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable


# ---------------- Fact-grounding ----------------

# Words too generic to contribute to fact-grounding. The user might say
# "i worked at acme" and the AI emits "worked as engineer at acme"; we
# shouldn't reward the AI for keeping common verbs like "worked".
_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "can", "could", "may", "might", "must", "i",
    "you", "we", "they", "he", "she", "it", "my", "your", "our", "their",
    "this", "that", "these", "those", "there", "here",
    # Action-verb pairs we treat as equivalent (work↔develop, lead↔manage)
    "worked", "develop", "developed", "build", "built", "create", "created",
    "led", "lead", "manage", "managed", "shipped", "delivered",
})


def _tokenise(text: str) -> set[str]:
    """Casefolded, diacritic-stripped, stopword-removed token set."""
    if not text:
        return set()
    # Decompose + strip combining marks so 'München' tokens as 'munchen'.
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", stripped)
    return {t for t in tokens if t and t not in _STOPWORDS and len(t) > 1}


def compute_fact_ratio(user_input: str, ai_output: str) -> float:
    """Return the fraction of meaningful tokens in ``ai_output`` that
    also appear in ``user_input``. Range: 0.0 (full hallucination) to
    1.0 (every output token traces to input).

    Strategy:
      - Casefold + diacritic-fold both sides.
      - Drop stopwords + common action-verb pairs (work/develop etc.)
        so we measure NOUN-PHRASE preservation rather than penalising
        the AI for swapping "worked" → "developed".
      - Tokens of length 1 are dropped (commas, single letters).
      - Return ``len(input ∩ output) / max(1, len(output))``.

    A ratio of 0.6 is the recommended accept threshold; below that
    we reject the AI's formatting and surface the raw user text."""

    input_tokens = _tokenise(user_input)
    output_tokens = _tokenise(ai_output)
    if not output_tokens:
        return 1.0  # nothing to ground
    grounded = input_tokens & output_tokens
    return len(grounded) / len(output_tokens)


# ---------------- Score / recommendation consistency ----------------


def score_recommendation_inconsistent(
    fit_score: float | None,
    recommendation: str | None,
) -> bool:
    """True iff the score and recommendation contradict each other.
    Used by the dashboard to surface a "model gave inconsistent signal"
    warning."""
    if fit_score is None or recommendation is None:
        return False
    rec = recommendation.casefold().strip()
    if rec == "apply" and fit_score < 0.55:
        return True
    if rec == "skip" and fit_score > 0.65:
        return True
    # "consider" is the middle band — both extremes count as inconsistent.
    if rec == "consider" and (fit_score < 0.25 or fit_score > 0.85):
        return True
    return False


# ---------------- CV builder state machine ----------------


@dataclass
class SectionQuestion:
    """One question in a section's elicitation schema."""
    key: str           # field key, e.g. "company_name"
    prompt: str        # what the UI shows the user
    required: bool = True
    hint: str | None = None


@dataclass
class CvSection:
    """A section of the CV with its elicitation schema."""
    section_id: str
    label: str
    questions: list[SectionQuestion]
    # True when this section can repeat (experience, education).
    repeatable: bool = False


# Fixed section sequence. The server walks this in order.
SECTIONS: list[CvSection] = [
    CvSection(
        section_id="header",
        label="Personal header",
        questions=[
            SectionQuestion("full_name", "What's your full name?"),
            SectionQuestion("email", "What's your contact email?"),
            SectionQuestion("phone", "Phone number (optional)?", required=False),
            SectionQuestion("location", "What city / region are you in?"),
            SectionQuestion("linkedin", "LinkedIn URL (optional)?",
                             required=False),
            SectionQuestion("portfolio",
                             "Personal website / GitHub / portfolio (optional)?",
                             required=False),
        ],
    ),
    CvSection(
        section_id="summary",
        label="Professional summary",
        questions=[
            SectionQuestion(
                "summary_raw",
                "In 3–4 sentences, what's your professional headline? "
                "What do you do, how long have you done it, what are you "
                "best known for?",
                hint="Write it casually — we'll polish the wording later. "
                "We will NOT add anything you don't say here.",
            ),
        ],
    ),
    CvSection(
        section_id="experience",
        label="Work experience",
        repeatable=True,
        questions=[
            SectionQuestion("company_name", "Company name?"),
            SectionQuestion("job_title", "Your job title there?"),
            SectionQuestion("start_date", "Start date (MM/YYYY)?"),
            SectionQuestion("end_date",
                             "End date (MM/YYYY) or 'present'?"),
            SectionQuestion("location",
                             "Location (city) or 'remote'?"),
            SectionQuestion(
                "achievements_raw",
                "What were your 3–5 main responsibilities or achievements? "
                "Write them as bullet points — we'll polish wording later. "
                "Be specific about scope (team size, budget, %, $) where you can.",
                hint="If you don't have a number, just say so — better an "
                "honest claim than an invented metric.",
            ),
        ],
    ),
    CvSection(
        section_id="education",
        label="Education",
        repeatable=True,
        questions=[
            SectionQuestion("school", "School / university name?"),
            SectionQuestion("degree", "Degree (e.g., BSc, MSc, MBA)?"),
            SectionQuestion("field", "Field of study?"),
            SectionQuestion("start_date", "Start year?"),
            SectionQuestion("end_date",
                             "End year (or expected graduation)?"),
            SectionQuestion("honors",
                             "Honours / GPA / distinction (optional)?",
                             required=False),
        ],
    ),
    CvSection(
        section_id="skills",
        label="Skills",
        questions=[
            SectionQuestion(
                "skills_raw",
                "List your technical skills, tools, and languages — "
                "comma-separated. We'll group them into categories.",
                hint="Only list skills you'd feel confident answering "
                "questions about in an interview.",
            ),
        ],
    ),
    CvSection(
        section_id="certifications",
        label="Certifications (optional)",
        repeatable=True,
        questions=[
            SectionQuestion("cert_name", "Certification name?"),
            SectionQuestion("cert_issuer", "Issuing body?"),
            SectionQuestion("cert_year", "Year obtained?"),
        ],
    ),
    CvSection(
        section_id="projects",
        label="Projects (optional)",
        repeatable=True,
        questions=[
            SectionQuestion("project_name", "Project name?"),
            SectionQuestion(
                "project_description",
                "1–2 sentence description — what does it do, what was "
                "your role, what tech did you use?",
            ),
            SectionQuestion("project_url",
                             "Link (GitHub / live URL, optional)?",
                             required=False),
        ],
    ),
]

SECTIONS_BY_ID: dict[str, CvSection] = {s.section_id: s for s in SECTIONS}


def get_section(section_id: str) -> CvSection:
    if section_id not in SECTIONS_BY_ID:
        raise KeyError(f"Unknown CV section: {section_id}")
    return SECTIONS_BY_ID[section_id]


def next_section_id(current_section_id: str | None) -> str | None:
    """Return the id of the next section to walk, or None at end."""
    if current_section_id is None:
        return SECTIONS[0].section_id
    ids = [s.section_id for s in SECTIONS]
    if current_section_id not in ids:
        return SECTIONS[0].section_id
    i = ids.index(current_section_id)
    if i + 1 >= len(ids):
        return None
    return ids[i + 1]


# ---------------- AI-format prompts ----------------


def build_format_prompt(section_type: str, raw_text: str) -> str:
    """Build a strictly-bounded prompt the AI uses to reformat raw user
    input into CV-ready prose. The prompt:

      1. Names the section context (so the AI uses appropriate tone).
      2. Includes the raw user text verbatim.
      3. Forbids invention in the strongest possible terms.
      4. Asks for parallel structure / action verbs / past tense.

    Returns a prompt string the caller hands to ``_dispatch_provider``."""

    section_intent = {
        "summary": (
            "Reformat the user's notes into a 3–4 sentence professional "
            "summary. Use first-person voice. Past tense for past roles, "
            "present tense for current role."
        ),
        "experience": (
            "Reformat the user's bullet points into 3–5 CV-style achievement "
            "bullets, each starting with a strong action verb. Preserve "
            "every NUMBER and metric the user wrote verbatim. Use past "
            "tense unless the user said 'currently'."
        ),
        "skills": (
            "Group the user's comma-separated skills into 2–4 logical "
            "categories (e.g., 'Languages', 'Cloud & Infra', 'Data'). "
            "Output ONLY the user's listed skills — do not add any."
        ),
    }.get(section_type, "Reformat the user's notes into CV-style prose.")

    return (
        "You are a CV formatter, NOT a CV writer. You take the user's raw "
        "notes and reformat them into clean CV prose.\n\n"
        "STRICT RULES:\n"
        "1. Do NOT add facts the user did not write. No invented metrics, "
        "no embellished scope, no skills the user did not name.\n"
        "2. Do NOT remove facts the user wrote. Every NUMBER, NAME, and "
        "NOUN-PHRASE must appear in your output.\n"
        "3. You MAY swap weak verbs for stronger action verbs (worked → "
        "developed, did → delivered) AS LONG AS the meaning is preserved.\n"
        "4. You MAY fix grammar, capitalisation, and punctuation.\n"
        "5. If the user's notes are too vague to format, OUTPUT them "
        "verbatim and do not invent specifics.\n\n"
        f"SECTION TASK:\n{section_intent}\n\n"
        f"USER NOTES (verbatim — do not invent beyond these):\n{raw_text}\n\n"
        "OUTPUT (formatted prose only — no commentary):"
    )


# ---------------- Assembly ----------------


@dataclass
class CvBuilderState:
    """Per-user CV-builder session state.

    The state is a sequence of section payloads. Each payload has the
    raw user answers and the (optional) AI-formatted text. A section
    is "approved" only after the user explicitly accepts (or edits) it.
    """
    current_section_id: str | None = None
    # section_id → list of payload dicts. For repeatable sections, the
    # list has one entry per instance (job, school, etc.).
    sections: dict[str, list[dict]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "currentSectionId": self.current_section_id,
            "sections": {k: list(v) for k, v in self.sections.items()},
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "CvBuilderState":
        if not isinstance(data, dict):
            return cls()
        raw_sections = data.get("sections")
        sections: dict[str, list[dict]] = {}
        if isinstance(raw_sections, dict):
            for k, v in raw_sections.items():
                if isinstance(v, list):
                    sections[k] = list(v)
        current = data.get("currentSectionId")
        if not isinstance(current, str):
            current = None
        return cls(current_section_id=current, sections=sections)


def assemble_cv_markdown(
    state: CvBuilderState,
    photo_data_uri: str | None = None,
) -> str:
    """Walk the state and emit a Markdown CV. Used when the user
    finishes the builder. The output overwrites profile.cv_text.

    ``photo_data_uri`` (DACH-CV norm) is embedded at the very top
    when provided — uses standard Markdown image syntax with the
    data URI, so the CV is self-contained and exports cleanly.
    """

    parts: list[str] = []
    if photo_data_uri and photo_data_uri.startswith("data:image/"):
        # Sized cap via HTML so PDF renderers honour it.
        parts.append(
            f'<img src="{photo_data_uri}" alt="Profile photo" '
            'style="max-width:120px;border-radius:8px;" />\n'
        )
    header = (state.sections.get("header") or [{}])[0]
    name = (header.get("full_name") or "").strip()
    if name:
        parts.append(f"# {name}")
    contact_bits = []
    if header.get("email"):
        contact_bits.append(header["email"])
    if header.get("phone"):
        contact_bits.append(header["phone"])
    if header.get("location"):
        contact_bits.append(header["location"])
    if header.get("linkedin"):
        contact_bits.append(header["linkedin"])
    if header.get("portfolio"):
        contact_bits.append(header["portfolio"])
    if contact_bits:
        parts.append(" · ".join(contact_bits))

    summary_entries = state.sections.get("summary") or []
    if summary_entries:
        s = summary_entries[0]
        text = s.get("formatted") or s.get("summary_raw") or ""
        if text.strip():
            parts.append("\n## Summary\n\n" + text.strip())

    experience_entries = state.sections.get("experience") or []
    if experience_entries:
        parts.append("\n## Experience")
        for e in experience_entries:
            title = (e.get("job_title") or "").strip()
            company = (e.get("company_name") or "").strip()
            start = (e.get("start_date") or "").strip()
            end = (e.get("end_date") or "").strip()
            loc = (e.get("location") or "").strip()
            head_bits = [b for b in [title, company] if b]
            date_bits = [b for b in [start, end] if b]
            row = "**" + " — ".join(head_bits) + "**"
            if date_bits:
                row += f"  · {' – '.join(date_bits)}"
            if loc:
                row += f" · {loc}"
            parts.append("\n" + row)
            body = (e.get("formatted") or e.get("achievements_raw") or "").strip()
            if body:
                parts.append(body)

    edu_entries = state.sections.get("education") or []
    if edu_entries:
        parts.append("\n## Education")
        for ed in edu_entries:
            school = (ed.get("school") or "").strip()
            degree = (ed.get("degree") or "").strip()
            field_ = (ed.get("field") or "").strip()
            start = (ed.get("start_date") or "").strip()
            end = (ed.get("end_date") or "").strip()
            head = ", ".join([b for b in [degree, field_] if b])
            row = f"**{school}**"
            if head:
                row += f" — {head}"
            if start or end:
                row += f"  · {start} – {end}"
            if ed.get("honors"):
                row += f"  ({ed['honors']})"
            parts.append("\n" + row)

    skills_entries = state.sections.get("skills") or []
    if skills_entries:
        s = skills_entries[0]
        text = s.get("formatted") or s.get("skills_raw") or ""
        if text.strip():
            parts.append("\n## Skills\n\n" + text.strip())

    cert_entries = state.sections.get("certifications") or []
    if cert_entries:
        parts.append("\n## Certifications")
        for c in cert_entries:
            row = f"- **{c.get('cert_name', '').strip()}**"
            issuer = c.get("cert_issuer")
            year = c.get("cert_year")
            extras = []
            if issuer:
                extras.append(issuer)
            if year:
                extras.append(str(year))
            if extras:
                row += " — " + ", ".join(extras)
            parts.append(row)

    proj_entries = state.sections.get("projects") or []
    if proj_entries:
        parts.append("\n## Projects")
        for p in proj_entries:
            row = f"- **{p.get('project_name', '').strip()}**"
            desc = (p.get("project_description") or "").strip()
            if desc:
                row += f" — {desc}"
            url = p.get("project_url")
            if url:
                row += f" ({url})"
            parts.append(row)

    return "\n".join(parts).strip() + "\n"


# ---------------- Public API used by route handlers ----------------


FACT_RATIO_THRESHOLD = 0.6


def validate_ai_format_output(user_input: str, ai_output: str) -> tuple[bool, float]:
    """Returns (accept, ratio). Caller falls back to raw user_input
    when accept is False."""
    ratio = compute_fact_ratio(user_input, ai_output)
    return (ratio >= FACT_RATIO_THRESHOLD, ratio)


# ---------------- Print-friendly HTML render ----------------


def _md_inline(text: str) -> str:
    """Convert simple inline markdown to HTML. Order matters: ``**``
    before single ``*``. We only handle the constructs the CV
    assembler actually emits."""
    from html import escape

    # Pre-extract HTML tags we explicitly let through (e.g., the
    # ``<img>`` photo tag the assembler emits at the top). We swap
    # them for a placeholder, escape the rest, then restore.
    img_re = re.compile(r'<img\b[^>]*/?>', re.IGNORECASE)
    placeholders: list[str] = []

    def _stash(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"\x00IMG{len(placeholders) - 1}\x00"

    safe = img_re.sub(_stash, text)
    safe = escape(safe)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    # Restore the stashed <img>.
    for i, raw in enumerate(placeholders):
        safe = safe.replace(f"\x00IMG{i}\x00", raw)
    return safe


def cv_markdown_to_html(markdown: str) -> str:
    """Convert the CV-builder's well-known markdown shape into HTML.

    Handles only the constructs the assembler emits — keeps the
    converter tight enough to audit. Not a general markdown parser."""

    lines = markdown.splitlines()
    out: list[str] = []
    in_ul = False

    def _close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            _close_ul()
            continue
        # Heading 1
        if line.startswith("# "):
            _close_ul()
            out.append(f"<h1>{_md_inline(line[2:].strip())}</h1>")
            continue
        # Heading 2
        if line.startswith("## "):
            _close_ul()
            out.append(f"<h2>{_md_inline(line[3:].strip())}</h2>")
            continue
        # List item
        if line.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_md_inline(line[2:].strip())}</li>")
            continue
        # Pass-through if the line is *only* an <img …> tag.
        stripped = line.strip()
        if re.match(r'^<img\b[^>]*/?>$', stripped, re.IGNORECASE):
            _close_ul()
            out.append(stripped)
            continue
        # Plain paragraph.
        _close_ul()
        out.append(f"<p>{_md_inline(line)}</p>")
    _close_ul()
    return "\n".join(out)


def render_cv_print_html(cv_markdown: str, *, auto_print: bool = False) -> str:
    """Self-contained print-styled HTML doc the user can Save-as-PDF
    from their browser. Photo is embedded inline as a data URI so the
    file works offline.

    ``auto_print=True`` triggers the browser print dialog on page
    load — used when the user clicks the explicit "Download PDF"
    button. Without it the page just displays for review.
    """
    body_html = cv_markdown_to_html(cv_markdown or "")
    auto_print_script = ""
    if auto_print:
        # Defer until the photo has loaded so it appears in the PDF.
        auto_print_script = (
            "<script>window.addEventListener('load', function() {"
            "setTimeout(function() { window.print(); }, 250); });</script>"
        )
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\" />\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />\n"
        "<meta name=\"robots\" content=\"noindex\" />\n"
        "<title>CV — DirectJob Scout</title>\n"
        "<style>\n"
        "@page { size: A4; margin: 18mm 16mm; }\n"
        "html, body {\n"
        "  font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;\n"
        "  font-size: 11pt;\n"
        "  line-height: 1.45;\n"
        "  color: #1f2030;\n"
        "  background: #fff;\n"
        "  margin: 0;\n"
        "}\n"
        "body { padding: 24px 32px; }\n"
        "h1 {\n"
        "  font-size: 22pt;\n"
        "  letter-spacing: -0.01em;\n"
        "  margin: 0 0 4pt;\n"
        "}\n"
        "h2 {\n"
        "  font-size: 13pt;\n"
        "  margin: 18pt 0 6pt;\n"
        "  padding-top: 10pt;\n"
        "  border-top: 1px solid #d5d7e0;\n"
        "}\n"
        "p { margin: 0 0 8pt; }\n"
        "p + p { margin-top: 4pt; }\n"
        "ul { margin: 4pt 0 10pt; padding-left: 20pt; }\n"
        "li { margin-bottom: 3pt; }\n"
        "strong { color: #1f2030; }\n"
        "img {\n"
        "  float: right;\n"
        "  width: 96pt;\n"
        "  height: auto;\n"
        "  margin: 0 0 12pt 12pt;\n"
        "  border-radius: 6pt;\n"
        "}\n"
        ".toolbar {\n"
        "  background: #f3f4f9;\n"
        "  padding: 8pt 14pt;\n"
        "  margin: -24px -32px 18pt -32px;\n"
        "  display: flex;\n"
        "  gap: 8pt;\n"
        "  font-size: 9.5pt;\n"
        "}\n"
        ".toolbar a, .toolbar button {\n"
        "  background: #1f2030;\n"
        "  color: #fff;\n"
        "  padding: 5pt 10pt;\n"
        "  border-radius: 4pt;\n"
        "  text-decoration: none;\n"
        "  border: 0;\n"
        "  font-size: 9.5pt;\n"
        "  cursor: pointer;\n"
        "}\n"
        "@media print { .toolbar { display: none; } body { padding: 0; } }\n"
        "</style>\n"
        f"{auto_print_script}\n"
        "</head>\n"
        "<body>\n"
        "<div class=\"toolbar\" role=\"toolbar\">\n"
        "  <button type=\"button\" onclick=\"window.print()\">Download as PDF</button>\n"
        "  <a href=\"/\">Back to app</a>\n"
        "</div>\n"
        f"<main>{body_html}</main>\n"
        "</body>\n"
        "</html>\n"
    )
