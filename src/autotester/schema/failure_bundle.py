"""Failure-bundle shapes (T-178, qa/contracts/failure-bundle.md FB1-FB3).

A bundle is one directory describing one failing case in one run. `BundleSource`
is a candidate artifact offered to the assembler, stamped with the run it came
from (FB2); `BundleManifest` is the `manifest.json` written last, listing every
file with its run id and hash so a loader can prove the bundle complete (FB1).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

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


class BundleManifest(Artifact):
    """`manifest.json`: written last, so its presence plus matching hashes is completeness."""

    bundle_id: str
    run_id: str
    case_id: str
    failing_step: int | None = None
    steps_included: list[int] = Field(default_factory=list)
    files: list[BundleFile] = Field(default_factory=list)
