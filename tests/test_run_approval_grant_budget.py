"""Run-approval scope + probe budget (ISS-d063-grant-budget-1/-2/-3, AT-675).

Each test is one attack or one fail-closed property: an account-derived row reused across
credential scopes, a probe-less human row passing the LIVE_CASE preflight, the grant form
unable to set (or to over-set) max_probes, a cross-site POST altering the inputs the account
grant derives from, and legacy/edited rows failing closed without a crash.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval

from autotester.core.consent import ApprovalRequired, is_account_derived
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.explore_consent import covering_approval
from autotester.stages.run_budget import probe_request
from autotester.stages.run_launcher import LaunchRefused, require_live_case_approval
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

LIVE = ApprovalKind.LIVE_CASE


def _project(secrets: bool) -> Project:
    refs = [SecretRef(key=k, domains=["demo.test"]) for k in ("USER_A", "USER_B")]
    return Project(slug="demo", name="Demo", base_url="https://demo.test/app",
                   allowed_domains=["demo.test"], secrets=refs if secrets else [])


@pytest.fixture
def make(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))

    def build(secrets: bool = True) -> ProjectStore:
        store = ProjectStore("demo", tmp_path)
        store.save_project(_project(secrets))
        (tmp_path / ".env").write_text("USER_A=value-a\nUSER_B=value-b\n", encoding="utf-8")
        return store
    return build


def _cover(store: ProjectStore, keys: set[str] | None = None, probes: int = 0) -> RunApproval:
    project = store.load_project()
    assert project is not None
    return covering_approval(project, store, CrawlBounds(max_actions=5), kind=LIVE,
                             account_keys=keys, probes=probes)


# -- ISS-d063-grant-budget-1: scope binding -----------------------------------------------

def test_an_account_row_is_not_reused_for_a_different_credential_scope(make) -> None:
    store = make()
    first = _cover(store, {"USER_A"})
    second = _cover(store, {"USER_B"})
    assert second.id != first.id and second.scope != first.scope
    assert is_account_derived(second) and len(store.list_approvals()) == 2
    assert _cover(store, {"USER_A"}).id == first.id      # same scope still reuses its own row


def test_a_credential_free_run_cannot_reuse_an_account_derived_row(make) -> None:
    store = make()
    _cover(store, {"USER_A"})                             # an account row now exists on disk
    store.save_project(_project(secrets=False))           # the run now declares no credentials
    with pytest.raises(ApprovalRequired):
        _cover(store)
    store.save_project(_project(secrets=True))
    (store.paths.env_file).write_text("", encoding="utf-8")   # declared but not provisioned
    with pytest.raises(ApprovalRequired):
        _cover(store)


# -- ISS-d063-grant-budget-3 / AT-675: probe budget at the consuming gate ----------------

def test_a_probe_less_human_row_is_refused_before_a_fill_run(make) -> None:
    store = make(secrets=False)
    grant_live_case_approval(store, target="https://demo.test/app", max_probes=0)
    with pytest.raises(ApprovalRequired, match="probes 2 > approved 0"):
        _cover(store, probes=2)
    assert _cover(store, probes=0).max_probes == 0        # a run that spends none still passes
    grant_live_case_approval(store, target="https://demo.test/app", max_probes=2)
    assert _cover(store, probes=2).max_probes == 2


def _case(*actions: Action) -> Case:
    steps = [Step(order=i, action=a, target="#x") for i, a in enumerate(actions)]
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="t", steps=steps)


def test_the_launcher_preflight_derives_probes_from_the_cases_and_refuses(make) -> None:
    store = make(secrets=False)
    grant_live_case_approval(store, target="https://demo.test/app", max_probes=0)
    project = store.load_project()
    fill = _case(Action.FILL, Action.ASSERT)
    assert probe_request([fill]) == 3 and probe_request([_case(Action.CLICK)]) == 0
    with pytest.raises(LaunchRefused) as refused:
        require_live_case_approval(project, store, [fill])
    assert refused.value.status == 403 and "probes" in refused.value.reason
    assert require_live_case_approval(project, store, [_case(Action.CLICK)]).max_probes == 0


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _form(**over: str) -> dict[str, str]:
    soon = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    return {"scope": "press the buttons", "expires_at": soon, "max_actions": "10",
            "wall_clock_s": "60", "kind": "live_case", **over}


def test_the_grant_form_exposes_and_stores_max_probes(make, client: TestClient) -> None:
    store = make()
    assert "name='max_probes'" in client.get("/projects/demo/env").text
    response = client.post("/projects/demo/crawl-approval", data=_form(max_probes="37"),
                           follow_redirects=False)
    assert response.status_code == 303
    row = store.list_approvals()[0]
    assert row.max_probes == 37 and row.is_signed_and_verified


@pytest.mark.parametrize("bad", ["-1", "40001", "abc", "1e3"])
def test_the_grant_form_refuses_out_of_range_probes(make, client: TestClient, bad: str) -> None:
    store = make()
    assert client.post("/projects/demo/crawl-approval",
                       data=_form(max_probes=bad)).status_code == 400
    assert store.list_approvals() == []


# -- fail-closed on existing signed rows ---------------------------------------------------

def test_legacy_and_edited_rows_fail_closed_without_a_crash(make) -> None:
    store = make(secrets=False)
    grant_live_case_approval(store, target="https://demo.test/app", max_probes=0)
    line = json.loads(store.paths.approvals.read_text(encoding="utf-8").splitlines()[0])
    legacy = {k: v for k, v in line.items() if k != "max_probes"}      # row from before the field
    edited = {**line, "max_probes": 10**6}                              # widened after signing
    store.paths.approvals.write_text(
        "\n".join(json.dumps(r) for r in (legacy, edited)) + "\n", encoding="utf-8")
    assert len(store.list_approvals()) == 2
    with pytest.raises(ApprovalRequired) as refused:
        _cover(store, probes=1)
    assert "narrower" in str(refused.value) or "edited" in str(refused.value)


# -- ISS-d063-grant-budget-2: nothing alters the grant's inputs cross-site -----------------

def test_a_cross_site_post_cannot_alter_inputs_or_mint_a_grant(make, client: TestClient) -> None:
    store = make()
    before = store.load_project()
    evil = {"Origin": "https://evil.example"}
    for path in ("/projects/demo/secrets", "/projects/demo/env", "/projects/demo/run",
                 "/projects/demo/crawl-approval"):
        assert client.post(path, headers=evil, data={"key": "USER_A", "domains": "evil.example"},
                           follow_redirects=False).status_code == 403
    assert store.load_project() == before
    assert store.list_approvals() == []
