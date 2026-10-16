"""Failure-bundle shapes (T-178, qa/contracts/failure-bundle.md FB1-FB3).

A bundle is one directory describing one failing case in one run. `BundleSource`
is a candidate artifact offered to the assembler, stamped with the run it came
from (FB2); `BundleManifest` is the `manifest.json` written last, listing every
file with its run id and hash so a loader can prove the bundle complete (FB1).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.schema.base import Artifact


class BundleFileKind(StrEnum):
    CASE = "case"
    VERDICT = "verdict"
    RESULT = "result"
    ERROR = "error"
    STEP = "step"
    SCREENSHOT = "screenshot"
    TRACE = "trace"


class BundleSource(BaseModel):
    """One screenshot offered to the assembler, stamped with its originating run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    path: Path = Field(description="screenshot file on disk the assembler may copy")
    step_order: int
    masked: bool = Field(
        default=False,
        description="accepted only when secret inputs were masked at capture (Evidence.masked)",
    )


class BundleFile(BaseModel):
    """One file inside a finished bundle."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="bundle-relative posix path")
    kind: BundleFileKind
    run_id: str
    sha256: str
    step_order: int | None = None

    @field_validator("name")
    @classmethod
    def _bundle_relative_name(cls, value: str) -> str:
        parts = value.split("/")
        if (not value or "\\" in value or ":" in value or "\x00" in value
                or PurePosixPath(value).is_absolute()
                or any(part in {"", ".", ".."} for part in parts)):
            raise ValueError("bundle file must have a relative POSIX name without traversal")
        return value


class BundleManifest(Artifact):
    """`manifest.json`: written last, so its presence plus matching hashes is completeness."""

    bundle_id: str
    run_id: str
    case_id: str
    failing_step: int | None = None
    failing_step_source: Literal["recorded", "explicit", "heuristic_fallback"] | None = Field(
        default=None,
        description="AT-787: where failing_step came from; heuristic_fallback = no recorded step",
    )
    steps_included: list[int] = Field(default_factory=list)
    files: list[BundleFile] = Field(default_factory=list)


class BundleAssembly(BaseModel):
    """A case's assembly outcome; visual shortfalls never imply full image coverage."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    bundle_id: str | None = Field(default=None, pattern=r"^fb_[A-Za-z0-9]+$")
    status: Literal["complete", "unavailable"]
    diagnostic: Literal["assembly_failed", "image_text_unavailable"] | None = None
    image_text_unavailable: bool = False
    images_requested: int = Field(default=0, ge=0)
    images_included: int = Field(default=0, ge=0)
    images_withheld: int = Field(default=0, ge=0)
    image_reasons: list[str] = Field(default_factory=list)


class BundleIndex(Artifact):
    """Typed run-local lookup, nested below bundles/ to avoid result-file discovery."""

    run_id: str
    cases: list[BundleAssembly] = Field(default_factory=list)
