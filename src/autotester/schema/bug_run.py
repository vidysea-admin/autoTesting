"""What reading the bug store and processing one run reports: the shapes of T-199b (TB3, TB4, TB6).

Its one job is the shapes. Nothing here is stored: a `BugSnapshot` is one read of the event log, and
a `RunReport` says what one `process_run` did, so a human can see a bad file by name, a verdict that
moved nothing, or a bug that could not be checked, instead of a silent skip.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.tracked_bug import BugEvent, TrackedBug


class BadEventFile(BaseModel):
    """An event file the store could not use. It is reported by name and never deleted (P4)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    why: str = Field(max_length=300)


class BugSnapshot(BaseModel):
    """One read of the log: the valid events (in replay order), the bugs they fold to, and the
    files that were not valid. A caller that holds one never makes the store read it again (P3)."""

    model_config = ConfigDict(extra="forbid")

    events: list[BugEvent] = Field(default_factory=list)
    bugs: dict[str, TrackedBug] = Field(default_factory=dict)
    bad: list[BadEventFile] = Field(default_factory=list)


class RunOutcome(StrEnum):
    PROCESSED = "processed"
    NOT_FINISHED = "not_finished"
    WRONG_PROJECT = "wrong_project"


class RunReport(BaseModel):
    """What `process_run` did with one run. Counts are of events, not verdicts."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    outcome: RunOutcome
    verdicts: int = 0
    events_built: int = 0
    applied: int = 0
    duplicate: int = 0
    refused: list[str] = Field(default_factory=list, description="'<bug_key>: <reason>' per event")
    unjudged_cases: list[str] = Field(
        default_factory=list, description="cases whose verdict could not judge (nothing moved)")
    no_verdict_cases: list[str] = Field(
        default_factory=list, description="cases with a raw result and no verdict (nothing moved)")
    case_changed: list[str] = Field(
        default_factory=list, description="bug keys whose case was deleted or criterion changed")
    unverifiable: list[str] = Field(
        default_factory=list, description="bug keys whose rubric could not be loaded to compare")
    bad_files: list[BadEventFile] = Field(default_factory=list)
