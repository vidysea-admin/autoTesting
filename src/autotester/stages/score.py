"""SCORE: compare AutoTester's issues against a human tester's own sheet.

Contract: qa/contracts/video-learning.md (T-136 acceptance). Pure over artifacts
on disk and one workbook — no provider, no network.

This is the north star made arithmetic: *an expert human tester and AutoTester
get the same material and the same build; AutoTester wins on bugs found, false
positives, and time.* Everything before this unit was the machinery; this is the
first module whose output is a number a human can disagree with.

**The two sheets do not share a schema** (measured 2026-09-08,
`.work/track-a-corpus-facts.md`). `ERP_Issues_Trainers.xlsx` has 12 columns and
names the recording `Clip`; `ERP_Issues_ALL.xlsx` has 13 and calls it
`Recording`. T-133's docstring claimed "the scorer accommodates both" while no
scorer existed (AT-201). It does now, and `RECORDING_COLUMNS` is why.

Four measured facts are enforced here rather than remembered, because each one
silently produces a recall of **zero**:

* `At` holds STRINGS like `"00:29"`, not numbers.
* The clip cell is `"erp1.mp4 (Divya Kamboj, trainer pipeline)"` — a filename
  plus who and what, not a filename.
* `ERP_Issues_ALL.xlsx` has **32** data rows, not the plan's 33.
* The corpus lives on `C:`, not `D:`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

from autotester.schema.issue import Issue
from autotester.stages.similarity_score import similarity

RECORDING_COLUMNS = ("Clip", "Recording")
"""What the recording column is called, in the two sheets that exist. Trainers
says `Clip`; ALL says `Recording`. A scorer that knows only one silently matches
nothing against the other."""

TITLE_COLUMN, WHAT_COLUMN, AT_COLUMN, ID_COLUMN = "Title", "What is wrong", "At", "ID"

MMSS = re.compile(r"^\s*(\d+):([0-5]?\d)\s*$")


class TruthSheetError(ValueError):
    """The workbook is not a shape this can score against — said out loud rather
    than returning an empty list, which would read as "nothing to find"."""


@dataclass
class TruthRow:
    """One row a human tester wrote, normalised."""

    id: str
    title: str
    what_is_wrong: str
    recording: str
    at_s: float
    row_number: int

    @property
    def text(self) -> str:
        return f"{self.title} {self.what_is_wrong}".strip()


@dataclass
class Match:
    """One truth row and the issue that claims it (or nothing)."""

    truth: TruthRow
    issue_id: str | None = None
    issue_title: str = ""
    similarity: float = 0.0
    seconds_apart: float | None = None

    @property
    def found(self) -> bool:
        return self.issue_id is not None


@dataclass
class Scorecard:
    """What the comparison found. Every field is a count or a list, never a
    grade — the judgement is the reader's."""

    truth_rows: int
    reported: int
    matches: list[Match] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)

    @property
    def found(self) -> int:
        return sum(1 for m in self.matches if m.found)

    @property
    def recall(self) -> float:
        return self.found / self.truth_rows if self.truth_rows else 0.0

    def as_dict(self) -> dict:
        return {
            "truth_rows": self.truth_rows,
            "reported": self.reported,
            "found": self.found,
            "missed": self.truth_rows - self.found,
            "false_positives": len(self.false_positives),
            "recall": round(self.recall, 4),
            "per_row": [
                {
                    "id": m.truth.id,
                    "found": m.found,
                    "similarity": round(m.similarity, 3),
                    "seconds_apart": m.seconds_apart,
                    "truth_title": m.truth.title[:120],
                    "matched_title": m.issue_title[:120],
                }
                for m in self.matches
            ],
            "false_positive_titles": [t[:120] for t in self.false_positives],
        }


def at_seconds(cell: object) -> float:
    """`"01:33"` -> `93.0`. The human sheet's `At` column holds strings.

    A number is accepted too and read as seconds, because a sheet edited by hand
    can hold either — but a value that is neither is refused rather than
    silently scored as second zero, which would match whatever happens to open
    the recording."""
    if isinstance(cell, (int, float)):
        return float(cell)
    match = MMSS.match(str(cell or ""))
    if not match:
        raise TruthSheetError(f"{cell!r} is not MM:SS — the At column holds strings like '00:29'")
    return int(match.group(1)) * 60 + int(match.group(2))


UNKNOWN_RECORDING = chr(0) + "unknown"
"""What an empty recording cell keys to. AT-223: blank/None/0 all keyed to `""`,
and `""` MATCHES `""` -- so a sheet with an empty clip column scored 1.0 recall
against issues with empty labels. A value that cannot identify a recording must
not be able to match one, so it gets a key nothing else can equal."""


