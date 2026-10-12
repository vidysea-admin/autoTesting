"""The shape of a human's pointer file once parsed (T-197 / TV1).

A pointer is a reviewer's hint about WHERE in a recording to look harder. It never
narrows what is analysed (TV2); a line that does not parse is kept as an error with
its line number, never dropped (TV1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PointerLine(BaseModel):
    """One accepted line. `kind` is `time` (one second), `window` (a range) or `free`
    (no time: applies to the whole recording)."""

    model_config = ConfigDict(extra="forbid")

    line_no: int = Field(ge=1, description="1-based physical line number in the file")
    kind: Literal["time", "window", "free"]
    start_s: float | None = None
    end_s: float | None = Field(default=None, description="set only for kind=window")
    approx: bool = Field(default=False, description="the reviewer wrote `~`")
    text: str | None = Field(default=None, description="the free-text note, when any")


class PointerError(BaseModel):
    """One refused line. The raw text is deliberately not kept: it may carry a secret."""

    model_config = ConfigDict(extra="forbid")

    line_no: int = Field(ge=1)
    reason: str


class PointerParse(BaseModel):
    """Everything a pointer file said. Count identity (TV1):
    `len(parsed) + len(errors) == non_blank_lines`, for every input."""

    model_config = ConfigDict(extra="forbid")

    parsed: list[PointerLine] = Field(default_factory=list)
    errors: list[PointerError] = Field(default_factory=list)
    non_blank_lines: int = 0
