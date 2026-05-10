"""Extract plain text from a CV file uploaded by the user.

Supports ``.docx`` (Word / Google Docs export), ``.txt``, and ``.pdf``.

The DOCX and TXT paths are pure-stdlib. PDF requires ``pypdf`` (added
to ``requirements.txt`` in 0.7.0). If ``pypdf`` is not installed we
degrade gracefully — :func:`extract_text` raises
``CvExtractError("pdf_unavailable")`` so the caller can surface a
clear message.
"""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

try:  # pragma: no cover - optional dependency
    from pypdf import PdfReader  # type: ignore[import-not-found]

    _PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in test_round3
    _PYPDF_AVAILABLE = False


_W_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB upload cap


class CvExtractError(ValueError):
    """Raised when the uploaded blob cannot be turned into plain text."""


def extract_docx_text(blob: bytes) -> str:
    """Return the visible text of a ``.docx`` file as UTF-8 plain text."""

    if len(blob) > _MAX_BYTES:
        raise CvExtractError("file_too_large")
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            try:
                document_xml = zf.read("word/document.xml")
            except KeyError as error:  # not a valid docx
                raise CvExtractError("not_a_docx") from error
    except zipfile.BadZipFile as error:
        raise CvExtractError("not_a_docx") from error

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as error:
        raise CvExtractError("docx_parse_failed") from error

    paragraphs: list[str] = []
    for paragraph in root.iter(f"{_W_NAMESPACE}p"):
        runs: list[str] = []
        for child in paragraph.iter():
            tag = child.tag
            if tag == f"{_W_NAMESPACE}t":
                if child.text:
                    runs.append(child.text)
            elif tag == f"{_W_NAMESPACE}tab":
                runs.append("\t")
            elif tag == f"{_W_NAMESPACE}br":
                runs.append("\n")
        line = "".join(runs).strip()
        if line:
            paragraphs.append(line)
    text = "\n".join(paragraphs)
    if not text.strip():
        raise CvExtractError("docx_empty")
    return text


def extract_pdf_text(blob: bytes) -> str:
    """Return the visible text of a PDF as UTF-8 plain text.

    Requires ``pypdf``. Raises ``CvExtractError("pdf_unavailable")``
    when the dependency is not installed so the HTTP layer can return
    a clear 4xx instead of a 5xx.
    """

    if len(blob) > _MAX_BYTES:
        raise CvExtractError("file_too_large")
    if not _PYPDF_AVAILABLE:
        raise CvExtractError("pdf_unavailable")
    try:
        reader = PdfReader(io.BytesIO(blob))
    except Exception as error:  # pypdf raises a variety of types
        raise CvExtractError("not_a_pdf") from error
    pages: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - skip pages that pypdf can't read
            page_text = ""
        page_text = page_text.strip()
        if page_text:
            pages.append(page_text)
    text = "\n\n".join(pages)
    if not text.strip():
        raise CvExtractError("pdf_empty")
    return text


def extract_text(filename: str, blob: bytes) -> str:
    """Dispatch on filename extension."""

    name = (filename or "").lower()
    if name.endswith(".docx"):
        return extract_docx_text(blob)
    if name.endswith(".pdf"):
        return extract_pdf_text(blob)
    if name.endswith(".txt"):
        if len(blob) > _MAX_BYTES:
            raise CvExtractError("file_too_large")
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CvExtractError("text_decode_failed") from error
        if not text.strip():
            raise CvExtractError("text_empty")
        return text
    raise CvExtractError("unsupported_extension")
