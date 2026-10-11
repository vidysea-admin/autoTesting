"""TS7 (tick side): one stateless pass over every scheduled project, its heartbeat, its
`--dry-run`, and the 0/2/3 exit codes the `autotester schedule tick` shell will return.
The shell itself needs `Project.schedule` (T-205) and is not built here."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from schedule_fakes import daily, make_deps, utc

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


def test_deleting_a_project_purges_its_claims_and_records_and_only_its_own(
    tmp_path: Path,
) -> None:
    """TS1 clause HO24 leaves open: markers and records go with the project, a neighbour with a
    longer slug that merely starts the same does not."""
    from autotester.stages.schedule_store import purge_project

    deps, _ = make_deps(tmp_path / "shared", "p")
    for slug in ("p", "pp"):
        run_tick([_item(slug)], DUE, deps_for=lambda _slug: deps,
                 heartbeat_path=tmp_path / "hb.json")
    assert len(list_claims(deps.claim_dir)) == 2 and len(read_records(deps.records_path)) == 2
    purge_project(deps.claim_dir, deps.records_path, "p")
    assert [r.project for r in read_records(deps.records_path)] == ["pp"]
    assert list(list_claims(deps.claim_dir)) == ["pp:fixed:2026-10-08T09:00Z"]
    purge_project(deps.claim_dir, deps.records_path, "p")  # idempotent
    assert len(read_records(deps.records_path)) == 1


def test_the_tick_modules_import_no_browser_or_pipeline_code() -> None:
    """The TS6 guard that can be written now: the tick starts nothing itself. (The full TS6 row,
    one launcher for the tick, the Test button and `trigger_run`, waits on `run_launcher.py`.)"""
    import ast

    import autotester.stages as stages

    banned_modules = {"browser.session", "stages.execute", "stages.run_case_pipeline",
                      "stages.parallel_run", "stages.explore", "stages.orchestrate",
                      "ui.routes_runs", "ui.run_execution"}
    banned_names = {"BrowserSession", "run_and_grade_case", "_execute_with_trace"}
    root = Path(stages.__file__).parent
    for name in ("scheduler.py", "schedule_tick.py", "schedule_store.py", "schedule_time.py"):
        for node in ast.walk(ast.parse((root / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").removeprefix("autotester.")
                assert module not in banned_modules, f"{name} imports {node.module}"
                assert not {a.name for a in node.names} & banned_names, name
            elif isinstance(node, ast.Import):
                assert not {a.name.removeprefix("autotester.") for a in node.names
                            } & banned_modules, name
