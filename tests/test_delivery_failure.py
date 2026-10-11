"""Delivery failure is recorded, bounded, redacted and harmless (team-test-button.md TT9;
hosting.md HO29), and one run is delivered once (brief item 3: idempotency).

The clock is injected and nothing sleeps. Transports are fakes; no network is touched.
"""

from __future__ import annotations

import threading
from datetime import timedelta
from pathlib import Path

import pytest
from delivery_fakes import (
    CANARY_SECRET,
    FAKE_PASSWORD,
    NOW,
    OkTransport,
    RaisingTransport,
    forbid_real_smtp,
    recipient,
    summary,
)

from autotester.core.redact import Redactor
from autotester.delivery.email import OutboxAdapter
from autotester.delivery.inbox import (
    MAX_ATTEMPTS,
    RETRY_DELAYS,
    STALE_AFTER,
    DeliveryLog,
    deliver_once,
    delivery_key,
    next_retry_at,
    retry_delay,
)
from autotester.delivery.message import render_message
from autotester.schema.delivery import DeliveryChannel, DeliveryRecord, DeliveryStatus

MSG = render_message(summary())


@pytest.fixture(autouse=True)
def _no_real_smtp(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    return forbid_real_smtp(monkeypatch)


def _send(log: DeliveryLog, transport: object, now=NOW, **kw: object):
    scrub = kw.pop("scrub", Redactor({"PW": FAKE_PASSWORD, "CANARY": CANARY_SECRET}).scrub)
    return deliver_once(log, transport, recipient(), MSG, run_id="run-0001", now=now,
                        scrub=scrub, **kw)  # type: ignore[arg-type]


def test_backoff_is_a_pure_increasing_bounded_schedule() -> None:
    delays = [retry_delay(n) for n in range(1, MAX_ATTEMPTS)]
    assert delays == list(RETRY_DELAYS) == sorted(delays) and delays[0] > timedelta(0)
    assert retry_delay(MAX_ATTEMPTS) is None and retry_delay(MAX_ATTEMPTS + 5) is None
    assert len(RETRY_DELAYS) + 1 == MAX_ATTEMPTS
    assert next_retry_at(NOW, 1) == NOW + RETRY_DELAYS[0]
    assert next_retry_at(NOW, MAX_ATTEMPTS) is None
    with pytest.raises(ValueError):
        retry_delay(0)


def test_a_transport_that_always_fails_leaves_a_failed_record_bounded_by_the_attempt_limit(
        tmp_path: Path) -> None:
    log, transport, now = DeliveryLog(tmp_path), RaisingTransport("SMTPServerDisconnected"), NOW
    seen = []
    for _ in range(MAX_ATTEMPTS + 3):  # keep calling past the bound
        rec = _send(log, transport, now)
        seen.append(rec)
        if rec and rec.next_retry_at:
            now = rec.next_retry_at
    final = log.latest(delivery_key("run-0001", DeliveryChannel.EMAIL, "user-a"))
    assert transport.calls == MAX_ATTEMPTS
    assert final.status is DeliveryStatus.FAILED and final.attempts == MAX_ATTEMPTS
    assert final.next_retry_at is None and final.recipient_user_id == "user-a"
    assert len(log.records_for_run("run-0001")) == MAX_ATTEMPTS


def test_a_retry_is_not_attempted_before_it_is_due(tmp_path: Path) -> None:
    log, transport = DeliveryLog(tmp_path), RaisingTransport("TimeoutError")
    first = _send(log, transport, NOW)
    assert first.attempts == 1 and first.next_retry_at == NOW + RETRY_DELAYS[0]
    _send(log, transport, NOW + RETRY_DELAYS[0] - timedelta(seconds=1))
    assert transport.calls == 1
    _send(log, transport, NOW + RETRY_DELAYS[0])
    assert transport.calls == 2


def test_failure_text_is_redacted_in_the_record_and_on_disk(tmp_path: Path) -> None:
    log = DeliveryLog(tmp_path)
    rec = _send(log, RaisingTransport(f"auth failed with {FAKE_PASSWORD} and {CANARY_SECRET}"))
    assert rec.error and FAKE_PASSWORD not in rec.error and CANARY_SECRET not in rec.error
    blob = "".join(p.read_text("utf-8") for p in tmp_path.rglob("*") if p.is_file())
    assert FAKE_PASSWORD not in blob and CANARY_SECRET not in blob
    assert "dev.a@example.test" not in blob  # the record stores the user id, not the address


def test_an_unexpected_exception_is_contained_recorded_and_scrubbed(tmp_path: Path) -> None:
    class Boom:
        outcome = DeliveryStatus.SENT

        def send(self, to: object, message: object, *, key: str) -> None:
            raise RuntimeError(f"explode {CANARY_SECRET}")

    rec = _send(DeliveryLog(tmp_path), Boom())  # must not raise: a mail failure never fails a run
    assert rec.status is DeliveryStatus.FAILED and CANARY_SECRET not in (rec.error or "")


def test_a_successful_send_is_recorded_once_and_replays_deliver_nothing(tmp_path: Path) -> None:
    transport = OkTransport()
    first = _send(DeliveryLog(tmp_path), transport)
    assert first.status is DeliveryStatus.SENT and first.attempts == 1
    for _ in range(3):  # a restart replays recover(): new log object, same directory
        again = _send(DeliveryLog(tmp_path), transport, NOW + timedelta(hours=1))
        assert again.status is DeliveryStatus.SENT
    assert transport.sent == [delivery_key("run-0001", DeliveryChannel.EMAIL, "user-a")]
    assert len(DeliveryLog(tmp_path).records_for_run("run-0001")) == 1


def test_the_outbox_transport_records_outboxed_not_sent(tmp_path: Path) -> None:
    rec = _send(DeliveryLog(tmp_path / "log"), OutboxAdapter(tmp_path / "box"))
    assert rec.status is DeliveryStatus.OUTBOXED
    assert len(list((tmp_path / "box").iterdir())) == 1


def test_a_crash_between_sent_and_recorded_is_never_resent(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = OkTransport()
    log = DeliveryLog(tmp_path)

    def die(*a: object, **k: object) -> None:
        raise OSError("disk went away after the message left")

    monkeypatch.setattr(DeliveryLog, "append", die)
    with pytest.raises(OSError):
        _send(log, transport)
    monkeypatch.undo()
    forbid_real_smtp(monkeypatch)
    in_flight = _send(DeliveryLog(tmp_path), transport, NOW + timedelta(minutes=1))
    assert in_flight is None and len(transport.sent) == 1          # may still be running: wait
    healed = _send(DeliveryLog(tmp_path), transport, NOW + STALE_AFTER)
    assert healed.status is DeliveryStatus.FAILED and healed.next_retry_at is None
    assert "not resent" in healed.error and len(transport.sent) == 1


def test_two_workers_racing_for_one_attempt_send_exactly_once(tmp_path: Path) -> None:
    gate, transport = threading.Barrier(2), OkTransport()
    logs = [DeliveryLog(tmp_path), DeliveryLog(tmp_path)]

    def work(log: DeliveryLog) -> None:
        gate.wait()
        _send(log, transport)

    threads = [threading.Thread(target=work, args=(lg,)) for lg in logs]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(transport.sent) == 1


def test_the_key_cannot_escape_the_log_directory() -> None:
    for run_id, user in (("../x", "u"), ("a/b", "u"), ("r", "..\\u"), ("", "u"), ("r", "a" * 99)):
        with pytest.raises(ValueError):
            delivery_key(run_id, DeliveryChannel.EMAIL, user)


def test_records_are_append_only_files_never_rewritten(tmp_path: Path) -> None:
    log, transport = DeliveryLog(tmp_path), RaisingTransport("OSError")
    first = _send(log, transport, NOW)
    path = next(p for p in tmp_path.rglob("*.json") if "records" in p.parts)
    before = path.read_bytes()
    _send(log, transport, first.next_retry_at)
    assert path.read_bytes() == before and len(list(path.parent.glob("*.json"))) == 2


def test_create_once_is_pinned_for_records_and_claims_on_their_own(tmp_path: Path) -> None:
    log, key = DeliveryLog(tmp_path), delivery_key("run-0001", DeliveryChannel.EMAIL, "user-a")
    first = DeliveryRecord(run_id="run-0001", channel=DeliveryChannel.EMAIL,
                           recipient_user_id="user-a", status=DeliveryStatus.SENT, attempts=1)
    log.append(key, first)
    path = log.records_dir / f"{key}.01.json"
    before = path.read_bytes()
    other = first.model_copy(update={"status": DeliveryStatus.FAILED, "error": "overwritten"})
    with pytest.raises(FileExistsError):    # a second writer loses; it does not replace the file
        log.append(key, other)
    assert path.read_bytes() == before
    assert log.claim(key, 1, NOW) is True and log.claim(key, 1, NOW + STALE_AFTER) is False
    assert log.claimed_at(key, 1) == NOW    # the first claim stands


def _mail(log: DeliveryLog, transport: OkTransport, run_id: str, user: str, now=NOW):
    return deliver_once(log, transport, recipient(user), MSG, run_id=run_id, now=now,
                        scrub=Redactor({}).scrub)


IDS = ["x", "y", "z", "x_", "x__", "x_y", "X", "x.1", "x.01", "x__email__y",
       "y__email__z", "email", "alice", "alice.smith", "Alice", "a-b", "a_b", "a--b"]


def test_the_delivery_key_is_injective_even_on_a_case_insensitive_file_system() -> None:
    keys = {}
    for run in IDS:
        for channel in DeliveryChannel:
            for user in IDS:
                keys.setdefault(delivery_key(run, channel, user).lower(), []).append(
                    (run, channel, user))
    assert all(len(v) == 1 for v in keys.values()), [v for v in keys.values() if len(v) > 1]
    assert len(keys) == len(IDS) ** 2 * len(DeliveryChannel)


def test_a_dotted_prefix_user_does_not_suppress_the_shorter_one(tmp_path: Path) -> None:
    log, transport = DeliveryLog(tmp_path), OkTransport()
    smith = _mail(log, transport, "run-1", "alice.smith")
    alice = _mail(log, transport, "run-1", "alice")           # was: nothing sent, smith's record
    assert alice is not None and alice.recipient_user_id == "alice"
    assert smith.recipient_user_id == "alice.smith" and len(transport.sent) == 2
    assert [r.recipient_user_id for r in log.records_for_key(
        delivery_key("run-1", DeliveryChannel.EMAIL, "alice"))] == ["alice"]
    assert _mail(log, transport, "run-1", "alice", NOW + timedelta(hours=1)) == alice
    assert len(transport.sent) == 2


def test_run_and_user_ids_that_spell_the_separator_do_not_collide(tmp_path: Path) -> None:
    log, transport = DeliveryLog(tmp_path), OkTransport()
    a = _mail(log, transport, "x__email__y", "z")
    b = _mail(log, transport, "x", "y__email__z")
    assert a.run_id == "x__email__y" and b.run_id == "x" and len(transport.sent) == 2
    assert [r.run_id for r in log.records_for_run("x")] == ["x"]            # not x__email__y's
    assert [r.run_id for r in log.records_for_run("x__email__y")] == ["x__email__y"]
    _mail(log, transport, "X", "z")                                       # case differs: own file
    assert len(transport.sent) == 3 and len(log.records_for_run("x")) == 1


def test_lookups_match_whole_file_names_and_ignore_stray_files(tmp_path: Path) -> None:
    log, transport = DeliveryLog(tmp_path), OkTransport()
    _mail(log, transport, "run-1", "alice")
    key = delivery_key("run-1", DeliveryChannel.EMAIL, "alice")
    for stray in (f"{key}.foo.json", f"{key}.01.json.bak", f"{key}.json"):
        (log.records_dir / stray).write_text("not a record", encoding="utf-8")
    assert len(log.records_for_key(key)) == 1 and len(log.records_for_run("run-1")) == 1
    assert log.records_for_run("run") == [] and log.records_for_key(key[:-1]) == []
    # `<key>.01.02.json` is the file of user `alice.01` attempt 2, not a second record of alice
    (log.records_dir / f"{key}.01.02.json").write_text("{}", encoding="utf-8")
    assert len(log.records_for_key(key)) == 1


def test_a_clock_skewed_worker_closing_a_live_attempt_does_not_break_the_first_worker(
        tmp_path: Path) -> None:
    bystander, results = OkTransport(), []

    class Racing:
        """Worker 1's transport; mid-send, worker 2 runs with a clock past STALE_AFTER."""

        outcome = DeliveryStatus.SENT
        sent = 0

        def send(self, to: object, message: object, *, key: str) -> None:
            self.sent += 1
            results.append(_send(DeliveryLog(tmp_path), bystander, NOW + STALE_AFTER))

    racer = Racing()
    first = _send(DeliveryLog(tmp_path), racer)               # must not raise FileExistsError
    assert racer.sent == 1 and bystander.sent == []           # worker 2 sent nothing
    closed = results[0]
    assert closed is not None and closed.status is DeliveryStatus.FAILED
    assert "outcome unknown" in closed.error and "may or may not have been sent" in closed.error
    assert first == closed                                    # worker 1 reports what is on disk
    files = list(DeliveryLog(tmp_path).records_dir.glob("*.json"))
    assert len(files) == 1 and len(DeliveryLog(tmp_path).records_for_run("run-0001")) == 1
    assert _send(DeliveryLog(tmp_path), racer, NOW + timedelta(hours=3)) == closed
    assert racer.sent == 1 and bystander.sent == []
