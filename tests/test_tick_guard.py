"""AT-644 (D-087): qa/.last-tick truncation guard and atomic append."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester import tick_guard
from autotester.cli import app

runner = CliRunner()
GOOD = "2026-09-24T22:26:20Z WAITING · note\n2026-09-24T23:02:27Z ADVANCED · x\n"


def _root(tmp_path: Path, text: str) -> Path:
    (tmp_path / "qa").mkdir()
    path = tmp_path / "qa" / ".last-tick"
    path.write_bytes(text.encode())
    return path


def test_valid_tick_passes(tmp_path: Path) -> None:
    assert tick_guard.problems(_root(tmp_path, GOOD)) == []


@pytest.mark.parametrize("text", ["", "  \n", GOOD.rstrip("\n"), "garbage\n" + GOOD,
                                  "2026-09-24T22:26:20Z WAITING · no", "{\"a\": 1"])
def test_truncated_or_partial_is_detected(tmp_path: Path, text: str) -> None:
    assert tick_guard.problems(_root(tmp_path, text))


def test_multiline_entry_is_valid(tmp_path: Path) -> None:
    assert tick_guard.problems(_root(tmp_path, GOOD + "  continuation prose\n")) == []


def test_append_keeps_history_and_format(tmp_path: Path) -> None:
    path = _root(tmp_path, GOOD)
    tick_guard.append_tick(path, "2026-10-12T08:00:00Z STOPPED · done")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and lines[:2] == GOOD.splitlines()
    assert tick_guard.problems(path) == []


def test_append_refuses_damaged_log_and_bad_line(tmp_path: Path) -> None:
    path = _root(tmp_path, GOOD.rstrip("\n"))
    with pytest.raises(tick_guard.TickGuardError):
        tick_guard.append_tick(path, "2026-10-12T08:00:00Z X")
    ok = _root(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path, GOOD)
    with pytest.raises(tick_guard.TickGuardError):
        tick_guard.append_tick(ok, "not a stamp")
    assert ok.read_text(encoding="utf-8") == GOOD


def test_failed_write_leaves_no_partial_file(tmp_path: Path, monkeypatch) -> None:
    path = _root(tmp_path, GOOD)

    def boom(*_a: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        tick_guard.append_tick(path, "2026-10-12T08:00:00Z X")
    assert path.read_text(encoding="utf-8") == GOOD
    assert [p.name for p in path.parent.iterdir()] == [".last-tick"]


def test_loop_status_strict_flags_truncated_log(tmp_path: Path, monkeypatch) -> None:
    _root(tmp_path, "2026-09-24T22:26:20Z\n2026-09-24T23:02:27Z")
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    result = runner.invoke(app, ["loop-status", "--strict"])
    assert "TICK LOG DAMAGED" in result.output and result.exit_code == 1


def test_tick_append_cli(tmp_path: Path, monkeypatch) -> None:
    path = _root(tmp_path, GOOD)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    assert runner.invoke(app, ["tick-append", "2026-10-12T08:00:00Z OK"]).exit_code == 0
    assert runner.invoke(app, ["tick-append", "bad"]).exit_code == 1
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3
