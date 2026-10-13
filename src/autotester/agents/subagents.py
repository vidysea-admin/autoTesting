"""The five subagents of the lead tester and the one place their tool allowlists live (T-180,
D-042, AL8-AL10): explorer, test-designer, runner, grader, reporter.

Each is a `SubagentSpec` with an EXPLICIT allowlist (a spec with none cannot be built). A
subagent is handed an `invocation` that holds its own prompt (a `SKILL.md`, AL4), the task text
and the files the lead chose to pass, never the lead's history nor another subagent's
transcript (AL9). `call_tool` is its only door to a tool: a name outside its allowlist is refused
before the dispatcher (and so any stage) is reached. The grader's list holds READ tools only,
checked at import (AL8, C7): it judges from the rubric and the evidence, and cannot act.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autotester.agents import tools
from autotester.agents.context import AgentContext
from autotester.providers.base import load_skill_prompt
from autotester.schema.agent_layer import (
    AgentToolName as T,
)
from autotester.schema.agent_layer import (
    RefusalClass,
    ToolEffect,
    ToolOutcome,
)
from autotester.schema.subagent import SubagentInvocation, SubagentName, SubagentSpec

SUBAGENTS: dict[SubagentName, SubagentSpec] = {
    SubagentName.EXPLORER: SubagentSpec(
        name=SubagentName.EXPLORER, skill="agent-explorer",
        description="Maps the product: runs a bounded crawl and reads the persona and catalog.",
        tools=(T.CRAWL, T.GET_PERSONA, T.GET_CATALOG)),
    SubagentName.TEST_DESIGNER: SubagentSpec(
        name=SubagentName.TEST_DESIGNER, skill="agent-test-designer",
        description="Designs cases from the persona and catalog; has no browser tool.",
        tools=(T.GET_PERSONA, T.GET_CATALOG)),
    SubagentName.RUNNER: SubagentSpec(
        name=SubagentName.RUNNER, skill="agent-runner",
        description="Executes stored cases in the browser; observes, never grades.",
        tools=(T.RUN_CASE,)),
    SubagentName.GRADER: SubagentSpec(
        name=SubagentName.GRADER, skill="agent-grader",
        description="Judges one executed case from its rubric and evidence only; cannot act.",
        tools=(T.READ_RESULT, T.READ_RUBRIC)),
    SubagentName.REPORTER: SubagentSpec(
        name=SubagentName.REPORTER, skill="agent-reporter",
        description="Writes up results and verdicts; has no browser tool.",
        tools=(T.GET_PERSONA, T.GET_CATALOG, T.READ_RESULT, T.READ_VERDICT)),
}
if set(SUBAGENTS) != set(SubagentName) or any(
        tools.TOOLS[t].effect is not ToolEffect.READ
        for t in SUBAGENTS[SubagentName.GRADER].tools):  # AL8: the grader reads, never acts
    raise RuntimeError("subagent table must hold all five, and the grader only READ tools")


def absent_tools(name: SubagentName) -> frozenset[T]:
    """Every tool of the full set that this subagent does NOT have (AL10)."""
    return frozenset(tools.TOOLS) - set(SUBAGENTS[name].tools)


def invocation(name: SubagentName, task: str, shared_files: dict[str, str] | None = None,
               *, skills_dir: Path | None = None) -> SubagentInvocation:
    """Build what ONE subagent sees (AL9): fresh, from its skill, the task and passed files."""
    spec = SUBAGENTS[name]
    return SubagentInvocation(
        subagent=name, system_prompt=load_skill_prompt(spec.skill, skills_dir=skills_dir),
        task=task, shared_files=dict(shared_files or {}), tools=spec.tools)


def call_tool(ctx: AgentContext, name: SubagentName, tool: Any, raw_args: Any) -> ToolOutcome:
    """A subagent's tool call: refused unless `tool` is on its allowlist, else the one
    dispatcher (guards and secret gate included). The refusal echoes no caller-supplied text."""
    allowed = {t.value for t in SUBAGENTS[name].tools}
    if not isinstance(tool, str) or tool not in allowed:
        return ToolOutcome(tool="unknown", ok=False, refusal=RefusalClass.NOT_ALLOWED,
                           summary="that tool is not on this subagent's allowlist")
    return tools.dispatch(ctx, tool, raw_args)


def deep_agents_config(name: SubagentName, *, skills_dir: Path | None = None) -> dict[str, Any]:
    """The plain dict a `create_deep_agent(subagents=[...])` entry is built from (T-179 owns
    the framework call): name, description, prompt and the allowlisted tool NAMES."""
    spec = SUBAGENTS[name]
    return {"name": spec.name.value, "description": spec.description,
            "system_prompt": load_skill_prompt(spec.skill, skills_dir=skills_dir),
            "tools": [t.value for t in spec.tools]}
