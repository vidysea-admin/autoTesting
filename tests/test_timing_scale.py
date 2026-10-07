"""AT-757: `timing_scale()` is default-1.0, loosen-only, capped at 4.0, and a bound
written `BASE * timing_scale()` at the default is bit-identical to today's literal."""

from __future__ import annotations

import pytest
from timing_scale import TIMING_SCALE_ENV, timing_scale


def test_default_is_one_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TIMING_SCALE_ENV, raising=False)
    assert timing_scale() == 1.0


@pytest.mark.parametrize(("raw", "expected"), [("2", 2.0), ("1.5", 1.5), (" 3 ", 3.0), ("4", 4.0)])
def test_valid_value_in_range_is_used(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: float,
) -> None:
    monkeypatch.setenv(TIMING_SCALE_ENV, raw)
    assert timing_scale() == expected


@pytest.mark.parametrize("raw", ["0.5", "0", "-3", "0.999"])
def test_below_one_clamps_up_so_it_can_never_tighten(
    monkeypatch: pytest.MonkeyPatch, raw: str,
) -> None:
    monkeypatch.setenv(TIMING_SCALE_ENV, raw)
    assert timing_scale() == 1.0


@pytest.mark.parametrize("raw", ["4.01", "10", "1000000"])
def test_above_four_clamps_down_to_four(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv(TIMING_SCALE_ENV, raw)
    assert timing_scale() == 4.0


@pytest.mark.parametrize("raw", ["", "   ", "fast", "2x", "nan", "inf", "-inf"])
def test_empty_or_invalid_falls_back_to_one(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv(TIMING_SCALE_ENV, raw)
    assert timing_scale() == 1.0


def test_every_bound_equals_its_literal_at_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(TIMING_SCALE_ENV, raising=False)
    s = timing_scale()
    # The five AT-757 / AT-771 bounds, as they were before the helper existed.
    assert 240.0 * s == 240.0  # crawl_inventory_live wall_clock_s
    assert 60 * s == 60  # mc_sessionstart hook subprocess timeout
    assert 3.0 * s == 3.0  # redact_wrap_perf 500 KB bound
    assert 2.5 * s == 2.5  # redact_ignorable_perf CJK/ASCII multiple
    assert 30.0 * s == 30.0  # video_parallel_sweep _WAIT_S
