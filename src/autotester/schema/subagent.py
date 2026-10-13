"""The shape of one subagent of the lead tester (T-180, D-042, AL8-AL10): its name, the skill
that is its prompt, and the EXPLICIT tool allowlist it is configured with.

`tools` has `min_length=1`: a subagent built with no list is refused here, so none can inherit
"all tools" by default. The allowlist lives in one place (`agents/subagents.py::SUBAGENTS`).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.agent_layer import AgentToolName


class SubagentName(StrEnum):
    EXPLORER = "explorer"
    TEST_DESIGNER = "test-designer"
    RUNNER = "runner"
    GRADER = "grader"
    REPORTER = "reporter"


class SubagentSpec(BaseModel):
    """One subagent. Frozen: the allowlist cannot be widened after construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: SubagentName
    description: str = Field(min_length=1, description="what the lead reads to choose it")
    skill: str = Field(min_length=1, description="folder under skills/ whose body is its prompt")
    tools: tuple[AgentToolName, ...] = Field(min_length=1)


class SubagentInvocation(BaseModel):
    """What ONE subagent is handed (AL9): its own prompt, the task text, the files the lead
    deliberately passed, and its tool names. There is no field for the lead's history or for
    another subagent's transcript."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subagent: SubagentName
    system_prompt: str
    task: str
    shared_files: dict[str, str] = Field(default_factory=dict)
    tools: tuple[AgentToolName, ...]
