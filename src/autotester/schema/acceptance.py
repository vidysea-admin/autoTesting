"""The T-136 acceptance-comparison artifact: AutoTester vs a human tester, as data.

Every measure is a number copied from `BenchTrial.score` or an explicit
unavailable marker (bench.md K8) -- never a default. Nothing here records who
won; that verdict is Umesh's and lives outside this artifact (K9).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.base import Artifact


class Measure(BaseModel):
    """One reported measurement: exactly one of a value or an unavailable reason."""

    model_config = ConfigDict(extra="forbid")

    value: float | None = Field(default=None, allow_inf_nan=False)
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> Measure:
        """A missing input is never a zero; a number never carries a reason."""
        if (self.value is None) == (self.unavailable_reason is None):
            raise ValueError("a measure is either a value or an unavailable reason")
        return self

    def text(self) -> str:
        """Human-readable form used by the CLI."""
        if self.value is None:
            return f"unavailable ({self.unavailable_reason})"
        return f"{self.value:.4g}"


class ParticipantColumn(BaseModel):
    """One side of the comparison, with its K6 kind and K7 ordering split."""

    model_config = ConfigDict(extra="forbid")

    participant: Literal["autotester", "human"]
    present: bool
    absent_reason: str | None = None
    label: str = ""
    kind: str = "unknown"
    ordering: str = "unknown"
    findings_reported: int = 0
    independent_findings: int = 0
    prompted_findings: int = 0
    crawl_findings: int = 0
    crawl_ids_scanned: list[str] = Field(default_factory=list)
    detected: int = 0
    seeded: int = 0
    detection_rate: Measure
    false_positive_rate: Measure
    severity_weighted_recall: Measure
    duration_s: Measure
    false_positive_population: str = "all_reported_findings"
    denominator_population: str = "unknown"


class BugRow(BaseModel):
    """One ground-truth bug and which participants found it."""

    model_config = ConfigDict(extra="forbid")

    bug_id: str
    description: str
    severity: str
    provenance: str
    found_by: list[str] = Field(default_factory=list)


class AcceptanceComparison(Artifact):
    """The comparison a reader who was not there can judge (bench.md K9)."""

    id: str
    project: str
    corpus_id: str
    corpus_mode: str
    # Provenance of the recall denominator, always printed beside recall (bench.md K12).
    recall_basis: str = "unknown"
    human_list: Literal["present", "absent"]
    # True when no human list exists: every finding then counts as a false positive.
    fp_rate_unadjudicated: bool
    autotester: ParticipantColumn
    human: ParticipantColumn
    bugs: list[BugRow] = Field(default_factory=list)
    bugs_unavailable_reason: str | None = None
    verdict: str = "not computed here: Umesh records the verdict on this artifact"
