"""T-174 (qa/contracts/cli-mcp.md CM1-CM5): the CLI contract and the MCP server.

Every `ExitCode` is provoked by a fixture (CM1); `--output json` is one scrubbed document (CM2);
`--dry-run` starts nothing (CM3); the MCP server lists three tools and refuses `run_tests` without
an approval (CM4); `mcp` is declared and no tool returns a secret (CM5). In-process.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval
from typer.testing import CliRunner

import autotester.ui.run_execution as run_execution
from autotester import cli, mcp_server
from autotester.browser.session import BrowserSession
from autotester.core.exit_codes import ExitCode
from autotester.providers.base import ProviderError
from autotester.schema.case import Case
from autotester.schema.cli_output import RegressionReport
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Verdict
from autotester.stages import run_launcher, run_service
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams
from autotester.store.project_store import ProjectStore

SECRET = "hunter2-planted-VALUE"
PROVOKED: set[int] = set()
RUNNER = CliRunner()


class World:
    result = Result.PASS
    leak = False
    printed = False


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(f"DEMO_PASSWORD={SECRET}\n", encoding="utf-8")
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"],
                               secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]))
    store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="t",
                        steps=[Step(order=0, action=Action.FILL, target="#pw",
                                    value="{{SECRET:DEMO_PASSWORD}}")]))
    World.result, World.leak, World.printed = Result.PASS, False, False

    class Judge:
        trace = None

        def __init__(self, project: Project) -> None:
            pass

        def available(self) -> bool:
            return True

    def fake_run_and_grade(case_, session, judge, run_id, store_):
        if World.printed:
            print("progress: running case", case_.id)       # must never reach stdout in json mode
        text = f"typed {SECRET}" if World.leak else "ok"
        raw = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED,
                        error=text if World.leak else None,
                        evidence=[Evidence(kind=EvidenceKind.SCREENSHOT,
                                           path=f"shots/{case_.id}.png")])
        return raw, Verdict(run_id=run_id, case_id=case_.id, result=World.result,
                            scoreboard=text, grader_provider="mock")

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", fake_run_and_grade)
    plan = ParallelPlan(1, 1, 1, "config", 99999.0, 8)
    monkeypatch.setattr(run_service, "DEFAULT_SEAMS",
                        RunSeams(judge_factory=Judge, planner=lambda *a, **kw: plan))
    return store


def without_credentials(store: ProjectStore) -> None:
    """A project with no provisioned account has no D-068 derived approval: only a human grant
    covers it, so with none on file the consent gate must say no."""
    store.save_project(store.load_project().model_copy(update={"secrets": []}))
    for case in store.list_cases():
        store.delete_case(case.id)
    store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="t",
                        steps=[Step(order=0, action=Action.CLICK, target="#go")]))


def invoke(*args: str):
    return RUNNER.invoke(cli.app, list(args))


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def code_of(result, expected: ExitCode) -> RegressionReport:
    PROVOKED.add(result.exit_code)
    assert result.exit_code == expected, (result.exit_code, result.stdout, result.stderr)
    return RegressionReport.model_validate_json(result.stdout)


# ---- CM1: one table, every code provoked ------------------------------------------------------

def test_the_table_has_distinct_values() -> None:
    assert len({int(c) for c in ExitCode}) == len(ExitCode) and ExitCode.OK == 0


def test_ok(world) -> None:
    grant_live_case_approval(world)
    report = code_of(invoke("run", "demo", "-o", "json"), ExitCode.OK)
    assert report.status == "passed" and report.verdict_counts == {"PASS": 1}


def test_test_failed(world) -> None:
    grant_live_case_approval(world)
    World.result = Result.FAIL
    assert code_of(invoke("run", "demo", "-o", "json"), ExitCode.TEST_FAILED).status == "failed"


def test_inconclusive(world) -> None:
    grant_live_case_approval(world)
    World.result = Result.INCONCLUSIVE
    code = code_of(invoke("run", "demo", "-o", "json"), ExitCode.INCONCLUSIVE)
    assert code.status == "inconclusive"


def test_usage_unknown_project(world) -> None:
    assert code_of(invoke("run", "nope", "-o", "json"), ExitCode.USAGE).status == "usage"


def test_refused_without_approval_starts_nothing(world, tmp_path) -> None:
    without_credentials(world)
    before = tree(tmp_path)
    report = code_of(invoke("run", "demo", "--output", "json"), ExitCode.REFUSED)
    assert report.status == "refused" and "no approval" in (report.message or "")
    assert tree(tmp_path) == before and not world.paths.runs_dir.exists()


@pytest.mark.parametrize("exc", [ProviderError("provider down"), TimeoutError("slow")])
def test_infra(world, monkeypatch, exc) -> None:
    def boom(*a, **kw):
        raise exc

    monkeypatch.setattr(run_service, "launch_run", boom)
    assert code_of(invoke("run", "demo", "-o", "json"), ExitCode.INFRA).status == "infra"


def test_internal(world, monkeypatch) -> None:
    def boom(*a, **kw):
        raise RuntimeError("bug")

    monkeypatch.setattr(run_service, "launch_run", boom)
    assert code_of(invoke("run", "demo", "-o", "json"), ExitCode.INTERNAL).status == "internal"


def test_help_mirrors_the_table() -> None:
    out = RUNNER.invoke(cli.app, ["run", "--help"], terminal_width=400).output
    assert all(f"{c.value} " in out for c in ExitCode)


def test_zz_every_code_in_the_table_was_provoked() -> None:
    assert {int(c) for c in ExitCode} <= PROVOKED, sorted({int(c) for c in ExitCode} - PROVOKED)


# ---- CM2: json is one typed, scrubbed document ------------------------------------------------

def test_json_stdout_is_exactly_one_document(world) -> None:
    grant_live_case_approval(world)
    World.printed = True
    result = invoke("run", "demo", "--output", "json")
    report = RegressionReport.model_validate(json.loads(result.stdout))   # only a document
    assert "\x1b" not in result.stdout and "progress:" not in result.stdout
    assert report.run_id and report.case_ids and report.cases[0].evidence_paths
    assert report.cases[0].result is Result.PASS and report.cases[0].outcome is Outcome.COMPLETED


def test_report_schema_forbids_extra_keys() -> None:
    with pytest.raises(ValueError):
        RegressionReport.model_validate(
            {"project": "x", "status": "passed", "exit_code": 0, "x": 1})


def test_planted_secret_appears_nowhere(world) -> None:
    grant_live_case_approval(world)
    World.leak, World.result = True, Result.FAIL
    for args in (("run", "demo", "-o", "json"), ("run-report", "demo", "-o", "json"),
                 ("run", "demo"), ("run-report", "demo")):
        result = invoke(*args)
        assert SECRET not in result.stdout + result.stderr, args
    assert "[REDACTED]" in invoke("run-report", "demo", "-o", "json").stdout


# ---- CM3: dry run sends nothing, starts nothing -----------------------------------------------

def test_dry_run_touches_nothing_and_lists_cases(world, tmp_path, monkeypatch) -> None:
    def raises(*a, **kw):
        raise AssertionError("a dry run must not reach this")

    monkeypatch.setattr(BrowserSession, "__init__", raises)
    monkeypatch.setattr(run_service, "launch_run", raises)
    monkeypatch.setattr(run_launcher, "judge_or_refuse", raises)
    monkeypatch.setattr(run_launcher, "for_role", raises)
    before = tree(tmp_path)
    report = code_of(invoke("run", "demo", "--dry-run", "--output", "json"), ExitCode.OK)
    assert report.dry_run and report.status == "dry_run" and report.run_id is None
    assert report.case_ids == [c.id for c in world.list_cases()]
    assert tree(tmp_path) == before and not world.paths.runs_dir.exists()


def test_dry_run_is_not_a_route_around_consent(world) -> None:
    without_credentials(world)
    assert invoke("run", "demo", "--dry-run", "-o", "json").exit_code == 0
    assert code_of(invoke("run", "demo", "-o", "json"), ExitCode.REFUSED).run_id is None


def test_dry_run_unknown_project_is_usage(world) -> None:
    assert code_of(invoke("run", "nope", "--dry-run", "-o", "json"), ExitCode.USAGE).dry_run


# ---- CM4/CM5: the MCP server ------------------------------------------------------------------

async def _call(name: str, args: dict):
    from mcp import Client

    async with Client(mcp_server.build_server()) as client:
        tools = [t.name for t in (await client.list_tools()).tools]
        return tools, await client.call_tool(name, args)


def test_exactly_three_tools(world) -> None:
    tools, _ = asyncio.run(_call("get_catalog", {"project": "demo"}))
    assert sorted(tools) == sorted(mcp_server.TOOL_NAMES)
    assert sorted(tools) == ["get_catalog", "get_report", "run_tests"]


def test_run_tests_without_approval_is_refused_and_starts_nothing(world, tmp_path) -> None:
    without_credentials(world)
    before = tree(tmp_path)
    _, result = asyncio.run(_call("run_tests", {"project": "demo"}))
    assert result.structured_content["exit_code"] == ExitCode.REFUSED
    assert result.structured_content["status"] == "refused" and tree(tmp_path) == before


def test_run_tests_with_approval_matches_get_report(world) -> None:
    grant_live_case_approval(world)
    _, result = asyncio.run(_call("run_tests", {"project": "demo"}))
    report = RegressionReport.model_validate(result.structured_content)
    assert report.status == "passed" and report.run_id
    again = asyncio.run(_call("get_report", {"project": "demo", "run_id": report.run_id}))[1]
    assert RegressionReport.model_validate(again.structured_content) == report


def test_dry_run_through_mcp(world, tmp_path) -> None:
    before = tree(tmp_path)
    _, result = asyncio.run(_call("run_tests", {"project": "demo", "dry_run": True}))
    assert result.structured_content["dry_run"] and tree(tmp_path) == before


def test_get_catalog_names_the_classes(world) -> None:
    _, result = asyncio.run(_call("get_catalog", {"project": "demo"}))
    assert "happy" in {e["case_class"] for e in result.structured_content["result"]["entries"]}


def test_no_tool_returns_a_secret(world) -> None:
    from mcp import Client

    grant_live_case_approval(world)
    World.leak, World.result = True, Result.FAIL

    async def everything() -> str:
        async with Client(mcp_server.build_server()) as client:
            parts = [(await client.list_tools()).model_dump_json()]
            for name in ("run_tests", "get_report", "get_catalog"):
                parts.append((await client.call_tool(name, {"project": "demo"})).model_dump_json())
            return "".join(parts)

    assert SECRET not in asyncio.run(everything())
