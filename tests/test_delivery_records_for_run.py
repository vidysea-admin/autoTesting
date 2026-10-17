"""`DeliveryLog.records_for_run` matches a run id exactly, never as a pattern (AT-967).

A run id may contain `.`; if the lookup regex left it unescaped, `run.1` would also return the
records of `run-1` and `run.` those of `run-`, so one run's page would show another run's
delivery attempts. The clock is injected, the transport is a fake, no network is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from delivery_fakes import NOW, OkTransport, forbid_real_smtp, recipient, summary

from autotester.core.redact import Redactor
from autotester.delivery.inbox import DeliveryLog, deliver_once
from autotester.delivery.message import render_message

MSG = render_message(summary())
# Each pair differs only where one id has `.` and the other a character that `.` would match.
LOOKALIKES = [("run.1", "run-1"), ("run.", "run-"), ("run-1.", "run-1-")]


@pytest.fixture(autouse=True)
def _no_real_smtp(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    return forbid_real_smtp(monkeypatch)


def _mail(log: DeliveryLog, transport: OkTransport, run_id: str, user: str) -> None:
    deliver_once(log, transport, recipient(user), MSG, run_id=run_id, now=NOW,
                 scrub=Redactor({}).scrub)


@pytest.mark.parametrize(("dotted", "dashed"), LOOKALIKES)
def test_a_dotted_run_id_does_not_pull_in_the_records_of_its_dashed_lookalike(
        tmp_path: Path, dotted: str, dashed: str) -> None:
    log, transport = DeliveryLog(tmp_path), OkTransport()
    for run in (dotted, dashed):
        for user in ("alice", "bob"):
            _mail(log, transport, run, user)
    assert len(transport.sent) == 4                     # four distinct keys, none suppressed
    for run in (dotted, dashed):
        records = log.records_for_run(run)
        assert sorted(r.recipient_user_id for r in records) == ["alice", "bob"]
        assert {r.run_id for r in records} == {run}


def test_a_run_id_with_no_records_returns_nothing_next_to_a_dotted_neighbour(
        tmp_path: Path) -> None:
    log, transport = DeliveryLog(tmp_path), OkTransport()
    _mail(log, transport, "run-1", "alice")
    assert log.records_for_run("run.1") == [] and log.records_for_run("run.") == []
    assert log.records_for_run("run-1.") == [] and len(log.records_for_run("run-1")) == 1
