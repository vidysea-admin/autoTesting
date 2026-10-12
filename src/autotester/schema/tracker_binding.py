"""The shapes of a project's tracker-sheet binding (T-199c; contract TB8, TB9, TB12, TB13, TB14).

Its one job is the shapes. A `TrackerBinding` ties one project to one sheet and tab, holds the
column mapping (`proposed` until a named person confirms it, `stale` when the header moved), the
first-write confirmation against a plan hash, and the last sync outcome. It is stored per project
(`ProjectPaths.tracker_file`) and carries its project slug, so project A's binding can never be
read as project B's. Nothing here reaches a sheet; the fake client in tests is the only one.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.sheet_plan import PlanConfirmation, SyncMemory, check_person
from autotester.schema.tracked_bug import no_control

MAPPED_FIELDS = ("title", "severity", "screen", "status", "assignee", "date", "screenshot_link",
                 "bug_key")
"""What a mapping proposes columns for. `date` is written as `first_seen`; `screenshot_link` is
proposed and kept but nothing writes it yet (no authenticated link exists in a plan)."""


class MappingStatus(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    STALE = "stale"


class ColumnMapping(BaseModel):
    """Which header cell holds which field. Inert until `confirmed` (TB8)."""

    model_config = ConfigDict(extra="forbid")

    status: MappingStatus = MappingStatus.PROPOSED
    columns: dict[str, str] = Field(default_factory=dict, description="field -> header text")
    positions: dict[str, int] = Field(default_factory=dict, description="field -> header index")
    unmapped: dict[str, list[str]] = Field(
        default_factory=dict, description="field -> candidate headers (empty: none found)")
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None

    @field_validator("confirmed_by")
    @classmethod
    def _person(cls, value: str | None) -> str | None:
        return None if value is None else check_person(value)

    @model_validator(mode="after")
    def _consistent(self) -> ColumnMapping:
        if set(self.columns) & set(self.unmapped):
            raise ValueError("a field is either mapped or unmapped, not both")
        if bad := sorted((set(self.columns) | set(self.unmapped)) - set(MAPPED_FIELDS)):
            raise ValueError(f"not a mappable field: {bad}")
        if self.status is MappingStatus.CONFIRMED and not (self.confirmed_by and self.confirmed_at):
            raise ValueError("a confirmed mapping records who and when")
        if self.status is MappingStatus.PROPOSED and (self.confirmed_by or self.confirmed_at):
            raise ValueError("a proposed mapping has no confirmer")
        return self


class ConflictNote(BaseModel):
    """A cell a human edited: listed on the tracker page, never overwritten (TB10)."""

    model_config = ConfigDict(extra="forbid")

    bug_key: str
    column: str
    sheet_has: str


class SyncState(BaseModel):
    """The last sync outcome, visible to `report.view` holders (TB12). `last_error` is scrubbed."""

    model_config = ConfigDict(extra="forbid")

    sync_status: Literal["never", "ok", "error"] = "never"
    last_error: str | None = None
    last_attempt_at: datetime | None = None
    retry_at: datetime | None = None
    plan_hash: str | None = None
    rows_planned: int = Field(default=0, ge=0)
    conflicts: list[ConflictNote] = Field(default_factory=list)
    written: bool = Field(default=False, description="always False in the dry-run slice")


class MappingReply(BaseModel):
    """The model fallback's answer: field -> a header cell it was shown, or None."""

    model_config = ConfigDict(extra="forbid")

    matches: dict[str, str | None] = Field(default_factory=dict)


class TrackerBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    sheet_id: str = Field(min_length=1, max_length=200)
    tab: str = Field(min_length=1, max_length=100)
    mapping: ColumnMapping = Field(default_factory=ColumnMapping)
    first_write: PlanConfirmation | None = Field(
        default=None, description="who confirmed which plan hash; None until a person does")
    memory: SyncMemory = Field(default_factory=SyncMemory)
    sync: SyncState = Field(default_factory=SyncState)

    @field_validator("sheet_id", "tab")
    @classmethod
    def _clean(cls, value: str) -> str:
        return no_control(value, "sheet_id/tab")
