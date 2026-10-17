"""AT-943: a purge that is interrupted (SystemExit, Ctrl-C, a hard kill) never stays half done.

`purge_project` used to catch OSError only, so an interrupt between two moves left some files
live, some stranded in a `.purge-*` stage directory, and nothing ever reclaimed it. The contract
now: an exception rolls every file back; a hard kill is repaired by the next purge, which adopts
the stranded stage (put back if the purge had not committed, deleted if it had).
"""

from __future__ import annotations

import multiprocessing as mp
import os
from pathlib import Path

import pytest
from test_schedule_marker import _seed, _slot

from autotester.stages import schedule_store
from autotester.stages.schedule_store import (
    append_record,
    claim,
    list_claims,
    project_records_path,
    purge_project,
    read_records,
)

KEY2 = "p:fixed:2026-10-09T09:00Z"


def _seed_three(base: Path, project: str = "p") -> Path:
    """Two claim markers plus the records file: three files, so three moves."""
    path = _seed(base, project)
    body = _slot(project)[1]
    assert claim(base / "claims", KEY2.replace("p:", f"{project}:", 1),
                 body.model_copy(update={"slot_key": KEY2.replace("p:", f"{project}:", 1)}))
    return path


def _files(base: Path) -> list[str]:
    return sorted(str(f.relative_to(base)) for f in base.rglob("*")
                  if f.is_file() and not f.name.endswith(".lock"))


def _stages(base: Path) -> list[Path]:
    return [d for d in base.iterdir() if d.name.startswith(".purge")]


def _interrupt_on_second_move(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    real, calls = os.replace, []

    def interrupted(src, dst):
        calls.append(src)
        if len(calls) == 2:
            raise exc
        return real(src, dst)

    monkeypatch.setattr(schedule_store.os, "replace", interrupted)


@pytest.mark.parametrize("exc", [SystemExit(1), KeyboardInterrupt()],
                         ids=["system_exit", "keyboard_interrupt"])
def test_a_purge_interrupted_by_systemexit_or_ctrl_c_leaves_every_file_and_no_stage_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exc: BaseException,
) -> None:
    path = _seed_three(tmp_path)
    before = _files(tmp_path)
    _interrupt_on_second_move(monkeypatch, exc)
    with pytest.raises(type(exc)):
        purge_project(tmp_path / "claims", path, "p")
    monkeypatch.undo()
    assert _files(tmp_path) == before and len(read_records(path)) == 1  # all, not 1 of 3
    assert _stages(tmp_path) == []
    purge_project(tmp_path / "claims", path, "p")  # the retry still finishes the job
    assert list_claims(tmp_path / "claims") == {} and not path.exists()


