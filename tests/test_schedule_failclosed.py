"""D-088 / ISS-t200-schedule-wiring-3: an unreadable or corrupt server queue file fails CLOSED.

The scheduler's overlap check reads the server's queue file; an unknown queue is never an idle
one. Absent file = legitimately empty. Unreadable or corrupt = the slot is recorded `failed`
with a reason and nothing is enqueued.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_schedule_wiring import _queue, _scheduled, _tick

from autotester.schema.schedule import SlotOutcome
from autotester.stages.schedule_store import project_records_path, read_records
from autotester.stages.schedule_wiring import schedule_paths
from autotester.ui import run_queue


@pytest.fixture
def server_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    path = tmp_path / ".work" / "run_queue.json"
    path.parent.mkdir(parents=True)
    return path


def test_missing_file_is_an_empty_queue(server_file: Path) -> None:
    assert not server_file.exists()
    assert run_queue.persisted_entries() == []


@pytest.mark.parametrize("content", [b"{not json", b"", b'{"entries": "nope"}', b"\xff\xfe\x00"])
def test_corrupt_file_raises(server_file: Path, content: bytes) -> None:
    server_file.write_bytes(content)
    with pytest.raises(RuntimeError, match="unreadable"):
        run_queue.persisted_entries()


def test_unreadable_file_raises(server_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server_file.write_text("{}", encoding="utf-8")

    def boom(*_a, **_k):
        raise PermissionError("locked")

    monkeypatch.setattr(run_queue, "read_json", boom)
    with pytest.raises(RuntimeError, match="not started"):
        run_queue.persisted_entries()


def test_tick_skips_and_records_a_reason_when_the_queue_file_is_corrupt(
    tmp_path: Path, server_file: Path
) -> None:
    root = tmp_path / "repo"
    _scheduled(root)
    server_file.write_text("{corrupt", encoding="utf-8")
    queue, manual = _queue()
    _tick(root, queue, persisted=run_queue.persisted_entries)
    records = read_records(project_records_path(schedule_paths(root).records, "demo"))
    assert [r.outcome for r in records] == [SlotOutcome.FAILED]
    assert "unreadable" in (records[0].detail or "")
    assert queue.snapshot() == [] and manual.pending == []
