"""R24.9 — restricted "tailor CV for this job" pipeline.

The legacy ``execute_cv_tailoring`` returned free-form prose: the
LLM was given the whole CV + job description and asked to "rewrite".
That violated R24's promise (templates are sacred — AI never edits
layout) and was also wasteful (~3000 output tokens for a job-tailored
variant).

R24.9 swaps that for a STRUCTURED tailoring:

  inputs:  current CvDocument + target job description
  output:  patched CvDocument with
             - a new ``summary`` written for THIS job
             - per-role ``bullets`` reordered so the most
               job-relevant achievement is on top
           but identical schema, identical contacts / education /
           skills / languages / certifications / publications.

Two consequences:

1. The user can swap templates / accents AFTER tailoring and the
   tailored content travels with them. The template never changes.
2. Output token count drops dramatically (~80-90% reduction) which
   is a margin win on the operator-paid plans.

The LLM produces a small JSON payload. We parse + apply it as a
patch on a deep-copy of the original CvDocument. Failure modes:
  - LLM returns bad JSON → return original doc unchanged + log.
  - LLM returns extra fields we don't expect → ignored.
  - LLM tries to rewrite experience.title / company / dates → ignored.
"""

from __future__ import annotations

import copy
import json
import re

from company_discovery.ai_providers import AIProviderConfig
from company_discovery.cv_schema import CvDocument, MAX_SUMMARY


_MAX_JOB_DESC_CHARS = 6000


def _strip_control(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text or "")


def build_cv_tailor_prompt(cv_doc: CvDocument, job_description: str) -> str:
    """Bounded JSON-output prompt. The CV is shown as a compact
    structured summary (NOT the rendered HTML); the model only
    needs to know titles + bullet text to reason about ordering."""

    # Compact textual summary of the CV the model can reason over.
    parts = [f"CANDIDATE: {cv_doc.full_name or '(unknown)'}"]
    if cv_doc.summary:
        parts.append(f"CURRENT SUMMARY: {cv_doc.summary}")
    parts.append("EXPERIENCE:")
    for idx, e in enumerate(cv_doc.experience):
        meta = " – ".join(x for x in (e.start, e.end) if x) or ""
        parts.append(
            f"[role-{idx}] {e.title} at {e.company} "
            f"({e.location or ''}) {meta}"
        )
        for bidx, b in enumerate(e.bullets):
            parts.append(f"  bullet-{idx}-{bidx}: {b}")
    cv_compact = "\n".join(parts)

    job = _strip_control(job_description)[:_MAX_JOB_DESC_CHARS]

    return f"""You are a CV-tailoring assistant. Given a candidate's
CURRENT CV (below) and a target JOB description (inside <job> tags),
produce a JSON patch that:

1. Rewrites the SUMMARY to fit this specific job (1-3 sentences,
   {MAX_SUMMARY} chars max, same language as the CV).
2. For each role, returns the ORDER you'd present its existing
   bullets to maximise job relevance (newest / most relevant first).

You may NOT invent new bullets, rewrite bullets, change titles,
companies, dates, or anything else about the CV structure. ONLY
reorder existing bullet indices and write a new summary.

Return ONLY this JSON shape:

{{
  "summary": "new tailored summary in 1-3 sentences",
  "experience": [
    {{ "role_index": 0, "bullet_order": [2, 0, 1] }},
    ...
  ]
}}

- ``role_index`` matches ``[role-N]`` labels below.
- ``bullet_order`` is a permutation of bullet indices for that role.
  Omit indices you'd drop from the front-page version (they stay
  in the document, just lower priority).

CURRENT CV:
{cv_compact}

<job>
{job}
</job>

Return the JSON now.""".strip()


def _parse_json_lenient(text: str) -> dict | None:
    """Same lenient parser as cv_extraction — see that module."""
    if not text:
        return None
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    parsed = json.loads(text[start:i + 1])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
    return None


def apply_tailor_patch(cv_doc: CvDocument, patch: dict) -> CvDocument:
    """Apply a JSON patch (the model's output) to a deep copy of the
    CV. The patch can ONLY:
      * replace ``summary``
      * reorder ``experience[i].bullets``

    Anything else in the patch is ignored — defense-in-depth so a
    misbehaving model can't change titles, companies, or dates.
    """
    if not isinstance(patch, dict):
        return cv_doc
    out = copy.deepcopy(cv_doc)
    new_summary = patch.get("summary")
    if isinstance(new_summary, str) and new_summary.strip():
        out.summary = new_summary[:MAX_SUMMARY]
    exp_patches = patch.get("experience")
    if isinstance(exp_patches, list):
        for ep in exp_patches:
            if not isinstance(ep, dict):
                continue
            try:
                idx = int(ep.get("role_index"))
            except (TypeError, ValueError):
                continue
            if idx < 0 or idx >= len(out.experience):
                continue
            order = ep.get("bullet_order")
            if not isinstance(order, list):
                continue
            current = out.experience[idx].bullets or []
            new_bullets: list[str] = []
            seen: set[int] = set()
            for raw in order:
                try:
                    bi = int(raw)
                except (TypeError, ValueError):
                    continue
                if bi < 0 or bi >= len(current) or bi in seen:
                    continue
                seen.add(bi)
                new_bullets.append(current[bi])
            # Append any bullets the model dropped — keeps the
            # original information; just deprioritises them.
            for bi, b in enumerate(current):
                if bi not in seen:
                    new_bullets.append(b)
            out.experience[idx].bullets = new_bullets
    return out


def tailor_cv_for_job(
    cv_doc: CvDocument,
    job_description: str,
    provider: AIProviderConfig,
    *,
    runtime_credential: str = "",
    record_call=None,
) -> CvDocument:
    """Run the structured tailoring prompt and return a patched
    ``CvDocument``. On any failure, returns the original document
    unchanged so the user always sees a usable CV."""

    if not cv_doc or not job_description.strip():
        return cv_doc

    from company_discovery.analysis import _dispatch_provider
    from company_discovery.model_router import TASK_CV_CONSULT

    prompt = build_cv_tailor_prompt(cv_doc, job_description)
    # We reuse TASK_CV_CONSULT (premium tier) — this is the same
    # complexity bucket as cv-consult and motivation-letter writing.
    result = _dispatch_provider(
        prompt, provider, runtime_credential,
        task=TASK_CV_CONSULT,
        record_call=record_call,
    )
    if result.status != "completed" or not result.output:
        return cv_doc
    patch = _parse_json_lenient(result.output)
    if patch is None:
        return cv_doc
    return apply_tailor_patch(cv_doc, patch)
