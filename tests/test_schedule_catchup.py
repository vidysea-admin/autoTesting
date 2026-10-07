"""TS3: a slot missed during downtime fires at most one catch-up inside the grace window; the
rest are recorded `missed`, never backfilled. Injected clock; nothing sleeps.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from schedule_fakes import daily, make_deps, one_offs, utc

from autotester.schema.schedule import SlotOutcome
from autotester.stages import scheduler
from autotester.stages.schedule_store import read_records
from autotester.stages.scheduler import grace_from_env, tick_project


def _outcomes(path: Path) -> list[str]:
    return [r.outcome.value for r in read_records(path)]


def test_a_30_minute_outage_fires_one_catch_up(tmp_path: Path) -> None:
    """The server was down 08:55-09:30 and the 09:00 daily slot passed unseen."""
    deps, q = make_deps(tmp_path, "p")
    tick_project("p", daily(), utc(2026, 10, 8, 9, 30), deps, since=utc(2026, 10, 7, 12))
    assert len(q) == 1
    assert _outcomes(deps.records_path) == ["catch_up"]


def test_a_slot_seen_on_time_is_enqueued_not_labelled_catch_up(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 30), deps, since=utc(2026, 10, 7, 12))
    assert len(q) == 1
    assert _outcomes(deps.records_path) == ["enqueued"]


@pytest.mark.parametrize(
    ("now", "runs", "outcome"),
    [
        (utc(2026, 10, 8, 10, 0, 0), 1, "catch_up"),   # exactly 60 min: inside the window
        (utc(2026, 10, 8, 10, 0, 59), 1, "catch_up"),  # 60 min to the minute: still inside
        (utc(2026, 10, 8, 10, 1, 0), 0, "missed"),     # 61 min: outside
    ],
    ids=["60-min", "60-min-plus-59s", "61-min"],
)
def test_the_60_minute_window_edge_is_inclusive(
    tmp_path: Path, now, runs: int, outcome: str
) -> None:
    deps, q = make_deps(tmp_path, "p")
    tick_project("p", daily(), now, deps, since=utc(2026, 10, 7, 12))
    assert len(q) == runs
    assert _outcomes(deps.records_path) == [outcome]


def test_a_three_day_outage_never_backfills_more_than_one_run(tmp_path: Path) -> None:
    """Server down from Oct 4 evening to Oct 7 10:30: slots Oct 5, 6, 7 (09:00) all passed."""
    deps, q = make_deps(tmp_path, "p")
    out = tick_project("p", daily(), utc(2026, 10, 7, 10, 30), deps, since=utc(2026, 10, 4, 18))
    assert len(q) == 0
    assert _outcomes(deps.records_path) == ["missed"] * 3
    assert len(out) == 3


def test_three_day_outage_with_the_latest_slot_still_in_window_runs_exactly_one(
    tmp_path: Path,
) -> None:
    deps, q = make_deps(tmp_path, "p")
    tick_project("p", daily(), utc(2026, 10, 7, 9, 20), deps, since=utc(2026, 10, 4, 18))
    assert len(q) == 1
    assert sorted(_outcomes(deps.records_path)) == ["catch_up", "missed", "missed"]


def test_two_slots_inside_the_window_run_only_the_latest_and_the_earlier_is_superseded(
    tmp_path: Path,
) -> None:
    """A user picked two one-off times 30 minutes apart and the server was down for both."""
    deps, q = make_deps(tmp_path, "p")
    cfg = one_offs("2026-10-08T09:00", "2026-10-08T09:30")
    tick_project("p", cfg, utc(2026, 10, 8, 9, 40), deps, since=utc(2026, 10, 8, 8))
    assert len(q) == 1
    recs = {r.slot_key: r for r in read_records(deps.records_path)}
    latest, earlier = "p:custom:2026-10-08T09:30Z", "p:custom:2026-10-08T09:00Z"
    assert recs[latest].outcome is SlotOutcome.CATCH_UP
    assert recs[earlier].outcome is SlotOutcome.MISSED
    assert recs[earlier].superseded_by == latest


def test_a_missed_slot_is_never_re_examined_by_a_later_tick(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    tick_project("p", daily(), utc(2026, 10, 8, 12), deps, since=utc(2026, 10, 7, 12))
    assert _outcomes(deps.records_path) == ["missed"]
    for later in (utc(2026, 10, 8, 12, 1), utc(2026, 10, 8, 18), utc(2026, 10, 9, 8)):
        assert tick_project("p", daily(), later, deps, since=utc(2026, 10, 7, 12)) == []
    assert len(q) == 0
    assert _outcomes(deps.records_path) == ["missed"]


def test_an_expired_one_off_is_recorded_missed_and_stays_in_the_config(tmp_path: Path) -> None:
    """The user's one-off was missed by a weekend outage: it must show as `missed`, not vanish."""
    deps, q = make_deps(tmp_path, "p")
    cfg = one_offs("2026-10-08T09:00")
    tick_project("p", cfg, utc(2026, 10, 10, 9), deps, since=utc(2026, 10, 7))
    assert len(q) == 0
    assert _outcomes(deps.records_path) == ["missed"]
    assert cfg.one_offs  # not silently deleted


def test_a_tick_killed_while_recording_a_missed_slot_resumes_without_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deps, _ = make_deps(tmp_path, "p")
    since = utc(2026, 10, 7, 12)
    real = scheduler.append_record
    calls = {"n": 0}

    def die_once(path, rec):
        calls["n"] += 1
        if calls["n"] == 1:
            raise SystemExit(1)
        real(path, rec)

    monkeypatch.setattr(scheduler, "append_record", die_once)
    with pytest.raises(SystemExit):
        tick_project("p", daily(), utc(2026, 10, 8, 12), deps, since=since)
    assert read_records(deps.records_path) == []  # claimed, record not yet written
    tick_project("p", daily(), utc(2026, 10, 8, 12, 5), deps, since=since)
    tick_project("p", daily(), utc(2026, 10, 8, 12, 9), deps, since=since)
    assert _outcomes(deps.records_path) == ["missed"]


@pytest.mark.parametrize(
    ("env", "grace", "warns"),
    [
        ({}, 60, False),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": "30"}, 30, False),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": "1"}, 1, False),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": "1440"}, 1440, False),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": "0"}, 60, True),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": "1441"}, 60, True),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": "soon"}, 60, True),
        ({"AUTOTESTER_SCHEDULE_GRACE_MINUTES": ""}, 60, True),
    ],
)
def test_grace_window_comes_from_the_env_and_falls_back_to_60_saying_so(
    env: dict, grace: int, warns: bool
) -> None:
    value, warning = grace_from_env(env)
    assert value == grace
    assert (warning is not None) is warns


def test_a_shorter_operator_grace_window_is_honoured(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    tick_project("p", daily(), utc(2026, 10, 8, 9, 31), deps, since=utc(2026, 10, 7, 12),
                 grace_minutes=30)
    assert len(q) == 0
    assert _outcomes(deps.records_path) == ["missed"]
