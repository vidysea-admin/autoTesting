"""The lead tester's stage tools and their one dispatcher (T-179, AL2/AL3/AL6).

Every tool body is a thin call into the existing stage function named by its `ToolSpec.wraps`
(C3: nothing re-implemented). `dispatch` is the only entry a model reaches: it runs the secret
gate on the raw call, validates the tool name and arguments, lets the tool run its guards
(`agents/guards.py`) BEFORE any browser opens, and releases a scrubbed, re-gated outcome. A
refusal comes back as a `ToolOutcome`, never as something the model can argue with.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from autotester.agents import guards
from autotester.agents.context import AgentContext
from autotester.browser.observe import PageObserver
from autotester.core.consent import ApprovalRequired
from autotester.schema.agent_layer import (
    AgentToolName as Name,
)
from autotester.schema.agent_layer import (
    CrawlArgs,
    EmptyArgs,
    GradeCaseArgs,
    RefusalClass,
    RunCaseArgs,
    ToolEffect,
    ToolOutcome,
    ToolSpec,
)
from autotester.schema.crawl import CrawlBounds
from autotester.schema.run import RawResult
from autotester.stages import catalog, execute, explore, grade

_PERSONA = "autotester.store.project_store.ProjectStore.load_portal_persona"
TOOLS: dict[Name, ToolSpec] = {
    Name.CRAWL: ToolSpec(
        name=Name.CRAWL, effect=ToolEffect.ACTING, wraps="autotester.stages.explore.run_crawl",
        description="Bounded crawl of the project; needs a covering approval."),
    Name.RUN_CASE: ToolSpec(
        name=Name.RUN_CASE, effect=ToolEffect.ACTING, wraps="autotester.stages.execute.run_case",
        description="Execute one stored case in the browser; observes only."),
    Name.GET_PERSONA: ToolSpec(
        name=Name.GET_PERSONA, effect=ToolEffect.READ, wraps=_PERSONA,
        description="Read the durable portal persona."),
    Name.GET_CATALOG: ToolSpec(
        name=Name.GET_CATALOG, effect=ToolEffect.READ, wraps="autotester.stages.catalog.catalog",
        description="Read which case classes can run, and what blocks the rest."),
    Name.GRADE_CASE: ToolSpec(
        name=Name.GRADE_CASE, effect=ToolEffect.GRADING, wraps="autotester.stages.grade.grade",
        description="Judge one executed case in a fresh context."),
}
_ARGS: dict[Name, type[BaseModel]] = {
    Name.CRAWL: CrawlArgs, Name.RUN_CASE: RunCaseArgs, Name.GET_PERSONA: EmptyArgs,
    Name.GET_CATALOG: EmptyArgs, Name.GRADE_CASE: GradeCaseArgs,
}


class _Refused(Exception):
    def __init__(self, kind: RefusalClass, detail: str) -> None:
        super().__init__(detail)
        self.kind, self.detail = kind, detail


def _refusal(tool: str, kind: RefusalClass, detail: str) -> ToolOutcome:
    return ToolOutcome(tool=tool, ok=False, refusal=kind, summary=detail)


def _crawl(ctx: AgentContext, args: CrawlArgs) -> ToolOutcome:
    asked = {"max_actions": args.max_actions, "wall_clock_s": args.wall_clock_s}
    bounds = CrawlBounds(**{k: v for k, v in asked.items() if v is not None})
    guards.crawl_approval(ctx.store, ctx.project, bounds)
    observer = PageObserver()
    login = ctx.store.get_case(ctx.project.login_case_id) if ctx.project.login_case_id else None
    with ctx.open_session(observer) as session:
        crawl = explore.run_crawl(ctx.project, session, ctx.store, observer=observer,
                                  bounds=bounds, login_case=login, incremental=args.incremental)
    return ToolOutcome(tool="crawl", ok=True, artifact_ref=f"crawl:{crawl.id}",
                       summary=f"{crawl.status.value}: {crawl.screens} screens, "
                               f"{crawl.actions} actions")


def _scrubbed(ctx: AgentContext, result: RawResult) -> RawResult:
    """Persist and return only scrubbed text (C5), whatever the stage let through."""
    cleaned = ctx.secrets.redactor().scrub_obj(result.model_dump(mode="json"))
    return RawResult.model_validate(cleaned)


def _run_case(ctx: AgentContext, args: RunCaseArgs) -> ToolOutcome:
    case = ctx.store.get_case(args.case_id)
    if case is None or not case.steps:
        raise _Refused(RefusalClass.NOTHING_TO_DO, "no such case, or it has no steps to run")
    why = guards.write_policy_refusal(case, ctx.project)
    if why is not None:
        raise _Refused(RefusalClass.WRITE_POLICY, why)
    guards.live_case_approval(ctx.store, ctx.project, case)
    with ctx.open_session(None) as session:
        result = _scrubbed(ctx, execute.run_case(case, session))
    ctx.store.save_result(ctx.run_id, result)
    return ToolOutcome(tool="run_case", ok=True, artifact_ref=f"result:{case.id}",
                       summary=f"outcome {result.outcome.value}"
                               + (f": {result.error}" if result.error else ""))


def _get_persona(ctx: AgentContext, _args: EmptyArgs) -> ToolOutcome:
    persona = ctx.store.load_portal_persona()
    if persona is None:
        raise _Refused(RefusalClass.NOTHING_TO_DO, "no portal persona yet; a crawl builds one")
    return ToolOutcome(tool="get_persona", ok=True, artifact_ref=f"persona:{persona.project}",
                       summary=f"{len(persona.screens)} screens, "
                               f"{len(persona.taught_flows)} flows, {len(persona.gotchas)} gotchas")


def _get_catalog(ctx: AgentContext, _args: EmptyArgs) -> ToolOutcome:
    cat = catalog.catalog(ctx.project, ctx.store.load_flowspec(), ctx.store)
    runnable = sum(1 for e in cat.entries if e.runnable)
    return ToolOutcome(tool="get_catalog", ok=True, artifact_ref=f"catalog:{cat.project}",
                       summary=f"{runnable} of {len(cat.entries)} case classes runnable")


def _grade_case(ctx: AgentContext, args: GradeCaseArgs) -> ToolOutcome:
    case = ctx.store.get_case(args.case_id)
    rubric = ctx.store.load_rubric(case.rubric_ref) if case and case.rubric_ref else None
    result = next((r for r in ctx.store.load_results(ctx.run_id) if r.case_id == args.case_id),
                  None)
    if case is None or rubric is None or result is None:
        raise _Refused(RefusalClass.NOTHING_TO_DO, "needs a stored case, its rubric and a result")
    verdict = grade.grade(rubric, result, ctx.run_id, ctx.judge, ctx.docs,
                          run_dir=ctx.store.paths.run_dir(ctx.run_id), secrets=ctx.secrets,
                          redactor=ctx.secrets.redactor())
    ctx.store.save_verdict(ctx.run_id, verdict)
    return ToolOutcome(tool="grade_case", ok=True, artifact_ref=f"verdict:{case.id}",
                       summary=f"{verdict.result.value}: {verdict.scoreboard}")


_HANDLERS: dict[Name, Callable[[AgentContext, Any], ToolOutcome]] = {
    Name.CRAWL: _crawl, Name.RUN_CASE: _run_case, Name.GET_PERSONA: _get_persona,
    Name.GET_CATALOG: _get_catalog, Name.GRADE_CASE: _grade_case,
}


def _release(ctx: AgentContext, outcome: ToolOutcome) -> ToolOutcome:
    """Scrub, then gate, the one thing that goes back to the model (AL6)."""
    clean = outcome.model_copy(update={"summary": ctx.secrets.redactor().scrub(outcome.summary)})
    try:
        guards.guard_model_bound(ctx.secrets, clean.model_dump_json())
    except ValueError:
        return _refusal(outcome.tool, RefusalClass.SECRET,
                        "result withheld: it carried a credential")
    return clean


def _validate(name: str, raw_args: dict[str, Any]) -> tuple[Name, BaseModel]:
    try:
        tool = Name(name)
    except ValueError:
        raise _Refused(RefusalClass.UNKNOWN_TOOL, "no such tool") from None
    try:
        return tool, _ARGS[tool](**raw_args)
    except ValidationError as exc:  # type + location only: pydantic's text would echo the input
        bad = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['type']}" for e in exc.errors())
        raise _Refused(RefusalClass.BAD_ARGUMENTS, f"invalid arguments ({bad})") from None


def dispatch(ctx: AgentContext, name: str, raw_args: dict[str, Any]) -> ToolOutcome:
    """Run one model-requested tool call. A refusal is returned, never raised."""
    try:
        guards.guard_model_bound(ctx.secrets, f"{name} {raw_args!r}")
    except ValueError:
        return _refusal("unknown", RefusalClass.SECRET,
                        "refused: the call carried a credential value; use {{SECRET:KEY}}")
    known = name in {n.value for n in Name}
    label = name if known else "unknown"
    try:
        tool, args = _validate(name, raw_args)
        outcome = _HANDLERS[tool](ctx, args)
    except _Refused as refused:
        outcome = _refusal(label, refused.kind, refused.detail)
    except ApprovalRequired as exc:
        outcome = _refusal(label, RefusalClass.APPROVAL, str(exc))
    return _release(ctx, outcome)
