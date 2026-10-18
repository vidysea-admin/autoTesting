"""T-210 / MP12: every declared PlatformLink is followed, failed with a reason, or not reached.

Pure tests pin the verdict rules (`judge_hops`), the host-in-platform rule and the finding a
hop outside every declared platform becomes. The live test follows seven fixture links in a real
Chromium: a redirect, an SSO meta-refresh hop, a control click, an off-platform redirect, an
off-platform hop in the MIDDLE of a redirect chain, a 404 landing, and a link from a platform
with no account (not reached).
"""

from __future__ import annotations

import faulthandler
import functools
from types import SimpleNamespace

import pytest
from multi_role_app import EVIL_HOST, PARENT_HOST, SCHOOL_HOST, build_project, start_app

from autotester.browser.secrets import SecretStore
from autotester.schema.link_outcome import LinkOutcome, LinkStatus
from autotester.schema.multi_role_enums import FindingClass, LinkKind
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.platform import Platform
from autotester.schema.platform_link import PlatformLink
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount
from autotester.stages.multi_role_session import RoleSessions, host_in_platform
from autotester.stages.platform_links import follow_platform_links, judge_hops


def _project(expected: str = "b.example.test", url_template: str = "/go") -> Project:
    def platform(pid: str) -> Platform:
        host = {"parent": "a", "school": "b"}[pid] + ".example.test"
        return Platform(id=pid, name=pid, base_url=f"https://{host}/",
                        allowed_domains=[host], include_subdomains=False)
    link = PlatformLink(from_platform="parent", to_platform="school", kind=LinkKind.REDIRECT,
                        url_template=url_template, expected_landing_host=expected)
    account = RoleAccount(id="mum", role="Parent", platform_id="parent",
                          username_key="MUM_USER", password_key="MUM_PASS")
    return Project(slug="p", name="P", base_url="https://p.example.test/",
                   allowed_domains=["a.example.test", "b.example.test"],
                   platforms=[platform("parent"), platform("school")],
                   platform_links=[link], role_accounts=[account])


A, B, EVIL = "https://a.example.test", "https://b.example.test", "https://evil.example.test"
JUDGE_CASES = {
    "followed": ([f"{A}/go", f"{B}/home"], f"{B}/home", 200, None, LinkStatus.FOLLOWED, None),
    "off_platform_direct": ([f"{A}/go", f"{EVIL}/x"], None, None, "net::ERR_FAILED",
                            LinkStatus.FAILED, "evil.example.test"),
    "off_platform_mid_chain": ([f"{A}/go", f"{B}/bounce", f"{EVIL}/x", f"{B}/home"],
                               f"{B}/home", 200, None, LinkStatus.FAILED, "evil.example.test"),
    "wrong_declared_host": ([f"{A}/go", f"{A}/home"], f"{A}/home", 200, None,
                            LinkStatus.FAILED, None),
    "http_error": ([f"{A}/go", f"{B}/gone"], f"{B}/gone", 404, None, LinkStatus.FAILED, None),
    "timeout": ([f"{A}/go"], None, None, "TimeoutError: slow", LinkStatus.FAILED, None),
    "no_navigation": ([], None, None, None, LinkStatus.FAILED, None),
}


@pytest.mark.parametrize("name", JUDGE_CASES)
def test_judge_hops_matrix(name):
    hops, landing, status, error, want, offender = JUDGE_CASES[name]
    project = _project()
    got, reason, off = judge_hops(project, project.platform_links[0], hops, landing, status, error)
    assert got is want and off == offender
    assert (reason is None) == (want is LinkStatus.FOLLOWED)
    if name in ("http_error", "timeout"):
        assert "404" in reason or "TimeoutError" in reason


def test_expected_landing_port_is_compared_only_when_declared():
    project = _project(expected="b.example.test:8080")
    link = project.platform_links[0]
    hit = judge_hops(project, link, [f"{B}:8080/h"], f"{B}:8080/h", 200, None)
    miss = judge_hops(project, link, [f"{B}:9999/h"], f"{B}:9999/h", 200, None)
    assert hit[0] is LinkStatus.FOLLOWED and miss[0] is LinkStatus.FAILED


