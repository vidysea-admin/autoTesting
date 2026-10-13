"""The lead tester built on Deep Agents (T-179, AL1/AL4/AL5/AL6/AL7/AL11).

`build_lead_agent` is the one `create_deep_agent` call: the stage tools (each a thin door into
`agents/tools.py::dispatch`, guards inside), the judgement subagents (`agents/subagents.py`
allowlists, each given only its own tools through `subagents.call_tool`), the `agent-lead` prompt
and the skill folders via `skills=`. The planner is the framework's (to-do list middleware); this
module plans nothing.

One middleware (`Rails`) sits on the lead's and every subagent's model and tool calls:
AL6 the model-bound secret gate on every message, AL11 the token/cost meter that HALTS the run,
AL5 one `ToolSpan` per planning step, tool call and delegation on the run's own `trace.jsonl`,
AL7 refusal of a delegation that is not a judgement step. `run_lead_agent` drives one task.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool

from autotester.agents import guards, subagents, tools
from autotester.agents.budget import BudgetExceeded, Meter
from autotester.agents.context import AgentContext
from autotester.agents.lead import JUDGEMENT, LEAD_SKILL
from autotester.core.trace import TraceWriter
from autotester.providers.base import load_skill_prompt
from autotester.schema.agent_layer import AgentToolName, RefusalClass, ToolOutcome
from autotester.schema.lead_loop import AgentRun, TokenBudget
from autotester.schema.subagent import SubagentName

_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
_TOOL_NAMES = {t.value for t in AgentToolName}


class Rails(AgentMiddleware):  # type: ignore[type-arg]
    """Secret gate, budget, trace and delegation rule on every call the framework makes."""

    def __init__(self, ctx: AgentContext, meter: Meter) -> None:
        super().__init__()
        self.ctx, self.meter, self.seq, self.plan_seq = ctx, meter, 0, 0
        self.tool_calls = self.delegations = self.refusals = 0
        self.trace = TraceWriter(ctx.store.paths.run_trace(ctx.run_id), ctx.run_id,
                                 ctx.secrets.redactor())

    def _span(self, op: str, name: str, began: float, ok: bool = True,
              refusal: str | None = None) -> None:
        self.trace.record_tool(seq=self.seq, op=op, name=name, ok=ok, refusal=refusal,
                               parent_seq=None if op == "plan" else self.plan_seq,
                               duration_s=time.monotonic() - began)
        if op == "plan":
            self.plan_seq = self.seq
        self.seq += 1

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        began = time.monotonic()
        self.meter.check()  # a run already over budget makes no further model call
        request = request.override(messages=[self._clean(m) for m in request.messages])
        texts = [request.system_message.text] if request.system_message else []
        for message in request.messages:
            texts += [str(message.content), json.dumps(getattr(message, "tool_calls", None))]
        for text in texts:
            guards.guard_model_bound(self.ctx.secrets, text)  # AL6: ValueError halts the run
        response = handler(request)
        for message in response.result:
            self.meter.add_message(message)
        self._span("plan", "lead", began)
        self.meter.check()  # AL11: the breach halts before the reply is acted on
        return response

    def _clean(self, message: Any) -> Any:
        """The model's own earlier tool-call arguments, scrubbed: a refused call that carried a
        credential must not come back to it (or a subagent) in the history (AL6)."""
        calls = getattr(message, "tool_calls", None)
        if not calls:
            return message
        scrub = self.ctx.secrets.redactor().scrub_obj
        return message.model_copy(update={"tool_calls": [
            {**c, "args": scrub(c.get("args") or {})} for c in calls]})

    def _refuse(self, call: dict[str, Any], op: str, who: str, began: float, kind: str,
                text: str) -> ToolMessage:
        self.refusals += 1
        self._span(op, who, began, False, kind)
        return ToolMessage(content=text, tool_call_id=call["id"], name=call["name"],
                           status="error")

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        began, call = time.monotonic(), request.tool_call
        name, args = str(call.get("name")), call.get("args") or {}
        is_task = name == "task"
        who, op = (str(args.get("subagent_type", "")), "delegate") if is_task else (name, "tool")
        if is_task and who not in JUDGEMENT:  # AL7: a mechanical step is never delegated
            return self._refuse(call, op, "delegate", began, RefusalClass.BAD_ARGUMENTS.value,
                                "not delegated: that is a mechanical step; call the tool directly")
        try:
            guards.guard_model_bound(self.ctx.secrets, json.dumps(args, default=str))
        except ValueError:
            return self._refuse(call, op, who, began, RefusalClass.SECRET.value,
                                "refused: the call carried a credential value")
        reply = handler(request)
        try:  # a framework tool may answer with a state `Command`, which has no content
            outcome = ToolOutcome.model_validate_json(str(getattr(reply, "content", "")))
        except ValueError:
            outcome = None
        ok = getattr(reply, "status", "success") != "error" and (outcome is None or outcome.ok)
        self.refusals += not ok
        self.delegations += is_task and ok
        self.tool_calls += (not is_task) and name in _TOOL_NAMES
        self._span(op, who, began, ok, outcome.refusal.value if outcome and outcome.refusal
                   else None)
        return reply


def _stage_tool(ctx: AgentContext, name: AgentToolName, owner: SubagentName | None) -> BaseTool:
    """One tool object. The lead's door is the dispatcher; a subagent's is `call_tool`, which
    refuses anything off its allowlist. Both return the `ToolOutcome` as JSON, never raise."""
    spec = tools.TOOLS[name]

    def run(**kwargs: Any) -> str:
        if owner is None:
            return tools.dispatch(ctx, name.value, kwargs).model_dump_json()
        return subagents.call_tool(ctx, owner, name.value, kwargs).model_dump_json()

    return StructuredTool.from_function(func=run, name=name.value, description=spec.description,
                                        args_schema=tools.ARGS[name])


def lead_tools(ctx: AgentContext) -> list[BaseTool]:
    return [_stage_tool(ctx, n, None) for n in tools.TOOLS]


def _subagent_dicts(ctx: AgentContext, rails: Rails, skills_dir: Path | None) -> list[Any]:
    """The judgement subagents only (the `runner` is a mechanical step, AL7): each with its own
    prompt and ONLY its allowlisted tools (AL10), under the same rails."""
    out = []
    for name in SubagentName:
        if name.value not in JUDGEMENT:
            continue
        cfg = subagents.deep_agents_config(name, skills_dir=skills_dir)
        cfg["tools"] = [_stage_tool(ctx, AgentToolName(t), name) for t in cfg["tools"]]
        cfg["middleware"] = [rails]
        out.append(cfg)
    return out


def build_lead_agent(ctx: AgentContext, model: BaseChatModel, *, budget: TokenBudget | None = None,
                     skills_dir: Path | None = None) -> tuple[Any, Rails]:
    """The one `create_deep_agent` call (AL1). Returns the compiled agent and its rails."""
    rails = Rails(ctx, Meter(budget))
    agent = create_deep_agent(
        model=model, tools=lead_tools(ctx),
        middleware=[TodoListMiddleware(), rails],  # the framework planner (AL1)
        system_prompt=load_skill_prompt(LEAD_SKILL, skills_dir=skills_dir),
        subagents=_subagent_dicts(ctx, rails, skills_dir),
        skills=["/"],  # the SK1 folders under the backend root below (AL4)
        # the packaged skills are read-only to the model: no write, edit or delete anywhere
        permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
        backend=FilesystemBackend(root_dir=skills_dir or _SKILLS_DIR, virtual_mode=True))
    return agent, rails


def run_lead_agent(ctx: AgentContext, model: BaseChatModel, task: str, *,
                   budget: TokenBudget | None = None, skills_dir: Path | None = None,
                   max_graph_steps: int = 60) -> AgentRun:
    """Drive one task to the end. A budget breach is a HALT with a named reason (AL11); a
    secret-gate hit or model failure is `model_error` with nothing echoed."""
    agent, rails = build_lead_agent(ctx, model, budget=budget, skills_dir=skills_dir)
    stopped, reason, summary = "finished", "", ""
    try:
        state = agent.invoke({"messages": [HumanMessage(task)]},
                             config={"recursion_limit": max_graph_steps})
        summary = ctx.secrets.redactor().scrub(str(state["messages"][-1].content))[:500]
    except BudgetExceeded as exc:
        stopped, reason = "budget_exceeded", str(exc)
        rails.trace.record_tool(seq=rails.seq, op="plan", name="budget", ok=False,
                                refusal="budget_exceeded")
    except Exception as exc:  # a gate hit or model failure: stop, never echo the text
        capped = type(exc).__name__ == "GraphRecursionError"
        stopped = "step_cap" if capped else "model_error"
        reason = "graph step cap reached" if capped else type(exc).__name__
    return AgentRun(run_id=ctx.run_id, stopped=stopped, reason=reason,  # type: ignore[arg-type]
                    tokens_used=rails.meter.tokens, tool_calls=rails.tool_calls,
                    delegations=rails.delegations, refusals=rails.refusals, summary=summary)
