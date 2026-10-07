"""Shapes for video intake: zip limits, the per-member report, and where a source came from.

Contract: qa/contracts/team-intake.md TI2 (named caps), TI3/TI5 (the report), TI11 (origin).
The ONE definition of the default upload limit lives here; `core/upload_limit.py` reads the
admin setting and falls back to it, and T-203's server settings reuse it as their default.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

DEFAULT_MAX_UPLOAD_BYTES = 2 * 1024**3
"""Admin `max_upload_bytes` default: 2 GiB per video (D-072#10, hosting.md HO15)."""


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
