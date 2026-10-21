"""AT-1384 fix cycle 1 (C1): the project's `image_mask_limit` must reach the image sanitiser at
every production site that grades a screenshot or bundles one. One test per site; each stubs
the callee and asserts it received the project's 0.85, not the 0.75 default (a site that
drops the limit would silently re-withhold a Pathlynks dashboard the project meant to keep).
Contract: qa/contracts/browser-and-secrets.md B11, qa/contracts/grade.md."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from downstream_fixture import downstream_fixture
from PIL import Image
from test_agent_tools import _case as tool_case
from test_agent_tools import _nav
from test_agent_tools import _project as tool_project
from test_orchestrate_downstream import _expand
from test_run_case_pipeline import _case, _session

from autotester.agents import tools
from autotester.agents.context import AgentContext
from autotester.browser.secrets import SecretStore
from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result, WritePolicy
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.run_state import StageName
from autotester.schema.verdict import Criterion, Rubric, Verdict
from autotester.stages import orchestrate_downstream as downstream
from autotester.stages import run_artifacts
from autotester.stages import run_case_pipeline as pipeline
from autotester.stages.run_case_pipeline import run_and_grade_case, run_and_grade_case_resilient
from autotester.store.project_store import ProjectStore

PATHLYNKS_LIMIT = 0.85


def _pathlynks_like() -> Project:
    return Project(slug="demo", name="Demo", base_url="https://demo.test",
                   allowed_domains=["demo.test"], image_mask_limit=PATHLYNKS_LIMIT)


def _record_grade(monkeypatch, module, seen: list) -> None:
    def fake_grade(rubric, raw, run_id, provider, *args, **kwargs):
        seen.append(kwargs.get("mask_limit", "dropped"))
        return Verdict(run_id=run_id, case_id=raw.case_id, result=Result.PASS,
                       rubric_hash=rubric.fingerprint, grader_provider="mask-limit-probe")

    monkeypatch.setattr(module, "grade", fake_grade)


def test_pathlynks_dashboard_graded_by_the_ui_run_path_uses_the_project_limit(
        tmp_path: Path, monkeypatch) -> None:
    """run_case_pipeline.py:227 -- a Pathlynks dashboard screenshot graded with limit 0.85."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_pathlynks_like())
    seen: list = []
    _record_grade(monkeypatch, pipeline, seen)
    run_and_grade_case(_case(), _session(tmp_path), MockProvider(), "run_1", store)
    assert seen == [PATHLYNKS_LIMIT]


def test_pathlynks_dashboard_graded_by_the_parallel_run_path_uses_the_project_limit(
        tmp_path: Path, monkeypatch) -> None:
    """run_case_pipeline.py:270 -- the resilient (parallel) route grades with limit 0.85."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_pathlynks_like())
    seen: list = []
    _record_grade(monkeypatch, pipeline, seen)
    run_and_grade_case_resilient(_case(), _session(tmp_path), MockProvider(), "run_1", store)
    assert seen == [PATHLYNKS_LIMIT]


def test_pathlynks_dashboard_graded_by_the_downstream_stage_uses_the_project_limit(
        tmp_path: Path, monkeypatch) -> None:
    """orchestrate_downstream.py:162 -- the checkpointed grade stage grades with limit 0.85."""
    f = downstream_fixture(tmp_path)
    _store, project, _spec, _ref, _gen, judge, ctx = f
    observed = ctx.runners[StageName.EXECUTE](ctx, _expand(f))
    seen: list = []
    _record_grade(monkeypatch, downstream, seen)
    stage = downstream.make_grade_stage(
        project.model_copy(update={"image_mask_limit": PATHLYNKS_LIMIT}), judge=judge)
    stage(ctx, observed)
    assert seen == [PATHLYNKS_LIMIT]


def test_pathlynks_dashboard_in_a_failure_bundle_is_sanitised_with_the_project_limit(
        tmp_path: Path, monkeypatch) -> None:
    """run_artifacts.py:92 -- the failure bundle of a failed Pathlynks case sanitises with 0.85."""
    store = ProjectStore("demo", tmp_path)
    store.save_project(_pathlynks_like())
    case = _case()
    store.add_case(case)
    run_dir = store.paths.run_dir("run-A")
    run_dir.mkdir(parents=True)
    Image.new("RGB", (30, 20), "white").save(run_dir / "shot.png")
    store.save_result("run-A", RawResult(
        case_id=case.id, outcome=Outcome.COMPLETED,
        evidence=[Evidence(kind=EvidenceKind.SCREENSHOT, path="shot.png", step_order=1)]))
    store.save_verdict("run-A", Verdict(run_id="run-A", case_id=case.id, result=Result.FAIL))
    seen: list = []

    @contextmanager
    def probe(paths, *, mask_limit="dropped"):
        seen.append(mask_limit)
        yield SimpleNamespace(paths=[], reasons=[], text_unavailable=False)

    monkeypatch.setattr(run_artifacts, "sanitized_images", probe)
    run = Run(id="run-A", project="demo", case_ids=[case.id])
    run_artifacts.assemble_run_bundles(store, run)
    assert seen == [PATHLYNKS_LIMIT]


def test_pathlynks_dashboard_graded_by_the_lead_agent_tool_uses_the_project_limit(
        tmp_path: Path, monkeypatch) -> None:
    """agents/tools.py:163 -- the agent's grade_case tool grades with limit 0.85."""
    project = tool_project(WritePolicy.READ_ONLY).model_copy(
        update={"image_mask_limit": PATHLYNKS_LIMIT})
    store = ProjectStore("demo", tmp_path)
    store.paths.ensure()
    store.save_project(project)
    ctx = AgentContext(project=project, store=store, secrets=SecretStore(project, {}),
                       judge=MockProvider(), run_id="run-1", open_session=lambda _o: None)
    case = store.add_case(tool_case([_nav()], rubric=True))
    store.save_rubric(Rubric(id="r1", case_id=case.id, criteria=[Criterion(id="c1", text="t")]))
    store.save_result("run-1", RawResult(case_id=case.id, outcome=Outcome.COMPLETED))
    seen: list = []
    _record_grade(monkeypatch, tools.grade, seen)
    out = tools.dispatch(ctx, "grade_case", {"case_id": case.id})
    assert out.ok and seen == [PATHLYNKS_LIMIT]
