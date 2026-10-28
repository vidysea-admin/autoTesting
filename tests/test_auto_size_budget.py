"""D-112 item 2: the human never types `wall_clock_s` / `max_actions`.

One derivation (`core.consent.derive_grant_bounds`, fed by `run_gates.derive_live_case_grant`
from the planned cases) is used by the refusal hint, `autotester approve` with the flags
omitted, and the UI grant form's pre-fill. Derived values stay inside the hard grant ceilings
and cover the gate's own request, so a derived grant is never refused by the run it was sized for.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from autotester.cli import app as cli_app
from autotester.core.consent import ApprovalRequired, require_approval, validate_grant_bounds
from autotester.schema.approval import (
    GRANT_SAFETY_MARGIN,
    MAX_GRANT_ACTIONS,
    MAX_GRANT_PROBES,
    MAX_GRANT_WALL_CLOCK_S,
    PROBES_PER_ACTION,
    GrantBounds,
    derive_grant_bounds,
)
from autotester.schema.case import Case
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind, CaseStatus
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project
from autotester.stages.run_budget import JUDGE_ALLOWANCE_PER_CASE_S, WALL_CLOCK_PER_ACTION_S
from autotester.stages.run_gates import (
    LaunchRefused,
    derive_live_case_grant,
    require_live_case_approval,
)
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app as ui_app

URL = "https://demo.test/login"
SOON = (date.today() + timedelta(days=5)).isoformat()   # inside the 30-day grant cap
runner = CliRunner()


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url=URL, allowed_domains=["demo.test"]))
    return s


def _case(n_steps: int, *, title: str = "t") -> Case:
    steps = [Step(order=i, action=Action.CLICK, target=f"#x{i}",
                  expected=ExpectedState(visible_text=["ok"])) for i in range(n_steps)]
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title=title, steps=steps)


def _ceil(x: float) -> int:
    return int(-(-x // 1))


# -- (1) the derivation function ---------------------------------------------------------------

def test_a_known_case_set_derives_actions_probes_and_time_with_the_margin() -> None:
    """5 steps in 2 cases: 5 actions, 5x8s per-step allowance, 45s judge per case in the gate's
    own request, then the safety margin and whole-second rounding."""
    request_wall = 5 * WALL_CLOCK_PER_ACTION_S + 2 * JUDGE_ALLOWANCE_PER_CASE_S   # 130.0
    got = derive_live_case_grant([_case(3, title="a"), _case(2, title="b")])
    assert isinstance(got, GrantBounds)
    assert got.actions == _ceil(5 * GRANT_SAFETY_MARGIN) == 7
    assert got.wall_clock_s == float(_ceil(request_wall * GRANT_SAFETY_MARGIN)) == 163.0
    assert got.probes == max(15, got.actions * PROBES_PER_ACTION) == 140


def test_a_step_less_case_still_costs_one_action() -> None:
    assert derive_live_case_grant([_case(0)]).actions == _ceil(1 * GRANT_SAFETY_MARGIN)


def test_the_derived_bounds_never_fall_below_what_the_gate_will_request() -> None:
    from autotester.stages.execute import probe_request
    from autotester.stages.run_budget import action_cost, wall_clock_request_s

    cases = [_case(n, title=f"c{n}") for n in (1, 4, 9)]
    got = derive_live_case_grant(cases)
    assert got.actions >= sum(action_cost(c) for c in cases)
    assert got.wall_clock_s >= wall_clock_request_s(cases)
    assert got.probes >= probe_request(cases)


def test_derivation_is_clamped_to_the_hard_grant_ceilings() -> None:
    got = derive_grant_bounds(ApprovalKind.LIVE_CASE, 1900, 5, 80000.0)
    assert got.actions == MAX_GRANT_ACTIONS
    assert got.wall_clock_s == MAX_GRANT_WALL_CLOCK_S
    assert got.probes <= MAX_GRANT_PROBES
    # and the result is accepted by the one grant cap, exactly as typed values are
    validate_grant_bounds(got.actions, got.wall_clock_s, None, kind=ApprovalKind.CRAWL)


def test_a_huge_case_set_clamps_the_cli_and_the_function_alike() -> None:
    got = derive_live_case_grant([_case(1900)])
    assert got.actions == MAX_GRANT_ACTIONS
    validate_grant_bounds(got.actions, got.wall_clock_s, None, kind=ApprovalKind.CRAWL)


def test_zero_means_not_asked_and_other_kinds_are_not_widened() -> None:
    assert derive_grant_bounds(ApprovalKind.LIVE_CASE, 0, 0, 0.0) == GrantBounds(0, 0, 0.0)
    assert derive_grant_bounds(ApprovalKind.CRAWL, 150, 25, 900.0) == GrantBounds(150, 25, 900.0)
    assert derive_grant_bounds(ApprovalKind.ADVERSARIAL, 7, 3, 60.0) == GrantBounds(7, 3, 60.0)


def test_a_non_finite_wall_clock_passes_through_untouched() -> None:
    got = derive_grant_bounds(ApprovalKind.LIVE_CASE, 4, 4, float("inf"))
    assert got.wall_clock_s == float("inf")


# -- (2) the refusal hint uses it --------------------------------------------------------------

def test_the_refusal_hint_prints_the_derived_numbers_and_they_cover_the_run(
    store: ProjectStore,
) -> None:
    cases = [_case(3, title="a"), _case(2, title="b")]
    want = derive_live_case_grant(cases)
    with pytest.raises(LaunchRefused) as exc:
        require_live_case_approval(store.load_project(), store, cases)
    text = exc.value.reason
    assert f"--max-actions {want.actions} " in text + " "
    assert f"--max-probes {want.probes} " in text + " "
    assert f"--wall-clock {want.wall_clock_s} " in text + " "


def test_other_kinds_keep_printing_their_asked_bounds_in_the_hint() -> None:
    with pytest.raises(ApprovalRequired) as exc:
        require_approval([], project="demo", kind=ApprovalKind.CRAWL, target=URL,
                         actions=150, wall_clock_s=900.0)
    assert "--max-actions 150 " in str(exc.value) and "--wall-clock 900.0" in str(exc.value)


# -- (3) `autotester approve` with the flags omitted ------------------------------------------

def _approve(*extra: str) -> object:
    return runner.invoke(cli_app, [
        "approve", "demo", "--kind", "live_case", "--target", URL, "--scope", "s",
        "--granted-by", "umesh", "--expires", SOON, *extra])


def test_omitted_flags_derive_print_and_sign_the_numbers(store: ProjectStore) -> None:
    for case in (_case(3, title="a"), _case(2, title="b")):
        store.add_case(case)
    want = derive_live_case_grant(store.list_cases())
    out = _approve()
    assert out.exit_code == 0, out.output
    row = store.list_approvals()[0]
    assert (row.max_actions, row.max_probes, row.wall_clock_s) == (
        want.actions, want.probes, want.wall_clock_s)
    assert f"{want.actions} actions" in out.output and f"{want.wall_clock_s:g}s" in out.output
    assert "derived" in out.output
    assert row.is_signed_and_verified


def test_the_derived_grant_actually_lets_the_run_through_the_gate(store: ProjectStore) -> None:
    cases = [_case(3, title="a"), _case(2, title="b")]
    for case in cases:
        store.add_case(case)
    assert _approve().exit_code == 0
    got = require_live_case_approval(store.load_project(), store, store.list_cases())
    assert got.run_kind is ApprovalKind.LIVE_CASE


def test_a_typed_flag_overrides_only_itself(store: ProjectStore) -> None:
    store.add_case(_case(3))
    want = derive_live_case_grant(store.list_cases())
    out = _approve("--max-actions", "50")
    assert out.exit_code == 0, out.output
    row = store.list_approvals()[0]
    assert row.max_actions == 50
    assert (row.max_probes, row.wall_clock_s) == (want.probes, want.wall_clock_s)


def test_retired_cases_are_not_sized_and_no_cases_falls_back_to_the_old_defaults(
    store: ProjectStore,
) -> None:
    retired = _case(40, title="old").model_copy(update={"status": CaseStatus.RETIRED})
    store.add_case(retired)
    out = _approve()
    assert out.exit_code == 0, out.output
    row = store.list_approvals()[0]
    assert (row.max_actions, row.max_probes, row.wall_clock_s) == (200, 200, 600.0)
    assert "no planned cases" in out.output


def test_non_live_case_kinds_keep_the_old_defaults(store: ProjectStore) -> None:
    store.add_case(_case(3))
    out = runner.invoke(cli_app, [
        "approve", "demo", "--kind", "crawl", "--target", URL, "--scope", "s",
        "--granted-by", "umesh", "--expires", SOON])
    assert out.exit_code == 0, out.output
    row = store.list_approvals()[0]
    assert (row.max_actions, row.max_probes, row.wall_clock_s) == (200, 200, 600.0)


def test_an_explicit_over_ceiling_flag_is_still_refused(store: ProjectStore) -> None:
    store.add_case(_case(3))
    assert _approve("--max-actions", "2001").exit_code == 1
    assert store.list_approvals() == []


# -- (4) the UI form pre-fills them ------------------------------------------------------------

def test_the_grant_form_prefills_the_derived_live_case_bounds_and_stays_editable(
    store: ProjectStore,
) -> None:
    for case in (_case(3, title="a"), _case(2, title="b")):
        store.add_case(case)
    want = derive_live_case_grant(store.list_cases())
    page = TestClient(ui_app).get("/projects/demo/env").text
    assert f"data-live-actions='{want.actions}'" in page
    assert f"data-live-probes='{want.probes}'" in page
    assert f"data-live-wall='{want.wall_clock_s:g}'" in page
    assert "derived from 2 planned case" in page
    # editable: still plain number inputs, none read-only
    assert "id='ca-actions' type='number'" in page and "readonly" not in page.split(
        "id='ca-actions'")[1].split(">")[0]


def test_without_planned_cases_the_form_keeps_its_old_defaults(store: ProjectStore) -> None:
    page = TestClient(ui_app).get("/projects/demo/env").text
    assert "data-live-actions" not in page
    assert "value='200'" in page and "value='600'" in page
