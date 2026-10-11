"""T-174 machine CLI/MCP contract (qa/contracts/cli-mcp.md CM1-CM5).
Exit codes, typed scrubbed JSON, offline dry runs, shared approval and declared dependency.
"""

from __future__ import annotations

import ast
import asyncio
import json
import sys
import tomllib
from pathlib import Path

import pytest
from cli_mcp_fixture import SECRET_VALUE, install_fakes, seed_project, tree_hash
from typer.testing import CliRunner

from autotester import cli_run, run_ops
from autotester.cli import app
from autotester.providers.base import ProviderError
from autotester.schema.catalog import Catalog
from autotester.schema.cli_output import ExitCode, RunReport
from autotester.schema.enums import Result
from autotester.stages import run_launcher

runner = CliRunner()
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _run(*args: str):
    return runner.invoke(app, ["run", "demo", *args])

def _report(result) -> RunReport:
    return RunReport.model_validate_json(result.stdout)

def _p_ok(root, mp):
    seed_project(root, approve=True)
    install_fakes(mp)
    return _run("--output", "json")

def _p_test_failed(root, mp):
    seed_project(root, ("ok", "bad"), approve=True)
    install_fakes(mp, {"bad": Result.FAIL})
    return _run("--output", "json")

def _p_usage(root, mp):
    return runner.invoke(app, ["run", "no-such-project", "--output", "json"])

def _p_refused(root, mp):
    seed_project(root)  # no credentials declared, no approval on disk
    install_fakes(mp)
    return _run("--output", "json")

def _p_infrastructure(root, mp):
    seed_project(root, approve=True)
    install_fakes(mp)
    _executor_raises(mp, ProviderError("model endpoint unreachable"))
    return _run("--output", "json")

def _p_internal(root, mp):
    seed_project(root, approve=True)
    install_fakes(mp)
    _executor_raises(mp, RuntimeError("stage blew up"))
    return _run("--output", "json")

def _executor_raises(mp, exc: BaseException) -> None:
    """The launcher's one executor fails the way a real stage would."""
    def explode(*_a, **_k):
        raise exc
    mp.setattr(run_launcher, "run_cases_traced", explode)

PROVOKERS = {
    "OK": _p_ok, "TEST_FAILED": _p_test_failed, "USAGE": _p_usage, "RUN_REFUSED": _p_refused,
    "INFRASTRUCTURE": _p_infrastructure, "INTERNAL": _p_internal,
}
DOCUMENTED = {"OK": 0, "TEST_FAILED": 1, "USAGE": 2, "RUN_REFUSED": 3, "INFRASTRUCTURE": 4,
              "INTERNAL": 5}

def test_every_code_in_the_table_has_a_provoking_test() -> None:
    """`__members__` includes aliases, so two codes collapsed to one value cannot hide."""
    assert {n: int(c) for n, c in ExitCode.__members__.items()} == DOCUMENTED
    assert set(PROVOKERS) == set(DOCUMENTED)


@pytest.mark.parametrize("name", list(DOCUMENTED))
def test_each_code_is_what_the_cli_exits_with(name, root, monkeypatch) -> None:
    result = PROVOKERS[name](root, monkeypatch)
    assert result.exit_code == DOCUMENTED[name], result.output
    assert _report(result).exit_code == DOCUMENTED[name]  # the document says the same thing


def test_a_timeout_is_infrastructure_not_internal(root, monkeypatch) -> None:
    seed_project(root, approve=True)
    install_fakes(monkeypatch)
    _executor_raises(monkeypatch, TimeoutError("browser did not answer"))
    assert _run("--output", "json").exit_code == int(ExitCode.INFRASTRUCTURE)


def test_help_documents_the_table() -> None:
    help_text = runner.invoke(app, ["run", "--help"]).output
    for name, value in DOCUMENTED.items():
        assert f"{value} {name}" in " ".join(help_text.split())


def test_doctors_own_contract_is_unchanged() -> None:
    assert "raise typer.Exit(0)" in (SRC / "cli.py").read_text(encoding="utf-8")


