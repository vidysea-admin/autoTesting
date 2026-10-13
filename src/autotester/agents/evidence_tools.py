"""The read-only evidence tools (T-180, AL8): `read_result`, `read_rubric`, `read_verdict`.

They give the grader and the reporter something to look at without a way to act. Each is a thin
read of the store (C3: nothing re-implemented); none opens a browser, writes, or calls a stage.
Registered into the one dispatcher (`agents/tools.py`), so the secret gate and the scrub apply.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from autotester.agents.context import AgentContext
from autotester.schema.agent_layer import (
    AgentToolName as Name,
)
from autotester.schema.agent_layer import (
    ReadCaseArgs,
    RefusalClass,
    ToolEffect,
    ToolOutcome,
    ToolSpec,
)

_STORE = "autotester.store.project_store.ProjectStore."
SPECS: dict[Name, ToolSpec] = {
    Name.READ_RESULT: ToolSpec(
        name=Name.READ_RESULT, effect=ToolEffect.READ, wraps=_STORE + "load_results",
        description="Read the stored outcome and evidence labels of one executed case."),
    Name.READ_RUBRIC: ToolSpec(
        name=Name.READ_RUBRIC, effect=ToolEffect.READ, wraps=_STORE + "load_rubric",
        description="Read the criteria and no-fire list of one case's rubric."),
    Name.READ_VERDICT: ToolSpec(
        name=Name.READ_VERDICT, effect=ToolEffect.READ, wraps=_STORE + "load_verdicts",
        description="Read the stored verdict of one case in this run."),
}
ARGS: dict[Name, type[BaseModel]] = {n: ReadCaseArgs for n in SPECS}


def _missing(what: str) -> ToolOutcome:
    return ToolOutcome(tool="unknown", ok=False, refusal=RefusalClass.NOTHING_TO_DO,
                       summary=f"no stored {what} for that case")


def _read_result(ctx: AgentContext, args: ReadCaseArgs) -> ToolOutcome:
    result = next((r for r in ctx.store.load_results(ctx.run_id) if r.case_id == args.case_id),
                  None)
    if result is None:
        return _missing("result").model_copy(update={"tool": "read_result"})
    labels = ", ".join(f"{e.kind.value}:{e.label or e.path}" for e in result.evidence[:20])
    return ToolOutcome(tool="read_result", ok=True, artifact_ref=f"result:{args.case_id}",
                       summary=f"outcome {result.outcome.value}; error {result.error or 'none'}; "
                               f"evidence [{labels}]")


def _read_rubric(ctx: AgentContext, args: ReadCaseArgs) -> ToolOutcome:
    case = ctx.store.get_case(args.case_id)
    rubric = ctx.store.load_rubric(case.rubric_ref) if case and case.rubric_ref else None
    if rubric is None:
        return _missing("rubric").model_copy(update={"tool": "read_rubric"})
    criteria = "; ".join(f"{c.id}: {c.text}" for c in rubric.criteria)
    return ToolOutcome(tool="read_rubric", ok=True, artifact_ref=f"rubric:{rubric.id}",
                       summary=f"criteria [{criteria}]; no-fire [{'; '.join(rubric.no_fire)}]")


def _read_verdict(ctx: AgentContext, args: ReadCaseArgs) -> ToolOutcome:
    verdict = next((v for v in ctx.store.load_verdicts(ctx.run_id) if v.case_id == args.case_id),
                   None)
    if verdict is None:
        return _missing("verdict").model_copy(update={"tool": "read_verdict"})
    return ToolOutcome(tool="read_verdict", ok=True, artifact_ref=f"verdict:{args.case_id}",
                       summary=f"{verdict.result.value}: {verdict.scoreboard}")


HANDLERS: dict[Name, Callable[[AgentContext, Any], ToolOutcome]] = {
    Name.READ_RESULT: _read_result, Name.READ_RUBRIC: _read_rubric,
    Name.READ_VERDICT: _read_verdict,
}
