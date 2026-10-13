"""T-179d: the Deep Agents lead tester end to end (AL1-AL7, AL11-AL13), offline.

A scripted chat model stands in for the LLM (no live model call, no browser); the framework
(`create_deep_agent`) runs for real around it. AL3/AL6 stage-level cases are in
`test_agent_tools.py`/`test_agent_read_only.py`; here the same refusals are driven THROUGH the
framework, and the middleware rails (budget, trace, delegation rule, secret gate) are proven."""

from __future__ import annotations

import ast
import importlib
import shutil
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from test_agent_tools import (
    RAW,
    Spies,
    _case,
    _ctx,
    _grant,
    _nav,
    spies,  # noqa: F401  (the fixture, re-exposed under the same name)
)

from autotester.agents import lead_agent, report_tools, tools
from autotester.agents.budget import Meter
from autotester.core.trace import read_tool_spans
from autotester.schema.agent_layer import AgentToolName as T
from autotester.schema.agent_layer import ToolEffect
from autotester.schema.enums import (
    Action,
    ApprovalKind,
    EvidenceKind,
    Outcome,
    WritePolicy,
)
from autotester.schema.flowspec import Step
from autotester.schema.lead_loop import AgentRun, TokenBudget
from autotester.schema.run import Evidence, RawResult

AGENT_SRC = Path(lead_agent.__file__)


