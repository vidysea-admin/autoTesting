"""When the tick log itself is corrupt, not merely gappy.

AT-399. Split from `test_loop_status.py` (doctor's 300-line rule) along a real
seam: that file asks what the log RECORDS — outages, pauses, what the tool cannot
know. This one asks whether the log can be TRUSTED, which is a prior question. It
matters because the first version of this module answered it by silently sorting
the stamps, and a repaired log reads exactly like a healthy one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.loop_status import Anomalies, read_ticks, report_lines, status

runner = CliRunner()


def _at(day: int, hour: int = 0, offset: str = "+00:00") -> str:
    return f"2026-09-{day:02d}T{hour:02d}:00:00{offset}"


def _tick_log(tmp_path: Path, lines: list[str]) -> Path:
    qa = tmp_path / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / ".last-tick").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path

def test_one_future_stamp_cannot_make_a_dead_loop_read_as_alive(
    tmp_path: Path,
) -> None:
    """The defect, measured before it was fixed: this module used to SORT the
    stamps, so a tick dated into the future became `ticks[-1]`, the open gap
    `now - ticks[-1]` went negative, and `asleep_now` returned False **for as
    long as that stamp stayed in the future**.

    One mistyped timestamp silenced the instrument built to notice a dead loop —
    the module's own failure mode, arriving through its own input. Here the loop
    has genuinely been silent since 2026-09-11 and the future stamp must not
    conceal it."""
    root = _tick_log(tmp_path, [
        f"{_at(11, 9)} ADVANCED the last real tick",
        f"{_at(16, 23)} ADVANCED a stamp typed eight hours ahead",
    ])
    report = status(root, now=datetime(2026, 9, 16, 15, tzinfo=UTC))

    assert report.anomalies.future == 1
    assert report.last_tick == datetime(2026, 9, 11, 9, tzinfo=UTC), "the last CREDIBLE tick"
    assert report.asleep_now is True, "the outage is visible despite the future stamp"


def test_a_future_stamp_does_not_inflate_the_gap_it_sits_at_the_end_of(
    tmp_path: Path,
) -> None:
    """Excluding it matters twice: the open gap reappears, and the gap that ends
    at it is no longer measured to a time that has not happened."""
    root = _tick_log(tmp_path, [
        f"{_at(11, 9)} ADVANCED real",
        f"{_at(16, 23)} ADVANCED eight hours ahead",
    ])
    report = status(root, now=datetime(2026, 9, 16, 15, tzinfo=UTC))

    assert len(report.gaps) == 1, "one open gap, not a closed gap ending in the future"
    assert report.gaps[0].end == datetime(2026, 9, 16, 15, tzinfo=UTC)
    assert 125 < report.gaps[0].hours < 127, "measured to now (~126h), not to the false stamp"


def test_out_of_order_ticks_are_reported_rather_than_silently_sorted(
    tmp_path: Path,
) -> None:
    """Sorting repaired the log and a repaired log reads as a healthy one. The
    arithmetic still needs chronological order, so `status` sorts — but only
    after recording that the raw order was wrong."""
    root = _tick_log(tmp_path, [
        f"{_at(16, 10)} ADVANCED written first, later time",
        f"{_at(16, 8)} ADVANCED written second, earlier time",
    ])
    report = status(root, now=datetime(2026, 9, 16, 11, tzinfo=UTC))

    assert report.anomalies.out_of_order == 1
    assert report.anomalies.any is True


def test_read_ticks_preserves_file_order(tmp_path: Path) -> None:
    """The load-bearing half of the fix: if this re-sorted, `status` could never
    see that anything was wrong."""
    root = _tick_log(tmp_path, [
        f"{_at(16, 10)} ADVANCED later time first",
        f"{_at(16, 8)} ADVANCED earlier time second",
    ])
    ticks = read_ticks(root / "qa" / ".last-tick")

    assert ticks[0] > ticks[1], "file order, not chronological order"


def test_a_healthy_log_reports_no_anomalies(tmp_path: Path) -> None:
    """The corruption check must be able to say 'nothing wrong', or it is an
    alarm that is always on."""
    root = _tick_log(tmp_path, [
        f"{_at(16, 5)} ADVANCED one",
        f"{_at(16, 6)} ADVANCED two",
    ])
    report = status(root, now=datetime(2026, 9, 16, 7, tzinfo=UTC))

    assert report.anomalies.any is False
    assert report.anomalies == Anomalies(future=0, out_of_order=0)


def test_the_corruption_is_printed_not_only_counted(tmp_path: Path) -> None:
    """Same lesson as AT-366 and AT-396: a structured field nothing renders is
    the same silence one layer up."""
    root = _tick_log(tmp_path, [
        f"{_at(11, 9)} ADVANCED real",
        f"{_at(16, 23)} ADVANCED ahead",
    ])
    rendered = "\n".join(text for text, _ in report_lines(
        status(root, now=datetime(2026, 9, 16, 15, tzinfo=UTC))))

    assert "CORRUPT" in rendered
    assert "dated after now" in rendered
    assert "alive indefinitely" in rendered, "the consequence, not just the count"


# -- AT-424: an all-future log is CORRUPT, not empty ---------------------------

def test_an_all_future_log_is_not_reported_as_no_ticks_recorded(tmp_path: Path) -> None:
    """The exact shape of AT-424: every stamp in the log is future-dated, so
    `credible` is empty and `last_tick` is None -- but `ticks` is 1, not 0. The
    old code returned early on `last_tick is None`, before the CORRUPT row for
    the future stamp was ever appended, so this rendered as the same line an
    untouched project gets. A log with one corrupt stamp in it is not the same
    fact as a log with nothing in it, and must not render as the same line."""
    root = _tick_log(tmp_path, [f"{_at(16, 23)} ADVANCED a stamp typed 8h ahead"])
    report = status(root, now=datetime(2026, 9, 16, 15, tzinfo=UTC))
    assert report.last_tick is None, "no credible tick survives -- the AT-424 precondition"
    assert report.anomalies.any is True

    rendered = [text for text, _ in report_lines(report)]

    assert rendered != ["loop-status: no ticks recorded"], (
        "an all-future log must never render as an empty one")
    assert any("CORRUPT" in line for line in rendered)
    assert any("dated after now" in line for line in rendered)


def test_a_truly_empty_log_still_reports_no_ticks_recorded(tmp_path: Path) -> None:
    """The fix must not overcorrect: zero parseable ticks is still exactly the
    'no ticks recorded' case AT-424's own `expected` carves out."""
    (tmp_path / "qa").mkdir()
    rendered = [text for text, _ in report_lines(
        status(tmp_path, now=datetime(2026, 9, 16, 7, tzinfo=UTC)))]

    assert rendered == ["loop-status: no ticks recorded"]


