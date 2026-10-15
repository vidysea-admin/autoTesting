"""Extract PDF page text in an isolated process the supervisor can terminate."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pypdf import PageObject, PdfReader

from autotester.schema.document import DocumentPage, DocumentReading, PdfLimits
from autotester.sources.pdf_ocr import ocr_pdf_page


def read_pdf_pages(path: Path, limits: PdfLimits) -> DocumentReading:
    """Read every page or report incompleteness; never treat skipped pages as learned."""
    logging.getLogger("pypdf").disabled = True
    try:
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            return DocumentReading(error="encrypted PDF is unsupported; provide an unlocked copy")
        if not 0 < len(reader.pages) <= limits.max_pages:
            return DocumentReading(error="PDF page count is empty or exceeds the page limit")
        pages: list[DocumentPage] = []
        chars = 0
        for number, page in enumerate(reader.pages, 1):
            result = _read_pdf_page(path, page, number, limits)
            chars += len(result.text)
            if chars > limits.max_chars:
                missing = [DocumentPage(number=n, method="unreadable",
                                       error="not processed: PDF character limit")
                           for n in range(number, len(reader.pages) + 1)]
                return DocumentReading(pages=pages + missing,
                                       error="PDF text exceeds character limit")
            pages.append(result)
        return DocumentReading(pages=pages, error=(
            "PDF has unreadable pages; inspect the page extraction evidence"
            if any(p.error for p in pages) else None))
    except Exception:
        return DocumentReading(error="PDF is corrupt or could not be read")


def _read_pdf_page(path: Path, page: PageObject, number: int, limits: PdfLimits) -> DocumentPage:
    try:
        text = (page.extract_text() or "").strip()
        return (DocumentPage(number=number, text=text, method="text") if text
                else ocr_pdf_page(path, number, limits))
    except Exception:
        return DocumentPage(number=number, method="unreadable", error="page could not be read")


def _worker_main() -> None:
    limits = PdfLimits.model_validate_json(sys.argv[3])
    result = read_pdf_pages(Path(sys.argv[1]), limits)
    Path(sys.argv[2]).write_text(result.model_dump_json(), encoding="utf-8")


if __name__ == "__main__":
    _worker_main()
