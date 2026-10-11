"""`POST /projects/{slug}/run` requires a `live_case` approval (AT-570, D-018).

Contract: qa/contracts/consent.md + core-invariants C12(b). Before this unit the
UI case-run path checked no approval at all, and `RunBudget(None)` made the
resulting run *unlimited* rather than unapproved.

Two properties per refusal, both asserted by construction rather than read off
the code: (1) the message names WHICH of the three real states refused the run
-- no `live_case` row exists / the row carries no signature / no signing key is
configured -- because an operator cannot fix a denial that will not say what it
is; (2) the run is reported as NOT-RUN, never as a pass: no run directory, no
result and no verdict are written.

Fakes only for the browser and the grader; the route's own control flow is real.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval
from test_ui_runs import _onboard_demo

from autotester.core.ids import APPROVAL_KEY_ENV
from autotester.schema.case import Case
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.run import RawResult, Run
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _case(idx: int, n_steps: int = 1) -> Case:
    return Case(
        project="demo", flow_id=f"flow-{idx}", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title=f"case-{idx}",
        steps=[Step(order=i, action=Action.CLICK, target=f"#t{idx}-{i}") for i in range(n_steps)],
    )


def _ready(client: TestClient, root: Path, monkeypatch: pytest.MonkeyPatch,
           n_steps: int = 1) -> ProjectStore:
    """An onboarded project with one runnable case, a stubbed browser and an
    available grader -- everything `trigger_run` needs EXCEPT an approval."""
    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module
    from autotester.browser.session import BrowserSession

    _onboard_demo(client)
    store = ProjectStore("demo", root)
    store.add_case(_case(0, n_steps))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    def fake_run_and_grade(case_, session, judge, run_id, store_):
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                         grader_provider="mock"))

    monkeypatch.setattr(
        routes_runs_module, "for_role", lambda project, role: _AvailableProvider())
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient", fake_run_and_grade)
    return store


def _assert_not_run(store: ProjectStore) -> None:
    """O4/C12: a refused run is NOT-RUN, never a pass. Nothing on disk may
    suggest the cases were exercised."""
    runs_dir = store.paths.runs_dir
    assert not runs_dir.exists() or not [p for p in runs_dir.iterdir() if p.is_dir()]


def _target(store: ProjectStore) -> str:
    project = store.load_project()
    assert project is not None
    return project.base_url


# -- reason 1: no live_case approval exists ----------------------------------

def test_a_case_run_with_no_approval_at_all_is_refused_and_says_so(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _ready(client, scratch_root, monkeypatch)
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 403
    assert "live_case" in response.text
    assert "no approval exists for it" in response.text
    assert "uv run autotester approve" in response.text  # names the way to fix it
    _assert_not_run(store)


def test_a_crawl_approval_does_not_cover_a_case_run(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The three rows in `projects/pathlynks/approvals.jsonl` are all
    `run_kind=crawl`; none of them authorises pressing buttons in a case."""
    store = _ready(client, scratch_root, monkeypatch)
    grant_live_case_approval(store, target=_target(store), run_kind=ApprovalKind.CRAWL)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403
    assert "no approval exists for it" in response.text
    _assert_not_run(store)


# -- reason 2: the row exists but carries no signature -----------------------

