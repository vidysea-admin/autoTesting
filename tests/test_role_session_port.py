"""G11 integration (g11-port-wiring, PW1..PW3): the real `RoleSessionPort` on a real Chromium.

`LiveRolePort` wraps T-210's `RoleSessions` and is run, unmodified oracles and all, through
`run_oracles` against the local two-account fixture app (tests/role_port_app.py). Each oracle must
yield the finding its planted fault calls for, and ONLY that finding (the clean screens and the
rule-abiding role are asserted clean). Nothing leaves the machine: no real product, no provider.
PW4 (a role that cannot sign in) is in test_role_session_port_login.py.
"""

from __future__ import annotations

import faulthandler
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from role_port_app import HOST, PASSWORDS, PII_EMAIL, PII_PHONE, PortApp, build_project, start_app
from role_port_run import (
    ALICE,
    BOB,
    OCR_ROW,
    SIX,
    context,
    declare,
    sign_in,
    skip_if_no_chromium,
    visit,
)

from autotester.browser.secrets import SecretStore
from autotester.core import image_privacy as privacy
from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.lint_rule import LayoutSurface, TextSurface
from autotester.schema.multi_role_enums import (
    AssertChannel,
    Expectation,
    FindingClass,
    OracleName,
)
from autotester.schema.oracle_context import OracleState, RoleSessionPort
from autotester.schema.request_budget import NetworkLogPort
from autotester.schema.role_step import RoleStep
from autotester.stages.multi_role_session import PlatformScopeError, RoleSessions
from autotester.stages.oracle_negative_input import FormInputPort
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.role_port_state import WITHHELD_DETAIL, ChannelUnavailable, UnsupportedStep
from autotester.stages.role_session_port import LiveRolePort


@pytest.fixture(scope="module", autouse=True)
def _deadline():
    faulthandler.dump_traceback_later(420, exit=True)
    yield
    faulthandler.cancel_dump_traceback_later()


@dataclass
class Live:
    app: PortApp
    roles: RoleSessions
    port: LiveRolePort
    run_dir: Path
    login_failures: dict[str, str]
    control: Any
    summary: Any
    findings: list


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    skip_if_no_chromium()
    base = tmp_path_factory.mktemp("g11port")
    app, run_dir = start_app(), base / "run"
    run_dir.mkdir()
    declare(run_dir)
    project = build_project(app, base)
    secrets = SecretStore.load(project, base / ".env", strict=False)
    with pytest.MonkeyPatch.context() as patch, RoleSessions(
            project, secrets, run_dir, paths_root=base) as roles:
        patch.setattr(privacy, "_local_ocr", lambda _path: OCR_ROW)
        port = LiveRolePort(roles, [sign_in(app)], success_selectors=["#ok"])
        failures = port.login_all()
        visit(port, ("/home", "/dashboard", "/reports", "/orders"))
        control = run_oracles(context(run_dir, port), [OracleName.STATE_AFTER])
        app.persist = False  # the planted fault: the server forgets the add
        summary, findings = run_oracles(context(run_dir, port), SIX)
        (run_dir / "findings.json").write_text(
            json.dumps([f.model_dump(mode="json") for f in findings]), encoding="utf-8")
        yield Live(app, roles, port, run_dir, failures, control, summary, findings)
    app.stop()


def _by(live: Live, oracle: OracleName) -> list:
    return [f for f in live.findings if f.oracle is oracle]


def _look(role: str, target: str, channel: AssertChannel = AssertChannel.UI) -> CrossRoleAssertion:
    return CrossRoleAssertion(id="look", observer_role_id=role, channel=channel,
                              expectation=Expectation.PRESENT, target=target, within_s=1)


# -- PW1: the adapter satisfies the port, on two isolated roles --------------------------------
def test_pw1_the_adapter_implements_the_port_and_every_capability(live: Live) -> None:
    assert live.login_failures == {}
    for protocol in (RoleSessionPort, FormInputPort, TextSurface, LayoutSurface, NetworkLogPort):
        assert isinstance(live.port, protocol), protocol.__name__


def test_pw1_two_roles_see_their_own_identity_in_isolated_profiles(live: Live) -> None:
    def who(role: str) -> str:
        live.port.perform(RoleStep(id="home", role_id=role, action="goto /home"))
        seen = live.port.observe(_look(role, "#who"))
        assert seen.matched
        return seen.detail

    # the redactor masks every .env value, usernames included, so identity shows as the key name
    assert "ALICE_USER" in who(ALICE) and "BOB_USER" in who(BOB)
    assert live.roles.profile_dir(ALICE) != live.roles.profile_dir(BOB)
    assert len(live.app.sessions) == 2


def test_pw1_a_target_outside_the_roles_platform_is_refused_before_the_browser_moves(
        live: Live) -> None:
    step = RoleStep(id="out", role_id=ALICE, action=f"goto http://evil.localhost:{live.app.port}/x")
    with pytest.raises(PlatformScopeError):
        live.port.perform(step)
    with pytest.raises(UnsupportedStep):
        live.port.perform(RoleStep(id="ph", role_id=ALICE, action="goto /orders/{unbound}"))


