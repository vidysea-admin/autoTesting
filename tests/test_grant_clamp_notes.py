"""AT-F1/F2 (fix/cli-clamp-and-standing-help): a derived grant clamped at a ceiling SAYS so,
and `derive_grant_bounds` is total (rejects negative / NaN / infinite input, saturates overflow).

Authority: qa/verdicts/auto-size-budget.b.md F1 (a plan over a ceiling looped silently at the
grant step: the hint printed the clamped numbers, `approve` signed them, the run was refused
with the same hint) and F2 (OverflowError above ~1.4e308 wall; negatives unclamped).
"""

from __future__ import annotations

from datetime import date, timedelta
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
    derive_grant_bounds,
    grant_clamp_warning,
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