def test_host_in_platform_rules():
    exact = Platform(id="x", name="x", base_url="https://a.test/", allowed_domains=["A.test"],
                     include_subdomains=False)
    wide = exact.model_copy(update={"include_subdomains": True})
    assert host_in_platform(exact, "a.test") and host_in_platform(exact, "a.test.")
    assert not host_in_platform(exact, "sub.a.test") and host_in_platform(wide, "sub.a.test")
    assert not host_in_platform(wide, "evila.test") and not host_in_platform(wide, "")


class _FakeRoles:
    def __init__(self, project: Project) -> None:
        self.project, self.driven = project, []
        self.secrets = SimpleNamespace(scrub_optional=lambda text: text.replace("hunter2", "***"))

    def accounts_on(self, platform_id: str) -> list[RoleAccount]:
        return [a for a in self.project.role_accounts if a.platform_id == platform_id]

    def run_as(self, account_id: str, fn):
        self.driven.append(account_id)
        return fn(SimpleNamespace(account=account_id))


def _follow(project: Project, trace) -> tuple[_FakeRoles, list[LinkOutcome]]:
    roles = _FakeRoles(project)
    return roles, follow_platform_links(project, roles, trace=trace)


def test_off_platform_hop_becomes_a_value_free_finding_and_round_trips():
    project = _project(url_template="/students/12345/report?next=/home")
    canned = ([f"{A}/students/12345/report", f"{EVIL}/phish"], None, None, "net::ERR_FAILED")
    roles, (out,) = _follow(project, lambda *_a: canned)
    assert out.status is LinkStatus.FAILED and out.landed_host == "evil.example.test"
    finding = out.finding
    assert isinstance(finding, MultiRoleFinding)
    assert finding.finding_class is FindingClass.OFF_PLATFORM_HOP
    assert (finding.role, finding.platform_id, finding.count) == ("Parent", "parent", 1)
    template = "/students/{id}/report?next={next}"  # ids and values never reach the finding
    assert finding.url_template == template
    assert finding.steps[0].startswith("login ") and finding.steps[1] == f"goto {template}"
    assert "example" not in finding.title
    assert LinkOutcome.model_validate_json(out.model_dump_json()) == out
    assert roles.driven == ["mum"]


def test_every_link_is_reported_in_order_and_a_link_without_an_account_is_not_reached():
    project = _project()
    orphan = PlatformLink(from_platform="school", to_platform="parent", kind=LinkKind.SSO,
                          url_template="/back", expected_landing_host="a.example.test")
    project.platform_links.append(orphan)
    ok = ([f"{A}/go", f"{B}/home"], f"{B}/home", 200, None)
    _, outcomes = _follow(project, lambda *_a: ok)
    assert [o.link_index for o in outcomes] == [0, 1]
    assert [o.status for o in outcomes] == [LinkStatus.FOLLOWED, LinkStatus.NOT_REACHED]
    assert "no role account" in outcomes[1].reason and outcomes[1].account_id is None
    assert outcomes[0].account_id == "mum" and outcomes[0].reason is None


def test_a_crashing_trace_is_that_links_failure_with_a_scrubbed_reason():
    def boom(*_a):
        raise RuntimeError("could not click, token hunter2 rejected")
    _, (out,) = _follow(_project(), boom)
    assert out.status is LinkStatus.FAILED and "hunter2" not in out.reason
    assert "RuntimeError" in out.reason and out.finding is None


def test_a_url_with_a_query_never_reaches_a_reason():
    def boom(*_a):
        raise RuntimeError("Page.goto: net::ERR_FAILED at https://a.example.test/x?token=abc123"
                           "\nlog")
    _, (out,) = _follow(_project(), boom)
    assert "token" not in out.reason and "abc123" not in out.reason and "<url>" in out.reason
    errored = ([f"{A}/go"], None, None, "net::ERR_FAILED")
    _, (out2,) = _follow(_project(), lambda *_a: errored)
    assert out2.reason == "net::ERR_FAILED"


