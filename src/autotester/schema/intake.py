"""Shapes for video intake: zip limits, the per-member report, and where a source came from.

Contract: qa/contracts/team-intake.md TI2 (named caps), TI3/TI5 (the report), TI11 (origin).
The default upload limit is defined once, in `schema/server_settings.py`; `core/upload_limit.py`
is the one accessor that reads the admin setting.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from autotester.schema.base import utc_now


class IntakeOutcome(StrEnum):
    """Exactly one of these per zip member that is listed (TI3)."""

    REGISTERED = "registered"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"
    FAILED = "failed"


class IntakeStatus(StrEnum):
    """Overall result. `partial` is never reported as `ok` (TI5)."""

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class ZipLimits(BaseModel):
    """The archive-level caps beside the per-file one (which is the admin upload limit).

    Checker-chosen defaults from TI2: 1000 entries, 20 videos, 10 GB uncompressed, 5 GB
    archive, 100:1 ratio. They live only here, never as literals in the expansion code."""

    model_config = ConfigDict(extra="forbid")

    max_entries: int = Field(default=1000, gt=0)
    max_videos: int = Field(default=20, gt=0)
    max_total_bytes: int = Field(default=10 * 1000**3, gt=0)
    max_archive_bytes: int = Field(default=5 * 1000**3, gt=0)
    max_ratio: int = Field(default=100, gt=0)
    ratio_min_bytes: int = Field(
        default=1024**2, ge=0,
        description="the ratio cap applies only to members declared larger than this: a "
                    "small member cannot be a bomb, and tiny repetitive files compress highly")


class UploadOrigin(BaseModel):
    """A file picked in the browser; `file_name` is the name the client sent."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["upload"] = "upload"
    file_name: str


class ZipOrigin(BaseModel):
    """A member of a zip: the archive's name and the member's path inside it."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["zip"] = "zip"
    archive_name: str
    member_path: str


class DriveOrigin(BaseModel):
    """A Google Drive file, by its id (never its name or a link carrying a token)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["drive"] = "drive"
    file_id: str


SourceOrigin = Annotated[UploadOrigin | ZipOrigin | DriveOrigin, Field(discriminator="kind")]
"""Exactly one of the three shapes (TI11)."""


class MemberResult(BaseModel):
    """One row of the per-member table the CLI prints and the Add-videos page shows."""

    model_config = ConfigDict(extra="forbid")

    member: str
    outcome: IntakeOutcome
    reason: str | None = None
    source_id: str | None = None
    duplicate_of: str | None = None


class IntakeReport(BaseModel):
    """What one zip intake did. `exit_code` is 0 only when nothing failed."""

    model_config = ConfigDict(extra="forbid")

    archive: str
    status: IntakeStatus
    members: list[MemberResult] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exit_code(self) -> int:
        return 0 if self.status is IntakeStatus.OK else 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def counts(self) -> dict[str, int]:
        return {o.value: sum(1 for m in self.members if m.outcome is o) for o in IntakeOutcome}


class DriveRef(BaseModel):
    """A pasted Drive link or bare id, parsed to the only thing that is ever used: the id.
    `kind` is what the link shape says (`unknown` for a bare id; the metadata decides)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: Literal["file", "folder", "unknown"] = "unknown"


class DriveItem(BaseModel):
    """One Drive file's metadata as Drive reports it. `name` is untrusted text: it may become
    a scrubbed label, never part of a path (TI4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str = ""
    mime_type: str = ""
    size: int | None = None
    md5: str | None = None


class IntakeActor(BaseModel):
    """Who the sign-in gate says is adding videos (TI10, TI11). `email` is None until T-204's
    sign-in exists: the row is then owned by nobody, never by a form field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: str | None = None


class DriveJob(BaseModel):
    """One pasted Drive link being fetched in the background (HO33). Holds the Drive id and the
    finished report, never the pasted link or anything `gws` printed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    project: str
    state: Literal["queued", "fetching", "done", "refused", "failed"] = "queued"
    drive_id: str | None = None
    message: str | None = None
    report: IntakeReport | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
