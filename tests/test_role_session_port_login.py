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
