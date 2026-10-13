"""T-201 TT7 / D-093 item 2: a finished request writes one `inbox` DeliveryRecord per recipient.

Real RunQueue with a manual spawner: done, failed and refused each leave exactly one record
(status sent, the presser as recipient); a queued or running request leaves none; reading the
inbox or finishing again never adds a second; a hostile project/run name is inert on /inbox.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import gate_on, project, team, user_id

from autotester.delivery.inbox import DeliveryLog
from autotester.schema.delivery import DeliveryChannel, DeliveryRecord, DeliveryStatus
from autotester.stages.report_delivery import record_inbox_delivery
from autotester.ui import routes_inbox, run_queue

HTML = {"accept": "text/html"}


def _queue(tmp_path: Path, runner, jobs: list) -> run_queue.RunQueue:
    return run_queue.RunQueue(limit=lambda: 5, spawn=jobs.append, runner=runner,
                              delivery=lambda: tmp_path / "delivery")


def _all(log: DeliveryLog):
    if not log.records_dir.is_dir():
        return
    for path in sorted(log.records_dir.glob("*.json")):
        yield DeliveryRecord.model_validate_json(path.read_text("utf-8"))


def _boom(entry):
    if entry.id == "run-failed":
        raise ValueError("x")
    if entry.id == "run-refused":
        raise run_queue.RunRefused("no")


@pytest.mark.parametrize("run_id", ["run-done", "run-failed", "run-refused"])
def test_finished_request_writes_one_inbox_record(tmp_path: Path, run_id: str) -> None:
    jobs: list = []
    queue = _queue(tmp_path, _boom, jobs)
    queue.submit("alpha", requested_by="dev@team.test", requested_by_id=7, run_id=run_id)
    assert list(_all(DeliveryLog(tmp_path / "delivery"))) == []         # running: nothing yet
    jobs.pop()()
    (rec,) = list(_all(DeliveryLog(tmp_path / "delivery")))
    assert (rec.run_id, rec.channel, rec.recipient_user_id, rec.status) == (
        run_id, DeliveryChannel.INBOX, "7", DeliveryStatus.SENT)


def test_queued_writes_none_and_redelivery_is_idempotent(tmp_path: Path) -> None:
    jobs: list = []
    queue = run_queue.RunQueue(limit=lambda: 1, spawn=jobs.append, runner=lambda e: None,
                               delivery=lambda: tmp_path / "delivery")
    queue.submit("alpha", requested_by_id=7, run_id="run-a")
    queue.submit("alpha", requested_by_id=7, run_id="run-b")            # queued behind a
    jobs.pop(0)()                                                        # a finishes; b starts
    log = DeliveryLog(tmp_path / "delivery")
    assert [r.run_id for r in _all(log)] == ["run-a"]
    done = next(e for e in queue.snapshot() if e.id == "run-a")
    assert record_inbox_delivery(done, log) is False                    # already written
    queue.recover()                  # restart: b was running, becomes interrupted, gets its row
    assert sorted(r.run_id for r in _all(log)) == ["run-a", "run-b"]
    queue.recover()                  # a second restart adds nothing
    assert sorted(r.run_id for r in _all(log)) == ["run-a", "run-b"]


def test_no_known_recipient_writes_nothing(tmp_path: Path) -> None:
    jobs: list = []
    queue = _queue(tmp_path, lambda e: None, jobs)
    queue.submit("alpha", requested_by=None, run_id="run-anon")
    jobs.pop()()
    assert list(_all(DeliveryLog(tmp_path / "delivery"))) == []


def test_reading_inbox_writes_no_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = gate_on(tmp_path, monkeypatch)
    project(root, "alpha")
    jobs: list = []
    queue = _queue(tmp_path, lambda e: None, jobs)
    monkeypatch.setattr(routes_inbox, "get_queue", lambda: queue)
    users = team()
    queue.submit("alpha", requested_by="admin@team.test",
                 requested_by_id=user_id("admin@team.test"), run_id="run-x")
    jobs.pop()()
    before = list(_all(DeliveryLog(tmp_path / "delivery")))
    for _ in range(3):
        users["admin"].get("/inbox", headers=HTML)
    assert list(_all(DeliveryLog(tmp_path / "delivery"))) == before and len(before) == 1


def test_hostile_names_are_inert_on_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = gate_on(tmp_path, monkeypatch)
    project(root, "alpha")
    jobs: list = []
    queue = _queue(tmp_path, lambda e: None, jobs)
    monkeypatch.setattr(routes_inbox, "get_queue", lambda: queue)
    users = team()
    evil = "<script>alert(1)</script>"
    queue.submit("alpha", requested_by=evil,
                 requested_by_id=user_id("admin@team.test"),
                 run_id="run-evil")
    jobs.pop()()
    page = users["admin"].get("/inbox", headers=HTML).text
    assert "<script>alert(1)" not in page and "<img src=x" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page      # shown, as text
    assert "run-evil" in page            # the row is there, the payload is just text
