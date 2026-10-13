"""The steps a lead-tester model may return, and what a finished loop reports (T-179 AL5/AL7).

A model returns ONE `LeadStep` per turn: call a stage tool, delegate a judgement step to a
subagent by name, or finish. The loop (`agents/lead.py`) owns everything else.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolCallStep(_Step):
    kind: Literal["tool"] = "tool"
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class DelegateStep(_Step):
    kind: Literal["delegate"] = "delegate"
    subagent: str
    task: str
    shared_files: dict[str, str] = Field(default_factory=dict)


class FinishStep(_Step):
    kind: Literal["finish"] = "finish"
    summary: str = ""


LeadStep = Annotated[ToolCallStep | DelegateStep | FinishStep, Field(discriminator="kind")]


class LeadRun(BaseModel):
    """What one lead loop did. `delegations` counts subagent calls actually made (AL7)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    stopped: Literal["finished", "step_cap", "model_error"]
    steps: int = 0
    tool_calls: int = 0
    delegations: int = 0
    refusals: int = 0
    summary: str = ""


class TokenBudget(BaseModel):
    """A run's declared ceiling (AL11): tokens and/or cost. Either left unset is not enforced."""

    model_config = ConfigDict(extra="forbid")

    max_tokens: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, gt=0)
    usd_per_million_tokens: float = Field(default=0.0, ge=0)
    """Price used to turn tokens into cost; with 0 the cost ceiling can never trip."""


class AgentRun(BaseModel):
    """How one framework-driven lead run ended. `stopped` names the reason, so a budget halt is
    distinguishable from completion, an error and an approval block (AL11)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    stopped: Literal["finished", "budget_exceeded", "model_error", "step_cap"]
    reason: str = ""
    tokens_used: int = 0
    tool_calls: int = 0
    delegations: int = 0
    refusals: int = 0
    summary: str = ""
