"""mongo-store U3c: the swept state sites go through the store, not around it.

The backend is swapped for the in-memory double, so a write that bypasses `filestore` lands on
disk instead and the test fails; a read that bypasses it sees the disk and not the double.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from state_backends import InMemoryBackend

import autotester.stages.schedule_store as schedule_store
import autotester.store.filestore as filestore
from autotester.auth import audit
from autotester.core.redact import Redactor
from autotester.core.trace import TraceWriter, read_spans, read_tool_spans
from autotester.delivery.inbox import DeliveryLog, delivery_key
from autotester.schema.delivery import DeliveryChannel, DeliveryRecord, DeliveryStatus
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.schema.schedule import SlotClaim, SlotRecord
from autotester.schema.team_enums import ScheduleMode, SlotOutcome
from autotester.stages.orchestrate_checkpoint import FileCheckpointer
from autotester.stages.schedule_store import (
    append_record,
    claim_path,
    list_claims,
    read_all_records,
    read_heartbeat,
    write_heartbeat,
)

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
TEXT = '{"last_tick": "2026-10-30T12:00:00+00:00"}'


@pytest.fixture
def memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    backend = InMemoryBackend()
    monkeypatch.setattr(filestore, "_backend", lambda name: backend)
    return backend


def _claim(key: str = "p:fixed:s1") -> SlotClaim:
    return SlotClaim(slot_key=key, mode=ScheduleMode.FIXED, instant=NOW, claimed_at=NOW,
                     intended=SlotOutcome.ENQUEUED)


def _slot(key: str) -> SlotRecord:
    return SlotRecord(slot_key=key, project="p", mode="fixed", instant=NOW, recorded_at=NOW,
                      outcome=SlotOutcome.ENQUEUED)


def test_the_checkpoint_flush_writes_through_the_store(memory: InMemoryBackend,
                                                       tmp_path: Path) -> None:
    path = tmp_path / "projects" / "p" / "runs" / "r1" / "checkpoint.json"
    FileCheckpointer(path, thread_id="r1").flush()
    assert "projects/p/runs/r1/checkpoint.json" in memory.docs
    assert not path.exists()


def test_the_heartbeat_writes_through_the_store(memory: InMemoryBackend, tmp_path: Path) -> None:
    path = tmp_path / ".work" / "schedule" / "heartbeat.json"
    write_heartbeat(path, NOW)
    assert memory.docs[".work/schedule/heartbeat.json"] == TEXT
    assert not path.exists()


def test_the_heartbeat_reads_back_from_the_store(memory: InMemoryBackend, tmp_path: Path) -> None:
    path = tmp_path / ".work" / "schedule" / "heartbeat.json"
    memory.put(".work/schedule/heartbeat.json", TEXT)
    assert read_heartbeat(path) == NOW
    for bad in ('{"last_tick": 5}', "{not json", '{"last_tick": "2026-10-30T12:00:00"}', "{}"):
        memory.put(".work/schedule/heartbeat.json", bad)
        assert read_heartbeat(path) is None  # unreadable or naive: never shown as healthy


def test_with_the_file_backend_the_heartbeat_is_the_same_file_as_before(tmp_path: Path) -> None:
    path = tmp_path / "hb" / "heartbeat.json"
    write_heartbeat(path, NOW)
    assert path.read_text(encoding="utf-8") == TEXT
    assert read_heartbeat(path) == NOW
    assert sorted(p.name for p in path.parent.iterdir()) == ["heartbeat.json"]


def test_the_trace_appends_through_the_store_and_asks_it_for_existence(
        memory: InMemoryBackend, tmp_path: Path) -> None:
    path = tmp_path / "projects" / "p" / "runs" / "r1" / "trace.jsonl"
    writer = TraceWriter(path, "r1", redactor=Redactor({}))
    writer.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="done"))
    writer.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="done"))
    rows = memory.docs["projects/p/runs/r1/trace.jsonl"].splitlines()
    assert len(rows) == 2 and json.loads(rows[0])["stage"] == "execute"
    assert not path.exists()
    elsewhere = tmp_path / "projects" / "p" / "runs" / "r2" / "trace.jsonl"
    elsewhere.parent.mkdir(parents=True)
    tool = json.dumps({"kind": "tool", "trace_id": "r2", "seq": 0, "op": "plan", "name": "lead"})
    elsewhere.write_text(rows[0] + "\n" + tool + "\n", encoding="utf-8")  # disk only: no store key
    assert read_spans(elsewhere) == [] and read_tool_spans(elsewhere) == []


def test_the_audit_line_appends_through_the_store(memory: InMemoryBackend, tmp_path: Path) -> None:
    audit.record_request("a@example.com", "POST", "/x/{id}", 200)
    audit.record_action("a@example.com", "u2", "disable")
    rows = [json.loads(r) for r in memory.docs[".work/audit.jsonl"].splitlines()]
    assert [r.get("action", r.get("status")) for r in rows] == [200, "disable"]
    assert not (tmp_path / ".work" / "audit.jsonl").exists()


def test_the_delivery_listing_comes_from_the_store(memory: InMemoryBackend,
                                                   tmp_path: Path) -> None:
    log = DeliveryLog(tmp_path / "d")
    key = delivery_key("run-0001", DeliveryChannel.EMAIL, "user-a")
    record = DeliveryRecord(run_id="run-0001", channel=DeliveryChannel.EMAIL,
                            recipient_user_id="user-a", status=DeliveryStatus.SENT, attempts=1)
    prefix = (tmp_path / "d" / "records").relative_to(tmp_path).as_posix()
    memory.put(f"{prefix}/{key}.01.json", record.model_dump_json())
    memory.put(f"{prefix}/unrelated.json", "not a record")
    assert [r.run_id for r in log.records_for_key(key)] == ["run-0001"]
    assert [r.run_id for r in log.records_for_run("run-0001")] == ["run-0001"]
    assert DeliveryLog(tmp_path / "empty").records_for_key(key) == []


def test_the_claim_listing_comes_from_the_store_and_a_torn_claim_reads_as_none(
        memory: InMemoryBackend, tmp_path: Path) -> None:
    claims = tmp_path / ".work" / "schedule" / "claims"
    rel = claims.relative_to(tmp_path).as_posix()
    memory.put(f"{rel}/{claim_path(claims, 'p:fixed:s1').name}", _claim().model_dump_json())
    memory.put(f"{rel}/{claim_path(claims, 'p:fixed:s2').name}", "")  # winner still writing
    memory.put(f"{rel}/ignored.txt", "x")
    found = list_claims(claims)
    assert sorted(found) == ["p:fixed:s1", "p:fixed:s2"]
    assert found["p:fixed:s1"] == _claim() and found["p:fixed:s2"] is None
    assert list_claims(tmp_path / "none") == {}


def test_a_slot_record_is_appended_through_the_store(memory: InMemoryBackend,
                                                     tmp_path: Path) -> None:
    path = tmp_path / ".work" / "schedule" / "records" / "p.jsonl"
    assert append_record(path, _slot("p:fixed:s1")) is True
    assert append_record(path, _slot("p:fixed:s2")) is True
    rows = memory.docs[".work/schedule/records/p.jsonl"].splitlines()
    assert [json.loads(r)["slot_key"] for r in rows] == ["p:fixed:s1", "p:fixed:s2"]
    assert not path.exists()


def test_every_projects_records_are_listed_from_the_store(
        memory: InMemoryBackend, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    records = tmp_path / ".work" / "schedule" / "records"
    memory.put(".work/schedule/records/a.jsonl", "")
    memory.put(".work/schedule/records/skip.txt", "")
    monkeypatch.setattr(schedule_store, "read_records", lambda p: [p.name])
    assert read_all_records(records) == ["a.jsonl"]  # listed from the store; no such dir on disk
    assert read_all_records(tmp_path / "none") == []
