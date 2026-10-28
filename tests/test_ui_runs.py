"""Run trigger. Contract: qa/contracts/ui-run.md RU1-RU4. Split out of
test_ui.py to match ui/routes_runs.py's own module split and stay under the
300-line design rule. A real browser is mocked out (BrowserSession.start/close,
run_and_grade_case_resilient — the serial and entry-case seam since AT-574,
patched on `ui/run_execution.py` since AT-567's module split moved that seam
there) — the route's own control flow (case lookup, provider availability,
persistence, redirect) is exercised for real.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval

from autotester.schema.enums import Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _onboard_demo(client: TestClient) -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })


def _approve_demo_runs(root: Path, target: str | None = None) -> None:
    """The `live_case` approval `POST /projects/demo/run` requires since AT-570.

    Granted, never bypassed -- so every run test also exercises the gate's happy
    path, the same reason `crawl_fake.grant_crawl_approval` exists for crawls. A
    guard only the production callers pass through is a guard tested nowhere.
    Bounds are non-zero (AT-660/CN10); refusal paths are covered on purpose in
    `tests/test_ui_runs_live_case_approval.py`."""
    store = ProjectStore("demo", root)
    project = store.load_project()
    assert project is not None, "onboard the project before approving its runs"
    # Read `base_url` back from disk rather than hardcoding it: `require_approval`
    # matches the target EXACTLY, and onboarding normalises what the form posted.
    grant_live_case_approval(store, target=target or project.base_url)


def test_run_refuses_a_project_with_no_cases(client: TestClient, scratch_root: Path) -> None:
    _onboard_demo(client)
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 400
    assert "no cases" in response.text


def test_run_refuses_when_no_ai_provider_is_configured(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind
    from autotester.schema.flowspec import Step

    _onboard_demo(client)
    ProjectStore("demo", scratch_root).add_case(Case(
        project="demo", flow_id="flow-home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Homepage loads",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")],
    ))

    class _UnavailableProvider:
        def available(self) -> bool:
            return False

    import autotester.ui.routes_runs as routes_runs_module

    monkeypatch.setattr(
        routes_runs_module, "for_role", lambda project, role: _UnavailableProvider())

    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 400
    assert "no AI provider" in response.text


def test_run_executes_every_case_and_redirects_to_the_report(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from autotester.browser.session import BrowserSession
    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind
    from autotester.schema.flowspec import Step

    _onboard_demo(client)
    store = ProjectStore("demo", scratch_root)
    case = store.add_case(Case(
        project="demo", flow_id="flow-home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Homepage loads",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")],
    ))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    calls = []

    def fake_run_and_grade_case_resilient(case_, session, judge, run_id, store_):
        calls.append(case_.id)
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module

    monkeypatch.setattr(
        routes_runs_module, "for_role", lambda project, role: _AvailableProvider())
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    _approve_demo_runs(scratch_root)  # AT-570: the live_case approval a run now needs
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/projects/demo/report"
    assert calls == [case.id]
    verdicts = {v.case_id: v for v in store.load_verdicts(_only_run_id(store))}
    assert verdicts[case.id].result is Result.PASS


def _only_run_id(store: ProjectStore) -> str:
    run_ids = sorted(p.name for p in store.paths.runs_dir.iterdir() if p.is_dir())
    assert len(run_ids) == 1
    return run_ids[0]


@pytest.mark.parametrize("priority,expected", [("p0", ["p0", "pin"]), ("p1", ["p1", "pin"])])
def test_trigger_runs_exact_selected_priority_plus_pinned_once(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
    priority: str, expected: list[str],
) -> None:
    from types import SimpleNamespace

    from autotester.schema.case import Case
    from autotester.schema.enums import CaseClass, CaseKind

    _onboard_demo(client)
    store = ProjectStore("demo", scratch_root)
    rows = [store.add_case(Case(project="demo", flow_id=name, kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title=name, priority="p3" if name == "pin" else name,
            pinned=name == "pin")) for name in ["p0", "p1", "p2", "pin"]]
    _approve_demo_runs(scratch_root)
    seen = []

    def execute(store_, run_id, secrets, project, cases, *args):
        seen.extend(c.id for c in cases)
        return SimpleNamespace(n=1, bound_by="config", excluded_s=None)

    monkeypatch.setattr("autotester.stages.run_launcher.run_cases_traced", execute)
    monkeypatch.setattr("autotester.ui.routes_runs.for_role",
                        lambda project, role: SimpleNamespace(available=lambda: True))
    response = client.post(f"/projects/demo/run?priority={priority}", follow_redirects=False)
    wanted = [c.id for c in rows if c.flow_id in expected]
    assert response.status_code == 303 and seen == wanted
    assert store.load_run(_only_run_id(store)).case_ids == wanted
    assert len(seen) == 2 and len(set(seen)) == 2
    assert client.post("/projects/demo/run?priority=p9").status_code == 422


def test_is_entry_case_matches_the_projects_own_base_url(scratch_root: Path) -> None:
    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind
    from autotester.schema.flowspec import Step
    from autotester.schema.project import Project
    from autotester.ui.routes_runs import _is_entry_case

    project = Project(slug="demo", name="Demo", base_url="https://demo.test/signin",
                       allowed_domains=["demo.test"])
    entry_case = Case(
        project="demo", flow_id="flow-login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Login",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin")],
    )
    deeper_case = Case(
        project="demo", flow_id="flow-profile", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Edit profile",
        steps=[Step(order=1, action=Action.CLICK, target="edit-profile-button")],
    )

    assert _is_entry_case(entry_case, project) is True
    assert _is_entry_case(deeper_case, project) is False


def test_entry_case_gets_an_isolated_wiped_profile_not_the_shared_one(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-044: an entry-screen case (e.g. a login flow) must never reuse the
    shared, persistently-authenticated profile the other cases rely on --
    it needs a genuinely logged-out state every time, or the entry screen
    (a sign-in form) may never appear."""
    from autotester.browser.session import BrowserSession
    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind
    from autotester.schema.flowspec import Step

    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    entry_case = store.add_case(Case(
        project="demo", flow_id="flow-login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Login",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin")],
    ))
    deep_case = store.add_case(Case(
        project="demo", flow_id="flow-profile", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Edit profile",
        steps=[Step(order=1, action=Action.CLICK, target="edit-profile-button")],
    ))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    profile_dirs: dict[str, object] = {}

    def fake_run_and_grade_case_resilient(case_, session, judge, run_id, store_):
        profile_dirs[case_.id] = session.paths.profile_dir
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module

    monkeypatch.setattr(
        routes_runs_module, "for_role", lambda project, role: _AvailableProvider())
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    _approve_demo_runs(scratch_root)  # AT-570: the live_case approval a run now needs
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303
    assert profile_dirs[entry_case.id] != profile_dirs[deep_case.id]
    assert "entry-test" in str(profile_dirs[entry_case.id])
    assert "entry-test" not in str(profile_dirs[deep_case.id])


def test_run_button_appears_only_when_the_project_has_cases(
    client: TestClient, scratch_root: Path
) -> None:
    _onboard_demo(client)
    without_cases = client.get("/projects/demo").text
    assert "no cases yet" in without_cases

    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind
    from autotester.schema.flowspec import Step

    ProjectStore("demo", scratch_root).add_case(Case(
        project="demo", flow_id="flow-home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Homepage loads",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")],
    ))
    with_cases = client.get("/projects/demo").text
    assert "action='/projects/demo/run'" in with_cases
