"""AT-887: every door that merges a crawl (CLI, UI button, orchestrated DISCOVER) also proposes
its flows, and re-merging leaves the persisted spec byte-identical (explore.md X13, extended)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.cli_crawl import _merge_into_flowspec
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review, Screen
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_merge import merge_stored_crawl
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_runners import make_discover_runner, make_model_runner
from autotester.stages.screen_identity import dangling_references
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

CRAWL = "crawl_doors"
PROJECT = Project(slug="demo", name="Demo", base_url="https://demo.test",
                  allowed_domains=["demo.test"])


def seeded(root: Path) -> tuple[ProjectStore, Crawl, list[ScreenNode]]:
    store = ProjectStore("demo", root)
    store.save_project(PROJECT)
    crawl = Crawl(project="demo", id=CRAWL, login_case_id="case_login")
    store.save_crawl(crawl)
    home = ScreenNode(crawl_id=CRAWL, project="demo", url_template="demo.test/home",
                      url_example="https://demo.test/home", signature="s_home", name="Home")
    link = ScreenEdge(crawl_id=CRAWL, from_node=home.id, action=Action.NAVIGATE,
                      target='role=link[name="Settings"] >> nth=0', outcome="navigated")
    settings = ScreenNode(crawl_id=CRAWL, project="demo", url_template="demo.test/settings",
                          url_example="https://demo.test/settings", signature="s_set",
                          name="Settings", discovered_by=link.id)
    for n in (home, settings):
        store.add_node(n)
    store.add_edge(link)
    return store, crawl, [home, settings]


def test_remerging_a_stored_crawl_leaves_the_persisted_file_byte_identical(tmp_path) -> None:
    store, _, _ = seeded(tmp_path)
    store.save_flowspec(merge_stored_crawl(store, None, "demo", CRAWL))
    first = store.paths.flowspec.read_bytes()
    spec = store.load_flowspec()
    assert len(spec.flows) == 1 and spec.flows[0].requires_auth
    store.save_flowspec(merge_stored_crawl(store, spec, "demo", CRAWL))
    assert store.paths.flowspec.read_bytes() == first


def test_the_cli_door_proposes_flows_and_says_so(tmp_path, capsys) -> None:
    store, _, _ = seeded(tmp_path)
    store.save_flowspec(FlowSpec(project="demo", review=Review(
        status=ReviewStatus.APPROVED, by="umesh")))
    _merge_into_flowspec(store, "demo", CRAWL)
    spec = store.load_flowspec()
    assert len(spec.flows) == 1 and spec.review.status is ReviewStatus.DRAFT
    assert "1 flow proposal(s)" in capsys.readouterr().out


def test_the_ui_button_proposes_flows_and_never_approves(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store, _, _ = seeded(tmp_path)
    store.save_flowspec(FlowSpec(project="demo", review=Review(
        status=ReviewStatus.APPROVED, by="umesh")))
    resp = TestClient(app).post(f"/projects/demo/crawls/{CRAWL}/merge", follow_redirects=False)
    assert resp.status_code == 303
    spec = ProjectStore("demo", tmp_path).load_flowspec()
    assert len(spec.flows) == 1 and spec.flows[0].source_id == CRAWL
    assert spec.review.status is ReviewStatus.DRAFT and spec.review.by is None


def test_orchestrated_discover_parks_flow_proposals_in_its_draft(tmp_path) -> None:
    store, crawl, nodes = seeded(tmp_path)
    runner = make_discover_runner(PROJECT, lambda: (crawl, nodes))
    ref = runner(StageContext(store=store, run_id="run1"), None)
    proposal = read_json(Path(ref), FlowSpec)
    assert proposal is not None and len(proposal.flows) == 1
    assert proposal.review.status is ReviewStatus.DRAFT
    assert store.load_flowspec() is None  # reviewed truth untouched


@pytest.mark.parametrize("start", ["none", "draft"])
def test_no_edges_stored_means_screens_only_plus_the_landing_screen(tmp_path, start) -> None:
    store = ProjectStore("demo", tmp_path)
    store.save_project(PROJECT)
    store.save_crawl(Crawl(project="demo", id="crawl_bare"))
    store.add_node(ScreenNode(crawl_id="crawl_bare", project="demo", url_template="demo.test/",
                              url_example="https://demo.test/", signature="s", name="Home"))
    base = None if start == "none" else FlowSpec(project="demo")
    spec = merge_stored_crawl(store, base, "demo", "crawl_bare")
    assert len(spec.screens) == 1 and [len(f.steps) for f in spec.flows] == [1]


# -- a screen the spec already knows is found again under a fresh node id (AT-102) ----------

def known_spec(status: ReviewStatus = ReviewStatus.APPROVED) -> FlowSpec:
    """A human/video-learned spec that already holds both crawled screens, by name and pattern."""
    return FlowSpec(project="demo", version=4, review=Review(status=status, by="umesh"), screens=[
        Screen(id="scr_home", name="Home", url_pattern="/home"),
        Screen(id="scr_settings", name="Settings", url_pattern="/settings")])


def test_the_cli_door_points_a_rediscovered_screen_at_the_existing_one(tmp_path) -> None:
    store, _, _ = seeded(tmp_path)
    store.save_flowspec(known_spec())
    _merge_into_flowspec(store, "demo", CRAWL)
    spec = store.load_flowspec()
    assert len(spec.flows) == 1 and dangling_references(spec) == []
    flow = spec.flows[0]
    assert (flow.entry_screen, flow.exit_screen) == ("scr_home", "scr_settings")
    assert [s.screen_id for s in flow.steps] == ["scr_home", "scr_home"]


def test_the_ui_door_points_a_rediscovered_screen_at_the_existing_one(
        tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store, _, _ = seeded(tmp_path)
    store.save_flowspec(known_spec())
    resp = TestClient(app).post(f"/projects/demo/crawls/{CRAWL}/merge", follow_redirects=False)
    assert resp.status_code == 303
    spec = ProjectStore("demo", tmp_path).load_flowspec()
    assert len(spec.flows) == 1 and dangling_references(spec) == []
    assert spec.flows[0].exit_screen == "scr_settings"


def test_the_orchestrated_door_leaves_no_dangling_reference_after_the_model_fold(tmp_path) -> None:
    store, crawl, nodes = seeded(tmp_path)
    store.save_flowspec(known_spec())
    ctx = StageContext(store=store, run_id="run1")
    proposal_ref = make_discover_runner(PROJECT, lambda: (crawl, nodes))(ctx, None)
    assert dangling_references(read_json(Path(proposal_ref), FlowSpec)) == []
    make_model_runner()(ctx, proposal_ref)
    folded = store.load_flowspec()
    assert len(folded.flows) == 1 and dangling_references(folded) == []


def test_a_rediscovery_changes_the_screen_reference_not_the_flow_id(tmp_path) -> None:
    store, _, _ = seeded(tmp_path)
    fresh = merge_stored_crawl(store, None, "demo", CRAWL)
    known = merge_stored_crawl(store, known_spec(), "demo", CRAWL)
    assert [f.id for f in known.flows] == [f.id for f in fresh.flows]
    assert fresh.flows[0].entry_screen != known.flows[0].entry_screen
    assert merge_stored_crawl(store, known, "demo", CRAWL) == known  # re-crawl adds nothing