class Scripted(BaseChatModel):
    """Replies from a script, one per model call (lead and subagents share it). Records what it
    was shown. `tokens` is the usage each reply reports."""

    script: list[AIMessage]
    tokens: int = 10
    seen: list[str] = Field(default_factory=list)

    def _generate(self, messages: Any, stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        self.seen.append(repr(messages))
        reply = self.script.pop(0) if self.script else AIMessage("done")
        reply.usage_metadata = {"input_tokens": 0, "output_tokens": self.tokens,
                                "total_tokens": self.tokens}
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def bind_tools(self, tools: Any, **kwargs: Any) -> Scripted:
        return self

    @property
    def _llm_type(self) -> str:
        return "scripted"


def call(name: str, **args: Any) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": f"c-{name}-{len(args)}"}])


def delegate(who: str, task: str = "design the cases") -> AIMessage:
    return call("task", description=task, subagent_type=who)


def run(ctx: Any, *script: AIMessage, **kw: Any) -> tuple[AgentRun, Scripted]:
    model = Scripted(script=[*script, AIMessage("all done")])
    return lead_agent.run_lead_agent(ctx, model, "test the product", **kw), model


@pytest.fixture
def ctx(tmp_path: Path, spies: Spies) -> Any:  # noqa: F811
    return _ctx(tmp_path, spies, WritePolicy.READ_ONLY)


# -- AL1 ------------------------------------------------------------------------------------
def test_al1_built_with_create_deep_agent_and_the_decided_version_floor() -> None:
    assert "create_deep_agent(" in AGENT_SRC.read_text(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    assert "deepagents>=0.7.24,<0.8" in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_al1_the_agent_has_the_framework_planner_and_it_plans(ctx: Any) -> None:
    model = Scripted(script=[call("write_todos", todos=[{"content": "map", "status": "pending"}]),
                             AIMessage("planned")])
    agent, _ = lead_agent.build_lead_agent(ctx, model)
    state = agent.invoke({"messages": [("user", "go")]})
    assert state["todos"] == [{"content": "map", "status": "pending"}]


# -- AL1b (read-only skills) and AL2 ---------------------------------------------------------
def test_al1_the_model_cannot_write_into_the_packaged_skills(ctx: Any, tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    shutil.copytree(Path(lead_agent.__file__).resolve().parents[1] / "skills", skills)
    before = (skills / "agent-lead" / "SKILL.md").read_bytes()
    out, _ = run(ctx, call("write_file", file_path="/agent-lead/SKILL.md", content="evil"),
                 skills_dir=skills)
    assert out.stopped == "finished"
    assert (skills / "agent-lead" / "SKILL.md").read_bytes() == before
    assert not (skills / "agent-lead" / "SKILL.md").read_bytes().startswith(b"evil")


def test_al2_every_stage_is_a_tool_and_wraps_a_real_existing_function() -> None:
    assert {"crawl", "run_case", "get_persona", "get_catalog", "grade_case", "report",
            "capture_network"} <= {t.value for t in tools.TOOLS}
    for spec in tools.TOOLS.values():
        module, _, attr = spec.wraps.rpartition(".")
        owner = importlib.import_module(module) if not module.endswith("ProjectStore") else (
            importlib.import_module(module.rpartition(".")[0]).ProjectStore)
        assert callable(getattr(owner, attr)), spec.name


def test_al2_report_and_capture_network_call_their_stage_once(ctx: Any,
                                                              monkeypatch: Any) -> None:
    seen: list[str] = []
    real = report_tools.network_capture.first_party_evidence
    monkeypatch.setattr(report_tools.network_capture, "first_party_evidence",
                        lambda *a, **k: (seen.append("net"), real(*a, **k))[1])
    ctx.store.save_result("run-1", RawResult(case_id="c1", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.NETWORK, path="GET https://app.test/api/x -> 500"),
        Evidence(kind=EvidenceKind.NETWORK, path="GET https://ads.other/p -> 200")]))
    out = tools.dispatch(ctx, "capture_network", {"case_id": "c1"})
    assert out.ok and seen == ["net"] and out.summary.startswith("1 first-party calls, 1 with")
    assert tools.dispatch(ctx, "report", {}).ok
    for name in (T.REPORT, T.CAPTURE_NETWORK):
        assert tools.TOOLS[name].effect is ToolEffect.READ  # neither acts


# -- AL3: the same three refusals, driven through the framework ------------------------------
def test_al3a_a_secret_in_a_tool_call_is_refused_and_never_reaches_a_browser(
        ctx: Any, spies: Spies) -> None:  # noqa: F811
    out, model = run(ctx, call("run_case", case_id=RAW))
    assert out.refusals == 1 and spies.sessions == 0
    spans = read_tool_spans(ctx.store.paths.run_trace(ctx.run_id))
    assert [s.refusal for s in spans if s.op == "tool"] == ["secret"]
    assert RAW not in "".join(model.seen)


def test_al3b_a_crawl_without_approval_is_refused_before_a_browser(
        ctx: Any, spies: Spies) -> None:  # noqa: F811
    out, _ = run(ctx, call("crawl", max_actions=5000))
    spans = read_tool_spans(ctx.store.paths.run_trace(ctx.run_id))
    assert [s.refusal for s in spans if s.op == "tool"] == ["approval"]
    assert out.refusals == 1 and spies.sessions == 0 and spies.count("run_crawl") == 0


def test_al3c_a_write_under_read_only_is_refused_by_the_tool(ctx: Any, spies: Spies) -> None:  # noqa: F811
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    step = Step(order=2, action=Action.CLICK, target="Delete account")
    case = ctx.store.add_case(_case([_nav(), step]))
    out, _ = run(ctx, call("run_case", case_id=case.id))
    spans = read_tool_spans(ctx.store.paths.run_trace(ctx.run_id))
    assert [s.refusal for s in spans if s.op == "tool"] == ["write_policy"]
    assert out.refusals == 1 and spies.sessions == 0 and spies.count("run_case") == 0


# -- AL4 ------------------------------------------------------------------------------------
def test_al4_skills_are_passed_and_no_prompt_is_inlined(ctx: Any, monkeypatch: Any) -> None:
    got: dict[str, Any] = {}
    real = lead_agent.create_deep_agent
    monkeypatch.setattr(lead_agent, "create_deep_agent",
                        lambda **kw: (got.update(kw), real(**kw))[1])
    lead_agent.build_lead_agent(ctx, Scripted(script=[]))
    assert got["skills"] == ["/"]
    assert got["system_prompt"] == lead_agent.load_skill_prompt("agent-lead")
    text = AGENT_SRC.read_text(encoding="utf-8")
    assert ".read_text(" not in text
    tree = ast.parse(text)
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr)}
    assert [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and len(n.value) > 120 and id(n) not in docs] == []