def test_an_all_future_log_does_not_also_claim_no_gaps(tmp_path: Path) -> None:
    """With no credible tick, `find_gaps` sees an empty ticks list and reports no
    gaps -- correct for the gap arithmetic, but printing the healthy-loop 'no
    gaps' line right under a CORRUPT row would tell the reader two contradictory
    things in the same breath. The 'ok' all-clear belongs only to a log that has
    at least one credible tick to be clear about."""
    root = _tick_log(tmp_path, [f"{_at(16, 23)} ADVANCED a stamp typed 8h ahead"])
    rendered = [text for text, _ in report_lines(
        status(root, now=datetime(2026, 9, 16, 15, tzinfo=UTC)))]

    assert not any("no gaps" in line for line in rendered), (
        "a corrupt, credible-tick-free log is not a clean loop")


# -- AT-592: --strict must fail on a log with no credible tick at all ----------

def test_strict_unhealthy_is_true_when_every_stamp_is_future(tmp_path: Path) -> None:
    """The defect itself: `asleep_now` only fires off an OPEN GAP, and
    `find_gaps` over an empty `credible` list returns `((), None)` -- no gap to
    key off, so an all-future log (CORRUPT, `last_tick is None`, `ticks == 1`)
    read as healthy. `strict_unhealthy` must catch what `asleep_now` cannot."""
    root = _tick_log(tmp_path, [f"{_at(16, 23)} ADVANCED a stamp typed 8h ahead"])
    report = status(root, now=datetime(2026, 9, 16, 15, tzinfo=UTC))

    assert report.last_tick is None
    assert report.asleep_now is False, "the old, insufficient signal"
    assert report.strict_unhealthy is True, "the new one must see it anyway"


def test_strict_unhealthy_is_false_on_a_healthy_log(tmp_path: Path) -> None:
    """The new signal must not turn into an alarm that is always on."""
    root = _tick_log(tmp_path, [
        f"{_at(16, 5)} ADVANCED one",
        f"{_at(16, 6)} ADVANCED two",
    ])
    report = status(root, now=datetime(2026, 9, 16, 7, tzinfo=UTC))

    assert report.strict_unhealthy is False