def test_json_stdout_is_one_document_and_nothing_else(root, monkeypatch) -> None:
    seed_project(root, ("a", "b"), approve=True)
    install_fakes(monkeypatch)
    result = _run("--output", "json")
    json.loads(result.stdout)  # the whole of stdout, not a prefix of it
    assert "\x1b" not in result.stdout
    report = _report(result)
    assert report.run_id and report.run_id.startswith("run-")
    assert len(report.cases) == 2 and report.counts == {"PASS": 2}
    assert report.status == "passed" and report.dry_run is False


def test_a_printed_human_line_would_break_the_parse() -> None:
    with pytest.raises(ValueError):
        RunReport.model_validate_json("running 2 cases...\n" + RunReport(
            project="demo", status="passed", exit_code=0).model_dump_json())


def test_the_planted_secret_appears_nowhere(root, monkeypatch) -> None:
    seed_project(root, secret=True)
    install_fakes(monkeypatch, {"ok": Result.FAIL})
    result = _run("--output", "json")
    assert result.exit_code == int(ExitCode.TEST_FAILED), result.output
    assert SECRET_VALUE not in result.stdout and SECRET_VALUE not in result.stderr
    assert "[REDACTED]" in result.stdout  # it was in the data and was masked, not absent


def test_text_output_is_the_default_and_is_not_json(root, monkeypatch) -> None:
    seed_project(root, approve=True)
    install_fakes(monkeypatch)
    result = _run()
    assert result.exit_code == 0 and "passed" in result.stdout and "{" not in result.stdout


def test_report_show_returns_the_stored_run(root, monkeypatch) -> None:
    seed_project(root, ("a", "bad"), approve=True)
    install_fakes(monkeypatch, {"bad": Result.FAIL})
    ran = _report(_run("--output", "json"))
    shown = runner.invoke(app, ["report", "show", "demo", "--output", "json"])
    assert _report(shown).run_id == ran.run_id and _report(shown).counts == ran.counts
    assert shown.exit_code == int(ExitCode.TEST_FAILED) == _report(shown).exit_code
    assert runner.invoke(app, ["report", "show", "demo", "run-nope"]).exit_code == 2


def test_catalog_json_is_the_catalog_model(root) -> None:
    seed_project(root)
    result = runner.invoke(app, ["catalog", "demo", "--output", "json"])
    assert result.exit_code == 0
    assert Catalog.model_validate_json(result.stdout).project == "demo"


@pytest.mark.parametrize("secret", [False, True], ids=["plain", "credentialed"])
def test_dry_run_touches_nothing_and_lists_the_cases(secret, root, monkeypatch) -> None:
    store = seed_project(root, ("a", "b"), secret=secret)
    install_fakes(monkeypatch, strict=True)  # browser, grader, network all raise on use
    before = tree_hash(root)
    result = _run("--dry-run", "--output", "json")
    assert result.exit_code == 0, result.output
    assert tree_hash(root) == before
    report = _report(result)
    assert report.dry_run and report.run_id is None and report.status == "dry_run"
    assert sorted(report.planned_case_ids) == sorted(c.id for c in store.list_cases())


def test_dry_run_is_not_a_route_around_the_approval_gate(root, monkeypatch) -> None:
    seed_project(root)
    install_fakes(monkeypatch)
    assert _run("--dry-run").exit_code == 0
    assert _run().exit_code == int(ExitCode.RUN_REFUSED)  # same command, no flag, no approval


def _mcp_call(tool: str, args: dict):
    from mcp.client import Client

    from autotester.mcp_server import server

    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(go())


def test_the_server_exposes_exactly_three_tools() -> None:
    from autotester.mcp_server import server
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {"run_tests", "get_report", "get_catalog"}


def test_run_tool_without_an_approval_starts_nothing(root, monkeypatch) -> None:
    store = seed_project(root)
    install_fakes(monkeypatch)
    result = _mcp_call("run_tests", {"project": "demo"})
    report = RunReport.model_validate(result.structured_content)
    assert report.exit_code == int(ExitCode.RUN_REFUSED) and report.run_id is None
    assert not store.paths.runs_dir.exists() or not list(store.paths.runs_dir.iterdir())


