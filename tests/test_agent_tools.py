"""T-179a: the lead tester's stage tools -- thin wrappers (AL2), guards in code (AL3), no
secret at the tool boundary (AL6). Offline: spies stand in for stages; no browser, no model."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest

from autotester.agents import guards, tools
from autotester.agents.context import AgentContext
from autotester.browser.secrets import SecretStore
from autotester.providers.mock import MockProvider
from autotester.schema.agent_layer import AgentToolName, RefusalClass
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import (
    Action,
    ApprovalKind,
    CaseClass,
    CaseKind,
    Outcome,
    Result,
    WritePolicy,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import RawResult
from autotester.schema.verdict import Criterion, Judgment, Rubric
from autotester.store.project_store import ProjectStore

BASE = "https://app.test"
RAW = "Hunter2-raw-value-9137"


class Spies:
    def __init__(self) -> None:
        self.calls: dict[str, list[tuple[Any, ...]]] = {}
        self.sessions = 0

    def hit(self, name: str, *args: Any) -> None:
        self.calls.setdefault(name, []).append(args)

    def count(self, name: str) -> int:
        return len(self.calls.get(name, []))


def _project(policy: WritePolicy) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.test"],
                   write_policy=policy,
                   secrets=[SecretRef(key="APP_PASS", domains=["app.test"])])


def _case(steps: list[Step], rubric: bool = False) -> Case:
    return Case(project="demo", flow_id="f1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="case", steps=steps, rubric_ref="r1" if rubric else None)


def _nav() -> Step:
    return Step(order=1, action=Action.NAVIGATE, target="/home")


def _grant(store: ProjectStore, kind: ApprovalKind, actions: int = 50) -> None:
    store.add_approval(RunApproval(
        project="demo", run_kind=kind, target=BASE, scope="t179a fixture", max_actions=actions,
        wall_clock_s=900.0, granted_by="umesh", granted_at="2026-10-01",
        expires_at="2099-01-01").sign())


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch) -> Spies:
    spy = Spies()
    result = lambda case_id: RawResult(case_id=case_id, outcome=Outcome.COMPLETED)  # noqa: E731
    monkeypatch.setattr(tools.execute, "run_case",
                        lambda case, session: (spy.hit("run_case", case, session),
                                               result(case.id))[1])
    monkeypatch.setattr(tools.explore, "run_crawl",
                        lambda *a, **k: (spy.hit("run_crawl", *a), _crawl())[1])
    monkeypatch.setattr(tools.grade, "grade",
                        lambda *a, **k: (spy.hit("grade", *a), _verdict(a))[1])
    monkeypatch.setattr(tools.catalog, "catalog",
                        lambda *a, **k: (spy.hit("catalog", *a), _catalog())[1])
    return spy


def _crawl() -> Any:
    from autotester.schema.crawl import Crawl
    return Crawl(project="demo")


def _catalog() -> Any:
    from autotester.schema.catalog import Catalog
    return Catalog(project="demo")


def _verdict(args: tuple[Any, ...]) -> Any:
    from autotester.schema.verdict import Verdict
    return Verdict(run_id=args[2], case_id=args[1].case_id, rubric_hash="h", result=Result.PASS,
                   grader_provider="mock")


def _ctx(tmp_path: Path, spy: Spies, policy: WritePolicy = WritePolicy.READ_ONLY) -> AgentContext:
    project = _project(policy)
    store = ProjectStore("demo", tmp_path)
    store.paths.ensure()
    store.save_project(project)

    def open_session(observer: object) -> Any:
        spy.sessions += 1
        return _Session()
    return AgentContext(project=project, store=store,
                        secrets=SecretStore(project, {"APP_PASS": RAW}),
                        judge=MockProvider(), run_id="run-1", open_session=open_session)


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _go(ctx: AgentContext, name: str, args: dict[str, Any] | None = None) -> Any:
    return tools.dispatch(ctx, name, args or {})


# -- AL2: each tool wraps its named existing function, once, with the trusted context ----------
def test_every_tool_names_a_real_existing_function() -> None:
    assert set(tools.TOOLS) == set(AgentToolName)
    for spec in tools.TOOLS.values():
        parts = spec.wraps.split(".")
        target: Any = importlib.import_module(".".join(parts[:3]))  # autotester.<pkg>.<module>
        for attr in parts[3:]:
            target = getattr(target, attr)
        assert callable(target), spec.wraps


def test_run_case_wraps_execute_run_case_once_with_the_context_session(
        tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    case = ctx.store.add_case(_case([_nav()]))
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.ok and out.artifact_ref == f"result:{case.id}"
    assert spies.count("run_case") == 1 and spies.sessions == 1
    assert ctx.store.load_results("run-1")[0].case_id == case.id


def test_crawl_wraps_run_crawl_once_when_within_the_approval(tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    _grant(ctx.store, ApprovalKind.CRAWL, actions=50)
    out = _go(ctx, "crawl", {"max_actions": 40, "wall_clock_s": 600})
    assert out.ok and spies.count("run_crawl") == 1


def test_read_tools_and_grade_wrap_catalog_persona_grade(tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    assert _go(ctx, "get_catalog").ok and spies.count("catalog") == 1
    assert _go(ctx, "get_persona").refusal is RefusalClass.NOTHING_TO_DO
    case = ctx.store.add_case(_case([_nav()], rubric=True))
    ctx.store.save_rubric(Rubric(id="r1", case_id=case.id, criteria=[Criterion(id="c1", text="t")]))
    assert _go(ctx, "grade_case", {"case_id": case.id}).refusal is RefusalClass.NOTHING_TO_DO
    ctx.store.save_result("run-1", RawResult(case_id=case.id, outcome=Outcome.COMPLETED))
    out = _go(ctx, "grade_case", {"case_id": case.id})
    assert out.ok and spies.count("grade") == 1
    assert spies.calls["grade"][0][3] is ctx.judge


# -- AL3: guards execute inside the tool, before any browser, whatever the model says -----------
def test_al3a_raw_secret_in_arguments_is_refused_before_any_action(
        tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    for name, args in (("run_case", {"case_id": RAW}), ("get_catalog", {"note": RAW}),
                       ("run_case", {"case_id": "c1", "x": f"use {RAW[::-1]} reversed"})):
        out = _go(ctx, name, args)
        assert out.refusal is RefusalClass.SECRET and not out.ok
        assert RAW not in out.model_dump_json()
    assert spies.sessions == 0 and not spies.calls


def test_al3b_crawl_beyond_the_approval_is_refused_before_a_browser_opens(
        tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    assert _go(ctx, "crawl").refusal is RefusalClass.APPROVAL  # no approval at all
    _grant(ctx.store, ApprovalKind.CRAWL, actions=50)
    out = _go(ctx, "crawl", {"max_actions": 5000})
    assert out.refusal is RefusalClass.APPROVAL and "grant" in out.summary.lower()
    assert spies.sessions == 0 and spies.count("run_crawl") == 0


def test_al3c_a_read_only_project_refuses_a_mutating_step_from_the_tool_itself(
        tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies, WritePolicy.READ_ONLY)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    fill = Step(order=1, action=Action.FILL, target="Display name", value="Eve")
    delete = Step(order=1, action=Action.CLICK, target="Delete account")
    for step in (fill, delete):
        case = ctx.store.add_case(_case([_nav(), step]))
        out = _go(ctx, "run_case", {"case_id": case.id})
        assert out.refusal is RefusalClass.WRITE_POLICY and "read_only" in out.summary
    assert spies.sessions == 0 and spies.count("run_case") == 0


def test_read_only_still_allows_login_placeholder_and_the_same_step_under_test_account(
        tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies, WritePolicy.READ_ONLY)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    login = Step(order=2, action=Action.FILL, target="Password", value="{{SECRET:APP_PASS}}")
    assert _go(ctx, "run_case", {"case_id": ctx.store.add_case(_case([_nav(), login])).id}).ok
    writer = _ctx(tmp_path / "w", spies, WritePolicy.TEST_ACCOUNT)
    _grant(writer.store, ApprovalKind.LIVE_CASE)
    fill = Step(order=2, action=Action.FILL, target="Display name", value="Eve")
    assert _go(writer, "run_case", {"case_id": writer.store.add_case(_case([_nav(), fill])).id}).ok


def test_run_case_without_a_live_case_approval_is_refused(tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    case = ctx.store.add_case(_case([_nav()]))
    assert _go(ctx, "run_case", {"case_id": case.id}).refusal is RefusalClass.APPROVAL
    assert spies.sessions == 0


# -- validation and AL6: unknown tools/fields, empty work, nothing secret leaves a tool ---------
def test_unknown_tool_field_and_case_do_nothing(tmp_path: Path, spies: Spies) -> None:
    ctx = _ctx(tmp_path, spies)
    assert _go(ctx, "shell", {"cmd": "ls"}).refusal is RefusalClass.UNKNOWN_TOOL
    assert _go(ctx, "run_case", {"case_id": "c", "project": "other"}).refusal \
        is RefusalClass.BAD_ARGUMENTS
    assert _go(ctx, "run_case", {"case_id": "missing"}).refusal is RefusalClass.NOTHING_TO_DO
    empty = ctx.store.add_case(_case([]))
    assert _go(ctx, "run_case", {"case_id": empty.id}).refusal is RefusalClass.NOTHING_TO_DO
    assert not spies.calls and spies.sessions == 0


def test_al6_a_secret_in_a_stage_result_never_reaches_the_model(
        tmp_path: Path, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _ctx(tmp_path, spies)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    case = ctx.store.add_case(_case([_nav()]))
    leaked = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=f"bad login {RAW}")
    monkeypatch.setattr(tools.execute, "run_case", lambda c, s: leaked)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert RAW not in out.model_dump_json()
    stored = ctx.store.paths.run_dir("run-1").joinpath(f"{case.id}.json")
    assert RAW not in stored.read_text("utf-8")


def test_al6_a_real_grade_withholds_a_prompt_carrying_a_secret(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, Spies())
    ctx.judge = MockProvider(responses={"judge": [Judgment(result=Result.PASS)]})
    case = ctx.store.add_case(_case([_nav()], rubric=True))
    ctx.store.save_rubric(Rubric(id="r1", case_id=case.id,
                                 criteria=[Criterion(id="c1", text=f"mentions {RAW}")]))
    ctx.store.save_result("run-1", RawResult(case_id=case.id, outcome=Outcome.COMPLETED))
    out = _go(ctx, "grade_case", {"case_id": case.id})
    assert ctx.judge.prompts == [] and RAW not in out.model_dump_json()  # type: ignore[attr-defined]
    assert ctx.store.load_verdicts("run-1")[0].result is Result.BLOCKED


def test_guards_module_exposes_the_write_policy_check_as_a_pure_function() -> None:
    assert guards.write_policy_refusal(_case([_nav()]), _project(WritePolicy.READ_ONLY)) is None
