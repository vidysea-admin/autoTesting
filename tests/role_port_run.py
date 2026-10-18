"""Shared setup for the live role-port tests: declarations, visits and the oracle context.

`declare` writes the four files the oracles read from the run directory (negative-input forms,
state probes, lint rules, request budget); `RoleSignIn` is built against the fixture app. Test
helper only: no product behaviour lives here.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import pytest
from role_port_app import ACCOUNTS, PortApp

from autotester.schema.enums import Action
from autotester.schema.flowspec import FieldConstraints, Flow, InputField, Step
from autotester.schema.lint_rule import DECLARATION_FILE, LintKind, LintRule, SurfaceChecks
from autotester.schema.multi_role_enums import AssertChannel, OracleName
from autotester.schema.negative_input_form import NegativeInputForm
from autotester.schema.oracle_context import OracleContext
from autotester.schema.request_budget import RequestBudget
from autotester.schema.role_signin import RoleSignIn
from autotester.schema.role_step import RoleStep
from autotester.schema.state_probe import ReaderKind, StateProbe
from autotester.stages.oracle_negative_input import FORMS_FILE
from autotester.stages.oracle_state_after import PROBES_FILE
from autotester.stages.role_port_network import BUDGET_FILE
from autotester.stages.role_session_port import LiveRolePort

ALICE, BOB = ACCOUNTS["alice"], ACCOUNTS["bob"]
SIX = [OracleName.NEGATIVE_INPUT, OracleName.COPY_LINT, OracleName.RESPONSIVE,
       OracleName.API_ERROR, OracleName.REQUEST_BUDGET, OracleName.STATE_AFTER]
OCR_ROW = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\t"
           "conf\ttext\n5\t1\t1\t1\t1\t1\t5\t5\t30\t10\t95\tword\n")


@functools.cache
def skip_if_no_chromium() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


def sign_in(app: PortApp) -> RoleSignIn:
    return RoleSignIn(platform_id="app", login_url=app.url("/login"), user_locator="#u",
                      password_locator="#p", submit_locator="#go", signed_in_target="#signed")


def declare(run_dir: Path) -> None:
    """The oracle inputs: a title field capped at 10, an Add counter, three lint rules, a budget."""
    flow = Flow(id="settings", name="Settings", entry_screen="settings", steps=[
        Step(order=1, action=Action.FILL, target="title", value="Asha")])
    form = NegativeInputForm(
        id="settings", platform_id="app", flow=flow, role_ids=[ALICE, BOB],
        fields=[InputField(name="title", required=True,
                           constraints=FieldConstraints(max_length=10))],
        url_template="/settings", submit_target="#submit", rejection_target="#err",
        valid_values={"title": "hello"})
    (run_dir / FORMS_FILE).write_text(f"[{form.model_dump_json()}]", encoding="utf-8")
    probe = StateProbe(
        id="orders", platform_id="app", kind=ReaderKind.COUNTER, reader_channel=AssertChannel.UI,
        reader_target="#count", reader_url="/orders", expected_delta=1,
        action=RoleStep(id="add", role_id=ALICE, action="click #add"), reader_role_ids=[ALICE, BOB])
    (run_dir / PROBES_FILE).write_text(f"[{probe.model_dump_json()}]", encoding="utf-8")
    rules = [LintRule(id="brand", kind=LintKind.BRAND_TERM, value="Vidysea"),
             LintRule(id="forbid", kind=LintKind.FORBIDDEN_STRING, value="lorem ipsum"),
             LintRule(id="tz", kind=LintKind.DISPLAY_TIMEZONE, value="IST")]
    (run_dir / DECLARATION_FILE).write_text(SurfaceChecks(rules=rules).model_dump_json(),
                                            encoding="utf-8")
    budget = RequestBudget(max_requests_per_screen=20, min_poll_interval_s=0.5)
    (run_dir / BUDGET_FILE).write_text(budget.model_dump_json(), encoding="utf-8")


def visit(port: LiveRolePort, paths: tuple[str, ...]) -> None:
    """Both roles open each path in turn."""
    for role in (ALICE, BOB):
        for n, path in enumerate(paths):
            port.perform(RoleStep(id=f"v{n}", role_id=role, action=f"goto {path}"))


def context(run_dir: Path, port: Any) -> OracleContext:
    return OracleContext(project_slug="g11port", run_dir=str(run_dir), scenario_id="g11",
                         role_ids=[ALICE, BOB], platform_ids=["app"], port=port)
