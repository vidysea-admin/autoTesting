"""G11 integration, PW4: a role whose sign-in fails makes its oracles `errored`, never clean.

Bob's `.env` password is wrong, so his sign-in lands on the 401 page and never shows the
`signed_in_target`. Alice signs in fine. Every oracle that reads bob (directly, or through a
whole-run read) must be reported `errored: RoleLoginFailed`, and no finding may be produced from
the half of the run that did work.
"""

from __future__ import annotations

import faulthandler

import pytest
from role_port_app import build_project, start_app
from role_port_run import ALICE, BOB, SIX, context, declare, sign_in, skip_if_no_chromium

from autotester.browser.secrets import SecretStore
from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.multi_role_enums import AssertChannel, Expectation
from autotester.schema.oracle_context import OracleState
from autotester.schema.role_step import RoleStep
from autotester.stages.multi_role_session import RoleSessions
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.role_port_state import RoleLoginFailed, RoleNotSignedIn
from autotester.stages.role_session_port import LiveRolePort


@pytest.fixture(autouse=True)
def _deadline():
    faulthandler.dump_traceback_later(300, exit=True)
    yield
    faulthandler.cancel_dump_traceback_later()


def test_pw4_a_failed_login_errors_every_oracle_and_yields_no_findings(tmp_path) -> None:
    skip_if_no_chromium()
    app, run_dir = start_app(), tmp_path / "run"
    run_dir.mkdir()
    declare(run_dir)
    project = build_project(app, tmp_path, bob_password="not-the-real-pw")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    try:
        with RoleSessions(project, secrets, run_dir, paths_root=tmp_path) as roles:
            port = LiveRolePort(roles, [sign_in(app)])
            with pytest.raises(RoleNotSignedIn):  # not yet attempted: also refused, not clean
                port.perform(RoleStep(id="early", role_id=ALICE, action="goto /home"))
            failures = port.login_all()
            assert list(failures) == [BOB] and "SignedInTargetMissing" in failures[BOB]
            port.perform(RoleStep(id="v", role_id=ALICE, action="goto /home"))  # alice is fine
            summary, findings = run_oracles(context(run_dir, port), SIX)
            with pytest.raises(RoleLoginFailed):
                port.perform(RoleStep(id="b", role_id=BOB, action="goto /home"))
    finally:
        app.stop()
    states = {s.oracle: s for s in summary.statuses}
    assert findings == []
    for oracle in SIX:
        assert states[oracle].state is OracleState.ERRORED, (oracle, states[oracle].state)
        assert states[oracle].reason == "RoleLoginFailed"


def test_an_api_look_sees_only_traffic_after_sign_in_and_reports_a_status_class(tmp_path) -> None:
    skip_if_no_chromium()
    app = start_app()
    try:
        project = build_project(app, tmp_path)
        secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
        with RoleSessions(project, secrets, tmp_path, paths_root=tmp_path) as roles:
            port = LiveRolePort(roles, [sign_in(app)])
            assert port.login_all() == {}
            look = CrossRoleAssertion(id="api", observer_role_id=ALICE, channel=AssertChannel.API,
                                      expectation=Expectation.PRESENT, target="/api/ping",
                                      within_s=1)
            assert port.observe(look).matched is False  # nothing since sign-in
            port.perform(RoleStep(id="d", role_id=ALICE, action="goto /dashboard"))
            seen = port.observe(look)
            assert seen.matched and seen.detail == "api response seen: ok"
    finally:
        app.stop()


def test_a_role_on_a_platform_with_no_sign_in_declared_is_failed_not_clean(tmp_path) -> None:
    skip_if_no_chromium()
    app = start_app()
    try:
        project = build_project(app, tmp_path)
        secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
        with RoleSessions(project, secrets, tmp_path, paths_root=tmp_path) as roles:
            port = LiveRolePort(roles, [])
            assert set(port.login_all()) == {ALICE, BOB}
            with pytest.raises(RoleLoginFailed):
                port.perform(RoleStep(id="d", role_id=ALICE, action="goto /home"))
    finally:
        app.stop()


def test_pw4_a_role_whose_sign_in_was_never_attempted_errors_every_oracle(tmp_path) -> None:
    skip_if_no_chromium()
    app, run_dir = start_app(), tmp_path / "run"
    run_dir.mkdir()
    declare(run_dir)
    project = build_project(app, tmp_path)
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    try:
        with RoleSessions(project, secrets, run_dir, paths_root=tmp_path) as roles:
            port = LiveRolePort(roles, [sign_in(app)], success_selectors=["#ok"])
            port.login(ALICE)  # bob is never attempted: not signed in, not marked failed either
            for path in ("/home", "/dashboard", "/reports", "/orders"):
                port.perform(RoleStep(id="v", role_id=ALICE, action=f"goto {path}"))
            summary, findings = run_oracles(context(run_dir, port), SIX)
    finally:
        app.stop()
    states = {s.oracle: s for s in summary.statuses}
    assert findings == []
    for oracle in SIX:
        assert states[oracle].state is OracleState.ERRORED, (oracle, states[oracle].state)
        assert states[oracle].reason == "RoleLoginFailed", (oracle, states[oracle].reason)
