"""Supervise local PDF extraction with a hard timeout and bounded input/output."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from autotester.schema.document import DocumentReading, PdfLimits


def extract_pdf_document(path: Path, limits: PdfLimits | None = None) -> DocumentReading:
    """Run untrusted PDF parsing outside the web worker; errors never echo document text."""
    limits = limits or PdfLimits()
    try:
        if path.stat().st_size > limits.max_bytes:
            return DocumentReading(error="PDF exceeds file size limit")
        with tempfile.TemporaryDirectory(prefix="autotester-pdf-") as folder:
            result = Path(folder) / "reading.json"
            subprocess.run([sys.executable, "-m", "autotester.sources.pdf_worker",
                            str(path.resolve()), str(result), limits.model_dump_json()],
                           timeout=limits.timeout_s, check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=(
                               subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
            if result.stat().st_size > limits.max_chars * 8 + limits.max_pages * 1000:
                return DocumentReading(error="PDF extraction output exceeds size limit")
            return DocumentReading.model_validate_json(result.read_text(encoding="utf-8"))
    except Exception:
        return DocumentReading(error="PDF extraction failed or exceeded its deadline")
