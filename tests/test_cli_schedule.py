"""`autotester schedule tick` (TS7): the stateless, externally driven entry that makes the
scheduler run on this machine. Exit 0 handled / 2 blocked or failed / 3 invalid config;
`--dry-run` claims nothing; `--output json` is one document on stdout, warnings on stderr.

The clock and the queue are the module's two seams (`_now`, `_open_queue`), so no test sleeps,
starts a thread or reaches a browser.
"""

from __future__ import annotations

import ast
import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest
from schedule_fakes import daily, utc
from typer.testing import CliRunner

from autotester import cli_schedule
from autotester.cli import app
from autotester.schema.project import Project
from autotester.schema.run_queue import QueueEntry
from autotester.schema.schedule import ScheduleConfig, TickReport
from autotester.stages.schedule_wiring import schedule_paths
from autotester.store.project_store import ProjectStore
from autotester.ui.run_queue import RunQueue

runner = CliRunner()
DUE = utc(2026, 10, 8, 9, 0, 10)
SAVED = utc(2026, 10, 7, 12)


class Manual:
    def __init__(self) -> None:
        self.pending: list[Callable[[], None]] = []

    def __call__(self, job: Callable[[], None]) -> None:
        self.pending.append(job)


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.delenv("AUTOTESTER_SCHEDULE_GRACE_MINUTES", raising=False)
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")  # AU17 loopback single-user: no owner
    monkeypatch.setattr(cli_schedule, "_now", lambda: DUE)
    manual = Manual()
    queue = RunQueue(limit=lambda: 2, spawn=manual, runner=lambda e: None)
    monkeypatch.setattr(cli_schedule, "_open_queue", lambda: queue)
    return tmp_path


def _project(root: Path, slug: str = "demo", schedule: ScheduleConfig | None = None) -> None:
    store = ProjectStore(slug, root)
    store.save_project(Project(slug=slug, name=slug, base_url="https://demo.test",
                               allowed_domains=["demo.test"],
                               schedule=schedule if schedule is not None else daily()))
    os.utime(store.paths.config, (SAVED.timestamp(), SAVED.timestamp()))


def test_nothing_scheduled_exits_0_and_writes_the_heartbeat(root: Path) -> None:
    result = runner.invoke(app, ["schedule", "tick"])
    assert result.exit_code == 0, result.output
    assert schedule_paths(root).heartbeat.is_file()


