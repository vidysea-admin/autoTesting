"""T-179a fix cycle 2, FAILED-1: above READ_ONLY the NAVIGATE guard is exactly as strict as the
browser seam. The oracle is the REAL `BrowserSession.goto` (placeholder resolution, then
`check_destination`) driven on a stub that has no browser; the guard must never refuse what the
seam accepts, and refuses exactly what the seam refuses for every target that needs no
resolution. READ_ONLY keeps every cycle-1 refusal. Offline; fake canary values only."""

from __future__ import annotations

from typing import Any

import pytest

from autotester.agents import guards
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.agent_layer import RefusalClass
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef

BASE = "https://app.test"
RO, TA, AW = WritePolicy.READ_ONLY, WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES
_VALUES = {"HOST": "app.test", "LOGIN_URL": f"{BASE}/signin", "EVIL": "evil.test",
           "APP_PASS": "Hunter2-raw-value-9137"}
_LOCAL = ["app.test", "localhost", "127.0.0.1", "::1"]


def _project(policy: WritePolicy, domains: list[str]) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=domains,
                   write_policy=policy,
                   secrets=[SecretRef(key="HOST", domains=["app.test"]),
                            SecretRef(key="LOGIN_URL", domains=["app.test"]),
                            SecretRef(key="APP_PASS", domains=["app.test"]),
                            SecretRef(key="EVIL", domains=["evil.test"])])


class _Page:
    url = BASE

    def __init__(self) -> None:
        self.visited: list[str] = []

    def goto(self, url: str, **_kw: Any) -> None:
        self.visited.append(url)


class _Seam:
    """Just the attributes `BrowserSession.goto` touches: no browser, no Playwright."""

    def __init__(self, project: Project) -> None:
        self.project, self.page = project, _Page()
        self.secrets = SecretStore(project, dict(_VALUES))

    def _timeout(self, *_a: Any) -> dict[str, Any]:
        return {}

    def _record(self, *_a: Any) -> None:
        return None


def seam_accepts(project: Project, url: str) -> bool:
    seam = _Seam(project)
    try:
        BrowserSession.goto(seam, url)  # type: ignore[arg-type]
    except Exception:  # NavigationRefused, SecretScopeError, UndeclaredSecret, ...
        return False
    return bool(seam.page.visited)


def guard_refusal(project: Project, url: str) -> tuple[RefusalClass, str] | None:
    step = Step(order=1, action=Action.NAVIGATE, target=url)
    case = Case(project="demo", flow_id="f1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="c", steps=[step])
    return guards.write_policy_refusal(case, project)


_PLAIN = [
    f"{BASE}/x", BASE, "https://APP.TEST/x", "https://sub.app.test/x", "http://app.test/x",
    "//app.test/x", "app.test/x", "https://app.test:8443/x", f"{BASE}/x?y=1", f"{BASE}/x#frag",
    f"{BASE}/x\ty", f"{BASE}/x\n", "ftp://app.test/x",
    "https://evil.test/x", "http://evil.test", "https://app.test.evil.test/",
    "https://u:p@app.test/", f"{BASE}\\@evil.test", "//evil.test/x", "data:text/html,x",
    "javascript:alert(1)", "file:///etc/passwd", "/reports", "Admin portal URL", "x",
    "http://localhost/", "http://localhost:3000/a", "http://127.0.0.1/", "http://127.0.0.1:8080/",
    "http://[::1]/", "http://[::1]:8080/", "https://evil.test:app.test", "https:///x",
]
_PLACEHOLDER = [
    "https://{{SECRET:HOST}}/x", "{{SECRET:LOGIN_URL}}", f"{BASE}/x/{{{{SECRET:APP_PASS}}}}",
    "{{SECRET:HOST}}/x", "https://{{SECRET:EVIL}}/x", "{{SECRET:NOPE}}/x", "{{SECRET:EVIL}}",
]


@pytest.mark.parametrize("policy", [TA, AW])
@pytest.mark.parametrize("domains", [["app.test"], _LOCAL], ids=["app", "app+local"])
@pytest.mark.parametrize("url", _PLAIN)
def test_guard_verdict_equals_seam_verdict_without_placeholders(
        policy: WritePolicy, domains: list[str], url: str) -> None:
    project = _project(policy, domains)
    refused = guard_refusal(project, url)
    assert (refused is None) == seam_accepts(project, url), (url, refused)
    if refused is not None:
        assert refused[0] is RefusalClass.DESTINATION and "http(s)" in refused[1]


@pytest.mark.parametrize("policy", [TA, AW])
@pytest.mark.parametrize("url", _PLACEHOLDER)
def test_a_placeholder_target_is_left_to_the_seam_at_these_policies(
        policy: WritePolicy, url: str) -> None:
    """The guard resolves nothing the seam has not: it never refuses a placeholder target, so
    the seam's act-time check (after resolution) is the only judge. Never stricter than the seam."""
    project = _project(policy, ["app.test"])
    assert PLACEHOLDER_RE.search(url) and guard_refusal(project, url) is None
    if url in ("https://{{SECRET:HOST}}/x", "{{SECRET:LOGIN_URL}}", "{{SECRET:HOST}}/x"):
        assert seam_accepts(project, url)  # the four cycle-1 shapes: the seam runs them
    if url in ("https://{{SECRET:EVIL}}/x", "{{SECRET:EVIL}}", "{{SECRET:NOPE}}/x"):
        assert not seam_accepts(project, url)  # only the seam can know: it refuses at act time


_SEAM_REFUSES = [u for u in _PLAIN if not seam_accepts(_project(RO, ["app.test"]), u)]


@pytest.mark.parametrize("url", _SEAM_REFUSES)
def test_read_only_never_runs_what_the_seam_would_refuse(url: str) -> None:
    refused = guard_refusal(_project(RO, ["app.test"]), url)
    assert refused is not None


@pytest.mark.parametrize("url", [
    "https://{{SECRET:HOST}}/x", "{{SECRET:LOGIN_URL}}", f"{BASE}/x/{{{{SECRET:APP_PASS}}}}",
    f"{BASE}/x?y=1", f"{BASE}/x\ty", f"{BASE}/x\n", "ftp://app.test/x", "/reports", "app.test/x",
    "//app.test/x", "Admin portal URL", "https://u:p@app.test/", "javascript:alert(1)",
    "https://evil.test/x", f"{BASE}/account/delete", f"{BASE}/logout"])
def test_read_only_keeps_every_cycle_one_refusal_of_the_raw_target(url: str) -> None:
    assert guard_refusal(_project(RO, ["app.test"]), url) is not None


def test_read_only_still_runs_a_plain_in_domain_get() -> None:
    assert guard_refusal(_project(RO, ["app.test"]), f"{BASE}/reports") is None
