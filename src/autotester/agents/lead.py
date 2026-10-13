"""The lead tester's loop (T-179c, AL4/AL5/AL7): a model returns one step per turn, the loop runs
it through the ONE dispatcher (`agents/tools.py::dispatch`, guards inside) or hands a judgement
step to a subagent, and writes a trace span for each.

The loop plans nothing itself: the model (behind `LeadModel`) does. It is the executor the
framework call (`create_deep_agent`, AL1) will sit over, and takes the same three things: the
`agent-lead` skill (AL4, via the one skill loader), the dispatcher, and a `Delegator` seam that
t180's subagents (`agents/subagents.py`) fill. Nothing here imports t180.

Safety held here (AL6): the system prompt, every transcript line and every delegated task or file
passes the model-bound secret gate before it leaves; a failing model or delegator is a stop or a
typed refusal, never raw text.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pydantic import TypeAdapter

from autotester.agents import guards, tools
from autotester.agents.context import AgentContext
from autotester.core.trace import TraceWriter
from autotester.providers.base import load_skill_prompt
from autotester.schema.agent_layer import RefusalClass, ToolOutcome
from autotester.schema.lead_loop import DelegateStep, FinishStep, LeadRun, LeadStep, ToolCallStep

LEAD_SKILL = "agent-lead"
JUDGEMENT = frozenset({"explorer", "test-designer", "grader", "reporter"})
# Roles that need judgement. Anything else (the `runner`, a single `run_case`) is a plain tool
# call and is never delegated (rule 2, AL7).
_STEP: TypeAdapter[ToolCallStep | DelegateStep | FinishStep] = TypeAdapter(LeadStep)


class LeadModel(Protocol):
    def next_step(self, system: str, transcript: Sequence[str]) -> object:
        """The next `LeadStep` (or a dict of one) given the system prompt and the turns so far."""


class Delegator(Protocol):
    def delegate(self, subagent: str, task: str, shared_files: dict[str, str]) -> str:
        """Run one subagent on a fresh context; return its final text."""


def lead_skills(skills_dir: Path | None = None) -> list[Path]:
    """The skill folders the framework's `skills=` argument is given (AL4)."""
    base = skills_dir or Path(__file__).resolve().parents[1] / "skills"
    return [base / LEAD_SKILL]


def _delegate(ctx: AgentContext, step: DelegateStep, delegator: Delegator | None) -> ToolOutcome:
    def refuse(kind: RefusalClass, why: str) -> ToolOutcome:
        return ToolOutcome(tool="delegate", ok=False, refusal=kind, summary=why)
    if step.subagent not in JUDGEMENT:
        return refuse(RefusalClass.BAD_ARGUMENTS,
                      "not delegated: that is a mechanical step; call the tool directly")
    if delegator is None:
        return refuse(RefusalClass.NOTHING_TO_DO, "no subagents are configured")
    try:
        for text in (step.task, *step.shared_files, *step.shared_files.values()):
            guards.guard_model_bound(ctx.secrets, text)
    except ValueError:
        return refuse(RefusalClass.SECRET, "refused: the task carried a credential value")
    try:
        said = ctx.secrets.redactor().scrub(
            delegator.delegate(step.subagent, step.task, dict(step.shared_files)))
        guards.guard_model_bound(ctx.secrets, said)
    except ValueError:
        return refuse(RefusalClass.SECRET, "result withheld: it carried a credential")
    except Exception:  # a failing subagent is a typed refusal, never raw text
        return refuse(RefusalClass.STAGE_ERROR, "the subagent failed")
    return ToolOutcome(tool="delegate", ok=True, summary=said[:1000])


def run_lead(ctx: AgentContext, model: LeadModel, delegator: Delegator | None = None, *,
             max_steps: int = 20, skills_dir: Path | None = None) -> LeadRun:
    """Drive the loop to a finish, the step cap, or a model failure. Every planning step, tool
    call and delegation writes one `ToolSpan` (AL5) to the run's own `trace.jsonl`."""
    trace = TraceWriter(ctx.store.paths.run_trace(ctx.run_id), ctx.run_id,
                        ctx.secrets.redactor())
    system = load_skill_prompt(LEAD_SKILL, skills_dir=skills_dir)
    transcript: list[str] = []
    run, seq = LeadRun(run_id=ctx.run_id, stopped="step_cap"), 0
    while run.steps < max_steps:
        began, plan_seq = time.monotonic(), seq
        try:
            for text in (system, *transcript):
                guards.guard_model_bound(ctx.secrets, text)
            step = _STEP.validate_python(model.next_step(system, tuple(transcript)))
        except Exception:  # a bad step, a gate hit or a model failure: stop, never echo
            trace.record_tool(seq=seq, op="plan", name="lead", ok=False, refusal="model_error",
                              duration_s=time.monotonic() - began)
            run.stopped = "model_error"
            break
        trace.record_tool(seq=seq, op="plan", name="lead", duration_s=time.monotonic() - began)
        seq, run.steps = seq + 1, run.steps + 1
        if isinstance(step, FinishStep):
            run.stopped, run.summary = "finished", ctx.secrets.redactor().scrub(step.summary)[:500]
            break
        began = time.monotonic()
        if isinstance(step, ToolCallStep):
            outcome, op, name = tools.dispatch(ctx, step.tool, step.args), "tool", step.tool
            run.tool_calls += 1
        else:
            outcome, op, name = _delegate(ctx, step, delegator), "delegate", "delegate"
            if outcome.ok:
                run.delegations += 1
            name = step.subagent if step.subagent in JUDGEMENT else "delegate"
        run.refusals += not outcome.ok
        trace.record_tool(seq=seq, op=op, name=outcome.tool if op == "tool" else name,
                          ok=outcome.ok, refusal=outcome.refusal and outcome.refusal.value,
                          parent_seq=plan_seq, duration_s=time.monotonic() - began)
        seq += 1
        transcript.append(outcome.model_dump_json())
    return run
