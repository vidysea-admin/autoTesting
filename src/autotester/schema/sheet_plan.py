"""The shapes of a tracker-sheet sync PLAN (T-199b dry run; contract TB9, TB10, TB11, TB13 in part).

Its one job is the shapes. A `SheetPlan` is the exact cells a sync would write and nothing more: it
is computed from the open bugs and one read of the sheet, shown to a human, and carries a hash of
its own content, so a plan that changed after it was shown cannot be mistaken for the one that was
confirmed. A `PlanConfirmation` names a person and a plan hash; it is not a first-live-write
record (`qa/gates/t199-first-live-write.md` is open and no such record exists in this slice).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.core.ids import content_id
from autotester.schema.tracked_bug import no_control

OWNED_FIELDS = ("bug_key", "title", "severity", "screen", "status", "assignee", "first_seen",
                "last_seen", "count")
"""The only bug fields a sync may write. A sheet column mapped to none of them is never touched."""

_PERSON_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.@/+-]{0,79}")


class SheetColumns(BaseModel):
    """Which sheet column holds which bug field. The mapping is an input here; proposing and
    confirming it from the header row is TB8, not built in this slice."""

    model_config = ConfigDict(extra="forbid")

    sheet_id: str = Field(min_length=1, max_length=200)
    tab: str = Field(min_length=1, max_length=100)
    columns: dict[str, str] = Field(description="bug field -> the sheet's header text")

    @field_validator("sheet_id", "tab")
    @classmethod
    def _no_control(cls, value: str) -> str:
        return no_control(value, "sheet_id/tab")

    @model_validator(mode="after")
    def _valid(self) -> SheetColumns:
        if "bug_key" not in self.columns:
            raise ValueError("the bug_key column must be mapped: rows are located by it")
        if bad := sorted(set(self.columns) - set(OWNED_FIELDS)):
            raise ValueError(f"not an owned bug field: {bad}")
        headers = list(self.columns.values())
        if any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
            raise ValueError("every mapped header must be non-empty and used once")
        return self


class SheetState(BaseModel):
    """One read of the sheet's tab: the header row and the data rows under it (row 2 onward)."""

    model_config = ConfigDict(extra="forbid")

    header: list[str]
    rows: list[list[str]] = Field(default_factory=list)


class CellChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column: str
    before: str
    after: str


class CellConflict(BaseModel):
    """A cell a human changed since we wrote it. It is reported and never overwritten (TB10)."""

    model_config = ConfigDict(extra="forbid")

    column: str
    sheet_has: str
    we_last_wrote: str | None
    we_would_write: str


class PlanRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["append", "update", "conflict"]
    bug_key: str
    row_number: int | None = Field(default=None, description="sheet row; None for an append")
    changes: list[CellChange] = Field(default_factory=list)
    conflicts: list[CellConflict] = Field(default_factory=list)
    note: str | None = None

    @property
    def cells(self) -> dict[str, str]:
        """Exactly the cells this row writes: column header -> new value."""
        return {c.column: c.after for c in self.changes}


class SheetPlan(BaseModel):
    """What a sync would write. `plan_hash` is derived from the content and checked on load."""

    model_config = ConfigDict(extra="forbid")

    sheet_id: str
    tab: str
    rows: list[PlanRow] = Field(default_factory=list)
    unchanged: int = Field(default=0, ge=0, description="bugs whose row already matches")
    plan_hash: str = ""

    @model_validator(mode="after")
    def _hash(self) -> SheetPlan:
        derived = content_id("plan", {"sheet": self.sheet_id, "tab": self.tab,
                                      "rows": [r.model_dump(mode="json") for r in self.rows]})
        if self.plan_hash and self.plan_hash != derived:
            raise ValueError("plan_hash does not match the plan's content")
        self.plan_hash = derived
        return self

    @property
    def writes(self) -> list[PlanRow]:
        return [r for r in self.rows if r.action != "conflict"]


class SyncMemory(BaseModel):
    """What we last wrote, per bug and column, so a later human edit is told from our own value."""

    model_config = ConfigDict(extra="forbid")

    written: dict[str, dict[str, str]] = Field(default_factory=dict)


def check_person(value: str) -> str:
    """A named person, never the machine actor. The one rule for every confirmation."""
    if not _PERSON_RE.fullmatch(value) or value.lower().startswith("system"):
        raise ValueError("a confirmation names a person, not the machine")
    return value


class PlanConfirmation(BaseModel):
    """A named person saw the plan with this hash. Whether that person holds `project.edit` is
    T-204's check; this slice only requires a named user, never the machine actor."""

    model_config = ConfigDict(extra="forbid")

    plan_hash: str = Field(min_length=1)
    confirmed_by: str
    confirmed_at: datetime

    @field_validator("confirmed_by")
    @classmethod
    def _person(cls, value: str) -> str:
        return check_person(value)

    @field_validator("confirmed_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("a confirmation time must carry a timezone")
        return value
