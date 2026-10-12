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
