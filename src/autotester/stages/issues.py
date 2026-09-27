"""ISSUES: turn an adjudicated analysis into rows a human tester can read.

Contract: qa/contracts/video-learning.md VL5/VL6. Pure over artifacts on
disk — no provider, no network.

The Excel columns are not this system's choice. They are the columns Vidysea's
own testers already use in `ERP_Issues_ALL.xlsx`, in their order, so a person
can put AutoTester's sheet beside their own and read across. That is the whole
point of T-136: the comparison is only fair if the shapes match.

**Measured, not assumed** (`.work/track-a-corpus-facts.md`, 2026-09-08): the two
human sheets do NOT share a schema. `ERP_Issues_ALL.xlsx` has these 13 columns
exactly. `ERP_Issues_Trainers.xlsx` — the sheet T-136's acceptance actually
scores against — has 12, with no `Date` and `Clip` where ALL says `Recording`.

**No scorer exists yet** — it is T-136, and reconciling those two shapes is its
first job, not a thing this module already does. This exporter writes the
13-column form, because that is the one a reader gets when they ask for "the
issues".
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from autotester.core.excel import autosize_columns
from autotester.schema.analysis import AnalysedIssue, VideoAnalysis
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, IssueOrigin
from autotester.schema.flowspec import Step
from autotester.schema.issue import Issue
from autotester.schema.project import Source
from autotester.store.project_store import PinnedCaseError, ProjectStore

ISSUE_COLUMNS = [
    "ID", "Date", "Severity", "Type", "Title", "What is wrong", "How we know",
    "Confirm first", "Said verbatim", "Recording", "At", "Screenshot shows", "Evidence",
]
"""The human sheet's columns, in the human sheet's order. Changing one breaks
the side-by-side comparison T-136 exists to make."""

SEVERITY_WORDS = {"S1": "High", "S2": "Medium", "S3": "Low"}
"""Their vocabulary, not ours. A tester reading `S2` has to translate; a tester
reading `Medium` does not, and this sheet is for them."""


def at_mmss(seconds: float) -> str:
    """`93.4` -> `01:33`. The human sheet writes times this way, and its `At`
    column holds strings — so a scorer comparing a float to that cell silently
    matches nothing (measured on the real workbook).

    A negative second is refused rather than rendered: `-1:55` in a tester's
    sheet looks like a time and is really a chunk offset applied twice, and the
    person who has to notice it is the one with the least context to."""
    if seconds < 0:
        raise ValueError(f"{seconds}: a negative timestamp is an upstream bug, not a time")
    total = round(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def _origin(issue: AnalysedIssue) -> IssueOrigin:
    """How we know — spoken, on-screen, or both.

    Derived from what the observation actually carried rather than taken from
    the model's own claim: a model asked "how do you know" answers plausibly
    every time, and the fields either hold a quote and on-screen text or they
    do not."""
    spoken = bool(issue.narration)
    on_screen = bool(issue.on_screen_text)
    if spoken and on_screen:
        return IssueOrigin.SPOKEN_AND_SCREEN
    if spoken:
        return IssueOrigin.SPOKEN
    if on_screen:
        return IssueOrigin.SCREEN
    return IssueOrigin.MODEL_DETECTED


def derive_issues(analysis: VideoAnalysis, source: Source, project: str) -> list[Issue]:
    """One `Issue` per adjudicated finding, provenance attached.

    `Issue.id` is content-addressed by the schema, so re-deriving the same
    analysis produces the same ids — which is what lets `add_issue` stay
    idempotent and a re-run not double the ledger."""
    return [
        Issue(
            project=project,
            source_id=source.id,
            recording_label=source.label or Path(source.path or "").name or source.id,
            recorded_on=source.recorded_on,
            at_s=issue.t_start,
            t_end_s=issue.t_end,
            screen=issue.screen,
            title=issue.title,
            what_is_wrong=issue.what_is_wrong,
            how_we_know=_origin(issue),
            models_agreeing=issue.models_agreeing,
            model_labels=list(issue.model_labels),
            said_verbatim=issue.narration,
            screenshot_shows=issue.on_screen_text,
            severity=issue.severity,
            category=issue.category,
            confidence=issue.confidence,
        )
        for issue in analysis.issues
    ]


def pin_issue_as_case(
    issue: Issue, flow_id: str, steps: list[Step], *, project: str | None = None,
) -> Case:
    """AT-585: the missing path from a confirmed finding to a regression case.

    Before this, `derive_issues` above only ever produced `Issue` rows for the
    Excel sheet a human reads, and `stages/expand.py::REGRESSION_ANCHOR` only
    ever replays a flow's happy path — a known bug had nowhere to become a
    case that must never silently return.

    Deliberately NOT a new taxonomy member: D-005/D-014 keep `CaseClass`
    closed ("Issue is a separate artifact"), so this reuses
    `CaseClass.REGRESSION_ANCHOR`/`CaseKind.ANCHOR` — the taxonomy's own
    "must survive every regression run" bucket — rather than inventing one.
    It is also deliberately NOT T-178's p0-p3 priority system; `Case.pinned`
    is the minimal marker until that unit subsumes it (see that field's
    docstring).

    `steps` are the human-confirmed repro steps, not a guess derived from the
    issue's narrative — pinning a case that cannot actually reproduce the bug
    would be worse than not pinning one at all.
    """
    return Case(
        project=project or issue.project,
        flow_id=flow_id,
        kind=CaseKind.ANCHOR,
        case_class=CaseClass.REGRESSION_ANCHOR,
        title=f"pinned regression — {issue.title}",
        rationale=f"AT-585: known bug {issue.id} must never silently return — "
                  f"{issue.what_is_wrong}",
        steps=steps,
        severity=issue.severity,
        pinned=True,
        pinned_issue_id=issue.id,
    )


def refuse_if_issue_already_pinned(store: ProjectStore, issue_id: str, new_case_id: str) -> None:
    """AT-604: `Case.id` is content-addressed on its steps, so pinning the same
    issue a second time with DIFFERENT steps would not collide with the first
    pinned case's id — it would silently create a SECOND protected case for the
    same finding. Both the UI pin route and `cli issues pin` call this,
    straight after building the candidate `Case`, so neither surface can do
    what the other refuses.

    Left to the ordinary duplicate-case guard (`ui/routes_cases.py::
    _refuse_duplicate`, and the CLI's own `has_case` check) is the case where
    `new_case_id` already equals the one on file — an identical resubmission,
    which is a different mistake with its own existing message.
    """
    existing = next(
        (c for c in store.list_cases() if c.pinned_issue_id == issue_id), None
    )
    if existing is not None and existing.id != new_case_id:
        raise PinnedCaseError(
            f"issue '{issue_id}' is already pinned as case '{existing.id}'. Unpin it "
            "first if it must be re-pinned with different steps -- pinning again would "
            "leave two protected cases for the same finding."
        )


def sync_source_issues(
    store: ProjectStore,
    source_id: str,
    derived: list[Issue],
    *,
    remove_missing: bool = True,
) -> None:
    """Refresh one source's rows without erasing trusted history.

    A complete analysis is authoritative and removes findings it no longer
    contains.  A partial analysis may add or improve findings, but cannot prove
    that an absent finding disappeared, so its missing rows are retained.
    Stable ids keep both human decisions and the original discovery timestamp.
    """
    current = {issue.id: issue for issue in store.list_issues()}
    incoming = {issue.id: issue for issue in derived}
    for issue in current.values():
        if remove_missing and issue.source_id == source_id and issue.id not in incoming:
            store.delete_issue(issue.id)
    for issue in derived:
        previous = current.get(issue.id)
        if previous is not None:
            if not remove_missing:
                # A partial reading is not authoritative enough to downgrade a
                # previously complete finding.  Its genuinely new ids are still
                # added below, but stable rows wait for a complete refresh.
                continue
            issue = issue.model_copy(update={
                "status": previous.status,
                "human_id": previous.human_id,
                "confirm_first": previous.confirm_first,
                "evidence_refs": list(previous.evidence_refs),
                "created_at": previous.created_at,
            })
            store.update_issue(issue)
        else:
            store.add_issue(issue)


def issue_row(issue: Issue) -> list[str]:
    """One sheet row, in `ISSUE_COLUMNS` order."""
    return [
        issue.human_id or issue.id,
        issue.recorded_on or "",
        SEVERITY_WORDS.get(issue.severity.value, issue.severity.value),
        issue.category.value,
        issue.title,
        issue.what_is_wrong,
        issue.how_we_know.value,
        issue.confirm_first or "",
        issue.said_verbatim or "",
        issue.recording_label,
        at_mmss(issue.at_s),
        issue.screenshot_shows or "",
        ", ".join(issue.evidence_refs),
    ]


def export_issues_excel(issues: list[Issue], out_path: Path) -> Path:
    """The issues as a workbook a tester can open beside their own."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All issues"
    sheet.append(ISSUE_COLUMNS)
    for issue in sorted(issues, key=lambda i: (i.recording_label, i.at_s)):
        sheet.append(issue_row(issue))
    autosize_columns(sheet)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(out_path)
    return out_path
