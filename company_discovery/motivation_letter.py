"""DACH-norm motivation letter drafter.

Two output paths:

1. AI-backed — uses the configured provider via an injectable caller.
   The prompt enforces DACH structure (Absenderzeile, Adresse, Datum,
   Betreff, Anrede, 3-paragraph Hauptteil, Schluss, Unterschrift).
   We never invent — the system prompt instructs the model to use
   ONLY facts present in the user's CV. Fact-ratio gate caller-side.

2. Templated fallback — when no AI is configured. Returns a clearly
   structured skeleton with `<...>` placeholders so the user can
   fill it in by hand. An "I'm running without an AI right now"
   banner sits at the top so the user knows what they're getting.
"""

from __future__ import annotations

from datetime import date
from typing import Callable


def build_letter_prompt(
    *, job_title: str, company: str, location: str, job_url: str,
    cv_text: str, user_name: str = "", user_location: str = "",
) -> tuple[str, str]:
    """Return (system, user) prompts for the AI motivation drafter.

    The system prompt locks the output structure; the user prompt
    carries the job + CV context. Caller bundles them via the
    standard _dispatch_provider path.
    """
    system = (
        "You write Bewerbungsschreiben (DACH-norm motivation letters) "
        "for job applicants in Germany / Austria / Switzerland.\n\n"
        "OUTPUT STRUCTURE — exactly these sections, in this order:\n"
        "1. Absenderzeile (applicant name + city, on one line)\n"
        "2. Empfängeradresse (company name + location)\n"
        "3. Date (in TT.MM.JJJJ format)\n"
        "4. Betreff (subject line — 'Bewerbung als <role>')\n"
        "5. Anrede ('Sehr geehrte Damen und Herren,' unless a "
        "specific contact name is in the JD)\n"
        "6. Hauptteil — EXACTLY 3 paragraphs:\n"
        "   a) Motivation (why this role + company)\n"
        "   b) Qualifications (drawn from the CV — facts only)\n"
        "   c) Soft skills + fit (specific to the JD)\n"
        "7. Schluss ('Mit freundlichen Grüßen,')\n"
        "8. Unterschrift line\n\n"
        "STRICT RULES:\n"
        "- Use ONLY facts present in the CV. Never invent companies, "
        "  dates, titles, skills, or achievements.\n"
        "- If the CV is missing a relevant fact, write a generic line "
        "  instead of inventing one.\n"
        "- Language: German if the JD or company name suggests DACH, "
        "  else English.\n"
        "- Output the letter as plain text. No markdown."
    )
    user = (
        f"Job title: {job_title}\n"
        f"Company: {company}\n"
        f"Location: {location}\n"
        f"Job posting URL: {job_url}\n"
        f"Applicant name: {user_name or '(use signature line from CV)'}\n"
        f"Applicant city: {user_location or '(use city from CV)'}\n\n"
        "Applicant CV (the ONLY source of facts about the applicant):\n"
        f"{cv_text}\n\n"
        "Draft the motivation letter."
    )
    return system, user


def draft_with_ai(
    *, job: dict, cv_text: str, user_name: str, user_location: str,
    ai_caller: Callable[[str, str], str | None] | None,
) -> str | None:
    """Call the AI to produce a letter. Returns None on any failure;
    callers fall back to the templated path."""
    if ai_caller is None:
        return None
    system, user = build_letter_prompt(
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        job_url=job.get("url", ""),
        cv_text=cv_text,
        user_name=user_name,
        user_location=user_location,
    )
    try:
        return ai_caller(system, user)
    except Exception:  # noqa: BLE001
        return None


def templated_fallback(
    *, job: dict, user_name: str = "", user_location: str = "",
) -> str:
    """Templated DACH letter skeleton with `<...>` placeholders.
    Always succeeds — used when AI is unavailable. The banner makes
    the templated nature explicit so the user never thinks an LLM
    wrote it."""
    today = date.today().strftime("%d.%m.%Y")
    company = job.get("company") or "<Firma>"
    company_location = job.get("location") or "<Ort der Firma>"
    title = job.get("title") or "<Position>"
    name = user_name or "<Ihr Name>"
    you_loc = user_location or "<Ihre Stadt>"
    return (
        "_(I'm running without an AI right now — this is a template "
        "you can fill in. Configure a provider in /profile to get a "
        "personalised draft.)_\n\n"
        f"{name}, {you_loc}\n\n"
        f"{company}\n"
        f"{company_location}\n\n"
        f"{today}\n\n"
        f"Betreff: Bewerbung als {title}\n\n"
        "Sehr geehrte Damen und Herren,\n\n"
        f"hiermit bewerbe ich mich um die ausgeschriebene Position "
        f"als {title} bei {company}. <Erkläre kurz, warum diese Rolle "
        "und dieses Unternehmen dich interessieren.>\n\n"
        "<2. Absatz: Welche Qualifikationen aus deinem Lebenslauf "
        "passen zu der Stelle? Nenne konkrete Beispiele aus deiner "
        "bisherigen Erfahrung.>\n\n"
        "<3. Absatz: Welche persönlichen Eigenschaften und Soft-Skills "
        "machen dich für genau dieses Team und diese Aufgabe geeignet?>\n\n"
        "Über die Gelegenheit zu einem persönlichen Gespräch würde "
        "ich mich sehr freuen.\n\n"
        "Mit freundlichen Grüßen,\n\n"
        f"{name}"
    )
