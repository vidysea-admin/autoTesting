"""D-068 (consent.md CN1/CN5/CN11): provisioned credentials ARE the standing run approval.

A project that declares credentials (SecretRef[]) and has them provisioned needs no per-run
human approval for its declared target and allowed_domains. The signed row is minted
automatically as an audit record, for LIVE_CASE, CRAWL and READ, never ADVERSARIAL. One row
covers any run of the same (project, run_kind, target) whatever case set minted it. Still
refused: no declared credentials, a target or domain outside the declaration, a lost key.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.core.consent import (
    ApprovalRequired,
    is_account_derived,
    prepare_account_grant,
    require_approval,
)
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project, SecretRef
from autotester.stages import explore_consent
from autotester.stages.explore_consent import covering_approval
from autotester.store.project_store import ProjectStore

GRANTED = (ApprovalKind.LIVE_CASE, ApprovalKind.CRAWL, ApprovalKind.READ)


def _project(domains: tuple[str, ...] = ("demo.test",), declared: bool = True) -> Project:
    refs = [SecretRef(key="DEMO_USER", domains=list(domains))] if declared else []
    return Project(slug="demo", name="Demo", base_url="https://demo.test/app",
                   allowed_domains=["demo.test"], secrets=refs)


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))

    def make(project: Project | None = None, provisioned: bool = True) -> ProjectStore:
        store = ProjectStore("demo", tmp_path)
        store.save_project(project or _project())
        if provisioned:
            (tmp_path / ".env").write_text("DEMO_USER=synthetic-account-value\n",
                                           encoding="utf-8")
        return store
    return make


def _cover(store: ProjectStore, kind: ApprovalKind, actions: int = 50, **kw):
    project = store.load_project()
    assert project is not None
    return covering_approval(project, store, CrawlBounds(max_actions=actions), kind=kind, **kw)


@pytest.mark.parametrize("kind", GRANTED)
def test_declared_provisioned_credentials_mint_a_signed_row_with_no_human_step(
    setup, kind: ApprovalKind,
) -> None:
    store = setup()
    row = _cover(store, kind)
    assert row.run_kind is kind and row.target == "https://demo.test/app"
    assert row.project == "demo" and row.production is False
    assert row.is_intact and row.is_signed_and_verified and is_account_derived(row)
    assert row.max_actions >= 50 and row.max_probes > 0 and row.wall_clock_s > 0
    assert store.list_approvals() == [row]
    scope = json.loads(row.scope)
    assert scope["keys"] == ["DEMO_USER"] and "cases" not in scope
    assert "synthetic-account-value" not in row.model_dump_json()


def test_a_second_run_reuses_the_row_instead_of_minting_another(setup) -> None:
    store = setup()
    first = _cover(store, ApprovalKind.CRAWL)
    assert _cover(store, ApprovalKind.CRAWL).id == first.id
    assert len(store.list_approvals()) == 1


def test_a_row_covers_any_case_set_of_the_same_triple(setup) -> None:
    """CN5 amended (gate d063-cn5-vs-cn11, B): minted for one case set, it covers another run
    of the triple, including one that references no credentials at all."""
    store = setup()
    minted = _cover(store, ApprovalKind.LIVE_CASE, actions=20, account_keys={"DEMO_USER"})
    other_set = _cover(store, ApprovalKind.LIVE_CASE, actions=5, account_keys=None)
    assert other_set.id == minted.id and len(store.list_approvals()) == 1


def test_exactness_survives_account_derived_rows(setup) -> None:
    store = setup()
    live = _cover(store, ApprovalKind.LIVE_CASE)
    rows = store.list_approvals()
    for target in ("https://demo.test/app/", "https://DEMO.test/app", "https://demo.test/app?x=1"):
        with pytest.raises(ApprovalRequired):
            require_approval(rows, project="demo", kind=ApprovalKind.LIVE_CASE, target=target)
    with pytest.raises(ApprovalRequired):
        require_approval(rows, project="other", kind=ApprovalKind.LIVE_CASE, target=live.target)
    assert _cover(store, ApprovalKind.CRAWL).id != live.id  # no transfer across run kinds


def test_a_wider_run_mints_a_new_row_not_a_widened_old_one(setup) -> None:
    store = setup()
    small = _cover(store, ApprovalKind.CRAWL, actions=10)
    big = _cover(store, ApprovalKind.CRAWL, actions=500)
    assert big.id != small.id and big.max_actions >= 500
    assert store.list_approvals()[0].model_dump_json() == small.model_dump_json()


def test_an_expired_account_row_is_replaced_by_a_new_one(setup) -> None:
    store = setup()
    project = store.load_project()
    old_now = datetime.now(UTC) - timedelta(days=2)
    secrets = SecretStore.load(project, store.paths.env_file, strict=False)
    stale = prepare_account_grant(project, secrets, kind=ApprovalKind.CRAWL,
        account_keys={"DEMO_USER"}, actions=50, probes=1000, wall_clock_s=600.0, now=old_now)
    store.add_approval(stale)
    fresh = _cover(store, ApprovalKind.CRAWL)
    assert fresh.id != stale.id and not fresh.is_expired(datetime.now(UTC))


def test_a_forged_account_row_is_never_honoured(setup) -> None:
    store = setup()
    genuine = _cover(store, ApprovalKind.CRAWL, actions=10)
    forged = type(genuine).model_validate(
        genuine.model_dump() | {"max_actions": 10**6, "max_probes": 10**9,
                                "wall_clock_s": 10.0**9, "id": ""})
    assert forged.is_signed_and_verified is False
    store.paths.approvals.write_text(forged.model_dump_json() + "\n", encoding="utf-8")
    row = _cover(store, ApprovalKind.CRAWL, actions=100)
    assert row.id != forged.id and row.is_signed_and_verified and row.max_actions < 10**6


@pytest.mark.parametrize("kind", [ApprovalKind.ADVERSARIAL])
def test_adversarial_never_gets_an_automatic_grant(setup, kind: ApprovalKind) -> None:
    store = setup()
    project = store.load_project()
    secrets = SecretStore.load(project, store.paths.env_file, strict=False)
    with pytest.raises(ApprovalRequired, match=r"(?i)adversarial"):
        prepare_account_grant(project, secrets, kind=kind, account_keys={"DEMO_USER"},
                              actions=5, probes=100, wall_clock_s=30.0)
    with pytest.raises(ApprovalRequired):
        _cover(store, kind)
    assert store.list_approvals() == []


@pytest.mark.parametrize("case", ["no-credentials-declared", "declared-not-provisioned",
                                  "domain-outside-the-declaration", "lost-signing-key"])
def test_refusals_that_remain_leave_no_trace(
    setup, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    project = {"no-credentials-declared": _project(declared=False),
               "domain-outside-the-declaration": _project(domains=("sibling.test",))}.get(
                   case, _project())
    store = setup(project, provisioned=case != "declared-not-provisioned")
    if case == "lost-signing-key":
        signed = _cover(store, ApprovalKind.CRAWL)  # history now holds a signed row
        monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY")
        before = (tmp_path / ".env").read_text(encoding="utf-8")
    with pytest.raises(ApprovalRequired, match="refusing to start"):
        _cover(store, ApprovalKind.LIVE_CASE)
    rows = store.list_approvals()
    assert rows == ([signed] if case == "lost-signing-key" else [])
    if case == "lost-signing-key":
        assert (tmp_path / ".env").read_text(encoding="utf-8") == before


def test_the_crawl_seam_and_preflight_use_the_same_derivation(setup) -> None:
    """`run_crawl`, the CLI and the UI all call `require_consent`; none needs a human row."""
    store = setup()
    project = store.load_project()
    explore_consent.require_consent(project, store, CrawlBounds(),
                                    SafetyPolicy(write_policy=project.write_policy))
    assert [r.run_kind for r in store.list_approvals()] == [ApprovalKind.CRAWL]


def test_a_covering_human_row_wins_and_is_not_duplicated(setup) -> None:
    from run_approval_fixture import grant_live_case_approval
    store = setup()
    human = grant_live_case_approval(store, target="https://demo.test/app", max_probes=10**6)
    assert _cover(store, ApprovalKind.LIVE_CASE).id == human.id
    assert store.list_approvals() == [human]


def test_a_probe_less_human_row_does_not_cover_a_credentialed_run(setup) -> None:
    """The run spends probes (fill receipt, polling); a row granting none would stop it at
    the first fill, so a fresh account row is minted instead (fixes the P2 finding)."""
    from run_approval_fixture import grant_live_case_approval
    store = setup()
    human = grant_live_case_approval(store, target="https://demo.test/app", max_probes=0)
    row = _cover(store, ApprovalKind.LIVE_CASE)
    assert row.id != human.id and is_account_derived(row) and row.max_probes > 0


# -- the shipped entry points: UI run and UI explore, no human row anywhere -----------------

def _ui(setup, monkeypatch: pytest.MonkeyPatch, provisioned: bool = True):
    from fastapi.testclient import TestClient
    from test_ui_runs_live_case_approval import _case

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module
    from autotester.browser.session import BrowserSession
    from autotester.schema.enums import Outcome, Result
    from autotester.schema.run import RawResult
    from autotester.schema.verdict import Verdict
    from autotester.ui.app import app

    store = setup(provisioned=provisioned)
    store.add_case(_case(0))
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _Judge:
        def available(self) -> bool:
            return True

    def fake(case_, session, judge, run_id, store_):
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                        grader_provider="mock"))
    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _Judge)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient", fake)
    return store, TestClient(app)


def test_ui_run_needs_no_human_approval_when_credentials_are_provisioned(
    setup, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, client = _ui(setup, monkeypatch)
    assert client.post("/projects/demo/run", follow_redirects=False).status_code == 303
    assert client.post("/projects/demo/run", follow_redirects=False).status_code == 303
    rows = store.list_approvals()
    assert len(rows) == 1 and rows[0].run_kind is ApprovalKind.LIVE_CASE
    assert is_account_derived(rows[0])


def test_ui_run_without_provisioned_credentials_is_still_refused(
    setup, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, client = _ui(setup, monkeypatch, provisioned=False)
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403 and "no approval exists" in response.text
    assert store.list_approvals() == []


def test_ui_explore_needs_no_human_approval_when_credentials_are_provisioned(
    setup, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import autotester.ui.routes_crawls as routes_crawls
    from autotester.stages import explore as explore_stage

    store, client = _ui(setup, monkeypatch)
    monkeypatch.setattr(explore_stage, "run_crawl", lambda *a, **k: SimpleNamespace(id="crawl-x"))
    monkeypatch.setattr(routes_crawls, "_queue_coverage_gap", lambda *a, **k: None)
    response = client.post("/projects/demo/explore", follow_redirects=False)
    assert response.status_code == 303
    assert [r.run_kind for r in store.list_approvals()] == [ApprovalKind.CRAWL]


def test_ui_explore_without_credentials_is_refused_and_leaves_no_trace(
    setup, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    store, client = _ui(setup, monkeypatch, provisioned=False)
    response = client.post("/projects/demo/explore", follow_redirects=False)
    assert response.status_code == 403
    assert store.list_approvals() == [] and not (tmp_path / "projects/demo/crawl").exists()


def test_cli_explore_preflight_passes_with_credentials_and_exits_2_without(setup) -> None:
    import typer

    from autotester.cli_crawl import _preflight_consent

    store = setup()
    _preflight_consent(store.load_project(), store, CrawlBounds())
    assert [r.run_kind for r in store.list_approvals()] == [ApprovalKind.CRAWL]
    bare = setup(_project(declared=False))
    bare.paths.approvals.unlink()
    with pytest.raises(typer.Exit) as exc:
        _preflight_consent(bare.load_project(), bare, CrawlBounds())
    assert exc.value.exit_code == 2 and bare.list_approvals() == []
