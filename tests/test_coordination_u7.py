"""mongo-store U7 (M19, M20, M52, M53): coordination and READ-SIDE sites go through the store.

Each test runs on the in-memory double and on `MongoBackend` over the fake, with the data root an
empty temp dir: a site that still reaches the disk leaves a file (the tree check) or reads nothing
(the read-back check). The old file-mode behaviour is pinned by the unchanged suites.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from state_backends import BACKEND_FACTORIES

import autotester.stages.schedule_store as schedule_store
import autotester.store.filestore as filestore
from autotester.core.paths import team_path
from autotester.core.redact import Redactor
from autotester.core.trace import TraceWriter, read_spans
from autotester.delivery.inbox import DeliveryLog
from autotester.schema.run_queue import RunQueueFile
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.schema.schedule import SlotClaim, SlotRecord
from autotester.schema.team_enums import ScheduleMode, SlotOutcome
from autotester.sources.intake_commit import IntakeBusy, intake_lock
from autotester.stages import bench_inputs
from autotester.stages.orchestrate_checkpoint import FileCheckpointer
from autotester.stages.schedule_store import (
    append_record,
    claim,
    list_claims,
    project_records_path,
    purge_project,
    read_records,
    recover_stale_purges,
)
from autotester.store.filestore import read_json, write_json, write_text
from autotester.store.filestore_paths import read_text_path
from autotester.store.project_store import ProjectStore
from autotester.store.team_store import create_marker
from autotester.ui.run_queue import RunQueue

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


@pytest.fixture(params=["memory", "mongo"])
def root(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "root"
    base.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(base))
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS"):
        monkeypatch.delenv(name, raising=False)
    backend = BACKEND_FACTORIES[request.param](base)
    monkeypatch.setattr(filestore, "_backend", lambda name: backend)
    return base


def _files(base: Path) -> list[str]:
    """Every regular file on disk, but the advisory sidecar locks (local by design)."""
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*")
                  if p.is_file() and not p.name.endswith(".lock"))


def _race(count: int, job: Callable[[int], bool]) -> int:
    gate, wins = threading.Barrier(count), []

    def run(number: int) -> None:
        gate.wait()
        wins.append(job(number))

    threads = [threading.Thread(target=run, args=(n,)) for n in range(count)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return sum(wins)


def _claim(key: str) -> SlotClaim:
    return SlotClaim(slot_key=key, mode=ScheduleMode.FIXED, instant=NOW, claimed_at=NOW,
                     intended=SlotOutcome.ENQUEUED)


def _slot(key: str, project: str = "p") -> SlotRecord:
    return SlotRecord(slot_key=key, project=project, mode="fixed", instant=NOW, recorded_at=NOW,
                      outcome=SlotOutcome.ENQUEUED)


# ---- delivery claims ---------------------------------------------------------------------------


def test_delivery_claims_and_records_are_exclusive_in_the_store(root: Path) -> None:
    log = DeliveryLog(team_path("delivery"))
    assert log.claim("k", 1, NOW) is True and log.claim("k", 1, NOW) is False
    assert log.claimed_at("k", 1) == NOW and log.claimed_at("k", 2) is None
    assert _race(16, lambda n: log.claim("race", 1, NOW)) == 1
    assert _files(root) == []


# ---- schedule claims, records, purge -----------------------------------------------------------


def test_a_slot_claim_has_one_winner_among_sixteen_and_lists_back(root: Path) -> None:
    claims = team_path("schedule", "claims")
    assert _race(16, lambda n: claim(claims, "p:fixed:s1", _claim("p:fixed:s1"))) == 1
    assert list(list_claims(claims)) == ["p:fixed:s1"]
    assert _files(root) == []


def test_slot_records_read_back_from_the_store_not_the_disk(root: Path) -> None:
    path = project_records_path(team_path("schedule", "records"), "p")
    assert read_records(path) == []
    assert append_record(path, _slot("p:fixed:s1")) is True
    assert append_record(path, _slot("p:fixed:s1")) is False
    assert [r.slot_key for r in read_records(path)] == ["p:fixed:s1"]
    assert _files(root) == []


def _seed_purge(root: Path, project: str = "p") -> tuple[Path, Path]:
    claims = team_path("schedule", "claims")
    records = project_records_path(team_path("schedule", "records"), project)
    for n in (1, 2):
        key = f"{project}:fixed:s{n}"
        assert claim(claims, key, _claim(key))
    assert append_record(records, _slot(f"{project}:fixed:s1", project))
    return claims, records


def test_purge_removes_the_claims_and_the_records_and_leaves_no_stage(root: Path) -> None:
    claims, records = _seed_purge(root)
    other_claims, other_records = _seed_purge(root, "q")
    purge_project(claims, records, "p")
    assert [k for k in list_claims(claims)] == ["q:fixed:s1", "q:fixed:s2"]
    assert read_records(records) == [] and len(read_records(other_records)) == 1
    assert [n for n in filestore.list_children(claims.parent) if n.startswith(".purge")] == []
    assert other_claims == claims and _files(root) == []


def test_an_interrupted_purge_puts_every_file_back(root: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    claims, records = _seed_purge(root)
    real, calls = schedule_store.rename_path, []

    def second_move_dies(src: Path, dst: Path) -> None:
        calls.append(src)
        if len(calls) == 2:
            raise KeyboardInterrupt
        real(src, dst)

    with monkeypatch.context() as patched:
        patched.setattr(schedule_store, "rename_path", second_move_dies)
        with pytest.raises(KeyboardInterrupt):
            purge_project(claims, records, "p")
    assert len(list_claims(claims)) == 2 and len(read_records(records)) == 1
    assert [n for n in filestore.list_children(claims.parent) if n.startswith(".purge")] == []
    purge_project(claims, records, "p")  # the retry still finishes the job
    assert list_claims(claims) == {} and read_records(records) == []


def test_a_purge_killed_mid_way_is_put_back_by_the_next_recovery(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claims, records = _seed_purge(root)
    real, calls = schedule_store.rename_path, []

    def die_after_two(src: Path, dst: Path) -> None:
        real(src, dst)
        calls.append(src)
        if len(calls) == 2:
            raise KeyboardInterrupt

    with monkeypatch.context() as patched:
        patched.setattr(schedule_store, "rename_path", die_after_two)
        patched.setattr(schedule_store, "_restore_stage", lambda stage: False)  # a hard kill
        with pytest.raises(KeyboardInterrupt):
            purge_project(claims, records, "p")
    assert len(list_claims(claims)) == 0  # two files are sitting in the stranded stage
    assert recover_stale_purges(claims, records, "p") == 1
    assert len(list_claims(claims)) == 2 and len(read_records(records)) == 1


# ---- checkpoint, trace, markers ----------------------------------------------------------------


def test_a_stale_checkpoint_instance_is_refused_on_a_document_backend(root: Path) -> None:
    path = root / "projects" / "p" / "runs" / "r1" / "checkpoint.json"
    first = FileCheckpointer(path, thread_id="r1")
    second = FileCheckpointer(path, thread_id="r1")
    first.flush()
    with pytest.raises(RuntimeError, match="changed outside"):
        second.flush()
    assert _files(root) == []


def test_the_checkpoint_write_is_a_compare_and_set_not_a_check_then_write(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = root / "projects" / "p" / "runs" / "r1" / "checkpoint.json"
    mine = FileCheckpointer(path, thread_id="r1")
    mine.flush()
    monkeypatch.setattr(FileCheckpointer, "_check_disk", lambda self: None)  # the window is open
    landed = (read_text_path(path) or "") + " "  # another process lands a newer snapshot
    write_text(path, landed)
    with pytest.raises(RuntimeError, match="changed outside"):
        mine.flush()
    assert read_text_path(path) == landed


def test_the_trace_reads_back_from_the_store(root: Path) -> None:
    path = root / "projects" / "p" / "runs" / "r1" / "trace.jsonl"
    writer = TraceWriter(path, "r1", redactor=Redactor({}))
    writer.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="done"))
    assert len(read_spans(path)) == 1 and _files(root) == []


def test_a_team_marker_has_one_winner_in_the_store(root: Path) -> None:
    assert _race(16, lambda n: create_marker(root, "release", "scope.json", body=str(n))) == 1
    assert _files(root) == []


# ---- run queue rev -----------------------------------------------------------------------------


def _queue(path: Path) -> RunQueue:
    return RunQueue(limit=lambda: 1, spawn=lambda job: None, runner=lambda e: None,
                    path=lambda: path)


def test_the_run_queue_file_carries_a_rev_that_grows_with_every_save(root: Path) -> None:
    path = root / ".work" / "run_queue.json"
    queue = _queue(path)
    queue.recover()
    queue.submit("p")
    first = read_json(path, RunQueueFile)
    queue.submit("p")
    second = read_json(path, RunQueueFile)
    assert first is not None and second is not None and second.rev == first.rev + 1


def test_a_run_queue_save_that_lost_the_race_writes_nothing_and_says_so(
        root: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = root / ".work" / "run_queue.json"
    queue = _queue(path)
    queue.recover()
    queue.submit("p")
    write_json(path, RunQueueFile(rev=50, entries=[]))  # another instance saved meanwhile
    with caplog.at_level(logging.WARNING):
        queue.submit("p")
    stored = read_json(path, RunQueueFile)
    assert stored is not None and stored.rev == 50 and stored.entries == []
    assert "changed under this instance" in caplog.text
    queue.nudge()  # the next save is made against what is stored now and lands
    landed = read_json(path, RunQueueFile)
    assert landed is not None and landed.rev == 51 and len(landed.entries) == 2


# ---- intake lock -------------------------------------------------------------------------------


def test_the_intake_lock_is_a_store_key_with_one_holder_and_a_stale_takeover(root: Path) -> None:
    store = ProjectStore("p", root)
    with intake_lock(store, timeout_s=5.0) as beat:
        assert read_text_path(store.paths.dir / ".intake.lock") == ""
        with pytest.raises(IntakeBusy), intake_lock(store, timeout_s=0.2, poll_s=0.01):
            pass
        beat()
        with intake_lock(store, timeout_s=2.0, stale_s=-1.0, poll_s=0.01):
            pass  # a lock not touched within `stale_s` is taken over (a killed holder)
    assert read_text_path(store.paths.dir / ".intake.lock") is None
    assert _files(root) == []


# ---- the M53-gated raw reads -------------------------------------------------------------------


def test_the_pinned_ceo_list_is_stored_and_read_through_the_store(root: Path) -> None:
    raw = json.dumps({"items": [{"id": "A1", "priority": "P1", "technique": "inbox"}]}).encode()
    pin = bench_inputs.save_atomic_list("demo", raw, "u@x.test", root)
    listed, digest = bench_inputs.load_pinned_list("demo", root)
    assert digest == pin.sha256 and len(listed.items) == 1
    assert [f for f in _files(root) if not f.endswith(".lock")] == []
    filestore.delete_path(root / ".work" / "ceo-bench" / "demo" / bench_inputs.LIST_NAME)
    with pytest.raises(bench_inputs.ListRefused, match="no atomic list"):
        bench_inputs.load_pinned_list("demo", root)


def test_a_stored_project_is_found_by_the_provider_migration_planner(root: Path) -> None:
    from autotester.providers.config_migration import plan_legacy_roles
    from autotester.schema.project import Project

    ProjectStore("p", root).save_project(
        Project(slug="p", name="P", base_url="https://x.test", allowed_domains=["x.test"]))
    entry = plan_legacy_roles(root, ["p"]).entries[0]
    assert entry.status != "missing" and entry.before_sha256 is not None
    write_text(root / "projects" / "p" / "project.json", "{not json")
    assert plan_legacy_roles(root, ["p"]).entries[0].status == "invalid"
