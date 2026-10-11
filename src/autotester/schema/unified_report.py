"""The damage-control report's typed shape: one run's four evidence classes plus crawl coverage.

One job — the rows `stages/unified_report.py` fills and `stages/unified_report_render.py` draws
(T-168, `damage-control-report.md` DC1-DC4). Every value here is COPIED from the owner that
produced it (the release record, first-party network evidence, the run's verdicts, the persona's
revisions, the crawl's own coverage rows); nothing is computed for the report (DC2). Each section
carries `unavailable`: the reason its input is missing, so a gap reads as "unavailable: why" and
never as an empty list that looks like a clean bill of health (C12).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.portal_persona import PersonaRevision
from autotester.schema.release import FlowOutcome, RegressionDiff, ReleaseIssue


class _Section(BaseModel):
    """A report section; `unavailable` set means its input does not exist, with the reason."""

    model_config = ConfigDict(extra="forbid")

    unavailable: str | None = Field(default=None, description="why this section has no data")


class RegressionSection(_Section):
    """RR3/RR6: the release's single issues log and its diff against the trusted baseline."""

    release_run_id: str | None = None
    git_sha: str | None = None
    finished: bool = False
    flagged_bad: bool = False
    flagged_reason: str | None = None
    diff: RegressionDiff = Field(default_factory=RegressionDiff)
    flows: list[FlowOutcome] = Field(default_factory=list)
    issues: list[ReleaseIssue] = Field(default_factory=list)


class ApiFailure(BaseModel):
    """One first-party response the product answered badly (NA1). `status` None = unreadable."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="`run:<case_id>` or `crawl:<crawl_id>`")
    method: str | None = None
    url: str | None = None
    status: int | None = None
    raw: str = Field(description="the evidence row exactly as stored (already scrubbed)")


class ApiSection(_Section):
    failures: list[ApiFailure] = Field(default_factory=list)
    sources_read: list[str] = Field(
        default_factory=list, description="which evidence sets were actually read")


class FailureLine(BaseModel):
    """RE6: one unmet criterion, verbatim off the stored verdict."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    reason: str
    fix_hint: str | None = None


class CaseLine(BaseModel):
    """One case of the run. `result` is the grader's word, or `not run` / `no verdict`."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    flow_id: str | None = None
    result: str
    outcome: str | None = None
    scoreboard: str = ""
    reason: str | None = Field(default=None, description="why it did not run / was not graded")
    failures: list[FailureLine] = Field(default_factory=list)
    repro_steps: list[str] = Field(default_factory=list)


class WorkflowSection(_Section):
    run_id: str | None = None
    cases: list[CaseLine] = Field(default_factory=list)


class RevisionLine(BaseModel):
    """One dated persona revision with the CR4 counts its owner produced."""

    model_config = ConfigDict(extra="forbid")

    revision: PersonaRevision
    counts: dict[str, int] = Field(description="`PersonaRevision.counts()`, copied")


class HistorySection(_Section):
    revisions: list[RevisionLine] = Field(default_factory=list, description="newest first")


class CoverageSection(_Section):
    """DC1: the crawl's own figure and reason breakdown, the same rows the crawl page shows."""

    crawl_id: str | None = None
    rows: list[tuple[str, str]] = Field(default_factory=list)
    unreached: list[tuple[str, str]] = Field(
        default_factory=list, description="(reason, what) for every control/screen not exercised")
    incomplete: bool = Field(
        default=True, description="True unless the crawl's own record shows full coverage; "
                                  "an incomplete section is never drawn green")


class UnifiedReport(Artifact):
    """One invocation's report: all four data classes, one artifact (DC3)."""

    project: str
    run_id: str
    regression: RegressionSection
    api: ApiSection
    workflows: WorkflowSection
    history: HistorySection
    coverage: CoverageSection
