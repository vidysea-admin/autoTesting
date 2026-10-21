"""The lead tester's stage tools and their one dispatcher (T-179, AL2/AL3/AL6).

Every tool body is a thin call into the existing stage function named by its `ToolSpec.wraps`
(C3: nothing re-implemented). `dispatch` is the only entry a model reaches: it runs the secret
gate on the raw call, validates the tool name and arguments, lets the tool run its guards
(`agents/guards.py`) BEFORE any browser opens, and releases a scrubbed, re-gated outcome. A
refusal comes back as a `ToolOutcome`, never as something the model can argue with.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel, ValidationError

from autotester.agents import evidence_tools, guards, report_tools
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
    **evidence_tools.SPECS, **report_tools.SPECS}
ARGS: dict[Name, type[BaseModel]] = {
    Name.CRAWL: CrawlArgs, Name.RUN_CASE: RunCaseArgs, Name.GET_PERSONA: EmptyArgs,
    Name.GET_CATALOG: EmptyArgs, Name.GRADE_CASE: GradeCaseArgs,
    **evidence_tools.ARGS, **report_tools.ARGS}


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


_UNICODE_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def _carries_credential(ctx: AgentContext, data: dict[str, Any]) -> bool:
    """True if any DECODED string of `data` (a key or a leaf, also read with a literal
    backslash-u escape turned into its character) trips the secret gate, or `data` is past the
    call caps: what cannot be checked is withheld. Never the JSON text, where a TAB is a
    backslash-t and the fold never sees the separator."""
    try:
        for text in _call_texts("result", data)[1:]:
            for form in (text, _UNICODE_ESC.sub(lambda m: chr(int(m[1], 16)), text)):
                guards.guard_model_bound(ctx.secrets, form)
    except (ValueError, _Refused):
        return True
    return False


def _withhold_if_credential(ctx: AgentContext, model: BaseModel) -> None:
    """The release gate's own detector, applied BEFORE a write: nothing it would refuse (a
    reversed, encoded, folded or separator-split secret the exact-value scrub misses) is ever
    put on disk."""
    if _carries_credential(ctx, model.model_dump(mode="json")):
        raise _Refused(RefusalClass.SECRET,
                       "result withheld: it carried a credential; nothing was stored")


def _scrubbed(ctx: AgentContext, result: RawResult) -> RawResult:
    """Persist and return only scrubbed text (C5), whatever the stage let through."""
    cleaned = ctx.secrets.redactor().scrub_obj(result.model_dump(mode="json"))
    clean = RawResult.model_validate(cleaned)
    _withhold_if_credential(ctx, clean)
    return clean


def _run_case(ctx: AgentContext, args: RunCaseArgs) -> ToolOutcome:
    case = ctx.store.get_case(args.case_id)
    if case is None or not case.steps:
        raise _Refused(RefusalClass.NOTHING_TO_DO, "no such case, or it has no steps to run")
    refused = guards.write_policy_refusal(case, ctx.project)
    if refused is not None:
        raise _Refused(*refused)
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
                          redactor=ctx.secrets.redactor(),
                          mask_limit=ctx.project.image_mask_limit)
    _withhold_if_credential(ctx, verdict)
    ctx.store.save_verdict(ctx.run_id, verdict)
    return ToolOutcome(tool="grade_case", ok=True, artifact_ref=f"verdict:{case.id}",
                       summary=f"{verdict.result.value}: {verdict.scoreboard}")


_HANDLERS: dict[Name, Callable[[AgentContext, Any], ToolOutcome]] = {
    Name.CRAWL: _crawl, Name.RUN_CASE: _run_case, Name.GET_PERSONA: _get_persona,
    Name.GET_CATALOG: _get_catalog, Name.GRADE_CASE: _grade_case,
    **evidence_tools.HANDLERS, **report_tools.HANDLERS}


def _release(ctx: AgentContext, outcome: ToolOutcome) -> ToolOutcome:
    """Scrub, then gate, the one thing that goes back to the model (AL6)."""
    clean = outcome.model_copy(update={"summary": ctx.secrets.redactor().scrub(outcome.summary)})
    if _carries_credential(ctx, clean.model_dump(mode="json")):
        return _refusal(outcome.tool, RefusalClass.SECRET,
                        "result withheld: it carried a credential")
    return clean


def _validate(name: str, raw_args: dict[str, Any]) -> tuple[Name, BaseModel]:
    try:
        tool = Name(name)
    except ValueError:
        raise _Refused(RefusalClass.UNKNOWN_TOOL, "no such tool") from None
    try:
        return tool, ARGS[tool](**raw_args)
    except ValidationError as exc:  # type + location only: pydantic's text would echo the input
        bad = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['type']}" for e in exc.errors())
        raise _Refused(RefusalClass.BAD_ARGUMENTS, f"invalid arguments ({bad})") from None


_MAX_NAME, _MAX_CHARS, _MAX_NODES, _MAX_DEPTH = 100, 16_384, 256, 6


def _too_big() -> _Refused:
    return _Refused(RefusalClass.BAD_ARGUMENTS,
                    "arguments are too big, too deep or not plain data")


def _scalar_text(node: object) -> str | None:
    """The text of a leaf, `""` for a leaf that cannot hold a credential, None if not plain data."""
    if isinstance(node, str):
        return node
    if node is None or isinstance(node, bool):
        return ""
    if (isinstance(node, int) and node.bit_length() <= 256) or isinstance(node, float):
        return repr(node)
    return None


def _children(node: object) -> list[object]:
    """The keys and values of a container, size-checked BEFORE they are expanded."""
    if isinstance(node, dict):
        items = [*node, *node.values()]
    elif isinstance(node, (list, tuple)):
        items = list(node)
    else:
        return []
    if len(items) > _MAX_NODES:
        raise _too_big()
    return items


def _call_texts(name: object, raw_args: object) -> list[str]:
    """Every real string of a call (name, keys, leaves), bounded in size, depth and node count
    and walked iteratively, so hostile nesting can neither recurse nor stall the secret scan."""
    if not isinstance(name, str) or len(name) > _MAX_NAME:
        raise _Refused(RefusalClass.UNKNOWN_TOOL, "no such tool")
    if not isinstance(raw_args, dict):
        raise _Refused(RefusalClass.BAD_ARGUMENTS, "arguments must be an object")
    texts, chars, nodes = [name], len(name), 0
    stack: list[tuple[object, int]] = [(raw_args, 0)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if depth > _MAX_DEPTH or nodes > _MAX_NODES:
            raise _too_big()
        if isinstance(node, dict) and not all(isinstance(k, str) for k in node):
            raise _Refused(RefusalClass.BAD_ARGUMENTS, "argument names must be text")
        if isinstance(node, (dict, list, tuple)):
            stack.extend((child, depth + 1) for child in _children(node))
            continue
        text = _scalar_text(node)
        if text is None:
            raise _too_big()
        texts.append(text)
        chars += len(text)
        if chars > _MAX_CHARS:
            raise _too_big()
    return texts


def _stage_error(ctx: AgentContext, label: str, exc: Exception) -> ToolOutcome:
    """`ExcType: message` as a typed refusal: scrubbed, then gated WHOLE, then truncated (a cut
    encoded secret would escape a gate that ran after the cut)."""
    try:
        text = f"{type(exc).__name__}: {exc}"
    except Exception:  # a hostile __str__ must not become a raw escape
        text = type(exc).__name__
    text = ctx.secrets.redactor().scrub(text)
    if _carries_credential(ctx, {"error": text}):
        return _refusal(label, RefusalClass.SECRET, "result withheld: the error had a credential")
    return _refusal(label, RefusalClass.STAGE_ERROR, text[:300])


def _dispatch(ctx: AgentContext, name: object, raw_args: object) -> ToolOutcome:
    try:
        for text in _call_texts(name, raw_args):
            guards.guard_model_bound(ctx.secrets, text)
    except _Refused as refused:
        return _refusal("unknown", refused.kind, refused.detail)
    except ValueError:
        return _refusal("unknown", RefusalClass.SECRET,
                        "refused: the call carried a credential value; use {{SECRET:KEY}}")
    name, raw_args = cast(str, name), cast(dict[str, Any], raw_args)  # _call_texts proved both
    label = name if name in {n.value for n in Name} else "unknown"
    try:
        tool, args = _validate(name, raw_args)
        outcome = _HANDLERS[tool](ctx, args)
    except _Refused as refused:
        outcome = _refusal(label, refused.kind, refused.detail)
    except ApprovalRequired as exc:
        outcome = _refusal(label, RefusalClass.APPROVAL, str(exc))
    except Exception as exc:  # a stage, session or judge failure: typed, scrubbed, never raw
        outcome = _stage_error(ctx, label, exc)
    return _release(ctx, outcome)


def dispatch(ctx: AgentContext, name: Any, raw_args: Any) -> ToolOutcome:
    """Run one model-requested tool call. A refusal or failure is RETURNED, never raised, and
    carries no unscrubbed text and no caller-supplied name."""
    try:
        return _dispatch(ctx, name, raw_args)
    except Exception:  # last resort (never BaseException): a fixed typed result with no detail
        return _refusal("unknown", RefusalClass.STAGE_ERROR, "the tool call failed")
