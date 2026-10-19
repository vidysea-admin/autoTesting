"""Shared setup for the live-port wiring tests (g11-oracle-wiring): the fixture app, a fake IMAP
server, a project with one mailbox account, and a `LiveRolePort` over real role sessions.

`wired_port` is module-scoped (one Chromium per test module); `probed_port` runs the two authz
oracles once against it. `tests/conftest.py` registers both fixtures. Synthetic data only (MPI2)."""

from __future__ import annotations

import contextlib
import faulthandler
import imaplib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from imap_fake import PASSWORD, FakeImap, make_mail
from role_port_app import HOST, PortApp, build_project, start_app
from role_port_run import ALICE, BOB, sign_in, skip_if_no_chromium

from autotester.browser.secrets import SecretStore
from autotester.schema.approval import RunApproval
from autotester.schema.authz_probe import (
    AuthzPlan,
    PrivilegeProbe,
    RoleAssignControl,
    TenantProbe,
)
from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.cross_role_scenario import CrossRoleScenario
from autotester.schema.enums import ApprovalKind, WritePolicy
from autotester.schema.mailbox_ref import MailboxRef
from autotester.schema.multi_role_enums import (
    AssertChannel,
    Expectation,
    OracleName,
)
from autotester.schema.oracle_context import OracleContext
from autotester.schema.project import Project, SecretRef
from autotester.schema.role_control import ControlBinding
from autotester.schema.role_step import RoleStep
from autotester.stages.cross_role_runner import run_scenario
from autotester.stages.multi_role_session import RoleSessions
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.role_session_port import LiveRolePort
from autotester.store.filestore import write_json
from autotester.store.project_store import ProjectStore

SLUG = "g11port"
ALICE_MAIL = "role.a@example.test"
CONTROLS = [
    ControlBinding(control_id="make-admin", assign_locator="#make-admin",
                   accepted_target="#now-admin", revert_locator="#undo-admin",
                   reverted_target="#now-user"),
    ControlBinding(control_id="locked", assign_locator="#make-admin",
                   accepted_target="#now-admin", revert_locator="#undo-admin",
                   reverted_target="#now-user"),
]
PLAN = AuthzPlan(
    platform_id="app",
    tenant_probes=[TenantProbe(id="rows", viewer_role_id=ALICE, owner_role_id=BOB,
                               list_url="/api/rows", detail_url="/api/rows/{id}")],
    privilege_probes=[PrivilegeProbe(
        id="admin", higher_role_id=BOB, lower_role_id=ALICE,
        read_urls=["/api/admin/users", "/api/admin/audit"],
        controls=[RoleAssignControl(id="make-admin", url="/assign"),
                  RoleAssignControl(id="locked", url="/assign-locked")])])
PLANNED = 11            # tenant: 1 viewer + 1 owner + 3 swaps; privilege: 2 reads + 2 controls x 2
AUTHZ = [OracleName.TENANT, OracleName.PRIVILEGE]


@pytest.fixture(scope="module")
def live_deadline():
    faulthandler.dump_traceback_later(420, exit=True)
    yield
    faulthandler.cancel_dump_traceback_later()


@dataclass
class Wired:
    app: PortApp
    imap: FakeImap
    roles: RoleSessions
    port: LiveRolePort
    base: Path
    project: Project

    def store(self, slug: str = SLUG, *, write_policy: WritePolicy = WritePolicy.ALLOW_WRITES,
              ) -> ProjectStore:
        """The same project saved under `slug` (so each gate test has its own approvals)."""
        store = ProjectStore(slug)
        store.save_project(self.project.model_copy(
            update={"slug": slug, "write_policy": write_policy}))
        return store

    def grant(self, store: ProjectStore, probes: int) -> None:
        store.add_approval(RunApproval(
            project=store.paths.slug, run_kind=ApprovalKind.ADVERSARIAL, target=self.app.url("/"),
            scope="bounded authorisation probes on the fixture app", max_actions=0,
            max_probes=probes, wall_clock_s=600.0, production=False, granted_by="umesh",
            granted_at="2026-10-10", expires_at="2026-12-01").sign())

    def run_dir(self, name: str, plan: AuthzPlan = PLAN) -> Path:
        run_dir = self.base / name
        run_dir.mkdir()
        write_json(run_dir / "authz_plan.json", plan)
        return run_dir

    def context(self, slug: str, run_dir: Path, port: Any = None) -> OracleContext:
        return OracleContext(project_slug=slug, run_dir=str(run_dir), scenario_id="authz",
                             role_ids=[ALICE, BOB], platform_ids=["app"], port=port or self.port)

    def tree_text(self) -> str:
        """Everything the run wrote, except browser profiles and the `.env` that holds values."""
        skip = {"profiles", ".env"}
        return "\n".join(p.read_bytes().decode("utf-8", "replace")
                         for p in self.base.rglob("*")
                         if p.is_file() and not skip & set(p.relative_to(self.base).parts))


