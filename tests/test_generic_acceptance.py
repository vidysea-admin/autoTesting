"""T-169: both entry modes end to end on the LOCAL fixture product, no CLI.

Mode 1 (teaching sources: a video and a doc -> INGEST) and Mode 2 (URL + test credentials only
-> DISCOVER) are each driven through the app's own routes (`/onboard`, flowspec approve,
cases/generate, run) and the orchestrator, then scored by the EXISTING bench_from_run +
acceptance_comparison. No browser and no model are used: the fixture site is served for real
(Mode 2's crawl reads its pages over HTTP), the vision/judge/executor are fakes.
Proposed contract criteria for this unit: qa/feedback-inbox.md (T-169 entry).
"""

from __future__ import annotations

import re
import urllib.request
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval

from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.crawl import Crawl
from autotester.schema.enums import (
    Action,
    CrawlStatus,
    EdgeOutcome,
    Outcome,
    Result,
    ReviewStatus,
)
from autotester.schema.flowspec import Step
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
)
from autotester.schema.run import RawResult
from autotester.schema.run_state import StageName
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.generic_acceptance import (
    EXPECTED_ENTRY,
    EXPECTED_MODE,
    ModeResult,
    ModeSeams,
    ModeSpec,
    run_mode,
)
from autotester.stages.orchestrate import choose_mode
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

SITE = Path(__file__).resolve().parent / "fixtures" / "regression_site"
DOC = Path(__file__).resolve().parent / "fixtures" / "sample_doc.md"


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def product_url(serve_dir: Callable[[Path], str]) -> str:
    return serve_dir(SITE)


def _spec(mode: str, base: str, tmp_path: Path) -> ModeSpec:
    host = "127.0.0.1"
    slug = "fixture-shop"
    creds = [("FIXTURE_SHOP_USER", "tester@fixture.test", host),
             ("FIXTURE_SHOP_PASSWORD", "not-a-real-secret-9x", host)]
    common = dict(slug=slug, name="Fixture Shop", base_url=f"{base}/index.html",
                  allowed_domains=[host], credentials=creds)
    if mode == "url_only":
        return ModeSpec(mode="url_only", **common)  # type: ignore[arg-type]
    video = tmp_path / "walkthrough.mp4"
    video.write_bytes(b"fixture video bytes")
    return ModeSpec(
        mode="teaching", evals="a visitor can reach the sign-in page",
        use_cases="visitor signs in", sources=[
            ("video", str(video), "Home to sign-in walkthrough"),
            ("doc", str(DOC), "Product notes")], **common)  # type: ignore[arg-type]


def _crawl_fixture(base: str, store: ProjectStore) -> Callable[[], tuple[Crawl, list[ScreenNode]]]:
    """DISCOVER's crawl seam: reads the fixture's real pages over HTTP (no browser)."""

    def _title(url: str) -> str:
        html = urllib.request.urlopen(url, timeout=10).read().decode()
        return re.search(r"<title>(.*?)</title>", html).group(1)  # type: ignore[union-attr]

    def crawl() -> tuple[Crawl, list[ScreenNode]]:
        c = Crawl(project="fixture-shop", status=CrawlStatus.COMPLETED,
                  stop_reason="frontier empty")
        home_url, login_url = f"{base}/index.html", urljoin(f"{base}/", "login.html")
        home = ScreenNode(crawl_id=c.id, project=c.project, url_template=home_url,
                          url_example=home_url, signature="sig-home", title=_title(home_url),
                          name="Home")
        login = ScreenNode(crawl_id=c.id, project=c.project, url_template=login_url,
                           url_example=login_url, signature="sig-login",
                           title=_title(login_url), name="Sign in")
        edge = ScreenEdge(crawl_id=c.id, from_node=home.id, to_node=login.id, action=Action.CLICK,
                          target="a", name="Sign in", outcome=EdgeOutcome.NAVIGATED)
        login = login.model_copy(update={"discovered_by": edge.id})
        for node in (home, login):
            store.add_node(node)
        store.add_edge(edge)
        c = c.model_copy(update={"screens": 2, "edges": 1})
        store.save_crawl(c)
        return c, [home, login]

    return crawl


def _vision(base: str) -> MockProvider:
    obs = VideoObservation(
        screens=[ObservedScreen(name="Home", t_start=0.0, url=f"{base}/index.html"),
                 ObservedScreen(name="Sign in", t_start=4.0, url=f"{base}/login.html")],
        flows=[ObservedFlow(name="Reach sign-in", entry_screen="Home", steps=[
            ObservedStep(order=1, t_start=0.0, action=Action.NAVIGATE, target=f"{base}/index.html"),
            ObservedStep(order=2, t_start=4.0, action=Action.CLICK, target="Sign in")])],
        summary="visitor opens home then sign-in")
    return MockProvider(responses={"vision": [obs]})


