"""The machine-readable result of a run (T-174, CM2/CM4).

One job: `RegressionReport`, the single JSON document `autotester run|run-report --output json`
and the MCP `run_tests` / `get_report` tools return. It carries the run id, per-case outcomes,
verdict counts and evidence paths, and never a secret value (the builder scrubs it).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.enums import Outcome, Result


class CaseReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    outcome: Outcome | None = Field(default=None, description="what the executor observed")
    result: Result | None = Field(default=None, description="the grader's verdict, if graded")
    scoreboard: str = ""
    error: str | None = None
    evidence_paths: list[str] = Field(default_factory=list, description="run-relative files")


class RegressionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    run_id: str | None = Field(default=None, description="None for a dry run or a refusal")
    status: Literal["passed", "failed", "dry_run", "refused", "usage", "infra", "internal",
                    "inconclusive"]
    exit_code: int = Field(description="`core.exit_codes.ExitCode` value for this status")
    dry_run: bool = False
    message: str | None = None
    case_ids: list[str] = Field(default_factory=list, description="ran, or would run")
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    cases: list[CaseReport] = Field(default_factory=list)
