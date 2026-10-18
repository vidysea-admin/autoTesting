"""The CEO-benchmark scorecard: counts and a hash, never a finding (MP29, MP30, MPI6).

One job: the committed shape of the scorecard. Every number in it is read from
`BenchTrial.score` by `stages/ceo_benchmark.py`; this file only holds them. It has no field that
could carry a finding's text or an identifier of one: totals, ratios, the list's sha256 and the
per-technique state are all that exist, so a scorecard written to a committed file is safe by
construction. A measure that cannot be computed is a `Measure` with a reason, never a zero.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.acceptance import Measure
from autotester.schema.ceo_inputs import SHA256_PATTERN, Technique

OrderingDetail = Literal[
    "recorded", "not recorded", "list hash differs from the recorded one",
    "list committed after run start",
]


class RecallLine(BaseModel):
    """A recall value with the counts it came from (`detected` of `total` in the population)."""

    model_config = ConfigDict(extra="forbid")

    measure: Measure
    detected: int = Field(ge=0)
    total: int = Field(ge=0)

    def text(self) -> str:
        """`0.5 (3/6)`, or `unavailable (<reason>)`."""
        if self.measure.value is None:
            return self.measure.text()
        return f"{self.measure.text()} ({self.detected}/{self.total})"


class TechniqueLine(BaseModel):
    """One recall line per CEO technique, naming the units that own it (MPI6)."""

    model_config = ConfigDict(extra="forbid")

    technique: Technique
    owner_units: list[str]
    state: Literal["ran", "not run"]
    recall: RecallLine | None = Field(
        default=None, description="None when the technique's owner did not run: never a zero")

    def text(self) -> str:
        """`<technique> (T-211, T-215): not run` or the recall text."""
        owners = ", ".join(self.owner_units)
        shown = "not run" if self.recall is None else self.recall.text()
        return f"{self.technique.value} ({owners}): {shown}"


class CeoScorecard(BaseModel):
    """The whole scorecard. Priorities are keyed `P0`, `P1`, `P2` (P0 first)."""

    model_config = ConfigDict(extra="forbid")

    atomic_count: int = Field(ge=0)
    atomic_sha256: str = Field(pattern=SHA256_PATTERN)
    ordering: OrderingDetail
    findings_total: int = Field(ge=0)
    matched: int = Field(ge=0)
    adjudicated_false_positives: int = Field(ge=0)
    unadjudicated: int = Field(ge=0)
    derived_excluded: int = Field(ge=0, description="atomic findings dropped from recall because "
                                  "a derived-from-finding scenario matched them")
    recall_overall: RecallLine
    recall_by_priority: dict[str, RecallLine]
    recall_excluding_seeded_data: RecallLine
    false_positive_rate: Measure
    wall_time_s: Measure
    techniques: list[TechniqueLine]
