"""A tracked bug: one failure the team owns, however many runs re-report it (TB1).

The bug key is the whole point. `bug_key = content_id("bug", {project, case_id,
criterion_id})` never holds a run id, a time, a path or a screenshot hash, so three
runs failing the same criterion are ONE bug and two failing criteria on one case are
two. Only the lifecycle in `stages/bug_loop.py` moves `status` (R44, machine-owned).

`BugStatus` lives here, not in `schema/enums.py`: that file sits at the 300-line cap.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotester.core.ids import content_id
from autotester.schema.base import Artifact
from autotester.schema.enums import Severity

DEFAULT_CLOSE_PASSES = 2
"""N consecutive evidenced PASS verdicts that close a bug (plan gate assumption, TB2).
`Project.bug_close_passes` stores the live value; this is only its default."""


class BugStatus(StrEnum):
    OPEN = "open"
    FIXED = "fixed"
    REOPENED = "reopened"
    STALE = "stale"
    """The case was deleted or its criterion changed, so no verdict can honestly close
    or confirm this bug any more (TB4). Never `fixed`."""


def case_bug_key(project: str, case_id: str, criterion_id: str) -> str:
    """The key of a case-failure bug. A secret planted in case text cannot reach it:
    `case_id` is itself a content hash and `criterion_id` is a short rubric id."""
    return content_id("bug", {"project": project, "case_id": case_id,
                              "criterion_id": criterion_id})


def verdict_ref(run_id: str, case_id: str) -> str:
    """A verdict's id: it lives at `runs/<run_id>/<case_id>.verdict.json` (no id field)."""
    return f"{run_id}/{case_id}"


class TrackedBug(Artifact):
    """One bug and its lifecycle. `applied` holds every verdict ref already counted, which
    is what makes a re-processed or crash-resumed run change nothing (TB6)."""

    bug_key: str
    project: str
    case_id: str | None = Field(default=None, description="None for a video-found bug")
    criterion_id: str | None = None
    criterion_fp: str = Field(
        default="", description="fingerprint of the criterion when the bug opened; a change "
                                "makes the bug stale (TB4)")
    title: str
    screen: str | None = None
    severity: Severity = Severity.S2
    status: BugStatus = BugStatus.OPEN
    count: int = Field(default=1, ge=1, description="FAIL verdicts seen")
    first_seen: datetime
    last_seen: datetime
    assignee: str | None = None
    evidence_run_id: str | None = Field(default=None, description="latest run with evidence")
    pass_streak: int = Field(default=0, ge=0, description="consecutive evidenced PASSes")
    streak_runs: list[str] = Field(default_factory=list)
    streak_verdicts: list[str] = Field(default_factory=list)
    closed_by_runs: list[str] = Field(default_factory=list)
    closed_by_verdicts: list[str] = Field(default_factory=list)
    applied: list[str] = Field(default_factory=list)


class ProcessedRun(BaseModel):
    """Marker that run R was fully processed. No timestamp: re-writing it is byte-stable."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    verdicts: list[str] = Field(default_factory=list)
