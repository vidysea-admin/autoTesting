"""AT-F1/F2 (fix/cli-clamp-and-standing-help): a derived grant clamped at a ceiling SAYS so,
and `derive_grant_bounds` is total (rejects negative / NaN / infinite input, saturates overflow).

Authority: qa/verdicts/auto-size-budget.b.md F1 (a plan over a ceiling looped silently at the
grant step: the hint printed the clamped numbers, `approve` signed them, the run was refused
with the same hint) and F2 (OverflowError above ~1.4e308 wall; negatives unclamped).
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app as cli_app
from autotester.core.consent import ApprovalRequired, require_approval
from autotester.schema.approval import (
    MAX_GRANT_ACTIONS,
    MAX_GRANT_PROBES,
    MAX_GRANT_WALL_CLOCK_S,
    GrantBounds,
    RunApproval,
    derive_grant_bounds,
    grant_clamp_warning,
    invalid_bounds_message,
)
from autotester.schema.case import Case
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

URL = "https://demo.test/login"
SOON = (date.today() + timedelta(days=5)).isoformat()
runner = CliRunner()
LIVE = ApprovalKind.LIVE_CASE


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url=URL, allowed_domains=["demo.test"]))
    return s


def _case(n_steps: int) -> Case:
    steps = [Step(order=i, action=Action.CLICK, target=f"#x{i}",
                  expected=ExpectedState(visible_text=["ok"])) for i in range(n_steps)]
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="t", steps=steps)


# -- F2: derive_grant_bounds is total ------------------------------------------------------

@pytest.mark.parametrize("bad", [(-5, 5, 5.0), (5, -5, 5.0), (5, 5, -5.0),
                                 (5, 5, float("nan")), (5, 5, float("inf")),
                                 (5, 5, float("-inf"))])
def test_negative_nan_and_infinite_inputs_are_rejected_with_a_clear_error(
    bad: tuple[int, int, float],
) -> None:
    with pytest.raises(ValueError, match="grant bounds must be non-negative and finite"):
        derive_grant_bounds(LIVE, *bad)


def test_overflowing_inputs_saturate_at_the_ceilings_instead_of_raising() -> None:
    assert derive_grant_bounds(LIVE, 5, 5, 1.7e308) == GrantBounds(
        7, 140, MAX_GRANT_WALL_CLOCK_S)
    assert derive_grant_bounds(LIVE, 10**400, 10**400, 5.0) == GrantBounds(
        MAX_GRANT_ACTIONS, MAX_GRANT_PROBES, 7.0)


def test_valid_inputs_and_other_kinds_are_unchanged() -> None:
    assert derive_grant_bounds(LIVE, 0, 0, 0.0) == GrantBounds(0, 0, 0.0)
    assert derive_grant_bounds(ApprovalKind.CRAWL, 150, 25, 900.0) == GrantBounds(150, 25, 900.0)
    got = derive_grant_bounds(LIVE, 100, 5, 100.0)
    assert got == GrantBounds(125, 2500, 125.0)


# -- F1: the warning names the bound, the plan and the ceiling -----------------------------

def test_no_warning_while_the_plan_fits_every_ceiling() -> None:
    assert grant_clamp_warning(LIVE, 2000, 40000, 86400.0) == ""
    assert grant_clamp_warning(LIVE, 0, 0, 0.0) == ""


def test_the_warning_names_each_clamped_bound_with_planned_and_ceiling() -> None:
    text = grant_clamp_warning(LIVE, 2100, 42000, 90000.0)
    assert f"actions: planned 2100 > ceiling {MAX_GRANT_ACTIONS}" in text
    assert f"probes: planned 42000 > ceiling {MAX_GRANT_PROBES}" in text
    assert "wall clock: planned 90000s > ceiling 86400s" in text
    assert "split" in text.lower()


def test_the_warning_names_only_the_bound_that_is_over() -> None:
    text = grant_clamp_warning(LIVE, 2100, 100, 100.0)
    assert "actions: planned 2100" in text
    assert "probes:" not in text and "wall clock:" not in text


def test_other_kinds_never_warn() -> None:
    assert grant_clamp_warning(ApprovalKind.CRAWL, 9999, 99999, 999999.0) == ""


def test_the_refusal_hint_says_the_plan_is_over_the_ceiling() -> None:
    with pytest.raises(ApprovalRequired) as exc:
        require_approval([], project="demo", kind=LIVE, target=URL, actions=2100, probes=42000,
                         wall_clock_s=21057.0)
    text = str(exc.value)
    assert "actions: planned 2100 > ceiling 2000" in text
    assert text.index("planned 2100") < text.index("Grant one with:")


def test_the_refusal_hint_is_silent_when_the_plan_fits() -> None:
    with pytest.raises(ApprovalRequired) as exc:
        require_approval([], project="demo", kind=LIVE, target=URL, actions=7, probes=140,
                         wall_clock_s=163.0)
    assert "ceiling" not in str(exc.value)


def test_approve_says_so_when_the_derived_plan_is_clamped(store: ProjectStore) -> None:
    store.add_case(_case(2100))
    out = runner.invoke(cli_app, [
        "approve", "demo", "--kind", "live_case", "--target", URL, "--scope", "s",
        "--granted-by", "umesh", "--expires", SOON])
    assert out.exit_code == 0, out.output
    assert "actions: planned 2100 > ceiling 2000" in out.output
    assert store.list_approvals()[0].max_actions == MAX_GRANT_ACTIONS


def test_approve_is_silent_about_ceilings_when_the_plan_fits(store: ProjectStore) -> None:
    store.add_case(_case(3))
    out = runner.invoke(cli_app, [
        "approve", "demo", "--kind", "live_case", "--target", URL, "--scope", "s",
        "--granted-by", "umesh", "--expires", SOON])
    assert out.exit_code == 0, out.output
    assert "ceiling" not in out.output


def test_the_standing_help_says_crawl_only() -> None:
    out = runner.invoke(cli_app, ["approve", "--help"])
    flat = " ".join(out.output.replace("│", " ").split())
    assert "crawl only; until revoked (autotester revoke)" in flat, flat


# -- cycle 1: the refusal path never crashes; F2 whole seconds; F3 bool ----------------------

@pytest.mark.parametrize("kind", list(ApprovalKind))
@pytest.mark.parametrize("bad", [(-1, 0, 0.0), (0, 0, float("inf")), (0, 0, float("nan")),
                                 (0, -1, 0.0), (5, 5, -2.5), (1, 1, float("-inf"))])
def test_require_approval_with_malformed_bounds_refuses_cleanly_for_every_kind(
    kind: ApprovalKind, bad: tuple[int, int, float],
) -> None:
    with pytest.raises(ApprovalRequired) as exc:
        require_approval([], project="demo", kind=kind, target=URL, actions=bad[0],
                        probes=bad[1], wall_clock_s=bad[2])
    assert "refusing to start" in str(exc.value)


@pytest.mark.parametrize("flag", [["--wall-clock", "inf"], ["--wall-clock", "nan"],
                                  ["--max-actions", "-1"], ["--wall-clock", "-5"]])
def test_explore_with_malformed_bounds_exits_2_with_the_refusal_not_a_traceback(
    store: ProjectStore, flag: list[str],
) -> None:
    out = runner.invoke(cli_app, ["explore", "demo", *flag])
    assert out.exit_code == 2, out.output
    assert "refusing to start" in out.output
    assert not isinstance(out.exception, ValueError)


def test_the_wall_clock_in_the_warning_is_whole_seconds_and_never_reads_equal() -> None:
    text = grant_clamp_warning(LIVE, 1, 1, 86400.0004)
    assert "planned 86401s > ceiling 86400s" in text
    assert "e+" not in grant_clamp_warning(LIVE, 1, 1, 1234567.0)
    assert "planned 1234567s" in grant_clamp_warning(LIVE, 1, 1, 1234567.0)
    assert "planned inf" in grant_clamp_warning(LIVE, 1, 1, float("inf"))


@pytest.mark.parametrize("bad", [(True, 0, 1.0), (0, False, 1.0)])
def test_a_bool_is_not_a_bound(bad: tuple[bool, bool, float]) -> None:
    with pytest.raises(ValueError, match="non-negative and finite"):
        derive_grant_bounds(LIVE, *bad)


# -- fix/hint-malformed-bounds: a malformed bound is named, never echoed into a command ------

APPROVE_CMD = "uv run autotester approve"


def _refusal(kind: ApprovalKind, actions: int, probes: int, wall: float) -> str:
    with pytest.raises(ApprovalRequired) as exc:
        require_approval([], project="demo", kind=kind, target=URL, actions=actions,
                         probes=probes, wall_clock_s=wall)
    return str(exc.value)


@pytest.mark.parametrize("kind", list(ApprovalKind))
@pytest.mark.parametrize(("bad", "flag", "why"), [
    ((-1, 0, 0.0), "--max-actions", "negative"),
    ((0, -3, 0.0), "--max-probes", "negative"),
    ((0, 0, -2.5), "--wall-clock", "negative"),
    ((0, 0, float("inf")), "--wall-clock", "infinite"),
    ((0, 0, float("nan")), "--wall-clock", "not a number"),
    ((True, 0, 0.0), "--max-actions", "not a number"),
])
def test_a_malformed_bound_is_named_with_its_reason_and_no_approve_command(
    kind: ApprovalKind, bad: tuple[int, int, float], flag: str, why: str,
) -> None:
    text = _refusal(kind, *bad)
    assert "refusing to start" in text
    assert f"{flag} is " in text and why in text
    assert APPROVE_CMD not in text and "Grant one with" not in text
    assert "--standing" not in text


def test_every_malformed_bound_is_named_when_several_are_bad() -> None:
    text = _refusal(ApprovalKind.CRAWL, -1, 5, float("nan"))
    assert "--max-actions is -1" in text and "--wall-clock is nan" in text
    assert "--max-probes" not in text


def test_a_wellformed_request_still_gets_its_approve_command() -> None:
    text = _refusal(ApprovalKind.CRAWL, 7, 140, 163.0)
    assert APPROVE_CMD in text and "--max-actions 7" in text and "--standing" in text
    assert "invalid" not in text


@pytest.mark.parametrize("kind", list(ApprovalKind))
@pytest.mark.parametrize("huge", [(10**5000, 0, 0.0), (0, 10**5000, 0.0), (0, 0, 1e308),
                                  (0, 0, 10**400)])
def test_an_absurdly_large_bound_is_named_and_capped_not_printed_in_full(
    kind: ApprovalKind, huge: tuple[int, int, float],
) -> None:
    text = _refusal(kind, *huge)
    assert len(text) < 700 and "implausibly large" in text
    assert "over 1000000000000" in text and APPROVE_CMD not in text


def test_the_clamp_warning_caps_a_huge_number_instead_of_printing_every_digit() -> None:
    for text in (grant_clamp_warning(LIVE, 10**5000, 1, 1.0),
                 grant_clamp_warning(LIVE, 1, 1, 1e308)):
        assert len(text) < 400 and "over 1000000000000" in text


def test_invalid_bounds_message_is_empty_for_good_bounds_and_names_the_flag_otherwise() -> None:
    assert invalid_bounds_message(0, 0, 0.0) == ""
    assert invalid_bounds_message(2000, 40000, 86400.0) == ""
    assert "--max-probes is -1" in invalid_bounds_message(1, -1, 1.0)


def test_explore_with_a_negative_bound_names_it_and_prints_no_approve_command(
    store: ProjectStore,
) -> None:
    out = runner.invoke(cli_app, ["explore", "demo", "--max-actions", "-1"])
    assert out.exit_code == 2, out.output
    assert "--max-actions is -1" in out.output and APPROVE_CMD not in out.output


# -- F1 (cycle 1): a NARROWER signed approval must not reopen the crash / long-digit path ----

NOW = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)


def _narrow(kind: ApprovalKind) -> RunApproval:
    return RunApproval(
        project="demo", run_kind=kind, target=URL, scope="s", max_actions=150, max_probes=150,
        wall_clock_s=600.0, granted_by="umesh", granted_at="2026-10-28T09:00:00+00:00",
        expires_at="2026-12-01T00:00:00+00:00").sign()


def _narrow_refusal(kind: ApprovalKind, actions: int, probes: int, wall: float) -> str:
    with pytest.raises(ApprovalRequired) as exc:
        require_approval([_narrow(kind)], project="demo", kind=kind, target=URL, actions=actions,
                         probes=probes, wall_clock_s=wall, now=NOW)
    return str(exc.value)


@pytest.mark.parametrize("kind", list(ApprovalKind))
@pytest.mark.parametrize("big", [10**5000, 10**13, 1e13], ids=["10e5000", "10e13", "1e13"])
@pytest.mark.parametrize("slot", [0, 1, 2])
def test_a_narrower_approval_refusal_caps_every_printed_number(
    kind: ApprovalKind, big: float, slot: int,
) -> None:
    text = _narrow_refusal(kind, *[big if i == slot else 0 for i in range(3)])
    assert "narrower than this run" in text and "implausibly large" in text
    assert "over 1000000000000" in text and APPROVE_CMD not in text
    assert not re.search(r"\d{14,}", text), text


@pytest.mark.parametrize("kind", list(ApprovalKind))
def test_a_narrower_approval_refusal_keeps_wellformed_numbers_as_they_were(
    kind: ApprovalKind,
) -> None:
    text = _narrow_refusal(kind, 200, 300, 700.5)
    assert "actions 200 > approved 150" in text and "probes 300 > approved 150" in text
    assert "wall clock 700.5s > approved 600.0s" in text