def test_pw1_a_mailbox_look_is_not_wired_and_raises_instead_of_matching_nothing(
        live: Live) -> None:
    with pytest.raises(ChannelUnavailable):
        live.port.observe(_look(ALICE, "Welcome", AssertChannel.MAILBOX))


# -- PW2: every oracle runs end to end and yields exactly its planted finding -------------------
def test_pw2_every_selected_oracle_ran_on_the_real_browser(live: Live) -> None:
    states = {s.oracle: s for s in live.summary.statuses}
    for oracle in SIX:
        assert states[oracle].state is OracleState.RAN, (oracle, states[oracle].reason)


def test_pw2_negative_input_flags_only_the_role_that_skips_the_rule(live: Live) -> None:
    found = _by(live, OracleName.NEGATIVE_INPUT)
    assert {f.role for f in found} == {BOB} and len(found) == 2
    assert all(f.finding_class is FindingClass.NEGATIVE_INPUT for f in found)
    assert all("max_length" in f.title and f"held for role {ALICE}" in f.title for f in found)


def test_pw2_copy_lint_reports_each_declared_rule_on_the_home_screen_only(live: Live) -> None:
    found = _by(live, OracleName.COPY_LINT)
    assert sorted((f.role, f.title.split(":")[0]) for f in found) == sorted(
        (role, rule) for role in (ALICE, BOB) for rule in ("brand", "forbid", "tz"))
    assert all(" on home " in f.title for f in found)


def test_pw2_responsive_flags_the_wide_screen_with_a_masked_screenshot(live: Live) -> None:
    found = _by(live, OracleName.RESPONSIVE)
    assert {f.role for f in found} == {ALICE, BOB} and len(found) == 2
    assert all(" on reports" in f.title and f.finding_class is FindingClass.RESPONSIVE_LAYOUT
               for f in found)
    shots = sorted((live.run_dir / "responsive").glob("*.png"))
    assert len(shots) == 2 and all(p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for p in shots)
    assert all("masked screenshot responsive/" in f.title for f in found)


def test_pw2_api_error_finds_the_failed_save_behind_the_success_screen(live: Live) -> None:
    found = _by(live, OracleName.API_ERROR)
    assert {f.role for f in found} == {ALICE, BOB} and len(found) == 2
    assert all(f.finding_class is FindingClass.HIDDEN_API_ERROR for f in found)
    assert all("POST" in f.title and "500" in f.title for f in found), [f.title for f in found]
    # the route word "save" is not on the closed ROUTE_WORDS list, so it is templated as {id}
    assert all(f.url_template == f"http://{HOST}:{live.app.port}/api/{{id}}" for f in found)


def test_pw2_request_budget_flags_the_busy_polling_screen_only(live: Live) -> None:
    found = _by(live, OracleName.REQUEST_BUDGET)
    kinds = sorted((f.role, f.title.split(":")[0]) for f in found)
    assert kinds == sorted((role, kind) for role in (ALICE, BOB)
                           for kind in ("Request budget exceeded", "Polling too fast"))
    assert all("dashboard" in f.title or "ping" in f.title for f in found)


def test_pw2_state_after_is_clean_when_persisted_and_flags_the_forgotten_add(live: Live) -> None:
    control_summary, control_findings = live.control
    assert control_findings == [] and any(
        s.state is OracleState.RAN for s in control_summary.statuses)
    by_role = {f.role: f.title for f in _by(live, OracleName.STATE_AFTER)}
    assert by_role[ALICE].startswith("not_persisted") and by_role[BOB].startswith("missing")


# -- PW3: no raw secret or personal data reaches a finding, the summary, a file or the detail ---
def test_pw3_no_canary_reaches_findings_summary_or_disk(live: Live) -> None:
    canaries = [*PASSWORDS.values(), PII_EMAIL, PII_PHONE]
    haystack = live.summary.model_dump_json() + "".join(
        f.model_dump_json() for f in live.findings)
    for path in live.run_dir.rglob("*"):
        if path.is_file():
            haystack += path.read_bytes().decode("latin-1")
    assert [c for c in canaries if c in haystack] == []
    assert any((live.run_dir / "responsive").glob("*.png"))  # the sweep did cover real artifacts


def test_pw3_observations_and_screen_text_are_scrubbed(live: Live) -> None:
    def detail(target: str) -> str:
        live.port.perform(RoleStep(id="h", role_id=ALICE, action="goto /home"))
        return live.port.observe(_look(ALICE, target)).detail

    debug = detail("#debug")
    assert detail("#contact") == WITHHELD_DETAIL
    assert "REDACTED" in debug and PASSWORDS["alice"] not in debug
    assert all(PASSWORDS["alice"] not in t.text for t in live.port.surface_texts())


def test_pw3_the_network_log_holds_templates_and_first_party_hosts_only(live: Live) -> None:
    logs = live.port.network_log()
    dumped = "".join(log.model_dump_json() for log in logs)
    assert HOST in dumped and "evil.localhost" not in dumped
    assert all(s.url.startswith(f"http://{HOST}:") for log in logs for s in log.samples)