def _cli_tick_log(tmp_path: Path, lines: list[str]) -> None:
    qa = tmp_path / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / ".last-tick").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def cli_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def test_cli_strict_exits_nonzero_on_an_all_future_tick_log(cli_root: Path) -> None:
    """The exact bug report, driven through the real CLI: `--strict` must exit
    non-zero on a log every stamp of which is dated after now, even though there
    is no open gap for the old `asleep_now`-only check to find."""
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    _cli_tick_log(cli_root, [f"{future} ADVANCED a stamp typed a day ahead"])

    result = runner.invoke(app, ["loop-status", "--strict"])

    assert result.exit_code != 0, result.output
    assert "CORRUPT" in result.output


def test_cli_strict_exits_zero_on_a_healthy_tick_log(cli_root: Path) -> None:
    """`--strict` must still come back clean on a loop with nothing wrong with
    it, or it is an alarm nobody can trust."""
    now = datetime.now(UTC)
    _cli_tick_log(cli_root, [
        (now - timedelta(minutes=2)).isoformat() + " ADVANCED one",
        (now - timedelta(minutes=1)).isoformat() + " ADVANCED two",
    ])

    result = runner.invoke(app, ["loop-status", "--strict"])

    assert result.exit_code == 0, result.output


def test_cli_non_strict_exit_code_on_the_corrupt_log_is_unchanged(cli_root: Path) -> None:
    """Non-strict behaviour must not move: `loop-status` without `--strict` has
    always exited 0 regardless of what it prints, and this fix only changes what
    `--strict` checks."""
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    _cli_tick_log(cli_root, [f"{future} ADVANCED a stamp typed a day ahead"])

    result = runner.invoke(app, ["loop-status"])

    assert result.exit_code == 0, result.output
    assert "CORRUPT" in result.output


# -- AT-610: write-order corruption stays report-only (answer A) ---------------

def test_out_of_order_ticks_with_a_credible_recent_tick_do_not_gate_strict(tmp_path: Path) -> None:
    """AT-610, answered A (qa/gates/at610-strict-out-of-order.md): `out_of_order`
    counts file-order inversions, but liveness runs on the sorted credible ticks
    -- a reordered log with a recent credible tick is a write-order smell, not a
    liveness lie. The CORRUPT row must still render: report-only means reported."""
    root = _tick_log(tmp_path, [
        f"{_at(16, 10)} ADVANCED written first, later time",
        f"{_at(16, 8)} ADVANCED written second, earlier time",
    ])
    report = status(root, now=datetime(2026, 9, 16, 11, tzinfo=UTC))

    assert report.anomalies.out_of_order == 1
    assert report.strict_unhealthy is False, "write-order corruption alone does not gate --strict"
    rendered = "\n".join(text for text, _ in report_lines(report))
    assert "CORRUPT" in rendered and "out of chronological order" in rendered


def test_cli_strict_zero_on_out_of_order_with_credible_tick(cli_root: Path) -> None:
    """AT-610 answer A, through the real CLI: two recent ticks written out of
    order must still leave `--strict` green."""
    now = datetime.now(UTC)
    _cli_tick_log(cli_root, [
        (now - timedelta(minutes=1)).isoformat() + " ADVANCED written first, later time",
        (now - timedelta(minutes=2)).isoformat() + " ADVANCED written second, earlier time",
    ])

    result = runner.invoke(app, ["loop-status", "--strict"])

    assert result.exit_code == 0, result.output
    assert "CORRUPT" in result.output


def test_cli_strict_nonzero_on_out_of_order_with_stale_tick(cli_root: Path) -> None:
    """AT-610's other half: the pin must not mask a real outage. Out-of-order
    lines with a genuinely stale last tick (`asleep_now`) still exit non-zero --
    write-order corruption never gets to excuse a dead loop."""
    now = datetime.now(UTC)
    _cli_tick_log(cli_root, [
        (now - timedelta(days=10)).isoformat() + " ADVANCED written first, later time",
        (now - timedelta(days=11)).isoformat() + " ADVANCED written second, earlier time",
    ])

    result = runner.invoke(app, ["loop-status", "--strict"])

    assert result.exit_code != 0, result.output
    assert "CORRUPT" in result.output
