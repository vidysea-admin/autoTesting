"""T-217 (multi-role-platform.md MP28): the payment oracle reports the path and never charges.

The fixture gateway (`credential_fakes.GatewayApp`) counts calls to its submit endpoint, so "stops
at the gateway" is asserted as `submit_calls == 0`, including when the declaration itself carries a
step that WOULD pay if the oracle kept going. Synthetic only; no provider, no network (MPI2).
"""

from __future__ import annotations

import json

import pytest
from credential_fakes import GatewayApp
from pydantic import ValidationError

from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.payment_path import (
    PAYMENT_FILE,
    CouponState,
    GatewayState,
    PaymentDeclaration,
    PaymentPath,
)
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_payment import (
    REPORT_FILE,
    PaymentNotDeclaredError,
    PaymentUnobservedError,
    check_path,
    payment_findings,
    run,
)
from autotester.stages.oracle_registry import run_oracles


def _path(**over) -> PaymentPath:
    base = {"id": "plan-pay", "role_id": "parent", "steps": ["goto /pricing", "click #choose-plan"],
            "gateway_steps": ["click #checkout"], "gateway_marker": "#gateway-form"}
    return PaymentPath(**{**base, **over})


def _coupon(**over) -> PaymentPath:
    base = {"coupon_steps": ["fill #coupon = {{SECRET:QA_COUPON}}", "click #apply-coupon"],
            "coupon_marker": "#discount"}
    return _path(**{**base, **over})


def _ctx(app: object | None, tmp_path) -> OracleContext:
    return OracleContext(project_slug="demo", run_dir=str(tmp_path), scenario_id="pay",
                         role_ids=["parent"], platform_ids=["school"], port=app)


def _decl(*paths: PaymentPath) -> PaymentDeclaration:
    return PaymentDeclaration(paths=list(paths))


# --- MP28: reaches the gateway page, and stops there -----------------------------------------
def test_mp28_a_path_that_reaches_the_gateway_is_reported_reached_with_no_finding(
        tmp_path) -> None:
    app = GatewayApp()
    report = check_path(_path(), app)
    assert report.gateway is GatewayState.REACHED and report.stopped_at_gateway is True
    assert report.coupon is CouponState.NOT_DECLARED and report.performed_steps == 3
    assert payment_findings(_ctx(GatewayApp(), tmp_path), _decl(_path())) == []
    assert app.submit_calls == 0


def test_mp28_the_gateway_submit_endpoint_records_zero_calls(tmp_path) -> None:
    app = GatewayApp()
    payment_findings(_ctx(app, tmp_path), _decl(_path(), _coupon(id="plan-coupon")))
    assert app.submit_calls == 0
    assert not any("#pay-now" in a for a in app.performed)


def test_mp28_it_stops_even_when_the_declaration_names_a_step_that_would_pay(tmp_path) -> None:
    """The declared gateway steps include the charge click; the walk must not reach it."""
    app = GatewayApp()
    path = _path(gateway_steps=["click #checkout", "click #pay-now"])
    report = check_path(path, app)
    assert report.gateway is GatewayState.REACHED and report.stopped_at_gateway is True
    assert app.submit_calls == 0 and "click #pay-now" not in app.performed
    assert report.performed_steps == 3


def test_mp28_it_stops_when_an_earlier_step_already_lands_on_the_gateway() -> None:
    app = GatewayApp()
    path = _path(steps=["goto /pricing", "click #checkout", "click #pay-now"],
                 gateway_steps=["click #checkout"])
    report = check_path(path, app)
    assert report.gateway is GatewayState.REACHED and app.submit_calls == 0
    assert report.performed_steps == 2


def test_mp28_a_path_that_never_reaches_the_gateway_is_a_finding(tmp_path) -> None:
    app = GatewayApp(checkout_leads_to="error")
    (finding,) = payment_findings(_ctx(app, tmp_path), _decl(_path()))
    assert finding.finding_class is FindingClass.PAYMENT_PATH and finding.role == "parent"
    assert finding.finding_id == "pay-plan-pay-gateway" and finding.platform_id == "school"
    assert priority_for(finding.finding_class).value == "P1" and finding.oracle is None
    assert finding.steps == ["goto /pricing", "click #choose-plan", "click #checkout"]
    assert app.submit_calls == 0


def test_mp28_a_step_that_raises_ends_the_path_as_not_reached_without_the_message(
        tmp_path) -> None:
    app = GatewayApp(fail_on="#choose-plan")
    (finding,) = payment_findings(_ctx(app, tmp_path), _decl(_path()))
    assert "boom" not in finding.model_dump_json() and finding.title.endswith("gateway page")
    assert "click #checkout" not in app.performed


# --- the coupon path where declared -----------------------------------------------------------
def test_mp28_a_coupon_that_applies_is_reported_applied(tmp_path) -> None:
    app = GatewayApp()
    report = check_path(_coupon(), app)
    assert report.coupon is CouponState.APPLIED and report.gateway is GatewayState.REACHED
    assert app.submit_calls == 0


def test_mp28_a_coupon_that_does_not_apply_is_a_finding_and_the_gateway_is_still_checked(
        tmp_path) -> None:
    app = GatewayApp(coupon_works=False)
    (finding,) = payment_findings(_ctx(app, tmp_path), _decl(_coupon()))
    assert finding.finding_id == "pay-plan-pay-coupon" and "coupon" in finding.title
    assert check_path(_coupon(), GatewayApp(coupon_works=False)).gateway is GatewayState.REACHED


