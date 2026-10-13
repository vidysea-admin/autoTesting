"""The agent-vs-pipeline comparison report (T-179 AL12/AL13): the four north-star axes for each
path, and the verdict line that is present whichever way the numbers went."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class PathMeasure(BaseModel):
    """What one path produced on the SAME corpus. All four numbers are measured, not estimated;
    a path that did not record one carries None (shown, never hidden)."""

    model_config = ConfigDict(extra="forbid")

    label: str
    bugs_found: int
    false_positives: int
    tokens: int | None
    wall_s: float | None


class Comparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus_id: str
    pipeline: PathMeasure
    agent: PathMeasure
    agent_stopped: str
    verdict: Literal["gain", "no_gain"]
    verdict_line: str