def test_run_tool_with_an_approval_runs_and_reports(root, monkeypatch) -> None:
    seed_project(root, approve=True)
    install_fakes(monkeypatch)
    ran = _mcp_call("run_tests", {"project": "demo"}).structured_content
    report = RunReport.model_validate(ran)
    assert report.status == "passed" and report.run_id
    again = _mcp_call("get_report", {"project": "demo"}).structured_content
    assert RunReport.model_validate(again).run_id == report.run_id
    cat = _mcp_call("get_catalog", {"project": "demo"}).structured_content
    assert Catalog.model_validate(cat).project == "demo"


def test_the_server_calls_the_functions_the_cli_calls() -> None:
    """No second implementation of a stage: the adapter imports run_ops and schema, nothing else."""
    def autotester_imports(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("autotester"):
                found |= {f"{node.module}.{a.name}" if node.module == "autotester" else node.module
                          for a in node.names}
        return found

    allowed = ("autotester.run_ops", "autotester.schema", "autotester.core.env")
    server = autotester_imports(SRC / "mcp_server.py")
    assert server and all(m.startswith(allowed) for m in server), server
    for fn in (run_ops.perform_run, run_ops.get_report, run_ops.get_catalog):
        assert any(v is fn for v in vars(cli_run).values()), fn


def test_stdio_transport_lists_tools_and_never_leaks_a_secret(root) -> None:
    """Real bounded transport, including a malformed-input secret at the catalog door."""
    from mcp.client import Client
    from mcp.client.stdio import StdioServerParameters, stdio_client

    from autotester.schema.run import RawResult, Run
    from autotester.schema.verdict import Failure, Verdict
    store = seed_project(root, secret=True)
    case = store.list_cases()[0]
    store.save_run(Run(id="run-1", project="demo", case_ids=[case.id]))
    store.save_result("run-1", RawResult(case_id=case.id, outcome="errored", error=SECRET_VALUE))
    store.save_verdict("run-1", Verdict(run_id="run-1", case_id=case.id, result=Result.FAIL,
                                        failures=[Failure(criterion_id="c", reason=SECRET_VALUE)]))
    params = StdioServerParameters(command=sys.executable, args=["-m", "autotester.mcp_server"],
                                   env={"AUTOTESTER_ROOT": str(root), "PATH": "",
                                        "PYTHONPATH": str(SRC.parent)})

    stderr_path = root / "stdio-stderr.txt"
    async def go(stderr):
        async with Client(stdio_client(params, errlog=stderr)) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            result = await client.call_tool("get_report", {"project": "demo"})
            bad = await client.call_tool("get_catalog", {"project": SECRET_VALUE})
            invalid = [await client.call_tool(tool, {"project": {"private": SECRET_VALUE}})
                       for tool in tools]
            invalid.append(await client.call_tool(SECRET_VALUE, {"project": "demo"}))
            return tools, result, bad, invalid
    with stderr_path.open("w", encoding="utf-8") as stderr:
        tools, result, bad, invalid = asyncio.run(asyncio.wait_for(go(stderr), timeout=30))
    assert tools == {"run_tests", "get_report", "get_catalog"}
    assert SECRET_VALUE not in json.dumps([result.structured_content, bad.structured_content])
    assert SECRET_VALUE not in str([result.content, bad.content])
    assert RunReport.model_validate(bad.structured_content).exit_code == int(ExitCode.USAGE)
    assert SECRET_VALUE not in stderr_path.read_text(encoding="utf-8")
    for error in invalid:
        assert SECRET_VALUE not in json.dumps(error.model_dump(mode="json"))
        assert error.is_error
        assert (RunReport.model_validate(error.structured_content).exit_code
                == int(ExitCode.INTERNAL))

def test_mcp_is_a_declared_dependency() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    deps = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["dependencies"]
    assert any(d.startswith("mcp") for d in deps)
    from autotester import doctor
    assert not [v for v in doctor.run() if v.rule == "undeclared-dependency"]


def test_credential_matching_a_controlled_status_keeps_outputs_typed(root):
    from autotester.mcp_server import tool_get_report

    (root / ".env").write_text("PASSWORD=usage\n", encoding="utf-8")
    result = _run("--output", "json")
    assert _report(result).status == "usage_error" and result.exit_code == int(ExitCode.USAGE)
    report = tool_get_report("unknown")
    assert isinstance(report, RunReport) and report.status == "usage_error"