def test_json_output_is_one_document_and_warnings_go_to_stderr(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOTESTER_SCHEDULE_GRACE_MINUTES", "0")
    result = CliRunner(mix_stderr=False).invoke(app, ["schedule", "tick", "--output", "json"]) \
        if "mix_stderr" in CliRunner.__init__.__code__.co_varnames else \
        runner.invoke(app, ["schedule", "tick", "--output", "json"])
    assert result.exit_code == 0
    report = TickReport.model_validate_json(result.stdout)
    assert report.tick_at == DUE and report.dry_run is False
    assert "AUTOTESTER_SCHEDULE_GRACE_MINUTES" in result.stderr


def test_a_scheduled_project_without_credentials_is_blocked_and_exits_2(root: Path) -> None:
    _project(root)
    result = runner.invoke(app, ["schedule", "tick", "--output", "json"])
    report = TickReport.model_validate_json(result.stdout)
    assert result.exit_code == 2
    assert [r.outcome.value for r in report.records] == ["blocked_no_credentials"]


def test_a_stored_schedule_that_will_not_load_exits_3(root: Path) -> None:
    _project(root)
    config = ProjectStore("demo", root).paths.config
    data = json.loads(config.read_text(encoding="utf-8"))
    data["schedule"]["timezone"] = "America/New_York"
    config.write_text(json.dumps(data), encoding="utf-8")
    result = runner.invoke(app, ["schedule", "tick", "--output", "json"])
    assert result.exit_code == 3 and TickReport.model_validate_json(result.stdout).invalid == [
        "demo"]


def test_dry_run_claims_nothing_and_writes_no_heartbeat(root: Path) -> None:
    _project(root)
    result = runner.invoke(app, ["schedule", "tick", "--dry-run", "--output", "json"])
    paths = schedule_paths(root)
    report = TickReport.model_validate_json(result.stdout)
    assert report.dry_run and report.would_block == ["demo:fixed:2026-10-08T09:00Z"]
    assert result.exit_code == 2
    assert not paths.claims.exists() and not paths.heartbeat.exists()


def test_project_option_limits_the_pass(root: Path) -> None:
    _project(root, "alpha")
    _project(root, "beta")
    result = runner.invoke(app, ["schedule", "tick", "--project", "beta", "--dry-run",
                                 "--output", "json"])
    keys = TickReport.model_validate_json(result.stdout).would_block
    assert keys == ["beta:fixed:2026-10-08T09:00Z"]


def test_text_output_names_each_outcome(root: Path) -> None:
    _project(root)
    result = runner.invoke(app, ["schedule", "tick"])
    assert "blocked_no_credentials" in result.output and "demo" in result.output


def test_the_dry_run_never_opens_a_queue(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> RunQueue:
        raise AssertionError("a dry run must not open the run queue")

    monkeypatch.setattr(cli_schedule, "_open_queue", boom)
    _project(root)
    assert runner.invoke(app, ["schedule", "tick", "--dry-run"]).exit_code == 2


def test_a_tick_with_nothing_due_never_opens_a_queue(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> RunQueue:
        raise AssertionError("nothing is due: the run queue (and the UI stack) must not load")

    monkeypatch.setattr(cli_schedule, "_open_queue", boom)
    _project(root)
    monkeypatch.setattr(cli_schedule, "_now", lambda: utc(2026, 10, 8, 5, 0, 10))
    assert runner.invoke(app, ["schedule", "tick"]).exit_code == 0


def test_the_tick_process_queue_is_private_and_never_recovers_the_servers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tick in its own process must not `recover()` the server's file (that would mark the
    server's running runs `interrupted`) nor write it: its queue is in memory only."""
    from autotester.ui import routes_runs, run_queue

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    server_file = tmp_path / ".work" / "run_queue.json"
    server_file.parent.mkdir(parents=True)
    running = QueueEntry(id="run-1", project="demo", status="running")  # type: ignore[arg-type]
    server_file.write_text(json.dumps({"entries": [json.loads(running.model_dump_json())]}),
                           encoding="utf-8")
    before = server_file.read_bytes()
    monkeypatch.setattr(run_queue, "_QUEUE", None)
    queue = routes_runs.tick_queue()
    assert run_queue.get_queue() is queue and queue.snapshot() == []
    queue.submit("other")
    assert server_file.read_bytes() == before
    assert [e.id for e in run_queue.persisted_entries()] == ["run-1"]


def test_cli_schedule_reaches_no_browser_or_runner_directly() -> None:
    """TS6: the command holds no import of the browser, a runner or a pipeline module. It
    reaches the executor only through `ui.routes_runs.tick_queue`, the door the UI uses."""
    source = Path(cli_schedule.__file__).read_text(encoding="utf-8")
    names: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.Import):
            modules |= {a.name for a in node.names}
    banned = {"BrowserSession", "run_and_grade_case", "run_and_grade_case_resilient",
              "_execute_with_trace", "launch_run", "prepare_run", "Run"}
    assert not names & banned
    assert not any(m.startswith(("autotester.browser", "autotester.stages.orchestrate",
                                 "autotester.stages.run_launcher", "autotester.stages.explore"))
                   for m in modules), modules


def test_a_real_tick_waits_for_the_runs_it_started(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Walk r3: the command drains the tick's runs before it exits (not on --dry-run)."""
    from autotester.ui import routes_runs

    waited: list[bool] = []
    monkeypatch.setattr(routes_runs, "wait_for_tick_runs", lambda: waited.append(True))
    runner.invoke(app, ["schedule", "tick", "--dry-run"])
    assert waited == []
    runner.invoke(app, ["schedule", "tick"])
    assert waited == [True]
