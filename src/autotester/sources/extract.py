"""Deterministic host-side text extraction for DOC sources.

Turns an uploaded document into plain text on the host, with NO model call —
the DOC half of the source-adapter seam (qa/contracts/source-adapters.md,
SA-table + SA5). `.txt`/`.md` are read as UTF-8; `.docx` is unzipped and its
`word/document.xml` stripped of tags (stdlib only — the contract open-question
#1 default, "stdlib-first, no new heavyweight dependency"). PDFs use a bounded
local pypdf worker, with Poppler/Tesseract for scanned pages. Corrupt, encrypted
or partly unreadable inputs yield explicit errors and page evidence, never
empty text passed off as a real reading. No extraction calls a model.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import NamedTuple

from autotester.schema.document import DocumentReading
from autotester.sources.pdf_extract import extract_pdf_document

TEXT_SUFFIXES = frozenset({".txt", ".md"})
DOCX_SUFFIX = ".docx"
PDF_SUFFIX = ".pdf"
DOC_SUFFIXES = frozenset(TEXT_SUFFIXES | {DOCX_SUFFIX, PDF_SUFFIX})

_DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class Extraction(NamedTuple):
    """The outcome of reading a document: text OR an honest error.

    Exactly one side is meaningful. `error` set with `text` None is the SA5
    honest-degradation state; it must never be silently collapsed to empty text.
    """

    text: str | None
    error: str | None
    reading: DocumentReading | None = None


def extract_document_text(path: Path) -> Extraction:
    """Read `path` to plain text on the host, or report why it could not be read.

    Deterministic and model-free. An unsupported suffix, a corrupt archive, or
    undecodable bytes all return an `Extraction` carrying an `error` — SA5's
    "honest degradation, never silent empty text".
    """
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT_SUFFIXES:
            return Extraction(_read_text(path), None)
        if suffix == DOCX_SUFFIX:
            return Extraction(_read_docx(path), None)
        if suffix == PDF_SUFFIX:
            reading = extract_pdf_document(path)
            text = "\n\n".join(f"[page {p.number}]\n{p.text}" for p in reading.pages)
            return Extraction(text if not reading.error else None, reading.error, reading)
        return Extraction(None, f"unsupported document type '{suffix or path.name}'")
    except Exception as exc:  # honest degradation (SA5): a reading is never faked
        return Extraction(None, f"{type(exc).__name__}: {exc}")


def _read_text(path: Path) -> str:
    """A plain-text document, decoded strictly so undecodable bytes surface (SA5)."""
    return path.read_text(encoding="utf-8")


def _read_docx(path: Path) -> str:
    """The visible paragraph text of a .docx, via stdlib zip + XML (no dependency).

    A .docx is a zip whose `word/document.xml` holds the body; each `<w:p>` is a
    paragraph and each `<w:t>` a run of text. A file that is not a valid zip (a
    corrupt upload) raises here and is caught by the caller as an error.

    A `<!DOCTYPE>` is refused before parsing: a legitimate Office document never
    carries one, and both XXE (external entities) and billion-laughs (entity
    expansion) attacks against the stdlib expat parser require one. Refusing it
    is the stdlib-only defence, and the refusal degrades to an error (SA5), not
    a crash, on a hostile upload.
    """
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    if b"<!doctype" in xml_bytes[:4096].lower():
        raise ValueError("refusing a document.xml carrying a DOCTYPE (XXE/entity-expansion guard)")
    root = ET.fromstring(xml_bytes)
    paragraphs = [
        "".join(run.text for run in para.iter(f"{_DOCX_NS}t") if run.text)
        for para in root.iter(f"{_DOCX_NS}p")
    ]
    return "\n".join(paragraphs).strip()
