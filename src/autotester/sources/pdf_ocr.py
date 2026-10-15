"""Read one scanned PDF page with bounded local Poppler and Tesseract commands."""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from autotester.schema.document import DocumentPage, PdfLimits


def ocr_pdf_page(path: Path, number: int, limits: PdfLimits) -> DocumentPage:
    """No upload or model call: render one page, then read Tesseract's TSV."""
    poppler = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not poppler or not tesseract:
        return DocumentPage(number=number, method="unreadable",
                            error="local OCR requires pdftoppm and tesseract on PATH")
    try:
        with tempfile.TemporaryDirectory(prefix="autotester-ocr-") as folder:
            prefix = Path(folder) / "page"
            _pdf_tool([poppler, "-f", str(number), "-l", str(number), "-singlefile",
                       "-scale-to", str(limits.image_side), "-png", str(path), str(prefix)],
                      limits.page_timeout_s)
            output = Path(folder) / "reading"
            _pdf_tool([tesseract, str(prefix.with_suffix(".png")), str(output),
                       "-l", "eng", "tsv"], limits.page_timeout_s)
            tsv = output.with_suffix(".tsv")
            if tsv.stat().st_size > limits.max_chars * 4:
                raise ValueError("OCR output exceeds character limit")
            text, confidence = _pdf_tsv(tsv.read_text(encoding="utf-8"))
            if not text:
                raise ValueError("page has no readable text")
            return DocumentPage(number=number, text=text, method="ocr", confidence=confidence,
                                error=("OCR confidence below review threshold"
                                       if confidence is None or confidence < limits.min_confidence
                                       else None))
    except (OSError, ValueError, subprocess.SubprocessError):
        return DocumentPage(number=number, method="unreadable",
                            error="local OCR failed, timed out, or found no readable text")


def _pdf_tool(arguments: list[str], timeout: float) -> None:
    subprocess.run(arguments, check=True, timeout=timeout, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
                   creationflags=(
                       subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))


def _pdf_tsv(tsv: str) -> tuple[str, float | None]:
    lines: dict[tuple[str, ...], list[str]] = {}
    confidences: list[float] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        text = row.get("text", "").strip()
        if not text:
            continue
        confidence = float(row["conf"])
        if not 0 <= confidence <= 100:
            raise ValueError("invalid OCR confidence")
        key = tuple(row.get(k, "") for k in ("page_num", "block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append(text)
        confidences.append(confidence)
    return ("\n".join(" ".join(words) for words in lines.values()),
            sum(confidences) / len(confidences) if confidences else None)
