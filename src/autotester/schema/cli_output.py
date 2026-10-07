"""The machine contract of the CLI and the MCP server: the exit-code table and the one
document `--output json` (and every MCP tool) prints. Contract: qa/contracts/cli-mcp.md.

Defined here once. `cli_run.py` mirrors the table in `--help`; nothing else spells a code.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.enums import Outcome, Result


class ExitCode(IntEnum):
    """What a pipeline may act on differently (CM1). `doctor` keeps its 0/1."""

    OK = 0
    TEST_FAILED = 1
    USAGE = 2
    RUN_REFUSED = 3
    INFRASTRUCTURE = 4
    INTERNAL = 5


EXIT_CODE_MEANING: dict[ExitCode, str] = {
    ExitCode.OK: "every case passed (or a read / dry run succeeded)",
    ExitCode.TEST_FAILED: "the run finished and at least one case did not pass",
    ExitCode.USAGE: "bad arguments, unknown project or run, nothing to run",
    ExitCode.RUN_REFUSED: "no valid RunApproval covers this run; nothing started",
    ExitCode.INFRASTRUCTURE: "provider, browser, network or timeout failure",
    ExitCode.INTERNAL: "an unexpected error inside AutoTester",
}

ReportStatus = Literal[
    "passed", "failed", "dry_run", "usage_error", "refused", "infrastructure_error",
    "internal_error",
]


class CaseOutcome(BaseModel):
    """One case's line in a report: what happened, how it was judged, where the evidence is."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str = ""
    outcome: Outcome | None = None
    result: Result | None = Field(default=None, description="None means never graded")
    failures: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)


class RunReport(BaseModel):
    """The single JSON document on stdout. Every string in it has passed `Redactor.scrub` (C5)."""

    model_config = ConfigDict(extra="forbid")

    project: str
    status: ReportStatus
    exit_code: int
    dry_run: bool = False
    run_id: str | None = None
    message: str | None = None
    planned_case_ids: list[str] = Field(default_factory=list)
    cases: list[CaseOutcome] = Field(default_factory=list)
    counts: dict[str, int] = Field(
        default_factory=dict, description="verdict result -> cases; NOT_GRADED for a case no "
                                          "grader judged (never counted as a pass)")
