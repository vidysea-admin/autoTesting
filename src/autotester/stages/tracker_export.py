"""TRACKER EXPORT: BugStore bugs as CSV / xlsx bytes in the Tracker sheet's layout (TB15).

Its one job is the file export of D-090: no `SheetClient`, no Google call, no network, so the live
path (`stages/sheet_write.py::LiveWriteRefused`) is untouched. The column mapping is the one
`schema/sheet_plan.py::SheetColumns` shape and the cell text is `stages/sheet_plan.py::bug_values`
plus `safe_cell`; this module only fixes the default header names and their order. Every value
passes the caller's `scrub` (a `Redactor.scrub`). Rows are sorted by (first seen, key) and the
xlsx container is rewritten with fixed metadata and zip times, so exporting the same bugs twice
gives identical bytes.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable
from datetime import datetime

from openpyxl import Workbook

from autotester.schema.sheet_plan import SheetColumns
from autotester.schema.tracked_bug import TrackedBug
from autotester.stages.sheet_plan import Scrub, bug_values, safe_cell

TRACKER_COLUMNS = SheetColumns(
    sheet_id="local-export", tab="Tracker",
    columns={"bug_key": "Bug ID", "title": "Title", "severity": "Severity", "screen": "Screen",
             "status": "Status", "assignee": "Assigned To", "first_seen": "First Seen",
             "last_seen": "Last Seen", "count": "Count"},
)
"""The Tracker tab's headers in sheet order, keyed by bug field (as the sheet plan maps them)."""

EVIDENCE_HEADER = "Evidence"
FIXED_TIME = datetime(2026, 1, 1)
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def header_row() -> list[str]:
    return [*TRACKER_COLUMNS.columns.values(), EVIDENCE_HEADER]


def evidence_path(bug: TrackedBug) -> str:
    """The login-gated product URL of the evidence run (relative; no host is guessed)."""
    if not bug.evidence_run_id:
        return ""
    return f"/projects/{bug.project}/runs/{bug.evidence_run_id}"


def bug_rows(bugs: Iterable[TrackedBug], scrub: Scrub) -> list[list[str]]:
    """One scrubbed, formula-safe row per bug, in the layout's order."""
    rows: list[list[str]] = []
    for bug in sorted(bugs, key=lambda b: (b.first_seen, b.bug_key)):
        values = bug_values(bug)
        row = [safe_cell(scrub(values[field])) for field in TRACKER_COLUMNS.columns]
        rows.append([*row, safe_cell(scrub(evidence_path(bug)))])
    return rows


def to_csv(bugs: Iterable[TrackedBug], scrub: Scrub) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(header_row())
    writer.writerows(bug_rows(bugs, scrub))
    return out.getvalue().encode("utf-8")


def to_xlsx(bugs: Iterable[TrackedBug], scrub: Scrub) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = TRACKER_COLUMNS.tab
    ws.append(header_row())
    for row in bug_rows(bugs, scrub):
        ws.append(row)
    wb.properties.created = wb.properties.modified = FIXED_TIME
    raw = io.BytesIO()
    wb.save(raw)
    return _normalise(raw.getvalue())


def _normalise(blob: bytes) -> bytes:
    """Rewrite the zip with fixed entry times so identical content is identical bytes."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(blob)) as src, \
            zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in sorted(src.namelist()):
            info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(info, src.read(name))
    return out.getvalue()