# -- AL5 ------------------------------------------------------------------------------------
def test_al5_a_span_per_plan_tool_call_and_delegation_with_the_runs_trace_id(ctx: Any) -> None:
    out, _ = run(ctx, call("get_catalog"), delegate("test-designer"), AIMessage("sub done"))
    spans = read_tool_spans(ctx.store.paths.run_trace(ctx.run_id))
    assert {s.trace_id for s in spans} == {ctx.run_id}
    assert [s.name for s in spans if s.op == "tool"] == ["get_catalog"]
    assert [s.name for s in spans if s.op == "delegate"] == ["test-designer"]
    assert sum(s.op == "plan" for s in spans) >= 3
    assert all(s.parent_seq is not None for s in spans if s.op != "plan")
    assert (out.tool_calls, out.delegations) == (1, 1)


# -- AL6 ------------------------------------------------------------------------------------
def test_al6_a_secret_in_a_delegated_task_is_refused_and_no_prompt_carries_it(ctx: Any) -> None:
    out, model = run(ctx, delegate("explorer", f"log in with {RAW}"))
    assert out.delegations == 0 and out.refusals == 1
    assert RAW not in "".join(model.seen)
    assert RAW not in ctx.store.paths.run_trace(ctx.run_id).read_text(encoding="utf-8")


def test_al6_a_secret_in_the_user_task_halts_before_any_model_call(ctx: Any) -> None:
    model = Scripted(script=[AIMessage("x")])
    out = lead_agent.run_lead_agent(ctx, model, f"use password {RAW}")
    assert out.stopped == "model_error" and model.seen == []
    assert RAW not in out.model_dump_json()


# -- AL7 ------------------------------------------------------------------------------------
def test_al7_a_deterministic_job_delegates_zero_times(ctx: Any) -> None:
    out, _ = run(ctx, call("get_persona"), call("get_catalog"))
    assert out.delegations == 0 and out.tool_calls == 2


def test_al7_a_job_with_one_judgement_step_delegates_exactly_once(ctx: Any) -> None:
    out, _ = run(ctx, call("get_catalog"), delegate("test-designer"), AIMessage("designed"))
    assert out.delegations == 1 and out.tool_calls == 1


def test_al7_a_mechanical_or_unknown_delegation_is_refused(ctx: Any) -> None:
    for who in ("runner", "general-purpose"):
        out, _ = run(ctx, delegate(who, "run case c1"))
        assert out.delegations == 0 and out.refusals == 1, who


# -- AL11 -----------------------------------------------------------------------------------
def _long_job() -> list[AIMessage]:
    return [call("get_catalog"), call("get_persona"), call("get_catalog")]


def test_al11_a_budget_below_the_job_halts_with_a_named_reason(ctx: Any) -> None:
    out, _ = run(ctx, *_long_job(), budget=TokenBudget(max_tokens=25))
    assert out.stopped == "budget_exceeded" and "token budget exceeded" in out.reason
    assert out.tokens_used > 25 and out.summary == ""
    spans = read_tool_spans(ctx.store.paths.run_trace(ctx.run_id))
    assert (spans[-1].name, spans[-1].refusal) == ("budget", "budget_exceeded")


def test_al11_a_budget_above_the_job_completes_normally(ctx: Any) -> None:
    out, _ = run(ctx, *_long_job(), budget=TokenBudget(max_tokens=10_000))
    assert out.stopped == "finished" and out.reason == "" and out.summary == "all done"


def test_al11_a_cost_ceiling_halts_and_a_missing_usage_figure_is_estimated() -> None:
    meter = Meter(TokenBudget(max_cost_usd=0.001, usd_per_million_tokens=10.0))
    meter.add_message(AIMessage("x" * 4000))  # no usage metadata: ~1000 tokens, $0.01
    with pytest.raises(Exception, match="cost budget exceeded"):
        meter.check()


def test_al11_the_reasons_are_distinguishable(ctx: Any, spies: Spies) -> None:  # noqa: F811
    done, _ = run(ctx, call("get_catalog"))
    blocked, _ = run(ctx, call("crawl"))  # approval refusal: the run goes on and finishes
    halted, _ = run(ctx, *_long_job(), budget=TokenBudget(max_tokens=5))
    assert (done.stopped, blocked.stopped, halted.stopped) == (
        "finished", "finished", "budget_exceeded")
    assert blocked.refusals == 1 and done.refusals == 0
