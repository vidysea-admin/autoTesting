"""T-136c: persist a finished run with its measured wall clock and name it for bench tooling.

One job: build and save the `Run` row for a script-driven run, always stamping `started_at` and
`finished_at` from clock readings the caller took around the real work (never defaulted here),
and print the explicit `run_id:` line `scripts/bench_from_run.py <slug> --run <id>` consumes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from autotester.schema.run import Run
from autotester.store.project_store import ProjectStore


def now_utc() -> datetime:
    """The single wall-clock reader scripts use to bracket a run (timezone-aware UTC)."""
    return datetime.now(UTC)


def record_run(
    store: ProjectStore,
    run_id: str,
    project: str,
    case_ids: list[str],
    started_at: datetime,
    finished_at: datetime,
) -> Run:
    """Save the Run with measured timestamps; refuse a clock that ran backwards."""
    if finished_at < started_at:
        raise ValueError("finished_at is before started_at -- not a measured wall clock")
    run = Run(id=run_id, project=project, case_ids=case_ids,
              started_at=started_at, finished_at=finished_at)
    store.save_run(run)
    return run


def run_id_lines(run_id: str, run_dir: object) -> list[str]:
    """The trailing lines a run script prints: the dir for humans, the id for bench tooling."""
    return [f"run: {run_dir}", f"run_id: {run_id}"]
