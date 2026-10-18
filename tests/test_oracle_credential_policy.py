"""T-217 (multi-role-platform.md MP27): the credential-policy oracle, password half.

The matrix is the A1 Verify line: every declared password rule x create and reset flows, with the
fixture form enforcing every rule but one, none, or all. A rule is reported by NAME; no probe
value or key value may appear in a finding. The mail half is `test_oracle_credential_mail.py`.
Synthetic only (MPI2).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from credential_fakes import PREVIOUS_KEY, PREVIOUS_VALUE, PolicyApp, meets
from pydantic import ValidationError

from autotester.schema.credential_policy import (
    POLICY_FILE,
    CredentialPolicy,
    FlowKind,
    PasswordRule,
    PasswordRules,
    PolicyFlow,
)
from autotester.schema.mailbox_ref import MailboxRef
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.role_step import RoleStep
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_credential_policy import (
    CredentialProbeError,
    PolicyNotDeclaredError,
    credential_findings,
    probe_value,
    run,
)
from autotester.stages.oracle_registry import run_oracles

RULES = PasswordRules(min_length=10, require_upper=True, require_lower=True, require_digit=True,
                      require_symbol=True, previous_password_key=PREVIOUS_KEY)
ALL = set(RULES.declared())
SINCE = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)
REF = MailboxRef(host_key="QA_IMAP_HOST", user_key="QA_IMAP_USER", password_key="QA_IMAP_PASS")
DECLARED = {"QA_IMAP_HOST", "QA_IMAP_USER", "QA_IMAP_PASS"}


def _flow(kind: FlowKind = FlowKind.RESET, fid: str = "reset-pw", **over) -> PolicyFlow:
    base = {"id": fid, "kind": kind, "role_id": "parent", "open_steps": ["goto /reset"],
            "password_field": "#pw", "submit_step": "click #save", "accepted_marker": "#done"}
    return PolicyFlow(**{**base, **over})


def _ctx(app: object | None, tmp_path, *outcomes) -> OracleContext:
    return OracleContext(
        project_slug="demo", run_dir=str(tmp_path), scenario_id="creds", role_ids=["parent"],
        platform_ids=["school"], port=app, assertion_outcomes=list(outcomes),
        steps=[RoleStep(id="open", role_id="parent", action="goto /reset")])


def _found(enforced: set[PasswordRule], kind: FlowKind, tmp_path) -> tuple[set[str], PolicyApp]:
    app = PolicyApp(RULES, enforced)
    policy = CredentialPolicy(rules=RULES, flows=[_flow(kind)])
    findings = credential_findings(_ctx(app, tmp_path), policy)
    return {f.finding_id.removeprefix("cred-reset-pw-").removeprefix("cred-create-pw-")
            for f in findings}, app


# --- MP27: the matrix over every declared rule on create and reset --------------------------
@pytest.mark.parametrize("kind", list(FlowKind))
@pytest.mark.parametrize("unenforced", sorted(ALL, key=lambda r: r.value))
def test_mp27_a_rule_the_product_does_not_enforce_is_reported_by_its_name(kind, unenforced,
                                                                         tmp_path) -> None:
    found, _ = _found(ALL - {unenforced}, kind, tmp_path)
    assert found == {unenforced.value}


@pytest.mark.parametrize("kind", list(FlowKind))
def test_mp27_a_product_enforcing_every_rule_has_no_finding(kind, tmp_path) -> None:
    assert _found(ALL, kind, tmp_path)[0] == set()


@pytest.mark.parametrize("kind", list(FlowKind))
def test_mp27_a_product_enforcing_nothing_is_reported_for_every_declared_rule(kind,
                                                                             tmp_path) -> None:
    assert _found(set(), kind, tmp_path)[0] == {r.value for r in ALL}


def test_mp27_each_probe_breaks_exactly_the_one_rule_it_names() -> None:
    for rule in sorted(ALL - {PasswordRule.NO_REUSE}, key=lambda r: r.value):
        value = probe_value(RULES, rule)
        assert not meets(rule, RULES, value, PREVIOUS_VALUE), rule
        for other in ALL - {rule, PasswordRule.NO_REUSE}:
            assert meets(other, RULES, value, PREVIOUS_VALUE), (rule, other)


def test_mp27_the_reuse_probe_carries_a_key_placeholder_never_the_previous_value() -> None:
    assert probe_value(RULES, PasswordRule.NO_REUSE) == "{{SECRET:" + PREVIOUS_KEY + "}}"


def test_mp27_a_finding_records_the_rule_never_the_value(tmp_path) -> None:
    policy = CredentialPolicy(rules=RULES, flows=[_flow(FlowKind.CREATE, "create-pw")])
    app = PolicyApp(RULES, set())
    findings = credential_findings(_ctx(app, tmp_path), policy)
    dumped = "".join(f.model_dump_json() for f in findings)
    assert app.typed, "the probes did type candidate passwords"
    for value in app.typed:
        assert value not in dumped
    assert PREVIOUS_VALUE not in dumped and all("[probe:" in " ".join(f.steps) for f in findings)
    words = {t for f in findings for t in f.title.replace(":", " ").split()}
    assert {r.value for r in ALL} <= words
    assert all(f.finding_class is FindingClass.WEAK_CREDENTIAL_POLICY and f.oracle is None
               and f.role == "parent" and f.platform_id == "school" for f in findings)
    assert priority_for(FindingClass.WEAK_CREDENTIAL_POLICY).value == "P1"


def test_mp27_an_accepted_weak_password_is_undone_by_the_declared_restore_steps(tmp_path) -> None:
    app = PolicyApp(RULES, ALL - {PasswordRule.MIN_LENGTH})
    flow = _flow(restore_steps=["click #restore"])
    credential_findings(_ctx(app, tmp_path), CredentialPolicy(rules=RULES, flows=[flow]))
    assert app.performed.count("click #restore") == 1       # only the accepted probe is restored
    rejected = PolicyApp(RULES, ALL)
    credential_findings(_ctx(rejected, tmp_path), CredentialPolicy(rules=RULES, flows=[flow]))
    assert "click #restore" not in rejected.performed


def test_mp27_a_failed_restore_is_said_in_the_title_and_the_finding_is_kept(tmp_path) -> None:
    app = PolicyApp(RULES, ALL - {PasswordRule.MIN_LENGTH}, fail_on="#restore")
    flow = _flow(restore_steps=["click #restore"])
    (finding,) = credential_findings(_ctx(app, tmp_path),
                                     CredentialPolicy(rules=RULES, flows=[flow]))
    assert "min_length" in finding.title and "not restored" in finding.title


# --- honesty: a form that could not be looked at is never a clean pass ----------------------
def test_mp27_a_form_that_cannot_be_reached_is_an_error_not_a_clean_pass(tmp_path) -> None:
    app = PolicyApp(RULES, ALL, fail_on="goto /reset")
    with pytest.raises(CredentialProbeError):
        credential_findings(_ctx(app, tmp_path), CredentialPolicy(rules=RULES, flows=[_flow()]))
    assert app.performed == ["goto /reset"], "an unreachable form is tried once, not per rule"


def test_mp27_a_lost_observation_is_an_error_not_a_clean_pass(tmp_path) -> None:
    app = PolicyApp(RULES, set(), observe_error=True)
    with pytest.raises(CredentialProbeError):
        credential_findings(_ctx(app, tmp_path), CredentialPolicy(rules=RULES, flows=[_flow()]))


def test_mp27_a_flow_without_a_session_port_is_an_error(tmp_path) -> None:
    with pytest.raises(CredentialProbeError):
        credential_findings(_ctx(None, tmp_path), CredentialPolicy(rules=RULES, flows=[_flow()]))


def test_mp27_nothing_to_probe_is_an_error_not_a_clean_pass(tmp_path) -> None:
    with pytest.raises(CredentialProbeError):
        credential_findings(_ctx(None, tmp_path), CredentialPolicy(rules=RULES, flows=[]))


# --- the declaration is bounded, closed and holds keys only ---------------------------------
def test_mp27_the_declaration_is_closed_bounded_and_value_free() -> None:
    with pytest.raises(ValidationError):
        PasswordRules(min_length=10, surprise=1)
    with pytest.raises(ValidationError):
        PasswordRules(previous_password_key="not a key")
    with pytest.raises(ValidationError):
        PasswordRules(min_length=4, require_upper=True, require_lower=True, require_digit=True,
                      require_symbol=True)
    flows = [_flow(fid=f"flow-{i}") for i in range(8)]
    with pytest.raises(ValidationError):
        CredentialPolicy(rules=RULES, flows=flows)                 # 8 flows x 6 rules = 48 > 40
    with pytest.raises(ValidationError):
        CredentialPolicy(rules=RULES, flows=[_flow(), _flow()])    # duplicate flow id
    with pytest.raises(ValidationError):
        _flow(open_steps=["dance #x"])


# --- wiring: the registry loads the module, the declaration is a file in the run dir -------
def test_mp27_run_reads_the_declaration_from_the_run_directory(tmp_path) -> None:
    (tmp_path / POLICY_FILE).write_text(
        CredentialPolicy(rules=RULES, flows=[_flow()]).model_dump_json(), encoding="utf-8")
    app = PolicyApp(RULES, ALL - {PasswordRule.REQUIRE_DIGIT})
    (finding,) = run(_ctx(app, tmp_path))
    assert finding.finding_id == "cred-reset-pw-require_digit"


def test_mp27_without_a_declaration_the_oracle_is_errored_in_the_registry(tmp_path) -> None:
    ctx = _ctx(PolicyApp(RULES, ALL), tmp_path)
    with pytest.raises(PolicyNotDeclaredError):
        run(ctx)
    summary, findings = run_oracles(ctx, [OracleName.CREDENTIAL_POLICY])
    status = next(s for s in summary.statuses if s.oracle is OracleName.CREDENTIAL_POLICY)
    assert status.state is OracleState.ERRORED and status.reason == "PolicyNotDeclaredError"
    assert findings == []


def test_mp27_an_invalid_declaration_is_not_declared_and_leaks_no_text(tmp_path) -> None:
    (tmp_path / POLICY_FILE).write_text('{"rules": {"min_length": "hunter2-canary"}}',
                                        encoding="utf-8")
    with pytest.raises(PolicyNotDeclaredError) as err:
        run(_ctx(PolicyApp(RULES, ALL), tmp_path))
    assert "hunter2-canary" not in str(err.value) and err.value.__cause__ is None


def test_mp27_the_registry_counts_the_findings_of_a_declared_policy(tmp_path) -> None:
    (tmp_path / POLICY_FILE).write_text(
        CredentialPolicy(rules=RULES, flows=[_flow()]).model_dump_json(), encoding="utf-8")
    ctx = _ctx(PolicyApp(RULES, set()), tmp_path)
    summary, findings = run_oracles(ctx, [OracleName.CREDENTIAL_POLICY])
    status = next(s for s in summary.statuses if s.oracle is OracleName.CREDENTIAL_POLICY)
    assert status.state is OracleState.RAN and status.finding_count == len(ALL) == len(findings)