def _drive(mode: str, client: TestClient, root: Path, base: str, tmp_path: Path,
           monkeypatch: pytest.MonkeyPatch) -> tuple[ModeResult, ProjectStore, ModeSpec]:
    spec = _spec(mode, base, tmp_path)
    store = ProjectStore(spec.slug, root)
    agent = MockProvider(responses={"agent": [ExpandedSteps(
        steps=[Step(order=1, action=Action.CLICK, target="Sign in")], rationale="x")] * 60})
    judge_ok = type("J", (), {"available": lambda self: True})()
    monkeypatch.setattr("autotester.ui.routes_learn.for_role", lambda project, role: agent)
    monkeypatch.setattr("autotester.ui.routes_runs.for_role", lambda project, role: judge_ok)
    from autotester.browser.session import BrowserSession
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    seen: list[str] = []

    def grade(case, session, judge, run_id, store_):
        seen.append(case.id)
        failed = len(seen) == 1  # exactly one case reports a failure: one unadjudicated finding
        verdict = Verdict(
            run_id=run_id, case_id=case.id, grader_provider="fake",
            result=Result.FAIL if failed else Result.PASS,
            failures=[Failure(criterion_id="c1", reason="sign-in link missing")] if failed else [])
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED), verdict

    monkeypatch.setattr("autotester.ui.run_execution.run_and_grade_case_resilient", grade)

    def review(store_: ProjectStore) -> None:
        from autotester.stages.expand import propose_cases
        rows = propose_cases(store_.load_flowspec())
        store_.stage_case_proposals(rows)
        for row in rows:
            store_.review_case_proposal(row.id, by="fixture-human", approved=True)

    seams = ModeSeams(
        ingest_provider=_vision(base), crawl_fn=_crawl_fixture(base, store),
        review_proposals=review,
        before_run=lambda s: grant_live_case_approval(
            s, project=spec.slug, target=s.load_project().base_url))  # type: ignore[union-attr]
    return run_mode(client, store, spec, seams), store, spec


@pytest.mark.parametrize("mode", ["teaching", "url_only"])
def test_both_modes_end_to_end_without_cli(
    mode: str, client: TestClient, scratch_root: Path, product_url: str, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, store, spec = _drive(mode, client, scratch_root, product_url, tmp_path, monkeypatch)

    # the entry path was chosen from what the user supplied, and recorded with a reason
    assert result.run_state.mode == EXPECTED_MODE[mode]
    entry = result.run_state.checkpoint(EXPECTED_ENTRY[mode])
    assert entry is not None and entry.status == "done"
    other = {"teaching": "discover", "url_only": "ingest"}[mode]
    assert all(c.stage.value != other for c in result.run_state.stages)
    model = result.run_state.checkpoint(StageName.MODEL)  # then it stops at the review gate
    assert model is not None and model.status == "done"

    # the UI path produced reviewed truth, cases and a graded run
    flowspec = store.load_flowspec()
    assert flowspec is not None and flowspec.review.status is ReviewStatus.APPROVED
    assert flowspec.flows, "the entry stage must yield at least one flow to test"
    assert store.list_cases() and store.load_run(result.run_id) is not None

    # scored by the existing bench/acceptance comparison: complete, recall unavailable (D-089)
    cmp = result.comparison
    assert result.problems == [], result.problems
    assert cmp.project == spec.slug and cmp.human_list == "absent"
    assert cmp.autotester.findings_reported == 1 and cmp.fp_rate_unadjudicated
    assert cmp.autotester.detection_rate.value is None
    assert "no human list" in cmp.autotester.detection_rate.text()
    assert cmp.autotester.duration_s.value is not None


def test_entry_path_follows_the_supplied_material(
    client: TestClient, scratch_root: Path, product_url: str, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credentials alone never route to INGEST; a video + doc always do (OR1)."""
    for mode in ("url_only", "teaching"):
        monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path / mode))
        (tmp_path / mode).mkdir()
        _drive(mode, client, tmp_path / mode, product_url, tmp_path / mode, monkeypatch)
        store = ProjectStore("fixture-shop", tmp_path / mode)
        assert choose_mode(store.list_sources())[0] == EXPECTED_MODE[mode]
