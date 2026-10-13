"""T-180: the five subagents -- explicit allowlists (AL10), a grader that cannot act (AL8),
and separate contexts (AL9). Offline: no browser, no model, no network."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from autotester.agents import subagents, tools
from autotester.agents.context import AgentContext
from autotester.browser.secrets import SecretStore
from autotester.providers.mock import MockProvider
from autotester.schema.agent_layer import AgentToolName as T
from autotester.schema.agent_layer import RefusalClass, ToolEffect
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, Outcome, Result, WritePolicy
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import Evidence, RawResult
from autotester.schema.subagent import SubagentName as N
from autotester.schema.subagent import SubagentSpec
from autotester.schema.verdict import Criterion, Rubric, Verdict
from autotester.store.project_store import ProjectStore

RAW = "Hunter2-raw-value-9137"
ACTING = {T.CRAWL, T.RUN_CASE, T.GRADE_CASE}


def _ctx(tmp_path: Path) -> AgentContext:
    project = Project(slug="demo", name="Demo", base_url="https://app.test",
                      allowed_domains=["app.test"], write_policy=WritePolicy.READ_ONLY,
                      secrets=[SecretRef(key="APP_PASS", domains=["app.test"])])
    store = ProjectStore("demo", tmp_path)
    store.paths.ensure()
    store.save_project(project)

    def no_browser(observer: object) -> Any:
        raise AssertionError("a subagent test must never open a browser")
    return AgentContext(project=project, store=store,
                        secrets=SecretStore(project, {"APP_PASS": RAW}),
                        judge=MockProvider(), run_id="run-1", open_session=no_browser)


def _seed(ctx: AgentContext, label: str = "shot-1") -> str:
    case = ctx.store.add_case(Case(project="demo", flow_id="f1", kind=CaseKind.BEST,
                                   case_class=CaseClass.HAPPY, title="c", steps=[],
                                   rubric_ref="r1"))
    ctx.store.save_rubric(Rubric(id="r1", case_id=case.id,
                                 criteria=[Criterion(id="c1", text="dashboard shows")],
                                 no_fire=["style nits"]))
    ctx.store.save_result("run-1", RawResult(
        case_id=case.id, outcome=Outcome.COMPLETED,
        evidence=[Evidence(kind="screenshot", path="a.png", label=label)]))
    ctx.store.save_verdict("run-1", Verdict(run_id="run-1", case_id=case.id, rubric_hash="h",
                                            result=Result.PASS, scoreboard="Criteria 1/1 met.",
                                            grader_provider="mock"))
    return case.id


# -- happy path: all five, named ----------------------------------------------------------
def test_the_five_subagents_are_configured_by_name() -> None:
    assert set(subagents.SUBAGENTS) == {N.EXPLORER, N.TEST_DESIGNER, N.RUNNER, N.GRADER,
                                        N.REPORTER}
    assert {n.value for n in N} == {"explorer", "test-designer", "runner", "grader", "reporter"}


# -- AL10: explicit minimum allowlists ------------------------------------------------------
def test_al10_the_allowlists_are_the_named_minimum() -> None:
    table = {n: set(s.tools) for n, s in subagents.SUBAGENTS.items()}
    assert table == {
        N.EXPLORER: {T.CRAWL, T.GET_PERSONA, T.GET_CATALOG},
        N.TEST_DESIGNER: {T.GET_PERSONA, T.GET_CATALOG},
        N.RUNNER: {T.RUN_CASE},
        N.GRADER: {T.READ_RESULT, T.READ_RUBRIC},
        N.REPORTER: {T.GET_PERSONA, T.GET_CATALOG, T.READ_RESULT, T.READ_VERDICT},
    }
    assert T.GRADE_CASE not in set().union(*table.values())  # persisted by the lead only
    assert not ACTING & table[N.REPORTER] and not ACTING & table[N.TEST_DESIGNER]


@pytest.mark.parametrize("name", list(N))
def test_al10_every_tool_outside_the_allowlist_is_absent_from_its_calls(
        name: N, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _ctx(tmp_path)
    reached: list[str] = []
    monkeypatch.setattr(tools, "dispatch", lambda c, t, a: reached.append(t))
    absent = subagents.absent_tools(name)
    assert absent == set(tools.TOOLS) - set(subagents.SUBAGENTS[name].tools) and absent
    for tool in absent:
        out = subagents.call_tool(ctx, name, tool.value, {})
        assert out.refusal is RefusalClass.NOT_ALLOWED and not out.ok
    assert reached == []  # no refused call ever reached the dispatcher


def test_al10_a_spec_with_no_tool_list_is_refused_not_given_everything() -> None:
    with pytest.raises(ValidationError):
        SubagentSpec(name=N.RUNNER, description="d", skill="agent-runner", tools=())
    with pytest.raises(ValidationError):
        SubagentSpec(name=N.RUNNER, description="d", skill="agent-runner")  # type: ignore[call-arg]
    spec = subagents.SUBAGENTS[N.RUNNER]
    with pytest.raises(ValidationError):
        spec.tools = tuple(T)  # type: ignore[misc]  # frozen: cannot be widened afterwards


@pytest.mark.parametrize("junk", [None, 7, "", "nope", "RUN_CASE", ["run_case"], RAW])
def test_a_malformed_tool_name_is_refused_without_echo(junk: Any, tmp_path: Path) -> None:
    out = subagents.call_tool(_ctx(tmp_path), N.GRADER, junk, {})
    assert out.refusal is RefusalClass.NOT_ALLOWED and RAW not in out.model_dump_json()


# -- AL8: the grader cannot act ---------------------------------------------------------------
def test_al8_the_graders_tools_are_all_read_only() -> None:
    grader = subagents.SUBAGENTS[N.GRADER].tools
    assert grader and all(tools.TOOLS[t].effect is ToolEffect.READ for t in grader)
    assert not ACTING & set(grader)


def test_al8_the_grader_reads_evidence_and_is_refused_every_acting_tool(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    case_id = _seed(ctx)
    result = subagents.call_tool(ctx, N.GRADER, "read_result", {"case_id": case_id})
    rubric = subagents.call_tool(ctx, N.GRADER, "read_rubric", {"case_id": case_id})
    assert result.ok and "completed" in result.summary and "shot-1" in result.summary
    assert rubric.ok and "dashboard shows" in rubric.summary
    for acting in ("run_case", "crawl", "grade_case"):
        refused = subagents.call_tool(ctx, N.GRADER, acting, {"case_id": case_id})
        assert refused.refusal is RefusalClass.NOT_ALLOWED
    assert len(ctx.store.load_verdicts("run-1")) == 1  # the grader wrote nothing


# -- AL9: separate contexts ---------------------------------------------------------------------
def test_al9_each_invocation_holds_only_its_own_prompt_task_and_passed_files() -> None:
    lead_history = "LEAD-HISTORY-MARKER " * 50
    explorer_log = "EXPLORER-RAW-TRANSCRIPT " * 40_000  # ~1 MB: the two would overflow one window
    grader_log = "GRADER-RAW-TRANSCRIPT " * 40_000
    a = subagents.invocation(N.EXPLORER, "map the app")
    b = subagents.invocation(N.GRADER, "grade case c1",
                             {"projects/demo/runs/run-1/results/c1.json": "outcome completed"})
    for inv, other in ((a, grader_log), (b, explorer_log)):
        text = inv.model_dump_json()
        assert lead_history not in text and other[:30] not in text
    assert len(explorer_log) + len(grader_log) > 1_500_000
    assert len(a.model_dump_json()) < 20_000 and len(b.model_dump_json()) < 20_000
    assert set(b.model_dump()) == {"subagent", "system_prompt", "task", "shared_files", "tools"}
    assert a.system_prompt != b.system_prompt


def test_al9_state_crosses_only_through_a_file_the_lead_passes(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    case_id = _seed(ctx)
    ended = subagents.call_tool(ctx, N.RUNNER, "run_case", {"case_id": "missing"})
    assert ended.refusal is RefusalClass.NOTHING_TO_DO  # the runner's context ends here
    read = subagents.call_tool(ctx, N.REPORTER, "read_result", {"case_id": case_id}).summary
    inv = subagents.invocation(N.REPORTER, "write up", {"result.txt": read})
    assert inv.shared_files == {"result.txt": read}
    assert ended.summary not in inv.model_dump_json()


# -- evidence tools and the framework hand-off ----------------------------------------------
def test_the_evidence_tools_report_missing_artifacts_and_scrub_secrets(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    missing = subagents.call_tool(ctx, N.GRADER, "read_result", {"case_id": "x"})
    assert missing.refusal is RefusalClass.NOTHING_TO_DO
    case_id = _seed(ctx, label=f"typed {RAW}")
    out = subagents.call_tool(ctx, N.GRADER, "read_result", {"case_id": case_id})
    assert RAW not in out.model_dump_json()
    assert subagents.call_tool(ctx, N.REPORTER, "read_verdict", {"case_id": case_id}).ok
    bad = subagents.call_tool(ctx, N.GRADER, "read_rubric", {"case_id": case_id, "x": 1})
    assert bad.refusal is RefusalClass.BAD_ARGUMENTS


@pytest.mark.parametrize("name", list(N))
def test_every_subagent_has_a_skill_prompt_and_a_framework_config(name: N) -> None:
    cfg = subagents.deep_agents_config(name)
    assert cfg["name"] == name.value and cfg["system_prompt"].strip()
    assert cfg["tools"] == [t.value for t in subagents.SUBAGENTS[name].tools]
    assert subagents.invocation(name, "t").system_prompt == cfg["system_prompt"]
