"""The product map measured against ground truth, in a REAL browser (coverage V8).

Umesh, 2026-09-16: "puura product map hona chiaye na, end to end testing, each possible route".
Nothing checked a crawl's reached set against what a product actually has, so "the crawl
got past login" could not be told apart from "the crawl mapped the product".

`tests/fixtures/inventory_site/inventory.json` declares every screen of a small app behind a
login: nav menu pages, a page-2 list, a row only on page 2, two hash routes, a nested page, a
link inside a click-opened drawer, and one screen reachable only by submitting a form. A crawl
with the login case must enter every `reached` route, must not enter the `policy` one, and
coverage (V7) must name the refusal. A depth-bounded crawl must account for every route it
missed through a reason coverage gives, never silently.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.enums import (
    Action,
    ApprovalKind,
    CaseClass,
    CaseKind,
    CrawlStatus,
    EdgeOutcome,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore import run_crawl
from autotester.stages.explore_safety import FORM_SUBMIT_REFUSED
from autotester.store.project_store import ProjectStore

SITE = Path(__file__).resolve().parent / "fixtures" / "inventory_site"
INVENTORY = json.loads((SITE / "inventory.json").read_text(encoding="utf-8"))
ROUTES = {r["id"]: r for r in INVENTORY["routes"]}


def _crawl_inventory(tmp_path: Path, base: str,
                     bounds: CrawlBounds) -> tuple[Crawl, list[ScreenNode], list[ScreenEdge]]:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:  # decide "no browser" before the crawl, so a real failure never reads as a skip
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    url, login = f"{base}{INVENTORY['base']}", f"{base}{INVENTORY['login']['url']}"
    project = Project(slug="inv", name="Inventory", base_url=url,
                      allowed_domains=["127.0.0.1"], headed=False)
    paths = ProjectPaths("inv", tmp_path)
    paths.ensure()
    (tmp_path / ".env").write_text("", encoding="utf-8")
    store = ProjectStore("inv", tmp_path)
    store.add_approval(RunApproval(
        project="inv", run_kind=ApprovalKind.CRAWL, target=url, scope="local inventory fixture",
        max_actions=bounds.max_actions, wall_clock_s=bounds.wall_clock_s, granted_by="test",
        granted_at="2026-09-17", expires_at="2099-01-01",
    ).sign())
    creds = INVENTORY["login"]
    case = Case(project="inv", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="sign in", steps=[
                    Step(order=1, action=Action.NAVIGATE, target=login),
                    Step(order=2, action=Action.FILL, target="#username", value=creds["username"]),
                    Step(order=3, action=Action.FILL, target="#password", value=creds["password"]),
                    Step(order=4, action=Action.CLICK, target="#sign-in"),
                ])
    session = BrowserSession(project, SecretStore.load(project, tmp_path / ".env", strict=False),
                             tmp_path / "shots", paths, observer=PageObserver())
    session.start()
    try:
        crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=case,
                          bounds=bounds)
    finally:
        session.close()
    return crawl, store.list_nodes(crawl.id), store.list_edges(crawl.id)


def _entered(route: dict, nodes: list[ScreenNode]) -> bool:
    """A route is entered when a screen has its template AND, where the template is shared,
    the control only that route shows."""
    return any(
        n.url_template.endswith(route["template"])
        and (route["marker"] is None or any(e.name == route["marker"] for e in n.elements))
        for n in nodes
    )


def _reached_ids(nodes: list[ScreenNode]) -> set[str]:
    return {rid for rid, route in ROUTES.items() if _entered(route, nodes)}


FULL = CrawlBounds(max_screens=40, max_actions=200, wall_clock_s=240.0, max_depth=6)


def test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    """One crawl, two halves (a real crawl costs seconds): every click-reachable route is
    entered, and the form-gated one is not entered and is named by coverage as a refusal."""
    crawl, nodes, edges = _crawl_inventory(tmp_path, serve_dir(SITE), FULL)
    expected = {rid for rid, r in ROUTES.items() if r["expect"] == "reached"}
    missed = expected - _reached_ids(nodes)

    assert crawl.status is CrawlStatus.COMPLETED, crawl.stop_reason
    assert len(expected) == 11, "the precondition: the inventory was not trimmed"
    assert not missed, f"routes the crawl never entered: {sorted(missed)}"

    gated = [r for r in ROUTES.values() if r["expect"] == "policy"]
    search = {n.id for n in nodes if _entered(ROUTES["search"], [n])}
    assert [r["id"] for r in gated] == ["results"]
    assert not _entered(gated[0], nodes), "read_only must never submit the search form"
    assert any(e.from_node in search and e.outcome is EdgeOutcome.DENIED_POLICY
               and e.reason == FORM_SUBMIT_REFUSED for e in edges)
    holes = crawl.coverage.holes if crawl.coverage else []
    assert any(h.url_template.endswith("/app/search.html")
               and h.reason == f"policy:{FORM_SUBMIT_REFUSED}" for h in holes)


def _explained(route: dict, missed: set[str], crawl: Crawl) -> bool:
    """A missed route is accounted for when coverage names the control that leads to it, or
    when the screen that control sits on was itself missed (the chain broke earlier)."""
    if route["from"] in missed:
        return True
    cov = crawl.coverage
    named = [*cov.holes, *cov.screens_not_entered] if cov else []
    parent = ROUTES[route["from"]]["template"]
    return any(h.name == route["via"] and h.url_template.endswith(parent) for h in named)


def test_every_route_a_depth_bound_kept_out_is_accounted_for_by_coverage(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    crawl, nodes, _edges = _crawl_inventory(tmp_path, serve_dir(SITE),
                                            FULL.model_copy(update={"max_depth": 1}))
    expected = {rid for rid, r in ROUTES.items() if r["expect"] == "reached"}
    missed = expected - _reached_ids(nodes)

    assert missed, "the precondition: max_depth=1 must keep some routes out"
    silent = sorted(rid for rid in missed if not _explained(ROUTES[rid], missed, crawl))
    assert not silent, f"routes missed with no reason in coverage: {silent}"
    assert crawl.coverage is not None and crawl.coverage.percent < 100
