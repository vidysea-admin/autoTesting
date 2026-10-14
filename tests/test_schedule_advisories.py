"""T-200 advisories: cross-process append safety and the per-slot sweep bound."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from test_schedule_gaps import NOW, _enqueued, _save

from autotester.schema.run import Run, RunBounds
from autotester.schema.schedule import SlotOutcome
from autotester.stages.schedule_store import read_records
from autotester.stages.schedule_sweep import STALE_AFTER, stale_after_for, sweep_dead_enqueued
from autotester.stages.schedule_wiring import schedule_paths

H = 3600.0


def test_stale_after_for_floor_margin_and_cap() -> None:
    assert stale_after_for(None) == STALE_AFTER
    assert stale_after_for(0) == STALE_AFTER and stale_after_for(-5) == STALE_AFTER
    assert stale_after_for(600) == STALE_AFTER                      # short bound: 3h floor
    assert stale_after_for(5 * H) == timedelta(hours=5, minutes=30)  # bound + margin
    assert stale_after_for(600_000_000.0) == timedelta(hours=24)     # absurd: capped
    assert stale_after_for(float("inf")) == timedelta(hours=24)


def _run_with_bound(store, seconds: float) -> None:
    store.save_run(Run(id="run-q1", project="demo", bounds=RunBounds(
        approval_id="a", max_actions=1, max_probes=1, wall_clock_s=seconds)))


def test_sweep_spares_a_run_inside_its_own_approved_bound(tmp_path: Path) -> None:
    path, _ = _enqueued(tmp_path)
    store = _save(tmp_path)
    _run_with_bound(store, 6 * H)
    records = schedule_paths(tmp_path).records
    assert sweep_dead_enqueued("demo", records, NOW + timedelta(hours=5), set, store) == 0
    assert read_records(path)[0].outcome is SlotOutcome.ENQUEUED
    assert sweep_dead_enqueued("demo", records, NOW + timedelta(hours=7), set, store) == 1


def test_sweep_still_fires_for_an_absurd_bound_after_24h(tmp_path: Path) -> None:
    _enqueued(tmp_path)
    store = _save(tmp_path)
    _run_with_bound(store, 600_000_000.0)
    records = schedule_paths(tmp_path).records
    assert sweep_dead_enqueued("demo", records, NOW + timedelta(hours=20), set, store) == 0
    assert sweep_dead_enqueued("demo", records, NOW + timedelta(hours=25), set, store) == 1


_CHILD = """
import sys
from datetime import UTC, datetime
from pathlib import Path
from autotester.schema.schedule import ScheduleMode, SlotOutcome, SlotRecord
from autotester.stages.schedule_store import append_record
tag, path = sys.argv[1], Path(sys.argv[2])
t = datetime(2026, 10, 8, 9, tzinfo=UTC)
for n in range(40):
    append_record(path, SlotRecord(slot_key=f"demo:fixed:{tag}-{n}", project="demo",
                  mode=next(iter(ScheduleMode)), instant=t, recorded_at=t,
                  outcome=SlotOutcome.ENQUEUED))
"""


def test_two_processes_append_without_losing_or_tearing_lines(tmp_path: Path) -> None:
    path = tmp_path / "demo.jsonl"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    procs = [subprocess.Popen([sys.executable, "-c", _CHILD, t, str(path)], env=env, cwd=root)
             for t in ("a", "b")]
    assert [p.wait(timeout=120) for p in procs] == [0, 0]
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 80 and len(read_records(path)) == 80
