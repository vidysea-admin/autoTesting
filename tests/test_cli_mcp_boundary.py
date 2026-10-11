"""T-174 machine-surface boundaries (qa/contracts/cli-mcp.md CM1, CM2, CM4, CM5): no secret and no
raw SDK text leaves the CLI or the MCP server, and a run can only start through the launcher.

Split from `test_cli_mcp.py` at doctor's 300-line cap, by responsibility: that file proves the
happy contract (codes, JSON, dry run, tools); this one proves what must never leave the process
and that the gate is not a parameter. The parser-refusal clause of CM2 is NOT covered here: it
is held on `qa/gates/t174-parser-recovery.md`.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from autotester import mcp_server, run_ops
from autotester.cli import app
from autotester.schema.project import Project
from autotester.stages import run_launcher
from autotester.store.project_store import ProjectStore

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize("tool,arguments", [
    (tool, {"project": {"private": "synthetic-mcp-boundary-secret"}})
    for tool in ("run_tests", "get_report", "get_catalog")
] + [("run_tests", {"project": "demo", "dry_run": {"private": "synthetic-mcp-boundary-secret"}}),
     ("get_report", {"project": "demo", "run_id": {"private": "synthetic-mcp-boundary-secret"}}),
     ("synthetic-mcp-boundary-secret", {"project": "demo"})])
def test_sdk_errors_are_typed_without_echoing_inputs(tool, arguments, root, caplog):
    import asyncio
    import json
    import logging

    from mcp.client import Client

    from autotester.mcp_server import server
    from autotester.schema.cli_output import ExitCode, RunReport

    secret = "synthetic-mcp-boundary-secret"
    (root / ".env").write_text(f"OTHER_PASSWORD={secret}\n", encoding="utf-8")
    caplog.set_level(logging.DEBUG)

    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, arguments)

    result = asyncio.run(asyncio.wait_for(go(), 15))
    assert secret not in json.dumps(result.model_dump(mode="json"))
    assert secret not in caplog.text
    assert result.is_error
    assert RunReport.model_validate(result.structured_content).exit_code == int(ExitCode.INTERNAL)


@pytest.mark.parametrize("name", ["mcp.server.mcpserver.server", "mcp.server.runner",
                                 "mcp.shared.jsonrpc_dispatcher", "mcp.shared.dispatcher"])
@pytest.mark.parametrize("unreadable", [False, True])
def test_sdk_log_boundary_removes_exception_and_stack_inputs(name, unreadable, root, caplog):
    import logging
    import sys

    import autotester.mcp_server  # noqa: F401 -- installs filters without loading credentials

    secret = "synthetic-mcp-log-secret"
    if unreadable:
        (root / ".env").mkdir()
    else:
        (root / ".env").write_text(f"OTHER_PASSWORD={secret}\n", encoding="utf-8")
    logger = logging.getLogger(name)
    try:
        raise ValueError(secret)
    except ValueError:
        record = logger.makeRecord(name, logging.ERROR, __file__, 1, "SDK %s", (secret,),
                                   sys.exc_info(), sinfo=secret)
    record.exc_text = secret
    logger.handle(record)
    assert caplog.records and secret not in caplog.text
    assert record.args == () and record.exc_info is None
    assert record.exc_text is None and record.stack_info is None


def test_malformed_rpc_params_keep_protocol_rejection_without_inputs(root):
    import asyncio

    from mcp.client import Client
    from mcp.shared.exceptions import MCPError
    from mcp.types import INVALID_PARAMS, CallToolResult, Request

    from autotester.mcp_server import server

    async def go():
        async with Client(server) as client:
            with pytest.raises(MCPError) as caught:
                await client.session.send_request(Request(method="tools/call", params={
                    "name": {"private": "synthetic-rpc-secret"}}), CallToolResult)
            assert caught.value.code == INVALID_PARAMS
            assert "synthetic-rpc-secret" not in repr(caught.value.error)
    asyncio.run(asyncio.wait_for(go(), 15))


def test_sdk_boundary_preserves_handshake_error_and_unchanged_context():
    import asyncio
    from types import SimpleNamespace

    from mcp.shared.exceptions import MCPError
    from mcp.types import INVALID_PARAMS

    from autotester.mcp_server import _safe_sdk_boundary

    ctx = SimpleNamespace(method="tools/call", params={"private": "synthetic-rpc-secret"})
    calls = []
    async def denied(actual):
        calls.append(actual)
        raise MCPError(code=INVALID_PARAMS, message="synthetic-rpc-secret", data=ctx.params)
    with pytest.raises(MCPError) as caught:
        asyncio.run(_safe_sdk_boundary(ctx, denied))
    assert calls == [ctx] and calls[0] is ctx
    assert caught.value.code == INVALID_PARAMS and caught.value.data is None
    assert "synthetic-rpc-secret" not in str(caught.value)



@pytest.mark.parametrize("surface", ["run", "report", "catalog", "mcp-run",
                                   "mcp-report", "mcp-catalog"])
@pytest.mark.parametrize("corrupt", [False, True], ids=["unknown", "corrupt"])
def test_machine_error_surfaces_mask_secrets_without_a_valid_project(root, surface, corrupt):
    """C5 applies before project parsing succeeds, across CLI and MCP errors."""
    import json

    from cli_mcp_fixture import SECRET_VALUE, seed_project

    from autotester import mcp_server
    from autotester.schema.cli_output import ExitCode, RunReport

    (root / ".env").write_text(f"OTHER_PASSWORD={SECRET_VALUE}\n", encoding="utf-8")
    slug = SECRET_VALUE
    if corrupt:
        store = seed_project(root)
        data = json.loads(store.paths.config.read_text(encoding="utf-8"))
        data["unexpected"] = SECRET_VALUE
        store.paths.config.write_text(json.dumps(data), encoding="utf-8")
        slug = "demo"
    if surface.startswith("mcp-"):
        fn = {"mcp-run": mcp_server.tool_run_tests, "mcp-report": mcp_server.tool_get_report,
              "mcp-catalog": mcp_server.tool_get_catalog}[surface]
        report = fn(slug, dry_run=True) if surface == "mcp-run" else fn(slug)
        if surface == "mcp-catalog":
            assert report.is_error
            report = RunReport.model_validate(report.structured_content)
        assert isinstance(report, RunReport)
        output = report.model_dump_json()
    else:
        argv = {"run": ["run", slug, "--dry-run"], "report": ["report", "show", slug],
                "catalog": ["catalog", slug]}[surface]
        result = runner.invoke(app, [*argv, "--output", "json"])
        report = RunReport.model_validate_json(result.stdout)
        output = result.stdout + result.stderr
        assert result.exit_code == report.exit_code
    assert report.exit_code == int(ExitCode.USAGE)
    assert SECRET_VALUE not in output


def test_unreadable_masking_source_withholds_every_error_string(root, monkeypatch):
    """An error reading credentials must not fall back to an empty redactor."""
    from cli_mcp_fixture import SECRET_VALUE

    from autotester import run_ops
    from autotester.schema.cli_output import RunReport

    env_file = root / ".env"
    env_file.write_text(f"OTHER_PASSWORD={SECRET_VALUE}\n", encoding="utf-8")
    original = Path.read_text

    def deny(path, *args, **kwargs):
        if path == env_file:
            raise PermissionError("cannot read masking source")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny)
    report = run_ops.error_report(SECRET_VALUE, RuntimeError(SECRET_VALUE))
    assert isinstance(report, RunReport) and report.exit_code != 0
    assert SECRET_VALUE not in report.model_dump_json()
    success = run_ops._scrubbed(RunReport(project=SECRET_VALUE, status="passed", exit_code=0))
    assert success.exit_code != 0 and success.status == "infrastructure_error"
    assert SECRET_VALUE not in success.model_dump_json()



def test_text_catalog_masks_a_valid_project_argument(root):
    """A successful text heading must use the scrubbed model, not the raw slug."""
    secret = "privatecatalog"
    (root / ".env").write_text(f"OTHER_PASSWORD={secret}\n", encoding="utf-8")
    ProjectStore(secret, root).save_project(Project(
        slug=secret, name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
    result = runner.invoke(app, ["catalog", secret])
    assert result.exit_code == 0, result.output
    assert secret not in result.stdout + result.stderr
    assert "[REDACTED]" in result.stdout


def test_a_run_is_only_ever_started_by_the_launcher() -> None:
    """CM4: `run_ops` reaches a run through `launch_run` and offers no way to skip its gate."""
    src = Path(inspect.getsourcefile(run_ops)).read_text(encoding="utf-8")
    assert "launch_run(" in src and src.count("launch_run(") == 1
    assert run_ops.launch_run is run_launcher.launch_run
    for fn in (run_ops.perform_run, mcp_server.tool_run_tests):
        names = set(inspect.signature(fn).parameters)
        assert not {n for n in names if "approv" in n or "skip" in n or "force" in n}, names
    assert set(inspect.signature(mcp_server.tool_run_tests).parameters) == {"project", "dry_run"}



@pytest.mark.parametrize("slug", ["../escape", "Upper", "a/b", ".."])
def test_an_unsafe_slug_is_usage_and_never_reaches_the_store(slug, root, monkeypatch):
    """CM1: a slug that is not a slug is a usage error on every surface, before any disk read."""
    from cli_mcp_fixture import install_fakes

    from autotester.schema.cli_output import ExitCode
    install_fakes(monkeypatch)
    for argv in (["run", slug, "--dry-run"], ["run", slug], ["catalog", slug],
                 ["report", "show", slug]):
        result = runner.invoke(app, [*argv, "--output", "json"])
        assert result.exit_code == int(ExitCode.USAGE), (argv, result.output)
    assert not (root / "projects").exists()


def test_report_show_joins_the_existing_report_group_and_clobbers_nothing():
    from autotester.cli_run import attach_commands

    names = {"excel", "html", "crawl", "show"}
    out = runner.invoke(app, ["report", "--help"]).output
    assert all(name in out for name in names), out
    fresh = typer.Typer()
    attach_commands(fresh)           # an app with no `report` group gets one, not an error
    assert "show" in runner.invoke(fresh, ["report", "--help"]).output


@pytest.mark.parametrize("surface", ["cli", "mcp"])
def test_a_machine_run_is_attributed_to_its_surface(surface, root, monkeypatch):
    """The saved Run says which surface asked and that it was not the Run button."""
    from cli_mcp_fixture import install_fakes, seed_project

    from autotester.schema.enums import Trigger
    store = seed_project(root, approve=True)
    install_fakes(monkeypatch)
    if surface == "cli":
        runner.invoke(app, ["run", "demo", "--output", "json"])
    else:
        mcp_server.tool_run_tests("demo")
    saved = store.load_run(next(p.name for p in store.paths.runs_dir.iterdir()))
    assert saved.trigger is Trigger.CI and saved.requested_by == surface


@pytest.mark.parametrize("run_id", ["../../other/secretdir", "a/b", "..", "C:/Windows", "-x"])
def test_an_unsafe_run_id_is_usage_and_reads_nothing(run_id, root):
    """Review finding (high): `run_id` is a path segment. No surface may resolve it outside the
    project's runs directory, and no file content may come back in the error text."""
    from cli_mcp_fixture import SECRET_VALUE, seed_project

    from autotester.schema.cli_output import ExitCode, RunReport
    seed_project(root)
    planted = root / "projects" / "other" / "secretdir"   # what `../../other/secretdir` resolves to
    planted.mkdir(parents=True)
    (planted / "run.json").write_text(f"{SECRET_VALUE} not json", "utf-8")
    cli = runner.invoke(app, ["report", "show", "demo", run_id, "--output", "json"])
    assert cli.exit_code == int(ExitCode.USAGE), cli.output
    assert SECRET_VALUE not in cli.output
    for report in (run_ops.get_report("demo", run_id), mcp_server.tool_get_report("demo", run_id)):
        assert isinstance(report, RunReport) and report.exit_code == int(ExitCode.USAGE)
        assert SECRET_VALUE not in report.model_dump_json()
