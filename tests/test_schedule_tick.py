"""TS7 (tick side): one stateless pass over every scheduled project, its heartbeat, its
`--dry-run`, and the 0/2/3 exit codes the `autotester schedule tick` shell will return.
The shell itself needs `Project.schedule` (T-205) and is not built here."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest
from schedule_fakes import daily, make_deps, utc

import autotester
from autotester.schema.schedule import (
    ScheduleConfig,
    SchedulerHealth,
    SlotOutcome,
    TickReport,
)
from autotester.stages.schedule_store import list_claims, read_heartbeat, read_records
from autotester.stages.schedule_tick import ScheduledProject, run_tick
from autotester.stages.scheduler import scheduler_health

SINCE = utc(2026, 10, 7, 12)
DUE = utc(2026, 10, 8, 9, 0, 10)
IDLE = utc(2026, 10, 8, 5, 0, 10)


def _run(tmp_path: Path, items, now, *, gate=None, **kw):
    decks = {}

    def deps_for(project: str):
        if project not in decks:
            decks[project] = make_deps(tmp_path / project, project, gate=gate)
        return decks[project][0]

    report = run_tick(items, now, deps_for=deps_for, heartbeat_path=tmp_path / "hb.json", **kw)
    return report, decks


def _item(project: str = "p", schedule: ScheduleConfig | None = None) -> ScheduledProject:
    return ScheduledProject(project, schedule or daily(), SINCE)


def test_nothing_due_exits_0_and_still_writes_the_heartbeat(tmp_path: Path) -> None:
    report, _ = _run(tmp_path, [_item()], IDLE)
    assert report.exit_code == 0 and report.records == []
    assert read_heartbeat(tmp_path / "hb.json") == IDLE


def test_a_due_slot_is_enqueued_recorded_and_the_tick_exits_0(tmp_path: Path) -> None:
    report, decks = _run(tmp_path, [_item()], DUE)
    assert report.exit_code == 0
    assert [r.outcome for r in report.records] == [SlotOutcome.ENQUEUED]
    assert len(decks["p"][1]) == 1 and read_heartbeat(tmp_path / "hb.json") == DUE


def test_a_blocked_slot_exits_2(tmp_path: Path) -> None:
    report, decks = _run(tmp_path, [_item()], DUE, gate=lambda slot: "no_secretref: x")
    assert [r.outcome for r in report.records] == [SlotOutcome.BLOCKED_NO_CREDENTIALS]
    assert report.exit_code == 2 and len(decks["p"][1]) == 0


def test_an_enqueue_that_raises_is_a_failed_record_with_its_cause_and_exits_2(
    tmp_path: Path,
) -> None:
    def deps_for(project: str):
        deps, _ = make_deps(tmp_path / project, project)

        def boom(slot):
            raise ConnectionError("queue down")

        return replace(deps, enqueue=boom)

    report = run_tick([_item()], DUE, deps_for=deps_for, heartbeat_path=tmp_path / "hb.json")
    assert report.exit_code == 2 and report.records[0].outcome is SlotOutcome.FAILED
    assert "ConnectionError" in (report.records[0].detail or "")


def test_an_invalid_config_name_exits_3_but_the_valid_projects_are_still_ticked(
    tmp_path: Path,
) -> None:
    report, decks = _run(tmp_path, [_item()], DUE, invalid=["broken"])
    assert report.exit_code == 3 and report.invalid == ["broken"]
    assert len(decks["p"][1]) == 1 and read_heartbeat(tmp_path / "hb.json") == DUE


def test_one_project_that_crashes_does_not_stop_the_others(tmp_path: Path) -> None:
    def deps_for(project: str):
        if project == "bad":
            raise OSError("disk path with a secret-looking value")
        return make_deps(tmp_path / project, project)[0]

    report = run_tick([_item("bad"), _item("good")], DUE, deps_for=deps_for,
                      heartbeat_path=tmp_path / "hb.json")
    assert report.exit_code == 2
    assert report.errors == ["bad: OSError"]  # the class only: a message may carry a secret
    assert [r.project for r in report.records] == ["good"]
    assert read_heartbeat(tmp_path / "hb.json") == DUE


def test_dry_run_prints_what_would_fire_and_changes_nothing(tmp_path: Path) -> None:
    report, decks = _run(tmp_path, [_item()], DUE, dry_run=True)
    deps, q = decks["p"]
    assert report.dry_run and report.exit_code == 0
    assert report.would_fire == ["p:fixed:2026-10-08T09:00Z"] and report.records == []
    assert list_claims(deps.claim_dir) == {} and not deps.claim_dir.exists()
    assert read_records(deps.records_path) == [] and len(q) == 0
    assert read_heartbeat(tmp_path / "hb.json") is None


def test_dry_run_with_a_blocking_preview_lists_would_block_and_exits_2(tmp_path: Path) -> None:
    report, _ = _run(tmp_path, [_item()], DUE, dry_run=True,
                     preview=lambda project: "no_secretref: x")
    assert report.would_fire == [] and report.would_block == ["p:fixed:2026-10-08T09:00Z"]
    assert report.exit_code == 2


def test_the_report_is_one_valid_json_document(tmp_path: Path) -> None:
    report, _ = _run(tmp_path, [_item()], DUE)
    parsed = json.loads(report.model_dump_json())
    assert TickReport.model_validate(parsed).exit_code == 0 and parsed["records"][0]["project"]


def test_a_manual_project_never_fires_however_many_ticks_run(tmp_path: Path) -> None:
    manual = ScheduleConfig()
    for n in range(5):
        report, decks = _run(tmp_path, [_item("m", manual)], utc(2026, 10, 8 + n, 9, 0, 10))
        assert report.records == [] and report.exit_code == 0
    assert len(decks["m"][1]) == 0


def test_the_heartbeat_a_tick_writes_is_what_the_stale_card_reads(tmp_path: Path) -> None:
    sched = daily()
    assert scheduler_health(sched, read_heartbeat(tmp_path / "hb.json"), DUE
                            ).state is SchedulerHealth.NEVER_TICKED
    _run(tmp_path, [_item()], DUE)
    status = scheduler_health(sched, read_heartbeat(tmp_path / "hb.json"), DUE)
    assert status.state is SchedulerHealth.HEALTHY and status.since == DUE



# --- TS6 guard: the scheduler side never reaches a browser or a pipeline module ---------------
SCHEDULER_SIDE = ("autotester.stages.scheduler", "autotester.stages.schedule_store",
                  "autotester.stages.schedule_time", "autotester.stages.schedule_gate",
                  "autotester.stages.schedule_tick")
# Outside core/, schema/ and store/, the scheduler side may reach exactly these modules. Anything
# else (a runner, a pipeline stage, the browser session, a provider, the UI app, a CLI) fails.
ALLOWED_OUTSIDE = frozenset(SCHEDULER_SIDE) | {
    "autotester.stages", "autotester.stages.explore_consent", "autotester.browser",
    "autotester.browser.secrets", "autotester.ui", "autotester.ui.env_editor"}
PLAIN_PACKAGES = ("core", "schema", "store")
BANNED_NAMES = {"BrowserSession", "run_and_grade_case", "run_and_grade_case_resilient",
                "_execute_with_trace"}
SRC = Path(autotester.__file__).parent


def _file_of(module: str) -> Path | None:
    rel = Path(*module.split(".")[1:])
    for candidate in (SRC / rel / "__init__.py", SRC / rel.with_suffix(".py")):
        if module != "autotester" and candidate.is_file():
            return candidate  # the root package is the CLI entry, never scheduler code
    return None


def _imports(module: str, text: str) -> tuple[set[str], set[str], list[str]]:
    """(repo modules imported, names imported, dynamic-import calls) of `text`, in any form and
    at any depth (lazy imports too). `from a import b` also counts `a.b` when that is a module."""
    here = _file_of(module)
    package = module if here and here.name == "__init__.py" else module.rsplit(".", 1)[0]
    found: set[str] = set()
    names: set[str] = set()
    dynamic: list[str] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                up = package.split(".")[: len(package.split(".")) - (node.level - 1)]
                base = ".".join(up + ([node.module] if node.module else []))
            found |= {base} | {f"{base}.{a.name}" for a in node.names}
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.Call):
            fn = node.func
            called = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if called in {"import_module", "__import__"}:
                dynamic.append(called)
    repo = {".".join(p[:n]) for p in (d.split(".") for d in found) if p[0] == "autotester"
            for n in range(2, len(p) + 1) if _file_of(".".join(p[:n]))}
    return repo, names, dynamic


def scheduler_side_violations(patched: dict[str, str] | None = None) -> list[str]:
    """Static import closure of the scheduler-side modules. Static, because importing them in a
    subprocess proves nothing: the root package's `__init__` imports the whole CLI, so
    `sys.modules` always holds the browser. `patched` swaps a module's source (self-tests)."""
    patched = patched or {}
    problems: list[str] = []
    seen: set[str] = set()
    todo = list(SCHEDULER_SIDE)
    while todo:
        module = todo.pop()
        if module in seen:
            continue
        seen.add(module)
        text = patched.get(module) or _file_of(module).read_text(encoding="utf-8")
        repo, names, dynamic = _imports(module, text)
        problems += [f"{module}: dynamic import via {called}()" for called in dynamic]
        if module in SCHEDULER_SIDE:
            problems += [f"{module}: imports {n}" for n in sorted(names & BANNED_NAMES)]
        for dep in sorted(repo):
            if dep not in ALLOWED_OUTSIDE and dep.split(".")[1] not in PLAIN_PACKAGES:
                problems.append(f"{module} -> {dep}")
            todo.append(dep)
    return problems