def _plain_imap(host: str, port: int, timeout: float) -> imaplib.IMAP4:
    return imaplib.IMAP4(host, port, timeout=timeout)


@pytest.fixture(scope="module")
def wired_port(tmp_path_factory, live_deadline):
    skip_if_no_chromium()
    base = tmp_path_factory.mktemp("g11wire")
    mails = [make_mail(1, subject="Welcome to the school portal", body="hi", to=ALICE_MAIL)]
    with contextlib.ExitStack() as stack, pytest.MonkeyPatch.context() as patch:
        imap = stack.enter_context(FakeImap(mails=mails))
        app = start_app()
        stack.callback(app.stop)
        project = build_project(app, base)
        keys = ("QA_IMAP_HOST", "QA_IMAP_USER", "QA_IMAP_PASS")
        with (base / ".env").open("a", encoding="utf-8") as env:
            env.write(f"QA_IMAP_HOST={imap.address}\nQA_IMAP_USER=qa-mailbox-user\n"
                      f"QA_IMAP_PASS={PASSWORD}\n")
        ref = MailboxRef(host_key=keys[0], user_key=keys[1], password_key=keys[2])
        accounts = [a.model_copy(update={"mailbox_ref": ref}) if a.id == ALICE else a
                    for a in project.role_accounts]
        project = project.model_copy(update={
            "role_accounts": accounts, "write_policy": WritePolicy.ALLOW_WRITES,
            "secrets": [*project.secrets, *(SecretRef(key=k, domains=[HOST]) for k in keys)]})
        patch.setenv("AUTOTESTER_ROOT", str(base))
        patch.setenv("AUTOTESTER_LEAK_EVIDENCE_KEY", "synthetic-master-key-for-tests")
        secrets = SecretStore.load(project, base / ".env", strict=False)
        run_dir = base / "sessions"
        run_dir.mkdir()
        with RoleSessions(project, secrets, run_dir, paths_root=base) as roles:
            port = LiveRolePort(roles, [sign_in(app)], controls=CONTROLS,
                                mail_connector=_plain_imap, mail_recipients={ALICE: ALICE_MAIL})
            assert port.login_all() == {}
            yield Wired(app, imap, roles, port, base, project)


def _mail_scenario(expectation: Expectation, target: str = "welcome") -> CrossRoleScenario:
    return CrossRoleScenario(
        id="invite", title="A welcome mail reaches alice", roles=[ALICE, BOB],
        steps=[RoleStep(id="open", role_id=ALICE, action="goto /home")],
        assertions=[CrossRoleAssertion(
            id="welcome-mail", observer_role_id=ALICE, channel=AssertChannel.MAILBOX,
            expectation=expectation, target=target, within_s=2, poll_interval_s=0.5)])


def _drive(w: Wired, scenario: CrossRoleScenario, port: Any = None, name: str = "mail"):
    return run_scenario(scenario, port or w.port, project_slug=SLUG, run_dir=str(w.base / name),
                        platform_ids=["app"], oracles=[OracleName.MAILBOX])


def _status(summary: Any, oracle: OracleName) -> Any:
    return next(s for s in summary.statuses if s.oracle is oracle)


@pytest.fixture(scope="module")
def probed_port(wired_port: Wired):
    store = wired_port.store("g11probe")
    wired_port.grant(store, PLANNED)
    run_dir = wired_port.run_dir("probe-run")
    before = len(wired_port.app.reads)
    summary, findings = run_oracles(wired_port.context("g11probe", run_dir), AUTHZ)
    return summary, findings, run_dir, len(wired_port.app.reads) - before
