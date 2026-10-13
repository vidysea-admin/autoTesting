"""T-179c: the lead loop (AL4 skill loader, AL5 trace spans, AL7 delegation counts, AL6 gates).
Offline: a scripted model and a fake delegator stand in; no browser, no live model."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from autotester.agents import lead, tools
from autotester.agents.context import AgentContext
from autotester.browser.secrets import SecretStore
from autotester.core.trace import read_spans, read_tool_spans
from autotester.providers.mock import MockProvider
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore

RAW = "Hunter2-raw-value-9137"


class Script:
    """A scripted model: returns its steps in order and records what it was shown."""

    def __init__(self, *steps: object) -> None:
        self.steps, self.seen = list(steps), []

    def next_step(self, system: str, transcript: Any) -> object:
        self.seen.append((system, tuple(transcript)))
        return self.steps.pop(0)


class Subs:
    def __init__(self, reply: str = "done") -> None:
        self.calls: list[tuple[str, str]] = []
        self.reply = reply

    def delegate(self, subagent: str, task: str, shared_files: dict[str, str]) -> str:
        self.calls.append((subagent, task))
        return self.reply


def _no_session(observer: object) -> Any:
    raise AssertionError("no browser in the lead loop tests")


@pytest.fixture
def ctx(tmp_path: Path) -> AgentContext:
    project = Project(slug="demo", name="Demo", base_url="https://app.test",
                      allowed_domains=["app.test"], secrets=[SecretRef(key="APP_PASS",
                                                                       domains=["app.test"])])
    store = ProjectStore("demo", tmp_path)
    store.paths.ensure()
    store.save_project(project)
    return AgentContext(project=project, store=store,
                        secrets=SecretStore(project, {"APP_PASS": RAW}), judge=MockProvider(),
                        run_id="run-7", open_session=_no_session)


def _tool(name: str, **args: Any) -> dict[str, Any]:
    return {"kind": "tool", "tool": name, "args": args}


def _deleg(who: str, task: str = "design cases") -> dict[str, Any]:
    return {"kind": "delegate", "subagent": who, "task": task}


FINISH = {"kind": "finish", "summary": "ok"}


def test_al4_the_system_prompt_comes_from_the_skill_loader(ctx: AgentContext) -> None:
    model = Script(FINISH)
    lead.run_lead(ctx, model)
    assert model.seen[0][0] == lead.load_skill_prompt("agent-lead")
    assert lead.lead_skills()[0].joinpath("SKILL.md").is_file()


def test_al4_no_prompt_literal_or_direct_skill_read_in_the_agent_modules() -> None:
    for path in (Path(lead.__file__), Path(tools.__file__)):
        text = path.read_text(encoding="utf-8")
        assert ".read_text(" not in text, path.name
        tree = ast.parse(text)
        docs = {id(n.body[0].value) for n in ast.walk(tree)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                and isinstance(n.body[0], ast.Expr)}
        long = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                and isinstance(n.value, str) and len(n.value) > 200 and id(n) not in docs]
        assert long == [], f"{path.name} embeds a prompt-sized string"


def test_al5_a_span_per_plan_tool_call_and_delegation_on_the_runs_own_trace(
        ctx: AgentContext) -> None:
    model = Script(_tool("get_persona"), _deleg("grader"), FINISH)
    out = lead.run_lead(ctx, model, Subs())
    spans = read_tool_spans(ctx.store.paths.run_trace("run-7"))
    assert [(s.op, s.name) for s in spans] == [
        ("plan", "lead"), ("tool", "get_persona"), ("plan", "lead"), ("delegate", "grader"),
        ("plan", "lead")]
    assert {s.trace_id for s in spans} == {"run-7"} == {ctx.run_id}
    assert [s.parent_seq for s in spans if s.op != "plan"] == [0, 2]
    assert not spans[1].ok and spans[1].refusal == "nothing_to_do"  # no persona stored yet
    assert (out.tool_calls, out.delegations, out.refusals) == (1, 1, 1)
    assert read_spans(ctx.store.paths.run_trace("run-7")) == []  # the stage view is unchanged


def test_al5_a_refused_call_still_gets_a_span_without_the_callers_text(ctx: AgentContext) -> None:
    lead.run_lead(ctx, Script(_tool("rm -rf"), FINISH))
    span = read_tool_spans(ctx.store.paths.run_trace("run-7"))[1]
    assert (span.name, span.ok, span.refusal) == ("unknown", False, "unknown_tool")


def test_al7_a_deterministic_job_delegates_zero_times(ctx: AgentContext) -> None:
    subs = Subs()
    out = lead.run_lead(ctx, Script(_tool("get_persona"), _tool("get_catalog"), FINISH), subs)
    assert out.delegations == 0 and subs.calls == []


def test_al7_a_mixed_job_delegates_exactly_once(ctx: AgentContext) -> None:
    subs = Subs()
    out = lead.run_lead(ctx, Script(_tool("get_catalog"), _deleg("test-designer"), FINISH), subs)
    assert out.delegations == 1 and subs.calls == [("test-designer", "design cases")]


def test_al7_a_mechanical_step_is_never_delegated(ctx: AgentContext) -> None:
    subs = Subs()
    out = lead.run_lead(ctx, Script(_deleg("runner", "run case c1"), FINISH), subs)
    assert out.delegations == 0 and out.refusals == 1 and subs.calls == []
    span = read_tool_spans(ctx.store.paths.run_trace("run-7"))[1]
    assert (span.op, span.ok, span.refusal) == ("delegate", False, "bad_arguments")


def test_al6_a_secret_in_a_delegated_task_is_refused_and_not_traced(ctx: AgentContext) -> None:
    subs = Subs()
    out = lead.run_lead(ctx, Script(_deleg("explorer", f"log in with {RAW}"), FINISH), subs)
    assert subs.calls == [] and out.refusals == 1
    assert RAW not in ctx.store.paths.run_trace("run-7").read_text(encoding="utf-8")


def test_al6_a_secret_in_a_subagent_reply_never_reaches_the_model(ctx: AgentContext) -> None:
    model = Script(_deleg("explorer"), FINISH)
    lead.run_lead(ctx, model, Subs(reply=f"pass is {RAW}"))
    assert RAW not in repr(model.seen)


def test_a_stage_secret_in_a_tool_outcome_never_reaches_the_model(
        ctx: AgentContext, monkeypatch: pytest.MonkeyPatch) -> None:
    model = Script(_tool("get_persona"), FINISH)
    out = tools.ToolOutcome(tool="get_persona", ok=True, summary=f"x {RAW}")
    monkeypatch.setattr(tools, "dispatch", lambda c, n, a: out)
    lead.run_lead(ctx, model)
    assert RAW not in repr(model.seen)


def test_a_bad_model_step_stops_the_loop_with_a_typed_stop(ctx: AgentContext) -> None:
    out = lead.run_lead(ctx, Script({"kind": "tool", "bogus": 1}, FINISH))
    assert out.stopped == "model_error" and out.steps == 0


def test_the_step_cap_stops_a_model_that_never_finishes(ctx: AgentContext) -> None:
    out = lead.run_lead(ctx, Script(*[_tool("get_catalog")] * 5), max_steps=3)
    assert out.stopped == "step_cap" and out.steps == 3


def test_a_failing_subagent_is_a_typed_refusal(ctx: AgentContext) -> None:
    class Boom:
        def delegate(self, *a: object) -> str:
            raise RuntimeError(RAW)
    out = lead.run_lead(ctx, Script(_deleg("grader"), FINISH), Boom())
    assert out.refusals == 1 and out.delegations == 0