def test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively() -> None:
    """TS6: the tick holds no import of BrowserSession, the runners or the pipeline modules.
    The real tree is clean, so adding any such import (direct, `from pkg import module`, lazy
    inside a function, or reached through another stage) fails here."""
    assert scheduler_side_violations() == []


LEAKS = {
    "from-import of a pipeline module": (
        "autotester.stages.scheduler", "from autotester.stages import explore"),
    "from-import of the browser session": (
        "autotester.stages.scheduler", "from autotester.browser import session"),
    "plain import of the browser session": (
        "autotester.stages.schedule_tick", "import autotester.browser.session"),
    "a stage that itself reaches the browser": (
        "autotester.stages.scheduler", "from autotester.stages.agent_loop import x"),
    "the gate importing the session": (
        "autotester.stages.schedule_gate", "from autotester.browser.session import BrowserSession"),
    "a lazy import inside a function": (
        "autotester.stages.schedule_store",
        "def f():\n    from autotester.stages import explore"),
    "a relative import": ("autotester.stages.schedule_time", "from . import explore"),
    "a string import": (
        "autotester.stages.schedule_tick", "import importlib\nimportlib.import_module('x')"),
}


@pytest.mark.parametrize("leak", sorted(LEAKS))
def test_the_guard_catches_each_way_of_reaching_the_pipeline(leak: str) -> None:
    module, line = LEAKS[leak]
    source = _file_of(module).read_text(encoding="utf-8")
    assert scheduler_side_violations({module: source + "\n" + line + "\n"}), leak
