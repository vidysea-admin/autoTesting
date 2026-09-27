"""What EXECUTE observed. Deliberately contains no judgement — see verdict.py."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.core.ids import run_id as _mint_run_id
from autotester.schema.base import Artifact
from autotester.schema.enums import EvidenceKind, Outcome, Trigger


class Evidence(BaseModel):
    """A file or value the grader may cite. Already redacted and masked."""

    model_config = ConfigDict(extra="forbid")

    kind: EvidenceKind
    path: str = Field(description="run-relative path, or the literal value for url/dom")
    step_order: int | None = None
    label: str | None = None
    masked: bool = Field(default=True, description="secrets removed before storage")


class ProviderUsage(BaseModel):
    """Token and call accounting per provider role — the cost story per run."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    role: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class RawResult(Artifact):
    """One case's execution record."""

    case_id: str
    outcome: Outcome
    used_script: bool = Field(default=False, description="False means the agent drove it")
    iterations: int = 1
    duration_s: float = 0.0
    error: str | None = None
    hitl_prompt: str | None = Field(default=None, description="what the human must supply")
    not_run_reason: str | None = Field(
        default=None,
        description="D-045/AT-581 (E6): set when case_class named an execution condition "
                    "(VIEWPORT_MOBILE/LOCALE_I18N) the executor could not enact -- outcome is "
                    "then NOT_RUN and this names why, never a silent default-condition PASS",
    )
    evidence: list[Evidence] = Field(default_factory=list)
    log_ref: str | None = None


class Run(Artifact):
    """One regression run over a set of cases."""

    id: str = Field(default_factory=_mint_run_id)
    project: str
    trigger: Trigger = Trigger.MANUAL
    git_sha: str | None = None
    label: str | None = None
    case_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    usage: list[ProviderUsage] = Field(default_factory=list)
    parallel_n: int | None = Field(
        default=None,
        description="T-173/D-041: cases that ran concurrently in this run; None means the run "
                    "predates parallel execution or was not eligible for it",
    )
    parallel_bound_by: Literal["config", "budget", "write_policy"] | None = Field(
        default=None,
        description="which term chose parallel_n -- project.max_parallel ('config'), the "
                    "measured RAM/CPU budget ('budget'), or a forced serial fallback because "
                    "write_policy is allow_writes ('write_policy')",
    )
