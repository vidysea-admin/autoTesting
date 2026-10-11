"""Zip intake, atomic registration and cleanup (team-intake.md TI6; R39, R65)."""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from zip_fixtures import (
    build_zip,
    make_store,
    video,
)

from autotester.schema.intake import IntakeOutcome, IntakeStatus
from autotester.sources import intake_commit, zip_intake
from autotester.sources.zip_intake import expand_zip
from autotester.store.project_store import ProjectStore

MIB = 1024 * 1024
CAP = MIB  # per-file cap injected small, standing in for the 2 GiB admin setting

def _run(store: ProjectStore, archive: Path, **kwargs):
    kwargs.setdefault("max_file_bytes", CAP)
    return expand_zip(store, archive, **kwargs)


def _rows(store: ProjectStore):
    return store.list_sources()


def _by_outcome(report, outcome: IntakeOutcome):
    return [m for m in report.members if m.outcome == outcome]


# ---- TI6 --------------------------------------------------------------------

def _three(tmp_path: Path) -> Path:
    return build_zip(tmp_path / "three.zip", [(f"v{i}.mp4", video(f"v{i}")) for i in range(3)])


def _assert_rows_and_files_agree(store: ProjectStore) -> None:
    from autotester.core.ids import file_sha256

    rows = _rows(store)
    for row in rows:
        assert Path(row.path).is_file() and file_sha256(row.path) == row.sha256
    on_disk = {p.resolve() for p in store.paths.sources_dir.rglob("recording.*")}
    assert on_disk == {Path(r.path).resolve() for r in rows}
    assert len({r.id for r in rows}) == len(rows)


def test_ti6_exception_after_member_two_leaves_rows_and_files_agreeing_and_rerun_converges(
        tmp_path, monkeypatch):
    """The row write fails on the third video (disk full, process shutting down)."""
    store = make_store(tmp_path)
    archive = _three(tmp_path)
    real = ProjectStore.add_source
    calls = {"n": 0}

    def flaky(self, source):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("boom after member 2")
        return real(self, source)

    monkeypatch.setattr(ProjectStore, "add_source", flaky)
    with pytest.raises(RuntimeError):
        _run(store, archive)
    _assert_rows_and_files_agree(store)
    assert len(_rows(store)) == 2
    assert not list((tmp_path / ".work" / "intake").glob("*/*"))
    assert not (store.paths.dir / ".intake.lock").exists()
    monkeypatch.setattr(ProjectStore, "add_source", real)
    again = _run(ProjectStore("demo", root=tmp_path), archive)
    assert again.status is IntakeStatus.OK and len(_rows(store)) == 3
    _assert_rows_and_files_agree(store)


def test_ti6_failure_inside_the_copy_never_leaves_a_row_without_its_file(tmp_path, monkeypatch):
    """The destination volume fills up while member 2 is being moved into place."""
    store = make_store(tmp_path)
    real_replace = os.replace
    state = {"n": 0}

    def failing(src, dst):
        if "sources" in str(dst):
            state["n"] += 1
            if state["n"] == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
        return real_replace(src, dst)

    monkeypatch.setattr(intake_commit.os, "replace", failing)
    report = _run(store, _three(tmp_path))
    assert [m.outcome for m in report.members].count(IntakeOutcome.FAILED) == 1
    assert report.status is IntakeStatus.PARTIAL and len(_rows(store)) == 2
    _assert_rows_and_files_agree(store)


_KILL_SCRIPT = """
import os, sys
from pathlib import Path
from autotester.store.project_store import ProjectStore
from autotester.sources.zip_intake import expand_zip
real = ProjectStore.add_source
n = {"v": 0}
def add(self, source):
    n["v"] += 1
    if n["v"] == 2:
        os._exit(9)
    return real(self, source)
ProjectStore.add_source = add
expand_zip(ProjectStore("demo", root=Path(sys.argv[1])), Path(sys.argv[2]), max_file_bytes=1 << 20)
"""


def test_ti6_process_killed_between_copy_and_row_heals_on_the_next_intake(tmp_path):
    """The server process is killed (os._exit, no cleanup) after member 2's file is in place."""
    store = make_store(tmp_path)
    archive = _three(tmp_path)
    script = tmp_path / "kill.py"
    script.write_text(_KILL_SCRIPT, encoding="utf-8")
    # The child must import the tree under test, not whatever tree the venv's editable install
    # points at (a clean copy run with another checkout's venv would import the wrong one).
    src = str(Path(__file__).resolve().parents[1] / "src")
    path = os.pathsep.join(filter(None, [src, os.environ.get("PYTHONPATH")]))
    env = {**os.environ, "PYTHONPATH": path}
    done = subprocess.run([sys.executable, str(script), str(tmp_path), str(archive)],
                          capture_output=True, text=True, timeout=120, env=env)
    assert done.returncode == 9
    for row in _rows(store):  # no row without its file, even at the instant of the kill
        assert Path(row.path).is_file()
    assert len(_rows(store)) == 1
    lock = store.paths.dir / ".intake.lock"
    if lock.exists():  # a killed holder leaves its lock: age it past the stale threshold
        os.utime(lock, (0, 0))
    again = _run(ProjectStore("demo", root=tmp_path), archive)
    assert again.status is IntakeStatus.OK and len(_rows(store)) == 3
    _assert_rows_and_files_agree(store)
    assert not list((tmp_path / ".work" / "intake").glob("*/*"))


def test_ti6_staging_is_under_the_project_working_area_and_removed_after(tmp_path, monkeypatch):
    """Staging may not be the repo tree or an unchecked system-temp name."""
    store = make_store(tmp_path)
    seen: list[Path] = []
    real = zip_intake.copy_bounded

    def spy(chunks, dest, cap, **kwargs):
        seen.append(Path(dest))
        return real(chunks, dest, cap, **kwargs)

    monkeypatch.setattr(zip_intake, "copy_bounded", spy)
    _run(store, _three(tmp_path))
    work = (tmp_path / ".work" / "intake").resolve()
    assert seen and all(work in p.resolve().parents for p in seen)
    assert not list(work.glob("*/*"))


def test_ti6_two_intakes_into_one_project_at_once_lose_and_duplicate_no_row(tmp_path):
    """Two testers upload the same zip to the same project in the same second."""
    store = make_store(tmp_path)
    archive = _three(tmp_path)
    reports, errors = [], []

    def worker() -> None:
        try:
            reports.append(_run(ProjectStore("demo", root=tmp_path), archive))
        except Exception as exc:  # pragma: no cover - surfaced by the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors and len(reports) == 2
    assert len(_rows(store)) == 3
    lines = store.paths.sources_index.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3 and len({json.loads(line)["id"] for line in lines}) == 3
    _assert_rows_and_files_agree(store)