def test_a_failed_restore_does_not_stop_the_rollback_of_the_files_after_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old rollback loop died at the first restore that failed and stranded the rest; now
    every file is tried, the original error still surfaces, and the next purge finishes."""
    path = _seed_three(tmp_path)
    before = _files(tmp_path)
    real, calls = os.replace, []

    def flaky(src, dst):
        calls.append(src)
        if len(calls) == 3:  # third move fails: two files are in the stage ...
            raise PermissionError("in use by another process")
        if len(calls) == 4:  # ... and the first restore fails too
            raise PermissionError("still in use")
        return real(src, dst)

    monkeypatch.setattr(schedule_store.os, "replace", flaky)
    with pytest.raises(PermissionError, match="in use by another process"):
        purge_project(tmp_path / "claims", path, "p")
    monkeypatch.undo()
    restored = [f for f in before if (tmp_path / f).is_file()]
    assert len(restored) == len(before) - 1  # one stuck, the other came back anyway
    purge_project(tmp_path / "claims", path, "p")  # adopts the stranded stage, then purges
    assert _files(tmp_path) == [] and _stages(tmp_path) == []


def _die_after_n_moves(base: str, n: int, patch_rmtree: bool) -> None:
    real, count = os.replace, [0]

    def replace_then_die(src, dst):
        real(src, dst)
        count[0] += 1
        if count[0] == n:
            os._exit(3)  # a hard kill: no except, no finally, no atexit

    if patch_rmtree:  # die at the very end instead: all moved and committed, stage not deleted
        schedule_store.shutil.rmtree = lambda *a, **k: os._exit(3)
    else:
        schedule_store.os.replace = replace_then_die
    root = Path(base)
    purge_project(root / "claims", project_records_path(root / "records", "p"), "p")


def _killed_purge(base: Path, moves: int, patch_rmtree: bool = False) -> None:
    child = mp.get_context("spawn").Process(target=_die_after_n_moves,
                                            args=(str(base), moves, patch_rmtree))
    child.start()
    child.join(timeout=60)
    assert child.exitcode == 3


@pytest.mark.parametrize("moves", [1, 3])
def test_a_purge_killed_after_n_moves_is_put_back_whole_by_the_next_purge_of_that_project(
    tmp_path: Path, moves: int,
) -> None:
    path = _seed_three(tmp_path)
    _killed_purge(tmp_path, moves)
    assert len(_stages(tmp_path)) == 1  # the hard kill really stranded a stage dir
    schedule_store.recover_stale_purges(tmp_path / "claims", path, "p")
    assert len(list_claims(tmp_path / "claims")) == 2 and len(read_records(path)) == 1
    assert _stages(tmp_path) == []  # all files back, nothing stranded
    purge_project(tmp_path / "claims", path, "p")
    assert _files(tmp_path) == []


def test_a_purge_killed_after_its_commit_but_before_deleting_the_stage_is_finished_not_undone(
    tmp_path: Path,
) -> None:
    path = _seed_three(tmp_path)
    _killed_purge(tmp_path, 0, patch_rmtree=True)
    assert _files(tmp_path) != [] and not path.exists()  # committed: the project is purged
    assert len(_stages(tmp_path)) == 1
    purge_project(tmp_path / "claims", path, "p")  # nothing to purge, but it reclaims the stage
    assert _stages(tmp_path) == [] and list_claims(tmp_path / "claims") == {}


def test_adopting_a_stale_stage_never_overwrites_a_file_that_came_back_in_its_place(
    tmp_path: Path,
) -> None:
    path = _seed_three(tmp_path)
    _killed_purge(tmp_path, 3)
    newer = _slot("p")[2].model_copy(update={"detail": "newer"})
    assert append_record(path, newer)  # a tick wrote a fresh records file meanwhile
    schedule_store.recover_stale_purges(tmp_path / "claims", path, "p")
    assert [r.detail for r in read_records(path)] == ["newer"]  # not clobbered
    assert len(_stages(tmp_path)) == 1  # the displaced old file is kept, not thrown away


def test_a_purge_of_one_project_leaves_another_projects_stranded_stage_alone(
    tmp_path: Path,
) -> None:
    other = _seed_three(tmp_path, "pp")
    p = _seed(tmp_path, "p")
    mid = mp.get_context("spawn").Process(target=_purge_pp_then_die, args=(str(tmp_path),))
    mid.start()
    mid.join(timeout=60)
    assert mid.exitcode == 3 and len(_stages(tmp_path)) == 1
    purge_project(tmp_path / "claims", p, "p")  # must not touch pp's stage
    assert len(_stages(tmp_path)) == 1  # still there: it is not p's to adopt
    schedule_store.recover_stale_purges(tmp_path / "claims", other, "pp")
    assert _stages(tmp_path) == [] and other.is_file()


def _purge_pp_then_die(base: str) -> None:
    real, count = os.replace, [0]

    def replace_then_die(src, dst):
        real(src, dst)
        count[0] += 1
        if count[0] == 1:
            os._exit(3)

    schedule_store.os.replace = replace_then_die
    root = Path(base)
    purge_project(root / "claims", project_records_path(root / "records", "pp"), "pp")