def test_mp28_a_coupon_the_walk_never_reached_is_not_called_unapplied() -> None:
    app = GatewayApp()
    path = _coupon(steps=["goto /pricing", "click #checkout"])
    report = check_path(path, app)
    assert report.gateway is GatewayState.REACHED and report.coupon is CouponState.NOT_REACHED


# --- provider test mode is the only way past the gateway --------------------------------------
def test_mp28_steps_past_the_gateway_are_refused_outside_provider_test_mode() -> None:
    with pytest.raises(ValidationError):
        _path(test_mode_steps=["click #pay-now"])
    with pytest.raises(ValidationError):
        _coupon(coupon_marker=None)
    with pytest.raises(ValidationError):
        _path(gateway_marker="owner@example.test")


def test_mp28_in_declared_test_mode_the_sandbox_steps_run_after_the_gateway(tmp_path) -> None:
    app = GatewayApp()
    path = _path(provider_test_mode=True, test_mode_steps=["click #pay-now"])
    report = check_path(path, app)
    assert report.test_mode_steps_run == 1 and app.submit_calls == 1
    assert app.performed[-1] == "click #pay-now"


def test_mp28_test_mode_steps_do_not_run_when_the_gateway_was_not_reached() -> None:
    app = GatewayApp(checkout_leads_to="error")
    path = _path(provider_test_mode=True, test_mode_steps=["click #pay-now"])
    assert check_path(path, app).test_mode_steps_run == 0 and app.submit_calls == 0


# --- honesty ----------------------------------------------------------------------------------
def test_mp28_a_page_that_cannot_be_looked_at_is_unobserved_not_not_reached(tmp_path) -> None:
    app = GatewayApp(observe_error=True)
    assert check_path(_path(), app).gateway is GatewayState.UNOBSERVED
    with pytest.raises(PaymentUnobservedError):
        payment_findings(_ctx(GatewayApp(observe_error=True), tmp_path), _decl(_path()))


def test_mp28_proven_findings_are_kept_when_another_path_was_unobserved(tmp_path) -> None:
    class Flaky(GatewayApp):
        def observe(self, assertion):
            if assertion.observer_role_id == "teacher":
                raise ConnectionError("lost")
            return super().observe(assertion)

    broken = _path(id="parent-pay")
    blind = _path(id="teacher-pay", role_id="teacher")
    app = Flaky(checkout_leads_to="error")
    findings = payment_findings(_ctx(app, tmp_path), _decl(broken, blind))
    assert [f.finding_id for f in findings] == ["pay-parent-pay-gateway"]


def test_mp28_no_session_port_is_an_error_and_no_declared_path_is_not(tmp_path) -> None:
    with pytest.raises(PaymentUnobservedError):
        payment_findings(_ctx(None, tmp_path), _decl(_path()))
    assert payment_findings(_ctx(None, tmp_path), _decl()) == []


def test_mp28_the_declaration_is_closed_and_bounded() -> None:
    with pytest.raises(ValidationError):
        PaymentPath(id="x", role_id="parent", gateway_steps=["click #a"], gateway_marker="#g",
                    surprise=True)
    with pytest.raises(ValidationError):
        _path(steps=["dance #x"])
    with pytest.raises(ValidationError):
        _path(gateway_steps=[])
    with pytest.raises(ValidationError):
        _decl(_path(), _path())                                 # duplicate id
    with pytest.raises(ValidationError):
        PaymentDeclaration(paths=[_path(id=f"p{i}") for i in range(13)])


# --- wiring -----------------------------------------------------------------------------------
def test_mp28_run_reads_the_declaration_and_writes_a_states_only_report(tmp_path) -> None:
    (tmp_path / PAYMENT_FILE).write_text(_decl(_coupon()).model_dump_json(), encoding="utf-8")
    assert run(_ctx(GatewayApp(), tmp_path)) == []
    report = json.loads((tmp_path / REPORT_FILE).read_text(encoding="utf-8"))
    assert report == [{"path_id": "plan-pay", "role_id": "parent", "gateway": "reached",
                       "coupon": "applied", "performed_steps": 5, "stopped_at_gateway": True,
                       "test_mode_steps_run": 0}]
    text = (tmp_path / REPORT_FILE).read_text(encoding="utf-8")
    assert "QA_COUPON" not in text and "#gateway-form" not in text


def test_mp28_without_a_declaration_the_oracle_is_errored_in_the_registry(tmp_path) -> None:
    ctx = _ctx(GatewayApp(), tmp_path)
    with pytest.raises(PaymentNotDeclaredError):
        run(ctx)
    summary, _ = run_oracles(ctx, [OracleName.PAYMENT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.PAYMENT)
    assert status.state is OracleState.ERRORED and status.reason == "PaymentNotDeclaredError"


def test_mp28_the_registry_counts_the_findings_of_a_declared_path(tmp_path) -> None:
    (tmp_path / PAYMENT_FILE).write_text(_decl(_path()).model_dump_json(), encoding="utf-8")
    ctx = _ctx(GatewayApp(checkout_leads_to="error"), tmp_path)
    summary, findings = run_oracles(ctx, [OracleName.PAYMENT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.PAYMENT)
    assert status.state is OracleState.RAN and status.finding_count == 1 == len(findings)


def test_mp28_an_invalid_declaration_is_not_declared_and_leaks_no_text(tmp_path) -> None:
    (tmp_path / PAYMENT_FILE).write_text('{"paths": [{"id": "canary-secret-value"}]}',
                                         encoding="utf-8")
    with pytest.raises(PaymentNotDeclaredError) as err:
        run(_ctx(GatewayApp(), tmp_path))
    assert "canary-secret-value" not in str(err.value) and err.value.__cause__ is None
