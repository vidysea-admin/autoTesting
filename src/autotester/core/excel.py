"""Workbook presentation helpers shared by every Excel exporter.

Extracted from `stages/report_export.py` when `stages/crawl_report.py` needed
the same column sizing: two exporters computing column widths two slightly
different ways is exactly the "one concept, two places" drift C3 forbids.
"""

from __future__ import annotations

import re
from typing import Any

# openpyxl refuses to write control characters (IllegalCharacterError). Live
# console output carries them (AT-530: a Pathlynks crawl's issue detail ended
# the whole report), so every string cell passes through `clean_cell` once.
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_cell(value: object) -> object:
    """`value` with control characters removed when it is a string; anything else unchanged."""
    return _ILLEGAL.sub("", value) if isinstance(value, str) else value


def autosize_columns(ws: Any, *, max_width: int = 60) -> None:
    """Widen every column to fit its longest cell, capped so one long error
    string cannot push a column off the screen."""
    for column in ws.columns:
        values = [cell.value for cell in column if cell.value is not None]
        if not values:
            continue
        width = max(len(str(value)) for value in values)
        ws.column_dimensions[column[0].column_letter].width = min(width + 2, max_width)
