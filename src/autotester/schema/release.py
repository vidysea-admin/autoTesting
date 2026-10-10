"""Release regression shapes: a flow's persisted plan, a run's scope, its record and diff.

One job — the typed rows a release run reads and writes (T-167, `release-regression.md`
RR3/RR6; the contract T-168's report layer reads). A `FlowPlan` is what a completed flow leaves
behind (the cases that validate it). A `ReleaseScope` freezes which plans one release executes,
so what a human confirmed is what runs. A `ReleaseRecord` is one release's durable outcome and
its ONE issues log; `RegressionDiff` is its comparison with the last trusted baseline. Nothing
here holds a verdict it computed: every `Result` in a record was returned by the grader
(`stages/grade.py`) and is copied, never decided, by the code that fills these.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from autotester.core.ids import content_hash
from autotester.schema.base import Artifact
from autotester.schema.enums import Result

BASELINE_RULE = "latest_earlier_finished_unflagged_all_pass_release"
"""RR3: the ONE rule naming 'the last trusted baseline'. A release R's baseline is the most
recent release created strictly before R that is `finished`, not `flagged_bad`, graded every
case in its frozen scope, and passed all of them. A release that fails any rule is skipped
(never 'whatever ran last'); with no such release R has no baseline and says so."""


def is_pass(result: Result) -> bool:
    """The single place a graded `Result` is read as 'passed' (never decided here)."""
    return result is Result.PASS


def issue_kind(result: Result) -> Literal["failed", "errored"]:
    """How a non-PASS graded `Result` reads in the log: FAIL is `failed`, the rest `errored`."""
    return "failed" if result is Result.FAIL else "errored"


def _unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


class FlowPlan(Artifact):
    """One flow's validation plan: the cases that decide whether the flow still works."""

    project: str = Field(min_length=1)
    flow_id: str = Field(min_length=1)
    case_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> FlowPlan:
        _unique(self.case_ids, "plan case ids")
        return self


class ReleaseScope(Artifact):
    """What one release executes, frozen when the run is first accepted (RR2/RR6)."""

    run_id: str = Field(min_length=1)
    project: str = Field(min_length=1)
    approval_id: str = Field(min_length=1)
    git_sha: str | None = None
    max_actions: int = Field(ge=1, description="the action total the approval must cover")
    wall_clock_s: float = Field(gt=0, description="the wall clock the approval must cover")
    expected_flow_ids: list[str] = Field(min_length=1)
    plans: list[FlowPlan] = Field(default_factory=list)
    unplanned_flow_ids: list[str] = Field(
        default_factory=list, description="flows with no plan; each is reported `not run`")

    @model_validator(mode="after")
    def _check(self) -> ReleaseScope:
        covered = [p.flow_id for p in self.plans] + self.unplanned_flow_ids
        _unique(covered, "scope flow ids")
        if set(covered) != set(self.expected_flow_ids):
            raise ValueError("scope must enumerate every expected flow exactly once")
        return self

    @property
    def case_ids(self) -> list[str]:
        return list(dict.fromkeys(c for p in self.plans for c in p.case_ids))

    @property
    def fingerprint(self) -> str:
        return content_hash(self.model_dump(mode="json", exclude={"created_at", "provenance"}))


class ReleaseDecision(BaseModel):
    """The human's answer to the `interrupt()` pause. It is NOT an approval (RR2)."""

    model_config = ConfigDict(extra="forbid")

    approved: StrictBool
    by: str = Field(min_length=1)
    note: str | None = None


class FlowOutcome(BaseModel):
    """One flow's line in the release log. `not_run` is never folded into `passed` (RR6)."""

    model_config = ConfigDict(extra="forbid")

    flow_id: str
    status: Literal["passed", "failed", "not_run"]
    case_ids: list[str] = Field(default_factory=list)


class ReleaseIssue(BaseModel):
    """One entry of the release's single issues log, always naming its flow (RR6)."""

    model_config = ConfigDict(extra="forbid")

    flow_id: str
    case_id: str | None = None
    kind: Literal["failed", "errored", "not_run", "regressed"]
    detail: str


class RegressionDiff(BaseModel):
    """This release against its trusted baseline (RR3). `baseline_run_id` None = no baseline."""

    model_config = ConfigDict(extra="forbid")

    baseline_rule: str = BASELINE_RULE
    baseline_run_id: str | None = None
    regressed: list[str] = Field(default_factory=list, description="PASS in baseline, not now")
    fixed: list[str] = Field(default_factory=list, description="not PASS in baseline, PASS now")
    new_cases: list[str] = Field(default_factory=list, description="no counterpart in baseline")
    note: str = ""


class ReleaseRecord(Artifact):
    """One release's durable outcome: per-flow results, ONE issues log and the diff."""

    run_id: str
    project: str
    approval_id: str
    git_sha: str | None = None
    scope: ReleaseScope
    finished: StrictBool = False
    flagged_bad: StrictBool = False
    flagged_reason: str | None = None
    results: dict[str, Result] = Field(default_factory=dict, description="case_id -> graded result")
    flows: list[FlowOutcome] = Field(default_factory=list)
    issues: list[ReleaseIssue] = Field(default_factory=list)
    diff: RegressionDiff = Field(default_factory=RegressionDiff)

    @model_validator(mode="after")
    def _check(self) -> ReleaseRecord:
        _unique([f.flow_id for f in self.flows], "record flow ids")
        if (self.scope.run_id, self.scope.project) != (self.run_id, self.project):
            raise ValueError("release record has foreign scope lineage")
        return self

    @property
    def is_trusted(self) -> bool:
        """RR3: eligible to be a baseline (see `BASELINE_RULE`)."""
        scope_cases = set(self.scope.case_ids)
        return bool(
            self.finished and not self.flagged_bad and not self.issues and scope_cases
            and set(self.results) == scope_cases and all(map(is_pass, self.results.values()))
            and self.flows and all(f.status == "passed" for f in self.flows))
