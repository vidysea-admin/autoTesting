"""T-199b: `process_run` is idempotent per run and survives a crash or a bad file (TB6, P3, P4).

Contract: qa/contracts/team-bug-loop.md TB6. Real files in a temp project; the only fake is the
clock. The store is judged by its files, byte for byte, never by what a writer thought it did.
"""

from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path

import pytest
from bug_loop_fixture import PROJECT, T0
from bug_run_fixture import add_case, finished_run, make_store, verdict

import autotester.store.bug_store as bug_store_module
from autotester.schema.enums import Result
from autotester.schema.tracked_bug import case_bug_key
from autotester.stages.bug_run import process_run
from autotester.store.bug_store import BugStore

R = Result
NOW = T0 + timedelta(days=1)


def _bugs(root: Path) -> BugStore:
    return BugStore(root / "bugs", clock=lambda: NOW)


def _files(bugs: BugStore) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(bugs.dir.glob("*.json"))}


def _key(case, crit: str = "C1") -> str:
    return case_bug_key(PROJECT, case.id, crit)


def _three_run_project(root: Path):
    store = make_store(root)
    one, two = add_case(store, "checkout"), add_case(store, "login")
    finished_run(store, "run1", 1, [verdict(one, "run1", R.FAIL), verdict(two, "run1", R.FAIL)],
                 [one, two])
    finished_run(store, "run2", 2, [verdict(one, "run2", R.PASS), verdict(two, "run2", R.FAIL)],
                 [one, two])
    return store, one, two


def test_tb6_processing_the_same_run_twice_changes_nothing_byte_for_byte(tmp_path: Path) -> None:
    store, _, two = _three_run_project(tmp_path)
    bugs = _bugs(tmp_path)
    for run in ("run1", "run2"):
        process_run(store, bugs, run)
    first_files, first_bugs = _files(bugs), bugs.bugs()
    again = [process_run(store, bugs, run) for run in ("run1", "run2", "run1", "run2")]
    assert _files(bugs) == first_files and bugs.bugs() == first_bugs
    assert all(r.applied == 0 for r in again) and first_bugs[_key(two)].count == 2


def test_tb6_a_crash_after_the_first_bug_of_a_run_converges_on_retry(
        tmp_path: Path, monkeypatch) -> None:
    clean_store, _, two = _three_run_project(tmp_path / "clean")
    clean = _bugs(tmp_path / "clean")
    for run in ("run1", "run2"):
        process_run(clean_store, clean, run)
    store, _, _ = _three_run_project(tmp_path / "crash")
    bugs = _bugs(tmp_path / "crash")
    process_run(store, bugs, "run1")
    real, calls = BugStore._write, {"n": 0}

    def dies_on_second(self, event):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk went away")
        real(self, event)

    monkeypatch.setattr(BugStore, "_write", dies_on_second)
    with pytest.raises(OSError):
        process_run(store, bugs, "run2")
    monkeypatch.setattr(BugStore, "_write", real)
    process_run(store, bugs, "run2")
    process_run(store, bugs, "run2")
    assert bugs.bugs() == clean.bugs() and _files(bugs) == _files(clean)
    assert bugs.get(_key(two)).count == 2


def test_p3_a_run_reads_each_stored_event_file_once(tmp_path: Path, monkeypatch) -> None:
    store, _, _ = _three_run_project(tmp_path)
    bugs = _bugs(tmp_path)
    process_run(store, bugs, "run1")
    stored = len(list(bugs.dir.glob("*.json")))
    calls, real = {"n": 0}, bug_store_module.read_json

    def counted(path, model_cls):
        calls["n"] += 1
        return real(path, model_cls)

    monkeypatch.setattr(bug_store_module, "read_json", counted)
    process_run(store, bugs, "run2")
    assert calls["n"] == stored


def test_p4_a_bad_event_file_does_not_stop_a_run_and_is_named_in_its_report(
        tmp_path: Path) -> None:
    store, _, two = _three_run_project(tmp_path)
    bugs = _bugs(tmp_path)
    process_run(store, bugs, "run1")
    bugs.dir.joinpath("bev_zero.json").write_bytes(b"")
    report = process_run(store, bugs, "run2")
    assert [b.name for b in report.bad_files] == ["bev_zero.json"]
    assert bugs.get(_key(two)).count == 2


# -- design rules the contract states ----------------------------------------------------------

def test_the_run_stage_never_reads_a_raw_result_or_the_network() -> None:
    import autotester.stages.bug_run as mod
    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "RawResult" not in names | imported and "outcome" not in attrs
    assert "load_results" not in attrs
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not {m.split(".")[0] for m in mods if m} & {"socket", "httpx", "requests", "urllib",
                                                       "subprocess", "googleapiclient"}
