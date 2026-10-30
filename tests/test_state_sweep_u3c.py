"""mongo-store U3c: the checkpoint flush and the scheduler heartbeat go through the store.

The backend is swapped for the in-memory double, so a write that bypasses `filestore` lands on
disk instead and the test fails.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from state_backends import InMemoryBackend

import autotester.store.filestore as filestore
from autotester.stages.orchestrate_checkpoint import FileCheckpointer
from autotester.stages.schedule_store import read_heartbeat, write_heartbeat

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
TEXT = '{"last_tick": "2026-10-30T12:00:00+00:00"}'


@pytest.fixture
def memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    backend = InMemoryBackend()
    monkeypatch.setattr(filestore, "backend_for", lambda key: backend)
    return backend


def test_the_checkpoint_flush_writes_through_the_store(memory: InMemoryBackend,
                                                       tmp_path: Path) -> None:
    path = tmp_path / "projects" / "p" / "runs" / "r1" / "checkpoint.json"
    saver = FileCheckpointer(path, thread_id="r1")
    saver.flush()
    assert "projects/p/runs/r1/checkpoint.json" in memory.docs
    assert not path.exists()


def test_the_heartbeat_writes_through_the_store(memory: InMemoryBackend, tmp_path: Path) -> None:
    path = tmp_path / ".work" / "schedule" / "heartbeat.json"
    write_heartbeat(path, NOW)
    assert memory.docs[".work/schedule/heartbeat.json"] == TEXT
    assert not path.exists()


def test_with_the_file_backend_the_heartbeat_is_the_same_file_as_before(tmp_path: Path) -> None:
    path = tmp_path / "hb" / "heartbeat.json"
    write_heartbeat(path, NOW)
    assert path.read_text(encoding="utf-8") == TEXT
    assert read_heartbeat(path) == NOW
    assert sorted(p.name for p in path.parent.iterdir()) == ["heartbeat.json"]