def test_an_unsigned_live_case_approval_is_refused_naming_the_signature(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The state every pathlynks row is actually in today: no `signature` field
    at all. `schema/approval.py` deliberately does NOT raise for this -- it is a
    different problem from a missing key, and the message must say which."""
    store = _ready(client, scratch_root, monkeypatch)
    approval = grant_live_case_approval(store, target=_target(store), sign=False)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403
    assert approval.id in response.text
    assert "no signature" in response.text
    assert "cannot verify" not in response.text  # not the missing-key state
    _assert_not_run(store)


# -- reason 3: no signing key is configured ----------------------------------

def test_a_missing_signing_key_refuses_a_signed_row_and_names_the_key(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-110 fail-closed, one layer out: with no `AUTOTESTER_APPROVAL_KEY`
    nothing can be verified, so a perfectly good row is still refused -- and
    the operator is told it is the KEY that is missing, not the signature."""
    store = _ready(client, scratch_root, monkeypatch)
    approval = grant_live_case_approval(store, target=_target(store))
    monkeypatch.delenv(APPROVAL_KEY_ENV, raising=False)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403
    assert approval.id in response.text
    assert "cannot verify" in response.text
    assert APPROVAL_KEY_ENV in response.text
    assert "no signature" not in response.text  # not the unsigned state
    _assert_not_run(store)


# -- the bound is real: the estimate is the run's size, not zero -------------

def test_an_approval_narrower_than_the_run_is_refused_with_the_shortfall(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falsifies "pass actions=0": a 3-step case costs 3 actions, so a 1-action
    grant must be refused at preflight and the shortfall named."""
    store = _ready(client, scratch_root, monkeypatch, n_steps=3)
    grant_live_case_approval(store, target=_target(store), max_actions=1)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403
    assert "narrower than this run" in response.text
    assert "actions 3 > approved 1" in response.text
    _assert_not_run(store)


def test_an_approval_granting_no_wall_clock_is_refused_before_a_browser_opens(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-660, the other half: `RunBudget` now refuses a zero time grant, so the
    preflight must request a real, positive wall clock or the run would pass the
    gate and then refuse every case mid-run. Falsifies a preflight that passes
    `wall_clock_s=0.0` (`require_approval`'s own default)."""
    store = _ready(client, scratch_root, monkeypatch)
    grant_live_case_approval(store, target=_target(store), wall_clock_s=0.0)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403
    assert "wall clock" in response.text
    assert "approved 0.0s" in response.text
    _assert_not_run(store)


def test_an_expired_live_case_approval_is_refused(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _ready(client, scratch_root, monkeypatch)
    grant_live_case_approval(store, target=_target(store), expires_at="2020-01-01")

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403
    assert "expired 2020-01-01" in response.text
    _assert_not_run(store)


# -- the happy path: a real grant lets the run through, serial and parallel ---

def test_a_signed_live_case_approval_lets_the_run_proceed(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A guard only the refusals exercise is a guard whose happy path is tested
    nowhere -- and a gate that refuses everything would pass every test above."""
    store = _ready(client, scratch_root, monkeypatch)
    approval = grant_live_case_approval(store, target=_target(store))

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/demo/report"
    run_ids = [p.name for p in store.paths.runs_dir.iterdir() if p.is_dir()]
    assert len(run_ids) == 1
    assert [v.result for v in store.load_verdicts(run_ids[0])] == [Result.PASS]

    # CN10: the bounds the run ACTUALLY ran under are recorded where a human can
    # read them, so a 19-year wall clock is reported rather than silently
    # honoured. Asserted on the real saved run.json, not on the object we built.
    run = store.load_run(run_ids[0])
    assert run is not None
    assert run.bounds is not None, "a run must record the approval it ran under"
    assert (run.bounds.approval_id, run.bounds.max_actions, run.bounds.max_probes,
            run.bounds.wall_clock_s) == (approval.id, 10_000, 0, 100_000.0)
    # C12(b): absence has its OWN representation. A Run with nothing recorded
    # reads as None -- never as zeros, which a reader could not tell apart from
    # an approval that really granted nothing.
    assert Run(id="run-x", project="demo", case_ids=[]).bounds is None


def test_the_parallel_path_receives_the_same_approval_as_its_budget(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`plan.n > 1` is the only branch that reaches `run_cases`, where the
    budget lives -- and `run_cases` now has no `approval` default, so a
    `_run_cases_in_parallel` that forgot to pass one raises `TypeError` and
    this route 500s instead of redirecting. Mid-run exhaustion is deliberately
    unreachable from here: the preflight already required the approval to cover
    the whole run, which is the better place for the refusal."""
    import autotester.ui.routes_runs as routes_runs_module

    store = _ready(client, scratch_root, monkeypatch)
    store.add_case(_case(1))
    grant_live_case_approval(store, target=_target(store), max_actions=2)
    fake_plan = ParallelPlan(config_ceiling=2, measured_budget=2, n=2, bound_by="config",
                              free_ram_mb=1e9, cpu_count=8)
    monkeypatch.setattr(routes_runs_module, "plan_parallel_run",
                        lambda project, **kw: fake_plan)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303
    run_ids = [p.name for p in store.paths.runs_dir.iterdir() if p.is_dir()]
    assert len(run_ids) == 1
    outcomes = sorted(r.outcome for r in store.load_results(run_ids[0]))
    assert outcomes == sorted([Outcome.COMPLETED, Outcome.COMPLETED])
