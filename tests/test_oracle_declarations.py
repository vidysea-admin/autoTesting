"""g11-oracle-wiring W1 (multi-role-platform.md MP27, MP28): declarations ride on the OracleContext.

The credential-policy and payment oracles used to read `<run_dir>/credential_policy.json` and
`<run_dir>/payment_paths.json` because `OracleContext` had no place for them (T-217 CORE-REQUEST).
Now a runner hands the typed declaration over in `context.declarations`. The file stays as the
fallback for a runner that still writes it (the T-217 tests do), and the context wins when both
exist. Synthetic only (MPI2); no browser, no provider.
"""

from __future__ import annotations

import pytest
from credential_fakes import PREVIOUS_KEY, GatewayApp, PolicyApp
from pydantic import ValidationError

from autotester.schema.credential_policy import (
    POLICY_FILE,
    CredentialPolicy,
    FlowKind,
    PasswordRule,
    PasswordRules,
    PolicyFlow,
)
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.oracle_declarations import OracleDeclarations
from autotester.schema.payment_path import PAYMENT_FILE, PaymentDeclaration, PaymentPath
from autotester.stages.oracle_credential_policy import PolicyNotDeclaredError
from autotester.stages.oracle_credential_policy import run as credential_run
from autotester.stages.oracle_payment import PaymentNotDeclaredError
from autotester.stages.oracle_payment import run as payment_run
from autotester.stages.oracle_registry import run_oracles

RULES = PasswordRules(min_length=10, require_upper=True, require_lower=True, require_digit=True,
                      require_symbol=True, previous_password_key=PREVIOUS_KEY)
ALL = set(RULES.declared())


def _policy() -> CredentialPolicy:
    flow = PolicyFlow(id="reset-pw", kind=FlowKind.RESET, role_id="parent",
                      open_steps=["goto /reset"], password_field="#pw",
                      submit_step="click #save", accepted_marker="#done")
    return CredentialPolicy(rules=RULES, flows=[flow])


def _payments() -> PaymentDeclaration:
    return PaymentDeclaration(paths=[PaymentPath(
        id="plan-pay", role_id="parent", steps=["goto /pricing", "click #choose-plan"],
        gateway_steps=["click #checkout"], gateway_marker="#gateway-form")])


def _ctx(app: object, tmp_path, **declared: object) -> OracleContext:
    return OracleContext(
        project_slug="demo", run_dir=str(tmp_path), scenario_id="decl", role_ids=["parent"],
        platform_ids=["school"], port=app, declarations=OracleDeclarations(**declared))


def test_w1_the_context_defaults_to_no_declarations() -> None:
    ctx = OracleContext(project_slug="demo", run_dir=".", scenario_id="s")
    assert ctx.declarations == OracleDeclarations()
    assert ctx.declarations.credential_policy is None and ctx.declarations.payment_paths is None


def test_w1_the_credential_oracle_takes_its_policy_from_the_context_and_reads_no_file(
        tmp_path) -> None:
    assert not (tmp_path / POLICY_FILE).exists()
    app = PolicyApp(RULES, ALL - {PasswordRule.REQUIRE_DIGIT})
    (finding,) = credential_run(_ctx(app, tmp_path, credential_policy=_policy()))
    assert finding.finding_id == "cred-reset-pw-require_digit"


def test_w1_the_payment_oracle_takes_its_paths_from_the_context_and_reads_no_file(
        tmp_path) -> None:
    assert not (tmp_path / PAYMENT_FILE).exists()
    app = GatewayApp(checkout_leads_to="error")
    (finding,) = payment_run(_ctx(app, tmp_path, payment_paths=_payments()))
    assert finding.finding_id == "pay-plan-pay-gateway" and app.submit_calls == 0


def test_w1_the_registry_runs_an_oracle_from_the_context_alone(tmp_path) -> None:
    """The point of the field: a runner builds the context and nothing is written beforehand."""
    ctx = _ctx(PolicyApp(RULES, ALL), tmp_path, credential_policy=_policy(),
               payment_paths=_payments())
    summary, _ = run_oracles(ctx, [OracleName.CREDENTIAL_POLICY])
    states = {s.oracle: s for s in summary.statuses}
    assert states[OracleName.CREDENTIAL_POLICY].state is OracleState.RAN
    assert list(tmp_path.iterdir()) == []                      # nothing was needed on disk


def test_w1_the_context_wins_over_a_file_in_the_run_directory(tmp_path) -> None:
    other = PaymentDeclaration(paths=[PaymentPath(
        id="other-path", role_id="parent", steps=["goto /x", "click #y"],
        gateway_steps=["click #z"], gateway_marker="#gw")])
    (tmp_path / PAYMENT_FILE).write_text(other.model_dump_json(), encoding="utf-8")
    app = GatewayApp(checkout_leads_to="error")
    (finding,) = payment_run(_ctx(app, tmp_path, payment_paths=_payments()))
    assert "plan-pay" in finding.finding_id or "plan-pay" in finding.title


def test_w1_the_file_is_still_the_fallback_when_the_context_declares_nothing(tmp_path) -> None:
    (tmp_path / POLICY_FILE).write_text(_policy().model_dump_json(), encoding="utf-8")
    app = PolicyApp(RULES, ALL - {PasswordRule.REQUIRE_UPPER})
    (finding,) = credential_run(_ctx(app, tmp_path))
    assert finding.finding_id == "cred-reset-pw-require_upper"


def test_w1_an_oracle_with_neither_source_is_still_errored_not_clean(tmp_path) -> None:
    with pytest.raises(PolicyNotDeclaredError):
        credential_run(_ctx(PolicyApp(RULES, ALL), tmp_path))
    with pytest.raises(PaymentNotDeclaredError):
        payment_run(_ctx(GatewayApp(), tmp_path))


def test_w1_a_declaration_is_validated_when_the_context_is_built() -> None:
    with pytest.raises(ValidationError):
        OracleDeclarations(credential_policy={"rules": {"min_length": "hunter2-canary"}})
    with pytest.raises(ValidationError):
        OracleDeclarations(unknown_oracle={})
    with pytest.raises(ValidationError) as err:
        OracleDeclarations(payment_paths={"paths": [{"id": "canary-secret-value"}]})
    assert "canary-secret-value" not in str(err.value)


def test_w1_declarations_are_never_serialised_with_the_context() -> None:
    """A declaration can hold a {{SECRET:KEY}} placeholder; the context dump must not carry it."""
    dumped = _ctx(None, "run", credential_policy=_policy()).model_dump_json()
    assert "reset-pw" not in dumped and "declarations" not in dumped


def test_w1_a_bad_declaration_dict_on_the_context_does_not_echo_the_input() -> None:
    """A runner builds the context with a declaration dict holding a canary; the error names the
    field but never the offending value (OracleContext carries `hide_input_in_errors`)."""
    with pytest.raises(ValidationError) as err:
        OracleContext(project_slug="p", run_dir="r", scenario_id="s", declarations={
            "payment_paths": {"paths": [{"id": "canary-secret-value"}]}})
    assert "canary-secret-value" not in str(err.value)