def test_a_finding_that_cannot_be_built_does_not_drop_the_link_or_the_next_ones(monkeypatch):
    import autotester.stages.platform_links as module

    def refuse(*_a):
        raise ValueError("unrepresentable")
    monkeypatch.setattr(module, "_off_platform_finding", refuse)
    project = _project()
    project.platform_links.append(project.platform_links[0])
    stray = ([f"{A}/go", f"{EVIL}/x"], None, None, "net::ERR_FAILED")
    _, outcomes = _follow(project, lambda *_a: stray)
    assert [o.link_index for o in outcomes] == [0, 1]
    assert all(o.status is LinkStatus.FAILED and o.finding is None for o in outcomes)
    assert all("finding could not be built" in o.reason for o in outcomes)


def test_a_non_http_scheme_on_a_declared_host_is_outside():
    project = _project()
    got = judge_hops(project, project.platform_links[0], [f"{A}/go", "ftp://a.example.test/x"],
                     None, None, None)
    assert got[0] is LinkStatus.FAILED and got[2] == "a.example.test"


def test_no_declared_links_means_no_outcomes():
    project = _project()
    project.platform_links = None
    assert follow_platform_links(project, _FakeRoles(project)) == []


# -- live: real Chromium, local fixture only --------------------------------------------------
@functools.cache
def _skip_if_no_chromium() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


def test_mp12_fixture_links_redirect_sso_control_off_platform_chain_404_and_unreached(tmp_path):
    _skip_if_no_chromium()
    faulthandler.dump_traceback_later(240, exit=True)
    app = start_app()
    try:
        project = build_project(app, tmp_path)
        secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
        with RoleSessions(project, secrets, tmp_path / "runs", paths_root=tmp_path) as roles:
            outcomes = follow_platform_links(project, roles)
        school = f"{SCHOOL_HOST}:{app.port}"
        st = [o.status for o in outcomes]
        assert st == [LinkStatus.FOLLOWED] * 3 + [LinkStatus.FAILED] * 3 + [LinkStatus.NOT_REACHED]
        assert [o.landed_host for o in outcomes[:3]] == [school] * 3
        assert [o.finding is not None for o in outcomes] == [False] * 3 + [True, True, False, False]
        for stopped in outcomes[3:5]:
            assert stopped.landed_host == f"{EVIL_HOST}:{app.port}"
            assert stopped.finding.finding_class is FindingClass.OFF_PLATFORM_HOP
        assert "404" in outcomes[5].reason and outcomes[6].account_id is None
        assert PARENT_HOST in {h for h, _ in app.hits}
    finally:
        faulthandler.cancel_dump_traceback_later()
        app.stop()


def test_mp12_containment_first_hop_never_reaches_the_stray_host_later_hop_is_parked(tmp_path):
    """A redirect answered by the FIRST request is refused before the stray host is contacted;
    one deeper in a chain is followed inside the browser, so it is detected, the host was asked
    once, and the role's browser is parked on about:blank instead of left on the stray site."""
    _skip_if_no_chromium()
    faulthandler.dump_traceback_later(240, exit=True)
    app = start_app()
    try:
        project = build_project(app, tmp_path)
        secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
        direct, chained = project.platform_links[3], project.platform_links[4]
        with RoleSessions(project, secrets, tmp_path / "runs", paths_root=tmp_path) as roles:
            for link, expected_hits in ((direct, []), (chained, ["/phish"])):
                project.platform_links = [link]
                (out,) = follow_platform_links(project, roles)
                assert out.status is LinkStatus.FAILED and out.finding is not None
                assert app.hits_on(EVIL_HOST) == expected_hits
                assert EVIL_HOST not in roles.run_as("alice-parent", lambda s: s.current_url())
            assert roles.run_as("alice-parent", lambda s: s.current_url()) == "about:blank"
    finally:
        faulthandler.cancel_dump_traceback_later()
        app.stop()
