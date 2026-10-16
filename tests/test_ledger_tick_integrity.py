"""AT-644 atomic tick append; AT-645/AT-676 line-numbered duplicate report and safe allocation."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from autotester.core import atomic_tick
from autotester.ledger import issue_ids


def test_append_tick_keeps_history_and_adds_newline(tmp_path: Path) -> None:
    p = tmp_path / ".last-tick"
    p.write_text("2026-01-01T00:00:00Z a\n2026-01-02T00:00:00Z b", encoding="utf-8")
    atomic_tick.append_tick(p, "2026-01-03T00:00:00Z c")
    assert p.read_text(encoding="utf-8").splitlines() == [
        "2026-01-01T00:00:00Z a", "2026-01-02T00:00:00Z b", "2026-01-03T00:00:00Z c"]
    assert not list(tmp_path.glob("*.tmp"))


def test_append_tick_rejects_empty_and_leaves_file(tmp_path: Path) -> None:
    p = tmp_path / ".last-tick"
    p.write_text("x\n", encoding="utf-8")
    with pytest.raises(ValueError):
        atomic_tick.append_tick(p, "  ")
    assert p.read_text(encoding="utf-8") == "x\n"


def test_append_tick_failed_replace_keeps_original(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / ".last-tick"
    p.write_text("a\nb\n", encoding="utf-8")

    def boom(*_args):
        raise OSError("boom")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic_tick.append_tick(p, "c")
    assert p.read_text(encoding="utf-8") == "a\nb\n"
    assert not list(tmp_path.glob("*.tmp"))


def _ledger(tmp_path: Path, rows: list[dict]) -> Path:
    (tmp_path / "qa").mkdir()
    p = tmp_path / "qa" / "issues.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


def test_duplicate_report_names_ids_and_lines(tmp_path: Path) -> None:
    _ledger(tmp_path, [{"id": "AT-1", "title": "a"}, {"id": "AT-2", "title": "m"},
                       {"id": "AT-1", "title": "b"}])
    (found,) = issue_ids.check_issue_id_unique(tmp_path)
    assert "AT-1" in found.detail and "lines 1, 3" in found.detail


def test_concurrent_append_new_issue_gives_distinct_ids(tmp_path: Path) -> None:
    p = _ledger(tmp_path, [{"id": "AT-5", "title": "seed"}])
    out: list[str] = []

    def work() -> None:
        out.append(issue_ids.append_new_issue(p, {"title": "t"})["id"])

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ids = [r["id"] for r in issue_ids.read_rows(p)]
    assert len(ids) == len(set(ids)) == 9 and len(set(out)) == 8


def test_append_does_not_glue_onto_unterminated_row(tmp_path: Path) -> None:
    p = _ledger(tmp_path, [])
    p.write_text('{"id": "AT-1", "title": "a"}', encoding="utf-8")
    issue_ids.append_new_issue(p, {"title": "b"})
    assert [r["id"] for r in issue_ids.read_rows(p)] == ["AT-1", "AT-2"]


def test_append_tick_threaded_keeps_every_line(tmp_path: Path) -> None:
    p = tmp_path / ".last-tick"
    p.write_text("seed\n", encoding="utf-8")
    errors: list[Exception] = []

    def work(i: int) -> None:
        try:
            atomic_tick.append_tick(p, f"t{i}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sorted(p.read_text(encoding="utf-8").splitlines()) == sorted(
        ["seed", *[f"t{i}" for i in range(8)]])
    assert sorted(f.name for f in tmp_path.iterdir()) == [".last-tick", ".last-tick.lock"]


def test_append_tick_retries_permission_error_then_succeeds(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / ".last-tick"
    p.write_text("a\n", encoding="utf-8")
    real, calls = os.replace, []

    def flaky(src, dst):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("held open")
        real(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    atomic_tick.append_tick(p, "b")
    assert len(calls) == 3 and p.read_text(encoding="utf-8") == "a\nb\n"


def test_append_tick_raises_when_every_retry_fails(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / ".last-tick"
    p.write_text("a\n", encoding="utf-8")
    monkeypatch.setattr(atomic_tick, "_RETRY_DELAYS_S", (0.0, 0.0))

    def locked(*_args):
        raise PermissionError("held open")

    monkeypatch.setattr(os, "replace", locked)
    with pytest.raises(PermissionError):
        atomic_tick.append_tick(p, "b")
    assert p.read_text(encoding="utf-8") == "a\n"