def recording_key(cell: object) -> str:
    """`"erp1.mp4 (Divya Kamboj, trainer pipeline)"` -> `"erp1.mp4"`.

    The clip cell names a file AND who recorded it AND what it covers. Comparing
    the whole cell to a source label matches nothing; taking the leading filename
    is what lets a truth row find its recording.

    **AT-223 — only a parenthetical AFTER a filename is prose.** Splitting on the
    first `(` unconditionally collapsed `clip (1).mp4` and `clip (2).mp4` to the
    same key, which is a real Windows filename shape and would have silently
    merged two different recordings. The split now happens only when what precedes
    the `(` already looks like a file."""
    text = str(cell or "").strip()
    if not text:
        return UNKNOWN_RECORDING
    head = text.split("(")[0].strip()
    if "(" in text and re.search(r"\.[A-Za-z0-9]{2,4}$", head):
        return head.casefold()
    return text.casefold()


def _header(sheet) -> dict[str, int]:
    row = next(sheet.iter_rows(max_row=1, values_only=True), None)
    if not row:
        raise TruthSheetError("the sheet is empty — no header row")
    return {str(v).strip(): i for i, v in enumerate(row) if v is not None}


def load_truth(path: Path, sheet_name: str) -> list[TruthRow]:
    """The human's rows, from the workbook they actually keep."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name not in workbook.sheetnames:
            raise TruthSheetError(
                f"{path.name} has no sheet {sheet_name!r} — it has {workbook.sheetnames}")
        sheet = workbook[sheet_name]
        columns = _header(sheet)
        recording_col = next((columns[c] for c in RECORDING_COLUMNS if c in columns), None)
        if recording_col is None:
            raise TruthSheetError(
                f"no recording column: expected one of {RECORDING_COLUMNS}, got {sorted(columns)}")
        for needed in (TITLE_COLUMN, WHAT_COLUMN, AT_COLUMN):
            if needed not in columns:
                raise TruthSheetError(f"column {needed!r} missing; got {sorted(columns)}")

        rows: list[TruthRow] = []
        for number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not any(values):
                continue
            rows.append(TruthRow(
                id=str(values[columns.get(ID_COLUMN, 0)] or f"row{number}"),
                title=str(values[columns[TITLE_COLUMN]] or ""),
                what_is_wrong=str(values[columns[WHAT_COLUMN]] or ""),
                recording=recording_key(values[recording_col]),
                at_s=at_seconds(values[columns[AT_COLUMN]]),
                row_number=number,
            ))
        return rows
    finally:
        workbook.close()


def _best_candidate(row: TruthRow, remaining: list[Issue], window_s: float):
    """The single best-scoring issue for `row`, or `None` if nothing shares its
    recording within `window_s`. Sorted, not `max()`: highest similarity, then
    closest in time, then the issue's own content-addressed id.

    **AT-221 — the tie-break must be total.** I claimed the ordering was
    deterministic; it was not. `max()` returns the FIRST maximum, so two issues
    of equal similarity handed the choice to `list_issues()` file order, and
    permuting them moved recall from 0.5 to 1.0. That is AT-197's defect exactly
    -- a non-total sort key letting caller order leak in -- reappearing in the
    module that computes the north star's own number. The id makes the key
    TOTAL, so no tie survives."""
    candidates = [
        (similarity(row.text, f"{i.title} {i.what_is_wrong}"), abs(i.at_s - row.at_s), i)
        for i in remaining
        if recording_key(i.recording_label) == row.recording
        and abs(i.at_s - row.at_s) <= window_s
    ]
    ordered = sorted(candidates, key=lambda c: (-c[0], c[1], c[2].id))
    return ordered[0] if ordered else None


def score(truth: list[TruthRow], issues: list[Issue], *,
          window_s: float = 20.0, threshold: float = 0.30) -> Scorecard:
    """Greedy best-match, each truth row claimed at most once.

    A truth row and an issue can match only when they name the same recording
    AND sit within `window_s` of each other AND read similarly enough. All three
    are required: text alone would let one loud finding claim every row, and
    time alone would match whatever the model happened to say at that second.

    Greedy rather than optimal (Hungarian): the assignment is tiny and a reader
    can follow why a given row was claimed. An optimal matcher would raise recall
    slightly and cost every reader the ability to check it.

    **AT-233 — a rejected best candidate keeps its score.** A candidate under
    `threshold` used to be discarded down to the same similarity=0.0,
    seconds_apart=None as a row with no candidate at all -- indistinguishable
    from silence. It now keeps its real similarity/seconds_apart on the Match
    (issue_id stays unset, so `found` is still False); only a row with no
    candidate in range at all stays at the 0.0/None default."""
    remaining = list(issues)
    matches: list[Match] = []

    for row in truth:
        if row.recording == UNKNOWN_RECORDING:
            # AT-223, second half: an unrecognisable recording must match
            # NOTHING, including another unrecognisable one.
            matches.append(Match(truth=row))
            continue
        best = _best_candidate(row, remaining, window_s)
        if best is None:
            matches.append(Match(truth=row))
            continue
        ratio, apart, issue = best
        if ratio < threshold:
            matches.append(Match(truth=row, similarity=ratio, seconds_apart=apart))
            continue
        remaining.remove(issue)
        matches.append(Match(truth=row, issue_id=issue.id, issue_title=issue.title,
                             similarity=ratio, seconds_apart=apart))

    return Scorecard(truth_rows=len(truth), reported=len(issues), matches=matches,
                     false_positives=[i.title for i in remaining])
